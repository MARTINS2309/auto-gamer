from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel

from ..services.rom_scanner import rom_scanner

router = APIRouter()

class RomSummary(BaseModel):
    id: str
    name: str
    system: str
    playable: bool = False

class RomDetails(RomSummary):
    states: List[str]

@router.get("/roms", response_model=List[RomSummary])
async def list_roms():
    return rom_scanner.list_games()

class RomImportRequest(BaseModel):
    path: str

@router.post("/roms/import")
async def import_roms(request: RomImportRequest):
    count = rom_scanner.import_roms(request.path)
    return {"message": "Import completed", "imported": count}

@router.get("/roms/{game_id}", response_model=RomDetails)
async def get_rom_details(game_id: str):
    details = rom_scanner.get_game_details(game_id)
    if not details:
        raise HTTPException(status_code=404, detail="ROM not found")
    return details

@router.get("/roms/{game_id}/states")
async def get_rom_states(game_id: str):
    details = rom_scanner.get_game_details(game_id)
    if not details:
        raise HTTPException(status_code=404, detail="ROM not found")
    return details["states"]
