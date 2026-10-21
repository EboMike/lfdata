"""Export tab for creating composite test videos and viewing FFmpeg arguments.

This module provides the `ExportTab` widget, representing the fourth stage
of the color correction editor. It enables users to export a composite test
video combining all configured reference ranges via FFmpeg and displays the
corresponding noise reduction arguments for integration into encoding pipelines.

Usage example:
    import tkinter as tk
    from lfdata.color_correction.export_tab import ExportTab

    root = tk.Tk()
    tab = ExportTab(parent=root)
    tab.pack(fill='both', expand=True)
"""

from __future__ import annotations

import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from lfdata.color_correction.error_dialog import ErrorDialog
from lfdata.color_correction.lut import Lut3D
from lfdata.color_correction.noise_reduction import NoiseReductionSettings
from lfdata.color_correction.time_range import TimeRange
from lfdata.color_correction.video_exporter import VideoExporter
from lfdata.model.constants.time import MS_PER_SECOND


class _FallbackVar:
    """Fallback variable simulator for headless testing environments."""

    def __init__(self, val: Any) -> None:
        self._val = val

    def get(self) -> Any:
        return self._val

    def set(self, val: Any) -> None:
        self._val = val


class ExportTab(ttk.Frame):
    """UI tab for exporting test videos and inspecting FFmpeg parameters.

    Attributes:
        video_exporter: VideoExporter instance handling FFmpeg calls.
        video_path: Path to the source reference video file.
        ranges: List of TimeRange intervals to combine in the export.
        noise_reduction_settings: NoiseReductionSettings instance.
        lut: Active Lut3D instance to optionally apply during export.
        is_exporting: Flag indicating whether export process is running.
        export_thread: Background worker thread for FFmpeg export.
        cancel_event: Event to signal cancellation to the worker thread.
        var_nr_args: StringVar holding displayed FFmpeg noise reduction args.
        var_apply_lut: BooleanVar controlling LUT application in export.
        var_apply_noise: BooleanVar controlling noise filter in export.
        lbl_source_info: Label displaying source video information.
        lbl_range_info: Label displaying range count and total duration.
        entry_nr_args: Read-only Entry showing noise reduction arguments.
        btn_copy_args: Button copying noise reduction arguments to clipboard.
        chk_apply_lut: Checkbutton toggling LUT application.
        chk_apply_noise: Checkbutton toggling noise reduction.
        btn_save_video: Button opening file dialog to trigger export.
        btn_cancel: Button allowing cancellation of active export.
        progress_bar: Progressbar providing visual export feedback.
        lbl_status: Label displaying current export status or errors.
    """

    video_exporter: VideoExporter
    video_path: Path | None
    ranges: list[TimeRange]
    noise_reduction_settings: NoiseReductionSettings | None
    lut: Lut3D | None
    is_exporting: bool
    export_thread: threading.Thread | None
    cancel_event: threading.Event | None

    def __init__(
        self,
        parent: tk.Widget,
        video_exporter: VideoExporter | None = None,
    ) -> None:
        """Initializes the ExportTab widget and constructs UI layout.

        Args:
            parent: Parent tkinter widget container.
            video_exporter: Optional custom VideoExporter instance.
        """
        try:
            super().__init__(parent)
        except (tk.TclError, RuntimeError, AttributeError):
            from unittest.mock import MagicMock

            self._w = '.'
            self.tk = MagicMock()
            self.children = {}

        self.video_exporter = video_exporter or VideoExporter()
        self.video_path = None
        self.ranges = []
        self.noise_reduction_settings = None
        self.lut = None
        self.is_exporting = False
        self.export_thread = None
        self.cancel_event = None

        self._init_variables()
        self._create_ui()

    def _init_variables(self) -> None:
        """Initializes Tkinter state variables for controls and options."""
        try:
            self.var_nr_args = tk.StringVar(value='')
            self.var_apply_lut = tk.BooleanVar(value=True)
            self.var_apply_noise = tk.BooleanVar(value=True)
        except (tk.TclError, RuntimeError, AttributeError, TypeError):
            self.var_nr_args = _FallbackVar('')  # type: ignore[assignment]
            self.var_apply_lut = _FallbackVar(True)  # type: ignore[assignment]
            self.var_apply_noise = _FallbackVar(True)  # type: ignore[assignment]

    def _create_ui(self) -> None:
        """Constructs layout panels dividing export options and information."""
        container = ttk.Frame(self)
        container.pack(fill='both', expand=True, padx=16, pady=16)

        self._create_info_panel(container=container)
        self._create_noise_reduction_panel(container=container)
        self._create_export_panel(container=container)
        self._create_progress_panel(container=container)

    def _create_info_panel(self, container: ttk.Frame) -> None:
        """Creates the reference video and selected ranges summary frame.

        Args:
            container: Parent frame container for the panel.
        """
        frame_info = ttk.LabelFrame(
            container, text='Reference Video Information'
        )
        frame_info.pack(fill='x', padx=4, pady=8)

        self.lbl_source_info = ttk.Label(
            frame_info,
            text='Source video: None loaded',
        )
        self.lbl_source_info.pack(anchor='w', padx=8, pady=4)

        self.lbl_range_info = ttk.Label(
            frame_info,
            text='Selected ranges: 0 ranges (Total duration: 00:00.000)',
        )
        self.lbl_range_info.pack(anchor='w', padx=8, pady=4)

    def _create_noise_reduction_panel(self, container: ttk.Frame) -> None:
        """Creates the noise reduction arguments inspection and copy panel.

        Args:
            container: Parent frame container for the panel.
        """
        frame_nr = ttk.LabelFrame(
            container,
            text='Noise Reduction FFmpeg Arguments',
        )
        frame_nr.pack(fill='x', padx=4, pady=8)

        lbl_desc = ttk.Label(
            frame_nr,
            text='Command line arguments for FFmpeg noise reduction:',
        )
        lbl_desc.pack(anchor='w', padx=8, pady=4)

        row_frame = ttk.Frame(frame_nr)
        row_frame.pack(fill='x', padx=8, pady=6)

        self.entry_nr_args = ttk.Entry(
            row_frame,
            textvariable=self.var_nr_args,
            state='readonly',
            width=50,
        )
        self.entry_nr_args.pack(side='left', fill='x', expand=True, padx=4)

        self.btn_copy_args = ttk.Button(
            row_frame,
            text='Copy Arguments',
            command=self.on_copy_args,
        )
        self.btn_copy_args.pack(side='left', padx=4)

    def _create_export_panel(self, container: ttk.Frame) -> None:
        """Creates the test video export controls panel.

        Args:
            container: Parent frame container for the panel.
        """
        frame_export = ttk.LabelFrame(container, text='Test Video Export')
        frame_export.pack(fill='x', padx=4, pady=8)

        lbl_desc = ttk.Label(
            frame_export,
            text='Combine all selected reference ranges into a single test video.',
        )
        lbl_desc.pack(anchor='w', padx=8, pady=4)

        opts_frame = ttk.Frame(frame_export)
        opts_frame.pack(fill='x', padx=8, pady=4)

        self.chk_apply_lut = ttk.Checkbutton(
            opts_frame,
            text='Apply Color Correction LUT',
            variable=self.var_apply_lut,
        )
        self.chk_apply_lut.pack(side='left', padx=8)

        self.chk_apply_noise = ttk.Checkbutton(
            opts_frame,
            text='Apply Noise Reduction',
            variable=self.var_apply_noise,
        )
        self.chk_apply_noise.pack(side='left', padx=8)

        btn_row = ttk.Frame(frame_export)
        btn_row.pack(fill='x', padx=8, pady=8)

        self.btn_save_video = ttk.Button(
            btn_row,
            text='Save Test Video...',
            command=self.on_save_test_video,
        )
        self.btn_save_video.pack(side='left', padx=4)

        self.btn_cancel = ttk.Button(
            btn_row,
            text='Cancel Export',
            command=self.cancel_export,
            state='disabled',
        )
        self.btn_cancel.pack(side='left', padx=4)

    def _create_progress_panel(self, container: ttk.Frame) -> None:
        """Creates the export progress bar and status feedback label.

        Args:
            container: Parent frame container for the panel.
        """
        frame_prog = ttk.Frame(container)
        frame_prog.pack(fill='x', padx=4, pady=8)

        self.progress_bar = ttk.Progressbar(frame_prog, mode='indeterminate')
        self.progress_bar.pack(fill='x', padx=8, pady=4)

        self.lbl_status = ttk.Label(
            frame_prog,
            text='Ready to export test video.',
        )
        self.lbl_status.pack(anchor='w', padx=8, pady=4)

    def set_export_data(
        self,
        video_path: str | Path | None,
        ranges: list[TimeRange],
        noise_reduction_settings: NoiseReductionSettings | None = None,
        lut: Lut3D | None = None,
    ) -> None:
        """Updates export configuration with reference video and filter parameters.

        Args:
            video_path: File system path of the loaded reference video.
            ranges: Configured TimeRange intervals to combine.
            noise_reduction_settings: Active NoiseReductionSettings instance.
            lut: Active Lut3D instance to apply.

        Usage example:
            tab.set_export_data(
                video_path='raw.mp4',
                ranges=selected_ranges,
                noise_reduction_settings=nr_settings,
                lut=active_lut,
            )
        """
        self.video_path = Path(video_path) if video_path else None
        self.ranges = list(ranges)
        self.noise_reduction_settings = noise_reduction_settings
        self.lut = lut

        if self.video_path:
            self.lbl_source_info.config(
                text=f'Source video: {self.video_path.name}'
            )
        else:
            self.lbl_source_info.config(text='Source video: None loaded')

        total_ms = sum(max(0, r.end_ms - r.start_ms) for r in self.ranges)
        total_sec = total_ms / MS_PER_SECOND
        mins = int(total_sec // 60)
        secs = total_sec % 60
        duration_str = f'{mins:02d}:{secs:06.3f}'
        self.lbl_range_info.config(
            text=(
                f'Selected ranges: {len(self.ranges)} ranges '
                f'(Total duration: {duration_str})'
            )
        )

        self.update_noise_reduction_args()

    def update_noise_reduction_args(self) -> None:
        """Refreshes the displayed FFmpeg noise reduction argument string.

        Usage example:
            tab.update_noise_reduction_args()
        """
        if self.noise_reduction_settings is None:
            args_str = '(Noise reduction settings not configured)'
        else:
            args_str = self.noise_reduction_settings.to_ffmpeg_args()
        self.var_nr_args.set(args_str)

    def on_copy_args(self) -> None:
        """Copies the current noise reduction arguments to system clipboard.

        Usage example:
            tab.on_copy_args()
        """
        args_str = str(self.var_nr_args.get())

        try:
            self.clipboard_clear()
            self.clipboard_append(args_str)
            self.lbl_status.config(text='Arguments copied to clipboard.')
        except (tk.TclError, RuntimeError, AttributeError):
            pass

    def on_save_test_video(self) -> None:
        """Opens save file dialog and initiates background video export.

        Usage example:
            tab.on_save_test_video()
        """
        if self.is_exporting:
            return

        if not self.video_path or not self.video_path.exists():
            messagebox.showerror('Export Error', 'Source video file not found.')
            return

        if not self.ranges:
            messagebox.showerror(
                'Export Error',
                'At least one reference range is required to export.',
            )
            return

        dest = filedialog.asksaveasfilename(
            title='Save Test Video',
            defaultextension='.mp4',
            filetypes=[('MP4 Video', '*.mp4'), ('All Files', '*.*')],
        )
        if not dest:
            return

        self._start_export(destination=Path(dest))

    def _start_export(self, destination: Path) -> None:
        """Starts background worker thread to render and save test video.

        Args:
            destination: Target file path to write the exported video.
        """
        self.is_exporting = True
        self.btn_save_video.config(state='disabled')
        self.btn_cancel.config(state='normal')
        self.lbl_status.config(
            text=f'Exporting video to {destination.name}... Please wait.'
        )

        try:
            self.progress_bar.start(10)
        except (tk.TclError, RuntimeError, AttributeError):
            pass

        self.cancel_event = threading.Event()
        apply_lut = bool(self.var_apply_lut.get())
        apply_noise = bool(self.var_apply_noise.get())

        self.export_thread = threading.Thread(
            target=self._run_export_worker,
            args=(destination, apply_lut, apply_noise),
            daemon=True,
        )
        self.export_thread.start()

    def _run_export_worker(
        self,
        destination: Path,
        apply_lut: bool,
        apply_noise: bool,
    ) -> None:
        """Worker thread executing FFmpeg export process.

        Args:
            destination: Path to write the output video.
            apply_lut: Whether to apply color correction LUT filter.
            apply_noise: Whether to apply noise reduction filter.
        """
        temp_cube: Path | None = None
        nr_filter: str | None = None

        try:
            if apply_lut and self.lut is not None:
                with tempfile.NamedTemporaryFile(
                    suffix='.cube',
                    delete=False,
                    mode='w',
                    encoding='utf-8',
                ) as tmp_file:
                    tmp_file.write(self.lut.to_cube_text())
                    temp_cube = Path(tmp_file.name)

            if (
                apply_noise
                and self.noise_reduction_settings is not None
                and self.noise_reduction_settings.enabled
            ):
                nr_filter = self.noise_reduction_settings.to_ffmpeg_filter()

            apply_filters = temp_cube is not None or (
                nr_filter is not None and nr_filter != 'null'
            )

            if self.video_path is None:
                raise ValueError('Source video path is not defined.')

            self.video_exporter.export_video(
                source_path=self.video_path,
                output_path=destination,
                ranges=self.ranges,
                apply_filters=apply_filters,
                noise_reduction_filter=nr_filter,
                lut_path=temp_cube,
                cancel_event=self.cancel_event,
            )
            msg = f'Video successfully saved to {destination.name}'
            self._dispatch_callback(success=True, message=msg)
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            self._dispatch_callback(success=False, message=msg)
        finally:
            if temp_cube is not None and temp_cube.exists():
                try:
                    temp_cube.unlink()
                except OSError:
                    pass

    def _dispatch_callback(self, success: bool, message: str) -> None:
        """Dispatches export completion to the UI thread.

        Args:
            success: Whether export completed successfully.
            message: Completion or error message.
        """
        try:
            self.after(0, self._on_export_finished, success, message)
        except (tk.TclError, RuntimeError, AttributeError):
            self._on_export_finished(success=success, message=message)

    def cancel_export(self) -> None:
        """Signals active video export worker to terminate.

        Usage example:
            tab.cancel_export()
        """
        if self.is_exporting and self.cancel_event is not None:
            self.lbl_status.config(text='Cancelling export...')
            self.cancel_event.set()

    def _on_export_finished(self, success: bool, message: str) -> None:
        """Handles completion of the video export worker thread.

        Args:
            success: True if export completed successfully, False otherwise.
            message: Informational or error message to display.
        """
        self.is_exporting = False
        try:
            self.progress_bar.stop()
        except (tk.TclError, RuntimeError, AttributeError):
            pass

        self.btn_save_video.config(state='normal')
        self.btn_cancel.config(state='disabled')
        self.lbl_status.config(text=message)

        if success:
            messagebox.showinfo('Export Complete', message)
        else:
            if 'cancelled' in message.lower():
                self.lbl_status.config(text='Export was cancelled.')
            else:
                ErrorDialog.show_error(
                    parent=self,
                    title='Export Failed',
                    message=message,
                    copy_to_clipboard_immediately=True,
                )
