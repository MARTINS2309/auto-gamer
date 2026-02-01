"""
LLM-Based Decision Agent

An alternative/complementary approach to PPO that uses a language model
for decision-making based on the extracted game state.

This can be used:
1. As a standalone agent (pure LLM decision-making)
2. As a teacher for the RL agent (behavioral cloning)
3. As a fallback when RL is uncertain
"""

import json
import time
from dataclasses import dataclass
from typing import Optional

import requests

from pokemon_agent import PokemonState, EmulatorKeys


@dataclass
class Decision:
    """A decision made by the LLM agent."""
    action: str
    reasoning: str
    confidence: float
    inference_time: float


DECISION_PROMPT_TEMPLATE = """You are playing Pokemon. Based on the current game state, choose the best action.

Current State:
- Scene: {scene_type}
- In Battle: {in_battle}
- Player HP: {player_hp}%
- Enemy HP: {enemy_hp}%
- Wild Pokemon: {wild_pokemon}
- Dialogue Box: {has_dialogue}
- Menu Open: {menu_open}

Available Actions: {actions}

Rules:
1. In battle: Attack (A) to damage enemy, use items if HP low
2. In dialogue: Press A to advance text
3. In overworld: Move around to find Pokemon
4. In menu: Navigate with arrows, select with A, cancel with B

Respond with JSON only:
{{"action": "chosen_action", "reasoning": "brief explanation", "confidence": 0.0-1.0}}"""


