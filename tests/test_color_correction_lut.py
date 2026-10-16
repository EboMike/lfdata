"""Unit tests for 3D Look-Up Table (Lut3D) color grading model."""

from __future__ import annotations

import tempfile
from pathlib import Path
from PIL import Image

from lfdata.color_correction.lut import Lut3D


def test_lut3d_default_initialization() -> None:
    lut = Lut3D(size=4)
    assert lut.size == 4
    assert lut.title == 'Identity'
    assert lut.brightness == 0.0
    assert lut.contrast == 1.0
    assert lut.saturation == 1.0
    assert lut.temperature == 0.0
    assert lut.tint == 0.0
    assert len(lut.table) == 4 * 4 * 4 * 3
    assert len(lut.base_table) == len(lut.table)


def test_lut3d_reset_to_identity() -> None:
    lut = Lut3D(size=3)
    lut.brightness = 0.25
    lut.contrast = 1.4
    lut.saturation = 0.8
    lut.temperature = -0.3
    lut.tint = 0.5
    lut.recompute()

    lut.reset_to_identity()
    assert lut.brightness == 0.0
    assert lut.contrast == 1.0
    assert lut.saturation == 1.0
    assert lut.temperature == 0.0
    assert lut.tint == 0.0
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
