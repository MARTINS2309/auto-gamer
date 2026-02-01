"""
Act - Execute actions in the game.

Modules:
- input: Unified input (socket + PostMessage fallback, reads mGBA config)
- launcher: Start mGBA with ROM
- action_blocks: Scripted sequences for deterministic game sections

See: mGBA/scripts/ai_control.lua for socket command protocol
See: docs/plan.md for architecture overview
"""

from .input import (
    InputSender, KEYS, load_mgba_keys,
    GameState, PartyMember, BattleState
)
from .launcher import GameLauncher, launch_mgba, is_mgba_running
from .action_blocks import (
    ActionBlock, ActionBlockRunner, ActionStep, Trigger, TriggerType,
    MemoryCondition, CapturePoint, install_default_blocks
)
