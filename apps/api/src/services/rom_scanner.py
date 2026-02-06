import hashlib
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import stable_retro as retro


def compute_sha1_hash(file_path: Path) -> str:
    """Compute SHA1 hash of file contents (matches stable-retro format)."""
    hasher = hashlib.sha1()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_short_hash(file_path: Path, length: int = 8) -> str:
    """Compute a short hash of a file's contents for unique identification."""
    return compute_sha1_hash(file_path)[:length]

# Progress callback type: (current: int, total: int, message: str) -> None
ProgressCallback = Callable[[int, int, str], None]

# ROM file extensions by system
ROM_EXTENSIONS = {
    "Nes": [".nes", ".fds"],
    "Snes": [".sfc", ".smc"],
    "Genesis": [".md", ".bin", ".gen"],
    "Gba": [".gba"],
    "Gb": [".gb", ".gbc"],
    "Atari2600": [".a26", ".bin"],
    "PCEngine": [".pce"],
    "GameGear": [".gg"],
    "SMS": [".sms"],
    "32x": [".32x"],
    "N64": [".n64", ".z64", ".v64"],
}

# Reverse lookup: extension -> system
EXTENSION_TO_SYSTEM = {}
for system, exts in ROM_EXTENSIONS.items():
    for ext in exts:
        if ext not in EXTENSION_TO_SYSTEM:
            EXTENSION_TO_SYSTEM[ext] = system


