"""Video generation and visualization for LF games."""

import colorsys
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from lfdata.model import LFGame
from lfdata.video.element import UIElement
from lfdata.video.generator import VisualElementGenerator
from lfdata.video.helpers import (
    DEFAULT_CONFIG,
    _merge_configs,
    hex_to_rgb,
    parse_color_with_alpha,
)


class VideoGenerator:
    """Generates visual videos from LF game events and data."""

    def __init__(self, game: LFGame) -> None:
        """Initializes the video generator with game data.

        Args:
            game: The LFGame data object.
        """
        self.game = game

    def _determine_video_end_ms(
        self,
        hud_gen: VisualElementGenerator,
        config: dict[str, Any],
        video_end_ms: int | None,
    ) -> int:
        """Determines the end timestamp in milliseconds for video generation.

        Args:
            hud_gen: Precomputed visual element HUD generator.
            config: Styling and configuration options.
            video_end_ms: Optional explicit ending timestamp in milliseconds.

        Returns:
            int: The calculated end timestamp in milliseconds.
        """
        if video_end_ms is not None:
            return video_end_ms

        actual_duration_ms = self.game.duration
        if hud_gen.game_ended_at_ms is not None:
            actual_duration_ms = hud_gen.game_ended_at_ms
        if actual_duration_ms is None:
            actual_duration_ms = 0

        if not self.game.events:
            return 0

        extra_footage_ms = config.get('extra_footage_ms', 10000)
        return actual_duration_ms + extra_footage_ms

    def generate(
        self,
        output_path: str | Path,
        config_path: str | Path | None = None,
        video_start_ms: int = 0,
        video_end_ms: int | None = None,
        video_player: str | None = None,
    ) -> Path:
        """Generates a video file visualizing the game.

        This method loads the configuration, runs the replay frame-by-frame,
        renders each frame as a PNG image, compiles them into a video using
        ffmpeg, and cleans up the temporary files.

        Args:
            output_path: The output file path for the generated video.
            config_path: The optional configuration file path.
            video_start_ms: The starting millisecond timestamp for the video.
            video_end_ms: The ending millisecond timestamp for the video.
            video_player: Optional player name to focus on.

        Returns:
            Path: The path to the generated video file.
        """
        output_path = Path(output_path)
        config = self._load_config(config_path)
        if video_player is not None:
            config['player_name'] = video_player

        hud_gen = VisualElementGenerator(
            self.game, config.get('player_name'), config
        )

        end_ms = self._determine_video_end_ms(hud_gen, config, video_end_ms)
        start_ms = video_start_ms
        fps = config.get('fps', 60)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self._generate_frames(
                temp_path=temp_path,
                start_ms=start_ms,
                end_ms=end_ms,
                fps=fps,
                config=config,
                hud_gen=hud_gen,
            )
            self._compile_video(temp_path, fps, output_path)

        return output_path

    def _load_config(self, config_path: str | Path | None) -> dict[str, Any]:
        """Loads and parses the optional YAML configuration file.

        Args:
            config_path: Optional config file path.

        Returns:
            dict[str, Any]: Loaded config dictionary.
        """
        config = DEFAULT_CONFIG
        if not config_path:
            return config

        import yaml

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    config = _merge_configs(DEFAULT_CONFIG, loaded)
        except Exception as e:
            print(f'Warning: failed to load config: {e}')
        return config

    def _render_and_save_frame(
        self,
        frame_idx: int,
        time_ms: int,
        temp_path: Path,
        config: dict[str, Any],
        hud_gen: VisualElementGenerator,
    ) -> None:
        """Renders a single frame and saves it as a PNG image.

        Args:
            frame_idx: The sequential index of the frame.
            time_ms: The millisecond timestamp.
            temp_path: The directory path to save frame PNGs.
            config: The merged video styling options.
            hud_gen: Precomputed visual element HUD generator.
        """
        elements = hud_gen.generate_at(time_ms)
        img = self._render_frame(elements, time_ms, config)
        img.save(temp_path / f'frame_{frame_idx:05d}.png')

    def _generate_frames(
        self,
        temp_path: Path,
        start_ms: int,
        end_ms: int,
        fps: int,
        config: dict[str, Any],
        hud_gen: VisualElementGenerator,
    ) -> None:
        """Generates all PNG frame images in parallel and saves them.

        Args:
            temp_path: The directory path to save frame PNGs.
            start_ms: The start timestamp of the video in milliseconds.
            end_ms: The end timestamp of the video in milliseconds.
            fps: The number of frames per second.
            config: The merged video styling and configuration options.
            hud_gen: Precomputed visual element HUD generator.
        """
        frame_step = 1000.0 / fps
        tasks = []
        frame_index = 0
        time_ms = float(start_ms)

        while time_ms <= end_ms:
            tasks.append((frame_index, int(time_ms)))
            frame_index += 1
            time_ms += frame_step
            if frame_step <= 0:
                break

        from concurrent.futures import ThreadPoolExecutor

        def worker(task: tuple[int, int]) -> None:
            """Thread worker function to render a single frame task.

            Args:
                task: A tuple of (frame_index, time_ms).
            """
            f_idx, t_ms = task
            self._render_and_save_frame(
                frame_idx=f_idx,
                time_ms=t_ms,
                temp_path=temp_path,
                config=config,
                hud_gen=hud_gen,
            )

        max_workers = min(16, max(1, os.cpu_count() or 4))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(worker, tasks)

    def _compile_video(
        self, frames_dir: Path, fps: int, output_path: Path
    ) -> None:
        """Compiles PNG frames in a directory into a video using ffmpeg.

        Args:
            frames_dir: The directory containing PNG frames.
            fps: The frames per second.
            output_path: The target path of the output video.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.touch()

        cmd = [
            'ffmpeg',
            '-y',
            '-framerate',
            str(fps),
            '-i',
            str(frames_dir / 'frame_%05d.png'),
            '-c:v',
            'libx264',
            '-pix_fmt',
            'yuv420p',
            str(output_path),
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            print(f'Warning: ffmpeg video encoding failed/skipped: {e}')

    def _render_frame(
        self,
        elements: list[UIElement],
        time_ms: int,
        config: dict[str, Any],
    ) -> Image.Image:
        """Renders all active UI elements onto an Image object.

        Args:
            elements: The active visual elements to render.
            time_ms: The current millisecond timestamp.
            config: The merged video configuration options.

        Returns:
            Image.Image: The rendered frame image.
        """
        resolution = config.get('resolution', [1920, 1080])
        bg_hex = config.get('background_color', '#00000000')

        bg_color = parse_color_with_alpha(bg_hex)
        img = Image.new('RGBA', (resolution[0], resolution[1]), bg_color)

        for el in elements:
            if el.element_type == 'scoreboard':
                self._draw_scoreboard(img, el, config)
            elif el.element_type == 'downtime_bar':
                self._draw_downtime_bar(img, el)

        self._draw_text_elements(img, elements, config)
        return img

    def _calculate_team_y_positions(
        self,
        teams: list[dict[str, Any]],
        y_start: int,
        spacing: int,
        team_heights: dict[int, int],
    ) -> None:
        """Calculates and assigns y_pos to teams based on visual ranks.

        Args:
            teams: List of team data dicts.
            y_start: Starting Y position in pixels.
            spacing: Vertical spacing between teams in pixels.
            team_heights: Precalculated height mapping for each team.
        """
        if len(teams) == 2:
            t0, t1 = teams[0], teams[1]
            h0 = team_heights[t0['team_index']]
            h1 = team_heights[t1['team_index']]
            t0['y_pos'] = y_start + (t0['visual_rank'] - 1.0) * (h1 + spacing)
            t1['y_pos'] = y_start + (t1['visual_rank'] - 1.0) * (h0 + spacing)
        else:
            curr_y = y_start
            for t in sorted(teams, key=lambda x: x.get('visual_rank', 1.0)):
                t['y_pos'] = curr_y
                curr_y += team_heights[t['team_index']] + spacing

    def _load_scoreboard_fonts(
        self,
        font_name: str,
        pixel_size: int,
        bold_pixel_size: int,
    ) -> tuple[ImageFont.ImageFont, ImageFont.ImageFont]:
        """Loads and returns standard and bold fonts for the scoreboard.

        Args:
            font_name: Font family/file name.
            pixel_size: Standard font size.
            bold_pixel_size: Bold font size.

        Returns:
            tuple[ImageFont.ImageFont, ImageFont.ImageFont]: The loaded fonts.
        """
        try:
            font = ImageFont.truetype(font_name, pixel_size)
            bold_font = ImageFont.truetype(font_name, bold_pixel_size)
        except OSError:
            try:
                font = ImageFont.load_default(size=pixel_size)
            except TypeError:
                font = ImageFont.load_default()
            try:
                bold_font = ImageFont.load_default(size=bold_pixel_size)
            except TypeError:
                bold_font = ImageFont.load_default()
        return font, bold_font

    def _draw_scoreboard(
        self,
        image: Image.Image,
        el: UIElement,
        config: dict[str, Any],
    ) -> None:
        """Draws the animated scoreboard table onto the image.

        Args:
            image: The Image canvas to draw on.
            el: The scoreboard UIElement containing team details.
            config: The merged video configuration options.
        """
        teams = (
            el.scoreboard_data.get('teams', []) if el.scoreboard_data else []
        )
        if not teams:
            return

        height = image.height
        header_h = int(35 * height / 1080)
        row_h = int(28 * height / 1080)
        totals_h = int(35 * height / 1080)
        spacing = int(20 * height / 1080)

        x_config = el.x if el.x is not None else 0.1
        y_config = el.y if el.y is not None else 0.6
        x_start = int(image.width * x_config)
        y_start = int(height * y_config)

        team_heights = {}
        for team in teams:
            p_count = len(team.get('players', []))
            team_heights[team['team_index']] = (
                header_h + (p_count * row_h) + totals_h
            )

        self._calculate_team_y_positions(teams, y_start, spacing, team_heights)

        font_size = el.style.size or 20
        pixel_size = max(1, int(height * font_size / 800))
        bold_pixel_size = max(1, int(height * (font_size + 2) / 800))

        font, bold_font = self._load_scoreboard_fonts(
            el.style.font, pixel_size, bold_pixel_size
        )

        for team in teams:
            self._draw_team_table(
                image,
                team,
                team_heights[team['team_index']],
                x_start,
                font,
                bold_font,
                header_h,
                row_h,
            )

    def _calculate_team_colors(
        self, team: dict[str, Any]
    ) -> tuple[
        tuple[int, int, int, int],
        tuple[int, int, int, int],
        tuple[int, int, int, int],
        tuple[int, int, int, int],
    ]:
        """Calculates color constants for rendering a team table.

        Args:
            team: The team data dictionary.

        Returns:
            tuple: bg_fill, text_color, dimmed_color, gray_color.
        """
        color_hex = team.get('color_rgb', '#ffffff')
        r_sat, g_sat, b_sat = hex_to_rgb(color_hex)
        h, lightness, s = colorsys.rgb_to_hls(
            r_sat / 255.0, g_sat / 255.0, b_sat / 255.0
        )

        r_semi, g_semi, b_semi = colorsys.hls_to_rgb(h, lightness, s * 0.5)
        bg_fill = (int(r_semi * 255), int(g_semi * 255), int(b_semi * 255), 100)

        r_sat_hls, g_sat_hls, b_sat_hls = colorsys.hls_to_rgb(h, lightness, 1.0)
        text_color = (
            int(r_sat_hls * 255),
            int(g_sat_hls * 255),
            int(b_sat_hls * 255),
            255,
        )
        dimmed_color = (
            int(r_sat_hls * 255),
            int(g_sat_hls * 255),
            int(b_sat_hls * 255),
            128,
        )
        gray_color = (128, 128, 128, 255)
        return bg_fill, text_color, dimmed_color, gray_color

    def _draw_table_structure(
        self,
        draw: ImageDraw.ImageDraw,
        x_start: int,
        ty: int,
        table_width: int,
        th: int,
        bg_fill: tuple[int, int, int, int],
        border_color: tuple[int, int, int, int],
        columns: list[str],
        offsets: list[int],
        bold_font: ImageFont.ImageFont,
        header_h: int,
        padding_y: int,
    ) -> int:
        """Draws the outer table rectangle and the header columns.

        Args:
            draw: ImageDraw context.
            x_start: X start coordinate.
            ty: Y start coordinate.
            table_width: Width of the table.
            th: Total table height.
            bg_fill: Background fill color.
            border_color: Border color.
            columns: List of column names.
            offsets: X offsets for each column.
            bold_font: Bold font.
            header_h: Header height.
            padding_y: Vertical padding.

        Returns:
            int: The Y coordinate starting for player rows.
        """
        draw.rectangle(
            [x_start, ty, x_start + table_width, ty + th],
            fill=bg_fill,
            outline=border_color,
            width=2,
        )

        for col_name, offset in zip(columns, offsets):
            draw.text(
                (offset, ty + padding_y),
                col_name,
                fill=(255, 255, 255, 255),
                font=bold_font,
            )

        sep_y = ty + header_h
        draw.line(
            [(x_start, sep_y), (x_start + table_width, sep_y)],
            fill=border_color,
            width=2,
        )
        return sep_y

    def _draw_player_rows(
        self,
        draw: ImageDraw.ImageDraw,
        players: list[dict[str, Any]],
        columns: list[str],
        offsets: list[int],
        font: ImageFont.ImageFont,
        text_color: tuple[int, int, int, int],
        gray_color: tuple[int, int, int, int],
        dimmed_color: tuple[int, int, int, int],
        y_row: int,
        row_h: int,
        height: int,
    ) -> int:
        """Draws individual player rows inside the table.

        Args:
            draw: ImageDraw context.
            players: List of player dicts.
            columns: List of columns.
            offsets: List of column offsets.
            font: Standard font.
            text_color: Active player text color.
            gray_color: Eliminated player text color.
            dimmed_color: Down player text color.
            y_row: Current Y position coordinate.
            row_h: Row height.
            height: Image height for scaling padding.

        Returns:
            int: The Y coordinate ending after player rows.
        """
        for p in players:
            p_color = text_color
            if p.get('is_eliminated'):
                p_color = gray_color
            elif p.get('is_down'):
                p_color = dimmed_color

            vals = self._compile_player_row_values(p, columns)
            row_padding = int(2 * height / 1080)
            for val, offset in zip(vals, offsets):
                draw.text(
                    (offset, y_row + row_padding), val, fill=p_color, font=font
                )
            y_row += row_h
        return y_row

    def _draw_totals_row(
        self,
        draw: ImageDraw.ImageDraw,
        totals: dict[str, int],
        columns: list[str],
        offsets: list[int],
        bold_font: ImageFont.ImageFont,
        border_color: tuple[int, int, int, int],
        x_start: int,
        table_width: int,
        y_row: int,
        padding_y: int,
    ) -> None:
        """Draws the totals row at the bottom of the table.

        Args:
            draw: ImageDraw context.
            totals: Dict of totals.
            columns: List of columns.
            offsets: List of column offsets.
            bold_font: Bold font.
            border_color: Border color.
            x_start: X start coordinate.
            table_width: Table width.
            y_row: Y coordinate starting the totals row.
            padding_y: Vertical padding.
        """
        draw.line(
            [(x_start, y_row), (x_start + table_width, y_row)],
            fill=border_color,
            width=2,
        )
        tot_vals = self._compile_totals_row_values(totals, columns)
        for val, offset in zip(tot_vals, offsets):
            draw.text(
                (offset, y_row + padding_y),
                val,
                fill=(255, 255, 255, 255),
                font=bold_font,
            )

    def _draw_team_table(
        self,
        image: Image.Image,
        team: dict[str, Any],
        th: int,
        x_start: int,
        font: ImageFont.ImageFont,
        bold_font: ImageFont.ImageFont,
        header_h: int,
        row_h: int,
    ) -> None:
        """Draws a single team's table border, headers, player rows, and totals.

        Args:
            image: The Image canvas to draw on.
            team: The team data dictionary.
            th: Total table height in pixels.
            x_start: The absolute starting X coordinate of the table.
            font: Standard size scoreboard text font.
            bold_font: Bold size scoreboard text font.
            header_h: The scoreboard header height in pixels.
            row_h: The scoreboard player row height in pixels.
        """
        bg_fill, text_color, dimmed_color, gray_color = (
            self._calculate_team_colors(team)
        )
        border_color = text_color

        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        table_width = int(800 * image.width / 1920)
        ty = int(team['y_pos'])

        columns, offsets = self._resolve_scoreboard_columns(
            x_start, table_width
        )
        padding_y = int(5 * image.height / 1080)

        sep_y = self._draw_table_structure(
            draw=draw,
            x_start=x_start,
            ty=ty,
            table_width=table_width,
            th=th,
            bg_fill=bg_fill,
            border_color=border_color,
            columns=columns,
            offsets=offsets,
            bold_font=bold_font,
            header_h=header_h,
            padding_y=padding_y,
        )

        y_row = self._draw_player_rows(
            draw=draw,
            players=team.get('players', []),
            columns=columns,
            offsets=offsets,
            font=font,
            text_color=text_color,
            gray_color=gray_color,
            dimmed_color=dimmed_color,
            y_row=sep_y,
            row_h=row_h,
            height=image.height,
        )

        self._draw_totals_row(
            draw=draw,
            totals=team.get('totals', {}),
            columns=columns,
            offsets=offsets,
            bold_font=bold_font,
            border_color=border_color,
            x_start=x_start,
            table_width=table_width,
            y_row=y_row,
            padding_y=padding_y,
        )

        image.alpha_composite(overlay)

    def _resolve_scoreboard_columns(
        self, x_start: int, table_width: int
    ) -> tuple[list[str], list[int]]:
        """Resolves which scoreboard columns to display based on game type.

        Args:
            x_start: Table starting X position.
            table_width: Table width in pixels.

        Returns:
            tuple: Active column headers and their absolute pixel X coordinates.
        """
        is_sm5 = (
            'sm5' in self.game.game_type.lower()
            or 'space marines' in self.game.game_type.lower()
        )

        columns = ['Player']
        if is_sm5:
            columns.append('Role')
        columns.append('Score')
        if is_sm5:
            columns.extend(['Lives', 'Shots', 'Missiles', 'Spec'])

        col_offset_map = {
            'Player': 20,
            'Role': 200,
            'Score': 350,
            'Lives': 450,
            'Shots': 550,
            'Missiles': 650,
            'Spec': 730,
        }

        offsets = [
            x_start + int(col_offset_map[col] * table_width / 800)
            for col in columns
        ]
        return columns, offsets

    def _compile_player_row_values(
        self, p: dict[str, Any], columns: list[str]
    ) -> list[str]:
        """Compiles values for a player row in column order.

        Args:
            p: The player data dictionary.
            columns: Active column headers.

        Returns:
            list[str]: Player row cell values.
        """
        vals = []
        for col in columns:
            if col == 'Player':
                vals.append(p.get('codename', ''))
            elif col == 'Role':
                vals.append(p.get('role_name', ''))
            elif col == 'Score':
                vals.append(str(p.get('score', 0)))
            elif col == 'Lives':
                vals.append(str(p.get('lives', 0)))
            elif col == 'Shots':
                vals.append(str(p.get('shots', 0)))
            elif col == 'Missiles':
                vals.append(str(p.get('missiles', 0)))
            elif col == 'Spec':
                vals.append(str(p.get('special_points', 0)))
        return vals

    def _compile_totals_row_values(
        self, totals: dict[str, Any], columns: list[str]
    ) -> list[str]:
        """Compiles values for the team totals row in column order.

        Args:
            totals: The team totals data dictionary.
            columns: Active column headers.

        Returns:
            list[str]: Totals row cell values.
        """
        vals = []
        for col in columns:
            if col == 'Player':
                vals.append('TOTAL')
            elif col == 'Role':
                vals.append('')
            elif col == 'Score':
                vals.append(str(totals.get('score', 0)))
            elif col == 'Lives':
                vals.append(str(totals.get('lives', 0)))
            elif col == 'Shots':
                vals.append(str(totals.get('shots', 0)))
            elif col == 'Missiles':
                vals.append(str(totals.get('missiles', 0)))
            elif col == 'Spec':
                vals.append(str(totals.get('special_points', 0)))
        return vals

    def _draw_downtime_progress(
        self,
        draw: ImageDraw.ImageDraw,
        inner_x1: int,
        inner_x2: int,
        inner_y1: int,
        inner_y2: int,
        safe_ms: int,
        total_remaining_ms: int,
    ) -> None:
        """Draws the safe and resettable progress rects inside the downtime bar.

        Args:
            draw: ImageDraw context.
            inner_x1: Inner rectangle X1.
            inner_x2: Inner rectangle X2.
            inner_y1: Inner rectangle Y1.
            inner_y2: Inner rectangle Y2.
            safe_ms: Remaining safe duration in milliseconds.
            total_remaining_ms: Total remaining downtime in milliseconds.
        """
        max_inner_w = inner_x2 - inner_x1
        rem_width = int(max_inner_w * total_remaining_ms / 8000)
        rem_width = max(0, min(max_inner_w, rem_width))

        if rem_width > 0:
            safe_width = int(rem_width * safe_ms / total_remaining_ms)

            if safe_width > 0:
                draw.rectangle(
                    [inner_x1, inner_y1, inner_x1 + safe_width, inner_y2],
                    fill=(255, 0, 0, 255),
                )
            if rem_width - safe_width > 0:
                draw.rectangle(
                    [
                        inner_x1 + safe_width,
                        inner_y1,
                        inner_x1 + rem_width,
                        inner_y2,
                    ],
                    fill=(255, 255, 0, 255),
                )

    def _draw_downtime_bar(self, image: Image.Image, el: UIElement) -> None:
        """Draws the downtime bar representing safe and resettable time.

        Args:
            image: The Image canvas to draw on.
            el: The downtime bar UIElement.
        """
        tl = el.top_left if el.top_left is not None else [0.3, 0.3]
        br = el.bottom_right if el.bottom_right is not None else [0.7, 0.35]

        width, height = image.size
        x1 = int(width * tl[0])
        y1 = int(height * tl[1])
        x2 = int(width * br[0])
        y2 = int(height * br[1])

        safe_ms = el.safe_ms
        resettable_ms = el.resettable_ms
        total_remaining_ms = safe_ms + resettable_ms

        if total_remaining_ms <= 0:
            return

        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        draw.rectangle(
            [x1, y1, x2, y2],
            fill=(0, 0, 0, 100),
            outline=(255, 255, 255, 255),
            width=2,
        )

        self._draw_downtime_progress(
            draw=draw,
            inner_x1=x1 + 2,
            inner_x2=x2 - 2,
            inner_y1=y1 + 2,
            inner_y2=y2 - 2,
            safe_ms=safe_ms,
            total_remaining_ms=total_remaining_ms,
        )

        image.alpha_composite(overlay)

    def _load_text_font(
        self,
        font_file: str,
        style: str | None,
        pixel_size: int,
    ) -> ImageFont.ImageFont:
        """Resolves font variants and loads font with error fallback.

        Args:
            font_file: Font family/file name.
            style: Font style (e.g. bold, italic).
            pixel_size: Size of font in pixels.

        Returns:
            ImageFont.ImageFont: The loaded font.
        """
        if style == 'bold':
            if font_file.lower() == 'verdana':
                font_file = 'verdanab.ttf'
            elif font_file.lower() == 'arial':
                font_file = 'arialbd.ttf'
        elif style == 'italic':
            if font_file.lower() == 'verdana':
                font_file = 'verdanai.ttf'
            elif font_file.lower() == 'arial':
                font_file = 'ariali.ttf'

        try:
            return ImageFont.truetype(font_file, pixel_size)
        except OSError:
            try:
                return ImageFont.load_default(size=pixel_size)
            except TypeError:
                return ImageFont.load_default()

    def _draw_text_elements(
        self,
        image: Image.Image,
        elements: list[UIElement],
        config: dict[str, Any],
    ) -> None:
        """Draws all text elements onto the image.

        Args:
            image: The Image canvas to draw on.
            elements: The active elements on the frame.
            config: The merged video configuration options.
        """
        width, height = image.size

        anchor_map = {'left': 'la', 'center': 'ma', 'right': 'ra'}

        for el in elements:
            if el.element_type != 'text' or not el.text:
                continue

            x_coord = int(width * (el.x if el.x is not None else 0.5))
            y_coord = int(height * (el.y if el.y is not None else 0.5))
            anchor = anchor_map.get(el.align or 'left', 'la')

            pixel_size = max(1, int(height * el.style.size / 800))
            font = self._load_text_font(
                font_file=el.style.font,
                style=el.style.style,
                pixel_size=pixel_size,
            )

            text_color = parse_color_with_alpha(el.style.color, el.alpha)
            bg_color = parse_color_with_alpha(
                el.style.background_color, el.alpha
            )

            overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            if bg_color[3] > 0:
                bbox = draw.textbbox(
                    (x_coord, y_coord), el.text, font=font, anchor=anchor
                )
                padding = max(1, int(height * 4 / 800))
                padded_bbox = (
                    bbox[0] - padding,
                    bbox[1] - padding,
                    bbox[2] + padding,
                    bbox[3] + padding,
                )
                draw.rectangle(padded_bbox, fill=bg_color)

            draw.text(
                (x_coord, y_coord),
                el.text,
                fill=text_color,
                font=font,
                anchor=anchor,
            )
            image.alpha_composite(overlay)
