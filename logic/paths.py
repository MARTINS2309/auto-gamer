"""
Paths - Central location for all output directories.
"""

from pathlib import Path

# Base directory (where app.py lives)
BASE_DIR = Path(__file__).parent.parent

# Output directories
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
CONFIG_DIR = DATA_DIR / "config"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
MODELS_DIR = DATA_DIR / "models"


def ensure_dirs():
    """Create all output directories."""
    for d in [DATA_DIR, LOGS_DIR, CONFIG_DIR, SCREENSHOTS_DIR, MODELS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# Create dirs on import
ensure_dirs()
