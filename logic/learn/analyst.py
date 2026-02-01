"""
AI Analyst - Reviews completed runs and updates genome between runs.

This runs AFTER a fast bot run completes. It:
1. Reviews screenshots and logs from the run
2. Analyzes what worked and what didn't
3. Tests hypotheses using save states
4. Commits learnings to the genome for the next run

The bot itself stays fast and rule-based - no AI during gameplay.
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime


@dataclass
class AnalysisResult:
    """Result of analyzing a run."""
    run_id: str
    genome_id: str

    # Scores from analysis
    overall_score: float = 0.0  # -1 to 1
    strategy_score: float = 0.0
    efficiency_score: float = 0.0

    # Proposed changes
    weight_adjustments: Dict[str, Dict[str, float]] = None  # scene -> action -> delta
    new_patterns: List[Tuple[str, str, str, float]] = None  # (scene, condition, action, confidence)
    new_locations: Dict[str, str] = None  # (map,x,y) -> description

    # Analysis notes
    observations: List[str] = None
    recommendations: List[str] = None

    # Test results (from save state experiments)
    tested_changes: bool = False
    test_improvement: float = 0.0  # How much better the tested changes performed

    def __post_init__(self):
        self.weight_adjustments = self.weight_adjustments or {}
        self.new_patterns = self.new_patterns or []
        self.new_locations = self.new_locations or {}
        self.observations = self.observations or []
        self.recommendations = self.recommendations or []


class RunAnalyst:
    """Analyzes completed runs and proposes genome updates."""

    # Valid actions for weight adjustments
    VALID_ACTIONS = ['a', 'b', 'up', 'down', 'left', 'right', 'start', 'select', 'l', 'r']
    VALID_SCENES = ['battle', 'overworld', 'dialogue', 'menu', 'title']

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.screenshots_dir = self.data_dir / "screenshots"
        self.genomes_dir = self.data_dir / "genomes"
        self.analysis_dir = self.data_dir / "analysis"
        self.analysis_dir.mkdir(parents=True, exist_ok=True)

    def analyze_run(self, run_dir: Path) -> Optional[AnalysisResult]:
        """
        Analyze a completed run and propose genome updates.

        Args:
            run_dir: Path to the run's screenshot directory

        Returns:
            AnalysisResult with proposed changes
        """
        # Load run info
        info_path = run_dir / "run_info.json"
        if not info_path.exists():
            return None

        with open(info_path) as f:
            run_info = json.load(f)

        # Load index with all entries
        index_path = run_dir / "index.json"
        if not index_path.exists():
            return None

        with open(index_path) as f:
            index = json.load(f)

        run_id = run_info.get("run_id", "unknown")
        genome_id = run_info.get("genome_id", "unknown")

        result = AnalysisResult(run_id=run_id, genome_id=genome_id)

        # Analyze entries
        entries = index.get("entries", [])
        run_stats = index.get("run_stats", {})

        # Calculate base scores from run stats
        result.overall_score = self._score_from_stats(run_stats)

        # Analyze action patterns
        scene_actions = self._count_scene_actions(entries)
        result.weight_adjustments = self._propose_weight_changes(scene_actions, run_stats)

        # Identify patterns
        result.new_patterns = self._identify_patterns(entries)

        # Generate observations
        result.observations = self._generate_observations(entries, run_stats)
        result.recommendations = self._generate_recommendations(result)

        # Save analysis
        self._save_analysis(result, run_dir)

        return result

    def _score_from_stats(self, stats: dict) -> float:
        """Calculate overall score from run stats."""
        if not stats:
            return 0.0

        score = 0.0

        # Positive factors
        score += stats.get("battles_won", 0) * 0.1
        score += stats.get("pokemon_caught", 0) * 0.2
        score += stats.get("badges_earned", 0) * 0.5

        # Negative factors
        score -= stats.get("battles_lost", 0) * 0.05
        score -= stats.get("deaths", 0) * 0.3

        # Normalize to -1 to 1
        return max(-1, min(1, score / 5))

    def _count_scene_actions(self, entries: list) -> Dict[str, Dict[str, int]]:
        """Count actions taken in each scene."""
        counts = {}
        for entry in entries:
            scene = entry.get("scene", "unknown")
            action = entry.get("action", "unknown")

            if scene not in counts:
                counts[scene] = {}
            if action not in counts[scene]:
                counts[scene][action] = 0
            counts[scene][action] += 1

        return counts

    def _propose_weight_changes(self, scene_actions: dict, run_stats: dict) -> Dict[str, Dict[str, float]]:
        """Propose weight adjustments based on action patterns and outcomes."""
        adjustments = {}

        # If run was successful, reinforce common actions
        # If run failed, try different actions
        success = run_stats.get("battles_won", 0) > run_stats.get("battles_lost", 0)

        for scene, actions in scene_actions.items():
            if scene not in self.VALID_SCENES:
                continue

            adjustments[scene] = {}
            total = sum(actions.values())

            for action, count in actions.items():
                if action not in self.VALID_ACTIONS:
                    continue

                ratio = count / total if total > 0 else 0

                if success:
                    # Reinforce frequently used actions
                    if ratio > 0.3:
                        adjustments[scene][action] = 0.1
                    elif ratio < 0.1:
                        adjustments[scene][action] = -0.05
                else:
                    # Try different actions
                    if ratio > 0.3:
                        adjustments[scene][action] = -0.1
                    elif ratio < 0.1:
                        adjustments[scene][action] = 0.1

        return adjustments

    def _identify_patterns(self, entries: list) -> List[Tuple[str, str, str, float]]:
        """Identify repeating patterns that could become rules."""
        patterns = []

        # Look for sequences
        for i in range(len(entries) - 2):
            e1, e2, e3 = entries[i], entries[i+1], entries[i+2]

            # Same scene, same action sequence = potential pattern
            if e1["scene"] == e2["scene"] == e3["scene"]:
                if e1["action"] == e2["action"] == e3["action"]:
                    # Found a repeated action pattern
                    scene = e1["scene"]
                    action = e1["action"]
                    condition = f"repeated_{action}"
                    patterns.append((scene, condition, action, 0.7))

        # Deduplicate
        return list(set(patterns))

    def _generate_observations(self, entries: list, run_stats: dict) -> List[str]:
        """Generate human-readable observations."""
        obs = []

        total_entries = len(entries)
        if total_entries > 0:
            # Scene distribution
            scenes = {}
            for e in entries:
                s = e.get("scene", "unknown")
                scenes[s] = scenes.get(s, 0) + 1

            top_scene = max(scenes.items(), key=lambda x: x[1])
            obs.append(f"Spent {100*top_scene[1]//total_entries}% of time in {top_scene[0]}")

        # Battle performance
        won = run_stats.get("battles_won", 0)
        lost = run_stats.get("battles_lost", 0)
        if won + lost > 0:
            win_rate = 100 * won // (won + lost)
            obs.append(f"Battle win rate: {win_rate}%")

        # Movement
        distance = run_stats.get("distance_traveled", 0)
        steps = run_stats.get("total_steps", 1)
        if steps > 0:
            move_rate = 100 * distance // steps
            obs.append(f"Movement efficiency: {move_rate}%")

        return obs

    def _generate_recommendations(self, result: AnalysisResult) -> List[str]:
        """Generate recommendations for improvement."""
        recs = []

        if result.overall_score < 0:
            recs.append("Consider more diverse actions")
            recs.append("May need to adjust battle strategy")

        if result.overall_score > 0.5:
            recs.append("Strategy is working well - minor refinements only")

        # Based on weight adjustments
        for scene, actions in result.weight_adjustments.items():
            for action, delta in actions.items():
                if abs(delta) > 0.05:
                    direction = "increase" if delta > 0 else "decrease"
                    recs.append(f"{direction} {action} weight in {scene}")

        return recs[:5]  # Limit to top 5

    def _save_analysis(self, result: AnalysisResult, run_dir: Path):
        """Save analysis to file."""
        analysis_path = self.analysis_dir / f"{result.run_id}_analysis.json"

        with open(analysis_path, "w") as f:
            json.dump(asdict(result), f, indent=2)

        # Also save summary to run dir
        summary_path = run_dir / "analysis.json"
        with open(summary_path, "w") as f:
            json.dump(asdict(result), f, indent=2)

    def apply_to_genome(self, result: AnalysisResult, genome) -> bool:
        """
        Apply analysis results to a genome.

        Args:
            result: AnalysisResult from analyze_run
            genome: KnowledgeGenome to update

        Returns:
            True if changes were applied
        """
        if not result or not genome:
            return False

        changes_made = False

        # Apply weight adjustments
        for scene, adjustments in result.weight_adjustments.items():
            if scene not in genome.weights:
                genome.weights[scene] = {}

            for action, delta in adjustments.items():
                current = genome.weights[scene].get(action, 1.0)
                new_weight = max(0.01, current + delta)
                genome.weights[scene][action] = new_weight
                changes_made = True

        # Add new patterns
        for scene, condition, action, confidence in result.new_patterns:
            if scene not in genome.patterns:
                genome.patterns[scene] = []

            # Check if pattern already exists
            exists = any(p[0] == condition and p[1] == action
                        for p in genome.patterns[scene])
            if not exists:
                genome.patterns[scene].append((condition, action, confidence))
                changes_made = True

        # Add new locations
        for loc_key, description in result.new_locations.items():
            if loc_key not in genome.locations:
                genome.locations[loc_key] = description
                changes_made = True

        # Update AI feedback scores on genome stats
        genome.stats.set_ai_feedback(
            strategy=result.strategy_score,
            efficiency=result.efficiency_score,
            notes="; ".join(result.observations[:3])
        )

        return changes_made


class SaveStateExperimenter:
    """Tests proposed changes using save states before committing."""

    def __init__(self, sender):
        """
        Args:
            sender: InputSender with socket connection to mGBA
        """
        self.sender = sender
        self.test_slot = 8  # Reserve slot 8 for experiments
        self.last_results: Dict[str, float] = {}  # Track results for analysis

    def test_changes(self, genome, proposed_changes: AnalysisResult,
                     test_steps: int = 100) -> float:
        """
        Test proposed changes using save states.

        1. Load a save state
        2. Run with original genome
        3. Reload save state
        4. Run with modified genome
        5. Compare results

        Returns:
            Improvement score (-1 to 1)
        """
        if not self.sender or not self.sender.use_socket:
            return 0.0

        # Save current state for restoration
        self.sender.save_state(self.test_slot)

        # Get baseline with original genome
        baseline_score = self._run_test(genome, test_steps)

        # Reload state
        self.sender.load_state(self.test_slot)

        # Create modified genome
        import copy
        test_genome = copy.deepcopy(genome)

        # Apply proposed changes
        for scene, adjustments in proposed_changes.weight_adjustments.items():
            if scene not in test_genome.weights:
                test_genome.weights[scene] = {}
            for action, delta in adjustments.items():
                current = test_genome.weights[scene].get(action, 1.0)
                test_genome.weights[scene][action] = max(0.01, current + delta)

        # Get score with modified genome
        modified_score = self._run_test(test_genome, test_steps)

        # Reload original state
        self.sender.load_state(self.test_slot)

        # Calculate improvement
        if baseline_score == 0:
            return 0.0 if modified_score == 0 else 1.0

        improvement = (modified_score - baseline_score) / max(abs(baseline_score), 1)
        return max(-1, min(1, improvement))

    def test_multiple_approaches(self, genome, proposed_changes: AnalysisResult,
                                  test_steps: int = 100) -> Tuple[float, Dict[str, float], str]:
        """
        Test multiple approaches and return the best one.

        Tests:
        1. Baseline (current genome)
        2. Proposed changes (from analyst)
        3. Opposite of proposed changes (explore other direction)
        4. Random mutation (pure exploration)
        5. Amplified changes (2x the proposed adjustments)

        Returns:
            Tuple of (best_improvement, all_results, best_approach_name)
        """
        import copy
        import random

        if not self.sender or not self.sender.use_socket:
            return 0.0, {}, "none"

        results = {}

        # Save current state for restoration
        self.sender.save_state(self.test_slot)

        # 1. Baseline test
        baseline_score = self._run_test(genome, test_steps)
        results["baseline"] = baseline_score
        self.sender.load_state(self.test_slot)

        # 2. Proposed changes
        proposed_genome = copy.deepcopy(genome)
        self._apply_weight_changes(proposed_genome, proposed_changes.weight_adjustments, 1.0)
        results["proposed"] = self._run_test(proposed_genome, test_steps)
        self.sender.load_state(self.test_slot)

        # 3. Opposite changes (negate the deltas)
        opposite_genome = copy.deepcopy(genome)
        self._apply_weight_changes(opposite_genome, proposed_changes.weight_adjustments, -1.0)
        results["opposite"] = self._run_test(opposite_genome, test_steps)
        self.sender.load_state(self.test_slot)

        # 4. Random mutation
        random_genome = copy.deepcopy(genome)
        self._apply_random_mutation(random_genome)
        results["random"] = self._run_test(random_genome, test_steps)
        self.sender.load_state(self.test_slot)

        # 5. Amplified changes (2x the proposed)
        amplified_genome = copy.deepcopy(genome)
        self._apply_weight_changes(amplified_genome, proposed_changes.weight_adjustments, 2.0)
        results["amplified"] = self._run_test(amplified_genome, test_steps)
        self.sender.load_state(self.test_slot)

        # Store results for analysis
        self.last_results = results

        # Find best approach
        best_approach = max(results.keys(), key=lambda k: results[k])
        best_score = results[best_approach]

        # Calculate improvement over baseline
        improvement = 0.0
        if baseline_score != 0:
            improvement = (best_score - baseline_score) / max(abs(baseline_score), 1)
        elif best_score > 0:
            improvement = 1.0

        # Update the proposed_changes with the best approach info
        if best_approach == "opposite":
            # Negate all the adjustments
            for scene in proposed_changes.weight_adjustments:
                for action in proposed_changes.weight_adjustments[scene]:
                    proposed_changes.weight_adjustments[scene][action] *= -1
        elif best_approach == "amplified":
            # Double all the adjustments
            for scene in proposed_changes.weight_adjustments:
                for action in proposed_changes.weight_adjustments[scene]:
                    proposed_changes.weight_adjustments[scene][action] *= 2
        elif best_approach == "random":
            # Replace adjustments with random ones that worked
            proposed_changes.weight_adjustments = self._get_random_adjustments()
        # If "proposed" or "baseline" won, keep adjustments as-is (or clear them for baseline)

        return max(-1, min(1, improvement)), results, best_approach

    def _apply_weight_changes(self, genome, adjustments: Dict[str, Dict[str, float]], scale: float):
        """Apply weight adjustments with a scaling factor."""
        for scene, scene_adjustments in adjustments.items():
            if scene not in genome.weights:
                genome.weights[scene] = {}
            for action, delta in scene_adjustments.items():
                current = genome.weights[scene].get(action, 1.0)
                genome.weights[scene][action] = max(0.01, current + (delta * scale))

    def _apply_random_mutation(self, genome):
        """Apply random weight mutations to a genome."""
        import random

        scenes = ['battle', 'overworld', 'dialogue', 'menu', 'title']
        actions = ['a', 'b', 'up', 'down', 'left', 'right', 'start']

        # Mutate 3-5 random weights
        for _ in range(random.randint(3, 5)):
            scene = random.choice(scenes)
            action = random.choice(actions)

            if scene not in genome.weights:
                genome.weights[scene] = {}

            current = genome.weights[scene].get(action, 1.0)
            delta = random.uniform(-0.3, 0.3)
            genome.weights[scene][action] = max(0.01, current + delta)

    def _get_random_adjustments(self) -> Dict[str, Dict[str, float]]:
        """Generate random adjustments that can be applied."""
        import random

        adjustments = {}
        scenes = ['battle', 'overworld', 'dialogue', 'menu']
        actions = ['a', 'b', 'up', 'down', 'left', 'right']

        for _ in range(random.randint(2, 4)):
            scene = random.choice(scenes)
            action = random.choice(actions)

            if scene not in adjustments:
                adjustments[scene] = {}

            adjustments[scene][action] = random.uniform(-0.2, 0.2)

        return adjustments

    def _run_test(self, genome, steps: int) -> float:
        """Run a quick test with the given genome and return a score."""
        score = 0.0
        last_hp = 0

        for _ in range(steps):
            # Get state
            state = self.sender.get_state()
            if not state:
                continue

            # Make decision
            scene = state.scene
            action = genome.decide(scene)

            # Execute
            self.sender.send(action, hold_frames=2)

            # Simple scoring: HP changes, position changes
            if state.player_hp > last_hp:
                score += 0.1  # Healed
            elif state.player_hp < last_hp:
                score -= 0.1  # Took damage
            last_hp = state.player_hp

            # Reward for not being stuck
            if state.battle:
                score += 0.05  # In battle = doing something

        return score


def analyze_latest_run(data_dir: str = "data") -> Optional[AnalysisResult]:
    """Convenience function to analyze the most recent run."""
    screenshots_dir = Path(data_dir) / "screenshots"

    if not screenshots_dir.exists():
        return None

    # Find most recent run
    runs = sorted(screenshots_dir.iterdir(), key=lambda p: p.name, reverse=True)
    if not runs:
        return None

    analyst = RunAnalyst(data_dir)
    return analyst.analyze_run(runs[0])


# =============================================================================
# Action Block Learning
# =============================================================================

@dataclass
class SequenceCandidate:
    """A candidate action sequence that might become an action block."""
    actions: List[str]
    trigger_state: Dict[str, Any]  # Memory/scene state when sequence started
    occurrences: int = 1
    success_rate: float = 0.0
    avg_duration: float = 0.0


class ActionBlockLearner:
    """
    Learns action blocks from run patterns.

    Identifies:
    1. Repeated action sequences at specific game states
    2. Sequences that always lead to successful outcomes
    3. Menu navigation patterns
    4. Dialogue skipping patterns
    """

    MIN_SEQUENCE_LENGTH = 3
    MIN_OCCURRENCES = 3  # Need to see pattern at least 3 times
    MIN_SUCCESS_RATE = 0.7

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.candidates: Dict[str, SequenceCandidate] = {}
        self.learned_blocks_dir = self.data_dir / "action_blocks"
        self.learned_blocks_dir.mkdir(parents=True, exist_ok=True)

    def analyze_runs_for_patterns(self, num_runs: int = 10) -> List[SequenceCandidate]:
        """
        Analyze recent runs to find repeating patterns.

        Returns list of sequence candidates worthy of becoming blocks.
        """
        screenshots_dir = self.data_dir / "screenshots"
        if not screenshots_dir.exists():
            return []

        # Get recent runs
        runs = sorted(screenshots_dir.iterdir(), key=lambda p: p.name, reverse=True)[:num_runs]

        all_sequences = []
        for run_dir in runs:
            sequences = self._extract_sequences(run_dir)
            all_sequences.extend(sequences)

        # Find repeated sequences
        self._find_patterns(all_sequences)

        # Filter to worthy candidates
        worthy = [
            c for c in self.candidates.values()
            if c.occurrences >= self.MIN_OCCURRENCES
            and c.success_rate >= self.MIN_SUCCESS_RATE
            and len(c.actions) >= self.MIN_SEQUENCE_LENGTH
        ]

        return sorted(worthy, key=lambda c: c.occurrences * c.success_rate, reverse=True)

    def _extract_sequences(self, run_dir: Path) -> List[Dict]:
        """Extract action sequences from a run."""
        index_path = run_dir / "index.json"
        if not index_path.exists():
            return []

        with open(index_path) as f:
            index = json.load(f)

        entries = index.get("entries", [])
        sequences = []
        current_seq = []
        current_state = None

        for entry in entries:
            scene = entry.get("scene", "unknown")
            action = entry.get("action", "")
            state = entry.get("state", {})

            # Start new sequence on scene change
            if current_state and scene != current_state.get("scene"):
                if len(current_seq) >= self.MIN_SEQUENCE_LENGTH:
                    sequences.append({
                        "actions": list(current_seq),
                        "trigger_state": dict(current_state),
                        "end_state": state,
                    })
                current_seq = []

            current_seq.append(action)
            if not current_state:
                current_state = {"scene": scene, **state}

            # Cap sequence length
            if len(current_seq) > 50:
                sequences.append({
                    "actions": list(current_seq),
                    "trigger_state": dict(current_state),
                    "end_state": state,
                })
                current_seq = []
                current_state = None

        return sequences

    def _find_patterns(self, sequences: List[Dict]):
        """Find repeating patterns across sequences."""
        from collections import defaultdict

        # Group by trigger state
        by_trigger = defaultdict(list)
        for seq in sequences:
            trigger = seq["trigger_state"]
            key = f"{trigger.get('scene', '')}_{trigger.get('map', 0)}"
            by_trigger[key].append(seq)

        # Find common subsequences within each group
        for trigger_key, seqs in by_trigger.items():
            if len(seqs) < 2:
                continue

            # Look for common prefixes
            for length in range(self.MIN_SEQUENCE_LENGTH, 20):
                prefix_counts = defaultdict(list)

                for seq in seqs:
                    if len(seq["actions"]) >= length:
                        prefix = tuple(seq["actions"][:length])
                        prefix_counts[prefix].append(seq)

                # Check for patterns with enough occurrences
                for prefix, matching_seqs in prefix_counts.items():
                    if len(matching_seqs) >= 2:
                        key = f"{trigger_key}_{hash(prefix)}"

                        if key not in self.candidates:
                            self.candidates[key] = SequenceCandidate(
                                actions=list(prefix),
                                trigger_state=matching_seqs[0]["trigger_state"],
                            )

                        self.candidates[key].occurrences = len(matching_seqs)

    def create_action_block(self, candidate: SequenceCandidate, name: str, description: str):
        """
        Create an ActionBlock from a sequence candidate.

        Returns the created block or None if creation failed.
        """
        from logic.act.action_blocks import (
            ActionBlock, ActionStep, Trigger, TriggerType
        )

        # Determine trigger type from state
        trigger_state = candidate.trigger_state
        scene = trigger_state.get("scene", "unknown")

        trigger = Trigger(
            type=TriggerType.SCENE,
            scene=scene
        )

        # Convert action strings to ActionSteps
        steps = []
        for action in candidate.actions:
            steps.append(ActionStep(
                action=action,
                hold_frames=3,
                wait_frames=6,
            ))

        # Generate unique ID
        block_id = f"learned_{name.lower().replace(' ', '_')}_{int(time.time())}"

        block = ActionBlock(
            id=block_id,
            name=name,
            description=description,
            trigger=trigger,
            actions=steps,
            priority=20,  # Lower than built-in blocks
        )

        # Save to disk
        block_path = self.learned_blocks_dir / f"{block_id}.json"
        with open(block_path, 'w') as f:
            json.dump(block.to_dict(), f, indent=2)

        return block

    def suggest_blocks(self) -> List[Dict]:
        """
        Analyze patterns and suggest new action blocks.

        Returns list of suggestions with metadata.
        """
        candidates = self.analyze_runs_for_patterns()

        suggestions = []
        for candidate in candidates[:5]:  # Top 5 suggestions
            suggestions.append({
                "actions": candidate.actions,
                "trigger": candidate.trigger_state,
                "occurrences": candidate.occurrences,
                "success_rate": candidate.success_rate,
                "suggested_name": self._suggest_name(candidate),
                "description": f"Auto-detected sequence in {candidate.trigger_state.get('scene', 'unknown')}"
            })

        return suggestions

    def _suggest_name(self, candidate: SequenceCandidate) -> str:
        """Generate a suggested name for a block."""
        scene = candidate.trigger_state.get("scene", "unknown")
        length = len(candidate.actions)

        # Detect common patterns
        actions = candidate.actions
        if all(a == "a" for a in actions[:3]):
            return f"{scene.title()} Dialogue Skip"
        elif "start" in actions and scene == "title":
            return "Game Start"
        elif actions.count("up") + actions.count("down") > len(actions) // 2:
            return f"{scene.title()} Menu Navigation"

        return f"{scene.title()} Sequence {length}"
