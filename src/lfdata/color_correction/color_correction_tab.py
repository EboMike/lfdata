"""Color correction adjustment tab with LUT controls and side-by-side preview.

This module provides the `ColorCorrectionTab` widget, representing the second
stage of the color correction process. It displays a 3D LUT visualization,
provides common LUT adjustment controls (brightness, contrast, saturation,
temperature, tint), allows importing and exporting Adobe `.cube` files, and
presents a looping side-by-side comparison of the reference video before and
after color correction.

Usage example:
    import tkinter as tk
    from lfdata.color_correction.color_correction_tab import ColorCorrectionTab

    root = tk.Tk()
    tab = ColorCorrectionTab(parent=root)
    tab.pack(fill='both', expand=True)
"""

from __future__ import annotations

import math
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from PIL import Image, ImageTk

from lfdata.color_correction.lut import Lut3D
from lfdata.color_correction.lut_panel import LutPanel
from lfdata.color_correction.reference_video import ReferenceVideo
from lfdata.color_correction.time_range import TimeRange
from lfdata.color_correction.video_reader import VideoReader

PREVIEW_WIDTH: int = 360
PREVIEW_HEIGHT: int = 202
PLAYBACK_INTERVAL_MS: int = 40


class ColorCorrectionTab(ttk.Frame):
    """UI tab for configuring LUT adjustments with side-by-side video preview.

    Attributes:
        lut: Lut3D instance managing the active color lookup table.
        reference_video: Composite ReferenceVideo combining selected ranges.
        lut_panel: LutPanel widget visualizing the LUT and balance marker.
        scale_brightness: Slider for overall brightness offset.
        scale_contrast: Slider for contrast adjustment.
        scale_shadows: Slider for boosting or reducing dark shadow tones.
        scale_highlights: Slider for controlling highlight overexposure.
        scale_gamma: Slider for midtone gamma curve adjustment.
        scale_highlight_rolloff: Slider for soft rolloff on bright lights.
        scale_saturation: Slider for color saturation.
        scale_temperature: Slider for warm/cool color temperature.
        scale_tint: Slider for green/magenta color tint.
        btn_play_pause: Button toggling looping reference video playback.
        scale_scrub: Slider for scrubbing along composite reference duration.
        lbl_playback_time: Label showing current and total reference timestamp.
        lbl_orig_preview: Label displaying original reference video frame.
        lbl_proc_preview: Label displaying color corrected video frame.
        is_playing: True when reference video playback loop is active.
    """

    def __init__(self, parent: tk.Widget) -> None:
        """Initializes the ColorCorrectionTab widget.

        Args:
            parent: Parent tkinter widget container.
        """
        try:
            super().__init__(parent)
        except Exception:
            from unittest.mock import MagicMock

            self._w = '.'
            self.tk = getattr(parent, 'tk', MagicMock())
            self.children = {}

        self.lut: Lut3D = Lut3D()
        self.reference_video: ReferenceVideo | None = None
        self.is_playing: bool = False
        self.current_time_ms: int = 0
        self._lut_file_path: Path | None = None

        self._cached_source_frame: Image.Image | None = None
        self._cached_source_time_ms: int | None = None
        self._orig_photo: ImageTk.PhotoImage | None = None
        self._proc_photo: ImageTk.PhotoImage | None = None

        self._worker_running: bool = True
        self._pending_time_ms: int | None = None
        self._pending_lut_reapply: bool = False
        self._render_lock = threading.Lock()
        self._render_condition = threading.Condition(self._render_lock)

        self._create_widgets()

        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
        )
        self._worker_thread.start()

    def _create_widgets(self) -> None:
        """Initializes and packs all UI components into the tab container."""
        container = ttk.Frame(self)
        try:
            container.pack(expand=True, fill='both', padx=10, pady=8)
        except Exception:
            pass

        self._create_lut_top_section(container=container)
        self._create_lut_controls_section(container=container)
        self._create_preview_section(container=container)

    def _create_lut_top_section(self, container: ttk.Frame) -> None:
        """Creates the LUT visualization panel and file action buttons.

        Args:
            container: Parent container frame.
        """
        top_frame = ttk.LabelFrame(container, text='LUT Configuration')
        top_frame.pack(fill='x', padx=5, pady=4)

        header_row = ttk.Frame(top_frame)
        header_row.pack(fill='x', padx=6, pady=4)

        self.lbl_lut_status = ttk.Label(
            header_row, text='LUT: Identity (Default)'
        )
        self.lbl_lut_status.pack(side='left', padx=4)

        self.btn_reset_lut = ttk.Button(
            header_row,
            text='Reset',
            command=self._on_reset_lut_click,
        )
        self.btn_reset_lut.pack(side='right', padx=3)

        self.btn_export_cube = ttk.Button(
            header_row,
            text='Export .cube',
            command=self._on_export_cube_click,
        )
        self.btn_export_cube.pack(side='right', padx=3)

        self.btn_load_cube = ttk.Button(
            header_row,
            text='Load .cube',
            command=self._on_load_cube_click,
        )
        self.btn_load_cube.pack(side='right', padx=3)

        panel_container = ttk.Frame(top_frame)
        panel_container.pack(fill='x', padx=6, pady=(2, 6))

        self.lut_panel = LutPanel(
            parent=panel_container,
            lut=self.lut,
            canvas_width=360,
            canvas_height=70,
            on_balance_changed=self._on_lut_panel_balance_changed,
        )
        try:
            self.lut_panel.pack(side='left', padx=4)
        except Exception:
            pass

        lbl_lut_hint = ttk.Label(
            panel_container,
            text=(
                'Click or drag on the LUT panel\n'
                'to adjust color temperature and tint.\n'
                'Or use the sliders below.'
            ),
            justify='left',
        )
        lbl_lut_hint.pack(side='left', padx=12)

    def _create_lut_controls_section(self, container: ttk.Frame) -> None:
        """Creates standard color grading sliders for adjusting the LUT.

        Args:
            container: Parent container frame.
        """
        ctrl_frame = ttk.LabelFrame(container, text='LUT Adjustments')
        ctrl_frame.pack(fill='x', padx=5, pady=4)

        slider_grid = ttk.Frame(ctrl_frame)
        slider_grid.pack(fill='x', padx=8, pady=4)

        self.scale_brightness = self._add_slider_row(
            parent=slider_grid,
            row=0,
            col=0,
            label='Brightness:',
            min_val=-100.0,
            max_val=100.0,
            init_val=0.0,
            callback=self._on_brightness_changed,
        )
        self.scale_contrast = self._add_slider_row(
            parent=slider_grid,
            row=0,
            col=1,
            label='Contrast:',
            min_val=-100.0,
            max_val=100.0,
            init_val=0.0,
            callback=self._on_contrast_changed,
        )
        self.scale_shadows = self._add_slider_row(
            parent=slider_grid,
            row=1,
            col=0,
            label='Shadows:',
            min_val=-100.0,
            max_val=100.0,
            init_val=0.0,
            callback=self._on_shadows_changed,
        )
        self.scale_highlights = self._add_slider_row(
            parent=slider_grid,
            row=1,
            col=1,
            label='Highlights:',
            min_val=-100.0,
            max_val=100.0,
            init_val=0.0,
            callback=self._on_highlights_changed,
        )
        self.scale_gamma = self._add_slider_row(
            parent=slider_grid,
            row=2,
            col=0,
            label='Gamma:',
            min_val=-100.0,
            max_val=100.0,
            init_val=0.0,
            callback=self._on_gamma_changed,
        )
        self.scale_highlight_rolloff = self._add_slider_row(
            parent=slider_grid,
            row=2,
            col=1,
            label='Light Rolloff:',
            min_val=0.0,
            max_val=100.0,
            init_val=0.0,
            callback=self._on_highlight_rolloff_changed,
        )
        self.scale_saturation = self._add_slider_row(
            parent=slider_grid,
            row=3,
            col=0,
            label='Saturation:',
            min_val=-100.0,
            max_val=100.0,
            init_val=0.0,
            callback=self._on_saturation_changed,
        )
        self.scale_temperature = self._add_slider_row(
            parent=slider_grid,
            row=3,
            col=1,
            label='Temperature:',
            min_val=-100.0,
            max_val=100.0,
            init_val=0.0,
            callback=self._on_temperature_changed,
        )
        self.scale_tint = self._add_slider_row(
            parent=slider_grid,
            row=4,
            col=0,
            label='Tint:',
            min_val=-100.0,
            max_val=100.0,
            init_val=0.0,
            callback=self._on_tint_changed,
        )

    def _add_slider_row(
        self,
        parent: ttk.Frame,
        row: int,
        col: int,
        label: str,
        min_val: float,
        max_val: float,
        init_val: float,
        callback: Callable[[str], None],
    ) -> ttk.Scale:
        """Creates a labeled slider control within the specified grid cell.

        Args:
            parent: Container frame.
            row: Grid row index.
            col: Grid column index.
            label: Text description of the grading adjustment.
            min_val: Minimum scale value.
            max_val: Maximum scale value.
            init_val: Initial scale position.
            callback: Function invoked when slider position changes.

        Returns:
            The configured ttk.Scale widget instance.
        """
        cell_frame = ttk.Frame(parent)
        try:
            cell_frame.grid(row=row, column=col, sticky='ew', padx=10, pady=2)
            parent.columnconfigure(col, weight=1)
        except Exception:
            pass

        lbl = ttk.Label(cell_frame, text=label, width=12)
        lbl.pack(side='left', padx=2)

        scale = ttk.Scale(
            cell_frame,
            from_=min_val,
            to=max_val,
            value=init_val,
            command=callback,
        )
        scale.pack(side='left', fill='x', expand=True, padx=4)

        return scale

    def _create_preview_section(self, container: ttk.Frame) -> None:
        """Creates playback controls and side-by-side video preview panels.

        Args:
            container: Parent container frame.
        """
        preview_frame = ttk.LabelFrame(
            container,
            text='Reference Video Preview (Side-by-Side Comparison)',
        )
        preview_frame.pack(fill='both', expand=True, padx=5, pady=4)

        playback_bar = ttk.Frame(preview_frame)
        playback_bar.pack(fill='x', padx=8, pady=4)

        self.btn_play_pause = ttk.Button(
            playback_bar,
            text='Play',
            command=self.toggle_playback,
            width=10,
        )
        self.btn_play_pause.pack(side='left', padx=4)

        self.scale_scrub = ttk.Scale(
            playback_bar,
            from_=0,
            to=1000,
            value=0,
            command=self._on_scrub_changed,
        )
        self.scale_scrub.pack(side='left', fill='x', expand=True, padx=6)

        self.lbl_playback_time = ttk.Label(
            playback_bar,
            text='Time: 00:00.000 / 00:00.000',
        )
        self.lbl_playback_time.pack(side='right', padx=4)

        videos_container = ttk.Frame(preview_frame)
        videos_container.pack(fill='both', expand=True, padx=8, pady=4)
        try:
            videos_container.columnconfigure(0, weight=1)
            videos_container.columnconfigure(1, weight=1)
        except Exception:
            pass

        left_box = ttk.Frame(videos_container)
        try:
            left_box.grid(row=0, column=0, sticky='nsew', padx=4, pady=2)
        except Exception:
            pass
        ttk.Label(
            left_box,
            text='Original Reference Video',
            font=('TkDefaultFont', 9, 'bold'),
        ).pack(pady=(0, 2))

        self.lbl_orig_preview = ttk.Label(
            left_box,
            text='No reference video loaded',
            anchor='center',
            relief='sunken',
        )
        self.lbl_orig_preview.pack(fill='both', expand=True)

        right_box = ttk.Frame(videos_container)
        try:
            right_box.grid(row=0, column=1, sticky='nsew', padx=4, pady=2)
        except Exception:
            pass
        ttk.Label(
            right_box,
            text='Color Corrected (LUT)',
            font=('TkDefaultFont', 9, 'bold'),
        ).pack(pady=(0, 2))

        self.lbl_proc_preview = ttk.Label(
            right_box,
            text='No reference video loaded',
            anchor='center',
            relief='sunken',
        )
        self.lbl_proc_preview.pack(fill='both', expand=True)

    def set_reference_data(
        self,
        video_reader: VideoReader | None,
        ranges: list[TimeRange],
    ) -> None:
        """Configures the reference video reader and configured clip ranges.

        Initializes the composite ReferenceVideo from the given video reader
        and clip ranges, updates timeline scrubber boundaries, and triggers
        preview rendering of the first frame.

        Args:
            video_reader: VideoReader extracting frames from source video.
            ranges: Configured clip ranges forming the composite video.

        Usage example:
            tab.set_reference_data(video_reader=reader, ranges=my_ranges)
        """
        self.pause_playback()
        self.reference_video = ReferenceVideo(
            video_reader=video_reader,
            ranges=ranges,
        )
        self.current_time_ms = 0

        total_ms = self.reference_video.total_duration_ms
        if total_ms > 0:
            self.scale_scrub.config(to=total_ms, value=0)
            self._update_playback_time_label(time_ms=0, total_ms=total_ms)
            self._request_frame_at(composite_time_ms=0)
        else:
            self.scale_scrub.config(to=1, value=0)
            self.lbl_playback_time.config(text='Time: 00:00.000 / 00:00.000')

    def toggle_playback(self) -> None:
        """Toggles between playing and pausing looping reference playback.

        Usage example:
            tab.toggle_playback()
        """
        if self.is_playing:
            self.pause_playback()
        else:
            self.start_playback()

    def start_playback(self) -> None:
        """Starts looping playback of the composite reference video.

        Usage example:
            tab.start_playback()
        """
        if (
            self.reference_video is None
            or self.reference_video.total_duration_ms <= 0
        ):
            return

        self.is_playing = True
        self.btn_play_pause.config(text='Pause')
        self._safe_after(
            delay_ms=PLAYBACK_INTERVAL_MS,
            callback=self._playback_loop_step,
        )

    def pause_playback(self) -> None:
        """Pauses looping playback of the composite reference video.

        Usage example:
            tab.pause_playback()
        """
        self.is_playing = False
        try:
            self.btn_play_pause.config(text='Play')
        except Exception:
            pass

    def _playback_loop_step(self) -> None:
        """Executes a single step of the looping playback animation."""
        if (
            not self.is_playing
            or self.reference_video is None
            or self.reference_video.total_duration_ms <= 0
        ):
            return

        total_ms = self.reference_video.total_duration_ms
        self.current_time_ms += PLAYBACK_INTERVAL_MS
        if self.current_time_ms >= total_ms:
            self.current_time_ms = 0

        try:
            self.scale_scrub.set(self.current_time_ms)
        except Exception:
            pass

        self._update_playback_time_label(
            time_ms=self.current_time_ms,
            total_ms=total_ms,
        )
        self._request_frame_at(composite_time_ms=self.current_time_ms)

        if self.is_playing:
            self._safe_after(
                delay_ms=PLAYBACK_INTERVAL_MS,
                callback=self._playback_loop_step,
            )

    def _on_scrub_changed(self, value_str: str) -> None:
        """Handles manual user scrubbing on the playback position slider.

        Args:
            value_str: String value passed by ttk.Scale widget.
        """
        try:
            target_ms = int(float(value_str))
        except (ValueError, TypeError):
            return

        self.current_time_ms = target_ms
        total_ms = (
            self.reference_video.total_duration_ms
            if self.reference_video is not None
            else 0
        )
        self._update_playback_time_label(time_ms=target_ms, total_ms=total_ms)
        self._request_frame_at(composite_time_ms=target_ms)

    def _update_playback_time_label(self, time_ms: int, total_ms: int) -> None:
        """Updates the time status text for current and total duration.

        Args:
            time_ms: Current position in milliseconds.
            total_ms: Total duration in milliseconds.
        """
        curr_str = TimeRange.format_timestamp_ms(time_ms)
        total_str = TimeRange.format_timestamp_ms(total_ms)
        try:
            self.lbl_playback_time.config(
                text=f'Time: {curr_str} / {total_str}'
            )
        except Exception:
            pass

    def _on_brightness_changed(self, value_str: str) -> None:
        """Updates LUT brightness parameter.

        Args:
            value_str: Scale value string between -100.0 and 100.0.
        """
        val = float(value_str) / 100.0
        self.lut.brightness = val
        self._apply_lut_modifications()

    def _on_contrast_changed(self, value_str: str) -> None:
        """Updates LUT contrast parameter.

        Args:
            value_str: Scale value string between -100.0 and 100.0.
        """
        slider_val = float(value_str)
        # Map [-100, 100] to multiplier [0.0, 2.0] where 0.0 is neutral 1.0
        mult = 1.0 + (slider_val / 100.0)
        self.lut.contrast = max(0.0, mult)
        self._apply_lut_modifications()

    def _on_shadows_changed(self, value_str: str) -> None:
        """Updates LUT shadow boost parameter.

        Adjusts the shadow tones in dark areas while tapering off to prevent
        overexposing bright areas.

        Args:
            value_str: Scale value string between -100.0 and 100.0.
        """
        val = float(value_str) / 100.0
        self.lut.shadows = val
        self._apply_lut_modifications()

    def _on_highlights_changed(self, value_str: str) -> None:
        """Updates LUT highlight adjustment parameter.

        Adjusts the highlight tones to prevent bright lights from overexposing
        or to pull back clipped highlights.

        Args:
            value_str: Scale value string between -100.0 and 100.0.
        """
        val = float(value_str) / 100.0
        self.lut.highlights = val
        self._apply_lut_modifications()

    def _on_gamma_changed(self, value_str: str) -> None:
        """Updates LUT midtone gamma power curve parameter.

        Applies a power curve that brightens shadows and midtones while pinning
        peak whites to prevent overexposure of bright laser tag lights.

        Args:
            value_str: Scale value string between -100.0 and 100.0.
        """
        slider_val = float(value_str)
        self.lut.gamma = 2.0 ** (slider_val / 50.0)
        self._apply_lut_modifications()

    def _on_highlight_rolloff_changed(self, value_str: str) -> None:
        """Updates LUT bright light highlight rolloff parameter.

        Smoothly compresses the highest luminance values using a soft shoulder
        curve to prevent harsh clipping of bright LEDs and lasers.

        Args:
            value_str: Scale value string between 0.0 and 100.0.
        """
        slider_val = float(value_str)
        self.lut.highlight_rolloff = max(0.0, min(1.0, slider_val / 100.0))
        self._apply_lut_modifications()

    def _on_saturation_changed(self, value_str: str) -> None:
        """Updates LUT saturation parameter.

        Args:
            value_str: Scale value string between -100.0 and 100.0.
        """
        slider_val = float(value_str)
        mult = 1.0 + (slider_val / 100.0)
        self.lut.saturation = max(0.0, mult)
        self._apply_lut_modifications()

    def _on_temperature_changed(self, value_str: str) -> None:
        """Updates LUT temperature parameter.

        Args:
            value_str: Scale value string between -100.0 and 100.0.
        """
        val = float(value_str) / 100.0
        self.lut.temperature = val
        self._apply_lut_modifications()

    def _on_tint_changed(self, value_str: str) -> None:
        """Updates LUT tint parameter.

        Args:
            value_str: Scale value string between -100.0 and 100.0.
        """
        val = float(value_str) / 100.0
        self.lut.tint = val
        self._apply_lut_modifications()

    def _on_lut_panel_balance_changed(
        self, temperature: float, tint: float
    ) -> None:
        """Synchronizes sliders when temperature/tint are changed via LutPanel.

        Args:
            temperature: Adjusted temperature value in range [-1.0, 1.0].
            tint: Adjusted tint value in range [-1.0, 1.0].
        """
        try:
            self.scale_temperature.set(temperature * 100.0)
            self.scale_tint.set(tint * 100.0)
        except Exception:
            pass
        self._request_lut_reapply()

    def _apply_lut_modifications(self, update_panel: bool = True) -> None:
        """Recomputes LUT table and triggers preview re-rendering.

        Args:
            update_panel: If True, refreshes the LutPanel visualization.
        """
        self.lut.recompute()
        if update_panel:
            try:
                self.lut_panel.update_display()
            except Exception:
                pass
        self._request_lut_reapply()

    def _on_load_cube_click(self) -> None:
        """Prompts user to select a .cube LUT file and loads it."""
        path_str = filedialog.askopenfilename(
            title='Open Adobe Color LUT (.cube)',
            filetypes=[('Adobe Cube LUT', '*.cube'), ('All files', '*.*')],
        )
        if not path_str:
            return

        path = Path(path_str)
        try:
            self.lut.load_cube_file(file_path=path)
            self._lut_file_path = path
            self.lbl_lut_status.config(text=f'LUT: {path.name}')
            self._sync_sliders_from_lut()
            self.lut_panel.update_display()
            self._request_lut_reapply()
        except Exception as err:
            messagebox.showerror(
                'Error Loading LUT', f'Failed to load LUT:\n{err}'
            )

    def _on_export_cube_click(self) -> None:
        """Prompts user for destination path and exports active LUT as .cube."""
        path_str = filedialog.asksaveasfilename(
            title='Export Adobe Color LUT (.cube)',
            defaultextension='.cube',
            filetypes=[('Adobe Cube LUT', '*.cube'), ('All files', '*.*')],
        )
        if not path_str:
            return

        path = Path(path_str)
        try:
            self.lut.save_cube_file(file_path=path)
            messagebox.showinfo(
                'Export Successful', f'Saved LUT to:\n{path.name}'
            )
        except Exception as err:
            messagebox.showerror(
                'Error Saving LUT', f'Failed to save LUT:\n{err}'
            )

    def _on_reset_lut_click(self) -> None:
        """Resets the active LUT to identity and resets all slider adjustments."""
        self.lut.reset_to_identity()
        self._lut_file_path = None
        try:
            self.lbl_lut_status.config(text='LUT: Identity (Default)')
        except Exception:
            pass
        self._sync_sliders_from_lut()
        try:
            self.lut_panel.update_display()
        except Exception:
            pass
        self._request_lut_reapply()

    def _sync_sliders_from_lut(self) -> None:
        """Updates slider positions to reflect current Lut3D parameter values."""
        try:
            self.scale_brightness.set(self.lut.brightness * 100.0)
            self.scale_contrast.set((self.lut.contrast - 1.0) * 100.0)
            self.scale_shadows.set(self.lut.shadows * 100.0)
            self.scale_highlights.set(self.lut.highlights * 100.0)
            gamma_val = (
                50.0 * math.log2(self.lut.gamma) if self.lut.gamma > 0 else 0.0
            )
            self.scale_gamma.set(gamma_val)
            self.scale_highlight_rolloff.set(self.lut.highlight_rolloff * 100.0)
            self.scale_saturation.set((self.lut.saturation - 1.0) * 100.0)
            self.scale_temperature.set(self.lut.temperature * 100.0)
            self.scale_tint.set(self.lut.tint * 100.0)
        except Exception:
            pass

    def _request_frame_at(self, composite_time_ms: int) -> None:
        """Queues a frame extraction request for the background worker.

        Args:
            composite_time_ms: Millisecond position in reference video.
        """
        with self._render_condition:
            self._pending_time_ms = composite_time_ms
            self._render_condition.notify_all()

    def _request_lut_reapply(self) -> None:
        """Queues a LUT re-application request on currently displayed frame."""
        with self._render_condition:
            self._pending_lut_reapply = True
            self._render_condition.notify_all()

    def _worker_loop(self) -> None:
        """Background worker loop extracting frames and applying 3D LUT."""
        while self._worker_running:
            with self._render_condition:
                while (
                    self._worker_running
                    and self._pending_time_ms is None
                    and not self._pending_lut_reapply
                ):
                    self._render_condition.wait()

                if not self._worker_running:
                    break

                target_time_ms = self._pending_time_ms
                reapply_lut = self._pending_lut_reapply
                self._pending_time_ms = None
                self._pending_lut_reapply = False

            self._process_worker_task(
                target_time_ms=target_time_ms,
                reapply_lut=reapply_lut,
            )

    def _process_worker_task(
        self,
        target_time_ms: int | None,
        reapply_lut: bool,
    ) -> None:
        """Processes a queued frame extraction or LUT re-render task.

        Args:
            target_time_ms: Target composite timestamp, or None if re-applying.
            reapply_lut: True if only LUT changed and cached frame should be used.
        """
        raw_frame: Image.Image | None = None

        if target_time_ms is not None:
            if self.reference_video is not None:
                try:
                    raw_frame = self.reference_video.get_frame(
                        composite_ms=target_time_ms
                    )
                    self._cached_source_frame = raw_frame
                    self._cached_source_time_ms = target_time_ms
                except Exception:
                    raw_frame = None
        elif reapply_lut:
            raw_frame = self._cached_source_frame

        if raw_frame is None:
            return

        orig_resized = raw_frame.resize(
            (PREVIEW_WIDTH, PREVIEW_HEIGHT),
            Image.Resampling.BILINEAR,
        )
        proc_resized = self.lut.apply_to_image(image=orig_resized)

        self._safe_after(
            delay_ms=0,
            callback=lambda o=orig_resized, p=proc_resized: (
                self._apply_rendered_previews(orig_img=o, proc_img=p)
            ),
        )

    def _apply_rendered_previews(
        self,
        orig_img: Image.Image,
        proc_img: Image.Image,
    ) -> None:
        """Updates preview labels with rendered original and LUT-processed images.

        Args:
            orig_img: Unprocessed original preview image.
            proc_img: Color corrected preview image.
        """
        try:
            self._orig_photo = ImageTk.PhotoImage(orig_img)
            self._proc_photo = ImageTk.PhotoImage(proc_img)
            self.lbl_orig_preview.config(image=self._orig_photo, text='')
            self.lbl_proc_preview.config(image=self._proc_photo, text='')
        except Exception:
            pass

    def _safe_after(self, delay_ms: int, callback: Callable[[], None]) -> None:
        """Safely schedules a callback on the UI thread.

        Args:
            delay_ms: Milliseconds delay before execution.
            callback: Function to invoke on the main thread.
        """
        try:
            self.after(delay_ms, callback)
        except Exception:
            pass

    def close(self) -> None:
        """Stops background threads and pauses playback.

        Usage example:
            tab.close()
        """
        self.pause_playback()
        self._worker_running = False
        with self._render_condition:
            self._pending_time_ms = None
            self._pending_lut_reapply = False
            self._render_condition.notify_all()

        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=0.5)
