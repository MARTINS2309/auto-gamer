"""
Virtual Grid Layout - Fine-grained dashboard grid with edit mode.

Features:
- Virtual grid based on aspect ratio (e.g., 16x9)
- Edit mode toggle for repositioning/resizing
- Drag component anchor (top-left) to reposition
- Drag resize handle to span arbitrary cells
- Overlap detection and prevention
"""

import tkinter as tk
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
import json
import os


@dataclass
class ComponentPlacement:
    """Tracks a component's position and size on the grid."""
    name: str
    row: int
    col: int
    rowspan: int
    colspan: int
    widget: Optional[tk.Widget] = None
    widget_class: Optional[type] = None
    widget_kwargs: dict = field(default_factory=dict)


class VirtualGridLayout(tk.Frame):
    """
    A virtual grid layout for dashboard components.

    Grid is based on aspect ratio (default 16x9) with configurable subdivisions.
    Components can be freely positioned and resized in edit mode.
    """

    def __init__(self, parent,
                 grid_cols: int = 16,
                 grid_rows: int = 9,
                 on_layout_change: Optional[Callable] = None,
                 config_path: Optional[str] = None,
                 **kwargs):
        super().__init__(parent, bg='#0a0a1a', **kwargs)

        self.grid_cols = grid_cols
        self.grid_rows = grid_rows
        self.on_layout_change = on_layout_change
        self.config_path = config_path or os.path.join(
            os.path.expanduser('~'), '.pokemon_ai', 'grid_layout.json'
        )

        # Component placements
        self.components: Dict[str, ComponentPlacement] = {}

        # Edit mode state
        self.edit_mode = False
        self._edit_overlay: Optional[tk.Canvas] = None
        self._dragging: Optional[str] = None  # Component name being dragged
        self._resize_mode = False  # True if resizing, False if moving
        self._drag_start: Tuple[int, int] = (0, 0)
        self._drag_origin: Tuple[int, int] = (0, 0)  # Original position

        # Cell size (calculated on resize)
        self._cell_width = 1
        self._cell_height = 1

        # Content frame (where components live)
        self._content = tk.Frame(self, bg='#0a0a1a')
        self._content.pack(fill=tk.BOTH, expand=True)

        # Bind resize to recalculate cell sizes
        self.bind('<Configure>', self._on_resize)

    def _on_resize(self, event=None):
        """Recalculate cell sizes when window resizes."""
        self._cell_width = max(1, self.winfo_width() // self.grid_cols)
        self._cell_height = max(1, self.winfo_height() // self.grid_rows)

        # Reposition all components
        self._reposition_all()

        # Update edit overlay if visible
        if self._edit_overlay:
            self._draw_grid_overlay()

    def _reposition_all(self):
        """Reposition all components based on their grid positions."""
        for name, comp in self.components.items():
            if comp.widget:
                x = comp.col * self._cell_width
                y = comp.row * self._cell_height
                w = comp.colspan * self._cell_width
                h = comp.rowspan * self._cell_height

                comp.widget.place(x=x, y=y, width=w, height=h)

    # -------------------------------------------------------------------------
    # Component Management
    # -------------------------------------------------------------------------

    def add_component(self, widget_class, name: str,
                      row: int, col: int,
                      rowspan: int = 2, colspan: int = 2,
                      **widget_kwargs) -> Optional[tk.Widget]:
        """
        Add a component to the grid.

        Args:
            widget_class: The widget class to instantiate
            name: Unique name for this component
            row, col: Top-left grid position
            rowspan, colspan: Size in grid cells
            **widget_kwargs: Arguments passed to widget constructor

        Returns:
            The created widget, or None if position conflicts
        """
        # Validate bounds
        row = max(0, min(row, self.grid_rows - rowspan))
        col = max(0, min(col, self.grid_cols - colspan))

        # Check for overlaps
        if self._check_overlap(name, row, col, rowspan, colspan):
            print(f"Cannot place {name}: overlaps existing component")
            return None

        # Create widget
        widget = widget_class(self._content, **widget_kwargs)

        # Calculate pixel position
        x = col * self._cell_width
        y = row * self._cell_height
        w = colspan * self._cell_width
        h = rowspan * self._cell_height

        widget.place(x=x, y=y, width=w, height=h)

        # Store placement
        self.components[name] = ComponentPlacement(
            name=name,
            row=row, col=col,
            rowspan=rowspan, colspan=colspan,
            widget=widget,
            widget_class=widget_class,
            widget_kwargs=widget_kwargs
        )

        return widget

    def remove_component(self, name: str):
        """Remove a component from the grid."""
        if name in self.components:
            comp = self.components[name]
            if comp.widget:
                comp.widget.destroy()
            del self.components[name]

    def get_component(self, name: str) -> Optional[tk.Widget]:
        """Get a component widget by name."""
        comp = self.components.get(name)
        return comp.widget if comp else None

    def move_component(self, name: str, new_row: int, new_col: int) -> bool:
        """Move a component to a new position."""
        if name not in self.components:
            return False

        comp = self.components[name]

        # Validate bounds
        new_row = max(0, min(new_row, self.grid_rows - comp.rowspan))
        new_col = max(0, min(new_col, self.grid_cols - comp.colspan))

        # Check overlap (excluding self)
        if self._check_overlap(name, new_row, new_col, comp.rowspan, comp.colspan):
            return False

        # Update position
        comp.row = new_row
        comp.col = new_col

        # Reposition widget
        if comp.widget:
            x = new_col * self._cell_width
            y = new_row * self._cell_height
            comp.widget.place(x=x, y=y)

        self._notify_change()
        return True

    def resize_component(self, name: str, new_rowspan: int, new_colspan: int) -> bool:
        """Resize a component."""
        if name not in self.components:
            return False

        comp = self.components[name]

        # Validate size
        new_rowspan = max(1, min(new_rowspan, self.grid_rows - comp.row))
        new_colspan = max(1, min(new_colspan, self.grid_cols - comp.col))

        # Check overlap
        if self._check_overlap(name, comp.row, comp.col, new_rowspan, new_colspan):
            return False

        # Update size
        comp.rowspan = new_rowspan
        comp.colspan = new_colspan

        # Resize widget
        if comp.widget:
            w = new_colspan * self._cell_width
            h = new_rowspan * self._cell_height
            comp.widget.place(width=w, height=h)

        self._notify_change()
        return True

    def _check_overlap(self, exclude_name: str,
                       row: int, col: int,
                       rowspan: int, colspan: int) -> bool:
        """Check if a placement would overlap existing components."""
        for name, comp in self.components.items():
            if name == exclude_name:
                continue

            # Check rectangle intersection
            if (col < comp.col + comp.colspan and
                col + colspan > comp.col and
                row < comp.row + comp.rowspan and
                row + rowspan > comp.row):
                return True

        return False

    def clear(self):
        """Remove all components."""
        for name in list(self.components.keys()):
            self.remove_component(name)

    # -------------------------------------------------------------------------
    # Edit Mode
    # -------------------------------------------------------------------------

    def toggle_edit_mode(self):
        """Toggle edit mode on/off."""
        self.edit_mode = not self.edit_mode

        if self.edit_mode:
            self._enable_edit_mode()
        else:
            self._disable_edit_mode()

    def _enable_edit_mode(self):
        """Enable edit mode - show grid overlay and handles."""
        # Create semi-transparent overlay canvas on top of everything
        self._edit_overlay = tk.Canvas(
            self, bg='#0a0a1a',
            highlightthickness=0
        )
        self._edit_overlay.place(x=0, y=0, relwidth=1, relheight=1)

        # Raise overlay above content so it receives mouse events
        self._edit_overlay.lift()

        # Make overlay semi-transparent by drawing component previews
        # Draw grid
        self._draw_grid_overlay()

        # Add component handles
        for name, comp in self.components.items():
            self._add_edit_handles(name, comp)

    def _disable_edit_mode(self):
        """Disable edit mode - hide overlay and handles."""
        if self._edit_overlay:
            self._edit_overlay.destroy()
            self._edit_overlay = None

        self._dragging = None
        self._resize_mode = False

    def _draw_grid_overlay(self):
        """Draw the grid lines on the overlay."""
        if not self._edit_overlay:
            return

        self._edit_overlay.delete("all")

        w = self.winfo_width()
        h = self.winfo_height()

        # Dark semi-transparent background
        self._edit_overlay.create_rectangle(
            0, 0, w, h,
            fill='#0a0a1a', outline='',
            tags="bg"
        )

        # Vertical lines
        for i in range(self.grid_cols + 1):
            x = i * self._cell_width
            color = '#444' if i % 4 == 0 else '#222'
            self._edit_overlay.create_line(
                x, 0, x, h,
                fill=color, tags="grid"
            )

        # Horizontal lines
        for i in range(self.grid_rows + 1):
            y = i * self._cell_height
            color = '#444' if i % 3 == 0 else '#222'
            self._edit_overlay.create_line(
                0, y, w, y,
                fill=color, tags="grid"
            )

        # Draw component rectangles
        for name, comp in self.components.items():
            x1 = comp.col * self._cell_width
            y1 = comp.row * self._cell_height
            x2 = x1 + comp.colspan * self._cell_width
            y2 = y1 + comp.rowspan * self._cell_height

            # Component filled area (semi-transparent)
            self._edit_overlay.create_rectangle(
                x1 + 2, y1 + 2, x2 - 2, y2 - 2,
                outline='#00aaff', width=3,
                fill='#1a2a3a', tags=f"comp_{name}"
            )

            # Label background
            self._edit_overlay.create_rectangle(
                x1 + 5, y1 + 5, x1 + len(name) * 8 + 15, y1 + 22,
                fill='#00aaff', outline='',
                tags=f"labelbg_{name}"
            )

            # Label
            self._edit_overlay.create_text(
                x1 + 10, y1 + 13,
                text=name, anchor='w',
                fill='white', font=('Consolas', 9, 'bold'),
                tags=f"label_{name}"
            )

            # Resize handle (bottom-right corner) - larger for easier grabbing
            handle_size = 20
            self._edit_overlay.create_rectangle(
                x2 - handle_size, y2 - handle_size, x2 - 2, y2 - 2,
                fill='#00aaff', outline='#0088cc', width=2,
                tags=(f"resize_{name}", f"resize_rect_{name}")
            )

            # Resize icon (diagonal lines)
            self._edit_overlay.create_line(
                x2 - 15, y2 - 5, x2 - 5, y2 - 15,
                fill='white', width=2, tags=(f"resize_{name}", f"resize_line1_{name}")
            )
            self._edit_overlay.create_line(
                x2 - 10, y2 - 5, x2 - 5, y2 - 10,
                fill='white', width=2, tags=(f"resize_{name}", f"resize_line2_{name}")
            )

    def _add_edit_handles(self, name: str, comp: ComponentPlacement):
        """Add drag handles for a component."""
        if not self._edit_overlay:
            return

        # Cursor changes for visual feedback
        self._edit_overlay.tag_bind(
            f"comp_{name}", "<Enter>",
            lambda e: self._edit_overlay.config(cursor='fleur')
        )
        self._edit_overlay.tag_bind(
            f"comp_{name}", "<Leave>",
            lambda e: self._edit_overlay.config(cursor='')
        )
        self._edit_overlay.tag_bind(
            f"resize_{name}", "<Enter>",
            lambda e: self._edit_overlay.config(cursor='sizing')
        )
        self._edit_overlay.tag_bind(
            f"resize_{name}", "<Leave>",
            lambda e: self._edit_overlay.config(cursor='')
        )

        # Bind events to component rectangle (for moving)
        self._edit_overlay.tag_bind(
            f"comp_{name}", "<Button-1>",
            lambda e, n=name: self._start_drag(e, n, False)
        )
        self._edit_overlay.tag_bind(
            f"comp_{name}", "<B1-Motion>",
            lambda e, n=name: self._on_drag(e, n)
        )
        self._edit_overlay.tag_bind(
            f"comp_{name}", "<ButtonRelease-1>",
            lambda e, n=name: self._end_drag(e, n)
        )

        # Bind resize handle
        self._edit_overlay.tag_bind(
            f"resize_{name}", "<Button-1>",
            lambda e, n=name: self._start_drag(e, n, True)
        )
        self._edit_overlay.tag_bind(
            f"resize_{name}", "<B1-Motion>",
            lambda e, n=name: self._on_drag(e, n)
        )
        self._edit_overlay.tag_bind(
            f"resize_{name}", "<ButtonRelease-1>",
            lambda e, n=name: self._end_drag(e, n)
        )

    def _start_drag(self, event, name: str, resize: bool):
        """Start dragging a component."""
        self._dragging = name
        self._resize_mode = resize
        self._drag_start = (event.x, event.y)

        comp = self.components[name]
        self._drag_origin = (comp.row, comp.col, comp.rowspan, comp.colspan)

    def _on_drag(self, event, name: str):
        """Handle drag motion."""
        if self._dragging != name:
            return

        comp = self.components[name]
        orig_row, orig_col, orig_rowspan, orig_colspan = self._drag_origin

        # Calculate delta in grid cells
        dx = (event.x - self._drag_start[0]) // self._cell_width
        dy = (event.y - self._drag_start[1]) // self._cell_height

        if self._resize_mode:
            # Resize: adjust span
            new_rowspan = max(1, orig_rowspan + dy)
            new_colspan = max(1, orig_colspan + dx)

            # Clamp to grid bounds
            new_rowspan = min(new_rowspan, self.grid_rows - comp.row)
            new_colspan = min(new_colspan, self.grid_cols - comp.col)

            # Preview (without saving)
            if not self._check_overlap(name, comp.row, comp.col, new_rowspan, new_colspan):
                self._preview_resize(name, new_rowspan, new_colspan)
        else:
            # Move: adjust position
            new_row = max(0, min(orig_row + dy, self.grid_rows - comp.rowspan))
            new_col = max(0, min(orig_col + dx, self.grid_cols - comp.colspan))

            # Preview (without saving)
            if not self._check_overlap(name, new_row, new_col, comp.rowspan, comp.colspan):
                self._preview_move(name, new_row, new_col)

    def _end_drag(self, event, name: str):
        """End dragging - finalize position."""
        if self._dragging != name:
            return

        comp = self.components[name]
        orig_row, orig_col, orig_rowspan, orig_colspan = self._drag_origin

        dx = (event.x - self._drag_start[0]) // self._cell_width
        dy = (event.y - self._drag_start[1]) // self._cell_height

        if self._resize_mode:
            new_rowspan = max(1, orig_rowspan + dy)
            new_colspan = max(1, orig_colspan + dx)
            new_rowspan = min(new_rowspan, self.grid_rows - comp.row)
            new_colspan = min(new_colspan, self.grid_cols - comp.col)

            if not self._check_overlap(name, comp.row, comp.col, new_rowspan, new_colspan):
                comp.rowspan = new_rowspan
                comp.colspan = new_colspan
        else:
            new_row = max(0, min(orig_row + dy, self.grid_rows - comp.rowspan))
            new_col = max(0, min(orig_col + dx, self.grid_cols - comp.colspan))

            if not self._check_overlap(name, new_row, new_col, comp.rowspan, comp.colspan):
                comp.row = new_row
                comp.col = new_col

        self._dragging = None
        self._resize_mode = False

        # Reposition actual widget
        self._reposition_all()

        # Redraw overlay
        self._draw_grid_overlay()
        for n in self.components:
            self._add_edit_handles(n, self.components[n])

        self._notify_change()

    def _preview_move(self, name: str, new_row: int, new_col: int):
        """Preview component move on overlay."""
        if not self._edit_overlay:
            return

        comp = self.components[name]
        x1 = new_col * self._cell_width
        y1 = new_row * self._cell_height
        x2 = x1 + comp.colspan * self._cell_width
        y2 = y1 + comp.rowspan * self._cell_height

        # Update all elements for this component
        self._edit_overlay.coords(f"comp_{name}", x1 + 2, y1 + 2, x2 - 2, y2 - 2)
        self._edit_overlay.coords(f"labelbg_{name}", x1 + 5, y1 + 5, x1 + len(name) * 8 + 15, y1 + 22)
        self._edit_overlay.coords(f"label_{name}", x1 + 10, y1 + 13)
        # Update resize handle elements
        self._edit_overlay.coords(f"resize_rect_{name}", x2 - 20, y2 - 20, x2 - 2, y2 - 2)
        self._edit_overlay.coords(f"resize_line1_{name}", x2 - 15, y2 - 5, x2 - 5, y2 - 15)
        self._edit_overlay.coords(f"resize_line2_{name}", x2 - 10, y2 - 5, x2 - 5, y2 - 10)

    def _preview_resize(self, name: str, new_rowspan: int, new_colspan: int):
        """Preview component resize on overlay."""
        if not self._edit_overlay:
            return

        comp = self.components[name]
        x1 = comp.col * self._cell_width
        y1 = comp.row * self._cell_height
        x2 = x1 + new_colspan * self._cell_width
        y2 = y1 + new_rowspan * self._cell_height

        # Update rectangle and resize handle elements
        self._edit_overlay.coords(f"comp_{name}", x1 + 2, y1 + 2, x2 - 2, y2 - 2)
        self._edit_overlay.coords(f"resize_rect_{name}", x2 - 20, y2 - 20, x2 - 2, y2 - 2)
        self._edit_overlay.coords(f"resize_line1_{name}", x2 - 15, y2 - 5, x2 - 5, y2 - 15)
        self._edit_overlay.coords(f"resize_line2_{name}", x2 - 10, y2 - 5, x2 - 5, y2 - 10)

    def _notify_change(self):
        """Notify listeners of layout change."""
        if self.on_layout_change:
            self.on_layout_change(self.get_layout())

    # -------------------------------------------------------------------------
    # Layout Persistence
    # -------------------------------------------------------------------------

    def get_layout(self) -> Dict[str, Any]:
        """Get current layout configuration."""
        return {
            'grid_cols': self.grid_cols,
            'grid_rows': self.grid_rows,
            'components': [
                {
                    'name': comp.name,
                    'row': comp.row,
                    'col': comp.col,
                    'rowspan': comp.rowspan,
                    'colspan': comp.colspan,
                }
                for comp in self.components.values()
            ]
        }

    def save_layout(self):
        """Save layout to config file."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.get_layout(), f, indent=2)
        except Exception as e:
            print(f"Failed to save layout: {e}")

    def load_layout(self) -> Optional[Dict]:
        """Load layout from config file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load layout: {e}")
        return None


class EditModeToggle(tk.Frame):
    """Button to toggle grid edit mode."""

    def __init__(self, parent, grid_layout: VirtualGridLayout, **kwargs):
        super().__init__(parent, bg='#1a1a2e', **kwargs)

        self.grid_layout = grid_layout
        self.edit_active = False

        self.toggle_btn = tk.Button(
            self, text="Edit Layout",
            command=self._toggle,
            bg='#2a4a6a', fg='white', font=('Consolas', 9),
            relief=tk.FLAT, cursor='hand2', padx=10
        )
        self.toggle_btn.pack(side=tk.LEFT)

        self.save_btn = tk.Button(
            self, text="Save",
            command=self._save,
            bg='#2a5e2a', fg='white', font=('Consolas', 9),
            relief=tk.FLAT, cursor='hand2', padx=10, state=tk.DISABLED
        )
        self.save_btn.pack(side=tk.LEFT, padx=(5, 0))

    def _toggle(self):
        """Toggle edit mode."""
        self.edit_active = not self.edit_active
        self.grid_layout.toggle_edit_mode()

        if self.edit_active:
            self.toggle_btn.config(text="Done Editing", bg='#6a4a2a')
            self.save_btn.config(state=tk.NORMAL)
        else:
            self.toggle_btn.config(text="Edit Layout", bg='#2a4a6a')
            self.save_btn.config(state=tk.DISABLED)

    def _save(self):
        """Save the current layout."""
        self.grid_layout.save_layout()
        self.toggle_btn.config(text="Saved!", bg='#2a5e2a')
        self.after(1000, lambda: self.toggle_btn.config(
            text="Done Editing" if self.edit_active else "Edit Layout",
            bg='#6a4a2a' if self.edit_active else '#2a4a6a'
        ))


# Keep old name for backwards compatibility
GridLayout = VirtualGridLayout
LayoutSelector = EditModeToggle
