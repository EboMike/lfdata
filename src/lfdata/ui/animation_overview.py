"""Animation timeline graph and keyframe editor panel."""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from lfdata.ui.config_manager import UIConfigManager
from lfdata.video.helpers import resolve_animated_value


class AnimationOverviewPanel(ttk.LabelFrame):
    """Panel for visualizing keyframes and editing their references/interpolators."""

    def __init__(
        self,
        parent: tk.Widget,
        config_manager: UIConfigManager,
        on_keyframe_changed: Callable[[], None] | None = None,
    ) -> None:
        """Initializes the AnimationOverviewPanel.

        Args:
            parent: The parent tkinter widget.
            config_manager: The configuration manager instance.
            on_keyframe_changed: Optional callback when keyframes are modified.
        """
        super().__init__(parent, text=' Animation Overview ')
        self.config_manager = config_manager
        self.on_keyframe_changed = on_keyframe_changed
        self.element_name: str | None = None
        self.selected_kf_idx: int | None = None

        # Control vars
        self.prop_var = tk.StringVar()
        self.ref_var = tk.StringVar()
        self.interp_var = tk.StringVar()

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Creates the layout widgets for the animation overview."""
        # Top frame for property selector
        top_frame = ttk.Frame(self)
        top_frame.pack(fill='x', padx=5, pady=2)

        ttk.Label(top_frame, text='Property:').pack(side='left', padx=2)
        self.cmb_prop = ttk.Combobox(
            top_frame,
            textvariable=self.prop_var,
            state='readonly',
            width=20,
        )
        self.cmb_prop.pack(side='left', padx=5)
        self.cmb_prop.bind('<<ComboboxSelected>>', self._on_property_selected)

        # Canvas for timeline plot
        self.canvas = tk.Canvas(
            self,
            height=130,
            bg='#18181b',
            highlightthickness=1,
            highlightbackground='#27272a',
        )
        self.canvas.pack(fill='both', expand=True, padx=5, pady=5)
        self.canvas.bind('<Configure>', lambda e: self.refresh())
        self.canvas.bind('<Button-1>', self._on_canvas_click)

        # Bottom frame for keyframe details & editing
        self.edit_frame = ttk.Frame(self)
        self.edit_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(self.edit_frame, text='Ref:').pack(side='left', padx=2)
        self.cmb_ref = ttk.Combobox(
            self.edit_frame,
            textvariable=self.ref_var,
            values=['start_of_video', 'start_of_game', 'end_of_game'],
            state='readonly',
            width=14,
        )
        self.cmb_ref.pack(side='left', padx=2)
        self.cmb_ref.bind('<<ComboboxSelected>>', self._on_ref_changed)

        ttk.Label(self.edit_frame, text='Interp:').pack(side='left', padx=5)
        self.cmb_interp = ttk.Combobox(
            self.edit_frame,
            textvariable=self.interp_var,
            values=['linear', 'ease-in', 'ease-out', 'ease-in-out'],
            state='readonly',
            width=11,
        )
        self.cmb_interp.pack(side='left', padx=2)
        self.cmb_interp.bind('<<ComboboxSelected>>', self._on_interp_changed)

        self.btn_delete = ttk.Button(
            self.edit_frame,
            text='Delete',
            width=8,
            command=self._on_delete_click,
        )
        self.btn_delete.pack(side='right', padx=2)

        self._update_edit_state()

    def load_element(self, element_name: str | None) -> None:
        """Loads a UI element to display its keyframes.

        Args:
            element_name: The name of the UI element.
        """
        self.element_name = element_name
        self.selected_kf_idx = None

        if not element_name:
            self.cmb_prop['values'] = []
            self.prop_var.set('')
            self.refresh()
            return

        el = self.config_manager.get_element(element_name)
        if not el:
            self.cmb_prop['values'] = []
            self.prop_var.set('')
            self.refresh()
            return

        # Populate supported properties
        options = []
        if 'x' in el:
            options.append('x')
        if 'y' in el:
            options.append('y')
        if 'extents' in el:
            options.append('extents (width)')
            options.append('extents (height)')
        if 'size' in el.get('style', {}):
            options.append('size (font size)')
        if 'tilt' in el:
            options.append('tilt')

        self.cmb_prop['values'] = options
        if options:
            self.prop_var.set(options[0])

        self.refresh()

    def select_property(self, prop: str) -> None:
        """Selects a property to display in the overview graph programmatically.

        Args:
            prop: The property key (e.g. 'x', 'y', 'extents', 'size', 'tilt').
        """
        mapping = {
            'x': 'x',
            'y': 'y',
            'extents_w': 'extents (width)',
            'extents_h': 'extents (height)',
            'extents': 'extents (width)',
            'size': 'size (font size)',
            'tilt': 'tilt',
        }
        mapped = mapping.get(prop, prop)
        if mapped in self.cmb_prop['values']:
            self.prop_var.set(mapped)
            self.selected_kf_idx = None
            self.refresh()

    def refresh(self) -> None:
        """Redraws the timeline canvas and updates editing widgets."""
        self.canvas.delete('all')
        self._update_edit_state()
        if not self.element_name:
            return

        keyframes = self._get_keyframes_list()
        if not keyframes:
            return

        # Compute limits
        width = max(100, self.canvas.winfo_width())
        height = max(50, self.canvas.winfo_height())
        pad_x = 20
        pad_y = 15

        duration_ms = 0
        if self.config_manager.game:
            duration_ms = self.config_manager.game.duration or 0

        extra_ms = self.config_manager.config.get('extra_footage_ms', 10000)
        pregame_ms = self.config_manager.config.get('pregame_delay_ms', 0)
        if isinstance(pregame_ms, dict) and 'keyframes' in pregame_ms:
            pregame_ms = resolve_animated_value(
                pregame_ms, self.config_manager.current_time_ms, 0, 0
            )

        max_ms = duration_ms + extra_ms + pregame_ms
        if max_ms <= 0:
            max_ms = 10000

        # Resolve properties mapping
        prop_str = self.prop_var.get()
        prop_key = 'x'
        extents_idx = None
        if prop_str == 'y':
            prop_key = 'y'
        elif prop_str == 'extents (width)':
            prop_key = 'extents'
            extents_idx = 0
        elif prop_str == 'extents (height)':
            prop_key = 'extents'
            extents_idx = 1
        elif prop_str == 'size (font size)':
            prop_key = 'size'
        elif prop_str == 'tilt':
            prop_key = 'tilt'

        # Get values to determine value range
        resolved_vals: list[float] = []
        for kf in keyframes:
            val_raw = kf.get('value')
            if extents_idx is not None:
                if (
                    isinstance(val_raw, (list, tuple))
                    and len(val_raw) > extents_idx
                ):
                    resolved_vals.append(float(val_raw[extents_idx]))
            elif val_raw is not None:
                try:
                    resolved_vals.append(float(val_raw))
                except (ValueError, TypeError):
                    pass

        if not resolved_vals:
            return

        val_min = min(resolved_vals)
        val_max = max(resolved_vals)

        # Set standard minimum ranges
        if prop_key in ('x', 'y', 'extents'):
            val_min = min(0.0, val_min)
            val_max = max(1.0, val_max)
        elif prop_key == 'size':
            val_min = min(0.0, val_min)
            val_max = max(100.0, val_max)
        elif prop_key == 'tilt':
            val_min = min(-10.0, val_min)
            val_max = max(10.0, val_max)

        if val_max == val_min:
            val_min -= 0.5
            val_max += 0.5

        # Draw grid lines
        for i in range(5):
            ratio = i / 4.0
            y_grid = pad_y + ratio * (height - 2 * pad_y)
            self.canvas.create_line(
                pad_x, y_grid, width - pad_x, y_grid, fill='#27272a'
            )
            # Label grid
            grid_val = val_max - ratio * (val_max - val_min)
            self.canvas.create_text(
                pad_x - 5,
                y_grid,
                text=f'{grid_val:.1f}',
                fill='#a1a1aa',
                anchor='e',
                font=('Consolas', 8),
            )

        # Render interpolation line
        steps = 100
        line_points = []
        for step in range(steps + 1):
            t_ms = int((step / float(steps)) * max_ms)
            v = self._get_value_at_time(
                self.element_name, prop_key, extents_idx, t_ms
            )
            if v is not None:
                x_coord = pad_x + (t_ms / float(max_ms)) * (width - 2 * pad_x)
                y_coord = (
                    height
                    - pad_y
                    - ((v - val_min) / (val_max - val_min))
                    * (height - 2 * pad_y)
                )
                line_points.extend([x_coord, y_coord])

        if len(line_points) >= 4:
            self.canvas.create_line(
                line_points, fill='#0ea5e9', width=2, smooth=True
            )

        # Draw current time vertical cursor
        curr_time = self.config_manager.current_time_ms
        cursor_x = pad_x + (curr_time / float(max_ms)) * (width - 2 * pad_x)
        self.canvas.create_line(
            cursor_x, 0, cursor_x, height, fill='#f43f5e', dash=(4, 2)
        )

        # Draw keyframe dots
        for idx, kf in enumerate(keyframes):
            kf_time_ms = kf.get('time', 0)
            ref = kf.get('reference', 'start_of_video')
            ref_clean = ref.strip().lower().replace(' ', '_')

            if ref_clean in ('start_of_game', 'game_start'):
                abs_time_ms = pregame_ms + kf_time_ms
            elif ref_clean in ('end_of_game', 'game_end'):
                abs_time_ms = pregame_ms + duration_ms + kf_time_ms
            else:
                abs_time_ms = kf_time_ms

            val_raw = kf.get('value')
            v = 0.0
            if extents_idx is not None:
                if (
                    isinstance(val_raw, (list, tuple))
                    and len(val_raw) > extents_idx
                ):
                    v = float(val_raw[extents_idx])
            elif val_raw is not None:
                try:
                    v = float(val_raw)
                except (ValueError, TypeError):
                    pass

            x_coord = pad_x + (abs_time_ms / float(max_ms)) * (
                width - 2 * pad_x
            )
            y_coord = (
                height
                - pad_y
                - ((v - val_min) / (val_max - val_min)) * (height - 2 * pad_y)
            )

            is_selected = idx == self.selected_kf_idx
            dot_color = '#ef4444' if is_selected else '#0ea5e9'
            radius = 6 if is_selected else 4

            self.canvas.create_oval(
                x_coord - radius,
                y_coord - radius,
                x_coord + radius,
                y_coord + radius,
                fill=dot_color,
                outline='#ffffff',
                width=1 if is_selected else 0,
            )

    def _get_value_at_time(
        self,
        element_name: str,
        prop: str,
        extents_idx: int | None,
        t_ms: int,
    ) -> float | None:
        """Temporarily sets current_time_ms to evaluate the property at t_ms.

        Args:
            element_name: The name of the UI element.
            prop: The property key.
            extents_idx: Index if the property is a list/tuple.
            t_ms: The timestamp in milliseconds.

        Returns:
            float | None: The resolved property value.
        """
        old_time = self.config_manager.current_time_ms
        self.config_manager.current_time_ms = t_ms
        try:
            el = self.config_manager.get_element(element_name)
            if not el:
                return None
            if prop == 'size':
                val = el.get('style', {}).get('size')
            else:
                val = el.get(prop)

            resolved = self.config_manager.resolve_val(val)
            if resolved is None:
                return None

            if extents_idx is not None:
                if (
                    isinstance(resolved, (list, tuple))
                    and len(resolved) > extents_idx
                ):
                    return float(resolved[extents_idx])
                return None

            return float(resolved)
        except Exception:
            return None
        finally:
            self.config_manager.current_time_ms = old_time

    def _get_keyframes_list(self) -> list[dict[str, Any]] | None:
        """Gets the list of keyframes for the active property.

        Returns:
            list[dict[str, Any]] | None: The active keyframes list.
        """
        if not self.element_name:
            return None
        el = self.config_manager.get_element(self.element_name)
        if not el:
            return None

        prop_str = self.prop_var.get()
        if prop_str == 'x':
            val = el.get('x')
        elif prop_str == 'y':
            val = el.get('y')
        elif prop_str in ('extents (width)', 'extents (height)'):
            val = el.get('extents')
        elif prop_str == 'size (font size)':
            val = el.get('style', {}).get('size')
        elif prop_str == 'tilt':
            val = el.get('tilt')
        else:
            return None

        if isinstance(val, dict) and 'keyframes' in val:
            return val['keyframes']
        return None

    def _on_property_selected(self, event: tk.Event) -> None:
        """Redraws when a different property is selected.

        Args:
            event: The combobox selection event.
        """
        self.selected_kf_idx = None
        self.refresh()

    def _on_canvas_click(self, event: tk.Event) -> None:
        """Selects the keyframe closest to click coordinates.

        Args:
            event: The canvas click event.
        """
        if not self.element_name:
            return

        keyframes = self._get_keyframes_list()
        if not keyframes:
            return

        width = max(100, self.canvas.winfo_width())
        height = max(50, self.canvas.winfo_height())
        pad_x = 20
        pad_y = 15

        duration_ms = 0
        if self.config_manager.game:
            duration_ms = self.config_manager.game.duration or 0

        extra_ms = self.config_manager.config.get('extra_footage_ms', 10000)
        pregame_ms = self.config_manager.config.get('pregame_delay_ms', 0)
        if isinstance(pregame_ms, dict) and 'keyframes' in pregame_ms:
            pregame_ms = resolve_animated_value(
                pregame_ms, self.config_manager.current_time_ms, 0, 0
            )

        max_ms = duration_ms + extra_ms + pregame_ms
        if max_ms <= 0:
            max_ms = 10000

        prop_str = self.prop_var.get()
        prop_key = 'x'
        extents_idx = None
        if prop_str == 'y':
            prop_key = 'y'
        elif prop_str == 'extents (width)':
            prop_key = 'extents'
            extents_idx = 0
        elif prop_str == 'extents (height)':
            prop_key = 'extents'
            extents_idx = 1
        elif prop_str == 'size (font size)':
            prop_key = 'size'
        elif prop_str == 'tilt':
            prop_key = 'tilt'

        resolved_vals = []
        for kf in keyframes:
            val_raw = kf.get('value')
            if extents_idx is not None:
                if (
                    isinstance(val_raw, (list, tuple))
                    and len(val_raw) > extents_idx
                ):
                    resolved_vals.append(float(val_raw[extents_idx]))
            elif val_raw is not None:
                try:
                    resolved_vals.append(float(val_raw))
                except (ValueError, TypeError):
                    pass

        if not resolved_vals:
            return

        val_min = min(resolved_vals)
        val_max = max(resolved_vals)

        if prop_key in ('x', 'y', 'extents'):
            val_min = min(0.0, val_min)
            val_max = max(1.0, val_max)
        elif prop_key == 'size':
            val_min = min(0.0, val_min)
            val_max = max(100.0, val_max)
        elif prop_key == 'tilt':
            val_min = min(-10.0, val_min)
            val_max = max(10.0, val_max)

        if val_max == val_min:
            val_min -= 0.5
            val_max += 0.5

        # Find closest keyframe node (within 10 px radius)
        closest_idx = None
        min_dist = 10.0

        for idx, kf in enumerate(keyframes):
            kf_time_ms = kf.get('time', 0)
            ref = kf.get('reference', 'start_of_video')
            ref_clean = ref.strip().lower().replace(' ', '_')

            if ref_clean in ('start_of_game', 'game_start'):
                abs_time_ms = pregame_ms + kf_time_ms
            elif ref_clean in ('end_of_game', 'game_end'):
                abs_time_ms = pregame_ms + duration_ms + kf_time_ms
            else:
                abs_time_ms = kf_time_ms

            val_raw = kf.get('value')
            v = 0.0
            if extents_idx is not None:
                if (
                    isinstance(val_raw, (list, tuple))
                    and len(val_raw) > extents_idx
                ):
                    v = float(val_raw[extents_idx])
            elif val_raw is not None:
                try:
                    v = float(val_raw)
                except (ValueError, TypeError):
                    pass

            x_coord = pad_x + (abs_time_ms / float(max_ms)) * (
                width - 2 * pad_x
            )
            y_coord = (
                height
                - pad_y
                - ((v - val_min) / (val_max - val_min)) * (height - 2 * pad_y)
            )

            dist = ((event.x - x_coord) ** 2 + (event.y - y_coord) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                closest_idx = idx

        if closest_idx is not None:
            self.selected_kf_idx = closest_idx
            self.refresh()

    def _update_edit_state(self) -> None:
        """Enables/disables keyframe inputs depending on selection."""
        keyframes = self._get_keyframes_list()
        if (
            not keyframes
            or self.selected_kf_idx is None
            or self.selected_kf_idx >= len(keyframes)
        ):
            self.cmb_ref['state'] = tk.DISABLED
            self.cmb_interp['state'] = tk.DISABLED
            self.btn_delete['state'] = tk.DISABLED
            self.ref_var.set('')
            self.interp_var.set('')
            return

        self.cmb_ref['state'] = 'readonly'
        self.cmb_interp['state'] = 'readonly'
        self.btn_delete['state'] = tk.NORMAL

        kf = keyframes[self.selected_kf_idx]
        self.ref_var.set(kf.get('reference', 'start_of_video'))
        self.interp_var.set(kf.get('interpolator', 'linear'))

    def _on_ref_changed(self, event: tk.Event) -> None:
        """Saves Reference changes to active keyframe.

        Args:
            event: The combobox selection event.
        """
        keyframes = self._get_keyframes_list()
        if (
            keyframes
            and self.selected_kf_idx is not None
            and self.selected_kf_idx < len(keyframes)
        ):
            # Update keyframe reference on all related keyframe lists
            # (If extents width/height, they share the list)
            kf = keyframes[self.selected_kf_idx]
            kf['reference'] = self.ref_var.get()
            self.refresh()
            if self.on_keyframe_changed:
                self.on_keyframe_changed()

    def _on_interp_changed(self, event: tk.Event) -> None:
        """Saves Interpolator changes to active keyframe.

        Args:
            event: The combobox selection event.
        """
        keyframes = self._get_keyframes_list()
        if (
            keyframes
            and self.selected_kf_idx is not None
            and self.selected_kf_idx < len(keyframes)
        ):
            kf = keyframes[self.selected_kf_idx]
            kf['interpolator'] = self.interp_var.get()
            self.refresh()
            if self.on_keyframe_changed:
                self.on_keyframe_changed()

    def _on_delete_click(self) -> None:
        """Deletes the selected keyframe and updates layout/timeline."""
        keyframes = self._get_keyframes_list()
        if (
            keyframes
            and self.selected_kf_idx is not None
            and self.selected_kf_idx < len(keyframes)
        ):
            del keyframes[self.selected_kf_idx]
            self.selected_kf_idx = None
            self.refresh()
            if self.on_keyframe_changed:
                self.on_keyframe_changed()
