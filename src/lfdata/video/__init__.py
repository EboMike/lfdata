"""Video generation and visualization for LF games."""

import colorsys
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from lfdata.model import LFGame
from lfdata.video.element import UIElement, UIElementStyle
from lfdata.video.generator import (
    DEFAULT_CONFIG,
    VisualElementGenerator,
    _merge_configs,
)

__all__ = [
    "VideoGenerator",
    "UIElement",
    "UIElementStyle",
    "VisualElementGenerator",
]


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Converts a hex color string to an RGB tuple.

    Args:
        hex_str: The color hex string (e.g. '#FF5000' or 'FF5000').

    Returns:
        tuple[int, int, int]: The RGB integer values (0-255).
    """
    hex_str = hex_str.strip()
    if hex_str.startswith("#"):
        hex_str = hex_str[1:]
    try:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return r, g, b
    except Exception:
        return 255, 255, 255


def parse_color_with_alpha(
    color_hex: str, element_alpha: float = 1.0
) -> tuple[int, int, int, int]:
    """Parses a hex color and merges it with the element alpha component.

    Args:
        color_hex: The color hex string (e.g. '#ffffffff' or 'ffffffff').
        element_alpha: The element-specific opacity fraction (0.0 to 1.0).

    Returns:
        tuple[int, int, int, int]: The combined RGBA color values (0-255).
    """
    color_hex = color_hex.strip()
    if color_hex.startswith("#"):
        color_hex = color_hex[1:]
    try:
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)
        if len(color_hex) >= 8:
            a = int(color_hex[6:8], 16)
        else:
            a = 255
    except Exception:
        r, g, b, a = 255, 255, 255, 255

    final_a = int(a * element_alpha)
    return r, g, b, final_a


class VideoGenerator:
    """Generates visual videos from LF game events and data."""

    def __init__(self, game: LFGame) -> None:
        """Initializes the video generator with game data.

        Args:
            game: The LFGame data object.
        """
        self.game = game

    def generate(
        self,
        output_path: str | Path,
        config_path: str | Path | None = None,
    ) -> Path:
        """Generates a video file visualizing the game.

        This method loads the configuration, runs the replay frame-by-frame,
        renders each frame as a PNG image, compiles them into a video using
        ffmpeg, and cleans up the temporary files.

        Args:
            output_path: The output file path for the generated video.
            config_path: The optional configuration file path.

        Returns:
            Path: The path to the generated video file.
        """
        output_path = Path(output_path)
        config = self._load_config(config_path)

        hud_gen = VisualElementGenerator(self.game, config.get("player_name"), config)

        actual_duration = self.game.duration
        if hud_gen.game_ended_at is not None:
            actual_duration = hud_gen.game_ended_at
        if actual_duration is None:
            actual_duration = 0

        if not self.game.events:
            end_time = 0
        else:
            extra_footage = config.get("extra_footage_ms", 10000)
            end_time = actual_duration + extra_footage

        fps = config.get("fps", 60)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self._generate_frames(temp_path, end_time, fps, config, hud_gen)
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
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    config = _merge_configs(DEFAULT_CONFIG, loaded)
        except Exception as e:
            print(f"Warning: failed to load config: {e}")
        return config

    def _generate_frames(
        self,
        temp_path: Path,
        end_time: int,
        fps: int,
        config: dict[str, Any],
        hud_gen: VisualElementGenerator,
    ) -> None:
        """Generates all PNG frame images in parallel and saves them.

        Args:
            temp_path: The directory path to save frame PNGs.
            end_time: The end timestamp of the video in milliseconds.
            fps: The number of frames per second.
            config: The merged video styling and configuration options.
            hud_gen: Precomputed visual element HUD generator.
        """
        frame_step = 1000.0 / fps
        tasks = []
        frame_index = 0
        time_ms = 0.0

        while time_ms <= end_time:
            tasks.append((frame_index, int(time_ms)))
            frame_index += 1
            time_ms += frame_step
            if frame_step <= 0:
                break

        from concurrent.futures import ThreadPoolExecutor

        def worker(task: tuple[int, int]) -> None:
            f_idx, t_ms = task
            elements = hud_gen.generate_at(t_ms)
            img = self._render_frame(elements, t_ms, config)
            img.save(temp_path / f"frame_{f_idx:06d}.png")

        max_workers = min(16, max(1, os.cpu_count() or 4))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(worker, tasks)

    def _compile_video(self, frames_dir: Path, fps: int, output_path: Path) -> None:
        """Compiles PNG frames in a directory into a video using ffmpeg.

        Args:
            frames_dir: The directory containing PNG frames.
            fps: The frames per second.
            output_path: The target path of the output video.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.touch()

        cmd = [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frames_dir / "frame_%06d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
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
            print(f"Warning: ffmpeg video encoding failed/skipped: {e}")

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
        resolution = config.get("resolution", [1920, 1080])
        bg_hex = config.get("background_color", "#00000000")

        bg_color = parse_color_with_alpha(bg_hex)
        img = Image.new("RGBA", (resolution[0], resolution[1]), bg_color)

        for el in elements:
            if el.element_type == "scoreboard":
                self._draw_scoreboard(img, el, config)
            elif el.element_type == "downtime_bar":
                self._draw_downtime_bar(img, el)

        self._draw_text_elements(img, elements, config)
        return img

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
        teams = el.scoreboard_data.get("teams", []) if el.scoreboard_data else []
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
            p_count = len(team.get("players", []))
            team_heights[team["team_index"]] = header_h + (p_count * row_h) + totals_h

        if len(teams) == 2:
            t0, t1 = teams[0], teams[1]
            h0 = team_heights[t0["team_index"]]
            h1 = team_heights[t1["team_index"]]
            t0["y_pos"] = y_start + (t0["visual_rank"] - 1.0) * (h1 + spacing)
            t1["y_pos"] = y_start + (t1["visual_rank"] - 1.0) * (h0 + spacing)
        else:
            curr_y = y_start
            for t in sorted(teams, key=lambda x: x.get("visual_rank", 1.0)):
                t["y_pos"] = curr_y
                curr_y += team_heights[t["team_index"]] + spacing

        font_size = el.style.size or 20
        pixel_size = max(1, int(height * font_size / 800))
        bold_pixel_size = max(1, int(height * (font_size + 2) / 800))

        try:
            font = ImageFont.truetype(el.style.font, pixel_size)
            bold_font = ImageFont.truetype(el.style.font, bold_pixel_size)
        except OSError:
            try:
                font = ImageFont.load_default(size=pixel_size)
            except TypeError:
                font = ImageFont.load_default()
            try:
                bold_font = ImageFont.load_default(size=bold_pixel_size)
            except TypeError:
                bold_font = ImageFont.load_default()

        for team in teams:
            self._draw_team_table(
                image,
                team,
                team_heights[team["team_index"]],
                x_start,
                font,
                bold_font,
                header_h,
                row_h,
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
        color_hex = team.get("color_rgb", "#ffffff")
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
        border_color = text_color

        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        table_width = int(800 * image.width / 1920)
        ty = int(team["y_pos"])

        draw.rectangle(
            [x_start, ty, x_start + table_width, ty + th],
            fill=bg_fill,
            outline=border_color,
            width=2,
        )

        columns, offsets = self._resolve_scoreboard_columns(x_start, table_width)

        padding_y = int(5 * image.height / 1080)
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

        y_row = sep_y
        for p in team.get("players", []):
            p_color = text_color
            if p.get("is_eliminated"):
                p_color = gray_color
            elif p.get("is_down"):
                p_color = dimmed_color

            vals = self._compile_player_row_values(p, columns)
            row_padding = int(2 * image.height / 1080)
            for val, offset in zip(vals, offsets):
                draw.text((offset, y_row + row_padding), val, fill=p_color, font=font)
            y_row += row_h

        draw.line(
            [(x_start, y_row), (x_start + table_width, y_row)],
            fill=border_color,
            width=2,
        )
        tot_vals = self._compile_totals_row_values(team.get("totals", {}), columns)
        for val, offset in zip(tot_vals, offsets):
            draw.text(
                (offset, y_row + padding_y),
                val,
                fill=(255, 255, 255, 255),
                font=bold_font,
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
            "sm5" in self.game.game_type.lower()
            or "space marines" in self.game.game_type.lower()
        )

        columns = ["Player"]
        if is_sm5:
            columns.append("Role")
        columns.append("Score")
        if is_sm5:
            columns.extend(["Lives", "Shots", "Missiles", "Spec"])

        col_offset_map = {
            "Player": 20,
            "Role": 200,
            "Score": 350,
            "Lives": 450,
            "Shots": 550,
            "Missiles": 650,
            "Spec": 730,
        }

        offsets = [
            x_start + int(col_offset_map[col] * table_width / 800) for col in columns
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
            if col == "Player":
                vals.append(p.get("codename", ""))
            elif col == "Role":
                vals.append(p.get("role_name", ""))
            elif col == "Score":
                vals.append(str(p.get("score", 0)))
            elif col == "Lives":
                vals.append(str(p.get("lives", 0)))
            elif col == "Shots":
                vals.append(str(p.get("shots", 0)))
            elif col == "Missiles":
                vals.append(str(p.get("missiles", 0)))
            elif col == "Spec":
                vals.append(str(p.get("special_points", 0)))
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
            if col == "Player":
                vals.append("TOTAL")
            elif col == "Role":
                vals.append("")
            elif col == "Score":
                vals.append(str(totals.get("score", 0)))
            elif col == "Lives":
                vals.append(str(totals.get("lives", 0)))
            elif col == "Shots":
                vals.append(str(totals.get("shots", 0)))
            elif col == "Missiles":
                vals.append(str(totals.get("missiles", 0)))
            elif col == "Spec":
                vals.append(str(totals.get("special_points", 0)))
        return vals

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
        total_remaining = safe_ms + resettable_ms

        if total_remaining <= 0:
            return

        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        draw.rectangle(
            [x1, y1, x2, y2],
            fill=(0, 0, 0, 100),
            outline=(255, 255, 255, 255),
            width=2,
        )

        inner_x1 = x1 + 2
        inner_x2 = x2 - 2
        inner_y1 = y1 + 2
        inner_y2 = y2 - 2

        max_inner_w = inner_x2 - inner_x1
        rem_width = int(max_inner_w * total_remaining / 8000)
        rem_width = max(0, min(max_inner_w, rem_width))

        if rem_width > 0:
            safe_width = int(rem_width * safe_ms / total_remaining)

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

        image.alpha_composite(overlay)

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

        anchor_map = {"left": "la", "center": "ma", "right": "ra"}

        for el in elements:
            if el.element_type != "text" or not el.text:
                continue

            x_coord = int(width * (el.x if el.x is not None else 0.5))
            y_coord = int(height * (el.y if el.y is not None else 0.5))
            anchor = anchor_map.get(el.align or "left", "la")

            pixel_size = max(1, int(height * el.style.size / 800))

            font_file = el.style.font
            if el.style.style == "bold":
                if font_file.lower() == "verdana":
                    font_file = "verdanab.ttf"
                elif font_file.lower() == "arial":
                    font_file = "arialbd.ttf"
            elif el.style.style == "italic":
                if font_file.lower() == "verdana":
                    font_file = "verdanai.ttf"
                elif font_file.lower() == "arial":
                    font_file = "ariali.ttf"

            try:
                font = ImageFont.truetype(font_file, pixel_size)
            except OSError:
                try:
                    font = ImageFont.load_default(size=pixel_size)
                except TypeError:
                    font = ImageFont.load_default()

            text_color = parse_color_with_alpha(el.style.color, el.alpha)
            bg_color = parse_color_with_alpha(el.style.background_color, el.alpha)

            overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
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
