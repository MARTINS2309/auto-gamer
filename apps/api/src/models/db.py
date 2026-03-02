import datetime
import os

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from .schemas import RunStatus

# Ensure data directory exists
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'runs.db')}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
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
        {"sqlite_autoincrement": True},
    )


class ThumbnailFailure(Base):
    """Tracks games where no thumbnail could be found."""

    __tablename__ = "thumbnail_failures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    system = Column(String, index=True, nullable=False)
    game_id = Column(String, index=True, nullable=False)
    attempts = Column(Integer, default=1)
    last_attempt = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = ({"sqlite_autoincrement": True},)


# =============================================================================
# ROM Model (User's local ROM files)
# =============================================================================


class RomModel(Base):
    """
    User's local ROM files.
    Identified by SHA1 hash, correlated to connectors and metadata via hash.
    """

    __tablename__ = "roms"

    # === Primary Key (hash-based ID) ===
    id = Column(String, primary_key=True, index=True)  # Short hash: "a1b2c3d4-Gba"

    # === File Info ===
    sha1_hash = Column(String(40), index=True, nullable=True)  # Full 40-char SHA1
    system = Column(String, index=True, nullable=False)  # e.g., "Gba", "Snes"
    file_path = Column(String, nullable=True)  # Path to user's ROM file
    file_name = Column(String, nullable=True)  # Original filename
    file_size = Column(Integer, nullable=True)  # File size in bytes
    display_name = Column(String, nullable=False)  # Cleaned name for display

    # === Relationships (populated by sync) ===
    connector_id = Column(String, ForeignKey("connectors.id"), nullable=True, index=True)
    metadata_id = Column(Integer, ForeignKey("game_metadata.id"), nullable=True, index=True)

    # === Timestamps ===
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    # === Relationships ===
    connector = relationship("ConnectorModel", back_populates="roms")
    game_metadata = relationship("GameMetadataModel", back_populates="roms")

    __table_args__ = (
        Index("ix_roms_sha1_system", "sha1_hash", "system"),
    )


# =============================================================================
# Connector Model (stable-retro connectors)
# =============================================================================


class ConnectorModel(Base):
    """
    stable-retro connectors for training AI.
    Contains game states and integration info.
    """

    __tablename__ = "connectors"

    # === Primary Key (stable-retro game ID) ===
    id = Column(String, primary_key=True, index=True)  # e.g., "PokemonFireRed-Gba-v0"

    # === Connector Info ===
    system = Column(String, index=True, nullable=False)  # e.g., "Gba"
    display_name = Column(String, nullable=False)  # Cleaned name from game ID
    sha1_hash = Column(String(40), index=True, nullable=True)  # From rom.sha file

    # === State/Training Info ===
    states = Column(JSON, default=list)  # Available save states: ["start", "gym1", ...]
    has_rom = Column(Boolean, default=False)  # ROM file exists in stable-retro data dir

    # === Metadata Link ===
    metadata_id = Column(Integer, ForeignKey("game_metadata.id"), nullable=True, index=True)

    # === Timestamps ===
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    # === Relationships ===
    roms = relationship("RomModel", back_populates="connector")
    game_metadata = relationship("GameMetadataModel", back_populates="connectors")

    __table_args__ = (
        Index("ix_connectors_sha1_system", "sha1_hash", "system"),
    )


# =============================================================================
# Game Metadata Model (IGDB, ScreenScraper, etc.)
# =============================================================================


