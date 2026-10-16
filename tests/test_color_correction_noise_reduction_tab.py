"""Tests for NoiseReductionTab UI component."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from PIL import Image

from lfdata.color_correction.lut import Lut3D
from lfdata.color_correction.noise_reduction_tab import NoiseReductionTab
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

    def set(self, val: Any) -> None:
        try:
            self._val = float(val)
        except (ValueError, TypeError):
            self._options['value'] = val

    def get(self) -> Any:
        return self._options.get('value', self._val)


def create_mocked_noise_reduction_tab() -> NoiseReductionTab:
    with (
        patch('tkinter.ttk.Frame', DummyWidget),
        patch('tkinter.ttk.LabelFrame', DummyWidget),
        patch('tkinter.ttk.Label', DummyWidget),
        patch('tkinter.ttk.Button', DummyWidget),
        patch('tkinter.ttk.Checkbutton', DummyWidget),
        patch('tkinter.ttk.Combobox', DummyWidget),
        patch('tkinter.ttk.Scale', DummyWidget),
    ):
        parent = DummyWidget()
        tab = NoiseReductionTab(parent=parent)
        return tab


def test_noise_reduction_tab_init() -> None:
    tab = create_mocked_noise_reduction_tab()
    try:
        assert tab.chk_enabled is not None
        assert tab.cmb_filter_type is not None
        assert tab.cmb_preset is not None
        assert tab.btn_reset is not None
        assert tab.lbl_filter_preview is not None
        assert tab.scale_luma_spatial is not None
        assert tab.scale_chroma_spatial is not None
        assert tab.scale_luma_temporal is not None
        assert tab.scale_chroma_temporal is not None
        assert tab.scale_nlmeans_strength is not None
        assert tab.scale_nlmeans_patch is not None
        assert tab.btn_play_pause is not None
        assert tab.scale_scrub is not None
        assert tab.lbl_playback_time is not None
        assert tab.lbl_orig_preview is not None
        assert tab.lbl_proc_preview is not None
    finally:
        tab.close()


def test_noise_reduction_tab_slider_adjustments() -> None:
    tab = create_mocked_noise_reduction_tab()
    try:
        tab._on_slider_changed('luma_spatial', '7.5')
        assert tab.settings.luma_spatial == 7.5

        tab._on_slider_changed('chroma_spatial', '5.2')
        assert tab.settings.chroma_spatial == 5.2

        tab._on_slider_changed('luma_temporal', '9.0')
        assert tab.settings.luma_temporal == 9.0

        tab._on_slider_changed('chroma_temporal', '6.1')
        assert tab.settings.chroma_temporal == 6.1

        tab._on_slider_changed('nlmeans_strength', '18.0')
        assert tab.settings.nlmeans_strength == 18.0

        tab._on_slider_changed('nlmeans_patch', '8.0')
        assert tab.settings.nlmeans_patch == 9
    finally:
        tab.close()


def test_noise_reduction_tab_filter_type_changed() -> None:
    tab = create_mocked_noise_reduction_tab()
    try:
        tab.cmb_filter_type._options['value'] = 'nlmeans'
        tab._on_filter_type_changed()
        assert tab.settings.filter_type == 'nlmeans'
        assert 'nlmeans=' in tab.lbl_filter_preview.text

        tab.cmb_filter_type._options['value'] = 'hqdn3d'
        tab._on_filter_type_changed()
        assert tab.settings.filter_type == 'hqdn3d'
        assert 'hqdn3d=' in tab.lbl_filter_preview.text
    finally:
        tab.close()


def test_noise_reduction_tab_preset_changed() -> None:
    tab = create_mocked_noise_reduction_tab()
    try:
        tab.cmb_preset._options['value'] = 'Mild'
        tab._on_preset_changed()
        assert tab.settings.luma_spatial == 2.0
        assert tab.settings.chroma_spatial == 1.5

        tab.cmb_preset._options['value'] = 'Strong'
        tab._on_preset_changed()
        assert tab.settings.luma_spatial == 8.0
        assert tab.settings.chroma_spatial == 6.0

        tab.cmb_preset._options['value'] = 'Medium (Default)'
        tab._on_preset_changed()
        assert tab.settings.luma_spatial == 4.0
        assert tab.settings.chroma_spatial == 3.0
    finally:
        tab.close()


def test_noise_reduction_tab_enabled_toggled_and_reset() -> None:
    tab = create_mocked_noise_reduction_tab()
    try:
        tab.var_enabled.set(False)
        tab._on_enabled_toggled()
        assert tab.settings.enabled is False
        assert tab.settings.to_ffmpeg_filter() == 'null'

        tab._on_reset_clicked()
        assert tab.settings.enabled is True
        assert tab.settings.filter_type == 'hqdn3d'
    finally:
        tab.close()


def test_noise_reduction_tab_scrub_and_playback() -> None:
    tab = create_mocked_noise_reduction_tab()
    try:
        tab._on_scrub_changed('1500')
        assert tab.current_time_ms == 1500

        tab._on_scrub_changed('invalid')
        assert tab.current_time_ms == 1500

        mock_reader = MagicMock()
        mock_reader.fps = 30.0
        mock_reader.duration_ms = 10000
        ranges = [TimeRange(start_ms=0, end_ms=5000)]
        tab.set_reference_data(video_reader=mock_reader, ranges=ranges)
        assert tab.current_time_ms == 0
        assert tab.reference_video is not None
        assert tab.reference_video.total_duration_ms == 5000

        assert not tab.is_playing
        tab.toggle_playback()
        assert tab.is_playing
        tab._playback_step()
        assert tab.current_time_ms > 0

        tab.pause_playback()
        assert not tab.is_playing

        tab.set_reference_data(video_reader=None, ranges=[])
        assert tab.reference_video.total_duration_ms == 0
        tab.play()
        assert not tab.is_playing
    finally:
        tab.close()


def test_noise_reduction_tab_set_lut() -> None:
    tab = create_mocked_noise_reduction_tab()
    try:
        new_lut = Lut3D()
        new_lut.brightness = 0.5
        tab.set_lut(new_lut)
        assert tab.lut.brightness == 0.5
        assert tab._cached_base_frame is None
    finally:
        tab.close()


def test_noise_reduction_tab_process_worker_task() -> None:
    tab = create_mocked_noise_reduction_tab()
    try:
        tab._worker_running = False
        with tab._render_condition:
            tab._render_condition.notify_all()
        if tab._worker_thread and tab._worker_thread.is_alive():
            tab._worker_thread.join(timeout=0.5)

        sample_img = Image.new('RGB', (100, 100), color=(120, 80, 40))
        mock_reader = MagicMock()
        mock_reader.get_frame_at_ms.return_value = sample_img
        mock_reader.duration_ms = 5000
        mock_reader.fps = 30.0
        ranges = [TimeRange(start_ms=0, end_ms=2000)]
        tab.set_reference_data(video_reader=mock_reader, ranges=ranges)

        with patch.object(tab, '_safe_after') as mock_safe_after:
            tab._process_worker_task(target_time_ms=500, reapply=False)
            mock_safe_after.assert_called_once()

            tab._process_worker_task(target_time_ms=None, reapply=True)
            assert mock_safe_after.call_count == 2

        with (
            patch(
                'lfdata.color_correction.noise_reduction_tab.ImageTk.PhotoImage'
            ) as mock_photo,
        ):
            mock_photo.return_value = MagicMock()
            tab._apply_rendered_previews(
                orig_img=sample_img,
                proc_img=sample_img,
            )
            assert tab.lbl_orig_preview.text == ''
            assert tab.lbl_proc_preview.text == ''
    finally:
        tab.close()
