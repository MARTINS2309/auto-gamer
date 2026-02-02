from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
