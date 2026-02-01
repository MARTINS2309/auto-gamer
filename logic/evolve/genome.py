"""
KnowledgeGenome - Heritable knowledge structure for evolutionary learning.

Each genome contains:
- Decision weights (action probabilities per scene)
- Learned patterns (what worked/didn't work)
- Fitness score (how well this genome performed)
- Lineage info (parent genomes)

Reference: docs/plan.md - RL training support
"""

import json
import random
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import copy


@dataclass
class GenomeStats:
    """Performance statistics for a genome."""
    # Run metrics
    total_steps: int = 0
    battles_won: int = 0
    battles_lost: int = 0
    pokemon_caught: int = 0
    badges_earned: int = 0
    deaths: int = 0
    distance_traveled: int = 0
    unique_maps_visited: int = 0
    max_money: int = 0
    playtime_seconds: float = 0.0

    # AI/Learner feedback scores (-1.0 to 1.0, 0 = neutral)
    ai_strategy_score: float = 0.0  # How good was the overall strategy
    ai_efficiency_score: float = 0.0  # How efficient were the actions
    ai_exploration_score: float = 0.0  # How well did it explore
    ai_battle_score: float = 0.0  # How well did it handle battles
    ai_notes: str = ""  # AI observations

    def fitness(self) -> float:
        """Calculate fitness score (higher = better). Combines run metrics + AI feedback."""
        score = 0.0

        # === Run Performance (objective metrics) ===
        score += self.battles_won * 10
        score += self.pokemon_caught * 20
        score += self.badges_earned * 100
        score += self.unique_maps_visited * 5
        score += self.distance_traveled * 0.1
        score += min(self.total_steps, 10000) * 0.01

        # Negative factors
        score -= self.battles_lost * 5
        score -= self.deaths * 50

        # Efficiency bonus
        if self.total_steps > 0:
            efficiency = (self.badges_earned * 100 + self.battles_won * 5) / self.total_steps
            score += efficiency * 1000

        # === AI/Learner Feedback (subjective assessment) ===
        ai_weight = 50  # How much AI feedback affects fitness
        score += self.ai_strategy_score * ai_weight
        score += self.ai_efficiency_score * ai_weight
        score += self.ai_exploration_score * ai_weight * 0.5
        score += self.ai_battle_score * ai_weight

        return max(0, score)

    def set_ai_feedback(self, strategy: float = None, efficiency: float = None,
                       exploration: float = None, battle: float = None, notes: str = None):
        """Set AI feedback scores. Values should be -1.0 to 1.0."""
        if strategy is not None:
            self.ai_strategy_score = max(-1, min(1, strategy))
        if efficiency is not None:
            self.ai_efficiency_score = max(-1, min(1, efficiency))
        if exploration is not None:
            self.ai_exploration_score = max(-1, min(1, exploration))
        if battle is not None:
            self.ai_battle_score = max(-1, min(1, battle))
        if notes is not None:
            self.ai_notes = notes


