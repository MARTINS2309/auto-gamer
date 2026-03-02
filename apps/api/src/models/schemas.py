from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class Algorithm(str, Enum):
    PPO = "PPO"
    A2C = "A2C"
    DQN = "DQN"
    SAC = "SAC"
    TD3 = "TD3"
    DDPG = "DDPG"


class Device(str, Enum):
    AUTO = "auto"
    CUDA = "cuda"
    CPU = "cpu"


class ObservationType(str, Enum):
    IMAGE = "image"
    RAM = "ram"


class ActionSpace(str, Enum):
    FILTERED = "filtered"
    DISCRETE = "discrete"
    MULTI_BINARY = "multi_binary"


class RewardShaping(str, Enum):
    DEFAULT = "default"


# =============================================================================
# Algorithm-Specific Hyperparameters (from SB3 documentation)
# https://stable-baselines3.readthedocs.io/en/master/
# =============================================================================


class PPOHyperparams(BaseModel):
    """PPO hyperparameters from SB3 documentation."""

    learning_rate: float = Field(default=0.0003, gt=0, description="Learning rate")
    n_steps: int = Field(default=2048, ge=1, description="Steps per environment per update")
    batch_size: int = Field(default=64, ge=1, description="Minibatch size")
    n_epochs: int = Field(default=10, ge=1, description="Number of epochs per update")
    gamma: float = Field(default=0.99, ge=0, le=1, description="Discount factor")
    gae_lambda: float = Field(
        default=0.95, ge=0, le=1, description="GAE lambda for bias-variance tradeoff"
    )
    clip_range: float = Field(default=0.2, ge=0, le=1, description="Clipping parameter")
    clip_range_vf: float | None = Field(
        default=None, ge=0, le=1, description="Value function clipping"
    )
    normalize_advantage: bool = Field(default=True, description="Normalize advantages")
    ent_coef: float = Field(default=0.0, ge=0, description="Entropy coefficient")
    vf_coef: float = Field(default=0.5, ge=0, description="Value function coefficient")
    max_grad_norm: float = Field(default=0.5, ge=0, description="Max gradient clipping")
    use_sde: bool = Field(default=False, description="Use State Dependent Exploration")
    sde_sample_freq: int = Field(default=-1, ge=-1, description="SDE noise sampling frequency")
    target_kl: float | None = Field(default=None, gt=0, description="KL divergence limit")


class A2CHyperparams(BaseModel):
    """A2C hyperparameters from SB3 documentation."""

    learning_rate: float = Field(default=0.0007, gt=0, description="Learning rate")
    n_steps: int = Field(default=5, ge=1, description="Steps per environment per update")
    gamma: float = Field(default=0.99, ge=0, le=1, description="Discount factor")
    gae_lambda: float = Field(
        default=1.0, ge=0, le=1, description="GAE lambda (1.0 = classic advantage)"
    )
    ent_coef: float = Field(default=0.0, ge=0, description="Entropy coefficient")
    vf_coef: float = Field(default=0.5, ge=0, description="Value function coefficient")
    max_grad_norm: float = Field(default=0.5, ge=0, description="Max gradient clipping")
    rms_prop_eps: float = Field(default=1e-5, gt=0, description="RMSProp epsilon")
    use_rms_prop: bool = Field(default=True, description="Use RMSprop vs Adam")
    use_sde: bool = Field(default=False, description="Use State Dependent Exploration")
    sde_sample_freq: int = Field(default=-1, ge=-1, description="SDE noise sampling frequency")
    normalize_advantage: bool = Field(default=False, description="Normalize advantages")


class DQNHyperparams(BaseModel):
    """DQN hyperparameters from SB3 documentation."""

    learning_rate: float = Field(default=0.0001, gt=0, description="Learning rate")
    buffer_size: int = Field(default=1_000_000, ge=1, description="Replay buffer size")
    learning_starts: int = Field(default=100, ge=0, description="Steps before learning")
    batch_size: int = Field(default=32, ge=1, description="Minibatch size")
    tau: float = Field(default=1.0, ge=0, le=1, description="Soft update coefficient")
    gamma: float = Field(default=0.99, ge=0, le=1, description="Discount factor")
    train_freq: int = Field(default=4, ge=1, description="Update frequency in steps")
    gradient_steps: int = Field(default=1, ge=-1, description="Gradient steps (-1 for auto)")
    target_update_interval: int = Field(
        default=10_000, ge=1, description="Target network update frequency"
    )
    exploration_fraction: float = Field(
        default=0.1, ge=0, le=1, description="Training fraction for exploration decay"
    )
    exploration_initial_eps: float = Field(
        default=1.0, ge=0, le=1, description="Initial exploration rate"
    )
    exploration_final_eps: float = Field(
        default=0.05, ge=0, le=1, description="Final exploration rate"
    )
    max_grad_norm: float = Field(default=10.0, ge=0, description="Max gradient clipping")


