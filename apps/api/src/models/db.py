from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Enum, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import os

from .schemas import RunStatus

# Ensure data directory exists
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'runs.db')}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# =============================================================================
# Thumbnail Cache Models
# =============================================================================

class ThumbnailMapping(Base):
    """Maps game IDs to their LibRetro thumbnail names."""
    __tablename__ = "thumbnail_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    system = Column(String, index=True, nullable=False)
    game_id = Column(String, index=True, nullable=False)
    libretro_name = Column(String, nullable=False)
    match_type = Column(String, nullable=False)  # 'exact', 'fuzzy', 'sha1'
    match_score = Column(Float, nullable=True)  # For fuzzy matches
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Composite unique constraint
    __table_args__ = (
        # Unique constraint on system + game_id
        {'sqlite_autoincrement': True},
    )


class ThumbnailFailure(Base):
    """Tracks games where no thumbnail could be found."""
    __tablename__ = "thumbnail_failures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    system = Column(String, index=True, nullable=False)
    game_id = Column(String, index=True, nullable=False)
    attempts = Column(Integer, default=1)
    last_attempt = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


# =============================================================================
# Game Metadata Cache (IGDB, ScreenScraper, etc.)
# =============================================================================

class GameMetadataCache(Base):
    """Cached game metadata from external APIs (IGDB, ScreenScraper, etc.)."""
    __tablename__ = "game_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identifiers
    game_id = Column(String, index=True, nullable=False)  # Our game ID (e.g., "SonicTheHedgehog-Genesis-v0")
    system = Column(String, index=True, nullable=False)
    rom_sha1 = Column(String, index=True, nullable=True)  # ROM checksum for ScreenScraper lookup

    # External IDs
    igdb_id = Column(Integer, nullable=True, index=True)
    screenscraper_id = Column(Integer, nullable=True)

    # Core Metadata
    name = Column(String, nullable=False)  # Canonical game name
    summary = Column(Text, nullable=True)
    storyline = Column(Text, nullable=True)

    # Ratings
    rating = Column(Float, nullable=True)  # 0-100
    rating_count = Column(Integer, nullable=True)

    # Classification (stored as JSON arrays)
    genres = Column(JSON, nullable=True)  # ["Action", "Platform"]
    themes = Column(JSON, nullable=True)  # ["Fantasy", "Sci-Fi"]
    game_modes = Column(JSON, nullable=True)  # ["Single player", "Multiplayer"]
    player_perspectives = Column(JSON, nullable=True)  # ["Side view", "Bird view"]
    platforms = Column(JSON, nullable=True)  # ["Sega Genesis", "Sega Mega Drive"]

    # Release Info
    release_date = Column(String, nullable=True)  # "1991-06-23"
    developer = Column(String, nullable=True)
    publisher = Column(String, nullable=True)

    # Media URLs (cached externally, URLs stored for reference)
    cover_url = Column(String, nullable=True)
    screenshot_urls = Column(JSON, nullable=True)  # List of URLs

    # Players / Duration (from ScreenScraper or manual)
    players = Column(String, nullable=True)  # "1-2" or "1"
    estimated_playtime = Column(Integer, nullable=True)  # Minutes

    # Cache metadata
    source = Column(String, nullable=False)  # "igdb", "screenscraper", "manual"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


# =============================================================================
# Run Model
# =============================================================================

class RunModel(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True, index=True)
    rom = Column(String, index=True)
    state = Column(String)
    algorithm = Column(String)
    hyperparams = Column(JSON)
    n_envs = Column(Integer)
    max_steps = Column(Integer)
    checkpoint_interval = Column(Integer)
    frame_capture_interval = Column(Integer)
    reward_shaping = Column(String)
    observation_type = Column(String)
    action_space = Column(String)
    
    status = Column(String, default=RunStatus.PENDING.value)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    pid = Column(Integer, nullable=True)
    error = Column(String, nullable=True)

    metrics = relationship("RunMetricModel", back_populates="run", cascade="all, delete-orphan")


class RunMetricModel(Base):
    __tablename__ = "run_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("runs.id"), index=True)
    step = Column(Integer, index=True)
    timestamp = Column(Float)
    
    # Core Metrics
    reward = Column(Float, nullable=True)
    avg_reward = Column(Float, nullable=True)
    best_reward = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)
    
    # Advanced / Algorithm specific
    loss = Column(Float, nullable=True)
    epsilon = Column(Float, nullable=True)
    
    # Full details blob
    details = Column(JSON, nullable=True)

    run = relationship("RunModel", back_populates="metrics")


Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
