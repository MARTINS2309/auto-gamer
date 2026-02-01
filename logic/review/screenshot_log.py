"""
Screenshot Logger - Saves sequential screenshots per run for review.

Creates a folder per run with:
- Screenshots numbered sequentially
- Metadata JSON with decision info per screenshot
- Summary file at the end

Reviewers (human or AI) can later examine if decisions matched the screen state.
"""

import json
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List


@dataclass
class ScreenshotEntry:
    """Metadata for a single screenshot."""
    step: int
    frame: int
    timestamp: float
    scene: str
    action: str
    reason: str
    # Game state
    x: int = 0
    y: int = 0
    map_num: int = 0
    in_battle: bool = False
    player_hp: int = 0
    enemy_hp: int = 0
    # Genome info
    genome_id: str = ""
    weight_used: float = 0.0


class ScreenshotLogger:
    """Logs screenshots and decisions for post-run review."""

    def __init__(self, base_dir: str = "data/screenshots"):
        self.base_dir = Path(base_dir)
        self.run_dir: Optional[Path] = None
        self.entries: List[ScreenshotEntry] = []
        self.run_id: str = ""
        self.genome_id: str = ""
        self.start_time: float = 0

    def start_run(self, genome_id: str = ""):
        """Start a new run - creates a timestamped folder."""
        self.genome_id = genome_id
        self.start_time = time.time()
        self.entries = []

        # Create run folder: YYYYMMDD_HHMMSS_genomeid
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"{timestamp}_{genome_id[:8]}" if genome_id else timestamp
        self.run_dir = self.base_dir / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Write run info
        info = {
            "run_id": self.run_id,
            "genome_id": genome_id,
            "start_time": datetime.now().isoformat(),
            "start_timestamp": self.start_time,
        }
        (self.run_dir / "run_info.json").write_text(json.dumps(info, indent=2))

        return self.run_dir

    def log_screenshot(self, sender, step: int, scene: str, action: str,
                       reason: str, game_state=None, weight: float = 0.0) -> Optional[str]:
        """
        Take and log a screenshot with decision metadata.
        Returns the screenshot path or None if failed.
        """
        if not self.run_dir or not sender:
            return None

        # Get frame from emulator
        frame = 0
        if game_state:
            frame = getattr(game_state, 'frame', 0)

        # Screenshot filename: step_frame_scene_action.png
        filename = f"{step:06d}_{frame:08d}_{scene}_{action}.png"
        screenshot_path = self.run_dir / filename

        # Take screenshot via emulator
        result = sender.screenshot(str(screenshot_path))
        if not result:
            return None

        # Create entry
        entry = ScreenshotEntry(
            step=step,
            frame=frame,
            timestamp=time.time(),
            scene=scene,
            action=action,
            reason=reason,
            genome_id=self.genome_id,
            weight_used=weight,
        )

        # Add game state info if available
        if game_state:
            entry.x = getattr(game_state, 'x', 0)
            entry.y = getattr(game_state, 'y', 0)
            entry.map_num = getattr(game_state, 'map_num', 0)
            entry.in_battle = getattr(game_state, 'battle', False)
            entry.player_hp = getattr(game_state, 'player_hp', 0)
            entry.enemy_hp = getattr(game_state, 'enemy_hp', 0)

        self.entries.append(entry)

        # Write metadata alongside screenshot
        meta_path = screenshot_path.with_suffix('.json')
        meta_path.write_text(json.dumps(asdict(entry), indent=2))

        return str(screenshot_path)

    def end_run(self, run_stats=None) -> Path:
        """End run and write summary."""
        if not self.run_dir:
            return Path(".")

        # Write all entries to index
        index = {
            "run_id": self.run_id,
            "genome_id": self.genome_id,
            "total_screenshots": len(self.entries),
            "duration_seconds": time.time() - self.start_time,
            "entries": [asdict(e) for e in self.entries],
        }

        if run_stats:
            index["run_stats"] = {
                "total_steps": run_stats.total_steps,
                "battles_won": run_stats.battles_won,
                "battles_lost": run_stats.battles_lost,
                "pokemon_caught": run_stats.pokemon_caught,
                "badges_earned": run_stats.badges_earned,
                "deaths": run_stats.deaths,
                "fitness": run_stats.fitness(),
            }

        (self.run_dir / "index.json").write_text(json.dumps(index, indent=2))

        # Write summary for quick review
        summary_lines = [
            f"Run: {self.run_id}",
            f"Genome: {self.genome_id}",
            f"Screenshots: {len(self.entries)}",
            f"Duration: {time.time() - self.start_time:.1f}s",
            "",
            "Scene Distribution:",
        ]

        # Count scenes
        scene_counts = {}
        action_counts = {}
        for entry in self.entries:
            scene_counts[entry.scene] = scene_counts.get(entry.scene, 0) + 1
            action_counts[entry.action] = action_counts.get(entry.action, 0) + 1

        for scene, count in sorted(scene_counts.items(), key=lambda x: -x[1]):
            summary_lines.append(f"  {scene}: {count}")

        summary_lines.append("")
        summary_lines.append("Action Distribution:")
        for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
            summary_lines.append(f"  {action}: {count}")

        (self.run_dir / "summary.txt").write_text("\n".join(summary_lines))

        return self.run_dir

    def get_run_path(self) -> Optional[Path]:
        """Get current run directory."""
        return self.run_dir
