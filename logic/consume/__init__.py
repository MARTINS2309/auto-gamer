"""
Consume - Get data from the game.

Modules:
- screen: Capture game screen
- state: Parse game state from screen/memory
- memory: Direct memory access
"""

from .screen import ScreenCapture
from .state import GameState
from .memory import MemoryReader, Position, Pokemon, Party, BattleState, Progress, Scene, Addr
