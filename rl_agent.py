"""
Reinforcement Learning Agent Module

Generic RL environment wrapper and PPO agent implementation using stable-baselines3.
Designed to work with any game that can provide a state vector and accept discrete actions.
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback


class GameEnvironment(gym.Env, ABC):
    """
    Abstract base class for game environments.

    Subclasses must implement:
        - _get_state(): Return current game state as numpy array
        - _execute_action(action): Execute the given action in the game
        - _calculate_reward(): Calculate reward based on state transition
        - _check_done(): Check if episode is finished
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        state_dim: int,
        n_actions: int,
        step_delay: float = 0.3,
        max_episode_steps: int = 2000,
    ):
        """
        Initialize the game environment.

        Args:
            state_dim: Dimension of the state vector
            n_actions: Number of discrete actions available
            step_delay: Delay between steps in seconds
            max_episode_steps: Maximum steps before episode reset
        """
        super().__init__()

        self.state_dim = state_dim
        self.n_actions = n_actions
        self.step_delay = step_delay
        self.max_episode_steps = max_episode_steps

        # Define spaces
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(state_dim,),
            dtype=np.float32,
        )
        self.action_space = spaces.Discrete(n_actions)

        # Episode tracking
        self.current_step = 0
        self.episode_reward = 0.0
        self.previous_state: Optional[np.ndarray] = None

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ) -> tuple[np.ndarray, dict]:
        """Reset the environment for a new episode."""
        super().reset(seed=seed)

        self.current_step = 0
        self.episode_reward = 0.0
        self.previous_state = None

        # Get initial state
        state = self._get_state()
        self.previous_state = state.copy()

        return state, {}

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]:
        """
        Execute one step in the environment.

        Args:
            action: Discrete action to execute

        Returns:
            observation: New state observation
            reward: Reward from this step
            terminated: Whether episode ended naturally
            truncated: Whether episode was cut short
            info: Additional information
        """
        import time

        # Execute action
        self._execute_action(action)

        # Wait for game to respond
        time.sleep(self.step_delay)

        # Get new state
        state = self._get_state()

        # Calculate reward
        reward = self._calculate_reward()
        self.episode_reward += reward

        # Check if done
        terminated = self._check_done()
        self.current_step += 1
        truncated = self.current_step >= self.max_episode_steps

        # Update previous state
        self.previous_state = state.copy()

        info = {
            "episode_reward": self.episode_reward,
            "current_step": self.current_step,
        }

        return state, reward, terminated, truncated, info

    @abstractmethod
    def _get_state(self) -> np.ndarray:
        """Get current game state as numpy array."""
        pass

    @abstractmethod
    def _execute_action(self, action: int) -> None:
        """Execute the given action in the game."""
        pass

    @abstractmethod
    def _calculate_reward(self) -> float:
        """Calculate reward based on state transition."""
        pass

    @abstractmethod
    def _check_done(self) -> bool:
        """Check if episode should end."""
        pass

    def render(self) -> None:
        """Render is handled by the actual game."""
        pass

    def close(self) -> None:
        """Cleanup resources."""
        pass


class RewardTracker(BaseCallback):
    """Callback to track and log rewards during training."""

    def __init__(self, log_freq: int = 100, verbose: int = 1):
        super().__init__(verbose)
        self.log_freq = log_freq
        self.episode_rewards: list[float] = []
        self.episode_lengths: list[int] = []
        self.current_episode_reward = 0.0
        self.current_episode_length = 0

    def _on_step(self) -> bool:
        # Track rewards
        reward = self.locals.get("rewards", [0])[0]
        self.current_episode_reward += reward
        self.current_episode_length += 1

        # Check for episode end
        dones = self.locals.get("dones", [False])
        if dones[0]:
            self.episode_rewards.append(self.current_episode_reward)
            self.episode_lengths.append(self.current_episode_length)

            if self.verbose > 0 and len(self.episode_rewards) % self.log_freq == 0:
                avg_reward = np.mean(self.episode_rewards[-self.log_freq :])
                avg_length = np.mean(self.episode_lengths[-self.log_freq :])
                print(
                    f"Episode {len(self.episode_rewards)} | "
                    f"Avg Reward: {avg_reward:.2f} | "
                    f"Avg Length: {avg_length:.1f}"
                )

            self.current_episode_reward = 0.0
            self.current_episode_length = 0

        return True

    def get_stats(self) -> dict:
        """Get training statistics."""
        if not self.episode_rewards:
            return {"episodes": 0}

        return {
            "episodes": len(self.episode_rewards),
            "avg_reward": np.mean(self.episode_rewards),
            "max_reward": np.max(self.episode_rewards),
            "min_reward": np.min(self.episode_rewards),
            "avg_length": np.mean(self.episode_lengths),
        }


