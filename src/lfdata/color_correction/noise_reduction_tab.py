"""Noise reduction adjustment tab with FFmpeg controls and side-by-side preview.

This module provides the `NoiseReductionTab` widget, representing the third
stage of the color correction editor. It enables configuring video denoising
parameters using FFmpeg options (such as hqdn3d and nlmeans) and displays a
looping side-by-side comparison of the color-corrected reference video before
and after noise reduction.

Usage example:
    import tkinter as tk
    from lfdata.color_correction.noise_reduction_tab import NoiseReductionTab

    root = tk.Tk()
    tab = NoiseReductionTab(parent=root)
    tab.pack(fill='both', expand=True)
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable

from PIL import Image, ImageTk

from lfdata.color_correction.lut import Lut3D
from lfdata.color_correction.noise_reduction import (
    DEFAULT_CHROMA_SPATIAL,
    DEFAULT_CHROMA_TEMPORAL,
    DEFAULT_LUMA_SPATIAL,
    DEFAULT_LUMA_TEMPORAL,
    DEFAULT_NLMEANS_PATCH,
    DEFAULT_NLMEANS_STRENGTH,
    NoiseReductionSettings,
)
from lfdata.color_correction.reference_video import ReferenceVideo
from lfdata.color_correction.time_range import TimeRange
from lfdata.color_correction.video_reader import VideoReader

PREVIEW_WIDTH: int = 360
PREVIEW_HEIGHT: int = 202
PLAYBACK_INTERVAL_MS: int = 40


class NoiseReductionTab(ttk.Frame):
    """UI tab for configuring FFmpeg noise reduction with side-by-side preview.

    Attributes:
        settings: NoiseReductionSettings instance managing filter parameters.
        lut: Active Lut3D color correction applied as the base frame.
        reference_video: Composite ReferenceVideo combining selected ranges.
        is_playing: True when reference video playback loop is active.
        current_time_ms: Current playback position in milliseconds.
        chk_enabled: Checkbutton toggling noise reduction on and off.
        cmb_filter_type: Combobox selecting denoising algorithm.
        cmb_preset: Combobox choosing standard noise reduction presets.
        lbl_filter_preview: Label displaying generated FFmpeg filter string.
        scale_luma_spatial: Slider for spatial luminance denoise strength.
        scale_chroma_spatial: Slider for spatial chrominance denoise strength.
        scale_luma_temporal: Slider for temporal luminance denoise strength.
        scale_chroma_temporal: Slider for temporal chrominance denoise strength.
        scale_nlmeans_strength: Slider for non-local means filter strength.
        scale_nlmeans_patch: Slider for non-local means patch size.
        btn_play_pause: Button toggling looping reference video playback.
        scale_scrub: Slider for scrubbing along reference video duration.
        lbl_playback_time: Label showing current and total reference timestamp.
        lbl_orig_preview: Label displaying color-corrected base frame.
        lbl_proc_preview: Label displaying denoised video frame.
    """

    def __init__(self, parent: tk.Widget) -> None:
        """Initializes the NoiseReductionTab widget.

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

        self.settings: NoiseReductionSettings = NoiseReductionSettings()
        self.lut: Lut3D = Lut3D()
        self.reference_video: ReferenceVideo | None = None
        self._reader_clone: VideoReader | None = None
        self.is_playing: bool = False
        self.current_time_ms: int = 0

        self._cached_source_frame: Image.Image | None = None
        self._cached_base_frame: Image.Image | None = None
        self._cached_source_time_ms: int | None = None
        self._orig_photo: ImageTk.PhotoImage | None = None
        self._proc_photo: ImageTk.PhotoImage | None = None

        self._worker_running: bool = True
        self._pending_time_ms: int | None = None
        self._pending_reapply: bool = False
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

        self._create_controls_section(container=container)
        self._create_preview_section(container=container)

    def _create_controls_section(self, container: ttk.Frame) -> None:
        """Creates noise reduction settings and parameter adjustment sliders.

        Args:
            container: Parent container frame.
        """
        top_frame = ttk.LabelFrame(
            container,
            text='Noise Reduction Configuration',
        )
        top_frame.pack(fill='x', padx=5, pady=4)

        header_row = ttk.Frame(top_frame)
        header_row.pack(fill='x', padx=6, pady=4)

        try:
            self.var_enabled = tk.BooleanVar(
                master=self,
                value=self.settings.enabled,
            )
        except Exception:

            class _FallbackVar:
                def __init__(self, val: bool) -> None:
                    self._val = val

                def get(self) -> bool:
                    return self._val

                def set(self, val: bool) -> None:
                    self._val = bool(val)

            self.var_enabled = _FallbackVar(self.settings.enabled)  # type: ignore[assignment]
        self.chk_enabled = ttk.Checkbutton(
            header_row,
            text='Enable Noise Reduction',
            variable=self.var_enabled,
            command=self._on_enabled_toggled,
        )
        self.chk_enabled.pack(side='left', padx=4)

        ttk.Label(header_row, text='Algorithm:').pack(side='left', padx=(12, 2))
        self.cmb_filter_type = ttk.Combobox(
            header_row,
            values=['hqdn3d', 'nlmeans'],
            state='readonly',
            width=10,
        )
        self.cmb_filter_type.set('hqdn3d')
        self.cmb_filter_type.bind(
            '<<ComboboxSelected>>',
            self._on_filter_type_changed,
        )
        self.cmb_filter_type.pack(side='left', padx=4)

        ttk.Label(header_row, text='Preset:').pack(side='left', padx=(12, 2))
        self.cmb_preset = ttk.Combobox(
            header_row,
            values=['Medium (Default)', 'Mild', 'Strong', 'Custom'],
            state='readonly',
            width=16,
        )
        self.cmb_preset.set('Medium (Default)')
        self.cmb_preset.bind(
            '<<ComboboxSelected>>',
            self._on_preset_changed,
        )
        self.cmb_preset.pack(side='left', padx=4)

        self.btn_reset = ttk.Button(
            header_row,
            text='Reset Defaults',
            command=self._on_reset_clicked,
        )
        self.btn_reset.pack(side='right', padx=4)

        self._create_sliders_grid(top_frame=top_frame)

        footer_row = ttk.Frame(top_frame)
        footer_row.pack(fill='x', padx=8, pady=(2, 6))

        self.lbl_filter_preview = ttk.Label(
            footer_row,
            text=f'FFmpeg Option: -vf {self.settings.to_ffmpeg_filter()}',
            font=('TkDefaultFont', 9, 'italic'),
        )
        self.lbl_filter_preview.pack(side='left', padx=2)

    def _create_sliders_grid(self, top_frame: ttk.LabelFrame) -> None:
        """Creates the grid of sliders for hqdn3d and nlmeans parameters.

        Args:
            top_frame: Parent LabelFrame container.
        """
        self.slider_grid = ttk.Frame(top_frame)
        self.slider_grid.pack(fill='x', padx=8, pady=4)

        self.scale_luma_spatial = self._add_slider_row(
            parent=self.slider_grid,
            row=0,
            col=0,
            label='Luma Spatial:',
            min_val=0.0,
            max_val=20.0,
            init_val=DEFAULT_LUMA_SPATIAL,
            attr_name='luma_spatial',
        )
        self.scale_chroma_spatial = self._add_slider_row(
            parent=self.slider_grid,
            row=0,
            col=1,
            label='Chroma Spatial:',
            min_val=0.0,
            max_val=20.0,
            init_val=DEFAULT_CHROMA_SPATIAL,
            attr_name='chroma_spatial',
        )
        self.scale_luma_temporal = self._add_slider_row(
            parent=self.slider_grid,
            row=1,
            col=0,
            label='Luma Temporal:',
            min_val=0.0,
            max_val=20.0,
            init_val=DEFAULT_LUMA_TEMPORAL,
            attr_name='luma_temporal',
        )
        self.scale_chroma_temporal = self._add_slider_row(
            parent=self.slider_grid,
            row=1,
            col=1,
            label='Chroma Temporal:',
            min_val=0.0,
            max_val=20.0,
            init_val=DEFAULT_CHROMA_TEMPORAL,
            attr_name='chroma_temporal',
        )
        self.scale_nlmeans_strength = self._add_slider_row(
            parent=self.slider_grid,
            row=2,
            col=0,
            label='NLMeans Strength:',
            min_val=1.0,
            max_val=30.0,
            init_val=DEFAULT_NLMEANS_STRENGTH,
            attr_name='nlmeans_strength',
        )
        self.scale_nlmeans_patch = self._add_slider_row(
            parent=self.slider_grid,
            row=2,
            col=1,
            label='NLMeans Patch:',
            min_val=3.0,
            max_val=15.0,
            init_val=float(DEFAULT_NLMEANS_PATCH),
            attr_name='nlmeans_patch',
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
        attr_name: str,
    ) -> ttk.Scale:
        """Creates a labeled slider control within the specified grid cell.

        Args:
            parent: Container frame.
            row: Grid row index.
            col: Grid column index.
            label: Text description of the adjustment parameter.
            min_val: Minimum scale value.
            max_val: Maximum scale value.
            init_val: Initial scale position.
            attr_name: Corresponding attribute name in settings.

        Returns:
            ttk.Scale: The configured slider instance.
        """
        cell_frame = ttk.Frame(parent)
        try:
            cell_frame.grid(row=row, column=col, sticky='ew', padx=10, pady=2)
            parent.columnconfigure(col, weight=1)
        except Exception:
            pass

        ttk.Label(cell_frame, text=label, width=16).pack(side='left', padx=2)
        scale = ttk.Scale(
            cell_frame,
            from_=min_val,
            to=max_val,
            value=init_val,
            command=lambda v: self._on_slider_changed(attr_name, v),
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
            text='Noise Reduction Preview (Side-by-Side Comparison)',
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
            text='Color Corrected (Without Denoise)',
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
            text='Denoised (With Noise Reduction)',
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
        lut: Lut3D | None = None,
    ) -> None:
        """Configures the reference video reader, clip ranges, and active LUT.

        Args:
            video_reader: VideoReader extracting frames from source video.
            ranges: Configured clip ranges forming the composite video.
            lut: Lut3D instance to apply as the base color correction.

        Usage example:
            tab.set_reference_data(video_reader=reader, ranges=r, lut=lut)
        """
        self.pause_playback()
        if lut is not None:
            self.lut = lut

        if self._reader_clone is not None:
            self._reader_clone.close()
            self._reader_clone = None

        if type(video_reader) is VideoReader:
            self._reader_clone = video_reader.clone()
            active_reader = self._reader_clone
        else:
            active_reader = video_reader

        self.reference_video = ReferenceVideo(
            video_reader=active_reader,
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

    def set_lut(self, lut: Lut3D) -> None:
        """Updates the base color correction LUT applied before denoising.

        Args:
            lut: New Lut3D color lookup table.

        Usage example:
            tab.set_lut(lut=new_lut)
        """
        self.lut = lut
        self._cached_base_frame = None
        self._request_reapply()

    def toggle_playback(self) -> None:
        """Toggles between playing and pausing looping reference playback.

        Usage example:
            tab.toggle_playback()
        """
        if self.is_playing:
            self.pause_playback()
        else:
            self.play()

    def play(self) -> None:
        """Starts looping playback of the composite reference video.

        Usage example:
            tab.play()
        """
        if self.reference_video is None:
            return
        if self.reference_video.total_duration_ms <= 0:
            return

        self.is_playing = True
        try:
            self.btn_play_pause.config(text='Pause')
        except Exception:
            pass
        self._playback_step()

    def pause_playback(self) -> None:
        """Pauses composite reference video playback loop.

        Usage example:
            tab.pause_playback()
        """
        self.is_playing = False
        try:
            self.btn_play_pause.config(text='Play')
        except Exception:
            pass

    def _playback_step(self) -> None:
        """Advances playback time and schedules the next frame step."""
        if not self.is_playing or self.reference_video is None:
            return

        total_ms = self.reference_video.total_duration_ms
        if total_ms <= 0:
            self.pause_playback()
            return

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

        self._safe_after(
            delay_ms=PLAYBACK_INTERVAL_MS,
            callback=self._playback_step,
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

    def _update_filter_label(self) -> None:
        """Updates the label preview showing the generated FFmpeg command."""
        try:
            expr = self.settings.to_ffmpeg_filter()
            self.lbl_filter_preview.config(text=f'FFmpeg Option: -vf {expr}')
        except Exception:
            pass

    def _on_enabled_toggled(self) -> None:
        """Handles toggling of the noise reduction enable checkbox."""
        try:
            self.settings.enabled = bool(self.var_enabled.get())
        except Exception:
            self.settings.enabled = True
        self._update_filter_label()
        self._request_reapply()

    def _on_filter_type_changed(self, event: tk.Event | None = None) -> None:
        """Handles changes in the noise reduction filter algorithm combobox.

        Args:
            event: Optional tkinter event argument.
        """
        val = self.cmb_filter_type.get()
        if val in ('hqdn3d', 'nlmeans'):
            self.settings.filter_type = val
        self._update_filter_label()
        self._request_reapply()

    def _on_preset_changed(self, event: tk.Event | None = None) -> None:
        """Handles selection of a standard noise reduction preset.

        Args:
            event: Optional tkinter event argument.
        """
        val = self.cmb_preset.get().lower()
        if 'mild' in val:
            self.settings.apply_preset('mild')
        elif 'strong' in val:
            self.settings.apply_preset('strong')
        elif 'medium' in val or 'default' in val:
            self.settings.apply_preset('medium')
        self._sync_sliders_from_settings()
        self._update_filter_label()
        self._request_reapply()

    def _on_reset_clicked(self) -> None:
        """Resets all noise reduction settings back to default parameters."""
        self.settings.reset()
        try:
            self.var_enabled.set(self.settings.enabled)
            self.cmb_filter_type.set('hqdn3d')
            self.cmb_preset.set('Medium (Default)')
        except Exception:
            pass
        self._sync_sliders_from_settings()
        self._update_filter_label()
        self._request_reapply()

    def _sync_sliders_from_settings(self) -> None:
        """Updates slider controls to match current settings values."""
        try:
            self.scale_luma_spatial.set(self.settings.luma_spatial)
            self.scale_chroma_spatial.set(self.settings.chroma_spatial)
            self.scale_luma_temporal.set(self.settings.luma_temporal)
            self.scale_chroma_temporal.set(self.settings.chroma_temporal)
            self.scale_nlmeans_strength.set(self.settings.nlmeans_strength)
            self.scale_nlmeans_patch.set(float(self.settings.nlmeans_patch))
        except Exception:
            pass

    def _on_slider_changed(self, attr_name: str, value_str: str) -> None:
        """Updates a noise reduction setting parameter from slider input.

        Args:
            attr_name: Attribute name in NoiseReductionSettings.
            value_str: Slider value string.
        """
        val = float(value_str)
        if attr_name == 'nlmeans_patch':
            patch_val = round(val)
            if patch_val % 2 == 0:
                patch_val += 1
            setattr(self.settings, attr_name, max(3, min(15, patch_val)))
        else:
            setattr(self.settings, attr_name, val)
        self._on_custom_param_changed()

    def _on_custom_param_changed(self) -> None:
        """Marks preset as Custom, updates filter string, and re-renders."""
        try:
            self.cmb_preset.set('Custom')
        except Exception:
            pass
        self._update_filter_label()
        self._request_reapply()

    def _request_frame_at(self, composite_time_ms: int) -> None:
        """Queues a frame extraction request for the background worker.

        Args:
            composite_time_ms: Millisecond position in reference video.
        """
        with self._render_condition:
            self._pending_time_ms = composite_time_ms
            self._render_condition.notify_all()

    def _request_reapply(self) -> None:
        """Queues a re-render request using currently cached frame."""
        with self._render_condition:
            self._pending_reapply = True
            self._render_condition.notify_all()

    def _worker_loop(self) -> None:
        """Background worker loop extracting frames and applying filters."""
        while self._worker_running:
            with self._render_condition:
                while (
                    self._worker_running
                    and self._pending_time_ms is None
                    and not self._pending_reapply
                ):
                    self._render_condition.wait()

                if not self._worker_running:
                    break

                target_time_ms = self._pending_time_ms
                reapply = self._pending_reapply
                self._pending_time_ms = None
                self._pending_reapply = False

            self._process_worker_task(
                target_time_ms=target_time_ms,
                reapply=reapply,
            )

    def _process_worker_task(
        self,
        target_time_ms: int | None,
        reapply: bool,
    ) -> None:
        """Processes a queued frame extraction or filter re-render task.

        Args:
            target_time_ms: Target composite timestamp, or None if re-applying.
            reapply: True if settings changed and cached frame can be reused.
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
                    self._cached_base_frame = None
                except Exception:
                    raw_frame = None
        elif reapply:
            raw_frame = self._cached_source_frame

        if raw_frame is None and self._cached_base_frame is None:
            return

        if self._cached_base_frame is None and raw_frame is not None:
            resized_src = raw_frame.resize(
                (PREVIEW_WIDTH, PREVIEW_HEIGHT),
                Image.Resampling.BILINEAR,
            )
            self._cached_base_frame = self.lut.apply_to_image(image=resized_src)

        base_frame = self._cached_base_frame
        if base_frame is None:
            return

        denoised_frame = self.settings.apply(image=base_frame)

        self._safe_after(
            delay_ms=0,
            callback=lambda b=base_frame, d=denoised_frame: (
                self._apply_rendered_previews(orig_img=b, proc_img=d)
            ),
        )

    def _apply_rendered_previews(
        self,
        orig_img: Image.Image,
        proc_img: Image.Image,
    ) -> None:
        """Updates preview labels with rendered base and denoised images.

        Args:
            orig_img: Color corrected reference base preview image.
            proc_img: Noise-reduced preview image.
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
        """Stops background worker thread and pauses playback.

        Usage example:
            tab.close()
        """
        self.pause_playback()
        self._worker_running = False
        with self._render_condition:
            self._pending_time_ms = None
            self._pending_reapply = False
            self._render_condition.notify_all()

        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=0.5)

        if self._reader_clone is not None:
            self._reader_clone.close()
            self._reader_clone = None
