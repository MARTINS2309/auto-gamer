import gymnasium as gym
import numpy as np
from gymnasium.wrappers import (
    FrameStackObservation,
    GrayscaleObservation,
    ResizeObservation,
)
from stable_baselines3.common.monitor import Monitor


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


def make_retro_env(
    game,
    state,
    observation_type="image",
    action_space="filtered",
    record_dir=None,
):
    """
    Create a retro environment with wrappers.

    Args:
        game: ROM game name
        state: Save state name
        observation_type: "image" or "ram"
        action_space: "filtered", "discrete", or "multi_binary"
        record_dir: Directory to save BK2 recordings (None = no recording)
    """
    import retro

    # record parameter accepts a directory path for BK2 movie files
    env = retro.make(
        game=game,
        state=state,
        render_mode="rgb_array",
        record=record_dir,
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