@dataclass
class KnowledgeGenome:
    """
    A genome of learned knowledge that can be inherited and evolved.
    """
    # Identity
    id: str = ""
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    created_at: str = ""

    # Decision weights per scene (action -> probability modifier)
    weights: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Learned patterns: scene -> [(condition, best_action, confidence)]
    patterns: Dict[str, List[Tuple[str, str, float]]] = field(default_factory=list)

    # Memory of key locations: (map, x, y) -> description
    locations: Dict[str, str] = field(default_factory=dict)

    # Statistics from runs using this genome
    stats: GenomeStats = field(default_factory=GenomeStats)

    # Mutation rate for this lineage
    mutation_rate: float = 0.1

    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.weights:
            self._init_default_weights()

    def _generate_id(self) -> str:
        """Generate unique genome ID."""
        data = f"{datetime.now().isoformat()}{random.random()}"
        return hashlib.md5(data.encode()).hexdigest()[:8]

    def _init_default_weights(self):
        """Initialize with default decision weights."""
        self.weights = {
            "overworld": {
                "up": 1.0, "down": 1.0, "left": 1.0, "right": 1.0,
                "a": 0.3, "b": 0.1, "start": 0.05, "select": 0.01
            },
            "battle": {
                "a": 2.0, "b": 0.5, "up": 0.3, "down": 0.3,
                "left": 0.2, "right": 0.2, "start": 0.1
            },
            "dialogue": {
                "a": 3.0, "b": 1.0, "up": 0.1, "down": 0.1
            },
            "menu": {
                "a": 1.5, "b": 1.0, "up": 1.0, "down": 1.0,
                "left": 0.5, "right": 0.5, "start": 0.3
            },
            "title": {
                "a": 2.0, "start": 2.0, "up": 0.5, "down": 0.5
            }
        }

    def fitness(self) -> float:
        """Get fitness score."""
        return self.stats.fitness()

    def mutate(self) -> "KnowledgeGenome":
        """Create a mutated copy of this genome."""
        child = copy.deepcopy(self)
        child.id = child._generate_id()
        child.generation = self.generation + 1
        child.parent_ids = [self.id]
        child.created_at = datetime.now().isoformat()
        child.stats = GenomeStats()  # Fresh stats

        # Mutate weights
        for scene, actions in child.weights.items():
            for action in actions:
                if random.random() < child.mutation_rate:
                    # Random mutation: multiply by 0.5 to 2.0
                    factor = random.uniform(0.5, 2.0)
                    actions[action] = max(0.01, actions[action] * factor)

        # Possibly adjust mutation rate itself
        if random.random() < 0.1:
            child.mutation_rate = max(0.01, min(0.5, child.mutation_rate * random.uniform(0.8, 1.2)))

        return child

    @staticmethod
    def crossover(parent1: "KnowledgeGenome", parent2: "KnowledgeGenome") -> "KnowledgeGenome":
        """Create child genome by combining two parents."""
        child = KnowledgeGenome()
        child.generation = max(parent1.generation, parent2.generation) + 1
        child.parent_ids = [parent1.id, parent2.id]

        # Crossover weights (randomly pick from each parent per scene)
        for scene in set(parent1.weights.keys()) | set(parent2.weights.keys()):
            if random.random() < 0.5 and scene in parent1.weights:
                child.weights[scene] = copy.deepcopy(parent1.weights[scene])
            elif scene in parent2.weights:
                child.weights[scene] = copy.deepcopy(parent2.weights[scene])

        # Merge patterns (take high-confidence ones from both)
        all_patterns = {}
        for scene, patterns in parent1.patterns.items():
            for cond, action, conf in patterns:
                key = (scene, cond)
                if key not in all_patterns or conf > all_patterns[key][1]:
                    all_patterns[key] = (action, conf)

        for scene, patterns in parent2.patterns.items():
            for cond, action, conf in patterns:
                key = (scene, cond)
                if key not in all_patterns or conf > all_patterns[key][1]:
                    all_patterns[key] = (action, conf)

        # Rebuild patterns dict
        child.patterns = {}
        for (scene, cond), (action, conf) in all_patterns.items():
            if scene not in child.patterns:
                child.patterns[scene] = []
            child.patterns[scene].append((cond, action, conf))

        # Merge locations
        child.locations = {**parent1.locations, **parent2.locations}

        # Average mutation rate
        child.mutation_rate = (parent1.mutation_rate + parent2.mutation_rate) / 2

        return child

    def decide(self, scene: str, context: dict = None) -> str:
        """
        Choose an action based on learned weights and patterns.
        Returns action name.
        """
        scene = scene.lower()
        weights = self.weights.get(scene, self.weights.get("overworld", {}))

        # Check patterns first
        if scene in self.patterns and context:
            for cond, action, conf in self.patterns[scene]:
                if conf > 0.7 and self._matches_condition(cond, context):
                    if random.random() < conf:
                        return action

        # Weighted random selection
        actions = list(weights.keys())
        probs = [weights[a] for a in actions]
        total = sum(probs)
        if total == 0:
            return random.choice(["a", "b", "up", "down", "left", "right"])

        probs = [p / total for p in probs]
        return random.choices(actions, weights=probs, k=1)[0]

    def _matches_condition(self, condition: str, context: dict) -> bool:
        """Check if a pattern condition matches current context."""
        # Simple string matching for now
        return condition in str(context)

    def learn(self, scene: str, action: str, outcome: str, reward: float):
        """
        Update weights based on outcome.
        positive reward = good outcome, negative = bad
        """
        scene = scene.lower()
        if scene not in self.weights:
            self.weights[scene] = {}
        if action not in self.weights[scene]:
            self.weights[scene][action] = 1.0

        # Adjust weight based on reward
        learning_rate = 0.1
        current = self.weights[scene][action]
        self.weights[scene][action] = max(0.01, current + learning_rate * reward)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "generation": self.generation,
            "parent_ids": self.parent_ids,
            "created_at": self.created_at,
            "weights": self.weights,
            "patterns": self.patterns,
            "locations": self.locations,
            "stats": asdict(self.stats),
            "mutation_rate": self.mutation_rate,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeGenome":
        """Create from dictionary."""
        genome = cls(
            id=data.get("id", ""),
            generation=data.get("generation", 0),
            parent_ids=data.get("parent_ids", []),
            created_at=data.get("created_at", ""),
            weights=data.get("weights", {}),
            patterns=data.get("patterns", {}),
            locations=data.get("locations", {}),
            mutation_rate=data.get("mutation_rate", 0.1),
        )
        if "stats" in data:
            genome.stats = GenomeStats(**data["stats"])
        return genome

    def save(self, path: Path):
        """Save genome to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "KnowledgeGenome":
        """Load genome from file."""
        with open(path) as f:
            return cls.from_dict(json.load(f))

    def __repr__(self):
        return f"Genome({self.id}, gen={self.generation}, fitness={self.fitness():.1f})"
