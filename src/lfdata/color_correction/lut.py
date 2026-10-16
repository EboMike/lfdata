"""3D Color Look-Up Table (LUT) loading, manipulation, and rendering.

This module provides the `Lut3D` class for managing 3D color lookup tables,
parsing and serializing Adobe `.cube` files, adjusting basic color grading
parameters (brightness, contrast, saturation, temperature, tint), and
applying color transformations to images.

Usage example:
    from lfdata.color_correction.lut import Lut3D

    lut = Lut3D()
    lut.brightness = 0.1
    lut.saturation = 1.2
    lut.recompute()
    filtered_img = lut.apply(image)
"""

from __future__ import annotations

import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

DEFAULT_LUT_SIZE: int = 17


class Lut3D:
    """Manages a 3D Look-Up Table with color grading parameter adjustments.

    Attributes:
        size: Size of the 3D cube along each dimension (e.g. 17 or 33).
        title: Descriptive title string stored in .cube metadata.
        brightness: Brightness offset parameter in range [-1.0, 1.0].
        contrast: Contrast multiplier parameter in range [0.0, 2.0].
        saturation: Saturation multiplier parameter in range [0.0, 2.0].
        temperature: Warm/cool color temperature bias in range [-1.0, 1.0].
        tint: Green/magenta color tint bias in range [-1.0, 1.0].
        base_table: Flat float list of base RGB values before adjustments.
        table: Flat float list of active RGB values after adjustments.
    """

    def __init__(self, size: int = DEFAULT_LUT_SIZE) -> None:
        """Initializes a Lut3D instance with an identity color table.

        Args:
            size: Dimension size of the 3D LUT (default 17).
        """
        self.size: int = size
        self.title: str = 'Identity'
        self.brightness: float = 0.0
        self.contrast: float = 1.0
        self.saturation: float = 1.0
        self.temperature: float = 0.0
        self.tint: float = 0.0

        self.base_table: list[float] = []
        self.table: list[float] = []
        self._filter_cache: ImageFilter.Color3DLUT | None = None

        self.reset_to_identity()

    def reset_to_identity(self) -> None:
        """Resets the base table and grading parameters to identity values.

        Usage example:
            lut.reset_to_identity()
        """
        self.title = 'Identity'
        self.brightness = 0.0
        self.contrast = 1.0
        self.saturation = 1.0
        self.temperature = 0.0
        self.tint = 0.0

        n = self.size
        total_points = n * n * n
        base: list[float] = [0.0] * (total_points * 3)

        idx = 0
        step = 1.0 / (n - 1) if n > 1 else 1.0
        for b_idx in range(n):
            b_val = b_idx * step
            for g_idx in range(n):
                g_val = g_idx * step
                for r_idx in range(n):
                    r_val = r_idx * step
                    base[idx] = r_val
                    base[idx + 1] = g_val
                    base[idx + 2] = b_val
                    idx += 3

        self.base_table = base
        self.recompute()

    def reset_adjustments(self) -> None:
        """Resets the adjustment parameters to neutral while keeping base LUT.

        Usage example:
            lut.reset_adjustments()
        """
        self.brightness = 0.0
        self.contrast = 1.0
        self.saturation = 1.0
        self.temperature = 0.0
        self.tint = 0.0
        self.recompute()

    def recompute(self) -> None:
        """Recomputes active table values from base table and grading parameters.

        Applies brightness, contrast, saturation, temperature, and tint
        adjustments across all LUT entries.

        Usage example:
            lut.recompute()
        """
        base_arr = np.array(self.base_table, dtype=np.float32).reshape(-1, 3)

        # 1. Brightness
        r = base_arr[:, 0] + self.brightness
        g = base_arr[:, 1] + self.brightness
        b = base_arr[:, 2] + self.brightness

        # 2. Contrast around 0.5 midpoint
        if self.contrast != 1.0:
            r = (r - 0.5) * self.contrast + 0.5
            g = (g - 0.5) * self.contrast + 0.5
            b = (b - 0.5) * self.contrast + 0.5

        # 3. Saturation (Rec. 709 luminance)
        if self.saturation != 1.0:
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            r = lum + self.saturation * (r - lum)
            g = lum + self.saturation * (g - lum)
            b = lum + self.saturation * (b - lum)

        # 4. Temperature (Warm shifts red up and blue down, cool opposite)
        if self.temperature != 0.0:
            temp_shift = self.temperature * 0.15
            r = r + temp_shift
            b = b - temp_shift

        # 5. Tint (Magenta shifts green down and red/blue up, green opposite)
        if self.tint != 0.0:
            tint_shift = self.tint * 0.15
            g = g - tint_shift
            r = r + tint_shift * 0.5
            b = b + tint_shift * 0.5

        # Clamp all values to valid [0.0, 1.0] range
        out_arr = np.clip(np.stack([r, g, b], axis=-1), 0.0, 1.0)
        self.table = out_arr.flatten().tolist()
        self._filter_cache = None

    def to_color3dlut(self) -> ImageFilter.Color3DLUT:
        """Returns a PIL ImageFilter.Color3DLUT instance for image filtering.

        Returns:
            ImageFilter.Color3DLUT: Configured Pillow 3D LUT filter.

        Usage example:
            filter_lut = lut.to_color3dlut()
        """
        if self._filter_cache is None:
            self._filter_cache = ImageFilter.Color3DLUT(self.size, self.table)
        return self._filter_cache

    def apply(self, image: Image.Image) -> Image.Image:
        """Applies the current 3D LUT transformation to a PIL Image.

        Args:
            image: Source RGB or RGBA PIL Image.

        Returns:
            Image.Image: Filtered PIL Image with color correction applied.

        Usage example:
            corrected = lut.apply(image=raw_frame)
        """
        lut_filter = self.to_color3dlut()
        if image.mode != 'RGB':
            rgb_image = image.convert('RGB')
            filtered_rgb = rgb_image.filter(lut_filter)
            if image.mode == 'RGBA':
                r, g, b = filtered_rgb.split()
                alpha = image.split()[3]
                return Image.merge('RGBA', (r, g, b, alpha))
            return filtered_rgb
        return image.filter(lut_filter)

    def apply_to_image(self, image: Image.Image) -> Image.Image:
        """Applies the current 3D LUT transformation to a PIL Image.

        Args:
            image: Source RGB or RGBA PIL Image.

        Returns:
            Image.Image: Filtered PIL Image with color correction applied.

        Usage example:
            corrected = lut.apply_to_image(image=raw_frame)
        """
        return self.apply(image=image)

    def to_cube_text(self, title: str | None = None) -> str:
        """Serializes active LUT values to Adobe .cube format string.

        Args:
            title: Optional title string to write into .cube header.

        Returns:
            str: Serialized .cube text representation.

        Usage example:
            cube_str = lut.to_cube_text()
        """
        out_title = title if title is not None else self.title
        lines: list[str] = [
            '# Created by LF Color Correction Editor',
            f'TITLE "{out_title}"',
            f'LUT_3D_SIZE {self.size}',
            'DOMAIN_MIN 0.0 0.0 0.0',
            'DOMAIN_MAX 1.0 1.0 1.0',
        ]

        idx = 0
        total_points = self.size * self.size * self.size
        for _ in range(total_points):
            r_val = self.table[idx]
            g_val = self.table[idx + 1]
            b_val = self.table[idx + 2]
            lines.append(f'{r_val:.6f} {g_val:.6f} {b_val:.6f}')
            idx += 3

        return '\n'.join(lines) + '\n'

    def from_cube_text(self, text: str) -> None:
        """Parses Adobe .cube text and initializes base LUT table values.

        Args:
            text: Contents of an Adobe .cube file.

        Raises:
            ValueError: If the format is invalid or missing dimensions.

        Usage example:
            lut.from_cube_text(cube_data)
        """
        lines = text.splitlines()
        lut_size: int | None = None
        title_str: str = 'CubeLUT'
        data_rows: list[float] = []

        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith('#'):
                continue

            parts = line_str.split()
            tag = parts[0].upper()

            if tag == 'TITLE':
                title_str = line_str[5:].strip().strip('"')
            elif tag == 'LUT_3D_SIZE':
                lut_size = int(parts[1])
            elif tag in ('LUT_1D_SIZE', 'DOMAIN_MIN', 'DOMAIN_MAX'):
                continue
            else:
                if len(parts) >= 3:
                    try:
                        r_f = float(parts[0])
                        g_f = float(parts[1])
                        b_f = float(parts[2])
                        data_rows.extend([r_f, g_f, b_f])
                    except ValueError:
                        continue

        if lut_size is None:
            total_triplets = len(data_rows) // 3
            cbrt = round(total_triplets ** (1.0 / 3.0))
            if cbrt * cbrt * cbrt == total_triplets and cbrt > 1:
                lut_size = cbrt
            else:
                raise ValueError('Invalid or unsupported .cube format.')

        expected_count = lut_size * lut_size * lut_size * 3
        if len(data_rows) < expected_count:
            raise ValueError(
                f'Incomplete .cube data: expected {expected_count} values, '
                f'found {len(data_rows)}'
            )

        self.size = lut_size
        self.title = title_str
        self.base_table = [
            max(0.0, min(1.0, float(v))) for v in data_rows[:expected_count]
        ]
        self.reset_adjustments()

    def load_cube(self, file_path: str | Path) -> None:
        """Parses an Adobe .cube file and initializes base LUT table values.

        Supports standard 3D CUBE format definitions with arbitrary dimensions.

        Args:
            file_path: Path to the .cube file on disk.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file format is invalid or missing dimensions.

        Usage example:
            lut.load_cube('grading.cube')
        """
        path_obj = Path(file_path)
        if not path_obj.exists():
            raise FileNotFoundError(f'LUT file not found: {file_path}')

        with open(path_obj, encoding='utf-8') as f:
            content = f.read()

        self.from_cube_text(text=content)
        if self.title == 'CubeLUT':
            self.title = path_obj.stem

    def load_cube_file(self, file_path: str | Path) -> None:
        """Loads an Adobe .cube file from disk.

        Args:
            file_path: Path to the .cube file on disk.

        Usage example:
            lut.load_cube_file(file_path=Path('sample.cube'))
        """
        self.load_cube(file_path=file_path)

    def save_cube(
        self, file_path: str | Path, title: str | None = None
    ) -> None:
        """Serializes active LUT values to an Adobe .cube file.

        Args:
            file_path: Destination path for the saved .cube file.
            title: Optional title string to write into .cube metadata header.

        Usage example:
            lut.save_cube('custom.cube')
        """
        path_obj = Path(file_path)
        content = self.to_cube_text(title=title)
        with open(path_obj, 'w', encoding='utf-8') as f:
            f.write(content)

    def save_cube_file(
        self, file_path: str | Path, title: str | None = None
    ) -> None:
        """Saves active LUT values to an Adobe .cube file.

        Args:
            file_path: Destination path for the saved .cube file.
            title: Optional title string to write into .cube metadata header.

        Usage example:
            lut.save_cube_file(file_path=Path('custom.cube'))
        """
        self.save_cube(file_path=file_path, title=title)

    def generate_visualization_image(
        self, width: int = 272, height: int = 64
    ) -> Image.Image:
        """Generates a visual 2D strip preview representing the 3D LUT mapping.

        Constructs an image composed of horizontal slices corresponding to
        varying Blue values across the spectrum with Red on the X axis and
        Green on the Y axis.

        Args:
            width: Pixel width of the generated visualization image.
            height: Pixel height of the generated visualization image.

        Returns:
            Image.Image: Rendered RGB preview image of the LUT color space.

        Usage example:
            vis_img = lut.generate_visualization_image(width=256, height=64)
        """
        slices_count = 16
        slice_w = max(1, width // slices_count)
        img_arr = np.zeros((height, width, 3), dtype=np.uint8)

        # Generate base slices
        for s_idx in range(slices_count):
            x_start = s_idx * slice_w
            x_end = min(width, (s_idx + 1) * slice_w)
            curr_w = x_end - x_start
            if curr_w <= 0:
                continue

            b_coord = s_idx / (slices_count - 1)
            r_coords = np.linspace(0.0, 1.0, curr_w, endpoint=True)
            g_coords = np.linspace(1.0, 0.0, height, endpoint=True)

            grid_r, grid_g = np.meshgrid(r_coords, g_coords)
            grid_b = np.full_like(grid_r, b_coord)

            slice_pixels = (
                np.stack([grid_r, grid_g, grid_b], axis=-1) * 255.0
            ).astype(np.uint8)
            img_arr[:, x_start:x_end, :] = slice_pixels

        base_img = Image.fromarray(img_arr, mode='RGB')
        return self.apply(base_img)
