"""
Input - Send inputs to mGBA.

Two modes:
1. Socket (preferred): Fast, uses ai_control.lua script, can read memory
2. PostMessage (fallback): Slower, but always works, needed for turbo (Tab)

Reads key mappings from mGBA config for PostMessage fallback.
See: mGBA/scripts/ai_control.lua for command reference
See: docs/plan.md for architecture overview
"""

import ctypes
import configparser
import socket
import time
import json
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field

from logic.paths import BASE_DIR

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Windows messages
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_TAB = 0x09  # Fast-forward in mGBA

# mGBA config path
MGBA_CONFIG = BASE_DIR / "mGBA" / "config.ini"

# Qt key code to Windows VK code mapping
QT_TO_VK = {
    46: 0xBE, 44: 0xBC,  # . ,
    **{i: i for i in range(48, 58)},   # 0-9
    **{i: i for i in range(65, 91)},   # A-Z
    16777234: 0x25, 16777235: 0x26, 16777236: 0x27, 16777237: 0x28,  # Arrows
    16777220: 0x0D, 16777219: 0x08, 16777217: 0x09, 32: 0x20,  # Enter, Back, Tab, Space
    **{16777264 + i: 0x60 + i for i in range(10)},  # Numpad 0-9
}


@dataclass
class GameState:
    """
    Full game state from mGBA memory.
    Reference: docs/plan.md Section 2 - Data Flow
    """
    scene: str = "unknown"  # title, battle, dialogue, menu, overworld
    x: int = 0
    y: int = 0
    direction: int = 0
    map_num: int = 0
    map_bank: int = 0
    battle: bool = False
    player_hp: int = 0
    player_max_hp: int = 0
    enemy_hp: int = 0
    enemy_max_hp: int = 0
    enemy_species: int = 0
    enemy_level: int = 0
    party_count: int = 0
    money: int = 0
    badges: int = 0
    can_catch: bool = False
    frame: int = 0


@dataclass
class PartyMember:
    """Pokemon party member data."""
    species: int = 0
    hp: int = 0
    max_hp: int = 0
    level: int = 0


@dataclass
class BattleState:
    """
    Battle state for decision making.
    Reference: docs/plan.md - player_hp, enemy_hp detection
    """
    active: bool = False
    player_hp: int = 0
    player_max_hp: int = 0
    enemy_hp: int = 0
    enemy_max_hp: int = 0
    enemy_species: int = 0
    wild: bool = False


def load_mgba_keys(config_path: Path = None) -> Dict[str, int]:
    """Load key mappings from mGBA config file."""
    config_path = config_path or MGBA_CONFIG
    defaults = {
        "a": 0x33, "b": 0x31, "start": 0xBE, "select": 0x30,
        "up": 0x38, "down": 0x32, "left": 0x34, "right": 0x36,
        "l": 0x37, "r": 0x39,
    }

    if not config_path.exists():
        return defaults

    try:
        config = configparser.ConfigParser()
        config.read(config_path)
        section = "gba.input.QT_K"
        if section not in config:
            return defaults

        key_map = {
            "keyA": "a", "keyB": "b", "keyStart": "start", "keySelect": "select",
            "keyUp": "up", "keyDown": "down", "keyLeft": "left", "keyRight": "right",
            "keyL": "l", "keyR": "r",
        }

        keys = {}
        for config_key, game_key in key_map.items():
            if config_key in config[section]:
                qt_code = int(config[section][config_key])
                keys[game_key] = QT_TO_VK.get(qt_code, qt_code)
            else:
                keys[game_key] = defaults[game_key]
        return keys

    except Exception:
        return defaults


KEYS = load_mgba_keys()


