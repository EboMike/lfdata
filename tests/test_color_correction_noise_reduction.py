"""Tests for NoiseReductionSettings model and filter generators."""

from __future__ import annotations

import pytest
from PIL import Image

from lfdata.color_correction.noise_reduction import (
    DEFAULT_CHROMA_SPATIAL,
    DEFAULT_CHROMA_TEMPORAL,
    DEFAULT_LUMA_SPATIAL,
    DEFAULT_LUMA_TEMPORAL,
    DEFAULT_NLMEANS_PATCH,
    DEFAULT_NLMEANS_RESEARCH,
    DEFAULT_NLMEANS_STRENGTH,
    NoiseReductionSettings,
)


def test_noise_reduction_settings_defaults() -> None:
    settings = NoiseReductionSettings()
    assert settings.enabled is True
    assert settings.filter_type == 'hqdn3d'
    assert settings.luma_spatial == DEFAULT_LUMA_SPATIAL
    assert settings.chroma_spatial == DEFAULT_CHROMA_SPATIAL
    assert settings.luma_temporal == DEFAULT_LUMA_TEMPORAL
    assert settings.chroma_temporal == DEFAULT_CHROMA_TEMPORAL
    assert settings.nlmeans_strength == DEFAULT_NLMEANS_STRENGTH
    assert settings.nlmeans_patch == DEFAULT_NLMEANS_PATCH
    assert settings.nlmeans_research == DEFAULT_NLMEANS_RESEARCH


def test_noise_reduction_settings_reset() -> None:
    settings = NoiseReductionSettings()
    settings.enabled = False
    settings.filter_type = 'nlmeans'
    settings.luma_spatial = 12.0
    settings.chroma_spatial = 9.0
    settings.luma_temporal = 15.0
    settings.chroma_temporal = 11.0
    settings.nlmeans_strength = 20.0
    settings.nlmeans_patch = 9
    settings.nlmeans_research = 21

    settings.reset()

    assert settings.enabled is True
    assert settings.filter_type == 'hqdn3d'
    assert settings.luma_spatial == DEFAULT_LUMA_SPATIAL
    assert settings.chroma_spatial == DEFAULT_CHROMA_SPATIAL
    assert settings.luma_temporal == DEFAULT_LUMA_TEMPORAL
    assert settings.chroma_temporal == DEFAULT_CHROMA_TEMPORAL
    assert settings.nlmeans_strength == DEFAULT_NLMEANS_STRENGTH
    assert settings.nlmeans_patch == DEFAULT_NLMEANS_PATCH
    assert settings.nlmeans_research == DEFAULT_NLMEANS_RESEARCH


def test_noise_reduction_settings_presets() -> None:
    settings = NoiseReductionSettings()

    settings.apply_preset('mild')
    assert settings.filter_type == 'hqdn3d'
    assert settings.luma_spatial == 2.0
    assert settings.chroma_spatial == 1.5
    assert settings.luma_temporal == 3.0
    assert settings.chroma_temporal == 2.2

    settings.apply_preset('strong')
    assert settings.filter_type == 'hqdn3d'
    assert settings.luma_spatial == 8.0
    assert settings.chroma_spatial == 6.0
    assert settings.luma_temporal == 12.0
    assert settings.chroma_temporal == 9.0

    settings.apply_preset('medium')
    assert settings.luma_spatial == DEFAULT_LUMA_SPATIAL
    assert settings.chroma_spatial == DEFAULT_CHROMA_SPATIAL

    settings.apply_preset('default')
    assert settings.luma_spatial == DEFAULT_LUMA_SPATIAL

    with pytest.raises(ValueError, match='Unknown noise reduction preset'):
        settings.apply_preset('nonexistent')


def test_noise_reduction_to_ffmpeg_filter() -> None:
    settings = NoiseReductionSettings()
    assert settings.to_ffmpeg_filter() == 'hqdn3d=4.0:3.0:6.0:4.5'

    settings.luma_spatial = 5.23
    settings.chroma_spatial = 2.87
    settings.luma_temporal = 7.12
    settings.chroma_temporal = 3.94
    assert settings.to_ffmpeg_filter() == 'hqdn3d=5.2:2.9:7.1:3.9'

    settings.filter_type = 'nlmeans'
    settings.nlmeans_strength = 12.55
    settings.nlmeans_patch = 7
    settings.nlmeans_research = 15
    assert settings.to_ffmpeg_filter() == 'nlmeans=s=12.6:p=7:r=15'

    settings.enabled = False
    assert settings.to_ffmpeg_filter() == 'null'


def test_noise_reduction_apply_hqdn3d() -> None:
    settings = NoiseReductionSettings()
    img = Image.new('RGB', (64, 64), color=(100, 150, 200))
    result = settings.apply(image=img)
    assert result.size == (64, 64)
    assert result.mode == 'RGB'


def test_noise_reduction_apply_rgba() -> None:
    settings = NoiseReductionSettings()
    img = Image.new('RGBA', (32, 32), color=(50, 80, 120, 180))
    result = settings.apply(image=img)
    assert result.size == (32, 32)
    assert result.mode == 'RGBA'
    assert result.split()[3].getextrema() == (180, 180)


def test_noise_reduction_apply_nlmeans() -> None:
    settings = NoiseReductionSettings()
    settings.filter_type = 'nlmeans'
    settings.nlmeans_strength = 8.0
    img = Image.new('RGB', (32, 32), color=(120, 100, 80))
    result = settings.apply(image=img)
    assert result.size == (32, 32)
    assert result.mode == 'RGB'


def test_noise_reduction_apply_disabled() -> None:
    settings = NoiseReductionSettings()
    settings.enabled = False
    img = Image.new('RGB', (20, 20), color=(10, 20, 30))
    result = settings.apply(image=img)
    assert result.size == (20, 20)
    assert list(result.tobytes()) == list(img.tobytes())
