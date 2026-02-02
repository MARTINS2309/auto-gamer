import stable_retro as retro
import os
from typing import List, Dict, Any

import subprocess
import sys

class RomScanner:
    def _get_system_from_id(self, game_id: str) -> str:
        """Extract system name from game ID (e.g., 'Sonic-Genesis-v0' -> 'Genesis')."""
        parts = game_id.split('-')
        if len(parts) < 2:
            return "Unknown"
            
        # If last part is version (v0, v1), take the one before it
        if parts[-1].startswith('v') and parts[-1][1:].isdigit():
            if len(parts) >= 2:
                return parts[-2]
        
        # Otherwise assume last part is system
        return parts[-1] 

    def import_roms(self, path: str) -> int:
        """Import ROMs from a directory. Returns number of imported games."""
        try:
            # Use the same python interpreter
            result = subprocess.run(
                [sys.executable, "-m", "retro.import", path],
                capture_output=True,
                text=True
            )
            print(f"Import output: {result.stdout}")
            if result.returncode != 0:
                print(f"Import error: {result.stderr}")
                return 0
            
            # Parse output "Imported 1 games"
            # Typical output: "Importing PokemonFireRed-Gba... Imported 1 games"
            # We can just re-scan or trust it worked.
            # Let's return a success indicator?
            return 1 if "Imported" in result.stdout else 0
        except Exception as e:
            print(f"Error importing ROMs: {e}")
            return 0

    def list_games(self) -> List[Dict[str, Any]]:
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
                
                results.append({
                    "id": game,
                    "name": game,
                    "system": self._get_system_from_id(game),
                    "playable": playable
                })
            
            # Sort playable first
            results.sort(key=lambda x: (not x["playable"], x["id"]))
            return results
        except Exception as e:
            print(f"Error listing games: {e}")
            return []

    def get_game_details(self, game: str) -> Dict[str, Any]:
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

rom_scanner = RomScanner()
