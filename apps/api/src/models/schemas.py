from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

class RunHyperparams(BaseModel):
    learning_rate: float = 0.0003
    n_steps: int = 2048
    batch_size: int = 64
    n_epochs: int = 10
    gamma: float = 0.99
    clip_range: float = 0.2
    ent_coef: float = 0.0
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5

class RunConfig(BaseModel):
    rom: str
    state: str
    algorithm: str = "PPO"
    hyperparams: RunHyperparams
    n_envs: int = 1
    max_steps: int = 1_000_000
    checkpoint_interval: int = 50_000
    frame_capture_interval: int = 10_000
    reward_shaping: str = "default"
    observation_type: str = "image" # image, ram, etc.
    action_space: str = "filtered"

class RunCreate(RunConfig):
    pass

class RunResponse(RunConfig):
    id: str
    status: RunStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pid: Optional[int] = None
    error: Optional[str] = None
    
    class Config:
        from_attributes = True

class MetricPoint(BaseModel):
    step: int
    timestamp: float
    reward: float
    avg_reward: float
    best_reward: float
    fps: float
    loss: Optional[float] = None
    epsilon: Optional[float] = None

class ActionCommand(BaseModel):
    action: str # stop, pause, resume, screenshot
