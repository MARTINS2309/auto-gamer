"""
Weight Learner - Adjusts action weights based on run history.

Analyzes completed runs to find which actions led to:
- Scene transitions (progress)
- Battle wins/losses
- Dialogue advancement
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
from dataclasses import dataclass

from logic.paths import LOGS_DIR


@dataclass
class ActionOutcome:
    """Outcome of an action."""
    action: str
    scene: str
    led_to_change: bool  # Did scene change after this action?
    next_scene: str


class WeightLearner:
    """Learns optimal weights from run history."""

    def __init__(self, log_dir: Path = None):
        self.log_dir = log_dir or LOGS_DIR
        self.outcomes: Dict[str, List[ActionOutcome]] = defaultdict(list)
        self.learning_rate = 0.1

    def load_runs(self, limit: int = 10) -> int:
        """Load recent run logs. Returns number loaded."""
        if not self.log_dir.exists():
            return 0

        logs = sorted(self.log_dir.glob("run_*.json"), reverse=True)[:limit]
        loaded = 0

        for log_path in logs:
            try:
                with open(log_path) as f:
                    data = json.load(f)
                self._process_run(data)
                loaded += 1
            except Exception as e:
                print(f"Failed to load {log_path}: {e}")

        return loaded

    def _process_run(self, run_data: dict):
        """Extract action outcomes from a run."""
        steps = run_data.get("steps", [])

        for i, step in enumerate(steps[:-1]):
            scene = step.get("scene", "unknown")
            action = step.get("action", "")
            next_step = steps[i + 1]
            next_scene = next_step.get("scene", "unknown")

            outcome = ActionOutcome(
                action=action,
                scene=scene,
                led_to_change=scene != next_scene,
                next_scene=next_scene
            )
            self.outcomes[scene].append(outcome)

    def compute_weight_adjustments(self) -> Dict[str, Dict[str, float]]:
        """
        Compute weight adjustments based on outcomes.

        Returns dict of {scene: {action: adjustment}}
        Positive = increase weight, negative = decrease.
        """
        adjustments = {}

        for scene, outcomes in self.outcomes.items():
            if not outcomes:
                continue

            # Count successes per action
            action_stats = defaultdict(lambda: {"success": 0, "total": 0})

            for outcome in outcomes:
                action_stats[outcome.action]["total"] += 1
                if outcome.led_to_change:
                    # Reward transitions to "better" scenes
                    if self._is_progress(outcome.scene, outcome.next_scene):
                        action_stats[outcome.action]["success"] += 1

            # Compute adjustments
            scene_adj = {}
            for action, stats in action_stats.items():
                if stats["total"] >= 5:  # Need enough samples
                    success_rate = stats["success"] / stats["total"]
                    # Adjust relative to baseline (0.1 = neutral)
                    adjustment = (success_rate - 0.1) * self.learning_rate
                    scene_adj[action] = adjustment

            if scene_adj:
                adjustments[scene] = scene_adj

        return adjustments

    def _is_progress(self, from_scene: str, to_scene: str) -> bool:
        """Determine if a scene transition is progress."""
        # Progress hierarchy
        progress_pairs = {
            ("title", "overworld"),      # Started game
            ("dialogue", "overworld"),   # Finished dialogue
            ("battle", "overworld"),     # Won battle (returned to overworld)
            ("menu", "overworld"),       # Exited menu
            ("overworld", "battle"),     # Encountered Pokemon (can be good)
        }

        # Negative transitions
        stuck_pairs = {
            ("battle", "battle"),        # Still in battle
            ("dialogue", "dialogue"),    # Still in dialogue
            ("menu", "menu"),            # Still in menu
        }

        return (from_scene, to_scene) in progress_pairs

    def apply_to_weights(self, weights: Dict) -> Dict:
        """Apply learned adjustments to weight dict."""
        adjustments = self.compute_weight_adjustments()

        for scene, adj in adjustments.items():
            if scene in weights:
                w = weights[scene]
                for action, delta in adj.items():
                    current = getattr(w, action, 0.0)
                    new_val = max(0.01, min(0.95, current + delta))
                    setattr(w, action, new_val)

        return weights

    def get_summary(self) -> str:
        """Get a summary of learned patterns."""
        lines = ["Learning Summary:"]

        for scene, outcomes in self.outcomes.items():
            total = len(outcomes)
            changes = sum(1 for o in outcomes if o.led_to_change)
            if total > 0:
                lines.append(f"  {scene}: {changes}/{total} actions led to change ({100*changes/total:.0f}%)")

        adjustments = self.compute_weight_adjustments()
        if adjustments:
            lines.append("\nWeight Adjustments:")
            for scene, adj in adjustments.items():
                for action, delta in adj.items():
                    sign = "+" if delta > 0 else ""
                    lines.append(f"  {scene}.{action}: {sign}{delta:.3f}")

        return "\n".join(lines)
