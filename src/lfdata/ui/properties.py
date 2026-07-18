"""UI element properties editor panel for the LF data UI."""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable
from lfdata.ui.config_manager import UIConfigManager
from lfdata.ui.animation_overview import AnimationOverviewPanel


class PropertiesPanel(ttk.LabelFrame):
    """Panel containing form inputs to edit the selected UI element properties."""

    def __init__(
        self,
        parent: tk.Widget,
        config_manager: UIConfigManager,
        on_update_callback: Callable[[], None],
        **kwargs: Any,
    ) -> None:
        """Initializes the properties panel.

        Args:
            parent: The parent tkinter widget.
            config_manager: The configuration manager instance.
            on_update_callback: Callback triggered when properties are modified.
            **kwargs: Additional keyword arguments for the parent widget.
        """
        super().__init__(parent, text=' UI Element Properties ', **kwargs)
        self.config_manager = config_manager
        self.on_update = on_update_callback
        self.selected_element: str | None = None

        self._create_widgets()
        self.clear()

    def _create_widgets(self) -> None:
        """Creates and layouts the form input widgets."""
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self, orient='vertical', command=self.canvas.yview
        )
        self.container = ttk.Frame(self.canvas)

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.container, anchor='nw'
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)

        self.container.bind(
            '<Configure>',
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox('all')
            ),
        )
        self.canvas.bind(
            '<Configure>',
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width),
        )

        self.canvas.bind(
            '<Enter>',
            lambda e: self.canvas.bind_all(
                '<MouseWheel>',
                lambda ev: (
                    self.canvas.yview_scroll(
                        int(-1 * (ev.delta / 120)), 'units'
                    )
                    if ev.delta
                    else None
                ),
            ),
        )
        self.canvas.bind(
            '<Leave>', lambda e: self.canvas.unbind_all('<MouseWheel>')
        )

        self.container.grid_columnconfigure(1, weight=1)

        self.default_frame = ttk.Frame(self.container)
        self.default_frame.grid(row=1, column=0, columnspan=3, sticky='nsew')
        self.default_frame.grid_columnconfigure(1, weight=1)

        self.hit_border_frame = ttk.LabelFrame(
            self.container, text=' Hit Border Options '
        )
        self.hit_border_frame.grid_columnconfigure(1, weight=1)

        # Variables
        self.x_var = tk.StringVar()
        self.y_var = tk.StringVar()
        self.w_var = tk.StringVar()
        self.h_var = tk.StringVar()
        self.align_var = tk.StringVar()
        self.enabled_var = tk.BooleanVar()
        self.font_var = tk.StringVar()
        self.size_var = tk.StringVar()
        self.tilt_var = tk.StringVar()
        self.start_time_offset_var = tk.StringVar()
        self.end_time_offset_var = tk.StringVar()
        self.start_ms_var = tk.StringVar()
        self.end_ms_var = tk.StringVar()
        self.fade_in_ms_var = tk.StringVar()
        self.fade_out_ms_var = tk.StringVar()
        self.formatted_text_var = tk.StringVar()

        # Hit Border specific variables
        self.hb_dur_hp_var = tk.StringVar()
        self.hb_dur_down_var = tk.StringVar()
        self.hb_max_scale_var = tk.StringVar()
        self.hb_col_zap_var = tk.StringVar()
        self.hb_col_resup_var = tk.StringVar()
        self.hb_col_other_var = tk.StringVar()

        # Animation states checkboxes variables
        self.x_anim_var = tk.BooleanVar()
        self.y_anim_var = tk.BooleanVar()
        self.w_anim_var = tk.BooleanVar()
        self.h_anim_var = tk.BooleanVar()
        self.size_anim_var = tk.BooleanVar()
        self.tilt_anim_var = tk.BooleanVar()

        # Labels and inputs list for clean layout
        row = 0

        # Enabled Checkbox
        ttk.Label(self.container, text='Enabled:').grid(
            row=row, column=0, sticky='w', padx=5, pady=3
        )
        self.chk_enabled = ttk.Checkbutton(
            self.container,
            variable=self.enabled_var,
            command=self._on_check_toggle,
        )
        self.chk_enabled.grid(row=row, column=1, sticky='w', padx=5, pady=3)
        row += 1

        # Coordinates (in default_frame)
        default_row = 0
        self._add_row(
            default_row, 'Anchor X (0-1):', self.x_var, 'x', self.x_anim_var
        )
        default_row += 1
        self._add_row(
            default_row, 'Anchor Y (0-1):', self.y_var, 'y', self.y_anim_var
        )
        default_row += 1
        self._add_row(
            default_row, 'Width Extent:', self.w_var, 'extents', self.w_anim_var
        )
        default_row += 1
        self._add_row(
            default_row,
            'Height Extent:',
            self.h_var,
            'extents',
            self.h_anim_var,
        )
        default_row += 1

        # Alignment
        ttk.Label(self.default_frame, text='Alignment:').grid(
            row=default_row, column=0, sticky='w', padx=5, pady=3
        )
        self.cmb_align = ttk.Combobox(
            self.default_frame,
            textvariable=self.align_var,
            values=['left', 'center', 'right'],
            state='readonly',
        )
        self.cmb_align.grid(
            row=default_row, column=1, sticky='ew', padx=5, pady=3
        )
        self.cmb_align.bind('<<ComboboxSelected>>', self._on_combobox_select)
        default_row += 1

        # Font & Style
        self._add_row(default_row, 'Font Family:', self.font_var)
        default_row += 1
        self._add_row(
            default_row, 'Font Size:', self.size_var, 'size', self.size_anim_var
        )
        default_row += 1
        self._add_row(
            default_row,
            'Tilt (degrees):',
            self.tilt_var,
            'tilt',
            self.tilt_anim_var,
        )
        default_row += 1

        # Timings (in ms)
        ttk.Label(self.default_frame, text='Start Time Offset:').grid(
            row=default_row, column=0, sticky='w', padx=5, pady=3
        )
        self.cmb_start_time_offset = ttk.Combobox(
            self.default_frame,
            textvariable=self.start_time_offset_var,
            values=[
                'beginning of video',
                'beginning of game',
                'end of game',
            ],
            state='readonly',
        )
        self.cmb_start_time_offset.grid(
            row=default_row, column=1, sticky='ew', padx=5, pady=3
        )
        self.cmb_start_time_offset.bind(
            '<<ComboboxSelected>>',
            self._on_start_time_offset_select,
        )
        default_row += 1

        self._add_row(default_row, 'Start Time (ms):', self.start_ms_var)
        default_row += 1

        ttk.Label(self.default_frame, text='End Time Offset:').grid(
            row=default_row, column=0, sticky='w', padx=5, pady=3
        )
        self.cmb_end_time_offset = ttk.Combobox(
            self.default_frame,
            textvariable=self.end_time_offset_var,
            values=[
                'beginning of video',
                'beginning of game',
                'end of game',
            ],
            state='readonly',
        )
        self.cmb_end_time_offset.grid(
            row=default_row, column=1, sticky='ew', padx=5, pady=3
        )
        self.cmb_end_time_offset.bind(
            '<<ComboboxSelected>>',
            self._on_end_time_offset_select,
        )
        default_row += 1

        self._add_row(default_row, 'End Time (ms):', self.end_ms_var)
        default_row += 1
        self._add_row(default_row, 'Fade In (ms):', self.fade_in_ms_var)
        default_row += 1
        self._add_row(default_row, 'Fade Out (ms):', self.fade_out_ms_var)
        default_row += 1

        # Formatted Text
        self._add_row(default_row, 'Formatted Text:', self.formatted_text_var)
        default_row += 1

        # Embedded Animation Overview Panel (initially hidden)
        self.anim_overview = AnimationOverviewPanel(
            self.default_frame,
            self.config_manager,
            on_keyframe_changed=self.on_update,
        )

        # Hit Border specific rows (in hit_border_frame)
        hb_row = 0
        self._add_hb_row(hb_row, 'Duration (Active HP):', self.hb_dur_hp_var)
        hb_row += 1
        self._add_hb_row(hb_row, 'Duration (Down):', self.hb_dur_down_var)
        hb_row += 1
        self._add_hb_row(hb_row, 'Max Scale:', self.hb_max_scale_var)
        hb_row += 1
        self._add_hb_row(hb_row, 'Tint Zapped (Active):', self.hb_col_zap_var)
        hb_row += 1
        self._add_hb_row(hb_row, 'Tint Resupplied:', self.hb_col_resup_var)
        hb_row += 1
        self._add_hb_row(hb_row, 'Tint Other:', self.hb_col_other_var)

    def _add_row(
        self,
        row: int,
        label: str,
        var: tk.StringVar,
        key: str | None = None,
        anim_var: tk.BooleanVar | None = None,
    ) -> None:
        """Helper to add a text label, entry, and optional animation toggle.

        Args:
            row: The row index.
            label: The label text.
            var: The tkinter StringVar to bind.
            key: The key identifier for this property.
            anim_var: The BooleanVar for animation state of this property.
        """
        ttk.Label(self.default_frame, text=label).grid(
            row=row, column=0, sticky='w', padx=5, pady=3
        )
        entry = ttk.Entry(self.default_frame, textvariable=var)
        entry.grid(row=row, column=1, sticky='ew', padx=5, pady=3)
        entry.bind('<FocusOut>', lambda e: self._apply_properties())
        entry.bind('<Return>', lambda e: self._apply_properties())

        if key is not None:
            entry.bind('<FocusIn>', lambda e: self._on_field_focus(key))

        if anim_var is not None and key is not None:
            chk = ttk.Checkbutton(
                self.default_frame,
                text='Animate',
                variable=anim_var,
                command=lambda: self._toggle_anim(key),
            )
            chk.grid(row=row, column=2, sticky='w', padx=5, pady=3)

    def _add_hb_row(
        self,
        row: int,
        label: str,
        var: tk.StringVar,
    ) -> None:
        """Helper to add a text label and entry for hit border properties.

        Args:
            row: The row index.
            label: The label text.
            var: The tkinter StringVar to bind.
        """
        ttk.Label(self.hit_border_frame, text=label).grid(
            row=row, column=0, sticky='w', padx=5, pady=3
        )
        entry = ttk.Entry(self.hit_border_frame, textvariable=var)
        entry.grid(row=row, column=1, sticky='ew', padx=5, pady=3)
        entry.bind('<FocusOut>', lambda e: self._apply_properties())
        entry.bind('<Return>', lambda e: self._apply_properties())

    def load_element(self, name: str | None) -> None:
        """Loads element configuration values into form variables.

        Args:
            name: The name of the element to load, or None.
        """
        self.selected_element = name
        if not name:
            self.clear()
            return

        el = self.config_manager.get_element(name)
        if not el:
            self.clear()
            return

        self._set_state(tk.NORMAL)

        # Set values
        enabled_val = self.config_manager.resolve_val(el.get('enabled', False))
        self.enabled_var.set(bool(enabled_val))

        if name == 'hit_border':
            self.default_frame.grid_remove()
            self.hit_border_frame.grid(
                row=1, column=0, columnspan=3, sticky='nsew'
            )

            dur_hp = el.get('duration_hp_s', 0.5)
            dur_down = el.get('duration_down_s', 1.0)
            max_scale = el.get('max_scale', 1.2)
            col_zap = el.get('color_zapped_hp', '#ffff00')
            col_resup = el.get('color_resupplied', '#ffffff')
            col_other = el.get('color_other', '#ff0000')

            self.hb_dur_hp_var.set(str(dur_hp))
            self.hb_dur_down_var.set(str(dur_down))
            self.hb_max_scale_var.set(str(max_scale))
            self.hb_col_zap_var.set(str(col_zap))
            self.hb_col_resup_var.set(str(col_resup))
            self.hb_col_other_var.set(str(col_other))
        else:
            self.hit_border_frame.grid_remove()
            self.default_frame.grid(
                row=1, column=0, columnspan=3, sticky='nsew'
            )

            x_val = self.config_manager.resolve_val(el.get('x', 0.0))
            y_val = self.config_manager.resolve_val(el.get('y', 0.0))
            self.x_var.set(f'{x_val:.3f}' if x_val is not None else '')
            self.y_var.set(f'{y_val:.3f}' if y_val is not None else '')

            extents = self.config_manager.resolve_val(el.get('extents'))
            if extents and len(extents) >= 2:
                self.w_var.set(f'{extents[0]:.3f}')
                self.h_var.set(f'{extents[1]:.3f}')
            else:
                self.w_var.set('')
                self.h_var.set('')

            align_val = self.config_manager.resolve_val(el.get('align', 'left'))
            self.align_var.set(align_val if align_val is not None else 'left')

            style = el.get('style', {})
            font_val = self.config_manager.resolve_val(style.get('font', ''))
            size_val = self.config_manager.resolve_val(style.get('size', ''))
            self.font_var.set(font_val if font_val is not None else '')
            self.size_var.set(str(size_val) if size_val is not None else '')

            tilt_val = self.config_manager.resolve_val(el.get('tilt', 0.0))
            self.tilt_var.set(f'{tilt_val:.3f}' if tilt_val is not None else '')

            start_val = self.config_manager.resolve_val(
                el.get('visible_start_ms', 0)
            )
            end_val = self.config_manager.resolve_val(
                el.get('visible_end_ms', 0)
            )
            fade_in_val = self.config_manager.resolve_val(
                el.get('fade_in_ms', 0)
            )
            fade_out_val = self.config_manager.resolve_val(
                el.get('fade_out_ms', 0)
            )
            offset_val = self.config_manager.resolve_val(
                el.get('start_time_offset', 'beginning of video')
            )
            end_offset_val = self.config_manager.resolve_val(
                el.get('end_time_offset', 'beginning of game')
            )

            self.start_ms_var.set(
                str(start_val) if start_val is not None else '0'
            )
            self.end_ms_var.set(str(end_val) if end_val is not None else '0')
            self.start_time_offset_var.set(
                offset_val if offset_val is not None else 'beginning of video'
            )
            self.end_time_offset_var.set(
                end_offset_val
                if end_offset_val is not None
                else 'beginning of game'
            )
            self.fade_in_ms_var.set(
                str(fade_in_val) if fade_in_val is not None else '0'
            )
            self.fade_out_ms_var.set(
                str(fade_out_val) if fade_out_val is not None else '0'
            )

            fmt_text = self.config_manager.resolve_val(
                el.get('formatted_text', '')
            )
            self.formatted_text_var.set(
                fmt_text if fmt_text is not None else ''
            )

            # Set animation vars
            self.x_anim_var.set(self.config_manager.is_prop_animated(name, 'x'))
            self.y_anim_var.set(self.config_manager.is_prop_animated(name, 'y'))

            ext_anim = self.config_manager.is_prop_animated(name, 'extents')
            self.w_anim_var.set(ext_anim)
            self.h_anim_var.set(ext_anim)

            self.size_anim_var.set(
                self.config_manager.is_prop_animated(name, 'size')
            )
            self.tilt_anim_var.set(
                self.config_manager.is_prop_animated(name, 'tilt')
            )

        self._update_animation_overview_visibility()

    def clear(self) -> None:
        """Clears all input values and disables forms."""
        self.enabled_var.set(False)
        self.x_var.set('')
        self.y_var.set('')
        self.w_var.set('')
        self.h_var.set('')
        self.align_var.set('')
        self.font_var.set('')
        self.size_var.set('')
        self.tilt_var.set('')
        self.start_time_offset_var.set('')
        self.end_time_offset_var.set('')
        self.start_ms_var.set('')
        self.end_ms_var.set('')
        self.fade_in_ms_var.set('')
        self.fade_out_ms_var.set('')
        self.formatted_text_var.set('')

        self.hb_dur_hp_var.set('')
        self.hb_dur_down_var.set('')
        self.hb_max_scale_var.set('')
        self.hb_col_zap_var.set('')
        self.hb_col_resup_var.set('')
        self.hb_col_other_var.set('')

        self.x_anim_var.set(False)
        self.y_anim_var.set(False)
        self.w_anim_var.set(False)
        self.h_anim_var.set(False)
        self.size_anim_var.set(False)
        self.tilt_anim_var.set(False)

        self._set_state(tk.DISABLED)
        self._update_animation_overview_visibility()

    def _set_state(self, state: str) -> None:
        """Helper to set widgets enabled/disabled.

        Args:
            state: The widget state ('normal' or 'disabled').
        """
        for frame in (
            self.container,
            self.default_frame,
            self.hit_border_frame,
        ):
            for child in frame.winfo_children():
                if isinstance(child, ttk.Entry):
                    child['state'] = state
                elif isinstance(child, ttk.Combobox):
                    child['state'] = 'readonly' if state == tk.NORMAL else state
                elif isinstance(child, ttk.Checkbutton):
                    child['state'] = state

    def _on_check_toggle(self) -> None:
        """Handles checkbox clicks immediately."""
        if not self.selected_element:
            return
        self.config_manager.update_element(
            self.selected_element, 'enabled', self.enabled_var.get()
        )
        self.on_update()

    def _on_combobox_select(self, event: tk.Event) -> None:
        """Handles alignment selection immediately.

        Args:
            event: The combobox select event.
        """
        if not self.selected_element:
            return
        self.config_manager.update_element(
            self.selected_element, 'align', self.align_var.get()
        )
        self.on_update()

    def _on_start_time_offset_select(self, event: tk.Event) -> None:
        """Handles start time offset selection immediately.

        Args:
            event: The combobox select event.
        """
        if not self.selected_element:
            return
        self.config_manager.update_element(
            self.selected_element,
            'start_time_offset',
            self.start_time_offset_var.get(),
        )
        self.on_update()

    def _on_end_time_offset_select(self, event: tk.Event) -> None:
        """Handles end time offset selection immediately.

        Args:
            event: The combobox select event.
        """
        if not self.selected_element:
            return
        self.config_manager.update_element(
            self.selected_element,
            'end_time_offset',
            self.end_time_offset_var.get(),
        )
        self.on_update()

    def _apply_properties(self) -> None:
        """Parses entry values and applies them back to config manager."""
        if not self.selected_element:
            return

        if self.selected_element == 'hit_border':
            self._apply_float(self.hb_dur_hp_var, 'duration_hp_s')
            self._apply_float(self.hb_dur_down_var, 'duration_down_s')
            self._apply_float(self.hb_max_scale_var, 'max_scale')

            col_zap = self.hb_col_zap_var.get().strip()
            if col_zap:
                self.config_manager.update_element(
                    'hit_border', 'color_zapped_hp', col_zap
                )
            col_resup = self.hb_col_resup_var.get().strip()
            if col_resup:
                self.config_manager.update_element(
                    'hit_border', 'color_resupplied', col_resup
                )
            col_other = self.hb_col_other_var.get().strip()
            if col_other:
                self.config_manager.update_element(
                    'hit_border', 'color_other', col_other
                )

            self.on_update()
            return

        # Coordinates & sizes
        self._apply_float(self.x_var, 'x')
        self._apply_float(self.y_var, 'y')

        w_str = self.w_var.get().strip()
        h_str = self.h_var.get().strip()
        if w_str and h_str:
            try:
                self.config_manager.update_element(
                    self.selected_element,
                    'extents',
                    [float(w_str), float(h_str)],
                )
            except ValueError:
                pass
        else:
            self.config_manager.update_element(
                self.selected_element, 'extents', None
            )

        # Style & timings
        font_str = self.font_var.get().strip()
        if font_str:
            self.config_manager.update_element(
                self.selected_element, 'font', font_str
            )
        self._apply_int(self.size_var, 'size')
        self._apply_float(self.tilt_var, 'tilt')

        offset_str = self.start_time_offset_var.get().strip()
        if offset_str:
            self.config_manager.update_element(
                self.selected_element, 'start_time_offset', offset_str
            )

        end_offset_str = self.end_time_offset_var.get().strip()
        if end_offset_str:
            self.config_manager.update_element(
                self.selected_element, 'end_time_offset', end_offset_str
            )

        self._apply_int(self.start_ms_var, 'visible_start_ms')
        self._apply_int(self.end_ms_var, 'visible_end_ms')
        self._apply_int(self.fade_in_ms_var, 'fade_in_ms')
        self._apply_int(self.fade_out_ms_var, 'fade_out_ms')

        txt = self.formatted_text_var.get()
        self.config_manager.update_element(
            self.selected_element, 'formatted_text', txt
        )

        self.on_update()

    def _apply_float(self, var: tk.StringVar, key: str) -> None:
        """Parses a StringVar to float and updates element config.

        Args:
            var: The entry variable.
            key: The config key.
        """
        val_str = var.get().strip()
        if val_str:
            try:
                self.config_manager.update_element(
                    self.selected_element, key, float(val_str)
                )
            except ValueError:
                pass

    def _apply_int(self, var: tk.StringVar, key: str) -> None:
        """Parses a StringVar to int and updates element config.

        Args:
            var: The entry variable.
            key: The config key.
        """
        val_str = var.get().strip()
        if val_str:
            try:
                self.config_manager.update_element(
                    self.selected_element, key, int(val_str)
                )
            except ValueError:
                pass

    def _toggle_anim(self, key: str) -> None:
        """Toggles animation for a property.

        Args:
            key: The property key.
        """
        if not self.selected_element:
            return

        new_state = self.config_manager.toggle_prop_animated(
            self.selected_element, key
        )

        if key == 'x':
            self.x_anim_var.set(new_state)
        elif key == 'y':
            self.y_anim_var.set(new_state)
        elif key == 'extents':
            self.w_anim_var.set(new_state)
            self.h_anim_var.set(new_state)
        elif key == 'size':
            self.size_anim_var.set(new_state)
        elif key == 'tilt':
            self.tilt_anim_var.set(new_state)

        self.on_update()
        self._update_animation_overview_visibility()

    def _on_field_focus(self, key: str) -> None:
        """Handles focus on animatable properties to sync timeline graph selection.

        Args:
            key: The property key focused.
        """
        if self._is_any_prop_animated() and self.anim_overview.winfo_ismapped():
            self.anim_overview.select_property(key)

    def _is_any_prop_animated(self) -> bool:
        """Checks if any property of the selected element is animated.

        Returns:
            bool: True if any property has animation enabled.
        """
        if not self.selected_element:
            return False
        return (
            self.x_anim_var.get()
            or self.y_anim_var.get()
            or self.w_anim_var.get()
            or self.h_anim_var.get()
            or self.size_anim_var.get()
            or self.tilt_anim_var.get()
        )

    def _update_animation_overview_visibility(self) -> None:
        """Shows or hides the animation overview within properties panel."""
        if self._is_any_prop_animated():
            self.anim_overview.grid(
                row=15, column=0, columnspan=3, sticky='ew', padx=5, pady=5
            )
            self.anim_overview.load_element(self.selected_element)
        else:
            self.anim_overview.grid_remove()
            self.anim_overview.load_element(None)
