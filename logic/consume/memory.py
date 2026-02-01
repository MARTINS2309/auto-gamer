"""
Memory Reader - Direct memory access for Pokemon games.

Reads game state directly from mGBA memory via socket connection.
Supports Pokemon FireRed/LeafGreen with extensible address maps.

Usage:
    reader = MemoryReader(socket_connection)
    player = reader.get_player()
    party = reader.get_party()
    battle = reader.get_battle()
"""

import socket
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import IntEnum


# =============================================================================
# Pokemon FireRed/LeafGreen Memory Addresses
# =============================================================================

class Addr:
    """Memory addresses for Pokemon FireRed/LeafGreen (US)."""

    # Player Position
    PLAYER_X = 0x02036E38
    PLAYER_Y = 0x02036E3A
    PLAYER_DIR = 0x02036E3C
    MAP_BANK = 0x02036E34
    MAP_NUM = 0x02036E36

    # Player Info
    PLAYER_NAME = 0x02024EA4
    TRAINER_ID = 0x02024EAC
    PLAY_TIME_H = 0x02024EAE
    PLAY_TIME_M = 0x02024EB0
    PLAY_TIME_S = 0x02024EB2

    # Progress
    MONEY = 0x02025000
    BADGES = 0x02025028
    POKEDEX_OWNED = 0x02024EA8

    # Party
    PARTY_COUNT = 0x02024029
    PARTY_START = 0x02024284
    PARTY_SIZE = 100  # bytes per Pokemon

    # Battle State
    BATTLE_FLAG = 0x02022B4C
    BATTLE_TYPE = 0x02022B50
    WILD_FLAG = 0x02022B4C

    # Active Pokemon in Battle
    PLAYER_HP = 0x02023BE4
    PLAYER_MAX_HP = 0x02023BE6
    PLAYER_ATK = 0x02023BE8
    PLAYER_DEF = 0x02023BEA
    PLAYER_SPD = 0x02023BEC
    PLAYER_SPATK = 0x02023BEE
    PLAYER_SPDEF = 0x02023BF0

    # Enemy Pokemon
    ENEMY_HP = 0x02023C08
    ENEMY_MAX_HP = 0x02023C0A
    ENEMY_SPECIES = 0x02023C00
    ENEMY_LEVEL = 0x02023C04

    # UI/Scene Detection
    GAME_STATE = 0x03005008
    TEXT_STATE = 0x020204B4
    MENU_STATE = 0x0203ADB8
    SCRIPT_PTR = 0x03000EB0

    # Items
    ITEM_POCKET = 0x02025C6A
    KEY_ITEMS = 0x02025D5C
    BALL_POCKET = 0x02025C22


class Direction(IntEnum):
    DOWN = 0
    UP = 1
    LEFT = 2
    RIGHT = 3


class BattleType(IntEnum):
    NONE = 0
    WILD = 1
    TRAINER = 2
    GYM = 3


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Position:
    """Player position and map info."""
    x: int = 0
    y: int = 0
    direction: Direction = Direction.DOWN
    map_bank: int = 0
    map_num: int = 0

    @property
    def map_id(self) -> int:
        """Combined map ID (bank << 8 | num)."""
        return (self.map_bank << 8) | self.map_num


@dataclass
class Pokemon:
    """Pokemon data structure."""
    species: int = 0
    nickname: str = ""
    level: int = 0
    hp: int = 0
    max_hp: int = 0
    attack: int = 0
    defense: int = 0
    speed: int = 0
    sp_attack: int = 0
    sp_defense: int = 0
    experience: int = 0
    moves: List[int] = field(default_factory=list)
    pp: List[int] = field(default_factory=list)
    status: int = 0  # 0=healthy, 1=sleep, 2=poison, etc.

    @property
    def hp_percent(self) -> int:
        if self.max_hp == 0:
            return 100
        return int(100 * self.hp / self.max_hp)

    @property
    def is_fainted(self) -> bool:
        return self.hp == 0 and self.max_hp > 0


@dataclass
class Party:
    """Player's Pokemon party."""
    count: int = 0
    pokemon: List[Pokemon] = field(default_factory=list)

    @property
    def alive_count(self) -> int:
        return sum(1 for p in self.pokemon if not p.is_fainted)

    @property
    def lead(self) -> Optional[Pokemon]:
        return self.pokemon[0] if self.pokemon else None