class LLMDecisionAgent:
    """
    Uses a local LLM to make game decisions based on extracted state.

    This provides an interpretable, reasoning-based approach compared to
    the black-box nature of RL policies.
    """

    ACTIONS = ["up", "down", "left", "right", "a", "b", "start", "wait"]

    def __init__(
        self,
        model: str = "phi4",
        ollama_url: str = "http://localhost:11434",
        emulator: str = "mgba",
    ):
        self.model = model
        self.ollama_url = ollama_url.rstrip("/")
        self.key_map = getattr(EmulatorKeys, emulator.upper(), EmulatorKeys.MGBA)

        # Track decision history for analysis
        self.decision_history: list[Decision] = []

    def decide(self, state: PokemonState) -> Decision:
        """
        Make a decision based on the current game state.

        Args:
            state: Current Pokemon game state from vision classifier

        Returns:
            Decision with action, reasoning, and confidence
        """
        prompt = DECISION_PROMPT_TEMPLATE.format(
            scene_type=state.scene_type,
            in_battle=state.in_battle,
            player_hp=state.player_hp,
            enemy_hp=state.enemy_hp,
            wild_pokemon=state.wild_pokemon,
            has_dialogue=state.has_dialogue,
            menu_open=state.menu_open,
            actions=", ".join(self.ACTIONS),
        )

        start_time = time.perf_counter()

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=30,
            )
            response.raise_for_status()
            elapsed = time.perf_counter() - start_time

            response_text = response.json().get("response", "")
            decision = self._parse_decision(response_text, elapsed)

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            decision = Decision(
                action="wait",
                reasoning=f"Error: {str(e)}",
                confidence=0.0,
                inference_time=elapsed,
            )

        self.decision_history.append(decision)
        return decision

    def _parse_decision(self, response: str, inference_time: float) -> Decision:
        """Parse LLM response into a Decision."""
        # Try to extract JSON
        try:
            # Find JSON in response
            import re
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                action = data.get("action", "wait").lower()
                if action not in self.ACTIONS:
                    action = "wait"

                return Decision(
                    action=action,
                    reasoning=data.get("reasoning", ""),
                    confidence=float(data.get("confidence", 0.5)),
                    inference_time=inference_time,
                )
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: try to find action keyword in response
        response_lower = response.lower()
        for action in self.ACTIONS:
            if action in response_lower:
                return Decision(
                    action=action,
                    reasoning=response[:100],
                    confidence=0.3,
                    inference_time=inference_time,
                )

        return Decision(
            action="wait",
            reasoning="Could not parse response",
            confidence=0.0,
            inference_time=inference_time,
        )

    def decide_with_rules(self, state: PokemonState) -> Decision:
        """
        Hybrid approach: Use rules for obvious situations, LLM for complex ones.

        This is faster and more reliable for common game states.
        """
        start_time = time.perf_counter()

        # Rule-based decisions for common situations
        if state.has_dialogue:
            return Decision(
                action="a",
                reasoning="Advancing dialogue",
                confidence=0.95,
                inference_time=time.perf_counter() - start_time,
            )

        if state.in_battle:
            # Low HP - might want to run or heal
            if state.player_hp < 20:
                return Decision(
                    action="b",  # Try to run
                    reasoning="HP critical, attempting escape",
                    confidence=0.7,
                    inference_time=time.perf_counter() - start_time,
                )

            # Enemy low HP - attack to finish
            if state.enemy_hp < 30:
                return Decision(
                    action="a",
                    reasoning="Enemy HP low, attacking to finish",
                    confidence=0.9,
                    inference_time=time.perf_counter() - start_time,
                )

            # Normal battle - attack
            return Decision(
                action="a",
                reasoning="In battle, selecting attack",
                confidence=0.8,
                inference_time=time.perf_counter() - start_time,
            )

        if state.menu_open:
            # Close menu to continue exploring
            return Decision(
                action="b",
                reasoning="Closing menu to explore",
                confidence=0.85,
                inference_time=time.perf_counter() - start_time,
            )

        # Overworld - explore randomly or use LLM for complex navigation
        # For simplicity, use random direction
        import random
        directions = ["up", "down", "left", "right"]
        direction = random.choice(directions)

        return Decision(
            action=direction,
            reasoning="Exploring overworld",
            confidence=0.6,
            inference_time=time.perf_counter() - start_time,
        )

    def get_stats(self) -> dict:
        """Get decision statistics."""
        if not self.decision_history:
            return {"total_decisions": 0}

        times = [d.inference_time for d in self.decision_history]
        confidences = [d.confidence for d in self.decision_history]
        action_counts = {}
        for d in self.decision_history:
            action_counts[d.action] = action_counts.get(d.action, 0) + 1

        return {
            "total_decisions": len(self.decision_history),
            "avg_inference_time": sum(times) / len(times),
            "avg_confidence": sum(confidences) / len(confidences),
            "action_distribution": action_counts,
        }

    def check_model_available(self) -> bool:
        """Check if the configured model is available."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            response.raise_for_status()
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            return any(self.model in name for name in model_names)
        except:
            return False


class HybridAgent:
    """
    Combines LLM reasoning with RL policy.

    Uses LLM for:
    - Initial exploration and data collection
    - Complex strategic decisions
    - When RL policy is uncertain

    Uses RL for:
    - Fast reaction-time decisions
    - Optimized tactical execution
    - Well-trained scenarios
    """

    def __init__(
        self,
        llm_model: str = "phi4",
        rl_model_path: str = "models/pokemon_agent.zip",
        use_llm_threshold: float = 0.7,
    ):
        self.llm_agent = LLMDecisionAgent(model=llm_model)
        self.use_llm_threshold = use_llm_threshold

        # Try to load RL model
        self.rl_model = None
        try:
            from stable_baselines3 import PPO
            from pathlib import Path
            if Path(rl_model_path).exists():
                self.rl_model = PPO.load(rl_model_path)
                print(f"Loaded RL model from {rl_model_path}")
        except Exception as e:
            print(f"Could not load RL model: {e}")

    def decide(self, state: PokemonState, prefer_llm: bool = False) -> tuple[str, str]:
        """
        Make a decision using either LLM or RL.

        Args:
            state: Current game state
            prefer_llm: Force LLM decision regardless of RL availability

        Returns:
            Tuple of (action, source) where source is "llm" or "rl"
        """
        # Use rules-based LLM for speed
        if prefer_llm or self.rl_model is None:
            decision = self.llm_agent.decide_with_rules(state)
            return decision.action, "llm"

        # Use RL model
        state_vector = state.to_vector()
        action_idx, _ = self.rl_model.predict(state_vector, deterministic=True)

        actions = ["up", "down", "left", "right", "a", "b", "start", "wait"]
        return actions[int(action_idx)], "rl"


def demo():
    """Demo the LLM decision agent."""
    from pokemon_agent import PokemonClassifier

    print("=" * 60)
    print("LLM Decision Agent Demo")
    print("=" * 60)

    # Check models
    llm_agent = LLMDecisionAgent(model="phi4")
    if not llm_agent.check_model_available():
        print("Warning: phi4 not available, trying qwen2.5:7b")
        llm_agent = LLMDecisionAgent(model="qwen2.5:7b")
        if not llm_agent.check_model_available():
            print("Error: No decision model available")
            print("Install with: ollama pull phi4")
            return

    classifier = PokemonClassifier()

    print("\nCapturing screen in 3 seconds...")
    for i in range(3, 0, -1):
        print(f"  {i}...")
        time.sleep(1)

    # Get game state
    state = classifier.classify_pokemon_state()
    print(f"\nDetected State:")
    print(f"  Scene: {state.scene_type}")
    print(f"  In Battle: {state.in_battle}")
    print(f"  Player HP: {state.player_hp}%")
    print(f"  Enemy HP: {state.enemy_hp}%")

    # Get LLM decision
    print("\nAsking LLM for decision...")
    decision = llm_agent.decide(state)

    print(f"\nDecision:")
    print(f"  Action: {decision.action}")
    print(f"  Reasoning: {decision.reasoning}")
    print(f"  Confidence: {decision.confidence:.2f}")
    print(f"  Time: {decision.inference_time:.2f}s")

    # Compare with rules-based
    print("\nRules-based decision (faster):")
    rule_decision = llm_agent.decide_with_rules(state)
    print(f"  Action: {rule_decision.action}")
    print(f"  Reasoning: {rule_decision.reasoning}")
    print(f"  Time: {rule_decision.inference_time:.4f}s")


if __name__ == "__main__":
    demo()
