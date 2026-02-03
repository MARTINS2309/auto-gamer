from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from ..services.play_manager import play_manager

router = APIRouter()


class PlaySessionResponse(BaseModel):
    """Response for starting a play session."""
    session_id: str
    rom_id: str
    state: Optional[str]
    message: str


class SessionInfoResponse(BaseModel):
    """Response with session info."""
    id: str
    rom_id: str
    state: Optional[str]
    started_at: str
    is_alive: bool


@router.post("/play/{rom_id}", response_model=PlaySessionResponse)
async def start_play_session(
    rom_id: str,
    state: Optional[str] = Query(None, description="Save state to load"),
    players: int = Query(1, ge=1, le=2, description="Number of players (1-2)")
):
    """
    Start an interactive play session for a ROM.

    This launches a pygame window where you can play the game manually
    using keyboard controls (arrow keys + X/Z).

    Args:
        rom_id: The ROM identifier (e.g., "SonicTheHedgehog-Genesis-v0")
        state: Optional save state name to load
        players: Number of players for multiplayer games (1-2)

    Returns:
        Session information including the session ID
    """
    try:
        session_id = play_manager.start_session(
            rom_id=rom_id,
            state=state,
            players=players
        )

        return PlaySessionResponse(
            session_id=session_id,
            rom_id=rom_id,
            state=state,
            message="Play session started. A game window should open shortly."
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/play/{session_id}")
async def stop_play_session(session_id: str):
    """
    Stop an active play session.

    Args:
        session_id: The session ID returned from start_play_session

    Returns:
        Confirmation message
    """
    if play_manager.stop_session(session_id):
        return {"message": "Play session stopped", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("/play/{session_id}", response_model=SessionInfoResponse)
async def get_play_session(session_id: str):
    """
    Get information about a play session.

    Args:
        session_id: The session ID

    Returns:
        Session information
    """
    info = play_manager.get_session(session_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionInfoResponse(**info)


@router.get("/play", response_model=list[SessionInfoResponse])
async def list_play_sessions():
    """
    List all active play sessions.

    Returns:
        List of active sessions
    """
    sessions = play_manager.list_sessions()
    return [SessionInfoResponse(**s) for s in sessions]
