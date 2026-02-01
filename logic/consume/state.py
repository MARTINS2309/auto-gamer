"""
Game State - Represents current game state.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class SceneType(Enum):
    UNKNOWN = "unknown"
    TITLE = "title"
    OVERWORLD = "overworld"
    BATTLE = "battle"
    DIALOGUE = "dialogue"
    MENU = "menu"


@dataclass
class GameState:
    """Current game state."""

    scene: SceneType = SceneType.UNKNOWN

    # Battle info
    in_battle: bool = False
    player_hp: int = 100
    player_max_hp: int = 100
    enemy_hp: int = 100
    enemy_max_hp: int = 100

    # Position
    player_x: int = 0
    player_y: int = 0
    map_id: int = 0

    # UI state
    has_dialogue: bool = False
    menu_open: bool = False

    # Raw data
    raw_screen: Optional[bytes] = field(default=None, repr=False)

    @property
    def player_hp_pct(self) -> int:
        if self.player_max_hp == 0:
            return 100
        return int(100 * self.player_hp / self.player_max_hp)

    @property
    def enemy_hp_pct(self) -> int:
        if self.enemy_max_hp == 0:
            return 100
        return int(100 * self.enemy_hp / self.enemy_max_hp)