class InputSender:
    """
    Unified input sender - uses socket when available, PostMessage as fallback.

    Socket mode uses ai_control.lua for fast input and memory access.
    See: mGBA/scripts/ai_control.lua for command protocol.
    """

    def __init__(self, hwnd: Optional[int] = None, socket_port: int = 8765):
        self.hwnd = hwnd
        self.keys = KEYS
        self.turbo_active = False

        # Socket connection
        self.sock: Optional[socket.socket] = None
        self.socket_port = socket_port
        self.use_socket = False

        # Connection health tracking
        self._last_ping_time: float = 0
        self._ping_interval: float = 5.0  # Check every 5 seconds
        self._consecutive_failures: int = 0
        self._max_failures: int = 3  # Disconnect after 3 failures

        # Try to connect to socket
        self._connect_socket()

    def _connect_socket(self) -> bool:
        """Try to connect to mGBA socket server."""
        for port_offset in range(10):
            port = self.socket_port + port_offset
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(5.0)  # Longer timeout for frame_advance operations
                self.sock.connect(("127.0.0.1", port))

                # Check for READY
                data = self.sock.recv(1024).decode().strip()
                if "READY" in data:
                    self.use_socket = True
                    self.socket_port = port
                    return True
                else:
                    self.sock.close()
                    self.sock = None
            except (socket.timeout, socket.error):
                if self.sock:
                    self.sock.close()
                    self.sock = None

        return False

    def _socket_cmd(self, cmd: str) -> Optional[str]:
        """Send socket command and get response."""
        if not self.sock:
            return None
        try:
            self.sock.sendall((cmd + "\n").encode())
            return self.sock.recv(4096).decode().strip()
        except (socket.error, socket.timeout):
            self.use_socket = False
            self.sock = None
            return None

    # -------------------------------------------------------------------------
    # Input Control (docs/plan.md: input module)
    # -------------------------------------------------------------------------

    def send(self, key: str, hold_frames: int = 3) -> bool:
        """
        Send a key press (press and release).

        Args:
            key: Button to press (a, b, up, down, etc.)
            hold_frames: Frames to hold the button (default 3, ~50ms at 60fps)
        """
        key = key.lower()

        # Try socket first - use frame_advance for deterministic timing
        if self.use_socket:
            resp = self._socket_cmd(f"INPUT {key.upper()}")
            if resp and resp.startswith("OK"):
                # Use frame_advance for precise timing
                self.frame_advance(hold_frames)
                self._socket_cmd("RELEASE")
                return True

        # Fallback to PostMessage - convert frames to ms
        if not self.hwnd or key not in self.keys:
            return False

        hold_time_ms = int(hold_frames * 16.67)
        vk = self.keys[key]
        user32.PostMessageW(self.hwnd, WM_KEYDOWN, vk, 0)
        kernel32.Sleep(hold_time_ms)
        user32.PostMessageW(self.hwnd, WM_KEYUP, vk, 0)
        return True

    def hold(self, keys: str) -> bool:
        """Hold keys across frames (socket only)."""
        if not self.use_socket:
            return False
        resp = self._socket_cmd(f"HOLD {keys.upper()}")
        return resp is not None and resp.startswith("OK")

    def release(self) -> bool:
        """Release all held keys (socket only)."""
        if not self.use_socket:
            return False
        resp = self._socket_cmd("RELEASE")
        return resp is not None and resp.startswith("OK")

    def enable_turbo(self) -> bool:
        """Enable fast-forward (always uses PostMessage for Tab key)."""
        if not self.hwnd or self.turbo_active:
            return False
        user32.PostMessageW(self.hwnd, WM_KEYDOWN, VK_TAB, 0)
        self.turbo_active = True
        return True

    def disable_turbo(self) -> bool:
        """Disable fast-forward."""
        if not self.hwnd or not self.turbo_active:
            return False
        user32.PostMessageW(self.hwnd, WM_KEYUP, VK_TAB, 0)
        self.turbo_active = False
        return True

    def set_turbo(self, enabled: bool) -> bool:
        """Set turbo mode on/off."""
        return self.enable_turbo() if enabled else self.disable_turbo()

    # -------------------------------------------------------------------------
    # Game State (docs/plan.md: PokemonState)
    # -------------------------------------------------------------------------

    def get_state(self) -> Optional[GameState]:
        """
        Get full game state (socket only).
        Returns scene, position, battle info, party, money, badges.
        """
        if not self.use_socket:
            return None

        resp = self._socket_cmd("STATE")
        if not resp or not resp.startswith("OK "):
            return None

        try:
            data = json.loads(resp[3:])
            return GameState(
                scene=data.get("scene", "unknown"),
                x=data.get("x", 0),
                y=data.get("y", 0),
                direction=data.get("dir", 0),
                map_num=data.get("map", 0),
                map_bank=data.get("bank", 0),
                battle=data.get("battle", False),
                player_hp=data.get("playerHp", 0),
                player_max_hp=data.get("playerMaxHp", 0),
                enemy_hp=data.get("enemyHp", 0),
                enemy_max_hp=data.get("enemyMaxHp", 0),
                enemy_species=data.get("enemySpecies", 0),
                enemy_level=data.get("enemyLevel", 0),
                party_count=data.get("party", 0),
                money=data.get("money", 0),
                badges=data.get("badges", 0),
                can_catch=data.get("canCatch", False),
                frame=data.get("frame", 0),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def get_player(self) -> Optional[Dict]:
        """Get player position and map info (socket only)."""
        if not self.use_socket:
            return None
        resp = self._socket_cmd("PLAYER")
        if resp and resp.startswith("OK "):
            try:
                return json.loads(resp[3:])
            except json.JSONDecodeError:
                pass
        return None

    def get_party(self) -> Optional[List[PartyMember]]:
        """Get party Pokemon summary (socket only)."""
        if not self.use_socket:
            return None
        resp = self._socket_cmd("PARTY")
        if not resp or not resp.startswith("OK "):
            return None
        try:
            data = json.loads(resp[3:])
            return [
                PartyMember(
                    species=p.get("species", 0),
                    hp=p.get("hp", 0),
                    max_hp=p.get("maxHp", 0),
                    level=p.get("level", 0)
                )
                for p in data
            ]
        except (json.JSONDecodeError, KeyError):
            return None

    def get_battle(self) -> Optional[BattleState]:
        """Get battle state (socket only)."""
        if not self.use_socket:
            return None
        resp = self._socket_cmd("BATTLE")
        if not resp or not resp.startswith("OK "):
            return None
        try:
            data = json.loads(resp[3:])
            return BattleState(
                active=data.get("active", False),
                player_hp=data.get("playerHp", 0),
                player_max_hp=data.get("playerMaxHp", 0),
                enemy_hp=data.get("enemyHp", 0),
                enemy_max_hp=data.get("enemyMaxHp", 0),
                enemy_species=data.get("enemySpecies", 0),
                wild=data.get("wild", False),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def detect_scene(self) -> str:
        """Detect game scene from memory (socket only)."""
        state = self.get_state()
        if not state:
            return "unknown"
        return state.scene

    # -------------------------------------------------------------------------
    # Memory Access (docs/plan.md: memory addresses)
    # -------------------------------------------------------------------------

    def read_memory(self, address: int, size: int = 1) -> Optional[int]:
        """Read memory value (socket only)."""
        if not self.use_socket:
            return None

        cmd = {1: "READ", 2: "READ16", 4: "READ32"}.get(size, "READ")
        resp = self._socket_cmd(f"{cmd} {hex(address)}")
        if resp and resp.startswith("OK "):
            try:
                return int(resp[3:])
            except ValueError:
                pass
        return None

    def write_memory(self, address: int, value: int) -> bool:
        """Write byte to memory (socket only)."""
        if not self.use_socket:
            return False
        resp = self._socket_cmd(f"WRITE {hex(address)} {value}")
        return resp is not None and resp.startswith("OK")

    def read_range(self, address: int, length: int) -> Optional[str]:
        """Read byte range as hex string (socket only)."""
        if not self.use_socket:
            return None
        resp = self._socket_cmd(f"RANGE {hex(address)} {length}")
        if resp and resp.startswith("OK "):
            return resp[3:]
        return None

    # -------------------------------------------------------------------------
    # Emulator Control (docs/plan.md: RL training support)
    # -------------------------------------------------------------------------

    def frame_advance(self, count: int = 1) -> Optional[int]:
        """Advance emulation by N frames (socket only). Returns new frame number."""
        if not self.use_socket:
            return None
        cmd = "FRAME" if count == 1 else f"FRAMES {count}"
        resp = self._socket_cmd(cmd)
        if resp and resp.startswith("OK "):
            try:
                return int(resp[3:])
            except ValueError:
                pass
        return None

    def reset(self) -> bool:
        """Reset emulation (socket only)."""
        if not self.use_socket:
            return False
        resp = self._socket_cmd("RESET")
        return resp is not None and resp.startswith("OK")

    def screenshot(self, path: str = "screenshot.png") -> Optional[str]:
        """Save screenshot (socket only). Returns path."""
        if not self.use_socket:
            return None
        resp = self._socket_cmd(f"SCREENSHOT {path}")
        if resp and resp.startswith("OK "):
            return resp[3:]
        return None

    # -------------------------------------------------------------------------
    # Save States (docs/plan.md: RL episode resets)
    # -------------------------------------------------------------------------

    def save_state(self, slot: int = 1) -> bool:
        """Save state to slot 0-9 (socket only)."""
        if not self.use_socket:
            return False
        resp = self._socket_cmd(f"SAVE {slot}")
        return resp is not None and resp.startswith("OK")

    def load_state(self, slot: int = 1) -> bool:
        """Load state from slot 0-9 (socket only)."""
        if not self.use_socket:
            return False
        resp = self._socket_cmd(f"LOAD {slot}")
        return resp is not None and resp.startswith("OK")

    # -------------------------------------------------------------------------
    # System Info
    # -------------------------------------------------------------------------

    def get_info(self) -> Optional[Dict]:
        """Get ROM info (socket only)."""
        if not self.use_socket:
            return None
        resp = self._socket_cmd("INFO")
        if resp and resp.startswith("OK "):
            try:
                return json.loads(resp[3:])
            except json.JSONDecodeError:
                pass
        return None

    def get_speed(self) -> Optional[Dict]:
        """Get speed info (socket only)."""
        if not self.use_socket:
            return None
        resp = self._socket_cmd("SPEED")
        if resp and resp.startswith("OK "):
            parts = resp[3:].split()
            return {
                "frame": int(parts[0].split("=")[1]) if len(parts) > 0 else 0,
                "freq": int(parts[1].split("=")[1]) if len(parts) > 1 else 0,
            }
        return None

    def ping(self) -> bool:
        """Test socket connection."""
        if not self.use_socket:
            return False
        resp = self._socket_cmd("PING")
        return resp == "PONG"

    # -------------------------------------------------------------------------
    # Connection Health
    # -------------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """Check if socket connection is alive."""
        return self.use_socket and self.sock is not None

    def check_connection(self) -> bool:
        """
        Periodic health check. Call this regularly during long-running operations.
        Returns True if connection is healthy, False if disconnected.
        """
        current_time = time.time()

        # Skip if checked recently
        if current_time - self._last_ping_time < self._ping_interval:
            return self.is_connected

        self._last_ping_time = current_time

        if not self.is_connected:
            return False

        # Try ping
        if self.ping():
            self._consecutive_failures = 0
            return True
        else:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._max_failures:
                print(f"Connection lost after {self._max_failures} failed pings")
                self._disconnect()
                return False
            return True  # Still connected, but ping failed

    def reconnect(self) -> bool:
        """
        Attempt to reconnect to mGBA socket.
        Returns True if reconnection successful.
        """
        print("Attempting to reconnect to mGBA...")
        self._disconnect()
        time.sleep(0.5)  # Brief pause before reconnect

        if self._connect_socket():
            self._consecutive_failures = 0
            self._last_ping_time = time.time()
            print("Reconnected successfully!")
            return True
        else:
            print("Reconnection failed")
            return False

    def _disconnect(self):
        """Clean disconnect from socket."""
        self.use_socket = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

    def get_connection_status(self) -> Dict:
        """Get detailed connection status for diagnostics."""
        return {
            "connected": self.is_connected,
            "use_socket": self.use_socket,
            "port": self.socket_port,
            "consecutive_failures": self._consecutive_failures,
            "hwnd": self.hwnd,
            "turbo_active": self.turbo_active,
        }

    def close(self):
        """Clean up socket connection."""
        if self.sock:
            try:
                self._socket_cmd("QUIT")
            except:
                pass
            self.sock.close()
            self.sock = None
