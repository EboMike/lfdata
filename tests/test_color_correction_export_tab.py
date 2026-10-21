"""Tests for ExportTab UI component."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from lfdata.color_correction.export_tab import ExportTab, _FallbackVar
from lfdata.color_correction.lut import Lut3D
from lfdata.color_correction.noise_reduction import NoiseReductionSettings
from lfdata.color_correction.time_range import TimeRange
from lfdata.color_correction.video_exporter import VideoExporter


class DummyWidget:
    """Mock widget for headless testing of tab components."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._options: dict[str, Any] = dict(kwargs)
        self.text: str = str(kwargs.get('text', ''))
        self.image: Any = kwargs.get('image', None)
        self._val: Any = kwargs.get('value', '')
        self._w: str = '.'
        self.tk: Any = MagicMock()
        self.children: dict[str, Any] = {}

    def pack(self, *args: Any, **kwargs: Any) -> None:
        pass

    def config(self, *args: Any, **kwargs: Any) -> None:
        self._options.update(kwargs)
        if 'text' in kwargs:
            self.text = str(kwargs['text'])

    def configure(self, *args: Any, **kwargs: Any) -> None:
        self.config(*args, **kwargs)

    def cget(self, key: str) -> Any:
        return self._options.get(key, getattr(self, key, ''))

    def set(self, val: Any) -> None:
        self._val = val

    def get(self) -> Any:
        return self._val

    def start(self, interval: int = 10) -> None:
        pass

    def stop(self) -> None:
        pass


def _create_test_tab() -> ExportTab:
    """Helper to instantiate ExportTab with mocked ttk widgets."""
    with (
        patch('tkinter.ttk.Frame', DummyWidget),
        patch('tkinter.ttk.LabelFrame', DummyWidget),
        patch('tkinter.ttk.Label', DummyWidget),
        patch('tkinter.ttk.Button', DummyWidget),
        patch('tkinter.ttk.Entry', DummyWidget),
        patch('tkinter.ttk.Checkbutton', DummyWidget),
        patch('tkinter.ttk.Progressbar', DummyWidget),
    ):
        parent = DummyWidget()
        mock_exporter = MagicMock(spec=VideoExporter)
        tab = ExportTab(parent=parent, video_exporter=mock_exporter)
    return tab


def test_fallback_var() -> None:
    var = _FallbackVar('initial')
    assert var.get() == 'initial'
    var.set('updated')
    assert var.get() == 'updated'


def test_export_tab_initial_state() -> None:
    tab = _create_test_tab()
    assert tab.video_path is None
    assert tab.ranges == []
    assert tab.noise_reduction_settings is None
    assert tab.lut is None
    assert tab.is_exporting is False
    assert tab.export_thread is None
    assert tab.cancel_event is None
    assert tab.var_apply_lut.get() is True
    assert tab.var_apply_noise.get() is True


def test_set_export_data_empty() -> None:
    tab = _create_test_tab()
    tab.set_export_data(
        video_path=None,
        ranges=[],
        noise_reduction_settings=None,
        lut=None,
    )
    assert 'None loaded' in tab.lbl_source_info.text
    assert '0 ranges' in tab.lbl_range_info.text
    assert tab.var_nr_args.get() == '(Noise reduction settings not configured)'


def test_set_export_data_populated(tmp_path: Path) -> None:
    tab = _create_test_tab()
    dummy_video = tmp_path / 'match.mp4'
    ranges = [
        TimeRange(start_ms=1000, end_ms=4500),
        TimeRange(start_ms=10000, end_ms=21700),
    ]
    nr = NoiseReductionSettings()
    nr.luma_spatial = 5.0
    nr.chroma_spatial = 3.5
    lut = Lut3D()
    lut.brightness = 0.2

    tab.set_export_data(
        video_path=dummy_video,
        ranges=ranges,
        noise_reduction_settings=nr,
        lut=lut,
    )

    assert dummy_video.name in tab.lbl_source_info.text
    assert '2 ranges' in tab.lbl_range_info.text
    assert '00:15.200' in tab.lbl_range_info.text
    assert 'hqdn3d=5.0:3.5' in tab.var_nr_args.get()


def test_set_export_data_disabled_noise_reduction(tmp_path: Path) -> None:
    tab = _create_test_tab()
    dummy_video = tmp_path / 'match.mp4'
    ranges = [TimeRange(start_ms=100, end_ms=500)]
    nr = NoiseReductionSettings()
    nr.enabled = False

    tab.set_export_data(
        video_path=dummy_video,
        ranges=ranges,
        noise_reduction_settings=nr,
    )

    assert tab.var_nr_args.get() == '(Noise reduction is disabled)'


def test_on_copy_args() -> None:
    tab = _create_test_tab()
    tab.var_nr_args.set('-vf "hqdn3d=4.0:3.0:6.0:4.5"')

    with (
        patch.object(tab, 'clipboard_clear') as mock_clear,
        patch.object(tab, 'clipboard_append') as mock_append,
    ):
        tab.on_copy_args()
        mock_clear.assert_called_once()
        mock_append.assert_called_once_with('-vf "hqdn3d=4.0:3.0:6.0:4.5"')
        assert 'copied to clipboard' in tab.lbl_status.text


def test_on_save_test_video_when_already_exporting() -> None:
    tab = _create_test_tab()
    tab.is_exporting = True
    with patch('tkinter.filedialog.asksaveasfilename') as mock_dialog:
        tab.on_save_test_video()
        mock_dialog.assert_not_called()


