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


class RunHyperparams(BaseModel):
    learning_rate: float = Field(default=0.0003, ge=1e-7, le=1)
    n_steps: int = Field(default=2048, ge=1, le=16384)
    batch_size: int = Field(default=64, ge=1, le=1024)
    n_epochs: int = Field(default=10, ge=1, le=100)
    gamma: float = Field(default=0.99, ge=0, le=1)
    gae_lambda: float = Field(default=0.95, ge=0, le=1)
    clip_range: float = Field(default=0.2, ge=0, le=1)
    ent_coef: float = Field(default=0.0, ge=0, le=1)
    vf_coef: float = Field(default=0.5, ge=0, le=1)
    max_grad_norm: float = Field(default=0.5, ge=0, le=10)


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
    reward: float
    avg_reward: float
    best_reward: float
    fps: float = Field(ge=0)
    loss: Optional[float] = None
    epsilon: Optional[float] = Field(default=None, ge=0, le=1)


class ActionCommand(BaseModel):
    action: Literal["stop", "pause", "resume", "screenshot"]
