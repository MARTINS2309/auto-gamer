from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.ws_manager import manager as ws_manager
from ..services.run_manager import manager as run_manager

router = APIRouter()

@router.websocket("/ws/runs/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await ws_manager.connect(run_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Handle client commands if any
            # e.g., {"action": "stop"}
            if data.get("action") == "stop":
                run_manager.stop_run(run_id)
    except WebSocketDisconnect:
        ws_manager.disconnect(run_id, websocket)
    except Exception as e:
        # Handle malformed json or other errors
        ws_manager.disconnect(run_id, websocket)