def test_on_save_test_video_missing_file(tmp_path: Path) -> None:
    tab = _create_test_tab()
    tab.video_path = tmp_path / 'missing.mp4'
    tab.ranges = [TimeRange(start_ms=100, end_ms=500)]

    with patch('tkinter.messagebox.showerror') as mock_err:
        tab.on_save_test_video()
        mock_err.assert_called_once()


def test_on_save_test_video_empty_ranges(tmp_path: Path) -> None:
    tab = _create_test_tab()
    src = tmp_path / 'test.mp4'
    src.write_text('dummy')
    tab.video_path = src
    tab.ranges = []

    with patch('tkinter.messagebox.showerror') as mock_err:
        tab.on_save_test_video()
        mock_err.assert_called_once()


def test_on_save_test_video_dialog_cancelled(tmp_path: Path) -> None:
    tab = _create_test_tab()
    src = tmp_path / 'test.mp4'
    src.write_text('dummy')
    tab.video_path = src
    tab.ranges = [TimeRange(start_ms=100, end_ms=500)]

    with (
        patch('tkinter.filedialog.asksaveasfilename', return_value=''),
        patch.object(tab, '_start_export') as mock_start,
    ):
        tab.on_save_test_video()
        mock_start.assert_not_called()


def test_on_save_test_video_triggers_export(tmp_path: Path) -> None:
    tab = _create_test_tab()
    src = tmp_path / 'test.mp4'
    src.write_text('dummy')
    tab.video_path = src
    tab.ranges = [TimeRange(start_ms=100, end_ms=500)]
    dest = tmp_path / 'output.mp4'

    with (
        patch('tkinter.filedialog.asksaveasfilename', return_value=str(dest)),
        patch.object(tab, '_start_export') as mock_start,
    ):
        tab.on_save_test_video()
        mock_start.assert_called_once_with(destination=dest)


def test_start_export_launches_thread(tmp_path: Path) -> None:
    tab = _create_test_tab()
    dest = tmp_path / 'rendered.mp4'

    with patch('threading.Thread') as mock_thread_cls:
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        tab._start_export(destination=dest)

        assert tab.is_exporting is True
        assert tab.btn_save_video.cget('state') == 'disabled'
        assert tab.btn_cancel.cget('state') == 'normal'
        mock_thread.start.assert_called_once()


def test_run_export_worker_success(tmp_path: Path) -> None:
    tab = _create_test_tab()
    src = tmp_path / 'test.mp4'
    src.write_text('dummy')
    dest = tmp_path / 'output.mp4'
    tab.video_path = src
    tab.ranges = [TimeRange(start_ms=1000, end_ms=3000)]
    tab.lut = Lut3D()
    tab.noise_reduction_settings = NoiseReductionSettings()
    tab.cancel_event = threading.Event()

    with patch.object(tab, '_dispatch_callback') as mock_cb:
        tab._run_export_worker(
            destination=dest,
            apply_lut=True,
            apply_noise=True,
        )

        assert tab.video_exporter.export_video.called  # type: ignore[attr-defined]
        mock_cb.assert_called_once_with(
            success=True,
            message=f'Video successfully saved to {dest.name}',
        )


def test_run_export_worker_error(tmp_path: Path) -> None:
    tab = _create_test_tab()
    dest = tmp_path / 'output.mp4'
    tab.video_path = None
    tab.ranges = [TimeRange(start_ms=1000, end_ms=3000)]

    with patch.object(tab, '_dispatch_callback') as mock_cb:
        tab._run_export_worker(
            destination=dest,
            apply_lut=False,
            apply_noise=False,
        )
        mock_cb.assert_called_once()
        call_args = mock_cb.call_args[1]
        assert call_args['success'] is False
        assert 'Source video path is not defined' in call_args['message']


def test_cancel_export() -> None:
    tab = _create_test_tab()
    tab.is_exporting = True
    tab.cancel_event = threading.Event()

    tab.cancel_export()
    assert tab.cancel_event.is_set()
    assert 'Cancelling export' in tab.lbl_status.text


def test_on_export_finished_success() -> None:
    tab = _create_test_tab()
    tab.is_exporting = True
    tab.btn_save_video.config(state='disabled')
    tab.btn_cancel.config(state='normal')

    with patch('tkinter.messagebox.showinfo') as mock_info:
        tab._on_export_finished(success=True, message='Finished test.mp4')
        assert tab.is_exporting is False
        assert tab.btn_save_video.cget('state') == 'normal'
        assert tab.btn_cancel.cget('state') == 'disabled'
        mock_info.assert_called_once_with(
            'Export Complete', 'Finished test.mp4'
        )


def test_on_export_finished_cancelled() -> None:
    tab = _create_test_tab()
    tab.is_exporting = True

    with (
        patch('tkinter.messagebox.showerror') as mock_err,
        patch('tkinter.messagebox.showinfo') as mock_info,
    ):
        tab._on_export_finished(success=False, message='Export was cancelled.')
        assert tab.is_exporting is False
        mock_err.assert_not_called()
        mock_info.assert_not_called()
        assert tab.lbl_status.text == 'Export was cancelled.'


def test_on_export_finished_error() -> None:
    tab = _create_test_tab()
    tab.is_exporting = True

    with patch(
        'lfdata.color_correction.export_tab.ErrorDialog.show_error'
    ) as mock_dialog:
        tab._on_export_finished(success=False, message='FFmpeg failed')
        assert tab.is_exporting is False
        mock_dialog.assert_called_once_with(
            parent=tab,
            title='Export Failed',
            message='FFmpeg failed',
            copy_to_clipboard_immediately=True,
        )
