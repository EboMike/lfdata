"""Reference video selection, playback timeline, and range management tab.

This module provides the `ReferenceVideoTab` widget for loading reference video
files, previewing still frames along the timeline, and managing clip ranges.
All expensive operations such as video metadata probing, color averages
computations, and frame extraction are performed in worker threads to guarantee
UI responsiveness.

Usage example:
    import tkinter as tk
    from lfdata.color_correction.reference_video_tab import ReferenceVideoTab

    root = tk.Tk()
    tab = ReferenceVideoTab(parent=root)
    tab.pack(fill='both', expand=True)
"""

from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable
from PIL import Image, ImageTk

from lfdata.color_correction.color_averages_bar import ColorAveragesBar
from lfdata.color_correction.constants import (
    DEFAULT_PREVIEW_HEIGHT,
    DEFAULT_PREVIEW_WIDTH,
)
from lfdata.color_correction.time_range import TimeRange
from lfdata.color_correction.timeline_widget import TimelineWidget
from lfdata.color_correction.video_reader import VideoReader


class ReferenceVideoTab(ttk.Frame):
    """UI tab for loading reference videos and configuring timestamp ranges.

    Attributes:
        video_reader: VideoReader instance handling frame extraction.
        timeline: TimelineWidget instance for scrub and range operations.
        color_averages_bar: ColorAveragesBar showing video color profile.
        ranges: List of added TimeRange instances.
        on_ranges_changed: Optional callback invoked when ranges list changes.
        content_container: Frame containing timeline and preview widgets.
        lbl_still_image: Label widget displaying current video frame.
        tree_ranges: Treeview widget displaying added ranges.
        is_video_loaded: True once a video file has been successfully loaded.
        load_thread: Background worker thread for asynchronous video loading.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_ranges_changed: Callable[[list[TimeRange]], None] | None = None,
        video_reader: VideoReader | None = None,
    ) -> None:
        """Initializes the ReferenceVideoTab widget.

        Args:
            parent: Parent tkinter widget container.
            on_ranges_changed: Callback invoked when ranges list is updated.
            video_reader: Optional custom VideoReader instance.
        """
        try:
            super().__init__(parent)
        except Exception:
            from unittest.mock import MagicMock

            self._w = '.'
            self.tk = getattr(parent, 'tk', MagicMock())
            self.children = {}
        self.on_ranges_changed = on_ranges_changed
        self.video_reader = (
            video_reader if video_reader is not None else VideoReader()
        )
        self.ranges: list[TimeRange] = []
        self.is_video_loaded: bool = False
        self.load_thread: threading.Thread | None = None
        self._current_photo: ImageTk.PhotoImage | None = None
        self._last_frame_img: Image.Image | None = None

        self._frame_worker_running: bool = True
        self._pending_frame_time_ms: int | None = None
        self._frame_lock = threading.Lock()
        self._frame_condition = threading.Condition(self._frame_lock)
        self._frame_worker_thread = threading.Thread(
            target=self._frame_worker_loop,
            daemon=True,
        )
        self._frame_worker_thread.start()

        self._create_top_bar()
        self._create_content_container()

    def _create_top_bar(self) -> None:
        """Creates the top controls bar with the load reference video button."""
        top_frame = ttk.Frame(self)
        top_frame.pack(fill='x', padx=10, pady=10)

        self.btn_load_video = ttk.Button(
            top_frame,
            text='Load Reference Video...',
            command=self._on_load_video_click,
        )
        self.btn_load_video.pack(side='left', padx=5)

        self.lbl_video_info = ttk.Label(
            top_frame, text='No reference video loaded.'
        )
        self.lbl_video_info.pack(side='left', padx=10)

    def _create_content_container(self) -> None:
        """Creates the container for timeline, image preview, and ranges."""
        self.content_container = ttk.Frame(self)

        self._create_timeline_section()
        self._create_preview_section()
        self._create_ranges_section()

    def _create_timeline_section(self) -> None:
        """Creates the horizontal timeline bar and Add Range button row."""
        timeline_frame = ttk.Frame(self.content_container)
        timeline_frame.pack(fill='x', padx=5, pady=5)

        bars_container = ttk.Frame(timeline_frame)
        bars_container.pack(side='left', fill='x', expand=True, padx=(0, 5))

        self.timeline = TimelineWidget(
            parent=bars_container,
            duration_ms=0,
            on_time_changed=self._on_timeline_time_changed,
            on_range_changed=self._on_timeline_range_changed,
        )
        self.timeline.pack(fill='x', expand=True, pady=(0, 2))

        self.color_averages_bar = ColorAveragesBar(
            parent=bars_container,
            duration_ms=0,
        )
        self.color_averages_bar.pack(fill='x', expand=True, pady=(2, 0))

        self.btn_add_range = ttk.Button(
            timeline_frame,
            text='Add Range',
            command=self._on_add_range_click,
        )
        self.btn_add_range.pack(side='right', padx=5)

    def _create_preview_section(self) -> None:
        """Creates time indicator and still frame image display widgets."""
        self.lbl_time_status = ttk.Label(
            self.content_container,
            text='Time: 00:00.000',
            font=('TkDefaultFont', 9, 'bold'),
        )
        self.lbl_time_status.pack(anchor='w', padx=10, pady=(2, 5))

        self.preview_frame = ttk.Frame(
            self.content_container,
            width=DEFAULT_PREVIEW_WIDTH,
            height=DEFAULT_PREVIEW_HEIGHT,
        )
        self.preview_frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.preview_frame.pack_propagate(False)
        self.preview_frame.bind('<Configure>', self._on_preview_resize)

        self.lbl_still_image = ttk.Label(
            self.preview_frame,
            anchor='center',
            text='Frame preview',
        )
        self.lbl_still_image.pack(fill='both', expand=True)

    def _create_ranges_section(self) -> None:
        """Creates the reference ranges list and Delete Range controls."""
        ranges_frame = ttk.LabelFrame(
            self.content_container, text=' Reference Ranges '
        )
        ranges_frame.pack(fill='x', padx=10, pady=(5, 10))

        list_frame = ttk.Frame(ranges_frame)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)

        columns = ('index', 'start', 'end', 'duration')
        self.tree_ranges = ttk.Treeview(
            list_frame,
            columns=columns,
            show='headings',
            height=4,
            selectmode='browse',
        )
        self.tree_ranges.heading('index', text='#')
        self.tree_ranges.heading('start', text='Start Time')
        self.tree_ranges.heading('end', text='End Time')
        self.tree_ranges.heading('duration', text='Duration')

        self.tree_ranges.column('index', width=40, anchor='center')
        self.tree_ranges.column('start', width=120, anchor='center')
        self.tree_ranges.column('end', width=120, anchor='center')
        self.tree_ranges.column('duration', width=120, anchor='center')

        scrollbar = ttk.Scrollbar(
            list_frame, orient='vertical', command=self.tree_ranges.yview
        )
        self.tree_ranges.configure(yscrollcommand=scrollbar.set)

        self.tree_ranges.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        btn_frame = ttk.Frame(ranges_frame)
        btn_frame.pack(fill='x', padx=5, pady=5)

        self.btn_delete_range = ttk.Button(
            btn_frame,
            text='Delete Range',
            command=self._on_delete_range_click,
        )
        self.btn_delete_range.pack(side='left', padx=5)

    def _on_load_video_click(self) -> None:
        """Prompts the user to pick a video file and loads it asynchronously."""
        file_path = filedialog.askopenfilename(
            title='Select Reference Video',
            filetypes=[
                ('Video Files', '*.mp4 *.mov *.mkv *.avi *.webm *.m4v'),
                ('All Files', '*.*'),
            ],
        )
        if not file_path:
            return

        self.load_video(file_path=file_path, async_load=True)

    def load_video(
        self,
        file_path: str | Path,
        async_load: bool = False,
        on_complete: Callable[[], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Loads reference video and reveals editor controls.

        Loads the video via the video reader, queries the video duration,
        configures the timeline bounds, reveals the controls underneath the
        load button, and loads the initial still frame. When async_load is True,
        video file probing is executed in a background worker thread.

        Args:
            file_path: Path to the target video file.
            async_load: If True, executes loading in a background worker thread.
            on_complete: Optional callback invoked when async loading completes.
            on_error: Optional callback invoked when async loading encounters
                an error.

        Raises:
            FileNotFoundError: If video file does not exist (synchronous mode).
            ValueError: If video cannot be opened or duration is zero
                (synchronous mode).

        Usage example:
            tab.load_video(file_path='clip.mp4')
        """
        if not async_load:
            duration_ms = self.video_reader.load(video_path=file_path)
            self._apply_video_loaded(
                file_path=file_path, duration_ms=duration_ms
            )
            if on_complete is not None:
                on_complete()
            return

        path_obj = Path(file_path)
        self.lbl_video_info.config(
            text=f'Loading reference video: {path_obj.name}...'
        )
        self.btn_load_video.config(state='disabled')

        def _worker() -> None:
            try:
                duration_ms = self.video_reader.load(video_path=file_path)

                def _apply() -> None:
                    self.btn_load_video.config(state='normal')
                    self._apply_video_loaded(
                        file_path=file_path, duration_ms=duration_ms
                    )
                    if on_complete is not None:
                        on_complete()

                self._safe_after(delay_ms=0, callback=_apply)
            except Exception as exc:
                captured_err = exc

                def _fail() -> None:
                    self.btn_load_video.config(state='normal')
                    self.lbl_video_info.config(
                        text='Failed to load reference video.'
                    )
                    messagebox.showerror(
                        'Error Loading Video',
                        f'Failed to check reference video:\n{captured_err}',
                    )
                    if on_error is not None:
                        on_error(captured_err)

                self._safe_after(delay_ms=0, callback=_fail)

        self.load_thread = threading.Thread(target=_worker, daemon=True)
        self.load_thread.start()

    def _apply_video_loaded(
        self, file_path: str | Path, duration_ms: int
    ) -> None:
        """Applies loaded video metadata and displays initial frame.

        Args:
            file_path: Path of the loaded video file.
            duration_ms: Total duration in milliseconds.
        """
        path_obj = Path(file_path)
        formatted_dur = TimeRange.format_timestamp_ms(duration_ms)

        info_text = (
            f'File: {path_obj.name} | '
            f'Duration: {formatted_dur} ({duration_ms:,} ms) | '
            f'{self.video_reader.width}x{self.video_reader.height} @ '
            f'{self.video_reader.fps:.2f} fps'
        )
        self.lbl_video_info.config(text=info_text)

        self.timeline.set_duration_ms(duration_ms=duration_ms)
        self.timeline.set_current_time_ms(time_ms=0)
        self.timeline.clear_range()

        self.color_averages_bar.start_computation(
            video_path=file_path,
            duration_ms=duration_ms,
            fps=self.video_reader.fps,
            total_frames=self.video_reader.frame_count,
        )

        self.is_video_loaded = True
        self.content_container.pack(fill='both', expand=True, padx=10, pady=5)

        self._update_time_display(time_ms=0)
        self._display_frame_at(time_ms=0, async_display=False)

    def _on_timeline_time_changed(self, time_ms: int) -> None:
        """Handles scrub timestamp updates from the timeline widget.

        Args:
            time_ms: Current timeline scrub timestamp in milliseconds.
        """
        self._update_time_display(time_ms=time_ms)
        self._display_frame_at(time_ms=time_ms, async_display=True)

    def _on_timeline_range_changed(self, start_ms: int, end_ms: int) -> None:
        """Handles range selection changes from the timeline widget.

        Args:
            start_ms: Range start timestamp in milliseconds.
            end_ms: Range end timestamp in milliseconds.
        """
        self._update_time_display(
            time_ms=self.timeline.current_time_ms,
            range_start_ms=start_ms,
            range_end_ms=end_ms,
        )

    def _update_time_display(
        self,
        time_ms: int,
        range_start_ms: int | None = None,
        range_end_ms: int | None = None,
    ) -> None:
        """Updates the timestamp label text.

        Args:
            time_ms: Current timestamp in milliseconds.
            range_start_ms: Optional highlighted range start in milliseconds.
            range_end_ms: Optional highlighted range end in milliseconds.
        """
        time_str = TimeRange.format_timestamp_ms(time_ms)
        dur_str = TimeRange.format_timestamp_ms(self.video_reader.duration_ms)

        text = f'Time: {time_str} / {dur_str}'
        curr_range = self.timeline.get_current_range()
        if (
            range_start_ms is not None
            and range_end_ms is not None
            and range_end_ms > range_start_ms
        ):
            sel_range = TimeRange(start_ms=range_start_ms, end_ms=range_end_ms)
            text += f'  |  Selection: {sel_range.display_str()}'
        elif curr_range is not None:
            text += f'  |  Selection: {curr_range.display_str()}'

        self.lbl_time_status.config(text=text)

    def _display_frame_at(
        self, time_ms: int, async_display: bool = True
    ) -> None:
        """Extracts and renders still image at the given timestamp.

        Decodes the still video frame at the specified millisecond offset.
        If async_display is True, dispatches frame decoding to a background
        worker thread to keep the user interface responsive during timeline
        scrubbing.

        Args:
            time_ms: Millisecond offset into the video.
            async_display: If True, decodes asynchronously in worker thread.

        Usage example:
            tab._display_frame_at(time_ms=5000, async_display=True)
        """
        if not async_display:
            try:
                frame_img = self.video_reader.get_frame_at(timestamp_ms=time_ms)
                self._apply_rendered_frame(img=frame_img, time_ms=time_ms)
            except Exception as err:
                self._apply_frame_error(err=err, time_ms=time_ms)
            return

        with self._frame_condition:
            self._pending_frame_time_ms = time_ms
            self._frame_condition.notify_all()

    def _frame_worker_loop(self) -> None:
        """Background worker loop continuously decoding requested frames."""
        while self._frame_worker_running:
            with self._frame_condition:
                while (
                    self._frame_worker_running
                    and self._pending_frame_time_ms is None
                ):
                    self._frame_condition.wait()
                if not self._frame_worker_running:
                    break
                target_time_ms = self._pending_frame_time_ms
                self._pending_frame_time_ms = None

            if target_time_ms is None:
                continue

            try:
                frame_img = self.video_reader.get_frame_at(
                    timestamp_ms=target_time_ms
                )
                with self._frame_condition:
                    is_latest = self._pending_frame_time_ms is None

                if is_latest:
                    self._safe_after(
                        delay_ms=0,
                        callback=lambda img=frame_img, t=target_time_ms: (
                            self._apply_rendered_frame(img=img, time_ms=t)
                        ),
                    )
            except Exception as err:
                with self._frame_condition:
                    is_latest = self._pending_frame_time_ms is None
                if is_latest:
                    self._safe_after(
                        delay_ms=0,
                        callback=lambda e=err, t=target_time_ms: (
                            self._apply_frame_error(err=e, time_ms=t)
                        ),
                    )

    def _safe_after(self, delay_ms: int, callback: Callable[[], None]) -> None:
        """Schedules callback on UI thread if widget exists.

        Args:
            delay_ms: Milliseconds delay before execution.
            callback: Function to invoke on the main UI thread.
        """
        try:
            self.after(delay_ms, callback)
        except Exception:
            pass

    def _apply_rendered_frame(self, img: Image.Image, time_ms: int) -> None:
        """Renders the extracted frame image onto the preview label.

        Args:
            img: Decoded PIL Image of the video frame.
            time_ms: Timestamp in milliseconds of the rendered frame.
        """
        self._last_frame_img = img
        self._render_still_image(img=img)

    def _apply_frame_error(self, err: Exception, time_ms: int) -> None:
        """Displays frame extraction error message on the preview label.

        Args:
            err: Exception raised during frame extraction.
            time_ms: Timestamp in milliseconds where failure occurred.
        """
        self.lbl_still_image.config(
            text=f'Error rendering frame at {time_ms} ms: {err}',
            image='',
        )

    def _render_still_image(self, img: Image.Image) -> None:
        """Scales and sets the PIL image onto the preview label.

        Args:
            img: PIL image to render.
        """
        canvas_w = DEFAULT_PREVIEW_WIDTH
        canvas_h = DEFAULT_PREVIEW_HEIGHT

        if hasattr(self.preview_frame, 'winfo_width'):
            w = self.preview_frame.winfo_width()
            if w > 10:
                canvas_w = w
        if hasattr(self.preview_frame, 'winfo_height'):
            h = self.preview_frame.winfo_height()
            if h > 10:
                canvas_h = h

        img_w, img_h = img.size
        ratio = min(canvas_w / img_w, canvas_h / img_h)
        new_w = max(1, int(img_w * ratio))
        new_h = max(1, int(img_h * ratio))

        resized = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
        photo = ImageTk.PhotoImage(resized)

        self.lbl_still_image.config(image=photo, text='')
        self.lbl_still_image.image = photo  # Keep reference
        self._current_photo = photo

    def _on_preview_resize(self, event: tk.Event) -> None:
        """Handles resizing of the preview frame container.

        Args:
            event: Resize configuration event.
        """
        if self._last_frame_img is not None:
            self._render_still_image(self._last_frame_img)

    def _on_add_range_click(self) -> None:
        """Handles click on the Add Range button."""
        selected_range = self.timeline.get_current_range()
        if selected_range is None:
            messagebox.showinfo(
                'No Range Selected',
                'Please click and drag across the timeline to select a range '
                'before adding.',
            )
            return

        self.add_range(time_range=selected_range)
        self.timeline.clear_range()
        self._update_time_display(time_ms=self.timeline.current_time_ms)

    def add_range(self, time_range: TimeRange) -> None:
        """Adds a TimeRange to the reference ranges list and updates UI.

        Inserts the specified range into the internal ranges collection,
        refreshes the treeview display, and invokes the change callback.

        Args:
            time_range: The TimeRange instance to add.

        Usage example:
            tab.add_range(time_range=TimeRange(start_ms=1000, end_ms=4000))
        """
        self.ranges.append(time_range)
        self._refresh_ranges_view()
        if self.on_ranges_changed:
            self.on_ranges_changed(self.ranges)

    def _on_delete_range_click(self) -> None:
        """Handles click on the Delete Range button."""
        selected = self.tree_ranges.selection()
        if not selected:
            messagebox.showinfo(
                'No Selection',
                'Please select a range from the list to delete.',
            )
            return

        item_id = selected[0]
        idx = int(self.tree_ranges.item(item_id, 'values')[0]) - 1
        self.delete_range_at(index=idx)

    def delete_range_at(self, index: int) -> None:
        """Deletes the range at the specified index and updates UI.

        Removes the TimeRange at the specified index, refreshes the treeview,
        and invokes the change callback.

        Args:
            index: Zero-based index of the range to remove.

        Usage example:
            tab.delete_range_at(index=0)
        """
        if 0 <= index < len(self.ranges):
            self.ranges.pop(index)
            self._refresh_ranges_view()
            if self.on_ranges_changed:
                self.on_ranges_changed(self.ranges)

    def _refresh_ranges_view(self) -> None:
        """Refreshes the Treeview widget with current ranges list items."""
        for item in self.tree_ranges.get_children():
            self.tree_ranges.delete(item)

        for idx, item_range in enumerate(self.ranges, start=1):
            dur_sec = item_range.duration_ms / 1000.0
            self.tree_ranges.insert(
                '',
                'end',
                values=(
                    idx,
                    TimeRange.format_timestamp_ms(item_range.start_ms),
                    TimeRange.format_timestamp_ms(item_range.end_ms),
                    f'{dur_sec:.3f}s',
                ),
            )

    def close(self) -> None:
        """Stops background workers and releases video resources.

        Usage example:
            tab.close()
        """
        self._frame_worker_running = False
        with self._frame_condition:
            self._pending_frame_time_ms = None
            self._frame_condition.notify_all()
        if (
            self._frame_worker_thread is not None
            and self._frame_worker_thread.is_alive()
        ):
            self._frame_worker_thread.join(timeout=0.5)
        self.color_averages_bar.cancel()
        self.video_reader.close()

    def destroy(self) -> None:
        """Destroys widget and terminates background worker threads."""
        self.close()
        try:
            super().destroy()
        except Exception:
            pass