class RomScanner:
    def _get_system_from_id(self, game_id: str) -> str:
        """Extract system name from game ID (e.g., 'Sonic-Genesis-v0' -> 'Genesis')."""
        parts = game_id.split("-")
        if len(parts) < 2:
            return "Unknown"

        # If last part is version (v0, v1), take the one before it
        if parts[-1].startswith("v") and parts[-1][1:].isdigit():
            if len(parts) >= 2:
                return parts[-2]

        # Otherwise assume last part is system
        return parts[-1]

    def import_roms(self, path: str, timeout: int = 120) -> int:
        """Import ROMs from a directory. Returns number of imported games."""
        import time

        print(f"[ROM_SCANNER] import_roms called with path={path}")
        start_time = time.time()

        try:
            # Use the same python interpreter
            cmd = [sys.executable, "-m", "retro.import", path]
            print(f"[ROM_SCANNER] Running command: {' '.join(cmd)}")
            print(f"[ROM_SCANNER] Timeout: {timeout}s")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            elapsed = time.time() - start_time
            print(f"[ROM_SCANNER] Command completed in {elapsed:.2f}s")
            print(f"[ROM_SCANNER] Return code: {result.returncode}")
            print(f"[ROM_SCANNER] Stdout: {result.stdout[:500] if result.stdout else '(empty)'}")
            print(f"[ROM_SCANNER] Stderr: {result.stderr[:500] if result.stderr else '(empty)'}")

            if result.returncode != 0:
                print(f"[ROM_SCANNER] Import error: {result.stderr}")
                return 0

            # Parse output "Imported 1 games"
            # Typical output: "Importing PokemonFireRed-Gba... Imported 1 games"
            return 1 if "Imported" in result.stdout else 0

        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            print(f"[ROM_SCANNER] TIMEOUT after {elapsed:.2f}s!")
            return 0
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[ROM_SCANNER] Error after {elapsed:.2f}s: {e}")
            return 0

    def list_games(self) -> list[dict[str, Any]]:
        """List all games available in stable-retro with metadata."""
        try:
            games = sorted(retro.data.list_games())
            results = []
            for game in games:
                try:
                    # Check if ROM file exists
                    retro.data.get_romfile_path(game)
                    playable = True
                except (FileNotFoundError, Exception):
                    playable = False

                results.append(
                    {
                        "id": game,
                        "name": game,
                        "system": self._get_system_from_id(game),
                        "playable": playable,
                    }
                )

            # Sort playable first
            results.sort(key=lambda x: (not x["playable"], x["id"]))
            return results
        except Exception as e:
            print(f"Error listing games: {e}")
            return []

    def get_game_details(self, game: str) -> dict[str, Any] | None:
        """Get details for a specific game, including available states."""
        try:
            # We don't want to call list_games() every time, ideally we cache it or trust the input
            # But verifying existence is good.
            # Using retro.data.get_romfile_path might throw if not found?
            # Let's trust list_states handles invalid games gracefully or check list_games efficiently.

            # Note: list_games() scans the directory, so might be slow if called repeatedly.
            # For now, let's assume valid input or catch error.

            states = retro.data.list_states(game)
            return {
                "id": game,
                "name": game,
                "system": self._get_system_from_id(game),
                "states": sorted(states) if states else [],
            }
        except Exception as e:
            print(f"Error getting game details: {e}")
            return None


    def scan_rom_folder(
        self, folder_path: str, progress_callback: ProgressCallback | None = None
    ) -> list[dict[str, Any]]:
        """
        Scan a folder for ROM files.
        Returns list of ROMs found with their metadata.

        This finds ROMs that may not have connectors in stable-retro.
        """
        results: list[dict[str, Any]] = []
        folder = Path(folder_path)

        if not folder.exists() or not folder.is_dir():
            print(f"[ROM_SCANNER] ROM folder not found: {folder_path}")
            return results

        print(f"[ROM_SCANNER] Scanning folder: {folder_path}")

        # Only look for ROM extensions - don't enumerate ALL files
        rom_extensions = set()
        for exts in ROM_EXTENSIONS.values():
            rom_extensions.update(exts)

        if progress_callback:
            progress_callback(0, 0, "Scanning for ROM files...")

        # Use generator - don't load all paths into memory
        i = 0
        for ext in rom_extensions:
            # Glob for each extension separately
            pattern = f"**/*{ext}"
            for file_path in folder.glob(pattern):
                if not file_path.is_file():
                    continue

                system = EXTENSION_TO_SYSTEM.get(ext)
                if not system:
                    continue

                filename = file_path.stem
                # Compute SHA1 hash for stable-retro matching
                sha1_hash = compute_sha1_hash(file_path)
                file_size = file_path.stat().st_size
                rom_id = f"{sha1_hash[:8]}-{system}"

                results.append(
                    {
                        "id": rom_id,
                        "name": self._format_display_name(filename),
                        "display_name": self._format_display_name(filename),
                        "system": system,
                        "file_path": str(file_path),
                        "file_name": file_path.name,
                        "file_size": file_size,
                        "sha1_hash": sha1_hash,
                        "has_rom": True,
                        "has_connector": False,
                    }
                )

                i += 1
                if progress_callback and i % 50 == 0:
                    progress_callback(i, 0, f"Found {i} ROM files...")

        print(f"[ROM_SCANNER] Found {len(results)} ROM files")
        if progress_callback:
            progress_callback(len(results), len(results), f"Found {len(results)} ROM files")

        return results

    def _clean_filename(self, filename: str) -> str:
        """Clean filename to create a valid ID."""
        # Remove common ROM info patterns like (U), [!], (Europe), etc.
        name = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", filename)
        # Remove non-alphanumeric chars except hyphens
        name = re.sub(r"[^a-zA-Z0-9]+", "", name)
        return name

    def _format_display_name(self, filename: str) -> str:
        """Format filename into display name."""
        # Remove ROM info patterns
        name = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", filename)
        # Add spaces between camelCase
        name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
        name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
        # Add spaces around numbers
        name = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", name)
        name = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", name)
        return name.strip()

    def list_connectors(
        self, progress_callback: ProgressCallback | None = None
    ) -> list[dict[str, Any]]:
        """
        List all connectors available in stable-retro.
        Uses ROM file hash as ID when ROM exists, for consistent deduplication with user ROMs.
        """
        try:
            games = sorted(retro.data.list_games())
            total = len(games)
            results = []

            if progress_callback:
                progress_callback(0, total, f"Scanning {total} connectors...")

            for i, game in enumerate(games):
                system = self._get_system_from_id(game)
                rom_path = None
                has_rom = False

                try:
                    # Get ROM file path
                    rom_path = retro.data.get_romfile_path(game)
                    has_rom = True
                except (FileNotFoundError, Exception):
                    pass

                # Compute SHA1 hash if ROM exists for matching
                sha1_hash = None
                if has_rom and rom_path:
                    sha1_hash = compute_sha1_hash(Path(rom_path))

                # Get available states
                try:
                    states = retro.data.list_states(game)
                except Exception:
                    states = []

                results.append(
                    {
                        "id": game,  # Connector ID is always the game name
                        "display_name": self._format_display_name(game),
                        "system": system,
                        "sha1_hash": sha1_hash,
                        "states": sorted(states) if states else [],
                        "has_rom": has_rom,
                    }
                )

                # Emit progress every 50 items
                if progress_callback and (i + 1) % 50 == 0:
                    progress_callback(i + 1, total, f"Checked {i + 1}/{total} connectors")

            if progress_callback:
                progress_callback(total, total, f"Found {total} connectors")

            return results
        except Exception as e:
            print(f"Error listing connectors: {e}")
            return []


rom_scanner = RomScanner()
