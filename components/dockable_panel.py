"""
Dockable Panel Component - Movable, resizable panels that can be undocked.

Features:
- Title bar with controls (minimize, pop-out, close)
- Can be undocked to separate window
- Can be re-docked back to main window
- Supports PanedWindow for resizing
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Dict, Any
import json
import os


class DockablePanel(tk.Frame):
    """A panel that can be docked in the main window or popped out."""

    def __init__(self, parent, title: str = "Panel",
                 min_width: int = 200, min_height: int = 100,
                 on_undock: Optional[Callable] = None,
                 on_dock: Optional[Callable] = None,
                 on_close: Optional[Callable] = None,
                 allow_close: bool = False,
                 **kwargs):
        super().__init__(parent, bg='#1a1a2e', **kwargs)

        self.title = title
        self.min_width = min_width
        self.min_height = min_height
        self.on_undock = on_undock
        self.on_dock = on_dock
        self.on_close = on_close
        self.allow_close = allow_close

        self._is_docked = True
        self._is_minimized = False
        self._popup_window: Optional[tk.Toplevel] = None
        self._content_widget: Optional[tk.Widget] = None
        self._original_parent = parent
        self._content_frame: Optional[tk.Frame] = None

        # Store widget creation info for recreation
        self._widget_class = None
        self._widget_kwargs = {}

        self._build_ui()

    def _build_ui(self):
        """Build the panel UI with title bar."""
        # Title bar
        self.title_bar = tk.Frame(self, bg='#252540', height=24)
        self.title_bar.pack(fill=tk.X)
        self.title_bar.pack_propagate(False)

        # Drag handle / title
        self.title_label = tk.Label(
            self.title_bar, text=f"  {self.title}",
            bg='#252540', fg='#888',
            font=('Consolas', 9, 'bold'),
            anchor='w', cursor='fleur'
        )
        self.title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Bind drag events
        self.title_label.bind('<Button-1>', self._start_drag)
        self.title_label.bind('<B1-Motion>', self._on_drag)
        self.title_label.bind('<ButtonRelease-1>', self._end_drag)

        # Control buttons (right side)
        btn_frame = tk.Frame(self.title_bar, bg='#252540')
        btn_frame.pack(side=tk.RIGHT)

        # Minimize button
        self.min_btn = tk.Label(
            btn_frame, text='_', bg='#252540', fg='#666',
            font=('Consolas', 9), width=2, cursor='hand2'
        )
        self.min_btn.pack(side=tk.LEFT)
        self.min_btn.bind('<Button-1>', lambda e: self._toggle_minimize())
        self.min_btn.bind('<Enter>', lambda e: self.min_btn.config(bg='#3a3a5a'))
        self.min_btn.bind('<Leave>', lambda e: self.min_btn.config(bg='#252540'))

        # Pop-out button
        self.popout_btn = tk.Label(
            btn_frame, text='[]', bg='#252540', fg='#666',
            font=('Consolas', 8), width=2, cursor='hand2'
        )
        self.popout_btn.pack(side=tk.LEFT)
        self.popout_btn.bind('<Button-1>', lambda e: self._toggle_undock())
        self.popout_btn.bind('<Enter>', lambda e: self.popout_btn.config(bg='#3a3a5a'))
        self.popout_btn.bind('<Leave>', lambda e: self.popout_btn.config(bg='#252540'))

        # Close button (optional)
        if self.allow_close:
            self.close_btn = tk.Label(
                btn_frame, text='x', bg='#252540', fg='#666',
                font=('Consolas', 9), width=2, cursor='hand2'
            )
            self.close_btn.pack(side=tk.LEFT)
            self.close_btn.bind('<Button-1>', lambda e: self._close_panel())
            self.close_btn.bind('<Enter>', lambda e: self.close_btn.config(bg='#5a2a2a'))
            self.close_btn.bind('<Leave>', lambda e: self.close_btn.config(bg='#252540'))

        # Content container
        self._content_frame = tk.Frame(self, bg='#1a1a2e')
        self._content_frame.pack(fill=tk.BOTH, expand=True)

    def set_content(self, widget_class, **widget_kwargs) -> tk.Widget:
        """Create and set the content widget."""
        # Store for recreation when undocking/docking
        self._widget_class = widget_class
        self._widget_kwargs = widget_kwargs

        self._content_widget = widget_class(self._content_frame, **widget_kwargs)
        self._content_widget.pack(fill=tk.BOTH, expand=True)
        return self._content_widget

    def get_content(self) -> Optional[tk.Widget]:
        """Get the content widget."""
        return self._content_widget

    def _toggle_minimize(self):
        """Toggle panel minimized state."""
        if self._is_minimized:
            self._content_frame.pack(fill=tk.BOTH, expand=True)
            self.min_btn.config(text='_')
            self._is_minimized = False
        else:
            self._content_frame.pack_forget()
            self.min_btn.config(text='+')
            self._is_minimized = True

    def _toggle_undock(self):
        """Toggle between docked and undocked state."""
        if self._is_docked:
            self._undock()
        else:
            self._dock()

    def _undock(self):
        """Pop out the panel into a separate window."""
        if self._popup_window:
            return

        # Store current geometry
        width = max(self.winfo_width(), self.min_width)
        height = max(self.winfo_height(), self.min_height)

        # Create popup window
        self._popup_window = tk.Toplevel(self.winfo_toplevel())
        self._popup_window.title(self.title)
        self._popup_window.configure(bg='#1a1a2e')
        self._popup_window.geometry(f"{width}x{height}")
        self._popup_window.minsize(self.min_width, self.min_height)
        self._popup_window.protocol('WM_DELETE_WINDOW', self._dock)

        # Title bar for popup
        title_bar = tk.Frame(self._popup_window, bg='#252540', height=28)
        title_bar.pack(fill=tk.X, side=tk.TOP)
        title_bar.pack_propagate(False)

        tk.Label(title_bar, text=f"  {self.title}", bg='#252540', fg='#888',
                font=('Consolas', 9, 'bold'), anchor='w').pack(side=tk.LEFT, fill=tk.X, expand=True)

        dock_btn = tk.Button(
            title_bar, text="Dock", command=self._dock,
            bg='#3a3a5a', fg='white', font=('Consolas', 8),
            relief=tk.FLAT, cursor='hand2', padx=10
        )
        dock_btn.pack(side=tk.RIGHT, padx=5, pady=2)

        # Content frame for popup
        popup_content = tk.Frame(self._popup_window, bg='#1a1a2e')
        popup_content.pack(fill=tk.BOTH, expand=True)

        # Recreate the widget in popup if we have the class info
        if self._widget_class:
            self._popup_content_widget = self._widget_class(popup_content, **self._widget_kwargs)
            self._popup_content_widget.pack(fill=tk.BOTH, expand=True)
        else:
            # Fallback: show message that content can't be moved
            tk.Label(popup_content, text=f"{self.title}\n\nContent in main window",
                    bg='#1a1a2e', fg='#888', font=('Consolas', 10)).pack(expand=True)

        # Hide original content and show placeholder
        self._content_frame.pack_forget()
        self.title_bar.pack_forget()

        # Show placeholder text in the docked space
        self._placeholder = tk.Label(
            self, text=f"{self.title}\n[Undocked]",
            bg='#1a1a2e', fg='#444',
            font=('Consolas', 9)
        )
        self._placeholder.pack(fill=tk.BOTH, expand=True)

        self._is_docked = False
        self.popout_btn.config(text='><')

        if self.on_undock:
            self.on_undock(self)

    def _dock(self):
        """Re-dock the panel back to the main window."""
        if not self._popup_window:
            return

        # Remove placeholder
        if hasattr(self, '_placeholder') and self._placeholder:
            self._placeholder.destroy()
            self._placeholder = None

        # Restore original content
        self.title_bar.pack(fill=tk.X)
        self._content_frame.pack(fill=tk.BOTH, expand=True)

        # Clear popup content widget reference
        if hasattr(self, '_popup_content_widget'):
            self._popup_content_widget = None

        # Destroy popup
        self._popup_window.destroy()
        self._popup_window = None

        self._is_docked = True
        self.popout_btn.config(text='[]')

        if self.on_dock:
            self.on_dock(self)

    def _close_panel(self):
        """Close/hide the panel."""
        if self._popup_window:
            self._popup_window.destroy()
            self._popup_window = None
        self.pack_forget()
        if self.on_close:
            self.on_close(self)

    def show(self):
        """Show the panel."""
        self.pack(fill=tk.BOTH, expand=True)

    # Drag handling (for future reordering)
    _drag_data = {"x": 0, "y": 0}

    def _start_drag(self, event):
        """Start dragging the panel."""
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self.title_label.config(bg='#3a3a5a')

    def _on_drag(self, event):
        """Handle drag motion."""
        # For now, just visual feedback
        # Full drag-and-drop reordering would require more complex logic
        pass

    def _end_drag(self, event):
        """End dragging."""
        self.title_label.config(bg='#252540')


class DockManager:
    """Manages dockable panel layout and persistence."""

    def __init__(self, root: tk.Tk, config_path: str = None):
        self.root = root
        self.config_path = config_path or os.path.join(
            os.path.expanduser('~'), '.pokemon_ai', 'layout.json'
        )
        self.panels: Dict[str, DockablePanel] = {}
        self._layout: Dict[str, Any] = {}

    def register_panel(self, name: str, panel: DockablePanel):
        """Register a panel with the manager."""
        self.panels[name] = panel
        panel.on_undock = lambda p: self._on_panel_undock(name, p)
        panel.on_dock = lambda p: self._on_panel_dock(name, p)

    def _on_panel_undock(self, name: str, panel: DockablePanel):
        """Handle panel undock event."""
        if panel._popup_window:
            # Save window geometry
            self._layout[name] = {
                'docked': False,
                'geometry': panel._popup_window.geometry()
            }
            self.save_layout()

    def _on_panel_dock(self, name: str, panel: DockablePanel):
        """Handle panel dock event."""
        self._layout[name] = {'docked': True}
        self.save_layout()

    def save_layout(self):
        """Save layout to file."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self._layout, f, indent=2)
        except Exception as e:
            print(f"Failed to save layout: {e}")

    def load_layout(self):
        """Load layout from file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self._layout = json.load(f)
                self._apply_layout()
        except Exception as e:
            print(f"Failed to load layout: {e}")

    def _apply_layout(self):
        """Apply loaded layout to panels."""
        for name, config in self._layout.items():
            if name in self.panels:
                panel = self.panels[name]
                if not config.get('docked', True):
                    panel._undock()
                    if panel._popup_window and 'geometry' in config:
                        panel._popup_window.geometry(config['geometry'])


class ResizableLayout(tk.Frame):
    """A resizable layout using PanedWindow for dockable panels."""

    def __init__(self, parent, orientation: str = 'horizontal', **kwargs):
        super().__init__(parent, bg='#0a0a1a', **kwargs)

        self.orientation = orientation
        orient = tk.HORIZONTAL if orientation == 'horizontal' else tk.VERTICAL

        self.paned = tk.PanedWindow(
            self, orient=orient, bg='#0a0a1a',
            sashwidth=6, sashrelief=tk.FLAT,
            borderwidth=0, showhandle=False
        )
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Style the sash
        self.paned.configure(sashpad=0)

    def add_pane(self, widget: tk.Widget, weight: int = 1,
                 minsize: int = 100, **kwargs):
        """Add a pane to the layout."""
        self.paned.add(widget, minsize=minsize, **kwargs)

    def insert_pane(self, index: int, widget: tk.Widget,
                    minsize: int = 100, **kwargs):
        """Insert a pane at a specific index."""
        self.paned.add(widget, minsize=minsize, **kwargs)
        # Move to correct position
        self.paned.paneconfigure(widget, before=self.paned.panes()[index] if index < len(self.paned.panes()) else None)
