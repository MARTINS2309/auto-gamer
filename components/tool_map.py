"""
Tool Map Component - Detailed view of active tools and their outputs.
"""

import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time


@dataclass
class ToolState:
    """State of a tool."""
    name: str
    active: bool = False
    use_count: int = 0
    last_output: str = ""
    history: List[str] = field(default_factory=list)
    color: str = "#00ff88"


class ToolMap(tk.LabelFrame):
    """Detailed tool activity panel."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, text="TOOL ACTIVITY", bg='#1a1a2e', fg='#666',
                        font=('Consolas', 11), **kwargs)

        self.tools: Dict[str, ToolState] = {
            "vision": ToolState("VISION", color="#00aaff"),
            "rules": ToolState("RULES", color="#ffaa00"),
            "input": ToolState("INPUT", color="#00ff88"),
            "coach": ToolState("COACH", color="#ff4444"),
            "memory": ToolState("MEMORY", color="#ff00ff"),
        }

        self._build_ui()

    def _build_ui(self):
        """Build the tool panel UI."""
        container = tk.Frame(self, bg='#1a1a2e')
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tool_frames: Dict[str, dict] = {}

        for tool_name, tool in self.tools.items():
            frame = tk.Frame(container, bg='#0d0d1a', relief=tk.FLAT, bd=1)
            frame.pack(fill=tk.X, pady=1)

            # Header row with output inline
            header = tk.Frame(frame, bg='#0d0d1a')
            header.pack(fill=tk.X, padx=5, pady=3)

            # Status indicator
            indicator = tk.Label(header, text="●", font=('Consolas', 10),
                               fg='#333', bg='#0d0d1a')
            indicator.pack(side=tk.LEFT)

            # Name
            name_lbl = tk.Label(header, text=tool.name, font=('Consolas', 9, 'bold'),
                               fg=tool.color, bg='#0d0d1a', width=7, anchor='w')
            name_lbl.pack(side=tk.LEFT, padx=(3, 5))

            # Count
            count_lbl = tk.Label(header, text="0", font=('Consolas', 8),
                                fg='#555', bg='#0d0d1a', width=4)
            count_lbl.pack(side=tk.RIGHT)

            # Output area (single line, inline)
            output = tk.Text(frame, height=1, bg='#0a0a14', fg='#888',
                           font=('Consolas', 8), wrap=tk.NONE,
                           state=tk.DISABLED, borderwidth=0, highlightthickness=0)
            output.pack(fill=tk.X, padx=5, pady=(0, 3))

            self.tool_frames[tool_name] = {
                "frame": frame,
                "indicator": indicator,
                "name": name_lbl,
                "count": count_lbl,
                "output": output,
            }

    def activate(self, tool_name: str):
        """Show tool as active."""
        if tool_name not in self.tool_frames:
            return

        self.tools[tool_name].active = True
        f = self.tool_frames[tool_name]
        f["indicator"].config(fg=self.tools[tool_name].color)
        f["frame"].config(bg='#1a1a2e')

    def deactivate(self, tool_name: str):
        """Show tool as inactive."""
        if tool_name not in self.tool_frames:
            return

        tool = self.tools[tool_name]
        tool.active = False
        tool.use_count += 1

        f = self.tool_frames[tool_name]
        f["indicator"].config(fg='#333')
        f["frame"].config(bg='#0d0d1a')
        f["count"].config(text=str(tool.use_count))

    def set_output(self, tool_name: str, text: str):
        """Set the output text for a tool."""
        if tool_name not in self.tool_frames:
            return

        self.tools[tool_name].last_output = text
        self.tools[tool_name].history.append(text)

        # Keep only last 20 entries
        if len(self.tools[tool_name].history) > 20:
            self.tools[tool_name].history = self.tools[tool_name].history[-20:]

        f = self.tool_frames[tool_name]
        output = f["output"]
        output.config(state=tk.NORMAL)
        output.delete(1.0, tk.END)
        output.insert(tk.END, text)
        output.config(state=tk.DISABLED)

    def reset_counts(self):
        """Reset all counts."""
        for name, tool in self.tools.items():
            tool.use_count = 0
            tool.active = False
            tool.last_output = ""
            tool.history.clear()

            f = self.tool_frames[name]
            f["indicator"].config(fg='#333')
            f["count"].config(text="0")

            output = f["output"]
            output.config(state=tk.NORMAL)
            output.delete(1.0, tk.END)
            output.config(state=tk.DISABLED)