class SACHyperparams(BaseModel):
    """SAC (Soft Actor-Critic) hyperparameters. Continuous action spaces only."""

    learning_rate: float = Field(default=0.0003, gt=0, description="Learning rate")
    buffer_size: int = Field(default=1_000_000, ge=1, description="Replay buffer size")
    learning_starts: int = Field(default=100, ge=0, description="Steps before learning")
    batch_size: int = Field(default=256, ge=1, description="Minibatch size")
    tau: float = Field(default=0.005, ge=0, le=1, description="Soft update coefficient")
    gamma: float = Field(default=0.99, ge=0, le=1, description="Discount factor")
    train_freq: int = Field(default=1, ge=1, description="Update frequency in steps")
    gradient_steps: int = Field(default=1, ge=-1, description="Gradient steps (-1 for auto)")
    ent_coef: float = Field(default=0.1, ge=0, description="Entropy coefficient (ignored if auto)")
    ent_coef_auto: bool = Field(default=True, description="Auto-tune entropy coefficient")
    target_entropy: float = Field(default=-1.0, description="Target entropy (ignored if auto)")
    target_entropy_auto: bool = Field(default=True, description="Auto-compute target entropy")
    target_update_interval: int = Field(
        default=1, ge=1, description="Target network update frequency"
    )
    use_sde: bool = Field(default=False, description="Use State Dependent Exploration")
    sde_sample_freq: int = Field(default=-1, ge=-1, description="SDE noise sampling frequency")
    use_sde_at_warmup: bool = Field(default=False, description="Use SDE during warmup")


class TD3Hyperparams(BaseModel):
    """TD3 (Twin Delayed DDPG) hyperparameters. Continuous action spaces only."""

    learning_rate: float = Field(default=0.001, gt=0, description="Learning rate")
    buffer_size: int = Field(default=1_000_000, ge=1, description="Replay buffer size")
    learning_starts: int = Field(default=100, ge=0, description="Steps before learning")
    batch_size: int = Field(default=256, ge=1, description="Minibatch size")
    tau: float = Field(default=0.005, ge=0, le=1, description="Soft update coefficient")
    gamma: float = Field(default=0.99, ge=0, le=1, description="Discount factor")
    train_freq: int = Field(default=1, ge=1, description="Update frequency in steps")
    gradient_steps: int = Field(default=1, ge=-1, description="Gradient steps (-1 for auto)")
    policy_delay: int = Field(default=2, ge=1, description="Delay between actor updates")
    target_policy_noise: float = Field(
        default=0.2, ge=0, description="Noise added to target policy"
    )
    target_noise_clip: float = Field(default=0.5, ge=0, description="Clipping for target noise")


class DDPGHyperparams(BaseModel):
    """DDPG (Deep Deterministic Policy Gradient) hyperparameters. Continuous action spaces only."""

    learning_rate: float = Field(default=0.001, gt=0, description="Learning rate")
    buffer_size: int = Field(default=1_000_000, ge=1, description="Replay buffer size")
    learning_starts: int = Field(default=100, ge=0, description="Steps before learning")
    batch_size: int = Field(default=256, ge=1, description="Minibatch size")
    tau: float = Field(default=0.005, ge=0, le=1, description="Soft update coefficient")
    gamma: float = Field(default=0.99, ge=0, le=1, description="Discount factor")
    train_freq: int = Field(default=1, ge=1, description="Update frequency in steps")
    gradient_steps: int = Field(default=1, ge=-1, description="Gradient steps (-1 for auto)")


# Union type for algorithm-specific hyperparameters
Hyperparams = (
    PPOHyperparams
    | A2CHyperparams
    | DQNHyperparams
    | SACHyperparams
    | TD3Hyperparams
    | DDPGHyperparams
)


