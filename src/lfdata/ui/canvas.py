"""Interactive screen layout arrangement canvas for the LF data UI.

This module provides a visual drag-and-drop canvas widget (`LayoutCanvas`) for positioning,
resizing, aligning, and selecting HUD elements on a simulated video frame screen grid.

Usage example:
    from lfdata.ui.canvas import LayoutCanvas

    canvas = LayoutCanvas(parent=window, config_manager=cfg_mgr, on_select_callback=my_select_cb)
    canvas.pack(fill='both', expand=True)
"""

import tkinter as tk
from typing import Any, Callable
from lfdata.ui.config_manager import UIConfigManager


class LayoutCanvas(tk.Canvas):
    """Interactive canvas widget for visual drag-and-drop HUD layout editing.

    Attributes:
        config_manager: UIConfigManager instance managing layout state.
        on_select_callback: Callback triggered when element selection changes.
        on_update_callback: Optional callback triggered when layout elements change.
        canvas_width: Width integer of canvas view area in pixels.
        canvas_height: Height integer of canvas view area in pixels.
    """

    def __init__(
        self,
        parent: tk.Widget,
        config_manager: UIConfigManager,
        on_select_callback: Callable[[str | None], None],
        on_update_callback: Callable[[], None] | None = None,
    ) -> None:
        """Initializes the layout canvas.

        Args:
            parent: The parent tkinter widget.
            config_manager: The configuration manager instance.
            on_select_callback: Callback triggered when selection changes.
            on_update_callback: Callback triggered when element changes.
        """
        super().__init__(
            parent,
            width=640,
            height=360,
            bg='#1e1e1e',
            highlightthickness=1,
            highlightbackground='#333333',
        )
        self.config_manager = config_manager
        self.on_select = on_select_callback
        self.on_update = on_update_callback
        self.selected_element: str | None = None

        self.width = 640
        self.height = 360

        # Drag/resize state
        self._drag_mode: str | None = None  # 'move' or 'resize'
        self._start_x = 0.0
        self._start_y = 0.0
        self._element_start_x = 0.0
        self._element_start_y = 0.0
        self._element_start_w = 0.0
        self._element_start_h = 0.0

        self.bind('<Button-1>', self._on_click)
        self.bind('<B1-Motion>', self._on_drag)
        self.bind('<ButtonRelease-1>', self._on_release)

        self.refresh_elements()

    def select_element(self, name: str | None) -> None:
        """Selects a UI element and refreshes the canvas.

        Args:
            name: The name of the UI element to select, or None to deselect.
        """
        self.selected_element = name
        self.refresh_elements()

    def refresh_elements(self) -> None:
        """Redraws all enabled UI elements and selection borders."""
        self.delete('all')

        # Draw grid lines for alignment helper
        for i in range(1, 10):
            x = (self.width / 10) * i
            y = (self.height / 10) * i
            self.create_line(x, 0, x, self.height, fill='#2a2a2a', dash=(2, 4))
            self.create_line(0, y, self.width, y, fill='#2a2a2a', dash=(2, 4))

        elements = self.config_manager.config.get('elements', {})
        for name, el in elements.items():
            enabled_val = self.config_manager.resolve_val(
                el.get('enabled', False)
            )
            if not enabled_val:
                continue

            x1, y1, x2, y2 = self._get_element_bounds(name=name, el=el)

            # Draw background box
            fill_color = (
                '#264f78' if name == self.selected_element else '#3e3e42'
            )
            outline_color = (
                '#007acc' if name == self.selected_element else '#555555'
            )
            width_border = 2 if name == self.selected_element else 1

            self.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill=fill_color,
                outline=outline_color,
                width=width_border,
                tags=(f'el:{name}', 'element'),
            )

            # Draw label
            self.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                text=name,
                fill='#ffffff',
                font=('Segoe UI', 9),
                tags=(f'el:{name}', 'text'),
            )

            # Draw resize handle if selected
            if name == self.selected_element:
                self.create_rectangle(
                    x2 - 8,
                    y2 - 8,
                    x2,
                    y2,
                    fill='#007acc',
                    outline='#ffffff',
                    tags=('resize_handle',),
                )

    def _get_element_bounds(
        self, name: str, el: dict[str, Any]
    ) -> tuple[float, float, float, float]:
        """Calculates canvas coordinates for an element.

        Args:
            name: The element name.
            el: The element configuration dictionary.

        Returns:
            A tuple of float (x1, y1, x2, y2).
        """
        x_raw = el.get('x', 0.5)
        y_raw = el.get('y', 0.5)
        align_raw = el.get('align', 'left')
        ext_raw = el.get('extents', [0.15, 0.05])

        x_rel = self.config_manager.resolve_val(x_raw)
        y_rel = self.config_manager.resolve_val(y_raw)
        align = self.config_manager.resolve_val(align_raw)
        ext = self.config_manager.resolve_val(ext_raw)

        if x_rel is None:
            x_rel = 0.5
        if y_rel is None:
            y_rel = 0.5
        if align is None:
            align = 'left'
        if ext is None or not isinstance(ext, (list, tuple)) or len(ext) < 2:
            ext = [0.15, 0.05]

        w_canvas = ext[0] * self.width
        h_canvas = ext[1] * self.height

        x_anchor = x_rel * self.width
        y_anchor = y_rel * self.height

        if align == 'center':
            x1 = x_anchor - w_canvas / 2
        elif align == 'right':
            x1 = x_anchor - w_canvas
        else:
            x1 = x_anchor

        y1 = y_anchor
        x2 = x1 + w_canvas
        y2 = y1 + h_canvas

        return x1, y1, x2, y2

    def _on_click(self, event: tk.Event) -> None:
        """Handles canvas mouse click events to detect selection, drag or resize.

        Args:
            event: The mouse event.
        """
        click_x = float(event.x)
        click_y = float(event.y)

        # Check if resize handle is clicked
        if self.selected_element:
            el = self.config_manager.get_element(self.selected_element)
            if el:
                enabled_val = self.config_manager.resolve_val(
                    el.get('enabled', False)
                )
                if enabled_val:
                    x1, y1, x2, y2 = self._get_element_bounds(
                        name=self.selected_element, el=el
                    )
                    if (
                        x2 - 10 <= click_x <= x2 + 2
                        and y2 - 10 <= click_y <= y2 + 2
                    ):
                        self._drag_mode = 'resize'
                        self._start_x = click_x
                        self._start_y = click_y
                        extents_raw = el.get('extents', [0.15, 0.05])
                        extents = self.config_manager.resolve_val(extents_raw)
                        if (
                            extents is None
                            or not isinstance(extents, (list, tuple))
                            or len(extents) < 2
                        ):
                            extents = [0.15, 0.05]
                        self._element_start_w = extents[0]
                        self._element_start_h = extents[1]
                        return

        # Check if any element box is clicked
        clicked_items = self.find_withtag('current')
        if clicked_items:
            tags = self.gettags(clicked_items[0])
            for tag in tags:
                if tag.startswith('el:'):
                    element_name = tag[3:]
                    self.selected_element = element_name
                    self.on_select(element_name)

                    el = self.config_manager.get_element(element_name)
                    if el:
                        self._drag_mode = 'move'
                        self._start_x = click_x
                        self._start_y = click_y
                        x_val = self.config_manager.resolve_val(
                            el.get('x', 0.5)
                        )
                        y_val = self.config_manager.resolve_val(
                            el.get('y', 0.5)
                        )
                        self._element_start_x = (
                            x_val if x_val is not None else 0.5
                        )
                        self._element_start_y = (
                            y_val if y_val is not None else 0.5
                        )
                    self.refresh_elements()
                    return

        # Clicked empty space
        self.selected_element = None
        self.on_select(None)
        self.refresh_elements()

    def _on_drag(self, event: tk.Event) -> None:
        """Handles canvas dragging to move or resize elements.

        Args:
            event: The mouse motion event.
        """
        if not self.selected_element or not self._drag_mode:
            return

        curr_x = float(event.x)
        curr_y = float(event.y)
        el = self.config_manager.get_element(self.selected_element)
        if not el:
            return

        if self._drag_mode == 'move':
            dx_rel = (curr_x - self._start_x) / self.width
            dy_rel = (curr_y - self._start_y) / self.height
            new_x = max(0.0, min(1.0, self._element_start_x + dx_rel))
            new_y = max(0.0, min(1.0, self._element_start_y + dy_rel))

            # Snap coordinates to grid if close (e.g. 0.01 threshold)
            if abs(new_x - round(new_x, 2)) < 0.005:
                new_x = round(new_x, 2)
            if abs(new_y - round(new_y, 2)) < 0.005:
                new_y = round(new_y, 2)

            self.config_manager.update_element(
                self.selected_element, 'x', new_x
            )
            self.config_manager.update_element(
                self.selected_element, 'y', new_y
            )

        elif self._drag_mode == 'resize':
            dw_rel = (curr_x - self._start_x) / self.width
            dh_rel = (curr_y - self._start_y) / self.height

            new_w = max(0.01, min(1.0, self._element_start_w + dw_rel))
            new_h = max(0.01, min(1.0, self._element_start_h + dh_rel))

            self.config_manager.update_element(
                self.selected_element, 'extents', [new_w, new_h]
            )

        self.refresh_elements()
        self.on_select(self.selected_element)

    def _on_release(self, event: tk.Event) -> None:
        """Handles mouse release to finalize moving or resizing.

        Args:
            event: The mouse release event.
        """
        was_dragging = self._drag_mode is not None
        self._drag_mode = None
        if was_dragging and self.on_update:
            self.on_update()