@dataclass
class BattleState:
    """Current battle state."""
    active: bool = False
    battle_type: BattleType = BattleType.NONE
    is_wild: bool = False
    can_catch: bool = False
    can_run: bool = False

    # Player's active Pokemon
    player_hp: int = 0
    player_max_hp: int = 0
    player_level: int = 0

    # Enemy Pokemon
    enemy_species: int = 0
    enemy_hp: int = 0
    enemy_max_hp: int = 0
    enemy_level: int = 0

    @property
    def player_hp_percent(self) -> int:
        if self.player_max_hp == 0:
            return 100
        return int(100 * self.player_hp / self.player_max_hp)

    @property
    def enemy_hp_percent(self) -> int:
        if self.enemy_max_hp == 0:
            return 100
        return int(100 * self.enemy_hp / self.enemy_max_hp)


@dataclass
class Progress:
    """Game progress info."""
    money: int = 0
    badges: int = 0
    badge_count: int = 0
    pokedex_owned: int = 0
    play_time_hours: int = 0
    play_time_minutes: int = 0
    play_time_seconds: int = 0

    @property
    def play_time_total_seconds(self) -> int:
        return self.play_time_hours * 3600 + self.play_time_minutes * 60 + self.play_time_seconds


@dataclass
class Scene:
    """Current game scene/context."""
    name: str = "unknown"
    in_battle: bool = False
    in_dialogue: bool = False
    in_menu: bool = False
    in_overworld: bool = False
    at_title: bool = False


# =============================================================================
# Memory Reader
# =============================================================================

