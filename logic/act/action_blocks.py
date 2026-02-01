"""
ActionBlocks - Scripted action sequences with memory/vision triggers.

For deterministic game sequences (intro, menus, tutorials) where learning
has no value. These execute predefined inputs to get to actual gameplay.

Triggers can be:
- Memory-based: Check specific addresses/values
- Scene-based: Match detected scene type
- Text-based: OCR match on screen (future)
- Composite: Multiple conditions

Each block captures data for the analyzer to understand game progression.
"""

import time
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Callable
from enum import Enum


class TriggerType(Enum):
    MEMORY = "memory"       # Check memory address values
    SCENE = "scene"         # Match scene type (title, battle, etc.)
    POSITION = "position"   # Player at specific location
    COMPOSITE = "composite" # Multiple conditions (AND/OR)
    ALWAYS = "always"       # Always triggers (for chaining)


@dataclass
class MemoryCondition:
    """Condition based on memory value."""
    address: int
    operator: str  # "==", "!=", ">", "<", ">=", "<=", "&" (bitmask)
    value: int
    label: str = ""  # Human-readable name

    def check(self, reader) -> bool:
        """Check if condition is met."""
        actual = reader(self.address)
        if self.operator == "==":
            return actual == self.value
        elif self.operator == "!=":
            return actual != self.value
        elif self.operator == ">":
            return actual > self.value
        elif self.operator == "<":
            return actual < self.value
        elif self.operator == ">=":
            return actual >= self.value
        elif self.operator == "<=":
            return actual <= self.value
        elif self.operator == "&":
            return (actual & self.value) != 0
        return False


@dataclass
class Trigger:
    """Trigger condition for an action block."""
    type: TriggerType
    scene: Optional[str] = None  # For SCENE type
    memory_conditions: List[MemoryCondition] = field(default_factory=list)
    position: Optional[Dict[str, int]] = None  # {x, y, map} for POSITION
    composite_op: str = "AND"  # "AND" or "OR" for COMPOSITE
    sub_triggers: List['Trigger'] = field(default_factory=list)

    def check(self, game_state, memory_reader=None) -> bool:
        """Check if trigger conditions are met."""
        if self.type == TriggerType.ALWAYS:
            return True

        elif self.type == TriggerType.SCENE:
            return game_state.scene == self.scene

        elif self.type == TriggerType.MEMORY:
            if not memory_reader:
                return False
            return all(cond.check(memory_reader) for cond in self.memory_conditions)

        elif self.type == TriggerType.POSITION:
            if not self.position:
                return False
            return (game_state.x == self.position.get("x", -1) and
                    game_state.y == self.position.get("y", -1) and
                    game_state.map_num == self.position.get("map", -1))

        elif self.type == TriggerType.COMPOSITE:
            results = [t.check(game_state, memory_reader) for t in self.sub_triggers]
            if self.composite_op == "AND":
                return all(results)
            else:  # OR
                return any(results)

        return False


@dataclass
class ActionStep:
    """Single action in a sequence."""
    action: str           # Button(s) to press: "a", "up", "start", "up+a"
    hold_frames: int = 3  # Frames to hold button (~50ms at 60fps)
    wait_frames: int = 6  # Frames to wait after release (~100ms at 60fps)
    repeat: int = 1       # Repeat this action N times
    comment: str = ""     # What this step does


@dataclass
class CapturePoint:
    """Data to capture during/after block execution."""
    name: str                    # e.g., "player_name", "starter_pokemon"
    memory_address: Optional[int] = None  # Read from memory
    state_field: Optional[str] = None     # Read from game state
    screenshot: bool = False     # Take screenshot


