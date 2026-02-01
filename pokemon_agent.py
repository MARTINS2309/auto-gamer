"""
Pokemon Agent Module

Pokemon-specific implementation of the game agent that uses vision-based
state detection, custom reward shaping, and GBA emulator input.
"""

import argparse
import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pyautogui

from rl_agent import GameEnvironment, RLAgent
from vision_classifier import VisionClassifier, parse_json_from_response


# Disable pyautogui failsafe (moving mouse to corner won't stop the script)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05  # Small delay between keypresses


@dataclass
class PokemonState:
    """Pokemon game state extracted from screen."""

    scene_type: str = "unknown"  # overworld, battle, menu, dialogue, title
    in_battle: bool = False
    player_hp: int = 100
    player_hp_max: int = 100
    enemy_hp: int = 100
    enemy_hp_max: int = 100
    can_catch: bool = False
    has_dialogue: bool = False
    menu_open: bool = False
    wild_pokemon: bool = False
    trainer_battle: bool = False
    player_pokemon_name: str = ""
    enemy_pokemon_name: str = ""
    raw_response: str = ""
    inference_time: float = 0.0

    def to_vector(self) -> np.ndarray:
        """Convert state to numpy array for RL agent."""
        scene_encoding = {
            "overworld": 0,
            "battle": 1,
            "menu": 2,
            "dialogue": 3,
            "title": 4,
            "unknown": 5,
        }

        return np.array(
            [
                scene_encoding.get(self.scene_type, 5),
                float(self.in_battle),
                self.player_hp / max(self.player_hp_max, 1),
                self.enemy_hp / max(self.enemy_hp_max, 1),
                float(self.can_catch),
                float(self.has_dialogue),
                float(self.menu_open),
                float(self.wild_pokemon),
                float(self.trainer_battle),
            ],
            dtype=np.float32,
        )


class EmulatorKeys:
    """Key mappings for different emulators."""

    MGBA = {
        "a": "x",
        "b": "z",
        "start": "enter",
        "select": "backspace",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "l": "a",
        "r": "s",
    }

    VBA = {
        "a": "z",
        "b": "x",
        "start": "enter",
        "select": "backspace",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "l": "a",
        "r": "s",
    }


class PokemonClassifier(VisionClassifier):
    """Pokemon-specific vision classifier."""

    POKEMON_PROMPT = """Analyze this Pokemon game screenshot and respond with a JSON object containing:
{
    "scene_type": "overworld" or "battle" or "menu" or "dialogue" or "title",
    "in_battle": true/false,
    "player_hp_percent": 0-100 (estimate from HP bar if in battle),
    "enemy_hp_percent": 0-100 (estimate from HP bar if in battle),
    "can_catch": true/false (only true if in wild battle with pokeballs),
    "has_dialogue": true/false (text box visible),
    "menu_open": true/false,
    "wild_pokemon": true/false (wild encounter, not trainer),
    "player_pokemon": "name if visible",
    "enemy_pokemon": "name if visible"
}

Be concise. Only output the JSON object."""

    def classify_pokemon_state(self) -> PokemonState:
        """Capture screen and extract Pokemon game state."""
        img = self.capture_screen()
        start_time = time.time()
        response = self.query_vlm(img, self.POKEMON_PROMPT)
        elapsed = time.time() - start_time

        # Parse response
        state = PokemonState(raw_response=response, inference_time=elapsed)

        # Try to extract JSON
        data = parse_json_from_response(response)

        if data:
            state.scene_type = data.get("scene_type", "unknown").lower()
            state.in_battle = bool(data.get("in_battle", False))
            state.player_hp = int(data.get("player_hp_percent", 100))
            state.player_hp_max = 100
            state.enemy_hp = int(data.get("enemy_hp_percent", 100))
            state.enemy_hp_max = 100
            state.can_catch = bool(data.get("can_catch", False))
            state.has_dialogue = bool(data.get("has_dialogue", False))
            state.menu_open = bool(data.get("menu_open", False))
            state.wild_pokemon = bool(data.get("wild_pokemon", False))
            state.trainer_battle = state.in_battle and not state.wild_pokemon
            state.player_pokemon_name = data.get("player_pokemon", "")
            state.enemy_pokemon_name = data.get("enemy_pokemon", "")
        else:
            # Fallback: try to extract from text
            response_lower = response.lower()
            state.in_battle = "battle" in response_lower or "fighting" in response_lower
            state.has_dialogue = "dialogue" in response_lower or "text" in response_lower
            state.menu_open = "menu" in response_lower

            if state.in_battle:
                state.scene_type = "battle"
            elif state.menu_open:
                state.scene_type = "menu"
            elif state.has_dialogue:
                state.scene_type = "dialogue"
            else:
                state.scene_type = "overworld"

        return state