class GameMetadataModel(Base):
    """
    Game metadata from external APIs (IGDB, ScreenScraper, etc.).
    Linked to ROMs and Connectors via hash or direct relationship.
    """

    __tablename__ = "game_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # === Identifiers ===
    game_id = Column(String, index=True, nullable=True)  # Legacy: connector/game ID for old cache lookups
    system = Column(String, index=True, nullable=False)  # e.g., "Gba"
    sha1_hash = Column(String(40), index=True, nullable=True)  # For hash-based lookup
    rom_sha1 = Column(String(40), index=True, nullable=True)  # Legacy: for old cache lookups

    # === External IDs ===
    igdb_id = Column(Integer, nullable=True, index=True)
    screenscraper_id = Column(Integer, nullable=True)

    # === Core Metadata ===
    name = Column(String, nullable=False)  # Canonical game name
    summary = Column(Text, nullable=True)
    storyline = Column(Text, nullable=True)

    # === Ratings ===
    rating = Column(Float, nullable=True)  # 0-100
    rating_count = Column(Integer, nullable=True)

    # === Classification (stored as JSON arrays) ===
    genres = Column(JSON, nullable=True)  # ["Action", "Platform"]
    themes = Column(JSON, nullable=True)  # ["Fantasy", "Sci-Fi"]
    game_modes = Column(JSON, nullable=True)  # ["Single player", "Multiplayer"]
    player_perspectives = Column(JSON, nullable=True)  # ["Side view", "Bird view"]
    platforms = Column(JSON, nullable=True)  # ["Sega Genesis", "Sega Mega Drive"]

    # === Release Info ===
    release_date = Column(String, nullable=True)  # "1991-06-23"
    developer = Column(String, nullable=True)
    publisher = Column(String, nullable=True)

    # === Media URLs ===
    cover_url = Column(String, nullable=True)
    screenshot_urls = Column(JSON, nullable=True)  # List of URLs

    # === Players / Duration ===
    players = Column(String, nullable=True)  # "1-2" or "1"
    estimated_playtime = Column(Integer, nullable=True)  # Minutes

    # === Thumbnail (cached from LibRetro/IGDB) ===
    libretro_name = Column(String, nullable=True)  # LibRetro thumbnail name
    thumbnail_match_type = Column(String, nullable=True)  # "exact", "fuzzy", "manual", "igdb_cover"
    thumbnail_match_score = Column(Float, nullable=True)  # 0.0-1.0 for fuzzy
    thumbnail_path = Column(String, nullable=True)  # Local path: "thumbnail_cache/abc123.png"
    thumbnail_status = Column(String, default="pending")  # pending, synced, failed

    # === Sync Status ===
    sync_status = Column(String, default="pending")  # pending, syncing, synced, failed, manual
    sync_error = Column(String, nullable=True)
    source = Column(String, default="igdb")  # "igdb", "screenscraper", "manual"

    # === Timestamps ===
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    # === Relationships ===
    roms = relationship("RomModel", back_populates="game_metadata")
    connectors = relationship("ConnectorModel", back_populates="game_metadata")

    __table_args__ = (
        Index("ix_metadata_sha1_system", "sha1_hash", "system"),
        {"sqlite_autoincrement": True},
    )


# =============================================================================
# Agent Model
# =============================================================================


class AgentModel(Base):
    """Persistent named agent that accumulates learning across multiple training runs."""

    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)  # UUID
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    algorithm = Column(String, nullable=False)  # Immutable after creation
    game_id = Column(String, nullable=False)  # ROM id this agent is trained on
    hyperparams = Column(JSON, nullable=True)  # Default hyperparams for new runs
    observation_type = Column(String, default="image")  # Immutable
    action_space = Column(String, default="filtered")  # Immutable

    # Aggregate stats (denormalized for quick display)
    total_steps = Column(Integer, default=0)
    total_runs = Column(Integer, default=0)
    best_reward = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    runs = relationship("RunModel", back_populates="agent", foreign_keys="[RunModel.agent_id]")


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
    frame_fps = Column(Integer)
    reward_shaping = Column(String)
    observation_type = Column(String)
    action_space = Column(String)

    # Agent relationships
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True, index=True)
    opponent_agent_id = Column(String, ForeignKey("agents.id"), nullable=True, index=True)

    status = Column(String, default=RunStatus.PENDING.value)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    pid = Column(Integer, nullable=True)
    error = Column(String, nullable=True)

    metrics = relationship("RunMetricModel", back_populates="run", cascade="all, delete-orphan")
    agent = relationship("AgentModel", back_populates="runs", foreign_keys=[agent_id])
    opponent_agent = relationship("AgentModel", foreign_keys=[opponent_agent_id])


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


# Legacy alias for backwards compatibility with metadata.py router
GameMetadataCache = GameMetadataModel

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
