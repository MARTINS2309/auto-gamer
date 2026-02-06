"""
Connector Builder — in-process service that wraps a RetroEnv for building
custom game connectors (data.json, scenario.json, save states).

Runs RetroEnv in-process (not subprocess) because memory search needs
low-latency RAM access.  Only one builder session at a time.
"""

import hashlib
import json
import logging
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..models.db import ConnectorModel, RomModel, SessionLocal

logger = logging.getLogger(__name__)

# Canonical ROM extensions per system (stable-retro is strict about these)
CANONICAL_EXTS: dict[str, str] = {
    "Snes": ".sfc",
    "Gba": ".gba",
    "Genesis": ".md",
    "Nes": ".nes",
    "Atari2600": ".a26",
    "Gb": ".gb",
    "Gbc": ".gbc",
    "PCEngine": ".pce",
    "Sms": ".sms",
    "GameGear": ".gg",
}

# Map our system names to stable-retro folder suffixes
SYSTEM_SUFFIX_MAP: dict[str, str] = {
    "Gba": "GbAdvance",
    "Gb": "GameBoy",
    "Nes": "Nes",
    "Snes": "Snes",
    "Genesis": "Genesis",
    "Atari2600": "Atari2600",
    "PCEngine": "PCEngine",
    "Sms": "Sms",
    "GameGear": "GameGear",
}

CUSTOM_INTEGRATIONS_DIR = Path("data/custom_integrations")


@dataclass
class WatchDef:
    """A named memory watch (variable)."""

    name: str
    address: int
    type: str  # e.g. "|u1", ">u2", "<i4"


@dataclass
class RewardDef:
    """A reward signal definition."""

    variable: str
    operation: str  # "delta", "threshold", "equals"
    reference: float
    multiplier: float


@dataclass
class DoneCondition:
    """An episode-done condition."""

    variable: str
    operation: str  # "equal", "less-than", "greater-than"
    reference: float


