import json
import os

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..models.db import DATA_DIR
from ..models.schemas import Algorithm, Device, RunHyperparams

CONFIG_FILE = os.path.join(DATA_DIR, "config.json")


# =============================================================================
# Input Configuration
# =============================================================================


class KeyboardMapping(BaseModel):
    """Keyboard key mappings for a system. Values are pygame key names."""

    up: str = "UP"
    down: str = "DOWN"
    left: str = "LEFT"
    right: str = "RIGHT"
    a: str = "x"
    b: str | None = "z"  # Optional for Atari2600
    x: str | None = "s"
    y: str | None = "a"
    l: str | None = "q"
    r: str | None = "w"
    start: str = "RETURN"
    select: str | None = "RSHIFT"  # Optional for Genesis
    # Extra buttons for 6-button controllers (Genesis)
    c: str | None = "c"
    z_btn: str | None = "d"  # 'z' is taken by B button


# Default keyboard layouts per system
DEFAULT_KEYBOARD_MAPPINGS: dict[str, KeyboardMapping] = {
    # NES-style: A, B, Start, Select
    "Nes": KeyboardMapping(
        up="UP",
        down="DOWN",
        left="LEFT",
        right="RIGHT",
        a="x",
        b="z",
        start="RETURN",
        select="RSHIFT",
        x=None,
        y=None,
        l=None,
        r=None,
    ),
    # SNES-style: A, B, X, Y, L, R
    "Snes": KeyboardMapping(
        up="UP",
        down="DOWN",
        left="LEFT",
        right="RIGHT",
        a="x",
        b="z",
        x="s",
        y="a",
        l="q",
        r="w",
        start="RETURN",
        select="RSHIFT",
    ),
    # Genesis 6-button: A, B, C, X, Y, Z
    "Genesis": KeyboardMapping(
        up="UP",
        down="DOWN",
        left="LEFT",
        right="RIGHT",
        a="a",
        b="s",
        c="d",
        x="z",
        y="x",
        z_btn="c",
        start="RETURN",
        select=None,
    ),
    # GBA: A, B, L, R
    "Gba": KeyboardMapping(
        up="UP",
        down="DOWN",
        left="LEFT",
        right="RIGHT",
        a="x",
        b="z",
        l="q",
        r="w",
        start="RETURN",
        select="RSHIFT",
        x=None,
        y=None,
    ),
    # Game Boy: A, B
    "Gb": KeyboardMapping(
        up="UP",
        down="DOWN",
        left="LEFT",
        right="RIGHT",
        a="x",
        b="z",
        start="RETURN",
        select="RSHIFT",
        x=None,
        y=None,
        l=None,
        r=None,
    ),
    # Atari 2600: Just one button
    "Atari2600": KeyboardMapping(
        up="UP",
        down="DOWN",
        left="LEFT",
        right="RIGHT",
        a="x",
        b=None,
        start="RETURN",
        select="RSHIFT",
        x=None,
        y=None,
        l=None,
        r=None,
    ),
    # PCEngine/TurboGrafx
    "PCEngine": KeyboardMapping(
        up="UP",
        down="DOWN",
        left="LEFT",
        right="RIGHT",
        a="x",
        b="z",
        start="RETURN",
        select="RSHIFT",
        x=None,
        y=None,
        l=None,
        r=None,
    ),
}


class ControllerConfig(BaseModel):
    """Controller/gamepad configuration."""

    enabled: bool = Field(True, description="Enable controller input")
    deadzone: float = Field(0.15, ge=0.0, le=0.5, description="Analog stick deadzone")
    # Button mappings (XInput style, 0-indexed)
    # These map controller buttons to retro actions
    a_button: int = Field(0, description="Controller button for A (XInput: A=0)")
    b_button: int = Field(1, description="Controller button for B (XInput: B=1)")
    x_button: int = Field(2, description="Controller button for X (XInput: X=2)")
    y_button: int = Field(3, description="Controller button for Y (XInput: Y=3)")
    l_button: int = Field(4, description="Controller button for L (XInput: LB=4)")
    r_button: int = Field(5, description="Controller button for R (XInput: RB=5)")
    start_button: int = Field(7, description="Controller button for Start (XInput: Start=7)")
    select_button: int = Field(6, description="Controller button for Select (XInput: Back=6)")
    # Extra buttons for 6-button controllers (Genesis)
    c_button: int = Field(8, description="Controller button for C (Genesis)")
    z_button: int = Field(9, description="Controller button for Z (Genesis)")


class InputConfig(BaseModel):
    """Complete input configuration."""

    keyboard_mappings: dict[str, KeyboardMapping] = Field(
        default_factory=lambda: DEFAULT_KEYBOARD_MAPPINGS.copy(),
        description="Keyboard mappings per system",
    )
    controller: ControllerConfig = Field(
        default_factory=ControllerConfig, description="Controller/gamepad settings"
    )


# =============================================================================
# Main Config
# =============================================================================


