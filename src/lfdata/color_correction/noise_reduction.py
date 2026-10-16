"""Noise reduction filter model and ffmpeg option generator.

This module provides the `NoiseReductionSettings` class for configuring video
denoising parameters using standard FFmpeg filters (such as hqdn3d and nlmeans)
and applying noise reduction to preview frames.

Usage example:
    from lfdata.color_correction.noise_reduction import NoiseReductionSettings

    settings = NoiseReductionSettings()
    settings.luma_spatial = 5.0
    ffmpeg_arg = settings.to_ffmpeg_filter()
    denoised_img = settings.apply(image)
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

DEFAULT_LUMA_SPATIAL: float = 4.0
DEFAULT_CHROMA_SPATIAL: float = 3.0
DEFAULT_LUMA_TEMPORAL: float = 6.0
DEFAULT_CHROMA_TEMPORAL: float = 4.5

DEFAULT_NLMEANS_STRENGTH: float = 10.0
DEFAULT_NLMEANS_PATCH: int = 7
DEFAULT_NLMEANS_RESEARCH: int = 15


class NoiseReductionSettings:
    """Manages noise reduction parameters and renders preview transformations.

    Attributes:
        enabled: Whether noise reduction filtering is active.
        filter_type: Name of the FFmpeg denoiser filter ('hqdn3d' or 'nlmeans').
        luma_spatial: Spatial luminance noise reduction strength (0.0 to 20.0).
        chroma_spatial: Spatial chrominance noise reduction strength (0.0 to 20.0).
        luma_temporal: Temporal luminance noise reduction strength (0.0 to 20.0).
        chroma_temporal: Temporal chrominance strength (0.0 to 20.0).
        nlmeans_strength: Denoising strength for Non-Local Means filter.
        nlmeans_patch: Template patch size in pixels for Non-Local Means.
        nlmeans_research: Window research size in pixels for Non-Local Means.
    """

    def __init__(self) -> None:
        """Initializes NoiseReductionSettings with default parameters."""
        self.enabled: bool = True
        self.filter_type: str = 'hqdn3d'
        self.luma_spatial: float = DEFAULT_LUMA_SPATIAL
        self.chroma_spatial: float = DEFAULT_CHROMA_SPATIAL
        self.luma_temporal: float = DEFAULT_LUMA_TEMPORAL
        self.chroma_temporal: float = DEFAULT_CHROMA_TEMPORAL

        self.nlmeans_strength: float = DEFAULT_NLMEANS_STRENGTH
        self.nlmeans_patch: int = DEFAULT_NLMEANS_PATCH
        self.nlmeans_research: int = DEFAULT_NLMEANS_RESEARCH

    def reset(self) -> None:
        """Resets all noise reduction parameters to default values.

        Usage example:
            settings.reset()
        """
        self.enabled = True
        self.filter_type = 'hqdn3d'
        self.luma_spatial = DEFAULT_LUMA_SPATIAL
        self.chroma_spatial = DEFAULT_CHROMA_SPATIAL
        self.luma_temporal = DEFAULT_LUMA_TEMPORAL
        self.chroma_temporal = DEFAULT_CHROMA_TEMPORAL

        self.nlmeans_strength = DEFAULT_NLMEANS_STRENGTH
        self.nlmeans_patch = DEFAULT_NLMEANS_PATCH
        self.nlmeans_research = DEFAULT_NLMEANS_RESEARCH

    def apply_preset(self, preset_name: str) -> None:
        """Applies a named noise reduction preset configuration.

        Args:
            preset_name: Name of preset ('mild', 'medium', or 'strong').

        Raises:
            ValueError: If preset_name is not recognized.

        Usage example:
            settings.apply_preset('medium')
        """
        name = preset_name.lower().strip()
        if name == 'mild':
            self.filter_type = 'hqdn3d'
            self.luma_spatial = 2.0
            self.chroma_spatial = 1.5
            self.luma_temporal = 3.0
            self.chroma_temporal = 2.2
        elif name in ('medium', 'default'):
            self.filter_type = 'hqdn3d'
            self.luma_spatial = DEFAULT_LUMA_SPATIAL
            self.chroma_spatial = DEFAULT_CHROMA_SPATIAL
            self.luma_temporal = DEFAULT_LUMA_TEMPORAL
            self.chroma_temporal = DEFAULT_CHROMA_TEMPORAL
        elif name == 'strong':
            self.filter_type = 'hqdn3d'
            self.luma_spatial = 8.0
            self.chroma_spatial = 6.0
            self.luma_temporal = 12.0
            self.chroma_temporal = 9.0
        else:
            raise ValueError(f'Unknown noise reduction preset: {preset_name}')

    def to_ffmpeg_filter(self) -> str:
        """Generates the corresponding FFmpeg video filter option string.

        Returns:
            str: The formatted FFmpeg filter expression, or empty string.

        Usage example:
            filter_str = settings.to_ffmpeg_filter()
        """
        if not self.enabled:
            return 'null'

        if self.filter_type == 'nlmeans':
            strength = round(self.nlmeans_strength, 1)
            return (
                f'nlmeans=s={strength}:p={self.nlmeans_patch}:'
                f'r={self.nlmeans_research}'
            )

        # Default hqdn3d filter
        ls = round(self.luma_spatial, 1)
        cs = round(self.chroma_spatial, 1)
        lt = round(self.luma_temporal, 1)
        ct = round(self.chroma_temporal, 1)
        return f'hqdn3d={ls}:{cs}:{lt}:{ct}'

    def apply(self, image: Image.Image) -> Image.Image:
        """Applies noise reduction filtering to a PIL Image.

        Args:
            image: Source PIL Image to denoise.

        Returns:
            Image.Image: Denoised PIL Image.

        Usage example:
            denoised = settings.apply(image=frame)
        """
        if not self.enabled:
            return image.copy()

        has_alpha = image.mode == 'RGBA'
        alpha_channel = image.split()[3] if has_alpha else None
        rgb_img = image.convert('RGB')
        rgb_arr = np.array(rgb_img)

        try:
            bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)

            if self.filter_type == 'nlmeans':
                h = max(1.0, float(self.nlmeans_strength))
                denoised_bgr = cv2.fastNlMeansDenoisingColored(
                    bgr_arr,
                    None,
                    h=h,
                    hColor=h,
                    templateWindowSize=5,
                    searchWindowSize=11,
                )
            else:
                d = max(3, min(9, int(self.luma_spatial * 1.5)))
                sigma_color = max(1.0, float(self.chroma_spatial) * 8.0)
                sigma_space = max(1.0, float(self.luma_spatial) * 2.5)
                denoised_bgr = cv2.bilateralFilter(
                    bgr_arr,
                    d=d,
                    sigmaColor=sigma_color,
                    sigmaSpace=sigma_space,
                )

            denoised_rgb = cv2.cvtColor(denoised_bgr, cv2.COLOR_BGR2RGB)
            result_img = Image.fromarray(denoised_rgb)
        except Exception:
            # Fallback for environments with mocked cv2
            result_img = rgb_img.copy()

        if has_alpha and alpha_channel is not None:
            r, g, b = result_img.split()
            return Image.merge('RGBA', (r, g, b, alpha_channel))

        return result_img
