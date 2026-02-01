"""
Game View Component - Displays the game screenshot.
"""

import tkinter as tk
from typing import Optional
from PIL import Image, ImageTk


class GameView(tk.LabelFrame):
    """Displays the game screenshot with optional overlay."""

    def __init__(self, parent, width: int = 480, height: int = 320, **kwargs):
        super().__init__(parent, text="GAME VIEW", bg='#1a1a2e', fg='#666',
                        font=('Consolas', 11), **kwargs)

        self.display_width = width
        self.display_height = height

        self.canvas = tk.Canvas(self, width=width, height=height, bg='black',
                                highlightthickness=1, highlightbackground='#333')
        self.canvas.pack(padx=10, pady=10)

        self._photo: Optional[ImageTk.PhotoImage] = None
        self._draw_placeholder()

    def _draw_placeholder(self):
        """Draw placeholder when no image is available."""
        self.canvas.delete("all")
        cx = self.display_width // 2
        cy = self.display_height // 2

        self.canvas.create_text(cx, cy, text="No Game Feed",
                               fill='#444', font=('Consolas', 16))
        self.canvas.create_text(cx, cy + 30, text="Click START to begin",
                               fill='#333', font=('Consolas', 10))

    def update_image(self, img: Image.Image):
        """Update the displayed image."""
        # Resize to fit display
        img_resized = img.resize((self.display_width, self.display_height),
                                 Image.Resampling.NEAREST)

        # Convert to PhotoImage (must keep reference!)
        self._photo = ImageTk.PhotoImage(img_resized)

        # Update canvas
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self._photo)

    def draw_overlay(self, scene_type: str, player_hp: int = None, enemy_hp: int = None):
        """Draw status overlay on the game view."""
        # Scene badge
        colors = {
            "overworld": "#00ff88",
            "battle": "#ff4444",
            "dialogue": "#00aaff",
            "menu": "#ffaa00",
            "title": "#aa44ff",
        }
        color = colors.get(scene_type.lower(), "#888")

        # Badge background
        self.canvas.create_rectangle(5, 5, 100, 30, fill='#000000aa', outline='')
        self.canvas.create_text(52, 17, text=scene_type.upper(), fill=color,
                               font=('Consolas', 10, 'bold'))

        # HP bars if in battle
        if player_hp is not None:
            self._draw_hp_bar(10, self.display_height - 30, 120, player_hp, "Player", "#00ff88")
        if enemy_hp is not None:
            self._draw_hp_bar(self.display_width - 130, 10, 120, enemy_hp, "Enemy", "#ff4444")

    def _draw_hp_bar(self, x: int, y: int, width: int, hp: int, label: str, color: str):
        """Draw an HP bar."""
        height = 15

        # Background
        self.canvas.create_rectangle(x, y, x + width, y + height, fill='#333', outline='#555')

        # HP fill
        hp_width = int(width * (hp / 100))
        if hp > 50:
            bar_color = "#00ff88"
        elif hp > 25:
            bar_color = "#ffaa00"
        else:
            bar_color = "#ff4444"

        self.canvas.create_rectangle(x, y, x + hp_width, y + height, fill=bar_color, outline='')

        # Label
        self.canvas.create_text(x + width // 2, y - 10, text=f"{label}: {hp}%",
                               fill='white', font=('Consolas', 8))

    def clear(self):
        """Clear and show placeholder."""
        self._photo = None
        self._draw_placeholder()
