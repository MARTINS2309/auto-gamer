"""
Activity Log Component - Scrolling log of actions and events.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LogEntry:
    """A single log entry."""
    timestamp: datetime
    level: str  # 'info', 'action', 'vision', 'warning', 'error'
    message: str
    details: Optional[str] = None


class ActivityLog(tk.LabelFrame):
    """Scrolling activity log with colored entries."""

    # Color scheme for different log levels
    LEVEL_COLORS = {
        'info': '#888888',
        'action': '#00aaff',
        'vision': '#aa00ff',
        'warning': '#ffaa00',
        'error': '#ff4444',
        'success': '#44ff44',
        'battle': '#ff6600',
        'dialogue': '#66ff66',
    }

    def __init__(self, parent, max_entries: int = 100, **kwargs):
        super().__init__(parent, text="ACTIVITY LOG", bg='#1a1a2e', fg='#666',
                        font=('Consolas', 11), **kwargs)

        self.max_entries = max_entries
        self.entries: list[LogEntry] = []

        self._build_ui()

    def _build_ui(self):
        """Build the activity log UI."""
        # Main container
        container = tk.Frame(self, bg='#1a1a2e')
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Text widget with scrollbar
        self.text = tk.Text(container, bg='#0d0d1a', fg='#888',
                           font=('Consolas', 9), wrap=tk.WORD,
                           state=tk.DISABLED, cursor='arrow',
                           borderwidth=0, highlightthickness=0)

        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL,
                                  command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure text tags for different levels
        for level, color in self.LEVEL_COLORS.items():
            self.text.tag_configure(level, foreground=color)

        self.text.tag_configure('timestamp', foreground='#555')
        self.text.tag_configure('details', foreground='#666', font=('Consolas', 8))

        # Style the scrollbar
        style = ttk.Style()
        style.configure("TScrollbar", background='#333', troughcolor='#1a1a2e')

    def log(self, message: str, level: str = 'info', details: str = None):
        """Add a log entry."""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            details=details
        )
        self.entries.append(entry)

        # Trim old entries
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]
            self._rebuild_display()
        else:
            self._append_entry(entry)

    def _append_entry(self, entry: LogEntry):
        """Append a single entry to the display."""
        self.text.configure(state=tk.NORMAL)

        # Format: [HH:MM:SS] message
        time_str = entry.timestamp.strftime("%H:%M:%S")

        self.text.insert(tk.END, f"[{time_str}] ", 'timestamp')
        self.text.insert(tk.END, f"{entry.message}\n", entry.level)

        if entry.details:
            self.text.insert(tk.END, f"    {entry.details}\n", 'details')

        self.text.configure(state=tk.DISABLED)
        self.text.see(tk.END)  # Auto-scroll to bottom

    def _rebuild_display(self):
        """Rebuild the entire display from entries."""
        self.text.configure(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)

        for entry in self.entries:
            time_str = entry.timestamp.strftime("%H:%M:%S")
            self.text.insert(tk.END, f"[{time_str}] ", 'timestamp')
            self.text.insert(tk.END, f"{entry.message}\n", entry.level)
            if entry.details:
                self.text.insert(tk.END, f"    {entry.details}\n", 'details')

        self.text.configure(state=tk.DISABLED)
        self.text.see(tk.END)

    def clear(self):
        """Clear all log entries."""
        self.entries.clear()
        self.text.configure(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)
        self.text.configure(state=tk.DISABLED)

    # Convenience methods for common log types
    def info(self, message: str, details: str = None):
        """Log an info message."""
        self.log(message, 'info', details)

    def action(self, message: str, details: str = None):
        """Log an action."""
        self.log(message, 'action', details)

    def vision(self, message: str, details: str = None):
        """Log a vision event."""
        self.log(message, 'vision', details)

    def warning(self, message: str, details: str = None):
        """Log a warning."""
        self.log(message, 'warning', details)

    def error(self, message: str, details: str = None):
        """Log an error."""
        self.log(message, 'error', details)

    def success(self, message: str, details: str = None):
        """Log a success."""
        self.log(message, 'success', details)

    def battle(self, message: str, details: str = None):
        """Log a battle event."""
        self.log(message, 'battle', details)

    def dialogue(self, message: str, details: str = None):
        """Log a dialogue event."""
        self.log(message, 'dialogue', details)
