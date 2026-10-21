"""Unit tests for 3D Look-Up Table (Lut3D) color grading model."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from lfdata.color_correction.lut import Lut3D


def test_lut3d_default_initialization() -> None:
    lut = Lut3D(size=4)
    assert lut.size == 4
    assert lut.title == 'Identity'
    assert lut.brightness == 0.0
    assert lut.contrast == 1.0
    assert lut.shadows == 0.0
    assert lut.deep_shadows == 0.0
    assert lut.black_level == 0.0
    assert lut.highlights == 0.0
    assert lut.gamma == 1.0
    assert lut.dark_expansion == 1.0
    assert lut.highlight_rolloff == 0.0
    assert lut.saturation == 1.0
    assert lut.temperature == 0.0
    assert lut.tint == 0.0
    assert len(lut.table) == 4 * 4 * 4 * 3
    assert len(lut.base_table) == len(lut.table)


def test_lut3d_reset_to_identity() -> None:
    lut = Lut3D(size=3)
    lut.brightness = 0.25
    lut.contrast = 1.4
    lut.shadows = 0.3
    lut.deep_shadows = 0.4
    lut.black_level = 0.1
    lut.highlights = -0.2
    lut.gamma = 1.5
    lut.dark_expansion = 1.5
    lut.highlight_rolloff = 0.4
    lut.saturation = 0.8
    lut.temperature = -0.3
    lut.tint = 0.5
    lut.recompute()

    lut.reset_to_identity()
    assert lut.brightness == 0.0
    assert lut.contrast == 1.0
    assert lut.shadows == 0.0
    assert lut.deep_shadows == 0.0
    assert lut.black_level == 0.0
    assert lut.highlights == 0.0
    assert lut.gamma == 1.0
    assert lut.dark_expansion == 1.0
    assert lut.highlight_rolloff == 0.0
    assert lut.saturation == 1.0
    assert lut.temperature == 0.0
    assert lut.tint == 0.0
    assert lut.table == lut.base_table


def test_lut3d_reset_adjustments() -> None:
    lut = Lut3D(size=3)
    lut.shadows = 0.4
    lut.deep_shadows = 0.3
    lut.black_level = 0.1
    lut.dark_expansion = 1.8
    lut.gamma = 1.8
    lut.recompute()
    assert lut.table != lut.base_table

    lut.reset_adjustments()
    assert lut.shadows == 0.0
    assert lut.deep_shadows == 0.0
    assert lut.black_level == 0.0
    assert lut.dark_expansion == 1.0
    assert lut.gamma == 1.0
    assert lut.table == lut.base_table


def test_lut3d_brightness_contrast_adjustment() -> None:
    lut = Lut3D(size=2)
    lut.brightness = 0.1
    lut.contrast = 1.2
    lut.recompute()

    assert lut.brightness == 0.1
    assert lut.contrast == 1.2
    # Verify values differ from identity
    assert lut.table != lut.base_table


def test_lut3d_shadows_and_highlights_adjustment() -> None:
    lut = Lut3D(size=5)
    lut.shadows = 0.5
    lut.highlights = -0.3
    lut.recompute()

    assert lut.shadows == 0.5
    assert lut.highlights == -0.3
    assert lut.table != lut.base_table

    # Test that black remains 0.0
    assert lut.table[0] == 0.0
    assert lut.table[1] == 0.0
    assert lut.table[2] == 0.0


def test_lut3d_gamma_and_highlight_rolloff() -> None:
    lut = Lut3D(size=5)
    lut.gamma = 1.6
    lut.highlight_rolloff = 0.5
    lut.recompute()

    assert lut.gamma == 1.6
    assert lut.highlight_rolloff == 0.5
    assert lut.table != lut.base_table

    # Pure black stays 0.0 and peak values do not exceed 1.0
    assert lut.table[0] == 0.0
    assert max(lut.table) <= 1.0


def test_lut3d_saturation_temperature_tint_adjustment() -> None:
    lut = Lut3D(size=2)
    lut.saturation = 0.5
    lut.temperature = 0.3
    lut.tint = -0.2
    lut.recompute()

    assert lut.saturation == 0.5
    assert lut.temperature == 0.3
    assert lut.tint == -0.2
    assert lut.table != lut.base_table


def test_lut3d_cube_serialization() -> None:
    lut = Lut3D(size=2)
    lut.title = 'TestLook'
    cube_text = lut.to_cube_text()

    assert 'TITLE "TestLook"' in cube_text
    assert 'LUT_3D_SIZE 2' in cube_text

    loaded_lut = Lut3D(size=2)
    loaded_lut.from_cube_text(text=cube_text)
    assert loaded_lut.size == 2
    assert loaded_lut.title == 'TestLook'
    assert len(loaded_lut.table) == len(lut.table)


def test_lut3d_file_load_save() -> None:
    lut = Lut3D(size=3)
    lut.title = 'ExportTest'
    lut.brightness = 0.05
    lut.recompute()

    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / 'test_lut.cube'
        lut.save_cube_file(file_path=file_path)
        assert file_path.exists()

        imported = Lut3D(size=2)
        imported.load_cube_file(file_path=file_path)
        assert imported.size == 3
        assert imported.title == 'ExportTest'


def test_lut3d_apply_to_image() -> None:
    lut = Lut3D(size=3)
    lut.brightness = 0.2
    lut.recompute()

    img = Image.new('RGB', (16, 16), color=(100, 100, 100))
    result = lut.apply_to_image(image=img)
    assert result.size == img.size
    # Brightness increase should make output pixels brighter
    px_orig = img.getpixel((0, 0))
    px_res = result.getpixel((0, 0))
    assert px_res[0] > px_orig[0]


def test_lut3d_generate_visualization_image() -> None:
    lut = Lut3D(size=4)
    vis = lut.generate_visualization_image(width=64, height=32)
    assert isinstance(vis, Image.Image)
    assert vis.size == (64, 32)


def test_lut3d_gamma_aggressive_dark_boost() -> None:
    lut = Lut3D(size=17)
    lut.gamma = 1.6
    lut.recompute()

    # Step size is 1.0 / 16 = 0.0625.
    # First non-zero point is at index 1 -> input value 0.0625
    # In table, R channel for (r=1, g=0, b=0) is at index 3
    r_dark_out = lut.table[3]
    # Pure clean power curve would give: 0.0625 ** (1 / 1.6) ~= 0.1768
    # Enhanced curve boosts somewhat dark areas significantly:
    assert r_dark_out > 0.25
    # Black stays 0
    assert lut.table[0] == 0.0
    # Peak white (last entry) stays 1.0
    assert lut.table[-1] == 1.0


def test_lut3d_deep_shadows_and_black_level() -> None:
    lut = Lut3D(size=17)
    # 1. Black level lifts the zero point
    lut.black_level = 0.2
    lut.recompute()
    assert pytest.approx(0.2 * 0.25, rel=1e-5) == float(lut.table[0])

    # 2. Deep shadows peaks in the near-black region
    lut_ds = Lut3D(size=17)
    lut_ds.deep_shadows = 0.5
    lut_ds.recompute()
    # At pure black (index 0), deep shadows boost is 0
    assert lut_ds.table[0] == 0.0
    # At r=0.0625, 0.125, etc., deep shadows boost is significant
    assert lut_ds.table[3] > 0.0625
    # Near highlight (index 15 -> r=0.9375), deep shadows boost is negligible
    idx_high = 15 * 3
    assert lut_ds.table[idx_high] - 0.9375 < 0.01


def test_lut3d_dark_expansion_effect() -> None:
    lut_std = Lut3D(size=17)
    lut_std.gamma = 1.5
    lut_std.dark_expansion = 1.0
    lut_std.recompute()

    lut_exp = Lut3D(size=17)
    lut_exp.gamma = 1.5
    lut_exp.dark_expansion = 2.0
    lut_exp.recompute()

    # With higher dark expansion, dark tones should be brighter
    assert lut_exp.table[3] > lut_std.table[3]
    # Pure black stays 0 for both
    assert lut_std.table[0] == 0.0
    assert lut_exp.table[0] == 0.0
    # Peak white stays 1.0
    assert lut_std.table[-1] == 1.0
    assert lut_exp.table[-1] == 1.0