class ConnectorBuilderSession:
    """
    Wraps a RetroEnv with thread-safe methods for the connector builder.

    All public methods acquire self._lock before touching the env.
    """

    def __init__(self, rom: RomModel):
        self.rom = rom
        self.game_name: str = ""
        self.integration_path: Path = CUSTOM_INTEGRATIONS_DIR
        self.game_path: Path | None = None
        self.env = None
        self.frame_count: int = 0
        self.watches: dict[str, WatchDef] = {}
        self.rewards: list[RewardDef] = []
        self.done_conditions: list[DoneCondition] = []
        self.saved_states: dict[str, bytes] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setup(self) -> dict:
        """Create temp integration folder with stubs and init RetroEnv."""
        import stable_retro as retro

        with self._lock:
            suffix = SYSTEM_SUFFIX_MAP.get(self.rom.system, self.rom.system)
            short_id = self.rom.id.split("-")[0] if self.rom.id else "unknown"
            self.game_name = f"Custom-{short_id}-{suffix}"

            self.integration_path = CUSTOM_INTEGRATIONS_DIR
            self.integration_path.mkdir(parents=True, exist_ok=True)

            self.game_path = self.integration_path / self.game_name
            self.game_path.mkdir(exist_ok=True)

            # 1. Copy ROM with canonical extension
            ext = CANONICAL_EXTS.get(self.rom.system)
            if not ext and self.rom.file_path:
                ext = Path(self.rom.file_path).suffix
            if not ext:
                ext = ".bin"

            dest_rom = self.game_path / f"rom{ext}"
            if not dest_rom.exists() and self.rom.file_path:
                shutil.copy2(self.rom.file_path, dest_rom)

            # 2. rom.sha
            sha_path = self.game_path / "rom.sha"
            if not sha_path.exists() and dest_rom.exists():
                sha1 = hashlib.sha1(dest_rom.read_bytes()).hexdigest()
                sha_path.write_text(sha1)

            # 3. data.json (empty variables)
            data_json = self.game_path / "data.json"
            if not data_json.exists():
                data_json.write_text(json.dumps({"info": {}}, indent=2))

            # 4. scenario.json (empty)
            scenario_json = self.game_path / "scenario.json"
            if not scenario_json.exists():
                scenario_json.write_text(
                    json.dumps(
                        {"done": {"variables": {}}, "reward": {"variables": {}}},
                        indent=2,
                    )
                )

            # 5. metadata.json
            metadata_json = self.game_path / "metadata.json"
            if not metadata_json.exists():
                metadata_json.write_text(
                    json.dumps(
                        {"default_state": None, "sorting_name": self.rom.display_name},
                        indent=2,
                    )
                )

            # Register custom integration path
            retro.data.add_custom_integration(str(self.integration_path.absolute()))

            # Create env booting from ROM start (no .state needed)
            inttype = retro.data.Integrations.STABLE | retro.data.Integrations.CUSTOM_ONLY
            self.env = retro.make(
                game=self.game_name,
                state=retro.State.NONE,
                inttype=inttype,
                use_restricted_actions=retro.Actions.ALL,
                render_mode="rgb_array",
                record=False,
            )
            self.env.reset()
            self.frame_count = 0

            return {
                "game_name": self.game_name,
                "system": self.rom.system,
                "rom_name": self.rom.display_name,
                "buttons": list(self.env.buttons) if self.env else [],
            }

    def close(self):
        """Clean up env."""
        with self._lock:
            if self.env:
                self.env.close()
                self.env = None

    # ------------------------------------------------------------------
    # Emulator control
    # ------------------------------------------------------------------

    def step(self, action: list[int] | None = None, n: int = 1) -> dict:
        """Step emulator N frames with given action (button mask)."""
        with self._lock:
            if not self.env:
                raise RuntimeError("No active session")

            action_array = np.zeros(self.env.action_space.shape, dtype=np.int64)
            if action:
                for i, v in enumerate(action):
                    if i < len(action_array):
                        action_array[i] = v

            reward_total = 0.0
            done = False
            for _ in range(n):
                _obs, reward, terminated, truncated, _info = self.env.step(action_array)
                reward_total += reward
                self.frame_count += 1
                done = terminated or truncated
                if done:
                    break

            return {
                "frame": self.frame_count,
                "reward": reward_total,
                "done": done,
            }

    def get_screen(self) -> np.ndarray:
        """Get current frame as RGB array (H, W, 3)."""
        with self._lock:
            if not self.env:
                raise RuntimeError("No active session")
            return self.env.render()

    def get_ram(self) -> bytes:
        """Return RAM bytes."""
        with self._lock:
            if not self.env:
                raise RuntimeError("No active session")
            ram = self.env.get_ram()
            return ram.tobytes()

    # ------------------------------------------------------------------
    # Memory search
    # ------------------------------------------------------------------

    def search(self, name: str, value: int) -> dict:
        """Exact value search via data.searches."""
        with self._lock:
            if not self.env:
                raise RuntimeError("No active session")
            self.env.data.update_ram()
            handle = self.env.data.searches[name]
            handle.search(value)
            return self._search_results(name)

    def delta_search(self, name: str, op: str, ref: int) -> dict:
        """Delta search. op: 'equal', 'less-than', 'greater-than', 'not-equal'."""
        with self._lock:
            if not self.env:
                raise RuntimeError("No active session")
            self.env.data.update_ram()
            handle = self.env.data.searches[name]
            handle.delta(op, ref)
            return self._search_results(name)

    def get_search_results(self, name: str) -> dict:
        """Get current results for a named search."""
        with self._lock:
            if not self.env:
                raise RuntimeError("No active session")
            return self._search_results(name)

    def remove_search(self, name: str):
        """Delete a named search."""
        with self._lock:
            if not self.env:
                raise RuntimeError("No active session")
            del self.env.data.searches[name]

    def _search_results(self, name: str) -> dict:
        """Get search result info (call inside lock)."""
        search = self.env.data.get_search(name)
        num = search.num_results()
        unique = None
        results = []
        if search.has_unique_result():
            unique = search.unique_result()
        elif num <= 100:
            # Only return typed_results for small result sets
            try:
                raw = search.typed_results()
                for addr_info, types in raw:
                    results.append({"address": addr_info[0], "types": list(types)})
            except Exception:
                pass
        return {
            "name": name,
            "num_results": num,
            "unique": unique,
            "results": results,
        }

    # ------------------------------------------------------------------
    # Watches (named memory variables)
    # ------------------------------------------------------------------

    def add_watch(self, name: str, address: int, type_str: str):
        """Register a named memory variable."""
        with self._lock:
            if not self.env:
                raise RuntimeError("No active session")
            self.watches[name] = WatchDef(name=name, address=address, type=type_str)
            # Also register in retro's GameData so lookup_value works
            self.env.data.set_variable(name, {"address": address, "type": type_str})
            # Write updated data.json
            self._write_data_json()

    def remove_watch(self, name: str):
        """Remove a named watch."""
        with self._lock:
            if not self.env:
                raise RuntimeError("No active session")
            self.watches.pop(name, None)
            try:
                self.env.data.remove_variable(name)
            except Exception:
                pass
            self._write_data_json()

    def read_watches(self) -> dict[str, int | float]:
        """Read current values of all watches."""
        with self._lock:
            if not self.env:
                raise RuntimeError("No active session")
            self.env.data.update_ram()
            values = {}
            for name in self.watches:
                try:
                    values[name] = self.env.data.lookup_value(name)
                except Exception:
                    values[name] = None
            return values

    def _write_data_json(self):
        """Persist current watches to data.json."""
        if not self.game_path:
            return
        info = {}
        for w in self.watches.values():
            info[w.name] = {"address": w.address, "type": w.type}
        data = {"info": info}
        (self.game_path / "data.json").write_text(json.dumps(data, indent=2))

    # ------------------------------------------------------------------
    # Rewards & done conditions
    # ------------------------------------------------------------------

    def add_reward(self, variable: str, operation: str, reference: float, multiplier: float) -> int:
        """Add a reward signal. Returns index."""
        self.rewards.append(
            RewardDef(variable=variable, operation=operation, reference=reference, multiplier=multiplier)
        )
        self._write_scenario_json()
        return len(self.rewards) - 1

    def add_done_condition(self, variable: str, operation: str, reference: float) -> int:
        """Add a done condition. Returns index."""
        self.done_conditions.append(
            DoneCondition(variable=variable, operation=operation, reference=reference)
        )
        self._write_scenario_json()
        return len(self.done_conditions) - 1

    def _write_scenario_json(self):
        """Persist rewards and done conditions to scenario.json."""
        if not self.game_path:
            return

        reward_vars = {}
        for r in self.rewards:
            reward_vars[r.variable] = {
                "reward": r.multiplier,
            }

        done_vars = {}
        for d in self.done_conditions:
            done_vars[d.variable] = {
                "op": d.operation,
                "reference": d.reference,
            }

        scenario = {
            "done": {
                "variables": done_vars,
            },
            "reward": {
                "variables": reward_vars,
            },
        }
        (self.game_path / "scenario.json").write_text(json.dumps(scenario, indent=2))

    # ------------------------------------------------------------------
    # Save states
    # ------------------------------------------------------------------

    def save_state(self, name: str) -> dict:
        """Save emulator state."""
        with self._lock:
            if not self.env:
                raise RuntimeError("No active session")
            state_bytes = self.env.unwrapped.em.get_state()
            self.saved_states[name] = state_bytes

            # Also write to .state file in integration folder
            if self.game_path:
                (self.game_path / f"{name}.state").write_bytes(state_bytes)

            return {"name": name, "size": len(state_bytes)}

    def load_state(self, name: str) -> dict:
        """Restore emulator state."""
        with self._lock:
            if not self.env:
                raise RuntimeError("No active session")

            state_bytes = self.saved_states.get(name)
            if not state_bytes and self.game_path:
                state_file = self.game_path / f"{name}.state"
                if state_file.exists():
                    state_bytes = state_file.read_bytes()

            if not state_bytes:
                raise ValueError(f"State '{name}' not found")

            self.env.unwrapped.em.set_state(state_bytes)
            self.env.unwrapped.data.reset()
            self.env.unwrapped.data.update_ram()

            return {"name": name, "frame": self.frame_count}

    def list_states(self) -> list[dict]:
        """List saved states."""
        states = []
        # In-memory states
        for name, data in self.saved_states.items():
            states.append({"name": name, "size": len(data)})
        # Also check .state files on disk
        if self.game_path:
            for f in self.game_path.glob("*.state"):
                name = f.stem
                if name not in self.saved_states:
                    states.append({"name": name, "size": f.stat().st_size})
        return states

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export(self, connector_name: str | None = None) -> dict:
        """
        Export connector files and register in DB.
        Returns info about the created connector.
        """
        with self._lock:
            if not self.game_path:
                raise RuntimeError("No active session")

            # Update metadata.json with default state
            state_names = list(self.saved_states.keys())
            if self.game_path:
                for f in self.game_path.glob("*.state"):
                    if f.stem not in state_names:
                        state_names.append(f.stem)

            default_state = state_names[0] if state_names else None
            metadata = {
                "default_state": default_state,
                "sorting_name": self.rom.display_name,
            }
            (self.game_path / "metadata.json").write_text(json.dumps(metadata, indent=2))

            # Ensure data.json and scenario.json are current
            self._write_data_json()
            self._write_scenario_json()

            # Register connector in DB
            final_name = connector_name or self.game_name
            db = SessionLocal()
            try:
                connector = db.query(ConnectorModel).filter(ConnectorModel.id == final_name).first()
                if not connector:
                    connector = ConnectorModel(
                        id=final_name,
                        system=self.rom.system,
                        display_name=self.rom.display_name or final_name,
                        sha1_hash=self.rom.sha1_hash,
                        states=state_names,
                        has_rom=True,
                    )
                    db.add(connector)
                else:
                    connector.states = state_names
                    connector.has_rom = True

                # Link ROM to connector
                rom = db.query(RomModel).filter(RomModel.id == self.rom.id).first()
                if rom:
                    rom.connector_id = final_name

                db.commit()

                return {
                    "connector_id": final_name,
                    "game_path": str(self.game_path),
                    "states": state_names,
                    "watches": len(self.watches),
                    "rewards": len(self.rewards),
                    "done_conditions": len(self.done_conditions),
                }
            finally:
                db.close()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return session info."""
        with self._lock:
            return {
                "active": self.env is not None,
                "game_name": self.game_name,
                "system": self.rom.system,
                "rom_name": self.rom.display_name,
                "frame": self.frame_count,
                "watches": {n: {"address": w.address, "type": w.type} for n, w in self.watches.items()},
                "rewards": len(self.rewards),
                "done_conditions": len(self.done_conditions),
                "states": list(self.saved_states.keys()),
            }


class ConnectorBuilderManager:
    """Singleton — enforces one builder session at a time."""

    def __init__(self):
        self._session: ConnectorBuilderSession | None = None
        self._lock = threading.Lock()

    @property
    def session(self) -> ConnectorBuilderSession | None:
        return self._session

    def start(self, rom_id: str) -> dict:
        """Start a new builder session for the given ROM."""
        with self._lock:
            if self._session and self._session.env:
                self._session.close()
                self._session = None

            db = SessionLocal()
            try:
                rom = db.query(RomModel).filter(RomModel.id == rom_id).first()
                if not rom:
                    raise ValueError(f"ROM not found: {rom_id}")
                if not rom.file_path:
                    raise ValueError(f"ROM has no file path: {rom_id}")

                # Detach from session so we can use it after close
                db.expunge(rom)
            finally:
                db.close()

            session = ConnectorBuilderSession(rom)
            result = session.setup()
            self._session = session
            return result

    def close(self):
        """Close the active session."""
        with self._lock:
            if self._session:
                self._session.close()
                self._session = None

    def require_session(self) -> ConnectorBuilderSession:
        """Get the active session or raise."""
        if not self._session or not self._session.env:
            raise RuntimeError("No active builder session. Start one first.")
        return self._session


# Global singleton
builder_manager = ConnectorBuilderManager()
