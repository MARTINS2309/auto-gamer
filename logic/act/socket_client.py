"""
Socket Client - Fast communication with mGBA via Lua script.

Uses the ai_control.lua script for direct input and memory access.
Much faster than PostMessage-based input.
"""

import socket
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class GameState:
    """Current game state from mGBA."""
    x: int = 0
    y: int = 0
    map_num: int = 0
    map_bank: int = 0
    battle: int = 0
    state: int = 0
    party_count: int = 0
    money: int = 0
    badges: int = 0


class MGBAClient:
    """Socket client for mGBA AI control script."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.timeout = 1.0

    def connect(self, retries: int = 5) -> bool:
        """Connect to mGBA socket server."""
        for attempt in range(retries):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(self.timeout)
                self.sock.connect((self.host, self.port + attempt))

                # Wait for READY
                response = self._recv()
                if response and "READY" in response:
                    self.connected = True
                    self.port = self.port + attempt
                    print(f"Connected to mGBA on port {self.port}")
                    return True

            except (socket.error, socket.timeout) as e:
                if self.sock:
                    self.sock.close()
                    self.sock = None

        print(f"Failed to connect to mGBA after {retries} attempts")
        return False

    def disconnect(self):
        """Disconnect from mGBA."""
        if self.sock:
            try:
                self._send("QUIT")
            except:
                pass
            self.sock.close()
            self.sock = None
        self.connected = False

    def _send(self, cmd: str) -> bool:
        """Send a command."""
        if not self.sock:
            return False
        try:
            self.sock.sendall((cmd + "\n").encode())
            return True
        except socket.error:
            self.connected = False
            return False

    def _recv(self) -> Optional[str]:
        """Receive a response."""
        if not self.sock:
            return None
        try:
            data = self.sock.recv(4096)
            return data.decode().strip() if data else None
        except socket.timeout:
            return None
        except socket.error:
            self.connected = False
            return None

    def _command(self, cmd: str) -> Optional[str]:
        """Send command and get response."""
        if not self._send(cmd):
            return None
        return self._recv()

    def ping(self) -> bool:
        """Test connection."""
        response = self._command("PING")
        return response == "PONG"

    def input(self, keys: str) -> bool:
        """
        Set input state.

        Args:
            keys: Key names separated by + (e.g., "A", "UP+A", "START")
                  Valid keys: A, B, START, SELECT, UP, DOWN, LEFT, RIGHT, L, R
        """
        response = self._command(f"INPUT {keys}")
        return response is not None and response.startswith("OK")

    def release(self) -> bool:
        """Release all keys."""
        response = self._command("RELEASE")
        return response is not None and response.startswith("OK")

    def press(self, key: str, hold_frames: int = 3) -> bool:
        """Press and release a key using frame-based timing."""
        if not self.input(key):
            return False
        self.frame_advance(hold_frames)
        return self.release()

    def read_byte(self, address: int) -> Optional[int]:
        """Read byte from memory."""
        response = self._command(f"READ {hex(address)}")
        if response and response.startswith("OK "):
            try:
                return int(response[3:])
            except ValueError:
                pass
        return None

    def read_word(self, address: int) -> Optional[int]:
        """Read 16-bit value from memory."""
        response = self._command(f"READ16 {hex(address)}")
        if response and response.startswith("OK "):
            try:
                return int(response[3:])
            except ValueError:
                pass
        return None

    def read_dword(self, address: int) -> Optional[int]:
        """Read 32-bit value from memory."""
        response = self._command(f"READ32 {hex(address)}")
        if response and response.startswith("OK "):
            try:
                return int(response[3:])
            except ValueError:
                pass
        return None

    def get_state(self) -> Optional[GameState]:
        """Get current game state."""
        response = self._command("STATE")
        if not response or not response.startswith("OK "):
            return None

        try:
            # Parse JSON-like response
            import json
            data = json.loads(response[3:])
            return GameState(
                x=data.get("x", 0),
                y=data.get("y", 0),
                map_num=data.get("map", 0),
                map_bank=data.get("bank", 0),
                battle=data.get("battle", 0),
                state=data.get("state", 0),
                party_count=data.get("party", 0),
                money=data.get("money", 0),
                badges=data.get("badges", 0),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def detect_scene(self) -> str:
        """Detect current game scene based on state."""
        state = self.get_state()
        if not state:
            return "unknown"

        # Battle detection
        if state.battle != 0:
            return "battle"

        # Menu/title detection based on game state
        game_state = state.state
        if game_state == 0:
            return "title"
        elif game_state in (1, 2):
            return "overworld"
        elif game_state in (3, 4):
            return "dialogue"
        elif game_state in (5, 6):
            return "menu"

        return "overworld"  # Default


class SocketInputSender:
    """
    Input sender using socket connection.
    Drop-in replacement for InputSender when mGBA script is running.
    """

    def __init__(self, client: MGBAClient):
        self.client = client
        self.turbo_active = False

    def send(self, key: str, hold_frames: int = 3) -> bool:
        """Send a key press."""
        return self.client.press(key.upper(), hold_frames)

    def enable_turbo(self) -> bool:
        """Enable turbo (not directly supported via socket)."""
        self.turbo_active = True
        return True

    def disable_turbo(self) -> bool:
        """Disable turbo."""
        self.turbo_active = False
        return True

    def set_turbo(self, enabled: bool) -> bool:
        """Set turbo mode."""
        self.turbo_active = enabled
        return True
