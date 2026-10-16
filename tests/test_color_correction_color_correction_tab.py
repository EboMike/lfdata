"""Tests for ColorCorrectionTab component."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from PIL import Image

from lfdata.color_correction.color_correction_tab import ColorCorrectionTab
from lfdata.color_correction.lut import Lut3D
from lfdata.color_correction.time_range import TimeRange


class DummyWidget:
    """Mock widget for headless testing of tab components."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._options: dict[str, Any] = dict(kwargs)
        self.text: str = str(kwargs.get('text', ''))
        self.image: Any = kwargs.get('image', None)
        self._val: float = float(kwargs.get('value', 0.0))
        self._w: str = '.'
        self.tk: Any = MagicMock()
        self.children: dict[str, Any] = {}

    def pack(self, *args: Any, **kwargs: Any) -> None:
        pass

    def grid(self, *args: Any, **kwargs: Any) -> None:
        pass

    def columnconfigure(self, *args: Any, **kwargs: Any) -> None:
        pass

    def bind(self, *args: Any, **kwargs: Any) -> None:
        pass

    def config(self, *args: Any, **kwargs: Any) -> None:
        self._options.update(kwargs)
        if 'text' in kwargs:
            self.text = str(kwargs['text'])
        if 'image' in kwargs:
            self.image = kwargs['image']

    def configure(self, *args: Any, **kwargs: Any) -> None:
        self.config(*args, **kwargs)

    def cget(self, key: str) -> Any:
        return self._options.get(key, getattr(self, key, ''))

    def set(self, val: float) -> None:
        self._val = float(val)

    def get(self) -> float:
        return self._val