# Legacy compatibility - maps to PPO defaults
class RunHyperparams(BaseModel):
    """Legacy hyperparams model - use algorithm-specific models for new code."""

    learning_rate: float = Field(default=0.0003, gt=0)
    n_steps: int = Field(default=2048, ge=1)
    batch_size: int = Field(default=64, ge=1)
    n_epochs: int = Field(default=10, ge=1)
    gamma: float = Field(default=0.99, ge=0, le=1)
    gae_lambda: float = Field(default=0.95, ge=0, le=1)
    clip_range: float = Field(default=0.2, ge=0, le=1)
    ent_coef: float = Field(default=0.0, ge=0)
    vf_coef: float = Field(default=0.5, ge=0)
    max_grad_norm: float = Field(default=0.5, ge=0)


# =============================================================================
# Agent Schemas
# =============================================================================


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    algorithm: Algorithm = Algorithm.PPO
    game_id: str = Field(min_length=1)
    hyperparams: RunHyperparams = Field(default_factory=RunHyperparams)
    observation_type: ObservationType = ObservationType.IMAGE
    action_space: ActionSpace = ActionSpace.FILTERED


class AgentUpdate(BaseModel):
    """Only name, description, and hyperparams can be updated. Algorithm/obs/action are immutable."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    hyperparams: RunHyperparams | None = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    algorithm: Algorithm
    game_id: str
    game_name: str | None = None
    hyperparams: dict[str, Any] | None = None
    observation_type: ObservationType
    action_space: ActionSpace
    total_steps: int = 0
    total_runs: int = 0
    best_reward: float | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentSummary(BaseModel):
    """Lightweight agent info for dropdowns/selectors."""

    id: str
    name: str
    algorithm: Algorithm
    game_id: str
    game_name: str | None = None
    total_steps: int = 0
    total_runs: int = 0
    best_reward: float | None = None

    class Config:
        from_attributes = True


# =============================================================================
# Run Schemas
# =============================================================================


class RunConfig(BaseModel):
    rom: str = Field(min_length=1)
    state: str = Field(min_length=1)
    algorithm: Algorithm = Algorithm.PPO
    hyperparams: RunHyperparams = Field(default_factory=RunHyperparams)
    n_envs: int = Field(default=1, ge=1, le=64)
    max_steps: int = Field(default=1_000_000, ge=1, le=100_000_000)
    checkpoint_interval: int = Field(default=50_000, ge=1000, le=10_000_000)
    frame_fps: int = Field(default=15, ge=1, le=60)
    reward_shaping: RewardShaping = RewardShaping.DEFAULT
    observation_type: ObservationType = ObservationType.IMAGE
    action_space: ActionSpace = ActionSpace.FILTERED
    agent_id: str = Field(min_length=1)
    opponent_agent_id: str | None = None


class RunCreate(RunConfig):
    pass


class RunUpdate(BaseModel):
    """Schema for updating a run's configuration (only allowed for specific fields/status)."""

    hyperparams: RunHyperparams | None = None
    # Potentially other fields later


class RunResponse(RunConfig):
    id: str
    status: RunStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    pid: int | None = Field(default=None, ge=1)
    error: str | None = None
    agent_id: str | None = None  # type: ignore[assignment]  # Nullable for old runs
    agent_name: str | None = None
    opponent_agent_id: str | None = None
    opponent_agent_name: str | None = None
    game_name: str | None = None
    game_thumbnail_url: str | None = None

    # Metrics summary (populated from latest metric row)
    latest_step: int | None = None
    best_reward: float | None = None
    avg_reward: float | None = None

    class Config:
        from_attributes = True


class MetricPoint(BaseModel):
    step: int = Field(ge=0)
    timestamp: float = Field(ge=0)
    reward: float | None = 0.0
    avg_reward: float | None = 0.0
    best_reward: float | None = 0.0
    fps: float | None = Field(default=0.0, ge=0)
    loss: float | None = None
    epsilon: float | None = Field(default=None, ge=0, le=1)
    details: dict[str, Any] | None = None
    type: str = "metric"


class ActionCommand(BaseModel):
    action: Literal["stop", "pause", "resume", "screenshot"]
