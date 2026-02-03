from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union, Literal
from datetime import datetime
from enum import Enum


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
    gae_lambda: float = Field(default=0.95, ge=0, le=1, description="GAE lambda for bias-variance tradeoff")
    clip_range: float = Field(default=0.2, ge=0, le=1, description="Clipping parameter")
    clip_range_vf: Optional[float] = Field(default=None, ge=0, le=1, description="Value function clipping")
    normalize_advantage: bool = Field(default=True, description="Normalize advantages")
    ent_coef: float = Field(default=0.0, ge=0, description="Entropy coefficient")
    vf_coef: float = Field(default=0.5, ge=0, description="Value function coefficient")
    max_grad_norm: float = Field(default=0.5, ge=0, description="Max gradient clipping")
    use_sde: bool = Field(default=False, description="Use State Dependent Exploration")
    sde_sample_freq: int = Field(default=-1, ge=-1, description="SDE noise sampling frequency")
    target_kl: Optional[float] = Field(default=None, gt=0, description="KL divergence limit")


class A2CHyperparams(BaseModel):
    """A2C hyperparameters from SB3 documentation."""
    learning_rate: float = Field(default=0.0007, gt=0, description="Learning rate")
    n_steps: int = Field(default=5, ge=1, description="Steps per environment per update")
    gamma: float = Field(default=0.99, ge=0, le=1, description="Discount factor")
    gae_lambda: float = Field(default=1.0, ge=0, le=1, description="GAE lambda (1.0 = classic advantage)")
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
    target_update_interval: int = Field(default=10_000, ge=1, description="Target network update frequency")
    exploration_fraction: float = Field(default=0.1, ge=0, le=1, description="Training fraction for exploration decay")
    exploration_initial_eps: float = Field(default=1.0, ge=0, le=1, description="Initial exploration rate")
    exploration_final_eps: float = Field(default=0.05, ge=0, le=1, description="Final exploration rate")
    max_grad_norm: float = Field(default=10.0, ge=0, description="Max gradient clipping")


# Union type for algorithm-specific hyperparameters
Hyperparams = Union[PPOHyperparams, A2CHyperparams, DQNHyperparams]


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


class RunConfig(BaseModel):
    rom: str = Field(min_length=1)
    state: str = Field(min_length=1)
    algorithm: Algorithm = Algorithm.PPO
    hyperparams: RunHyperparams = Field(default_factory=RunHyperparams)
    n_envs: int = Field(default=1, ge=1, le=64)
    max_steps: int = Field(default=1_000_000, ge=1, le=100_000_000)
    checkpoint_interval: int = Field(default=50_000, ge=1000, le=10_000_000)
    frame_capture_interval: int = Field(default=10_000, ge=1, le=100_000)
    reward_shaping: RewardShaping = RewardShaping.DEFAULT
    observation_type: ObservationType = ObservationType.IMAGE
    action_space: ActionSpace = ActionSpace.FILTERED


class RunCreate(RunConfig):
    pass


class RunUpdate(BaseModel):
    """Schema for updating a run's configuration (only allowed for specific fields/status)."""
    hyperparams: Optional[RunHyperparams] = None
    # Potentially other fields later


class RunResponse(RunConfig):
    id: str
    status: RunStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pid: Optional[int] = Field(default=None, ge=1)
    error: Optional[str] = None

    class Config:
        from_attributes = True


class MetricPoint(BaseModel):
    step: int = Field(ge=0)
    timestamp: float = Field(ge=0)
    reward: Optional[float] = 0.0
    avg_reward: Optional[float] = 0.0
    best_reward: Optional[float] = 0.0
    fps: Optional[float] = Field(default=0.0, ge=0)
    loss: Optional[float] = None
    epsilon: Optional[float] = Field(default=None, ge=0, le=1)
    details: Optional[Dict[str, Any]] = None
    type: str = "metric"


class ActionCommand(BaseModel):
    action: Literal["stop", "pause", "resume", "screenshot"]
