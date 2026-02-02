from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import os

from ..models.db import DATA_DIR

CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

class GlobalConfig(BaseModel):
    default_algorithm: str = "PPO"
    default_device: str = "cuda"
    storage_path: str = "./data"
    
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