class MemoryReader:
    """
    Reads Pokemon game memory via mGBA socket connection.

    Can use an existing socket connection or create its own.
    """

    def __init__(self, sock: Optional[socket.socket] = None, port: int = 8765):
        self.sock = sock
        self.port = port
        self._connected = sock is not None

    def connect(self) -> bool:
        """Connect to mGBA socket server."""
        if self._connected:
            return True

        for offset in range(10):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(1.0)
                self.sock.connect(("127.0.0.1", self.port + offset))

                # Wait for READY
                data = self.sock.recv(1024).decode().strip()
                if "READY" in data:
                    self._connected = True
                    self.port += offset
                    return True
                self.sock.close()
            except (socket.error, socket.timeout):
                if self.sock:
                    self.sock.close()
                self.sock = None

        return False

    def disconnect(self):
        """Disconnect from socket."""
        if self.sock:
            try:
                self._cmd("QUIT")
            except:
                pass
            self.sock.close()
            self.sock = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self.sock is not None

    # -------------------------------------------------------------------------
    # Low-level Memory Access
    # -------------------------------------------------------------------------

    def _cmd(self, cmd: str) -> Optional[str]:
        """Send command and get response."""
        if not self.sock:
            return None
        try:
            self.sock.sendall((cmd + "\n").encode())
            return self.sock.recv(4096).decode().strip()
        except (socket.error, socket.timeout):
            self._connected = False
            return None

    def read8(self, addr: int) -> int:
        """Read 1 byte."""
        resp = self._cmd(f"READ {hex(addr)}")
        if resp and resp.startswith("OK "):
            try:
                return int(resp[3:])
            except ValueError:
                pass
        return 0

    def read16(self, addr: int) -> int:
        """Read 2 bytes (little-endian)."""
        resp = self._cmd(f"READ16 {hex(addr)}")
        if resp and resp.startswith("OK "):
            try:
                return int(resp[3:])
            except ValueError:
                pass
        return 0

    def read32(self, addr: int) -> int:
        """Read 4 bytes (little-endian)."""
        resp = self._cmd(f"READ32 {hex(addr)}")
        if resp and resp.startswith("OK "):
            try:
                return int(resp[3:])
            except ValueError:
                pass
        return 0

    def read_range(self, addr: int, length: int) -> bytes:
        """Read byte range."""
        resp = self._cmd(f"RANGE {hex(addr)} {length}")
        if resp and resp.startswith("OK "):
            try:
                return bytes.fromhex(resp[3:])
            except ValueError:
                pass
        return b""

    def write8(self, addr: int, value: int) -> bool:
        """Write 1 byte."""
        resp = self._cmd(f"WRITE {hex(addr)} {value}")
        return resp is not None and resp.startswith("OK")

    # -------------------------------------------------------------------------
    # High-level Game State
    # -------------------------------------------------------------------------

    def get_position(self) -> Position:
        """Get player position."""
        return Position(
            x=self.read16(Addr.PLAYER_X),
            y=self.read16(Addr.PLAYER_Y),
            direction=Direction(self.read8(Addr.PLAYER_DIR) & 0x03),
            map_bank=self.read16(Addr.MAP_BANK),
            map_num=self.read16(Addr.MAP_NUM),
        )

    def get_progress(self) -> Progress:
        """Get game progress."""
        badges = self.read8(Addr.BADGES)
        return Progress(
            money=self.read32(Addr.MONEY),
            badges=badges,
            badge_count=bin(badges).count('1'),
            play_time_hours=self.read16(Addr.PLAY_TIME_H),
            play_time_minutes=self.read8(Addr.PLAY_TIME_M),
            play_time_seconds=self.read8(Addr.PLAY_TIME_S),
        )

    def get_party(self) -> Party:
        """Get player's Pokemon party."""
        count = self.read8(Addr.PARTY_COUNT)
        pokemon = []

        for i in range(min(count, 6)):
            base = Addr.PARTY_START + (i * Addr.PARTY_SIZE)
            mon = Pokemon(
                species=self.read16(base),
                level=self.read8(base + 84),
                hp=self.read16(base + 86),
                max_hp=self.read16(base + 88),
                attack=self.read16(base + 90),
                defense=self.read16(base + 92),
                speed=self.read16(base + 94),
                sp_attack=self.read16(base + 96),
                sp_defense=self.read16(base + 98),
            )
            pokemon.append(mon)

        return Party(count=count, pokemon=pokemon)

    def get_battle(self) -> BattleState:
        """Get current battle state."""
        battle_flag = self.read8(Addr.BATTLE_FLAG)
        is_battle = battle_flag != 0
        is_wild = self.read8(Addr.WILD_FLAG) == 1

        return BattleState(
            active=is_battle,
            battle_type=BattleType.WILD if is_wild else BattleType.TRAINER if is_battle else BattleType.NONE,
            is_wild=is_wild,
            can_catch=is_battle and is_wild,
            can_run=is_wild,
            player_hp=self.read16(Addr.PLAYER_HP),
            player_max_hp=self.read16(Addr.PLAYER_MAX_HP),
            enemy_species=self.read16(Addr.ENEMY_SPECIES),
            enemy_hp=self.read16(Addr.ENEMY_HP),
            enemy_max_hp=self.read16(Addr.ENEMY_MAX_HP),
            enemy_level=self.read8(Addr.ENEMY_LEVEL),
        )

    def get_scene(self) -> Scene:
        """Detect current game scene."""
        game_state = self.read8(Addr.GAME_STATE)
        battle_flag = self.read8(Addr.BATTLE_FLAG)
        text_state = self.read8(Addr.TEXT_STATE)
        menu_state = self.read8(Addr.MENU_STATE)

        in_battle = battle_flag != 0
        in_dialogue = text_state != 0
        in_menu = menu_state != 0
        at_title = game_state == 0

        # Determine scene name
        if at_title:
            name = "title"
        elif in_battle:
            name = "battle"
        elif in_dialogue:
            name = "dialogue"
        elif in_menu:
            name = "menu"
        else:
            name = "overworld"

        return Scene(
            name=name,
            in_battle=in_battle,
            in_dialogue=in_dialogue,
            in_menu=in_menu,
            in_overworld=not (in_battle or in_dialogue or in_menu or at_title),
            at_title=at_title,
        )

    def get_full_state(self) -> Dict[str, Any]:
        """Get complete game state as dictionary."""
        pos = self.get_position()
        progress = self.get_progress()
        party = self.get_party()
        battle = self.get_battle()
        scene = self.get_scene()

        return {
            "scene": scene.name,
            "position": {
                "x": pos.x,
                "y": pos.y,
                "direction": pos.direction.name,
                "map_bank": pos.map_bank,
                "map_num": pos.map_num,
                "map_id": pos.map_id,
            },
            "progress": {
                "money": progress.money,
                "badges": progress.badge_count,
                "play_time": f"{progress.play_time_hours}:{progress.play_time_minutes:02d}:{progress.play_time_seconds:02d}",
            },
            "party": {
                "count": party.count,
                "alive": party.alive_count,
                "pokemon": [
                    {
                        "species": p.species,
                        "level": p.level,
                        "hp": p.hp,
                        "max_hp": p.max_hp,
                        "hp_percent": p.hp_percent,
                    }
                    for p in party.pokemon
                ],
            },
            "battle": {
                "active": battle.active,
                "type": battle.battle_type.name,
                "player_hp": battle.player_hp_percent,
                "enemy_hp": battle.enemy_hp_percent,
                "enemy_species": battle.enemy_species,
                "enemy_level": battle.enemy_level,
                "can_catch": battle.can_catch,
            } if battle.active else None,
        }

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def get_state_via_lua(self) -> Optional[Dict]:
        """Get state using Lua's STATE command (faster)."""
        resp = self._cmd("STATE")
        if resp and resp.startswith("OK "):
            try:
                return json.loads(resp[3:])
            except json.JSONDecodeError:
                pass
        return None

    def ping(self) -> bool:
        """Test connection."""
        resp = self._cmd("PING")
        return resp == "PONG"
