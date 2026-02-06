"""
Connector Builder router — REST endpoints for building game connectors.

All endpoints use `def` (sync) because they access the thread-locked RetroEnv.
"""

import base64
import io
import logging

from fastapi import APIRouter, HTTPException
from PIL import Image
from pydantic import BaseModel

from ..services.connector_builder import builder_manager

logger = logging.getLogger(__name__)
router = APIRouter()


# ------------------------------------------------------------------
# Request / Response models
# ------------------------------------------------------------------


class StartRequest(BaseModel):
    rom_id: str


class StepRequest(BaseModel):
    frames: int = 1
    action: list[int] | None = None


class SearchRequest(BaseModel):
    name: str
    value: int


class DeltaSearchRequest(BaseModel):
    name: str
    op: str  # "equal", "less-than", "greater-than", "not-equal"
    ref: int


class WatchRequest(BaseModel):
    name: str
    address: int
    type: str  # e.g. "|u1", ">u2", "<i4"


class RewardRequest(BaseModel):
    variable: str
    operation: str  # "delta", "threshold", "equals"
    reference: float = 0
    multiplier: float = 1.0


class DoneConditionRequest(BaseModel):
    variable: str
    operation: str  # "equal", "less-than", "greater-than"
    reference: float


class SaveStateRequest(BaseModel):
    name: str


class LoadStateRequest(BaseModel):
    name: str


class ExportRequest(BaseModel):
    connector_name: str | None = None


# ------------------------------------------------------------------
# Session lifecycle
# ------------------------------------------------------------------


@router.post("/builder/start")
def start_session(req: StartRequest):
    """Start a new connector builder session for a ROM."""
    try:
        result = builder_manager.start(req.rom_id)
        return result
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/builder/close")
def close_session():
    """Close the active builder session."""
    builder_manager.close()
    return {"message": "Session closed"}


@router.get("/builder/status")
def get_status():
    """Get info about the active builder session."""
    try:
        session = builder_manager.require_session()
        return session.get_status()
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ------------------------------------------------------------------
# Emulator control
# ------------------------------------------------------------------


@router.post("/builder/step")
def step_emulator(req: StepRequest):
    """Step the emulator N frames with optional action."""
    try:
        session = builder_manager.require_session()
        return session.step(action=req.action, n=req.frames)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/builder/screen")
def get_screen():
    """Get current frame as base64 JPEG."""
    try:
        session = builder_manager.require_session()
        rgb = session.get_screen()

        # Encode as JPEG
        img = Image.fromarray(rgb)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        return {"image": b64, "width": rgb.shape[1], "height": rgb.shape[0]}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------------------------------------------------------------
# Memory search
# ------------------------------------------------------------------


@router.post("/builder/search")
def search_memory(req: SearchRequest):
    """Start or refine an exact-value search."""
    try:
        session = builder_manager.require_session()
        return session.search(req.name, req.value)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/builder/delta-search")
def delta_search_memory(req: DeltaSearchRequest):
    """Delta search (increased/decreased/unchanged)."""
    try:
        session = builder_manager.require_session()
        return session.delta_search(req.name, req.op, req.ref)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/builder/searches/{name}")
def get_search_results(name: str):
    """Get search results for a named search."""
    try:
        session = builder_manager.require_session()
        return session.get_search_results(name)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/builder/searches/{name}")
def remove_search(name: str):
    """Remove a named search."""
    try:
        session = builder_manager.require_session()
        session.remove_search(name)
        return {"message": f"Search '{name}' removed"}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------------------------------------------------------------
# Watches
# ------------------------------------------------------------------


@router.post("/builder/watches")
def add_watch(req: WatchRequest):
    """Add a named memory watch."""
    try:
        session = builder_manager.require_session()
        session.add_watch(req.name, req.address, req.type)
        return {"message": f"Watch '{req.name}' added", "name": req.name}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/builder/watches")
def read_watches():
    """Read all watch values."""
    try:
        session = builder_manager.require_session()
        return session.read_watches()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/builder/watches/{name}")
def remove_watch(name: str):
    """Remove a named watch."""
    try:
        session = builder_manager.require_session()
        session.remove_watch(name)
        return {"message": f"Watch '{name}' removed"}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------------------------------------------------------------
# Rewards & done conditions
# ------------------------------------------------------------------


@router.post("/builder/rewards")
def add_reward(req: RewardRequest):
    """Add a reward signal."""
    try:
        session = builder_manager.require_session()
        idx = session.add_reward(req.variable, req.operation, req.reference, req.multiplier)
        return {"index": idx, "message": "Reward added"}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/builder/done-conditions")
def add_done_condition(req: DoneConditionRequest):
    """Add a done condition."""
    try:
        session = builder_manager.require_session()
        idx = session.add_done_condition(req.variable, req.operation, req.reference)
        return {"index": idx, "message": "Done condition added"}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------------------------------------------------------------
# Save states
# ------------------------------------------------------------------


@router.post("/builder/states/save")
def save_state(req: SaveStateRequest):
    """Save emulator state."""
    try:
        session = builder_manager.require_session()
        return session.save_state(req.name)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/builder/states/load")
def load_state(req: LoadStateRequest):
    """Load emulator state."""
    try:
        session = builder_manager.require_session()
        return session.load_state(req.name)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/builder/states")
def list_states():
    """List saved states."""
    try:
        session = builder_manager.require_session()
        return session.list_states()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------------------------------------------------------------
# Export
# ------------------------------------------------------------------


@router.post("/builder/export")
def export_connector(req: ExportRequest):
    """Export connector + register in DB."""
    try:
        session = builder_manager.require_session()
        result = session.export(connector_name=req.connector_name)
        return result
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