class DummyCanvas(DummyWidget):
    """Mock Canvas for LUT panel drawing."""

    def delete(self, *args: Any, **kwargs: Any) -> None:
        pass

    def create_image(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def create_oval(self, *args: Any, **kwargs: Any) -> int:
        return 1


def create_mocked_tab() -> ColorCorrectionTab:
    with (
        patch('tkinter.ttk.Frame', DummyWidget),
        patch('tkinter.ttk.LabelFrame', DummyWidget),
        patch('tkinter.ttk.Label', DummyWidget),
        patch('tkinter.ttk.Button', DummyWidget),
        patch('tkinter.ttk.Scale', DummyWidget),
        patch('tkinter.Canvas', DummyCanvas),
    ):
        parent = DummyWidget()
        tab = ColorCorrectionTab(parent=parent)
        return tab


def test_color_correction_tab_init() -> None:
    tab = create_mocked_tab()
    try:
        assert tab.lbl_lut_status is not None
        assert tab.btn_load_cube is not None
        assert tab.btn_export_cube is not None
        assert tab.btn_reset_lut is not None
        assert tab.lut_panel is not None
        assert tab.scale_brightness is not None
        assert tab.scale_contrast is not None
        assert tab.scale_saturation is not None
        assert tab.scale_temperature is not None
        assert tab.scale_tint is not None
        assert tab.btn_play_pause is not None
        assert tab.scale_scrub is not None
        assert tab.lbl_playback_time is not None
        assert tab.lbl_orig_preview is not None
        assert tab.lbl_proc_preview is not None
    finally:
        tab.close()


def test_color_correction_tab_slider_adjustments() -> None:
    tab = create_mocked_tab()
    try:
        tab._on_brightness_changed('25.0')
        assert tab.lut.brightness == 0.25

        tab._on_contrast_changed('40.0')
        assert tab.lut.contrast == 1.4

        tab._on_saturation_changed('-30.0')
        assert tab.lut.saturation == 0.7

        tab._on_temperature_changed('50.0')
        assert tab.lut.temperature == 0.5

        tab._on_tint_changed('-40.0')
        assert tab.lut.tint == -0.4
    finally:
        tab.close()


def test_color_correction_tab_lut_panel_balance_sync() -> None:
    tab = create_mocked_tab()
    try:
        tab._on_lut_panel_balance_changed(temperature=0.3, tint=-0.2)
        assert tab.scale_temperature.get() == 30.0
        assert tab.scale_tint.get() == -20.0
    finally:
        tab.close()


def test_color_correction_tab_reset() -> None:
    tab = create_mocked_tab()
    try:
        tab.lut.brightness = 0.5
        tab.lut.contrast = 1.8
        tab.lut.recompute()

        tab._on_reset_lut_click()
        assert tab.lut.brightness == 0.0
        assert tab.lut.contrast == 1.0
        assert 'Identity' in tab.lbl_lut_status.text
    finally:
        tab.close()


def test_color_correction_tab_load_and_export_cube() -> None:
    tab = create_mocked_tab()
    try:
        sample_lut = Lut3D(size=2)
        sample_lut.title = 'SavedLook'

        with tempfile.TemporaryDirectory() as tmp_dir:
            lut_file = Path(tmp_dir) / 'test.cube'
            sample_lut.save_cube_file(file_path=lut_file)

            with (
                patch(
                    'tkinter.filedialog.askopenfilename',
                    return_value=str(lut_file),
                ),
                patch('tkinter.messagebox.showerror'),
                patch('tkinter.messagebox.showinfo'),
            ):
                tab._on_load_cube_click()
                assert 'test.cube' in tab.lbl_lut_status.text
                assert tab.lut.title == 'SavedLook'

            out_file = Path(tmp_dir) / 'exported.cube'
            with (
                patch(
                    'tkinter.filedialog.asksaveasfilename',
                    return_value=str(out_file),
                ),
                patch('tkinter.messagebox.showerror'),
                patch('tkinter.messagebox.showinfo'),
            ):
                tab._on_export_cube_click()
                assert out_file.exists()
    finally:
        tab.close()


def test_color_correction_tab_reference_data_and_scrub() -> None:
    tab = create_mocked_tab()
    try:
        mock_reader = MagicMock()
        mock_reader.duration_ms = 10000
        ranges = [
            TimeRange(start_ms=1000, end_ms=4000),  # 3000 ms
            TimeRange(start_ms=6000, end_ms=8000),  # 2000 ms
        ]

        tab.set_reference_data(video_reader=mock_reader, ranges=ranges)
        assert tab.reference_video is not None
        assert tab.reference_video.total_duration_ms == 5000
        assert '00:05.000' in tab.lbl_playback_time.text

        # Scrubbing updates current_time_ms
        tab._on_scrub_changed('2500')
        assert tab.current_time_ms == 2500
        assert '00:02.500' in tab.lbl_playback_time.text
    finally:
        tab.close()


def test_color_correction_tab_playback_loop() -> None:
    tab = create_mocked_tab()
    try:
        mock_reader = MagicMock()
        mock_reader.duration_ms = 5000
        ranges = [TimeRange(start_ms=0, end_ms=100)]  # 100 ms duration

        tab.set_reference_data(video_reader=mock_reader, ranges=ranges)

        tab.start_playback()
        assert tab.is_playing is True
        assert tab.btn_play_pause.text == 'Pause'

        # Loop steps
        tab.current_time_ms = 90
        tab._playback_loop_step()
        # Next tick should wrap around to 0
        assert tab.current_time_ms == 0

        tab.pause_playback()
        assert tab.is_playing is False
        assert tab.btn_play_pause.text == 'Play'

        tab.toggle_playback()
        assert tab.is_playing is True
    finally:
        tab.close()


def test_color_correction_tab_worker_task_processing() -> None:
    tab = create_mocked_tab()
    try:
        tab._worker_running = False
        with tab._render_condition:
            tab._render_condition.notify_all()
        if tab._worker_thread and tab._worker_thread.is_alive():
            tab._worker_thread.join(timeout=0.5)

        mock_reader = MagicMock()
        fake_frame = Image.new('RGB', (100, 50), color=(128, 128, 128))
        mock_reader.get_frame_at.return_value = fake_frame

        ranges = [TimeRange(start_ms=1000, end_ms=3000)]
        tab.set_reference_data(video_reader=mock_reader, ranges=ranges)

        # Process a frame request
        tab._process_worker_task(target_time_ms=500, reapply_lut=False)
        assert tab._cached_source_frame is fake_frame
        assert tab._cached_source_time_ms == 500

        # Process a re-apply request
        tab.lut.brightness = 0.2
        tab.lut.recompute()
        tab._process_worker_task(target_time_ms=None, reapply_lut=True)
        assert tab._cached_source_frame is fake_frame
    finally:
        tab.close()