class GlobalConfig(BaseModel):
    # System Settings
    default_device: Device = Field(
        Device.AUTO, description="Preferred device for training (auto/cuda/cpu)"
    )
    max_concurrent_runs: int = Field(
        1, ge=1, le=16, description="Maximum number of parallel training sessions"
    )
    storage_path: str = Field("./data", min_length=1, description="Root path for storing run data")

    # Paths & Integration
    roms_path: str | None = Field(None, description="Default path to look for new ROMs to import")
    recording_path: str | None = Field(None, description="Path to save recordings (BK2 movies)")

    # Default Run Configuration
    default_algorithm: Algorithm = Field(
        Algorithm.PPO, description="Default algorithm selected in UI"
    )
    default_hyperparams: RunHyperparams = Field(
        default_factory=RunHyperparams,
        description="Default hyperparameters used when creating a new run",
    )

    # Input Configuration
    input: InputConfig = Field(
        default_factory=InputConfig, description="Keyboard and controller input settings"
    )

    # External API Credentials
    igdb_client_id: str | None = Field(None, description="IGDB/Twitch API Client ID")
    igdb_client_secret: str | None = Field(None, description="IGDB/Twitch API Client Secret")
    screenscraper_dev_id: str | None = Field(None, description="ScreenScraper Developer ID")
    screenscraper_dev_password: str | None = Field(
        None, description="ScreenScraper Developer Password"
    )
    screenscraper_username: str | None = Field(None, description="ScreenScraper Username")
    screenscraper_password: str | None = Field(None, description="ScreenScraper User Password")


router = APIRouter()


def load_config() -> GlobalConfig:
    if not os.path.exists(CONFIG_FILE):
        return GlobalConfig()
    try:
        with open(CONFIG_FILE) as f:
            return GlobalConfig(**json.load(f))
    except Exception:
        return GlobalConfig()


def save_config(config: GlobalConfig):
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config.model_dump(), f, indent=2)


@router.get("/config", response_model=GlobalConfig)
def get_config():
    return load_config()


@router.put("/config", response_model=GlobalConfig)
def update_config(config: GlobalConfig):
    save_config(config)
    return config


@router.post("/config/reset", response_model=GlobalConfig)
def reset_config():
    """Reset configuration to defaults."""
    config = GlobalConfig()
    save_config(config)
    return config


# =============================================================================
# Input Configuration Endpoints
# =============================================================================


@router.get("/config/input", response_model=InputConfig)
def get_input_config():
    """Get input configuration."""
    config = load_config()
    return config.input


@router.put("/config/input", response_model=InputConfig)
def update_input_config(input_config: InputConfig):
    """Update input configuration."""
    config = load_config()
    config.input = input_config
    save_config(config)
    return config.input


@router.get("/config/input/keyboard/{system}", response_model=KeyboardMapping)
def get_keyboard_mapping(system: str):
    """Get keyboard mapping for a specific system."""
    config = load_config()

    # Check if system has a custom mapping
    if system in config.input.keyboard_mappings:
        return config.input.keyboard_mappings[system]

    # Fall back to defaults
    if system in DEFAULT_KEYBOARD_MAPPINGS:
        return DEFAULT_KEYBOARD_MAPPINGS[system]

    # Generic fallback (SNES-style as most complete)
    return DEFAULT_KEYBOARD_MAPPINGS.get("Snes", KeyboardMapping())


@router.put("/config/input/keyboard/{system}", response_model=KeyboardMapping)
def update_keyboard_mapping(system: str, mapping: KeyboardMapping):
    """Update keyboard mapping for a specific system."""
    config = load_config()
    config.input.keyboard_mappings[system] = mapping
    save_config(config)
    return mapping


@router.post("/config/input/keyboard/{system}/reset", response_model=KeyboardMapping)
def reset_keyboard_mapping(system: str):
    """Reset keyboard mapping for a system to defaults."""
    config = load_config()

    if system in DEFAULT_KEYBOARD_MAPPINGS:
        config.input.keyboard_mappings[system] = DEFAULT_KEYBOARD_MAPPINGS[system]
    elif system in config.input.keyboard_mappings:
        del config.input.keyboard_mappings[system]

    save_config(config)
    return get_keyboard_mapping(system)


@router.get("/config/input/systems")
def get_supported_systems():
    """Get list of systems with default keyboard mappings."""
    return {
        "systems": list(DEFAULT_KEYBOARD_MAPPINGS.keys()),
        "buttons": {
            "Nes": ["up", "down", "left", "right", "a", "b", "start", "select"],
            "Snes": [
                "up",
                "down",
                "left",
                "right",
                "a",
                "b",
                "x",
                "y",
                "l",
                "r",
                "start",
                "select",
            ],
            "Genesis": ["up", "down", "left", "right", "a", "b", "c", "x", "y", "z_btn", "start"],
            "Gba": ["up", "down", "left", "right", "a", "b", "l", "r", "start", "select"],
            "Gb": ["up", "down", "left", "right", "a", "b", "start", "select"],
            "Atari2600": ["up", "down", "left", "right", "a", "start", "select"],
            "PCEngine": ["up", "down", "left", "right", "a", "b", "start", "select"],
        },
    }
