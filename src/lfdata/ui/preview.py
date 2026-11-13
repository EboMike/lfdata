"""Image preview and playback control panel for the LF data UI.

This module provides a GUI panel widget (`ImagePreview`) featuring frame
rendering controls, a timeline scrub slider, playback buttons, debounced
asynchronous frame updates, and an interactive PIL image preview canvas.

Usage example:
    from lfdata.ui.preview import ImagePreview

    preview = ImagePreview(parent=window, config_manager=cfg_mgr)
    preview.pack(fill='both', expand=True)
"""

import copy
import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable
from PIL import Image, ImageTk

from lfdata.model.constants.time import MS_PER_SECOND, SECONDS_PER_MINUTE
from lfdata.ui.config_manager import UIConfigManager
from lfdata.ui.preview_renderer import PreviewRenderer
from lfdata.video.constants import (
    DEFAULT_EXTRA_FOOTAGE_MS,
    DEFAULT_PREGAME_DELAY_MS,
)

DEFAULT_PREVIEW_WIDTH: int = 640
DEFAULT_PREVIEW_HEIGHT: int = 360


class ImagePreview(ttk.LabelFrame):
    """GUI widget displaying rendered frame previews and playback controls.

    Attributes:
        config_manager: UIConfigManager instance managing layout state.
        current_time_ms: Current timeline scrub position in milliseconds.
        on_time_changed_callback: Optional callback function triggered on scrub.
        renderer: PreviewRenderer instance managing caching and frame rendering.
        async_render: Whether to perform rendering on a background thread.
        last_rendered_image: Most recently rendered PIL Image instance.
    """

    def __init__(
        self,
        parent: tk.Widget,
        config_manager: UIConfigManager,
        on_time_changed_callback: Callable[[int], None] | None = None,
        preview_renderer: PreviewRenderer | None = None,
        async_render: bool = False,
    ) -> None:
        """Initializes the image preview panel.

        Args:
            parent: The parent tkinter widget.
            config_manager: The configuration manager instance.
            on_time_changed_callback: Optional timestamp change callback.
            preview_renderer: Optional PreviewRenderer instance.
            async_render: Whether to perform rendering on a background thread.
        """
        super().__init__(parent, text=' Rendered Preview ')
        self.config_manager = config_manager
        self.current_time_ms = 0
        self.on_time_changed_callback = on_time_changed_callback
        self.renderer = preview_renderer or PreviewRenderer()
        self.async_render = async_render

        self._debounce_timer_id: str | None = None
        self._render_generation: int = 0
        self.last_rendered_image: Image.Image | None = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Creates control buttons, slider, and preview image widgets."""
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(ctrl_frame, text='Player Focus:').pack(side='left', padx=2)
        self.player_var = tk.StringVar(value='None')
        self.cmb_player = ttk.Combobox(
            ctrl_frame,
            textvariable=self.player_var,
            state='readonly',
            width=20,
        )
        self.cmb_player.pack(side='left', padx=5)
        self.cmb_player.bind('<<ComboboxSelected>>', self._on_player_changed)

        self.btn_refresh = ttk.Button(
            ctrl_frame, text='Refresh Preview', command=self.update_preview
        )
        self.btn_refresh.pack(side='right', padx=5)

        self.lbl_time = ttk.Label(ctrl_frame, text='Time: 0 ms (00:00)')
        self.lbl_time.pack(side='right', padx=10)

        self.slider_var = tk.DoubleVar(value=0.0)
        self.slider = ttk.Scale(
            self,
            from_=0.0,
            to=100.0,
            orient='horizontal',
            variable=self.slider_var,
            command=self._on_slider_move,
        )
        self.slider.pack(fill='x', padx=10, pady=5)
        self.slider.bind('<ButtonRelease-1>', lambda e: self.update_preview())

        self.img_frame = ttk.Frame(
            self,
            width=DEFAULT_PREVIEW_WIDTH,
            height=DEFAULT_PREVIEW_HEIGHT,
            style='Preview.TFrame',
        )
        self.img_frame.pack(fill='both', expand=True, padx=5, pady=5)
        self.img_frame.pack_propagate(False)

        self.img_frame.bind('<Configure>', self._on_frame_configure)

        self.lbl_image = ttk.Label(
            self.img_frame,
            text='Please load a TDF file to enable preview.',
            anchor='center',
        )
        self.lbl_image.pack(fill='both', expand=True)

    def on_tdf_loaded(self) -> None:
        """Updates slider range and player dropdown options when TDF loads."""
        self.renderer.clear_cache()
        players = ['None'] + self.config_manager.get_player_names()
        self.cmb_player['values'] = players
        self.player_var.set('None')

        duration_ms = 0
        if self.config_manager.game:
            hud_gen, _ = self.renderer.get_or_create_generators(
                game=self.config_manager.game,
                player_name=None,
                config=self.config_manager.config,
            )
            max_ms = hud_gen.get_video_end_ms()
        else:
            extra_ms = self.config_manager.config.get(
                'extra_footage_ms', DEFAULT_EXTRA_FOOTAGE_MS
            )
            pregame_ms = self.config_manager.config.get(
                'pregame_delay_ms', DEFAULT_PREGAME_DELAY_MS
            )
            max_ms = duration_ms + extra_ms + pregame_ms

        self.slider.config(to=float(max_ms))
        self.slider_var.set(0.0)
        self.current_time_ms = 0
        self._update_time_label(0)
        self.update_preview()

    def _on_player_changed(self, event: tk.Event) -> None:
        """Triggers updates when focused player is changed.

        Args:
            event: The combobox select event.
        """
        self.update_preview()

    def _on_slider_move(self, val: str) -> None:
        """Handles slider moves to update label and schedule preview render.

        Args:
            val: The current slider value as string.
        """
        val_ms = int(float(val))
        self.current_time_ms = val_ms
        self.config_manager.current_time_ms = val_ms
        self._update_time_label(val_ms)
        if self.on_time_changed_callback:
            self.on_time_changed_callback(val_ms)
        self.schedule_preview(debounce_ms=100)

    def _update_time_label(self, time_ms: int) -> None:
        """Formats and sets the text for the time indicator label.

        Args:
            time_ms: The timestamp in milliseconds.
        """
        total_sec = time_ms // MS_PER_SECOND
        min_part = total_sec // SECONDS_PER_MINUTE
        sec_part = total_sec % SECONDS_PER_MINUTE
        self.lbl_time.config(
            text=f'Time: {time_ms:,} ms ({min_part:02d}:{sec_part:02d})'
        )

    def schedule_preview(self, debounce_ms: int = 250) -> None:
        """Schedules a debounced preview update after the given delay.

        Args:
            debounce_ms: Delay in milliseconds before triggering render.
        """
        self._cancel_debounce_timer()
        self._debounce_timer_id = str(
            self.after(debounce_ms, self._on_debounce_fired)
        )

    def _cancel_debounce_timer(self) -> None:
        """Cancels any pending debounced preview update timer."""
        if self._debounce_timer_id is not None:
            try:
                self.after_cancel(self._debounce_timer_id)
            except Exception:
                pass
            self._debounce_timer_id = None

    def _on_debounce_fired(self) -> None:
        """Invoked when the debounce timer elapses."""
        self._debounce_timer_id = None
        self.update_preview()

    def update_preview(
        self,
        sync: bool = False,
        debounce_ms: int = 0,
    ) -> None:
        """Renders the current frame either in-memory or via subprocess.

        Args:
            sync: Whether to force synchronous rendering on the caller thread.
            debounce_ms: Optional debounce delay in milliseconds.
        """
        if debounce_ms > 0:
            self.schedule_preview(debounce_ms=debounce_ms)
            return

        self._cancel_debounce_timer()

        if not self.config_manager.tdf_path and not self.config_manager.game:
            self.lbl_image.config(
                text='Please load a TDF file to enable preview.'
            )
            return

        if self.last_rendered_image is None:
            self.lbl_image.config(text='Rendering frame, please wait...')
            self.update_idletasks()

        self._render_generation += 1
        gen_id = self._render_generation

        p_focus = self.player_var.get()
        norm_player = p_focus if p_focus and p_focus != 'None' else None
        cfg_copy = copy.deepcopy(self.config_manager.config)
        game = self.config_manager.game
        tdf_path = self.config_manager.tdf_path
        time_ms = self.current_time_ms
        base_cmd = self.config_manager.get_lfdata_command()

        if sync or not self.async_render:
            self._execute_render(
                gen_id=gen_id,
                game=game,
                tdf_path=tdf_path,
                time_ms=time_ms,
                config=cfg_copy,
                player_name=norm_player,
                base_cmd=base_cmd,
            )
        else:
            thread = threading.Thread(
                target=self._execute_render,
                kwargs={
                    'gen_id': gen_id,
                    'game': game,
                    'tdf_path': tdf_path,
                    'time_ms': time_ms,
                    'config': cfg_copy,
                    'player_name': norm_player,
                    'base_cmd': base_cmd,
                },
                daemon=True,
            )
            thread.start()

    def _execute_render(
        self,
        gen_id: int,
        game: object | None,
        tdf_path: str | None,
        time_ms: int,
        config: dict[str, object],
        player_name: str | None,
        base_cmd: list[str],
    ) -> None:
        """Executes the render operation and delivers result back to the UI.

        Args:
            gen_id: Render generation sequence integer.
            game: Optional LFGame model instance.
            tdf_path: Optional path to the TDF file.
            time_ms: Timestamp in milliseconds to render.
            config: Video layout configuration dictionary.
            player_name: Optional focused player codename string.
            base_cmd: CLI executable prefix command list.
        """
        if gen_id != self._render_generation:
            return

        try:
            from lfdata.model.objects.game import LFGame

            lf_game = game if isinstance(game, LFGame) else None
            img = self.renderer.render_frame(
                game=lf_game,
                tdf_path=tdf_path,
                time_ms=time_ms,
                config=config,
                player_name=player_name,
                base_cmd=base_cmd,
                is_cancelled=lambda: gen_id != self._render_generation,
            )
            if img is None or gen_id != self._render_generation:
                return

            if self.async_render:
                self.after(
                    0,
                    lambda: self._on_render_success(img=img, gen_id=gen_id),
                )
            else:
                self._on_render_success(img=img, gen_id=gen_id)
        except Exception as e:
            if gen_id != self._render_generation:
                return
            err_msg = str(e)
            if self.async_render:
                self.after(
                    0,
                    lambda: self._on_render_error(
                        err_msg=err_msg, gen_id=gen_id
                    ),
                )
            else:
                self._on_render_error(err_msg=err_msg, gen_id=gen_id)

    def _on_render_success(self, img: Image.Image, gen_id: int) -> None:
        """Displays the newly rendered frame if the generation is still current.

        Args:
            img: The rendered PIL image.
            gen_id: The render generation sequence ID.
        """
        if gen_id != self._render_generation:
            return
        self.last_rendered_image = img
        self._show_image(img)

    def _on_render_error(self, err_msg: str, gen_id: int) -> None:
        """Displays an error message if the generation is still current.

        Args:
            err_msg: The error message string.
            gen_id: The render generation sequence ID.
        """
        if gen_id != self._render_generation:
            return
        self.lbl_image.config(text=f'Failed to render: {err_msg}')

    def _show_image(self, raw_img: Image.Image) -> None:
        """Resizes and displays the PIL image on the label.

        Args:
            raw_img: The PIL image object.
        """
        canvas_w = DEFAULT_PREVIEW_WIDTH
        canvas_h = DEFAULT_PREVIEW_HEIGHT
        if hasattr(self.img_frame, 'winfo_width'):
            w = self.img_frame.winfo_width()
            if w > 1:
                canvas_w = w
        if hasattr(self.img_frame, 'winfo_height'):
            h = self.img_frame.winfo_height()
            if h > 1:
                canvas_h = h

        img_w, img_h = raw_img.size

        ratio = min(canvas_w / img_w, canvas_h / img_h)
        new_w = max(1, int(img_w * ratio))
        new_h = max(1, int(img_h * ratio))

        resized = raw_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(resized)

        self.lbl_image.config(image=photo, text='')
        self.lbl_image.image = photo

    def _on_frame_configure(self, event: tk.Event) -> None:
        """Handles container resizing to upscale/downscale the preview image.

        Args:
            event: The configuration event.
        """
        if self.last_rendered_image:
            self._show_image(self.last_rendered_image)