class PokemonEnv(GameEnvironment):
    """Pokemon game environment for RL training."""

    # Action mapping
    ACTIONS = [
        "up",
        "down",
        "left",
        "right",
        "a",
        "b",
        "start",
        "wait",
    ]

    def __init__(
        self,
        model: str = "llava:7b",
        emulator: str = "mgba",
        step_delay: float = 0.3,
        max_episode_steps: int = 2000,
    ):
        super().__init__(
            state_dim=9,  # PokemonState.to_vector() dimension
            n_actions=len(self.ACTIONS),
            step_delay=step_delay,
            max_episode_steps=max_episode_steps,
        )

        self.classifier = PokemonClassifier(model=model)
        self.key_map = getattr(EmulatorKeys, emulator.upper(), EmulatorKeys.MGBA)

        # State tracking for rewards
        self.current_state: Optional[PokemonState] = None
        self.previous_pokemon_state: Optional[PokemonState] = None
        self.battles_won = 0
        self.battles_lost = 0
        self.pokemon_caught = 0

    def _get_state(self) -> np.ndarray:
        """Get current game state via vision classifier."""
        self.previous_pokemon_state = self.current_state
        self.current_state = self.classifier.classify_pokemon_state()
        return self.current_state.to_vector()

    def _execute_action(self, action: int) -> None:
        """Execute action via keyboard input."""
        action_name = self.ACTIONS[action]

        if action_name == "wait":
            return  # No key press

        # Map to emulator key
        key = self.key_map.get(action_name, action_name)
        pyautogui.press(key)

    def _calculate_reward(self) -> float:
        """Calculate reward based on state transition."""
        if self.current_state is None:
            return 0.0

        reward = 0.0
        curr = self.current_state
        prev = self.previous_pokemon_state

        # Exploration reward
        if curr.scene_type == "overworld":
            reward += 0.1  # Small reward for moving around

        # Battle rewards
        if curr.in_battle:
            if prev and prev.in_battle:
                # Track HP changes
                player_hp_delta = curr.player_hp - prev.player_hp
                enemy_hp_delta = curr.enemy_hp - prev.enemy_hp

                # Reward for damaging enemy
                if enemy_hp_delta < 0:
                    reward += abs(enemy_hp_delta) * 0.05

                # Penalty for taking damage
                if player_hp_delta < 0:
                    reward -= abs(player_hp_delta) * 0.02

                # Big reward for winning (enemy HP goes to 0)
                if curr.enemy_hp <= 0 and prev.enemy_hp > 0:
                    reward += 10.0
                    self.battles_won += 1

            elif prev and not prev.in_battle:
                # Just entered battle - small reward for encountering Pokemon
                if curr.wild_pokemon:
                    reward += 1.0

        # Battle ended (was in battle, now not)
        if prev and prev.in_battle and not curr.in_battle:
            if prev.player_hp > 0:
                # We survived - likely won or ran
                reward += 2.0
            else:
                # We fainted
                reward -= 5.0
                self.battles_lost += 1

        # Penalty for getting stuck in dialogue/menu too long
        if curr.has_dialogue or curr.menu_open:
            reward -= 0.05

        return reward

    def _check_done(self) -> bool:
        """Check if episode should end."""
        if self.current_state is None:
            return False

        # Episode ends if player faints (could add more conditions)
        if self.current_state.in_battle and self.current_state.player_hp <= 0:
            return True

        return False

    def get_stats(self) -> dict:
        """Get training statistics."""
        return {
            "battles_won": self.battles_won,
            "battles_lost": self.battles_lost,
            "pokemon_caught": self.pokemon_caught,
        }