@dataclass
class ActionBlock:
    """
    A scripted sequence of actions with trigger conditions.

    Blocks can chain to other blocks, allowing complex sequences
    like: Title -> New Game -> Intro -> Name Entry -> Starter Select
    """
    id: str
    name: str
    description: str
    trigger: Trigger
    actions: List[ActionStep]
    captures: List[CapturePoint] = field(default_factory=list)
    next_block_id: Optional[str] = None  # Chain to another block
    priority: int = 0  # Higher = checked first
    enabled: bool = True
    timeout_ms: int = 30000  # Max time to run before aborting

    # Execution state (not saved)
    _executed: bool = field(default=False, repr=False)
    _execution_time: float = field(default=0.0, repr=False)

    def to_dict(self) -> dict:
        """Convert to dictionary for saving."""
        d = asdict(self)
        # Recursively fix trigger types (enums aren't JSON serializable)
        d['trigger'] = self._serialize_trigger(d['trigger'])
        # Remove runtime state
        d.pop('_executed', None)
        d.pop('_execution_time', None)
        return d

    def _serialize_trigger(self, trigger_dict: dict) -> dict:
        """Recursively serialize trigger, converting enums to values."""
        result = {}
        for key, value in trigger_dict.items():
            if key == 'type' and hasattr(value, 'value'):
                # Convert TriggerType enum to string
                result[key] = value.value
            elif key == 'sub_triggers' and value:
                # Recursively serialize sub_triggers
                result[key] = [self._serialize_trigger(st) for st in value]
            else:
                result[key] = value
        return result

    @staticmethod
    def _parse_trigger(trigger_data: dict) -> 'Trigger':
        """Recursively parse trigger from dict."""
        trigger_type = TriggerType(trigger_data.get('type', 'always'))

        memory_conditions = [
            MemoryCondition(**mc) for mc in trigger_data.get('memory_conditions', [])
        ]

        # Recursively parse sub_triggers
        sub_triggers = [
            ActionBlock._parse_trigger(st) for st in trigger_data.get('sub_triggers', [])
        ]

        return Trigger(
            type=trigger_type,
            scene=trigger_data.get('scene'),
            memory_conditions=memory_conditions,
            position=trigger_data.get('position'),
            composite_op=trigger_data.get('composite_op', 'AND'),
            sub_triggers=sub_triggers,
        )

    @classmethod
    def from_dict(cls, d: dict) -> 'ActionBlock':
        """Create from dictionary."""
        # Parse trigger
        trigger_data = d.pop('trigger', {})
        trigger = cls._parse_trigger(trigger_data)

        # Parse actions
        actions = [ActionStep(**a) for a in d.pop('actions', [])]

        # Parse captures
        captures = [CapturePoint(**c) for c in d.pop('captures', [])]

        return cls(
            trigger=trigger,
            actions=actions,
            captures=captures,
            **d
        )


