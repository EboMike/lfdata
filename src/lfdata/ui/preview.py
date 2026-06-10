"""Image preview and playback control panel for the LF data UI."""

import subprocess
import tempfile
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageTk
from lfdata.ui.config_manager import UIConfigManager


class ImagePreview(ttk.LabelFrame):
    """Panel for controls, slider, and the rendered game state image."""

    def __init__(
        self,
        parent: tk.Widget,
        config_manager: UIConfigManager,
    ) -> None:
        """Initializes the image preview panel.

        Args:
            parent: The parent tkinter widget.
            config_manager: The configuration manager instance.
        """
        super().__init__(parent, text=' Rendered Preview ')
        self.config_manager = config_manager
        self.current_time_ms = 0

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Creates control buttons, slider, and preview image widgets."""
        # Top control bar
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(ctrl_frame, text='Player Focus:').pack(side='left', padx=2)
        self.player_var = tk.StringVar(value='None')
        self.cmb_player = ttk.Combobox(
            ctrl_frame,
            textvariable=self.player_var,
            state='readonly',
            width=20,
        )
        self.cmb_player.pack(side='left', padx=5)
        self.cmb_player.bind('<<ComboboxSelected>>', self._on_player_changed)

        self.btn_refresh = ttk.Button(
            ctrl_frame, text='Refresh Preview', command=self.update_preview
        )
        self.btn_refresh.pack(side='right', padx=5)

        self.lbl_time = ttk.Label(ctrl_frame, text='Time: 0 ms (00:00)')
        self.lbl_time.pack(side='right', padx=10)

        # Slider bar
        self.slider_var = tk.DoubleVar(value=0.0)
        self.slider = ttk.Scale(
            self,
            from_=0.0,
            to=100.0,
            orient='horizontal',
            variable=self.slider_var,
            command=self._on_slider_move,
        )
        self.slider.pack(fill='x', padx=10, pady=5)
        self.slider.bind('<ButtonRelease-1>', lambda e: self.update_preview())

        # Image display container
        self.img_frame = ttk.Frame(
            self,
            width=640,
            height=360,
            style='Preview.TFrame',
        )
        self.img_frame.pack(fill='both', expand=True, padx=5, pady=5)
        self.img_frame.pack_propagate(False)

        self.last_rendered_image: Image.Image | None = None
        self.img_frame.bind('<Configure>', self._on_frame_configure)

        self.lbl_image = ttk.Label(
            self.img_frame,
            text='Please load a TDF file to enable preview.',
            anchor='center',
        )
        self.lbl_image.pack(fill='both', expand=True)

    def on_tdf_loaded(self) -> None:
        """Updates slider range and player dropdown options when TDF loads."""
        players = ['None'] + self.config_manager.get_player_names()
        self.cmb_player['values'] = players
        self.player_var.set('None')

        duration_ms = 0
        if self.config_manager.game:
            duration_ms = self.config_manager.game.duration or 0

        # Max end time is duration plus config margins
        extra_ms = self.config_manager.config.get('extra_footage_ms', 10000)
        pregame_ms = self.config_manager.config.get('pregame_delay_ms', 0)
        max_ms = duration_ms + extra_ms + pregame_ms

        self.slider.config(to=float(max_ms))
        self.slider_var.set(0.0)
        self.current_time_ms = 0
        self._update_time_label(0)
        self.update_preview()

    def _on_player_changed(self, event: tk.Event) -> None:
        """Triggers updates when focused player is changed.

        Args:
            event: The combobox select event.
        """
        self.update_preview()

    def _on_slider_move(self, val: str) -> None:
        """Handles slider moves to update label without triggering heavy render.

        Args:
            val: The current slider value as string.
        """
        val_ms = int(float(val))
        self.current_time_ms = val_ms
        self._update_time_label(val_ms)

    def _update_time_label(self, time_ms: int) -> None:
        """Formats and sets the text for the time indicator label.

        Args:
            time_ms: The timestamp in milliseconds.
        """
        total_sec = time_ms // 1000
        min_part = total_sec // 60
        sec_part = total_sec % 60
        self.lbl_time.config(
            text=f'Time: {time_ms:,} ms ({min_part:02d}:{sec_part:02d})'
        )

    def update_preview(self) -> None:
        """Runs lfdata in a subprocess to render current frame and displays it."""
        if not self.config_manager.tdf_path:
            self.lbl_image.config(
                text='Please load a TDF file to enable preview.'
            )
            return

        self.lbl_image.config(text='Rendering frame, please wait...')
        self.update_idletasks()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cfg_path = temp_path / 'temp_config.yaml'
            self.config_manager.save_config(str(cfg_path))

            # Run lfdata CLI subprocess to render the image
            cmd = self.config_manager.get_lfdata_command() + [
                '--input_tdf',
                self.config_manager.tdf_path,
                '--config',
                str(cfg_path),
                '--image-outdir',
                str(temp_path),
                '--image-at',
                str(self.current_time_ms),
            ]

            p_focus = self.player_var.get()
            if p_focus and p_focus != 'None':
                cmd.extend(['--video_player', p_focus])

            try:
                subprocess.run(cmd, check=True, capture_output=True)
                img_file = temp_path / f'image_at_{self.current_time_ms}.png'
                if img_file.exists():
                    self._display_image(img_file)
                else:
                    self.lbl_image.config(text='Error: Preview file not found.')
            except Exception as e:
                self.lbl_image.config(text=f'Failed to render: {e}')

    def _display_image(self, path: Path) -> None:
        """Loads and draws the preview image from a path.

        Args:
            path: The filesystem path to the PNG image.
        """
        try:
            with Image.open(path) as raw_img:
                # Store a copy in memory for resizing (fallback if copy is mocked)
                try:
                    copied = raw_img.copy()
                    if not isinstance(getattr(copied, 'size', None), tuple):
                        self.last_rendered_image = raw_img
                    else:
                        self.last_rendered_image = copied
                except Exception:
                    self.last_rendered_image = raw_img
                self._show_image(self.last_rendered_image)
        except Exception as e:
            self.lbl_image.config(text=f'Error displaying image: {e}')

    def _show_image(self, raw_img: Image.Image) -> None:
        """Resizes and displays the PIL image on the label.

        Args:
            raw_img: The PIL image object.
        """
        canvas_w = 640
        canvas_h = 360
        if hasattr(self.img_frame, 'winfo_width'):
            w = self.img_frame.winfo_width()
            if w > 1:
                canvas_w = w
        if hasattr(self.img_frame, 'winfo_height'):
            h = self.img_frame.winfo_height()
            if h > 1:
                canvas_h = h

        img_w, img_h = raw_img.size

        ratio = min(canvas_w / img_w, canvas_h / img_h)
        new_w = int(img_w * ratio)
        new_h = int(img_h * ratio)

        resized = raw_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(resized)

        self.lbl_image.config(image=photo, text='')
        # Keep reference to avoid garbage collection
        self.lbl_image.image = photo

    def _on_frame_configure(self, event: tk.Event) -> None:
        """Handles container resizing to upscale/downscale the preview image.

        Args:
            event: The configuration event.
        """
        if self.last_rendered_image:
            self._show_image(self.last_rendered_image)
