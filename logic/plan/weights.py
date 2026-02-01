"""
Weighted Decider - Fast decisions using probability weights.
"""

import random
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ActionWeights:
    """Weights for each action in a scene type."""
    up: float = 0.25
    down: float = 0.25
    left: float = 0.25
    right: float = 0.25
    a: float = 0.0
    b: float = 0.0
    start: float = 0.0
    select: float = 0.0
    l: float = 0.0
    r: float = 0.0

    def as_dict(self) -> Dict[str, float]:
        return {
            "up": self.up, "down": self.down, "left": self.left, "right": self.right,
            "a": self.a, "b": self.b, "start": self.start, "select": self.select,
            "l": self.l, "r": self.r
        }


# Default weights per scene type
DEFAULT_WEIGHTS = {
    "overworld": ActionWeights(up=0.35, down=0.15, left=0.25, right=0.25),
    "battle": ActionWeights(up=0.1, down=0.1, a=0.7, b=0.1),
    "dialogue": ActionWeights(a=0.8, b=0.2),
    "menu": ActionWeights(up=0.1, down=0.1, b=0.7, a=0.1),
    "title": ActionWeights(a=0.3, start=0.7),
    "unknown": ActionWeights(a=0.5, b=0.5),
}


class WeightedDecider:
    """Makes decisions based on probability weights."""

    def __init__(self, weights: Dict[str, ActionWeights] = None):
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        self.history: list = []

    def decide(self, scene: str) -> str:
        """Pick an action based on scene weights."""
        scene = scene.lower()
        w = self.weights.get(scene, DEFAULT_WEIGHTS["unknown"])
        actions = list(w.as_dict().keys())
        probs = list(w.as_dict().values())

        total = sum(probs)
        if total == 0:
            action = "a"
        else:
            probs = [p / total for p in probs]
            action = random.choices(actions, weights=probs)[0]

        self.history.append(action)
        return action

    def get_reason(self, scene: str, action: str) -> str:
        """Get a human-readable reason for the decision."""
        reasons = {
            "overworld": "exploring",
            "battle": "fighting",
            "dialogue": "advancing text",
            "menu": "navigating menu",
            "title": "starting game",
        }
        return reasons.get(scene.lower(), "unknown scene")
