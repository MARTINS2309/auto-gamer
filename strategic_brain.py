"""
Strategic Brain Module

A long-context LLM that maintains game history and provides strategic guidance.
This augments the vision classifier data and helps the RL agent make better decisions.

Architecture:
┌─────────────────────────────────────────────────────────────────────┐
│                     STRATEGIC BRAIN SYSTEM                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │   VISION     │    │  STRATEGIC       │    │   RL AGENT       │  │
│  │  CLASSIFIER  │───▶│  BRAIN           │───▶│   (PPO)          │  │
│  │  (VLM)       │    │  (Long-Context)  │    │                  │  │
│  └──────────────┘    └──────────────────┘    └──────────────────┘  │
│         │                    │                        │             │
│    Raw State           Strategic Context         Action            │
│    - scene             - game progress           Selection         │
│    - HP values         - battle history                            │
│    - current scene     - strategic advice                          │
│                        - next objectives                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

The Strategic Brain:
1. Maintains a rolling history of game states and events
2. Tracks progress (badges, pokemon caught, story progression)
3. Provides strategic recommendations based on context
4. Augments the state vector with strategic embeddings
"""

import json
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

import numpy as np
import requests

from pokemon_agent import PokemonState


@dataclass
class GameEvent:
    """A significant game event to remember."""
    timestamp: float
    event_type: str  # battle_start, battle_won, battle_lost, caught_pokemon, dialogue, etc.
    details: dict
    state_snapshot: Optional[dict] = None


@dataclass
class StrategicContext:
    """Strategic context from the brain."""
    recommended_action: str
    reasoning: str
    current_objective: str
    progress_summary: str
    confidence: float
    inference_time: float


@dataclass
class GameMemory:
    """Long-term game memory."""
    # Rolling history of recent states
    recent_states: deque = field(default_factory=lambda: deque(maxlen=100))

    # Significant events
    events: list = field(default_factory=list)

    # Game progress tracking
    battles_won: int = 0
    battles_lost: int = 0
    pokemon_caught: int = 0
    current_location: str = "unknown"
    last_heal_location: str = "unknown"

    # Strategic state
    current_objective: str = "Explore and find wild Pokemon"
    known_pokemon: list = field(default_factory=list)

    def add_state(self, state: PokemonState):
        """Add a state to recent history."""
        self.recent_states.append({
            "timestamp": time.time(),
            "scene_type": state.scene_type,
            "in_battle": state.in_battle,
            "player_hp": state.player_hp,
            "enemy_hp": state.enemy_hp,
            "player_pokemon": state.player_pokemon_name,
            "enemy_pokemon": state.enemy_pokemon_name,
        })

    def add_event(self, event_type: str, details: dict):
        """Record a significant event."""
        self.events.append(GameEvent(
            timestamp=time.time(),
            event_type=event_type,
            details=details,
        ))

        # Update progress based on event
        if event_type == "battle_won":
            self.battles_won += 1
        elif event_type == "battle_lost":
            self.battles_lost += 1
        elif event_type == "caught_pokemon":
            self.pokemon_caught += 1
            if "pokemon" in details:
                self.known_pokemon.append(details["pokemon"])

    def get_history_summary(self, max_states: int = 20) -> str:
        """Get a text summary of recent history for the LLM."""
        lines = []

        # Recent states
        states = list(self.recent_states)[-max_states:]
        for s in states:
            lines.append(f"- {s['scene_type']}: HP={s['player_hp']}%, Enemy HP={s.get('enemy_hp', 'N/A')}%")

        # Recent events
        recent_events = self.events[-10:]
        if recent_events:
            lines.append("\nRecent Events:")
            for e in recent_events:
                lines.append(f"- {e.event_type}: {e.details}")

        # Progress
        lines.append(f"\nProgress: {self.battles_won} wins, {self.battles_lost} losses, {self.pokemon_caught} caught")

        return "\n".join(lines)