class ActionBlockRunner:
    """
    Executes action blocks based on game state.

    Checks triggers each frame and runs matching blocks.
    Tracks execution history for analyzer.
    """

    def __init__(self, sender, blocks_dir: Path = None):
        self.sender = sender
        self.blocks_dir = blocks_dir or Path("data/action_blocks")
        self.blocks_dir.mkdir(parents=True, exist_ok=True)

        self.blocks: Dict[str, ActionBlock] = {}
        self.execution_history: List[Dict] = []
        self.captured_data: Dict[str, Any] = {}

        self.current_block: Optional[ActionBlock] = None
        self.current_step: int = 0

        self._load_blocks()

    def _load_blocks(self):
        """Load all action blocks from disk."""
        for path in self.blocks_dir.glob("*.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                    block = ActionBlock.from_dict(data)
                    self.blocks[block.id] = block
            except Exception as e:
                print(f"Failed to load block {path}: {e}")

        print(f"Loaded {len(self.blocks)} action blocks")

    def save_block(self, block: ActionBlock):
        """Save an action block to disk."""
        path = self.blocks_dir / f"{block.id}.json"
        with open(path, 'w') as f:
            json.dump(block.to_dict(), f, indent=2)
        self.blocks[block.id] = block

    def add_block(self, block: ActionBlock):
        """Add a block to the registry."""
        self.blocks[block.id] = block
        self.save_block(block)

    def check_triggers(self, game_state, memory_reader=None) -> Optional[ActionBlock]:
        """
        Check all block triggers against current state.
        Returns highest priority matching block.
        """
        if self.current_block:
            return None  # Already executing a block

        # Sort by priority (higher first)
        sorted_blocks = sorted(
            [b for b in self.blocks.values() if b.enabled],
            key=lambda b: b.priority,
            reverse=True
        )

        for block in sorted_blocks:
            # Skip already executed blocks (prevents re-triggering)
            if block._executed:
                continue
            # Skip ALWAYS blocks - they only run when chained to
            if block.trigger.type == TriggerType.ALWAYS:
                continue
            if block.trigger.check(game_state, memory_reader):
                return block

        return None

    def start_block(self, block: ActionBlock):
        """Start executing an action block."""
        self.current_block = block
        self.current_step = 0
        block._executed = False
        block._execution_time = time.time()

        print(f"Starting action block: {block.name}")

    def execute_step(self) -> bool:
        """
        Execute current step of active block.
        Returns True only if all blocks complete (no more chained blocks).
        Returns False if still executing (including newly chained blocks).
        """
        if not self.current_block:
            return True

        block = self.current_block

        # Check timeout
        elapsed = time.time() - block._execution_time
        if elapsed * 1000 > block.timeout_ms:
            print(f"Block {block.name} timed out")
            self._complete_block(success=False)
            # Check if a new block was chained
            return self.current_block is None

        # Get current step
        if self.current_step >= len(block.actions):
            self._complete_block(success=True)
            # Check if a new block was chained - if so, continue executing
            return self.current_block is None

        step = block.actions[self.current_step]

        # Execute action using frame-based timing
        for _ in range(step.repeat):
            # Send button with hold duration in frames
            self.sender.send(step.action, hold_frames=step.hold_frames)
            # Wait for additional frames after release
            if step.wait_frames > 0:
                self.sender.frame_advance(step.wait_frames)

        self.current_step += 1
        return False

    def _complete_block(self, success: bool):
        """Complete current block execution."""
        block = self.current_block
        if not block:
            return

        block._executed = True
        elapsed = time.time() - block._execution_time

        # Record execution
        self.execution_history.append({
            "block_id": block.id,
            "block_name": block.name,
            "success": success,
            "elapsed_ms": int(elapsed * 1000),
            "timestamp": time.time(),
            "captured": dict(self.captured_data),
        })

        print(f"Completed block: {block.name} ({'success' if success else 'failed'})")

        # Chain to next block if specified
        next_id = block.next_block_id
        self.current_block = None
        self.current_step = 0

        if success and next_id and next_id in self.blocks:
            self.start_block(self.blocks[next_id])

    def capture_data(self, game_state, memory_reader=None):
        """Capture data points defined in current block."""
        if not self.current_block:
            return

        for capture in self.current_block.captures:
            value = None

            if capture.memory_address and memory_reader:
                value = memory_reader(capture.memory_address)
            elif capture.state_field:
                value = getattr(game_state, capture.state_field, None)

            if value is not None:
                self.captured_data[capture.name] = value

    def get_execution_summary(self) -> Dict:
        """Get summary of executed blocks for analyzer."""
        return {
            "total_executions": len(self.execution_history),
            "blocks_executed": list(set(h["block_id"] for h in self.execution_history)),
            "captured_data": dict(self.captured_data),
            "history": self.execution_history[-20:],  # Last 20
        }

    def reset(self):
        """Reset execution state for new run."""
        self.current_block = None
        self.current_step = 0
        self.captured_data.clear()
        # Don't clear history - analyzer needs it


# =============================================================================
# Pre-built Action Blocks for Pokemon FireRed
# =============================================================================

def create_intro_blocks() -> List[ActionBlock]:
    """Create action blocks for Pokemon FireRed intro sequence."""

    blocks = []

    # Block 1: Title Screen -> Press Start
    # Triggers on title scene, chains to full intro sequence
    blocks.append(ActionBlock(
        id="title_start",
        name="Title Screen",
        description="Press START at title screen to begin",
        priority=100,
        trigger=Trigger(
            type=TriggerType.SCENE,
            scene="title"
        ),
        actions=[
            ActionStep("start", hold_frames=6, wait_frames=60, comment="Press START"),
            ActionStep("a", hold_frames=6, wait_frames=30, comment="Select New Game"),
            ActionStep("a", hold_frames=6, wait_frames=30, comment="Confirm"),
        ],
        next_block_id="oak_intro"
    ))

    # Block 2: Oak Intro - Spam A through dialogue until name entry
    blocks.append(ActionBlock(
        id="oak_intro",
        name="Oak Intro",
        description="Skip through Professor Oak's introduction",
        priority=80,
        trigger=Trigger(type=TriggerType.ALWAYS),
        actions=[
            # A presses to get through Oak intro dialogue
            ActionStep("a", hold_frames=3, wait_frames=12, repeat=50, comment="Skip dialogue"),
        ],
        next_block_id="name_entry_player",
        timeout_ms=60000
    ))

    # Block 3: Player Name Entry - Use START to confirm default name
    blocks.append(ActionBlock(
        id="name_entry_player",
        name="Player Name Entry",
        description="Confirm player name with START",
        priority=70,
        trigger=Trigger(type=TriggerType.ALWAYS),
        actions=[
            # In FireRed name entry: START jumps to OK button
            ActionStep("start", hold_frames=6, wait_frames=18, comment="Jump to OK"),
            ActionStep("a", hold_frames=6, wait_frames=30, comment="Confirm name"),
            ActionStep("a", hold_frames=6, wait_frames=18, repeat=5, comment="Continue dialogue"),
        ],
        next_block_id="rival_intro"
    ))

    # Block 4: Rival Intro dialogue
    blocks.append(ActionBlock(
        id="rival_intro",
        name="Rival Introduction",
        description="Skip rival introduction dialogue",
        priority=60,
        trigger=Trigger(type=TriggerType.ALWAYS),
        actions=[
            ActionStep("a", hold_frames=3, wait_frames=12, repeat=20, comment="Skip dialogue"),
        ],
        next_block_id="name_entry_rival"
    ))

    # Block 5: Rival Name Entry - Use START to confirm default name
    blocks.append(ActionBlock(
        id="name_entry_rival",
        name="Rival Name Entry",
        description="Confirm rival name with START",
        priority=50,
        trigger=Trigger(type=TriggerType.ALWAYS),
        actions=[
            ActionStep("start", hold_frames=6, wait_frames=18, comment="Jump to OK"),
            ActionStep("a", hold_frames=6, wait_frames=30, comment="Confirm name"),
            ActionStep("a", hold_frames=6, wait_frames=18, repeat=5, comment="Continue dialogue"),
        ],
        next_block_id="final_confirm"
    ))

    # Block 6: Final confirmation and shrink animation
    blocks.append(ActionBlock(
        id="final_confirm",
        name="Final Confirmation",
        description="Confirm and start game",
        priority=40,
        trigger=Trigger(type=TriggerType.ALWAYS),
        actions=[
            ActionStep("a", hold_frames=3, wait_frames=12, repeat=30, comment="Confirm and skip"),
        ],
        # No next_block - intro complete!
    ))

    return blocks


def create_starter_block() -> ActionBlock:
    """Block for selecting starter Pokemon (triggers in Oak's lab)."""
    return ActionBlock(
        id="starter_select",
        name="Starter Selection",
        description="Select starter Pokemon from Oak's lab",
        priority=30,
        trigger=Trigger(
            type=TriggerType.COMPOSITE,
            composite_op="AND",
            sub_triggers=[
                Trigger(type=TriggerType.SCENE, scene="overworld"),
                Trigger(
                    type=TriggerType.POSITION,
                    position={"x": 7, "y": 5, "map": 16}  # Oak's lab pokeball table
                ),
            ]
        ),
        actions=[
            # This would need to be customized based on which starter
            ActionStep("a", hold_frames=6, wait_frames=18, comment="Interact with Pokeball"),
            ActionStep("a", hold_frames=6, wait_frames=18, repeat=5, comment="Confirm selection"),
        ],
        captures=[
            CapturePoint(name="starter_species", memory_address=0x02024284),  # First party mon
        ]
    )


def install_default_blocks(runner: ActionBlockRunner):
    """Install all default action blocks."""
    for block in create_intro_blocks():
        runner.add_block(block)

    runner.add_block(create_starter_block())

    print(f"Installed {len(runner.blocks)} default action blocks")
