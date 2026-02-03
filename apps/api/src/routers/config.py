from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import json
import os

from ..models.db import DATA_DIR
from ..models.schemas import RunHyperparams

CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

class GlobalConfig(BaseModel):
    # System Settings
    default_device: str = Field("cuda", description="Preferred device for training (cpu/cuda)")
    max_concurrent_runs: int = Field(1, description="Maximum number of parallel training sessions")
    storage_path: str = Field("./data", description="Root path for storing run data")
    
    # Paths & Integration
    roms_path: Optional[str] = Field(None, description="Default path to look for new ROMs to import")
    
    # Default Run Configuration
    default_algorithm: str = Field("PPO", description="Default algorithm selected in UI")
    default_hyperparams: RunHyperparams = Field(default_factory=RunHyperparams, description="Default hyperparameters used when creating a new run")

router = APIRouter()

def load_config() -> GlobalConfig:
    if not os.path.exists(CONFIG_FILE):
        return GlobalConfig()
    try:
        with open(CONFIG_FILE, "r") as f:
            return GlobalConfig(**json.load(f))
    except:
        return GlobalConfig()

def save_config(config: GlobalConfig):
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config.model_dump(), f, indent=2)

@router.get("/config", response_model=GlobalConfig)
async def get_config():
    return load_config()

@router.put("/config", response_model=GlobalConfig)
async def update_config(config: GlobalConfig):
    save_config(config)
    return config

@router.post("/config/reset", response_model=GlobalConfig)
async def reset_config():
    """Reset configuration to defaults."""
    config = GlobalConfig()
    save_config(config)
    return config
