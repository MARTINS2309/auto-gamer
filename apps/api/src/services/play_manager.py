import asyncio
import json
import logging
import os
import struct
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime

from ..models.db import RomModel, SessionLocal
from ..services.ws_manager import manager as ws_manager

logger = logging.getLogger(__name__)


class NeedsConnectorError(Exception):
    """Raised when a game requires a connector to be built before playing."""

    pass


@dataclass
class PlaySession:
    """Represents an active play session."""

    id: str
    rom_id: str
    state: str | None
    process: subprocess.Popen
    started_at: datetime
    gamepad_file: str = ""


class PlayManager:
    """Manages interactive play sessions using stable-retro."""

    def __init__(self, max_sessions: int = 2):
        self.sessions: dict[str, PlaySession] = {}
        self.max_sessions = max_sessions
        self.lock = threading.Lock()
        self.loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def start_session(
        self,
        rom_id: str,
        state: str | None = None,
        players: int = 1,
        recording_path: str | None = None,
        keyboard_mapping: dict | None = None,
        controller_config: dict | None = None,
    ) -> str:
        """
        Start a new interactive play session.
        Only works for games with stable-retro connectors.

        Args:
            rom_id: The ROM/game ID (e.g., "SonicTheHedgehog-Genesis-v0" OR "guid-from-db")
            state: Optional save state to load
            players: Number of players (1-2)
            recording_path: Optional path to save recordings

        Returns:
            Session ID

        Raises:
            NeedsConnectorError: If game has no stable-retro connector
            Exception: If max sessions reached or launch fails
        """
        with self.lock:
            # Clean up any dead sessions first
            self._cleanup_dead_sessions()

            # Check max sessions
            if len(self.sessions) >= self.max_sessions:
                raise Exception(f"Maximum concurrent play sessions ({self.max_sessions}) reached")

            session_id = str(uuid.uuid4())
            target_game = rom_id

            # Resolve rom_id to a stable-retro game name
            if not self._is_retro_game(rom_id):
                # Look up in DB
                db = SessionLocal()
                try:
                    rom = db.query(RomModel).filter(
                        (RomModel.id == rom_id) | (RomModel.connector_id == rom_id)
                    ).first()

                    if rom and rom.connector_id and self._is_retro_game(rom.connector_id):
                        target_game = rom.connector_id
                    else:
                        raise NeedsConnectorError(
                            "This game requires a connector for play. "
                            "Use the Connector Builder to create one."
                        )
                finally:
                    db.close()

            # Build command — use same Python interpreter as the API server
            cmd = [
                sys.executable,
                "-m",
                "src.scripts.interactive_custom",
                "--game",
                target_game,
            ]

            if state:
                # If custom integration, verify state exists or ignore?
                # For custom, usually only 'Start' is valid unless we gen metadata
                cmd.extend(["--state", state])

            if players > 1:
                cmd.extend(["--players", str(players)])

            if recording_path:
                os.makedirs(recording_path, exist_ok=True)
                cmd.extend(["--record", recording_path])

            logger.info(f"[PlayManager] Starting play session for {target_game}")
            logger.info(f"[PlayManager] Command: {' '.join(cmd)}")

            # Create gamepad file for browser-based controller forwarding
            gamepad_file = os.path.join(tempfile.gettempdir(), f"autogamer-gamepad-{session_id}.json")

            # Pass input config to subprocess via environment variables
            env = os.environ.copy()
            env["AUTOGAMER_GAMEPAD_FILE"] = gamepad_file
            env["AUTOGAMER_STREAM_FRAMES"] = "1"
            if keyboard_mapping:
                env["AUTOGAMER_KEYBINDS"] = json.dumps(keyboard_mapping)
                logger.info(f"[PlayManager] Custom keybinds: {keyboard_mapping}")
            if controller_config:
                env["AUTOGAMER_CONTROLLER"] = json.dumps(controller_config)
                logger.info(f"[PlayManager] Controller config: {controller_config}")

            try:
                # Launch the interactive player (headless, frames on stdout, input on stdin)
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                )

                logger.info(f"[PlayManager] Process started with PID: {process.pid}")

                # Give it a moment to fail fast
                time.sleep(0.5)

                # Check if process died immediately
                exit_code = process.poll()
                if exit_code is not None:
                    stdout, stderr = process.communicate()
                    stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
                    stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""

                    logger.error(f"[PlayManager] Process exited immediately with code {exit_code}")
                    logger.error(f"[PlayManager] STDOUT: {stdout_str[:2000]}")
                    logger.error(f"[PlayManager] STDERR: {stderr_str[:2000]}")

                    raise Exception(
                        f"Game failed to launch (exit code {exit_code}): {stderr_str[:500]}"
                    )

                session = PlaySession(
                    id=session_id,
                    rom_id=rom_id,
                    state=state,
                    process=process,
                    started_at=datetime.utcnow(),
                    gamepad_file=gamepad_file,
                )

                self.sessions[session_id] = session
                logger.info(f"[PlayManager] Session {session_id} created successfully")

                # Start stdout reader (frames) and stderr reader (logs)
                threading.Thread(
                    target=self._stdout_reader, args=(session_id,), daemon=True
                ).start()
                threading.Thread(
                    target=self._stderr_reader, args=(session_id, process), daemon=True
                ).start()

                return session_id

            except Exception as e:
                logger.error(f"[PlayManager] Failed to start session: {e}")
                raise Exception(f"Failed to start play session: {e}")

    def _is_retro_game(self, game_id: str) -> bool:
        """Check if game_id is a known stable-retro game."""
        try:
            import stable_retro as retro
            return game_id in retro.data.list_games()
        except ImportError:
            return False

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

            self._remove_gamepad_file(session)
            del self.sessions[session_id]
            return True

    def get_session(self, session_id: str) -> dict | None:
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

    def send_input(self, session_id: str, buttons: list[str]) -> None:
        """Write input state to the subprocess stdin pipe. Lock-free for low latency."""
        session = self.sessions.get(session_id)
        if not session:
            return
        stdin = session.process.stdin
        if not stdin:
            return
        try:
            stdin.write(json.dumps(buttons).encode() + b"\n")
            stdin.flush()
        except (BrokenPipeError, OSError):
            pass

    @staticmethod
    def _read_exact(pipe, n: int) -> bytes:
        """Read exactly n bytes from a pipe, or raise EOFError."""
        data = b""
        while len(data) < n:
            chunk = pipe.read(n - len(data))
            if not chunk:
                raise EOFError("pipe closed")
            data += chunk
        return data

    def _stdout_reader(self, session_id: str):
        """Read raw RGB frames from subprocess stdout and broadcast via WS.

        Binary protocol: [u16 LE width][u16 LE height][width*height*3 bytes RGB]
        Each frame is forwarded as-is (with the 4-byte header) over binary WebSocket.
        """
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                return
            pipe = session.process.stdout

        frame_count = 0
        try:
            while True:
                # Read 4-byte header
                header = self._read_exact(pipe, 4)
                w, h = struct.unpack("<HH", header)
                pixel_bytes = w * h * 3

                # Read raw RGB pixel data
                pixels = self._read_exact(pipe, pixel_bytes)

                frame_count += 1
                if self.loop:
                    # Send header + pixels as one binary WS message
                    asyncio.run_coroutine_threadsafe(
                        ws_manager.broadcast_bytes(session_id, header + pixels),
                        self.loop,
                    )
        except EOFError:
            pass  # subprocess exited
        except Exception as e:
            logger.warning(f"[PlayManager] stdout reader error: {e}")

        # EOF — process exited, clean up
        logger.info(
            f"[PlayManager] Session {session_id} ended (streamed {frame_count} frames)"
        )
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                ws_manager.broadcast(
                    session_id, {"type": "status", "status": "ended"}
                ),
                self.loop,
            )
        with self.lock:
            if session_id in self.sessions:
                self._remove_gamepad_file(self.sessions[session_id])
                del self.sessions[session_id]

    def _stderr_reader(self, session_id: str, process: subprocess.Popen):
        """Drain stderr from the play subprocess to the logger."""
        try:
            while True:
                raw_line = process.stderr.readline()
                if not raw_line:
                    break
                line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
                if line:
                    logger.info(f"[PlayManager:{session_id}:err] {line}")
        except Exception as e:
            logger.warning(f"[PlayManager] stderr reader error: {e}")

    def _cleanup_dead_sessions(self):
        """Remove any sessions whose processes have exited."""
        dead_ids = [
            sid for sid, session in self.sessions.items() if session.process.poll() is not None
        ]
        for sid in dead_ids:
            self._remove_gamepad_file(self.sessions[sid])
            del self.sessions[sid]

    @staticmethod
    def _remove_gamepad_file(session: PlaySession) -> None:
        """Clean up the gamepad IPC file."""
        if session.gamepad_file:
            try:
                os.remove(session.gamepad_file)
            except OSError:
                pass


# Global instance
play_manager = PlayManager()
