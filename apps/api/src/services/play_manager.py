import subprocess
import threading
import uuid
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PlaySession:
    """Represents an active play session."""
    id: str
    rom_id: str
    state: Optional[str]
    process: subprocess.Popen
    started_at: datetime


class PlayManager:
    """Manages interactive play sessions using stable-retro."""

    def __init__(self, max_sessions: int = 2):
        self.sessions: Dict[str, PlaySession] = {}
        self.max_sessions = max_sessions
        self.lock = threading.Lock()

    def start_session(
        self,
        rom_id: str,
        state: Optional[str] = None,
        players: int = 1
    ) -> str:
        """
        Start a new interactive play session.

        Args:
            rom_id: The ROM/game ID (e.g., "SonicTheHedgehog-Genesis-v0")
            state: Optional save state to load
            players: Number of players (1-2)

        Returns:
            Session ID

        Raises:
            Exception: If max sessions reached or launch fails
        """
        with self.lock:
            # Clean up any dead sessions first
            self._cleanup_dead_sessions()

            # Check max sessions
            if len(self.sessions) >= self.max_sessions:
                raise Exception(f"Maximum concurrent play sessions ({self.max_sessions}) reached")

            session_id = str(uuid.uuid4())

            # Build command
            cmd = [
                "python", "-m", "stable_retro.examples.interactive",
                "--game", rom_id,
            ]

            if state:
                cmd.extend(["--state", state])

            if players > 1:
                cmd.extend(["--players", str(players)])

            try:
                # Launch the interactive player
                # Note: This opens a pygame window for the user
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                session = PlaySession(
                    id=session_id,
                    rom_id=rom_id,
                    state=state,
                    process=process,
                    started_at=datetime.utcnow()
                )

                self.sessions[session_id] = session

                # Start a thread to monitor the process
                monitor = threading.Thread(
                    target=self._monitor_session,
                    args=(session_id,),
                    daemon=True
                )
                monitor.start()

                return session_id

            except Exception as e:
                raise Exception(f"Failed to start play session: {e}")

    def stop_session(self, session_id: str) -> bool:
        """
        Stop an active play session.

        Args:
            session_id: The session ID to stop

        Returns:
            True if session was stopped, False if not found
        """
        with self.lock:
            if session_id not in self.sessions:
                return False

            session = self.sessions[session_id]

            if session.process.poll() is None:
                # Process is still running
                session.process.terminate()
                try:
                    session.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    session.process.kill()

            del self.sessions[session_id]
            return True

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get info about a session."""
        with self.lock:
            if session_id not in self.sessions:
                return None

            session = self.sessions[session_id]
            is_alive = session.process.poll() is None

            return {
                "id": session.id,
                "rom_id": session.rom_id,
                "state": session.state,
                "started_at": session.started_at.isoformat(),
                "is_alive": is_alive,
            }

    def list_sessions(self) -> list:
        """List all active sessions."""
        with self.lock:
            self._cleanup_dead_sessions()
            return [
                {
                    "id": s.id,
                    "rom_id": s.rom_id,
                    "state": s.state,
                    "started_at": s.started_at.isoformat(),
                    "is_alive": s.process.poll() is None,
                }
                for s in self.sessions.values()
            ]

    def _monitor_session(self, session_id: str):
        """Monitor a session and clean up when it exits."""
        while True:
            with self.lock:
                if session_id not in self.sessions:
                    break

                session = self.sessions[session_id]
                if session.process.poll() is not None:
                    # Process has exited
                    del self.sessions[session_id]
                    print(f"[PlayManager] Session {session_id} ended")
                    break

            # Check every second
            import time
            time.sleep(1)

    def _cleanup_dead_sessions(self):
        """Remove any sessions whose processes have exited."""
        dead_ids = [
            sid for sid, session in self.sessions.items()
            if session.process.poll() is not None
        ]
        for sid in dead_ids:
            del self.sessions[sid]


# Global instance
play_manager = PlayManager()
