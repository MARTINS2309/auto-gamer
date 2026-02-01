"""
State Display Component - Shows game state, HP bars, and stats.
"""

import tkinter as tk
from tkinter import ttk


class StateDisplay(tk.LabelFrame):
    """Displays current game state and statistics."""

    SCENE_COLORS = {
        "overworld": "#00ff88",
        "battle": "#ff4444",
        "dialogue": "#00aaff",
        "menu": "#ffaa00",
        "title": "#aa44ff",
        "unknown": "#888888",
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent, text="GAME STATE", bg='#1a1a2e', fg='#666',
                        font=('Consolas', 11), **kwargs)

        self._build_ui()

    def _build_ui(self):
        """Build the state display UI - compact vertical layout."""
        inner = tk.Frame(self, bg='#1a1a2e')
        inner.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # Top: Scene type (prominent)
        scene_row = tk.Frame(inner, bg='#1a1a2e')
        scene_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(scene_row, text="Scene:", font=('Consolas', 9), fg='#666',
                bg='#1a1a2e').pack(side=tk.LEFT)
        self.scene_label = tk.Label(scene_row, text="UNKNOWN", font=('Consolas', 16, 'bold'),
                                    fg='#888', bg='#1a1a2e')
        self.scene_label.pack(side=tk.LEFT, padx=(8, 0))

        # Stats row
        stats_row = tk.Frame(inner, bg='#1a1a2e')
        stats_row.pack(fill=tk.X, pady=(0, 8))

        self.step_label = tk.Label(stats_row, text="Step: 0", font=('Consolas', 11, 'bold'),
                                   fg='#fff', bg='#1a1a2e')
        self.step_label.pack(side=tk.LEFT)

        self.speed_label = tk.Label(stats_row, text="0.0/s", font=('Consolas', 10),
                                    fg='#888', bg='#1a1a2e')
        self.speed_label.pack(side=tk.LEFT, padx=(15, 0))

        self.runtime_label = tk.Label(stats_row, text="0:00", font=('Consolas', 10),
                                      fg='#666', bg='#1a1a2e')
        self.runtime_label.pack(side=tk.LEFT, padx=(15, 0))

        # HP Bars section
        hp_frame = tk.Frame(inner, bg='#1a1a2e')
        hp_frame.pack(fill=tk.X)

        # Player HP row
        player_row = tk.Frame(hp_frame, bg='#1a1a2e')
        player_row.pack(fill=tk.X, pady=2)

        tk.Label(player_row, text="Player:", font=('Consolas', 9), fg='#888',
                bg='#1a1a2e', width=7, anchor='w').pack(side=tk.LEFT)

        self.player_hp_bar = ttk.Progressbar(player_row, length=150, mode='determinate',
                                             style='green.Horizontal.TProgressbar')
        self.player_hp_bar.pack(side=tk.LEFT, padx=(0, 5))
        self.player_hp_bar['value'] = 100

        self.player_hp_label = tk.Label(player_row, text="100%", font=('Consolas', 9, 'bold'),
                                        fg='#00ff88', bg='#1a1a2e', width=5)
        self.player_hp_label.pack(side=tk.LEFT)

        # Enemy HP row
        enemy_row = tk.Frame(hp_frame, bg='#1a1a2e')
        enemy_row.pack(fill=tk.X, pady=2)

        tk.Label(enemy_row, text="Enemy:", font=('Consolas', 9), fg='#888',
                bg='#1a1a2e', width=7, anchor='w').pack(side=tk.LEFT)

        self.enemy_hp_bar = ttk.Progressbar(enemy_row, length=150, mode='determinate',
                                            style='red.Horizontal.TProgressbar')
        self.enemy_hp_bar.pack(side=tk.LEFT, padx=(0, 5))
        self.enemy_hp_bar['value'] = 100

        self.enemy_hp_label = tk.Label(enemy_row, text="100%", font=('Consolas', 9, 'bold'),
                                       fg='#ff4444', bg='#1a1a2e', width=5)
        self.enemy_hp_label.pack(side=tk.LEFT)

        # Hidden vision label (for compatibility)
        self.vision_label = tk.Label(inner, text="", font=('Consolas', 1),
                                     fg='#1a1a2e', bg='#1a1a2e')
        self.vision_label.pack()

    def set_scene(self, scene_type: str):
        """Update the scene type display."""
        color = self.SCENE_COLORS.get(scene_type.lower(), "#888")
        self.scene_label.config(text=scene_type.upper(), fg=color)

    def set_player_hp(self, hp: int):
        """Update player HP bar."""
        self.player_hp_bar['value'] = hp
        self.player_hp_label.config(text=f"{hp}%")

        if hp > 50:
            self.player_hp_label.config(fg='#00ff88')
        elif hp > 25:
            self.player_hp_label.config(fg='#ffaa00')
        else:
            self.player_hp_label.config(fg='#ff4444')

    def set_enemy_hp(self, hp: int):
        """Update enemy HP bar."""
        self.enemy_hp_bar['value'] = hp
        self.enemy_hp_label.config(text=f"{hp}%")

    def set_step(self, step: int):
        """Update step counter."""
        self.step_label.config(text=f"Step: {step:,}")

    def set_speed(self, speed: float):
        """Update speed display."""
        self.speed_label.config(text=f"{speed:.1f}/s")

    def set_vision_count(self, count: int):
        """Update vision call count."""
        self.vision_label.config(text=f"Vision: {count} calls")

    def set_runtime(self, seconds: int):
        """Update runtime display."""
        mins = seconds // 60
        secs = seconds % 60
        self.runtime_label.config(text=f"{mins}:{secs:02d}")

    def reset(self):
        """Reset all displays to default."""
        self.set_scene("unknown")
        self.set_player_hp(100)
        self.set_enemy_hp(100)
        self.set_step(0)
        self.set_speed(0)
        self.set_vision_count(0)
        self.set_runtime(0)
