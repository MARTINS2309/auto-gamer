from collections import deque

import cv2
import gymnasium as gym
import numpy as np
from gymnasium.wrappers import (
    FrameStackObservation,
    GrayscaleObservation,
    ResizeObservation,
)
from stable_baselines3 import A2C, DDPG, DQN, PPO, SAC, TD3
from stable_baselines3.common.monitor import Monitor

ALGO_MAP = {"PPO": PPO, "A2C": A2C, "DQN": DQN, "SAC": SAC, "TD3": TD3, "DDPG": DDPG}


class SimpleDiscreteActions(gym.ActionWrapper):
    """
    Convert MultiBinary action space to Discrete(n_buttons).
    Allows pressing one button at a time.
    """

    def __init__(self, env):
        super().__init__(env)
        # Assume MultiBinary
        self.n_buttons = env.action_space.shape[0]
        self.action_space = gym.spaces.Discrete(self.n_buttons)

    def action(self, action):
        vec = np.zeros(self.n_buttons, dtype=np.int8)
        vec[action] = 1
        return vec


class SelfPlayWrapper(gym.Wrapper):
    """
    Wraps a 2-player retro env, providing frozen opponent inference for Player 2.
    Presents a single-player MultiBinary(n_buttons) interface to the outer wrapper chain.

    Placement in wrapper chain:
        retro.make(players=2)   # MultiBinary(2 * n_buttons)
        -> SelfPlayWrapper      # MultiBinary(n_buttons) — hides P2
        -> SimpleDiscreteActions # Discrete(n_buttons)
        -> Monitor -> ResizeObs -> Grayscale -> FrameStack
    """

    def __init__(
        self,
        env: gym.Env,
        opponent_model_path: str,
        algorithm: str,
        n_buttons: int,
        device: str = "cpu",
    ):
        super().__init__(env)
        self.n_buttons = n_buttons
        self.action_space = gym.spaces.MultiBinary(n_buttons)
        # observation_space stays the same (shared screen)

        # Load frozen opponent (CPU by default to avoid GPU contention)
        AlgoClass = ALGO_MAP.get(algorithm, PPO)
        self.opponent = AlgoClass.load(opponent_model_path, device=device)  # type: ignore[attr-defined]
        print(f"[SelfPlay] Loaded opponent model from {opponent_model_path} ({algorithm}) on {device}")

        # Internal observation pipeline for opponent inference:
        # raw RGB -> resize 84x84 -> grayscale -> stack 4 frames
        self._opp_frames: deque[np.ndarray] = deque(maxlen=4)
        self._last_raw_obs: np.ndarray | None = None

    def _opponent_obs(self, raw_rgb: np.ndarray) -> np.ndarray:
        """Raw RGB (H, W, 3) -> (4, 84, 84) grayscale stacked, matching training wrappers."""
        frame = cv2.resize(raw_rgb, (84, 84), interpolation=cv2.INTER_AREA)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        self._opp_frames.append(frame)
        while len(self._opp_frames) < 4:
            self._opp_frames.appendleft(frame)
        return np.stack(list(self._opp_frames), axis=0)

    def step(self, p1_action):  # type: ignore[override]
        """
        p1_action: MultiBinary(n_buttons) from outer wrapper chain.
        Gets opponent action via frozen model, combines both, steps 2-player env.
        """
        # Get opponent's discrete action from frozen model
        opp_obs = self._opponent_obs(self._last_raw_obs)  # type: ignore[arg-type]
        p2_discrete, _ = self.opponent.predict(opp_obs, deterministic=True)

        # Convert Discrete -> MultiBinary (one-hot)
        p2_multi = np.zeros(self.n_buttons, dtype=np.int8)
        p2_multi[int(p2_discrete)] = 1

        # Combine: [P1 buttons | P2 buttons]
        combined = np.concatenate([p1_action, p2_multi])
        obs, reward, terminated, truncated, info = self.env.step(combined)
        self._last_raw_obs = obs
        return obs, reward, terminated, truncated, info

    def reset(self, **kwargs):  # type: ignore[override]
        obs, info = self.env.reset(**kwargs)
        self._last_raw_obs = obs
        self._opp_frames.clear()
        return obs, info


def make_retro_env(
    game,
    state,
    observation_type="image",
    action_space="filtered",
    record_dir=None,
    opponent_model_path=None,
    opponent_algorithm=None,
    opponent_device="cpu",
):
    """
    Create a retro environment with wrappers.

    Args:
        game: ROM game name
        state: Save state name
        observation_type: "image" or "ram"
        action_space: "filtered", "discrete", or "multi_binary"
        record_dir: Directory to save BK2 recordings (None = no recording)
        opponent_model_path: Path to frozen opponent model for self-play (enables 2-player)
        opponent_algorithm: Algorithm name of the opponent model (e.g., "PPO")
        opponent_device: Device for opponent inference (default: "cpu")
    """
    import retro

    players = 2 if opponent_model_path else 1

    # record parameter accepts a directory path for BK2 movie files
    env = retro.make(
        game=game,
        state=state,
        render_mode="rgb_array",
        record=record_dir,
        players=players,
    )

    # Self-play wrapper: sits between retro.make(players=2) and SimpleDiscreteActions
    if opponent_model_path:
        n_buttons = env.action_space.shape[0] // 2  # MultiBinary(2*n) -> n per player
        env = SelfPlayWrapper(
            env,
            opponent_model_path=opponent_model_path,
            algorithm=opponent_algorithm or "PPO",
            n_buttons=n_buttons,
            device=opponent_device,
        )

    # Apply action wrapper - convert multi_binary to discrete for easier learning
    if action_space in ("filtered", "discrete"):
        # TODO: "filtered" should ideally be a list of useful combos
        # For now, we fallback to simple discrete (single buttons) ensuring DQN compatibility
        env = SimpleDiscreteActions(env)
    # "multi_binary" keeps the original action space

    env = Monitor(env)

    if observation_type == "image":
        env = ResizeObservation(env, (84, 84))
        env = GrayscaleObservation(env)
        env = FrameStackObservation(env, stack_size=4)
    # "ram" uses raw RAM observations without image processing

    return env
