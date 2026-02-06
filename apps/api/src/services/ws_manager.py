from fastapi import WebSocket


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
        if run_id in self.active_connections:
            # Iterate over a copy to allow modification during iteration if we needed to remove
            # But disconnect() modifies the list, so we must be careful.
            # safe_connections = self.active_connections[run_id][:]

            # Identify dead connections
            dead_connections = []

            for connection in self.active_connections[run_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error broadcasting to {run_id}: {e}")
                    dead_connections.append(connection)

            # Clean up
            for dead in dead_connections:
                self.disconnect(run_id, dead)

    async def broadcast_bytes(self, run_id: str, data: bytes):
        """Send binary data to all connected WebSocket clients for a session."""
        if run_id not in self.active_connections:
            return
        dead_connections = []
        for connection in self.active_connections[run_id]:
            try:
                await connection.send_bytes(data)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(run_id, dead)


manager = ConnectionManager()