STRATEGIC_PROMPT = """You are a Pokemon game strategist AI. Based on the current game state and history, provide strategic guidance.

CURRENT STATE:
{current_state}

RECENT HISTORY:
{history}

CURRENT OBJECTIVE: {objective}

Analyze the situation and respond with JSON only:
{{
    "recommended_action": "up/down/left/right/a/b/start/wait",
    "reasoning": "brief explanation of why this action",
    "current_objective": "what the player should focus on now",
    "progress_summary": "brief assessment of overall progress",
    "confidence": 0.0-1.0
}}

Strategic considerations:
- If HP < 30%, consider healing or escaping
- In battle, attack to build XP unless HP is critical
- In overworld, move toward grass to find Pokemon
- Advance dialogue to progress story
- Don't get stuck repeating the same action"""


class StrategicBrain:
    """
    Long-context LLM that maintains game history and provides strategic guidance.

    This acts as a "memory" and "planner" that augments the reactive RL policy
    with longer-term strategic thinking.
    """

    def __init__(
        self,
        model: str = "qwen3:14b",
        ollama_url: str = "http://localhost:11434",
        context_window: int = 32000,
    ):
        self.model = model
        self.ollama_url = ollama_url.rstrip("/")
        self.context_window = context_window

        # Game memory
        self.memory = GameMemory()

        # Tracking
        self.last_strategic_update = 0
        self.strategic_update_interval = 5.0  # Seconds between strategic updates
        self.last_context: Optional[StrategicContext] = None

    def update(self, state: PokemonState, force: bool = False) -> Optional[StrategicContext]:
        """
        Update the strategic brain with new state.

        Only queries the LLM periodically to save resources.
        Returns strategic context if updated, None otherwise.
        """
        # Always update memory
        self.memory.add_state(state)
        self._detect_events(state)

        # Check if we should query the LLM
        now = time.time()
        if not force and (now - self.last_strategic_update) < self.strategic_update_interval:
            return self.last_context

        # Query for strategic guidance
        context = self._get_strategic_context(state)
        self.last_strategic_update = now
        self.last_context = context

        return context

    def _detect_events(self, state: PokemonState):
        """Detect significant game events from state transitions."""
        if len(self.memory.recent_states) < 2:
            return

        prev = self.memory.recent_states[-2]
        curr = self.memory.recent_states[-1]

        # Battle start
        if not prev.get("in_battle") and curr.get("in_battle"):
            self.memory.add_event("battle_start", {
                "enemy": state.enemy_pokemon_name,
                "wild": state.wild_pokemon,
            })

        # Battle end
        if prev.get("in_battle") and not curr.get("in_battle"):
            if prev.get("player_hp", 100) > 0:
                self.memory.add_event("battle_won", {
                    "enemy": prev.get("enemy_pokemon"),
                })
            else:
                self.memory.add_event("battle_lost", {
                    "enemy": prev.get("enemy_pokemon"),
                })

    def _get_strategic_context(self, state: PokemonState) -> StrategicContext:
        """Query the LLM for strategic guidance."""
        current_state = f"""
Scene: {state.scene_type}
In Battle: {state.in_battle}
Player HP: {state.player_hp}%
Enemy HP: {state.enemy_hp}%
Dialogue: {state.has_dialogue}
Menu: {state.menu_open}
Wild Pokemon: {state.wild_pokemon}
Player Pokemon: {state.player_pokemon_name}
Enemy Pokemon: {state.enemy_pokemon_name}
"""

        prompt = STRATEGIC_PROMPT.format(
            current_state=current_state,
            history=self.memory.get_history_summary(),
            objective=self.memory.current_objective,
        )

        start_time = time.perf_counter()

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_ctx": min(self.context_window, 32000),
                    },
                },
                timeout=30,
            )
            response.raise_for_status()
            elapsed = time.perf_counter() - start_time

            response_text = response.json().get("response", "")
            return self._parse_response(response_text, elapsed)

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            return StrategicContext(
                recommended_action="wait",
                reasoning=f"Error: {str(e)}",
                current_objective=self.memory.current_objective,
                progress_summary="Unable to assess",
                confidence=0.0,
                inference_time=elapsed,
            )

    def _parse_response(self, response: str, inference_time: float) -> StrategicContext:
        """Parse LLM response into StrategicContext."""
        import re

        try:
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                # Update objective if changed
                new_objective = data.get("current_objective", self.memory.current_objective)
                if new_objective:
                    self.memory.current_objective = new_objective

                return StrategicContext(
                    recommended_action=data.get("recommended_action", "wait").lower(),
                    reasoning=data.get("reasoning", ""),
                    current_objective=new_objective,
                    progress_summary=data.get("progress_summary", ""),
                    confidence=float(data.get("confidence", 0.5)),
                    inference_time=inference_time,
                )
        except (json.JSONDecodeError, ValueError):
            pass

        return StrategicContext(
            recommended_action="wait",
            reasoning="Could not parse response",
            current_objective=self.memory.current_objective,
            progress_summary="",
            confidence=0.0,
            inference_time=inference_time,
        )

    def get_augmented_state(self, state: PokemonState) -> np.ndarray:
        """
        Get an augmented state vector that includes strategic context.

        This can be used by the RL agent for better decision-making.
        """
        base_vector = state.to_vector()  # 9 dimensions

        # Add strategic features (5 dimensions)
        strategic_features = np.array([
            self.memory.battles_won / max(1, self.memory.battles_won + self.memory.battles_lost),  # Win rate
            min(1.0, self.memory.pokemon_caught / 10),  # Progress (normalized)
            1.0 if state.player_hp < 30 else 0.0,  # HP critical flag
            1.0 if self.last_context and self.last_context.confidence > 0.7 else 0.0,  # High confidence
            len(self.memory.recent_states) / 100,  # Experience (normalized)
        ], dtype=np.float32)

        return np.concatenate([base_vector, strategic_features])

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

    def save_memory(self, path: str = "game_memory.json"):
        """Save game memory to file."""
        data = {
            "battles_won": self.memory.battles_won,
            "battles_lost": self.memory.battles_lost,
            "pokemon_caught": self.memory.pokemon_caught,
            "current_objective": self.memory.current_objective,
            "known_pokemon": self.memory.known_pokemon,
            "events": [asdict(e) for e in self.memory.events[-100:]],  # Last 100 events
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def load_memory(self, path: str = "game_memory.json"):
        """Load game memory from file."""
        try:
            with open(path) as f:
                data = json.load(f)
            self.memory.battles_won = data.get("battles_won", 0)
            self.memory.battles_lost = data.get("battles_lost", 0)
            self.memory.pokemon_caught = data.get("pokemon_caught", 0)
            self.memory.current_objective = data.get("current_objective", "Explore and find wild Pokemon")
            self.memory.known_pokemon = data.get("known_pokemon", [])
        except FileNotFoundError:
            pass


def demo():
    """Demo the strategic brain."""
    from pokemon_agent import PokemonClassifier

    print("=" * 60)
    print("Strategic Brain Demo")
    print("=" * 60)

    # Initialize
    brain = StrategicBrain(model="qwen3:14b")

    # Check if model is available
    if not brain.check_model_available():
        print("Warning: qwen3:14b not available, trying phi4")
        brain = StrategicBrain(model="phi4")
        if not brain.check_model_available():
            print("Error: No suitable model available")
            print("Install with: ollama pull qwen3:14b")
            return

    print(f"Using model: {brain.model}")

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

    # Get strategic context
    print("\nQuerying strategic brain...")
    context = brain.update(state, force=True)

    print(f"\nStrategic Context:")
    print(f"  Recommended Action: {context.recommended_action}")
    print(f"  Reasoning: {context.reasoning}")
    print(f"  Current Objective: {context.current_objective}")
    print(f"  Progress: {context.progress_summary}")
    print(f"  Confidence: {context.confidence:.2f}")
    print(f"  Inference Time: {context.inference_time:.2f}s")

    # Show augmented state
    aug_state = brain.get_augmented_state(state)
    print(f"\nAugmented State Vector: {len(aug_state)} dimensions")
    print(f"  Base: {state.to_vector()}")
    print(f"  Strategic: {aug_state[9:]}")


if __name__ == "__main__":
    demo()
