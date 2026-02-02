from fastapi import APIRouter
from typing import List

router = APIRouter()

@router.get("/emulators", response_model=List[str])
async def list_emulators():
    # Stable-retro doesn't expose cores directly in a simple list always,
    # but supports Sega Genesis, SNES, NES, Atari2600, etc.
    return [
        "Genesis",
        "SNES",
        "NES",
        "Atari2600",
        "GameBoy",
        "GBA",
        "PCEngine"
    ]
