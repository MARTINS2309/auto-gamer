from fastapi import APIRouter

router = APIRouter()


@router.get("/emulators", response_model=list[str])
def list_emulators():
    """
    Dynamically lists all systems supported by the current stable-retro installation.
    """
    try:
        import stable_retro as retro

        # Extract systems (e.g., 'Genesis' from 'Sonic-Genesis')
        games = retro.data.list_games()
        systems = set()
        for game in games:
            parts = game.split("-")
            if len(parts) >= 2:
                # Heuristic: usually the 2nd part or last part depending on naming
                # Most consistent in stable-retro: GameName-System-Version
                # So taking parts[-2] if ends with 'v[0-9]' else parts[-1]

                # Logic copied from RomScanner for consistency
                if parts[-1].startswith("v") and parts[-1][1:].isdigit() and len(parts) >= 2:
                    systems.add(parts[-2])
                else:
                    systems.add(parts[-1])

        return sorted(list(systems))
    except ImportError:
        # Fallback if retro not found (dev mode without pkg?)
        return ["Genesis", "SNES", "NES", "Atari2600", "GameBoy"]
