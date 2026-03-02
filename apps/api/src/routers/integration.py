"""
Integration Tool router — endpoints to launch/manage the native
gym-retro-integration Qt5 tool and rescan connectors afterwards.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ..models.db import RomModel, SessionLocal
from ..services.integration_launcher import launcher
from ..services.rom_sync import rom_sync

logger = logging.getLogger(__name__)
router = APIRouter()


def _find_connector_rom(connector_id: str) -> str | None:
    """Find the rom.* file inside a connector's integration directory."""
    try:
        import retro

        data_root = Path(retro.data.path())
        for subdir in ("stable", "contrib", "experimental", "custom"):
            game_dir = data_root / subdir / connector_id
            if game_dir.is_dir():
                for f in game_dir.iterdir():
                    if f.name.startswith("rom.") and f.name != "rom.sha":
                        return str(f)
    except Exception as e:
        logger.warning("Failed to resolve connector %s: %s", connector_id, e)
    return None


class LaunchRequest(BaseModel):
    rom_id: Optional[str] = None
    connector_id: Optional[str] = None


@router.post("/integration/launch")
def launch_integration(body: LaunchRequest = LaunchRequest()):
    """Launch the native gym-retro-integration tool.

    - connector_id: opens the existing integration (edit mode)
    - rom_id: opens with the ROM file (new connector mode)
    - neither: opens the tool empty
    """
    file_path = None
    logger.info("Launch request: rom_id=%s, connector_id=%s", body.rom_id, body.connector_id)

    # Prefer connector_id (edit existing) over rom_id (new)
    if body.connector_id:
        file_path = _find_connector_rom(body.connector_id)
        if not file_path:
            logger.warning("Connector %s rom file not found, launching empty", body.connector_id)

    if not file_path and body.rom_id:
        db = SessionLocal()
        try:
            rom = db.query(RomModel).filter(RomModel.id == body.rom_id).first()
            if rom and rom.file_path:
                file_path = rom.file_path
            else:
                logger.warning("ROM %s not found or has no file_path", body.rom_id)
        finally:
            db.close()

    logger.info("Resolved file_path: %s", file_path)
    result = launcher.launch(rom_path=file_path)
    if result["status"] == "binary_not_found":
        raise HTTPException(status_code=404, detail=result["message"])
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.get("/integration/status")
def integration_status():
    """Check if the integration tool is running."""
    return launcher.status()


@router.post("/integration/stop")
def stop_integration():
    """Stop the integration tool."""
    return launcher.stop()


@router.post("/integration/rescan")
async def rescan_integrations(background_tasks: BackgroundTasks):
    """Rescan connectors after the integration tool has been used."""
    background_tasks.add_task(rom_sync.sync_connectors)
    return {"message": "Connector rescan started"}
