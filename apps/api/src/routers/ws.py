import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.play_manager import play_manager
from ..services.run_manager import manager as run_manager
from ..services.ws_manager import manager as ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/runs/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await ws_manager.connect(run_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            if action == "stop":
                await asyncio.to_thread(run_manager.stop_run, run_id)
            elif action == "set_frame_freq":
                freq = int(data.get("value", 30))
                run_manager.set_frame_freq(run_id, freq)
                await websocket.send_json({"type": "frame_freq", "value": freq})
            elif action == "set_focused_env":
                env_index = int(data.get("value", -1))
                run_manager.set_focused_env(run_id, env_index)
                await websocket.send_json({"type": "focused_env", "value": env_index})
    except WebSocketDisconnect:
        ws_manager.disconnect(run_id, websocket)
    except Exception:
        ws_manager.disconnect(run_id, websocket)


@router.websocket("/ws/play/frames/{session_id}")
async def play_frames_websocket(websocket: WebSocket, session_id: str):
    """Stream play session frames to the browser."""
    session = play_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    await ws_manager.connect(session_id, websocket)
    try:
        while True:
            # Keep-alive: just receive and ignore (frames sent via broadcast)
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id, websocket)
    except Exception:
        ws_manager.disconnect(session_id, websocket)


@router.websocket("/ws/play/gamepad/{session_id}")
async def gamepad_websocket(websocket: WebSocket, session_id: str):
    """Receive browser input state and pipe it to the subprocess stdin."""
    session = play_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    logger.info(f"[Input WS] Connected for session {session_id}")

    msg_count = 0
    try:
        while True:
            data = await websocket.receive_json()
            buttons = data if isinstance(data, list) else data.get("buttons", [])
            play_manager.send_input(session_id, buttons)
            msg_count += 1
            if msg_count <= 5 or (buttons and msg_count <= 20):
                logger.info(f"[Input WS] msg#{msg_count}: {buttons}")
    except WebSocketDisconnect:
        logger.info(f"[Input WS] Disconnected (received {msg_count} msgs)")
    except Exception as e:
        logger.warning(f"[Input WS] Error for session {session_id}: {e}")