class RLAgent:
    """
    Wrapper for PPO agent with training and inference capabilities.

    Attributes:
        env: The game environment
        model_path: Path to save/load the trained model
    """

    def __init__(
        self,
        env: GameEnvironment,
        model_path: str = "models/agent.zip",
        learning_rate: float = 3e-4,
        n_steps: int = 512,
        batch_size: int = 64,
        ent_coef: float = 0.05,
        net_arch: Optional[list[int]] = None,
    ):
        """
        Initialize the RL agent.

        Args:
            env: Game environment to train on
            model_path: Path to save/load model
            learning_rate: Learning rate for PPO
            n_steps: Number of steps before policy update
            batch_size: Batch size for training
            ent_coef: Entropy coefficient for exploration
            net_arch: Neural network architecture
        """
        self.env = env
        self.model_path = Path(model_path)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)

        if net_arch is None:
            net_arch = [128, 128]

        # Create or load model
        if self.model_path.exists():
            print(f"Loading existing model from {self.model_path}")
            self.model = PPO.load(str(self.model_path), env=env)
        else:
            print("Creating new PPO model")
            self.model = PPO(
                "MlpPolicy",
                env,
                learning_rate=learning_rate,
                n_steps=n_steps,
                batch_size=batch_size,
                ent_coef=ent_coef,
                policy_kwargs={"net_arch": net_arch},
                verbose=1,
            )

        self.reward_tracker = RewardTracker()

    def train(
        self,
        total_timesteps: int = 10000,
        checkpoint_freq: int = 5000,
    ) -> dict:
        """
        Train the agent.

        Args:
            total_timesteps: Total training steps
            checkpoint_freq: Steps between saving checkpoints

        Returns:
            Training statistics
        """
        checkpoint_callback = CheckpointCallback(
            save_freq=checkpoint_freq,
            save_path=str(self.model_path.parent),
            name_prefix="checkpoint",
        )

        print(f"Starting training for {total_timesteps} steps...")

        self.model.learn(
            total_timesteps=total_timesteps,
            callback=[self.reward_tracker, checkpoint_callback],
            reset_num_timesteps=False,
        )

        # Save final model
        self.model.save(str(self.model_path))
        print(f"Model saved to {self.model_path}")

        return self.reward_tracker.get_stats()

    def predict(self, state: np.ndarray, deterministic: bool = True) -> int:
        """
        Predict action for given state.

        Args:
            state: Current game state
            deterministic: Whether to use deterministic policy

        Returns:
            Selected action index
        """
        action, _ = self.model.predict(state, deterministic=deterministic)
        return int(action)

    def play(self, n_steps: int = 100, render: bool = True) -> float:
        """
        Run the trained agent.

        Args:
            n_steps: Number of steps to run
            render: Whether to render (no-op for screen-based games)

        Returns:
            Total reward achieved
        """
        state, _ = self.env.reset()
        total_reward = 0.0

        for step in range(n_steps):
            action = self.predict(state)
            state, reward, terminated, truncated, info = self.env.step(action)
            total_reward += reward

            if terminated or truncated:
                print(f"Episode ended at step {step + 1}")
                state, _ = self.env.reset()

        print(f"Play session complete. Total reward: {total_reward:.2f}")
        return total_reward


if __name__ == "__main__":
    # Test with a simple dummy environment
    class DummyEnv(GameEnvironment):
        def __init__(self):
            super().__init__(state_dim=4, n_actions=4, step_delay=0.01)
            self._state = np.zeros(4, dtype=np.float32)

        def _get_state(self) -> np.ndarray:
            return self._state

        def _execute_action(self, action: int) -> None:
            self._state = np.random.randn(4).astype(np.float32)

        def _calculate_reward(self) -> float:
            return np.random.uniform(-1, 1)

        def _check_done(self) -> bool:
            return False

    print("Testing RL Agent with dummy environment...")
    env = DummyEnv()
    agent = RLAgent(env, model_path="models/test_agent.zip")

    # Quick training test
    stats = agent.train(total_timesteps=100)
    print(f"Training stats: {stats}")

    # Cleanup
    import shutil
    if Path("models").exists():
        shutil.rmtree("models")
    print("Test complete!")
