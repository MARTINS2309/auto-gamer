"""
Control Panel Component - Buttons and settings for controlling the runner.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class ControlPanel(tk.LabelFrame):
    """Control panel with start/stop/pause buttons and settings."""

    def __init__(self, parent,
                 on_start: Optional[Callable] = None,
                 on_stop: Optional[Callable] = None,
                 on_pause: Optional[Callable] = None,
                 on_reset: Optional[Callable] = None,
                 on_settings_change: Optional[Callable] = None,
                 **kwargs):
        super().__init__(parent, text="CONTROLS", bg='#1a1a2e', fg='#666',
                        font=('Consolas', 11), **kwargs)

        self.on_start = on_start
        self.on_stop = on_stop
        self.on_pause = on_pause
        self.on_reset = on_reset
        self.on_settings_change = on_settings_change

        self.is_running = False
        self.is_paused = False

        self._build_ui()

    def _build_ui(self):
        """Build the control panel UI."""
        # Top row: Main control buttons
        btn_frame = tk.Frame(self, bg='#1a1a2e')
        btn_frame.pack(fill=tk.X, padx=15, pady=(15, 10))

        # Start button
        self.start_btn = tk.Button(btn_frame, text="▶ START", command=self._on_start,
                                   bg='#2a5e2a', fg='white', font=('Consolas', 12, 'bold'),
                                   width=12, height=2, relief=tk.FLAT, cursor='hand2')
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Pause button
        self.pause_btn = tk.Button(btn_frame, text="⏸ PAUSE", command=self._on_pause,
                                   bg='#5e5e2a', fg='white', font=('Consolas', 12, 'bold'),
                                   width=12, height=2, relief=tk.FLAT, state=tk.DISABLED,
                                   cursor='hand2')
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Stop button
        self.stop_btn = tk.Button(btn_frame, text="⏹ STOP", command=self._on_stop,
                                  bg='#5e2a2a', fg='white', font=('Consolas', 12, 'bold'),
                                  width=12, height=2, relief=tk.FLAT, state=tk.DISABLED,
                                  cursor='hand2')
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Reset button
        self.reset_btn = tk.Button(btn_frame, text="↺ RESET", command=self._on_reset,
                                   bg='#3a3a4e', fg='white', font=('Consolas', 12, 'bold'),
                                   width=12, height=2, relief=tk.FLAT, cursor='hand2')
        self.reset_btn.pack(side=tk.LEFT)

        # Separator
        ttk.Separator(self, orient='horizontal').pack(fill=tk.X, padx=15, pady=10)

        # Settings row
        settings_frame = tk.Frame(self, bg='#1a1a2e')
        settings_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        # Vision interval
        vision_frame = tk.Frame(settings_frame, bg='#1a1a2e')
        vision_frame.pack(side=tk.LEFT, padx=(0, 30))

        tk.Label(vision_frame, text="Vision Interval:", font=('Consolas', 10),
                fg='#888', bg='#1a1a2e').pack(anchor='w')
        self.vision_interval = tk.Scale(vision_frame, from_=1, to=20, orient=tk.HORIZONTAL,
                                        length=150, bg='#1a1a2e', fg='#00aaff',
                                        highlightthickness=0, troughcolor='#333',
                                        command=self._on_setting_change)
        self.vision_interval.set(5)
        self.vision_interval.pack()
        tk.Label(vision_frame, text="(actions between vision calls)",
                font=('Consolas', 8), fg='#555', bg='#1a1a2e').pack()

        # Action delay
        delay_frame = tk.Frame(settings_frame, bg='#1a1a2e')
        delay_frame.pack(side=tk.LEFT, padx=(0, 30))

        tk.Label(delay_frame, text="Action Delay:", font=('Consolas', 10),
                fg='#888', bg='#1a1a2e').pack(anchor='w')
        self.action_delay = tk.Scale(delay_frame, from_=0.05, to=0.5, resolution=0.01,
                                     orient=tk.HORIZONTAL, length=150, bg='#1a1a2e', fg='#ffaa00',
                                     highlightthickness=0, troughcolor='#333',
                                     command=self._on_setting_change)
        self.action_delay.set(0.1)
        self.action_delay.pack()
        tk.Label(delay_frame, text="(seconds between actions)",
                font=('Consolas', 8), fg='#555', bg='#1a1a2e').pack()

        # Max steps (0 = unlimited)
        steps_frame = tk.Frame(settings_frame, bg='#1a1a2e')
        steps_frame.pack(side=tk.LEFT, padx=(0, 30))

        tk.Label(steps_frame, text="Max Steps:", font=('Consolas', 10),
                fg='#888', bg='#1a1a2e').pack(anchor='w')

        steps_input = tk.Frame(steps_frame, bg='#1a1a2e')
        steps_input.pack()
        self.max_steps = tk.Spinbox(steps_input, from_=0, to=100000, width=8,
                                    font=('Consolas', 11), bg='#222', fg='white',
                                    buttonbackground='#333', insertbackground='white')
        self.max_steps.delete(0, tk.END)
        self.max_steps.insert(0, "0")
        self.max_steps.pack()
        tk.Label(steps_frame, text="(0 = unlimited)",
                font=('Consolas', 8), fg='#555', bg='#1a1a2e').pack()

        # Checkboxes frame
        checks_frame = tk.Frame(settings_frame, bg='#1a1a2e')
        checks_frame.pack(side=tk.LEFT)

        # Auto-launch game checkbox
        self.auto_launch_var = tk.BooleanVar(value=True)
        self.auto_launch_cb = tk.Checkbutton(checks_frame, text="Auto-launch game",
                                             variable=self.auto_launch_var,
                                             font=('Consolas', 10), fg='#888', bg='#1a1a2e',
                                             selectcolor='#333', activebackground='#1a1a2e')
        self.auto_launch_cb.pack(anchor='w')

        # Turbo mode checkbox
        self.turbo_var = tk.BooleanVar(value=True)
        self.turbo_cb = tk.Checkbutton(checks_frame, text="Turbo mode (fast-forward)",
                                       variable=self.turbo_var,
                                       font=('Consolas', 10), fg='#00ff88', bg='#1a1a2e',
                                       selectcolor='#333', activebackground='#1a1a2e')
        self.turbo_cb.pack(anchor='w')

        # Use learning checkbox
        self.use_learning_var = tk.BooleanVar(value=True)
        self.use_learning_cb = tk.Checkbutton(checks_frame, text="Learn from history",
                                              variable=self.use_learning_var,
                                              font=('Consolas', 10), fg='#ffaa00', bg='#1a1a2e',
                                              selectcolor='#333', activebackground='#1a1a2e')
        self.use_learning_cb.pack(anchor='w')

    def _on_start(self):
        """Handle start button click."""
        self.is_running = True
        self.is_paused = False
        self._update_button_states()
        if self.on_start:
            self.on_start()

    def _on_stop(self):
        """Handle stop button click."""
        self.is_running = False
        self.is_paused = False
        self._update_button_states()
        if self.on_stop:
            self.on_stop()

    def _on_pause(self):
        """Handle pause button click."""
        self.is_paused = not self.is_paused
        self._update_button_states()
        if self.on_pause:
            self.on_pause(self.is_paused)

    def _on_reset(self):
        """Handle reset button click."""
        if self.on_reset:
            self.on_reset()

    def _on_setting_change(self, *args):
        """Handle setting changes."""
        if self.on_settings_change:
            self.on_settings_change(self.get_settings())

    def _update_button_states(self):
        """Update button states based on running/paused status."""
        if self.is_running:
            self.start_btn.config(state=tk.DISABLED, bg='#1a3a1a')
            self.stop_btn.config(state=tk.NORMAL, bg='#5e2a2a')
            self.pause_btn.config(state=tk.NORMAL)

            if self.is_paused:
                self.pause_btn.config(text="▶ RESUME", bg='#2a5e2a')
            else:
                self.pause_btn.config(text="⏸ PAUSE", bg='#5e5e2a')
        else:
            self.start_btn.config(state=tk.NORMAL, bg='#2a5e2a')
            self.stop_btn.config(state=tk.DISABLED, bg='#3a2a2a')
            self.pause_btn.config(state=tk.DISABLED, text="⏸ PAUSE", bg='#3a3a2a')

    def get_settings(self) -> dict:
        """Get current settings as a dictionary."""
        return {
            'vision_interval': self.vision_interval.get(),
            'action_delay': self.action_delay.get(),
            'max_steps': int(self.max_steps.get()),
            'auto_launch': self.auto_launch_var.get(),
            'turbo': self.turbo_var.get(),
            'use_learning': self.use_learning_var.get(),
        }

    def set_settings(self, settings: dict):
        """Set settings from a dictionary."""
        if 'vision_interval' in settings:
            self.vision_interval.set(settings['vision_interval'])
        if 'action_delay' in settings:
            self.action_delay.set(settings['action_delay'])
        if 'max_steps' in settings:
            self.max_steps.delete(0, tk.END)
            self.max_steps.insert(0, str(settings['max_steps']))
        if 'auto_launch' in settings:
            self.auto_launch_var.set(settings['auto_launch'])