class PokemonAgent:
    """High-level Pokemon agent that combines vision, RL, and input."""

    def __init__(
        self,
        model: str = "llava:7b",
        emulator: str = "mgba",
        model_path: str = "models/pokemon_agent.zip",
    ):
        self.env = PokemonEnv(model=model, emulator=emulator)
        self.agent = RLAgent(
            self.env,
            model_path=model_path,
            learning_rate=3e-4,
            n_steps=512,
            batch_size=64,
            ent_coef=0.05,
            net_arch=[128, 128],
        )

    def demo(self, n_captures: int = 5) -> None:
        """
        Demo mode: capture and classify screen several times.

        Args:
            n_captures: Number of screen captures to analyze
        """
        print(f"\nDemo Mode: Capturing and classifying {n_captures} frames")
        print("Make sure the emulator window is visible!\n")

        # Give user time to switch to emulator
        for i in range(5, 0, -1):
            print(f"Starting in {i}...")
            time.sleep(1)

        for i in range(n_captures):
            print(f"\n--- Capture {i + 1}/{n_captures} ---")
            state = self.env.classifier.classify_pokemon_state()

            print(f"Scene: {state.scene_type}")
            print(f"In Battle: {state.in_battle}")
            if state.in_battle:
                print(f"  Player HP: {state.player_hp}%")
                print(f"  Enemy HP: {state.enemy_hp}%")
                print(f"  Wild: {state.wild_pokemon}")
                print(f"  Can Catch: {state.can_catch}")
            print(f"Dialogue: {state.has_dialogue}")
            print(f"Menu: {state.menu_open}")
            print(f"Inference Time: {state.inference_time:.2f}s")

            if i < n_captures - 1:
                time.sleep(2)  # Wait between captures

    def train(self, total_steps: int = 10000, checkpoint_freq: int = 2000) -> None:
        """
        Train the agent.

        Args:
            total_steps: Total training timesteps
            checkpoint_freq: Steps between checkpoints
        """
        print(f"\nTraining Mode: {total_steps} steps")
        print("Make sure the emulator window is visible and focused!")
        print("Tip: Use Tab in mGBA to fast-forward\n")

        # Countdown
        for i in range(5, 0, -1):
            print(f"Starting in {i}...")
            time.sleep(1)

        stats = self.agent.train(
            total_timesteps=total_steps,
            checkpoint_freq=checkpoint_freq,
        )

        print("\n=== Training Complete ===")
        print(f"Stats: {stats}")
        print(f"Environment Stats: {self.env.get_stats()}")

    def play(self, n_steps: int = 500) -> None:
        """
        Run the trained agent.

        Args:
            n_steps: Number of steps to run
        """
        print(f"\nPlay Mode: Running for {n_steps} steps")
        print("Make sure the emulator window is visible!")

        # Countdown
        for i in range(5, 0, -1):
            print(f"Starting in {i}...")
            time.sleep(1)

        total_reward = self.agent.play(n_steps=n_steps)
        print(f"\nTotal reward: {total_reward:.2f}")
        print(f"Environment Stats: {self.env.get_stats()}")


def main():
    parser = argparse.ArgumentParser(description="Pokemon AI Agent")
    parser.add_argument(
        "command",
        choices=["demo", "train", "play"],
        help="Command to run",
    )
    parser.add_argument(
        "--model",
        default="llava:7b",
        help="Ollama model to use (default: llava:7b)",
    )
    parser.add_argument(
        "--emulator",
        default="mgba",
        choices=["mgba", "vba"],
        help="Emulator key mapping (default: mgba)",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=10000,
        help="Number of steps for train/play (default: 10000)",
    )
    parser.add_argument(
        "--captures",
        type=int,
        default=5,
        help="Number of captures for demo (default: 5)",
    )
    parser.add_argument(
        "--model-path",
        default="models/pokemon_agent.zip",
        help="Path to save/load model",
    )

    args = parser.parse_args()

    agent = PokemonAgent(
        model=args.model,
        emulator=args.emulator,
        model_path=args.model_path,
    )

    if args.command == "demo":
        agent.demo(n_captures=args.captures)
    elif args.command == "train":
        agent.train(total_steps=args.steps)
    elif args.command == "play":
        agent.play(n_steps=args.steps)


if __name__ == "__main__":
    main()
