import asyncio

from fastapi import WebSocket

# Timeout for individual WebSocket sends — drop message to slow clients
_SEND_TIMEOUT = 0.5  # seconds


class ConnectionManager:
    def __init__(self):
        # Map run_id -> List of WebSockets
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, run_id: str, websocket: WebSocket):
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)

    def disconnect(self, run_id: str, websocket: WebSocket):
        if run_id in self.active_connections:
            if websocket in self.active_connections[run_id]:
                self.active_connections[run_id].remove(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]

    async def broadcast(self, run_id: str, message: dict):
        if run_id not in self.active_connections:
            return

        dead_connections = []

        for connection in self.active_connections[run_id]:
            try:
                await asyncio.wait_for(
                    connection.send_json(message), timeout=_SEND_TIMEOUT
                )
            except asyncio.TimeoutError:
                print(f"[WS] Send timeout for {run_id}, dropping client")
                dead_connections.append(connection)
            except Exception as e:
                print(f"[WS] Error broadcasting to {run_id}: {e}")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(run_id, dead)

    async def broadcast_bytes(self, run_id: str, data: bytes):
        """Send binary data to all connected WebSocket clients for a session."""
        if run_id not in self.active_connections:
            return

        dead_connections = []
        for connection in self.active_connections[run_id]:
            try:
                await asyncio.wait_for(
                    connection.send_bytes(data), timeout=_SEND_TIMEOUT
                )
            except asyncio.TimeoutError:
                print(f"[WS] Binary send timeout for {run_id}, dropping client")
                dead_connections.append(connection)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(run_id, dead)


manager = ConnectionManager()
