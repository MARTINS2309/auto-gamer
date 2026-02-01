"""
Run Logger - Logs actions and events for later analysis.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from logic.paths import LOGS_DIR


@dataclass
class StepEntry:
    """Single step log entry."""
    step: int
    timestamp: float
    scene: str
    action: str
    reason: str


@dataclass
class RunLog:
    """Complete run log."""
    start_time: str
    end_time: str = ""
    total_steps: int = 0
    steps: List[StepEntry] = field(default_factory=list)
    scene_counts: Dict[str, int] = field(default_factory=dict)
    action_counts: Dict[str, int] = field(default_factory=dict)

    def save(self, path: str = None):
        if path is None:
            safe_time = self.start_time.replace(":", "-")
            path = f"run_log_{safe_time}.json"

        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2, default=str)


class RunLogger:
    """Logs a run for later analysis."""

    def __init__(self, log_dir: Path = None):
        self.log_dir = log_dir or LOGS_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_run: Optional[RunLog] = None

    def start_run(self):
        """Start a new run log."""
        self.current_run = RunLog(start_time=datetime.now().isoformat())

    def log_step(self, step: int, timestamp: float, scene: str, action: str, reason: str = ""):
        """Log a single step."""
        if not self.current_run:
            self.start_run()

        entry = StepEntry(step=step, timestamp=timestamp, scene=scene, action=action, reason=reason)
        self.current_run.steps.append(entry)
        self.current_run.total_steps = step

        # Update counts
        self.current_run.scene_counts[scene] = self.current_run.scene_counts.get(scene, 0) + 1
        self.current_run.action_counts[action] = self.current_run.action_counts.get(action, 0) + 1

    def end_run(self) -> Optional[str]:
        """End and save the run log. Returns the file path."""
        if not self.current_run:
            return None

        self.current_run.end_time = datetime.now().isoformat()
        safe_time = self.current_run.start_time.replace(":", "-")
        path = self.log_dir / f"run_{safe_time}.json"
        self.current_run.save(str(path))

        result = str(path)
        self.current_run = None
        return result
