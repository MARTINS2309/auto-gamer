"""
Input Pad Component - GBA controller visualization.
"""

import tkinter as tk
from typing import Dict


class InputPad(tk.LabelFrame):
    """Visual GBA controller with button indicators."""

    BUTTON_COLORS = {
        'default': '#333',
        'active': '#00ff88',
        'bumper_active': '#ff00ff',
    }

    def __init__(self, parent, width: int = 320, height: int = 160, **kwargs):
        super().__init__(parent, text="INPUT", bg='#1a1a2e', fg='#666',
                        font=('Consolas', 11), **kwargs)

        self.actions: Dict[str, bool] = {
            "up": False, "down": False, "left": False, "right": False,
            "a": False, "b": False, "start": False, "select": False,
            "l": False, "r": False
        }

        self.canvas = tk.Canvas(self, width=width, height=height, bg='#0a0a1a',
                                highlightthickness=0)
        self.canvas.pack(padx=5, pady=5)

        self._draw()

    def _draw(self):
        """Draw the controller in compact horizontal layout."""
        c = self.canvas
        c.delete("all")

        w = int(c['width'])
        h = int(c['height'])

        # === L/R Bumpers at top ===
        l_color = self.BUTTON_COLORS['bumper_active'] if self.actions['l'] else self.BUTTON_COLORS['default']
        r_color = self.BUTTON_COLORS['bumper_active'] if self.actions['r'] else self.BUTTON_COLORS['default']

        # L bumper (top left)
        c.create_rectangle(10, 8, 70, 32, fill=l_color, outline='#555', width=2)
        c.create_text(40, 20, text='L', fill='#000' if self.actions['l'] else '#666',
                     font=('Consolas', 12, 'bold'))

        # R bumper (top right)
        c.create_rectangle(w-70, 8, w-10, 32, fill=r_color, outline='#555', width=2)
        c.create_text(w-40, 20, text='R', fill='#000' if self.actions['r'] else '#666',
                     font=('Consolas', 12, 'bold'))

        # === D-pad (left side) ===
        cx, cy = 55, 90

        # D-pad base (plus shape)
        c.create_rectangle(cx-12, cy-35, cx+12, cy+35, fill='#222', outline='#444')
        c.create_rectangle(cx-35, cy-12, cx+35, cy+12, fill='#222', outline='#444')

        # Direction buttons
        directions = {
            "up": [(cx, cy-24), (cx-10, cy-12), (cx+10, cy-12)],
            "down": [(cx, cy+24), (cx-10, cy+12), (cx+10, cy+12)],
            "left": [(cx-24, cy), (cx-12, cy-10), (cx-12, cy+10)],
            "right": [(cx+24, cy), (cx+12, cy-10), (cx+12, cy+10)],
        }

        for name, points in directions.items():
            color = self.BUTTON_COLORS['active'] if self.actions[name] else self.BUTTON_COLORS['default']
            c.create_polygon(points, fill=color, outline='#555')

        # === A/B Buttons (right side) ===
        ax, ay = w - 45, 70
        bx, by = w - 80, 100

        # A button (larger)
        a_color = self.BUTTON_COLORS['active'] if self.actions['a'] else self.BUTTON_COLORS['default']
        c.create_oval(ax-18, ay-18, ax+18, ay+18, fill=a_color, outline='#555', width=2)
        c.create_text(ax, ay, text='A', fill='#000' if self.actions['a'] else '#666',
                     font=('Consolas', 12, 'bold'))

        # B button
        b_color = self.BUTTON_COLORS['active'] if self.actions['b'] else self.BUTTON_COLORS['default']
        c.create_oval(bx-15, by-15, bx+15, by+15, fill=b_color, outline='#555', width=2)
        c.create_text(bx, by, text='B', fill='#000' if self.actions['b'] else '#666',
                     font=('Consolas', 11, 'bold'))

        # === Start/Select (center bottom) ===
        sy = h - 30
        mid = w // 2

        # Select (left of center)
        sel_color = self.BUTTON_COLORS['active'] if self.actions['select'] else self.BUTTON_COLORS['default']
        c.create_rectangle(mid-75, sy, mid-25, sy+20, fill=sel_color, outline='#555')
        c.create_text(mid-50, sy+10, text='SELECT', fill='#000' if self.actions['select'] else '#666',
                     font=('Consolas', 8, 'bold'))

        # Start (right of center)
        start_color = self.BUTTON_COLORS['active'] if self.actions['start'] else self.BUTTON_COLORS['default']
        c.create_rectangle(mid+25, sy, mid+75, sy+20, fill=start_color, outline='#555')
        c.create_text(mid+50, sy+10, text='START', fill='#000' if self.actions['start'] else '#666',
                     font=('Consolas', 8, 'bold'))

    def press(self, button: str):
        """Highlight a button as pressed."""
        if button in self.actions:
            self.actions[button] = True
            self._draw()

    def release(self, button: str):
        """Release a button."""
        if button in self.actions:
            self.actions[button] = False
            self._draw()

    def release_all(self):
        """Release all buttons."""
        for key in self.actions:
            self.actions[key] = False
        self._draw()

    def flash(self, button: str, duration_ms: int = 100):
        """Flash a button briefly."""
        self.press(button)
        self.after(duration_ms, lambda: self.release(button))
