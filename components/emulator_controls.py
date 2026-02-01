"""
Emulator Controls Component - Direct control of mGBA via scripting API.

Controls:
- Save/Load states (slots 0-9)
- Reset game
- Speed control (turbo, pause)
- Frame advance
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class EmulatorControls(tk.LabelFrame):
    """Controls for mGBA emulator via socket API."""

    def __init__(self, parent, on_command: Optional[Callable] = None, **kwargs):
        super().__init__(parent, text="EMULATOR", bg='#1a1a2e', fg='#666',
                        font=('Consolas', 10), **kwargs)

        self.on_command = on_command  # Callback for commands
        self.sender = None  # InputSender reference
        self.current_slot = tk.IntVar(value=1)
        self.connected = False

        self._build_ui()

    def _build_ui(self):
        """Build the emulator controls UI - compact horizontal layout."""
        # Main container - horizontal layout
        container = tk.Frame(self, bg='#1a1a2e')
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # === Left section: Connection + State slots ===
        left_section = tk.Frame(container, bg='#1a1a2e')
        left_section.pack(side=tk.LEFT, fill=tk.Y)

        # Connection status
        self.status_label = tk.Label(left_section, text="● Disconnected", fg='#ff4444',
                                     bg='#1a1a2e', font=('Consolas', 8))
        self.status_label.pack(anchor='w')

        # State slot selector
        slot_frame = tk.Frame(left_section, bg='#1a1a2e')
        slot_frame.pack(fill=tk.X, pady=(2, 0))

        tk.Label(slot_frame, text="Slot:", fg='#666', bg='#1a1a2e',
                font=('Consolas', 8)).pack(side=tk.LEFT)

        for i in range(10):
            btn = tk.Radiobutton(slot_frame, text=str(i), variable=self.current_slot,
                                value=i, bg='#1a1a2e', fg='#888',
                                selectcolor='#2a4a6a', activebackground='#1a1a2e',
                                font=('Consolas', 7), indicatoron=0, width=2,
                                relief=tk.FLAT, bd=1)
            btn.pack(side=tk.LEFT, padx=1)

        # === Middle section: Save/Load buttons ===
        mid_section = tk.Frame(container, bg='#1a1a2e')
        mid_section.pack(side=tk.LEFT, fill=tk.Y, padx=(15, 0))

        # Row 1: Save/Load
        row1 = tk.Frame(mid_section, bg='#1a1a2e')
        row1.pack(fill=tk.X)

        self.save_btn = tk.Button(row1, text="💾 Save", command=self._save_state,
                                  bg='#2a5e2a', fg='white', font=('Consolas', 9),
                                  width=7, relief=tk.FLAT, cursor='hand2')
        self.save_btn.pack(side=tk.LEFT, padx=(0, 3))

        self.load_btn = tk.Button(row1, text="📂 Load", command=self._load_state,
                                  bg='#2a4a6a', fg='white', font=('Consolas', 9),
                                  width=7, relief=tk.FLAT, cursor='hand2')
        self.load_btn.pack(side=tk.LEFT)

        # Row 2: Quick Save/Load
        row2 = tk.Frame(mid_section, bg='#1a1a2e')
        row2.pack(fill=tk.X, pady=(3, 0))

        self.qsave_btn = tk.Button(row2, text="Q.Save", command=self._quick_save,
                                   bg='#1a4a1a', fg='white', font=('Consolas', 8),
                                   width=7, relief=tk.FLAT, cursor='hand2')
        self.qsave_btn.pack(side=tk.LEFT, padx=(0, 3))

        self.qload_btn = tk.Button(row2, text="Q.Load", command=self._quick_load,
                                   bg='#1a3a5a', fg='white', font=('Consolas', 8),
                                   width=7, relief=tk.FLAT, cursor='hand2')
        self.qload_btn.pack(side=tk.LEFT)

        # === Right section: Emulator controls ===
        right_section = tk.Frame(container, bg='#1a1a2e')
        right_section.pack(side=tk.LEFT, fill=tk.Y, padx=(15, 0))

        # Row 1: Reset, Frame
        row3 = tk.Frame(right_section, bg='#1a1a2e')
        row3.pack(fill=tk.X)

        self.reset_btn = tk.Button(row3, text="↺ Reset", command=self._reset,
                                   bg='#5e2a2a', fg='white', font=('Consolas', 9),
                                   width=7, relief=tk.FLAT, cursor='hand2')
        self.reset_btn.pack(side=tk.LEFT, padx=(0, 3))

        self.frame_btn = tk.Button(row3, text="⏭ Frame", command=self._frame_advance,
                                   bg='#3a3a4e', fg='white', font=('Consolas', 9),
                                   width=7, relief=tk.FLAT, cursor='hand2')
        self.frame_btn.pack(side=tk.LEFT)

        # Row 2: Screenshot, Turbo
        row4 = tk.Frame(right_section, bg='#1a1a2e')
        row4.pack(fill=tk.X, pady=(3, 0))

        self.screenshot_btn = tk.Button(row4, text="📷 Shot", command=self._take_screenshot,
                                        bg='#4a3a6a', fg='white', font=('Consolas', 8),
                                        width=7, relief=tk.FLAT, cursor='hand2')
        self.screenshot_btn.pack(side=tk.LEFT, padx=(0, 3))

        self.turbo_var = tk.BooleanVar(value=False)
        self.turbo_btn = tk.Checkbutton(row4, text="⚡Turbo", variable=self.turbo_var,
                                        command=self._toggle_turbo, font=('Consolas', 8),
                                        fg='#00ff88', bg='#1a1a2e', selectcolor='#2a4a2a',
                                        activebackground='#1a1a2e', indicatoron=0,
                                        width=7, relief=tk.FLAT, cursor='hand2')
        self.turbo_btn.pack(side=tk.LEFT)

        # Initially disable all buttons
        self._set_buttons_enabled(False)

    def set_sender(self, sender):
        """Set the InputSender reference for direct control."""
        self.sender = sender
        self._update_connection_status()

    def _update_connection_status(self):
        """Update the connection status display."""
        if self.sender and self.sender.is_connected:
            self.status_label.config(text="● Connected", fg='#44ff44')
            self.connected = True
            self._set_buttons_enabled(True)
        else:
            self.status_label.config(text="● Disconnected", fg='#ff4444')
            self.connected = False
            self._set_buttons_enabled(False)

    def _set_buttons_enabled(self, enabled: bool):
        """Enable or disable all control buttons."""
        state = tk.NORMAL if enabled else tk.DISABLED
        for btn in [self.save_btn, self.load_btn, self.reset_btn,
                   self.frame_btn, self.screenshot_btn,
                   self.qsave_btn, self.qload_btn]:
            btn.config(state=state)

    def _save_state(self):
        """Save state to current slot."""
        if not self.sender or not self.sender.is_connected:
            return
        slot = self.current_slot.get()
        if self.sender.save_state(slot):
            self._log(f"Saved state to slot {slot}", "success")
        else:
            self._log(f"Failed to save state", "error")

    def _load_state(self):
        """Load state from current slot."""
        if not self.sender or not self.sender.is_connected:
            return
        slot = self.current_slot.get()
        if self.sender.load_state(slot):
            self._log(f"Loaded state from slot {slot}", "success")
        else:
            self._log(f"Failed to load state", "error")

    def _quick_save(self):
        """Quick save to slot 0."""
        if not self.sender or not self.sender.is_connected:
            return
        if self.sender.save_state(0):
            self._log("Quick saved (slot 0)", "success")

    def _quick_load(self):
        """Quick load from slot 0."""
        if not self.sender or not self.sender.is_connected:
            return
        if self.sender.load_state(0):
            self._log("Quick loaded (slot 0)", "success")

    def _reset(self):
        """Reset the emulator."""
        if not self.sender or not self.sender.is_connected:
            return
        if self.sender.reset():
            self._log("Emulator reset", "warning")
        else:
            self._log("Reset failed", "error")

    def _frame_advance(self):
        """Advance one frame."""
        if not self.sender or not self.sender.is_connected:
            return
        frame = self.sender.frame_advance(1)
        if frame is not None:
            self._log(f"Frame: {frame}", "info")

    def _toggle_turbo(self):
        """Toggle turbo mode."""
        if not self.sender:
            return
        if self.turbo_var.get():
            self.sender.enable_turbo()
            self.turbo_btn.config(bg='#2a6a2a')
            self._log("Turbo ON", "success")
        else:
            self.sender.disable_turbo()
            self.turbo_btn.config(bg='#1a1a2e')
            self._log("Turbo OFF", "info")

    def _take_screenshot(self):
        """Take a screenshot."""
        if not self.sender or not self.sender.is_connected:
            return
        import time
        filename = f"screenshot_{int(time.time())}.png"
        path = self.sender.screenshot(filename)
        if path:
            self._log(f"Screenshot: {path}", "success")
        else:
            self._log("Screenshot failed", "error")

    def _log(self, msg: str, level: str = "info"):
        """Send log message via callback."""
        if self.on_command:
            self.on_command({"type": "log", "msg": msg, "level": level})

    def sync_turbo_state(self, turbo_active: bool):
        """Sync turbo checkbox with actual state."""
        self.turbo_var.set(turbo_active)
        if turbo_active:
            self.turbo_btn.config(bg='#2a6a2a')
        else:
            self.turbo_btn.config(bg='#1a1a2e')
