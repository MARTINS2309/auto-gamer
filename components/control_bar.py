"""
Unified Control Bar - All controls organized by function.

Sections:
1. Preflight: Status indicators for mGBA, socket, ROM
2. Run Controls: Start, Pause, Stop, Reset
3. Timing: Vision interval, Action delay, Max steps
4. Options: Auto-launch, Learning mode
5. Emulator: Save/Load states, Reset, Frame, Screenshot, Turbo
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Dict


class ControlBar(tk.Frame):
    """Unified control bar with all controls organized by section."""

    def __init__(self, parent,
                 on_start: Optional[Callable] = None,
                 on_stop: Optional[Callable] = None,
                 on_pause: Optional[Callable] = None,
                 on_reset: Optional[Callable] = None,
                 on_settings_change: Optional[Callable] = None,
                 on_emu_command: Optional[Callable] = None,
                 on_preflight_check: Optional[Callable] = None,
                 on_launch_mgba: Optional[Callable] = None,
                 **kwargs):
        super().__init__(parent, bg='#1a1a2e', **kwargs)

        # Callbacks
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_pause = on_pause
        self.on_reset = on_reset
        self.on_settings_change = on_settings_change
        self.on_emu_command = on_emu_command
        self.on_preflight_check = on_preflight_check
        self.on_launch_mgba = on_launch_mgba

        # State
        self.is_running = False
        self.is_paused = False
        self.sender = None  # InputSender reference
        self.connected = False

        # Preflight state
        self.preflight_status: Dict[str, bool] = {
            'mgba_window': False,
            'socket_connected': False,
            'rom_loaded': False,
        }
        self._preflight_timer = None

        # Settings variables
        self.current_slot = tk.IntVar(value=1)
        self.turbo_var = tk.BooleanVar(value=False)
        self.auto_launch_var = tk.BooleanVar(value=True)
        self.use_learning_var = tk.BooleanVar(value=True)
        self.turbo_setting_var = tk.BooleanVar(value=True)
        self.auto_train_var = tk.BooleanVar(value=False)
        self.train_runs_var = tk.IntVar(value=10)

        self._build_ui()

        # Start preflight auto-check
        self._schedule_preflight_check()

    def _build_ui(self):
        """Build the unified control bar."""
        # Main horizontal container
        main = tk.Frame(self, bg='#1a1a2e')
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # === Section 0: Preflight Status ===
        self._build_preflight_section(main)

        # Vertical separator
        self._add_separator(main)

        # === Section 1: Run Controls ===
        self._build_run_section(main)

        # Vertical separator
        self._add_separator(main)

        # === Section 2: Timing Settings ===
        self._build_timing_section(main)

        # Vertical separator
        self._add_separator(main)

        # === Section 3: Options ===
        self._build_options_section(main)

        # Vertical separator
        self._add_separator(main)

        # === Section 4: Emulator Controls ===
        self._build_emulator_section(main)

    def _add_separator(self, parent):
        """Add a vertical separator."""
        sep = tk.Frame(parent, bg='#333', width=2)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

    def _build_preflight_section(self, parent):
        """Build preflight status indicators section."""
        section = tk.Frame(parent, bg='#1a1a2e')
        section.pack(side=tk.LEFT, fill=tk.Y)

        # Section label
        tk.Label(section, text="PREFLIGHT", font=('Consolas', 8, 'bold'),
                fg='#555', bg='#1a1a2e').pack(anchor='w')

        # Status indicators row
        status_row = tk.Frame(section, bg='#1a1a2e')
        status_row.pack(fill=tk.X)

        # Status indicator style: colored dot + label
        self.preflight_indicators = {}

        # mGBA Window indicator
        mgba_frame = tk.Frame(status_row, bg='#1a1a2e')
        mgba_frame.pack(side=tk.LEFT, padx=(0, 8))
        self.preflight_indicators['mgba_window'] = {
            'dot': tk.Label(mgba_frame, text="●", font=('Consolas', 10),
                           fg='#ff4444', bg='#1a1a2e'),
            'label': tk.Label(mgba_frame, text="mGBA", font=('Consolas', 8),
                             fg='#888', bg='#1a1a2e')
        }
        self.preflight_indicators['mgba_window']['dot'].pack(side=tk.LEFT)
        self.preflight_indicators['mgba_window']['label'].pack(side=tk.LEFT)

        # Socket Connected indicator
        socket_frame = tk.Frame(status_row, bg='#1a1a2e')
        socket_frame.pack(side=tk.LEFT, padx=(0, 8))
        self.preflight_indicators['socket_connected'] = {
            'dot': tk.Label(socket_frame, text="●", font=('Consolas', 10),
                           fg='#ff4444', bg='#1a1a2e'),
            'label': tk.Label(socket_frame, text="Lua", font=('Consolas', 8),
                             fg='#888', bg='#1a1a2e')
        }
        self.preflight_indicators['socket_connected']['dot'].pack(side=tk.LEFT)
        self.preflight_indicators['socket_connected']['label'].pack(side=tk.LEFT)

        # ROM Loaded indicator
        rom_frame = tk.Frame(status_row, bg='#1a1a2e')
        rom_frame.pack(side=tk.LEFT, padx=(0, 8))
        self.preflight_indicators['rom_loaded'] = {
            'dot': tk.Label(rom_frame, text="●", font=('Consolas', 10),
                           fg='#ff4444', bg='#1a1a2e'),
            'label': tk.Label(rom_frame, text="ROM", font=('Consolas', 8),
                             fg='#888', bg='#1a1a2e')
        }
        self.preflight_indicators['rom_loaded']['dot'].pack(side=tk.LEFT)
        self.preflight_indicators['rom_loaded']['label'].pack(side=tk.LEFT)

        # Dynamic action button - changes based on preflight state
        self.action_btn = tk.Button(status_row, text="Launch", command=self._do_preflight_action,
                                    bg='#4a6a2a', fg='white', font=('Consolas', 8),
                                    width=8, relief=tk.FLAT, cursor='hand2')
        self.action_btn.pack(side=tk.LEFT, padx=(5, 0))

    def _build_run_section(self, parent):
        """Build run control buttons section."""
        section = tk.Frame(parent, bg='#1a1a2e')
        section.pack(side=tk.LEFT, fill=tk.Y)

        # Section label
        tk.Label(section, text="RUN", font=('Consolas', 8, 'bold'),
                fg='#555', bg='#1a1a2e').pack(anchor='w')

        # Buttons row
        btns = tk.Frame(section, bg='#1a1a2e')
        btns.pack(fill=tk.X)

        # Start button
        self.start_btn = tk.Button(btns, text="START", command=self._on_start,
                                   bg='#2a5e2a', fg='white', font=('Consolas', 10, 'bold'),
                                   width=7, relief=tk.FLAT, cursor='hand2')
        self.start_btn.pack(side=tk.LEFT, padx=(0, 3))

        # Pause button
        self.pause_btn = tk.Button(btns, text="PAUSE", command=self._on_pause,
                                   bg='#5e5e2a', fg='white', font=('Consolas', 10, 'bold'),
                                   width=7, relief=tk.FLAT, state=tk.DISABLED, cursor='hand2')
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 3))

        # Stop button
        self.stop_btn = tk.Button(btns, text="STOP", command=self._on_stop,
                                  bg='#5e2a2a', fg='white', font=('Consolas', 10, 'bold'),
                                  width=7, relief=tk.FLAT, state=tk.DISABLED, cursor='hand2')
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 3))

        # Reset button
        self.reset_btn = tk.Button(btns, text="RESET", command=self._on_reset,
                                   bg='#3a3a4e', fg='white', font=('Consolas', 10, 'bold'),
                                   width=7, relief=tk.FLAT, cursor='hand2')
        self.reset_btn.pack(side=tk.LEFT)

    def _build_timing_section(self, parent):
        """Build timing settings section."""
        section = tk.Frame(parent, bg='#1a1a2e')
        section.pack(side=tk.LEFT, fill=tk.Y)

        # Section label
        tk.Label(section, text="TIMING", font=('Consolas', 8, 'bold'),
                fg='#555', bg='#1a1a2e').pack(anchor='w')

        # Settings row
        settings = tk.Frame(section, bg='#1a1a2e')
        settings.pack(fill=tk.X)

        # Stride (frames between decisions)
        stride_frame = tk.Frame(settings, bg='#1a1a2e')
        stride_frame.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(stride_frame, text="Stride:", font=('Consolas', 8),
                fg='#666', bg='#1a1a2e').pack(side=tk.LEFT)
        self.stride = tk.Scale(stride_frame, from_=1, to=60, orient=tk.HORIZONTAL,
                               length=80, bg='#1a1a2e', fg='#00aaff',
                               highlightthickness=0, troughcolor='#333',
                               font=('Consolas', 7), command=self._on_setting_change)
        self.stride.set(10)  # 10 frames = ~6 decisions/sec at 60fps
        self.stride.pack(side=tk.LEFT)

        # Batch size (actions per log entry)
        batch_frame = tk.Frame(settings, bg='#1a1a2e')
        batch_frame.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(batch_frame, text="Batch:", font=('Consolas', 8),
                fg='#666', bg='#1a1a2e').pack(side=tk.LEFT)
        self.batch_size = tk.Scale(batch_frame, from_=1, to=20, orient=tk.HORIZONTAL,
                                   length=80, bg='#1a1a2e', fg='#ffaa00',
                                   highlightthickness=0, troughcolor='#333',
                                   font=('Consolas', 7), command=self._on_setting_change)
        self.batch_size.set(5)  # 5 actions per log entry
        self.batch_size.pack(side=tk.LEFT)

        # Max steps
        steps_frame = tk.Frame(settings, bg='#1a1a2e')
        steps_frame.pack(side=tk.LEFT)

        tk.Label(steps_frame, text="Steps:", font=('Consolas', 8),
                fg='#666', bg='#1a1a2e').pack(side=tk.LEFT)
        self.max_steps = tk.Spinbox(steps_frame, from_=0, to=100000, width=6,
                                    font=('Consolas', 9), bg='#222', fg='white',
                                    buttonbackground='#333', insertbackground='white')
        self.max_steps.delete(0, tk.END)
        self.max_steps.insert(0, "0")
        self.max_steps.pack(side=tk.LEFT)

    def _build_options_section(self, parent):
        """Build options checkboxes section."""
        section = tk.Frame(parent, bg='#1a1a2e')
        section.pack(side=tk.LEFT, fill=tk.Y)

        # Section label
        tk.Label(section, text="OPTIONS", font=('Consolas', 8, 'bold'),
                fg='#555', bg='#1a1a2e').pack(anchor='w')

        # Checkboxes
        checks = tk.Frame(section, bg='#1a1a2e')
        checks.pack(fill=tk.X)

        # Auto-launch
        self.auto_launch_cb = tk.Checkbutton(checks, text="Auto-launch",
                                             variable=self.auto_launch_var,
                                             font=('Consolas', 9), fg='#888', bg='#1a1a2e',
                                             selectcolor='#333', activebackground='#1a1a2e')
        self.auto_launch_cb.pack(side=tk.LEFT)

        # Turbo setting (for run)
        self.turbo_setting_cb = tk.Checkbutton(checks, text="Turbo",
                                               variable=self.turbo_setting_var,
                                               font=('Consolas', 9), fg='#00ff88', bg='#1a1a2e',
                                               selectcolor='#333', activebackground='#1a1a2e')
        self.turbo_setting_cb.pack(side=tk.LEFT)

        # Learning
        self.use_learning_cb = tk.Checkbutton(checks, text="Learn",
                                              variable=self.use_learning_var,
                                              font=('Consolas', 9), fg='#ffaa00', bg='#1a1a2e',
                                              selectcolor='#333', activebackground='#1a1a2e')
        self.use_learning_cb.pack(side=tk.LEFT)

        # Auto-train (continuous learning)
        self.auto_train_cb = tk.Checkbutton(checks, text="Auto-train",
                                            variable=self.auto_train_var,
                                            font=('Consolas', 9), fg='#ff66ff', bg='#1a1a2e',
                                            selectcolor='#333', activebackground='#1a1a2e')
        self.auto_train_cb.pack(side=tk.LEFT)

        # Train runs count
        runs_frame = tk.Frame(checks, bg='#1a1a2e')
        runs_frame.pack(side=tk.LEFT, padx=(5, 0))
        tk.Label(runs_frame, text="x", font=('Consolas', 8),
                fg='#666', bg='#1a1a2e').pack(side=tk.LEFT)
        self.train_runs_spin = tk.Spinbox(runs_frame, from_=1, to=1000, width=4,
                                          textvariable=self.train_runs_var,
                                          font=('Consolas', 9), bg='#222', fg='#ff66ff',
                                          buttonbackground='#333', insertbackground='white')
        self.train_runs_spin.pack(side=tk.LEFT)

    def _build_emulator_section(self, parent):
        """Build emulator controls section."""
        section = tk.Frame(parent, bg='#1a1a2e')
        section.pack(side=tk.LEFT, fill=tk.Y)

        # Section label with connection status
        header = tk.Frame(section, bg='#1a1a2e')
        header.pack(fill=tk.X)

        tk.Label(header, text="EMULATOR", font=('Consolas', 8, 'bold'),
                fg='#555', bg='#1a1a2e').pack(side=tk.LEFT)

        self.status_label = tk.Label(header, text="", fg='#ff4444',
                                     bg='#1a1a2e', font=('Consolas', 7))
        self.status_label.pack(side=tk.LEFT, padx=(5, 0))

        # Controls row
        emu_row = tk.Frame(section, bg='#1a1a2e')
        emu_row.pack(fill=tk.X)

        # State slot selector (compact)
        slot_frame = tk.Frame(emu_row, bg='#1a1a2e')
        slot_frame.pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(slot_frame, text="Slot:", fg='#666', bg='#1a1a2e',
                font=('Consolas', 7)).pack(side=tk.LEFT)

        for i in range(10):
            btn = tk.Radiobutton(slot_frame, text=str(i), variable=self.current_slot,
                                value=i, bg='#1a1a2e', fg='#888',
                                selectcolor='#2a4a6a', activebackground='#1a1a2e',
                                font=('Consolas', 7), indicatoron=0, width=2,
                                relief=tk.FLAT, bd=1)
            btn.pack(side=tk.LEFT)

        # Save/Load buttons
        self.save_btn = tk.Button(emu_row, text="Save", command=self._save_state,
                                  bg='#2a5e2a', fg='white', font=('Consolas', 8),
                                  width=5, relief=tk.FLAT, cursor='hand2')
        self.save_btn.pack(side=tk.LEFT, padx=(5, 2))

        self.load_btn = tk.Button(emu_row, text="Load", command=self._load_state,
                                  bg='#2a4a6a', fg='white', font=('Consolas', 8),
                                  width=5, relief=tk.FLAT, cursor='hand2')
        self.load_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Reset/Frame buttons
        self.emu_reset_btn = tk.Button(emu_row, text="Reset", command=self._emu_reset,
                                       bg='#5e2a2a', fg='white', font=('Consolas', 8),
                                       width=5, relief=tk.FLAT, cursor='hand2')
        self.emu_reset_btn.pack(side=tk.LEFT, padx=(0, 2))

        self.frame_btn = tk.Button(emu_row, text="Frame", command=self._frame_advance,
                                   bg='#3a3a4e', fg='white', font=('Consolas', 8),
                                   width=5, relief=tk.FLAT, cursor='hand2')
        self.frame_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Screenshot button
        self.screenshot_btn = tk.Button(emu_row, text="Shot", command=self._take_screenshot,
                                        bg='#4a3a6a', fg='white', font=('Consolas', 8),
                                        width=4, relief=tk.FLAT, cursor='hand2')
        self.screenshot_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Turbo toggle (live)
        self.turbo_btn = tk.Checkbutton(emu_row, text="Turbo", variable=self.turbo_var,
                                        command=self._toggle_turbo, font=('Consolas', 8),
                                        fg='#00ff88', bg='#1a1a2e', selectcolor='#2a4a2a',
                                        activebackground='#1a1a2e', indicatoron=0,
                                        width=6, relief=tk.FLAT, cursor='hand2')
        self.turbo_btn.pack(side=tk.LEFT)

        # Initially disable emulator buttons
        self._set_emu_buttons_enabled(False)

    # -------------------------------------------------------------------------
    # Run Control Handlers
    # -------------------------------------------------------------------------

    def _on_start(self):
        """Handle start button click."""
        # Final preflight check before starting
        self._run_preflight()
        if not self.is_preflight_ready():
            self._log("Preflight checks failed - cannot start", "error")
            return

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
                self.pause_btn.config(text="RESUME", bg='#2a5e2a')
            else:
                self.pause_btn.config(text="PAUSE", bg='#5e5e2a')
        else:
            # Start button depends on preflight status
            if self.is_preflight_ready():
                self.start_btn.config(state=tk.NORMAL, bg='#2a5e2a')
            else:
                self.start_btn.config(state=tk.DISABLED, bg='#3a3a2a')
            self.stop_btn.config(state=tk.DISABLED, bg='#3a2a2a')
            self.pause_btn.config(state=tk.DISABLED, text="PAUSE", bg='#3a3a2a')

    # -------------------------------------------------------------------------
    # Preflight Check System
    # -------------------------------------------------------------------------

    def is_preflight_ready(self) -> bool:
        """Check if all preflight checks pass."""
        return all(self.preflight_status.values())

    def _schedule_preflight_check(self):
        """Schedule periodic preflight check."""
        self._run_preflight()
        # Re-check every 2 seconds when not running
        self._preflight_timer = self.after(2000, self._schedule_preflight_check)

    def _run_preflight(self):
        """Run preflight checks and update indicators."""
        # Call external preflight callback - this does fresh window detection
        if self.on_preflight_check:
            external_status = self.on_preflight_check()
            if external_status:
                self.preflight_status.update(external_status)

        # Update UI indicators
        self._update_preflight_ui()

        # Update action button based on state
        self._update_action_button()

        # Update start button state
        self._update_button_states()

    def _update_action_button(self):
        """Update the action button text based on preflight state."""
        if not self.preflight_status['mgba_window']:
            self.action_btn.config(text="Launch", bg='#4a6a2a')
        elif not self.preflight_status['socket_connected']:
            self.action_btn.config(text="Connect", bg='#6a4a2a')
        elif not self.preflight_status['rom_loaded']:
            self.action_btn.config(text="Load ROM", bg='#6a6a2a')
        else:
            self.action_btn.config(text="Ready", bg='#2a6a2a')

    def _do_preflight_action(self):
        """Execute the appropriate preflight action based on state."""
        if not self.preflight_status['mgba_window']:
            # Launch mGBA
            if self.on_launch_mgba:
                self.on_launch_mgba()
            # Re-check after launch
            self.after(2000, self._run_preflight)
        elif not self.preflight_status['socket_connected']:
            # Try to connect (re-run preflight which will attempt connection)
            self._run_preflight()
        else:
            # Just re-check status
            self._run_preflight()

    def _update_preflight_ui(self):
        """Update preflight indicator colors."""
        for key, status in self.preflight_status.items():
            if key in self.preflight_indicators:
                indicator = self.preflight_indicators[key]
                if status:
                    indicator['dot'].config(fg='#44ff44')  # Green
                else:
                    indicator['dot'].config(fg='#ff4444')  # Red

    def set_preflight_status(self, key: str, status: bool):
        """Manually set a preflight status."""
        if key in self.preflight_status:
            self.preflight_status[key] = status
            self._update_preflight_ui()
            self._update_button_states()

    def get_preflight_status(self) -> Dict[str, bool]:
        """Get current preflight status."""
        return self.preflight_status.copy()

    # -------------------------------------------------------------------------
    # Emulator Control Handlers
    # -------------------------------------------------------------------------

    def set_sender(self, sender):
        """Set the InputSender reference for direct control."""
        self.sender = sender
        self._update_connection_status()
        # Run preflight check with new sender
        self._run_preflight()

    def _update_connection_status(self):
        """Update the connection status display."""
        if self.sender and self.sender.is_connected:
            self.status_label.config(text="Connected", fg='#44ff44')
            self.connected = True
            self._set_emu_buttons_enabled(True)
        else:
            self.status_label.config(text="Disconnected", fg='#ff4444')
            self.connected = False
            self._set_emu_buttons_enabled(False)

    def _set_emu_buttons_enabled(self, enabled: bool):
        """Enable or disable emulator control buttons."""
        state = tk.NORMAL if enabled else tk.DISABLED
        for btn in [self.save_btn, self.load_btn, self.emu_reset_btn,
                   self.frame_btn, self.screenshot_btn]:
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

    def _emu_reset(self):
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
        if self.on_emu_command:
            self.on_emu_command({"type": "log", "msg": msg, "level": level})

    def sync_turbo_state(self, turbo_active: bool):
        """Sync turbo checkbox with actual state."""
        self.turbo_var.set(turbo_active)
        if turbo_active:
            self.turbo_btn.config(bg='#2a6a2a')
        else:
            self.turbo_btn.config(bg='#1a1a2e')

    # -------------------------------------------------------------------------
    # Settings
    # -------------------------------------------------------------------------

    def get_settings(self) -> dict:
        """Get current settings as a dictionary."""
        return {
            'stride': self.stride.get(),
            'batch_size': self.batch_size.get(),
            'max_steps': int(self.max_steps.get()),
            'auto_launch': self.auto_launch_var.get(),
            'turbo': self.turbo_setting_var.get(),
            'use_learning': self.use_learning_var.get(),
            'auto_train': self.auto_train_var.get(),
            'train_runs': self.train_runs_var.get(),
        }

    def set_settings(self, settings: dict):
        """Set settings from a dictionary."""
        if 'stride' in settings:
            self.stride.set(settings['stride'])
        if 'batch_size' in settings:
            self.batch_size.set(settings['batch_size'])
        if 'max_steps' in settings:
            self.max_steps.delete(0, tk.END)
            self.max_steps.insert(0, str(settings['max_steps']))
        if 'auto_launch' in settings:
            self.auto_launch_var.set(settings['auto_launch'])
        if 'turbo' in settings:
            self.turbo_setting_var.set(settings['turbo'])
        if 'use_learning' in settings:
            self.use_learning_var.set(settings['use_learning'])
        if 'auto_train' in settings:
            self.auto_train_var.set(settings['auto_train'])
        if 'train_runs' in settings:
            self.train_runs_var.set(settings['train_runs'])

    def destroy(self):
        """Clean up timers before destroying."""
        if self._preflight_timer:
            self.after_cancel(self._preflight_timer)
            self._preflight_timer = None
        super().destroy()
