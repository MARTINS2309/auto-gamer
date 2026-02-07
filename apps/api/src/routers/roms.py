"""
ROM Router - Unified game library access.

Serves data from three tables:
- ROMs: User's local ROM files
- Connectors: stable-retro AI training connectors
- Metadata: IGDB game information

Provides a unified "library" view that joins these tables.
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ..models.db import ConnectorModel, GameMetadataModel, RomModel, SessionLocal
from ..services.rom_scanner import rom_scanner
from ..services.rom_sync import rom_sync
from .config import load_config

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class GameStatus(str):
    """Game status derived from ROM and connector availability."""

    TRAINABLE = "trainable"  # Has ROM AND has connector
    PLAYABLE = "playable"  # Has ROM, no connector
    CONNECTOR_ONLY = "connector_only"  # Has connector, no ROM


def derive_game_status(has_rom: bool, has_connector: bool) -> str:
    """Derive game status from has_rom and has_connector flags."""
    if has_rom and has_connector:
        return GameStatus.TRAINABLE
    if has_rom:
        return GameStatus.PLAYABLE
    return GameStatus.CONNECTOR_ONLY


class GameListItem(BaseModel):
    """Lightweight list response for grid view."""

    id: str
    system: str
    display_name: str

    # Categorization
    has_rom: bool = False
    has_connector: bool = False
    status: str = "connector_only"

    # Connector info (if available)
    connector_id: str | None = None
    states: list[str] = []

    # Metadata sync status
    sync_status: str = "pending"

    # Essential metadata for cards
    rating: float | None = None
    genres: list[str] = []
    release_date: str | None = None
    developer: str | None = None

    # Thumbnail
    thumbnail_url: str | None = None

    class Config:
        from_attributes = True


class GameResponse(BaseModel):
    """Complete game data - includes all metadata."""

    id: str
    system: str
    display_name: str

    # Categorization
    has_rom: bool = False
    has_connector: bool = False
    status: str = "connector_only"

    # Connector info
    connector_id: str | None = None
    states: list[str] = []

    # Sync status
    sync_status: str = "pending"
    sync_error: str | None = None
    synced_at: datetime | None = None

    # IGDB Metadata
    igdb_id: int | None = None
    igdb_name: str | None = None
    summary: str | None = None
    storyline: str | None = None
    rating: float | None = None
    rating_count: int | None = None
    genres: list[str] = []
    themes: list[str] = []
    game_modes: list[str] = []
    player_perspectives: list[str] = []
    platforms: list[str] = []
    release_date: str | None = None
    developer: str | None = None
    publisher: str | None = None
    cover_url: str | None = None
    screenshot_urls: list[str] = []

    # Thumbnail
    thumbnail_url: str | None = None
    thumbnail_status: str = "pending"

    class Config:
        from_attributes = True


# Legacy aliases
RomListItem = GameListItem
RomResponse = GameResponse


class SyncStatusResponse(BaseModel):
    """Status of sync operation with detailed breakdown."""

    is_syncing: bool
    current: str | None = None
    completed: int = 0

    # Game counts
    total: int = 0
    total_connectors: int = 0
    total_roms: int = 0
    trainable: int = 0  # ROMs with connectors
    playable_only: int = 0  # ROMs without connectors
    connector_only: int = 0  # Connectors without ROMs

    # Sync status
    synced: int = 0
    pending: int = 0
    failed: int = 0

    # Metadata coverage
    with_igdb: int = 0
    with_name: int = 0
    with_year: int = 0
    with_rating: int = 0
    with_developer: int = 0
    with_summary: int = 0
    with_genres: int = 0

    # Thumbnail coverage
    with_thumbnail: int = 0
    missing_thumbnails: int = 0


class RomImportRequest(BaseModel):
    path: str | None = None


class ResyncRequest(BaseModel):
    igdb_id: int | None = None
    libretro_name: str | None = None


# =============================================================================
# Routes
# =============================================================================


@router.get("/roms", response_model=list[GameListItem])
def list_games(
    include_connectors: bool = Query(True, description="Include connector-only entries"),
):
    """
    Get unified game library.
    Combines ROMs and connectors with their metadata.

    Args:
        include_connectors: If False, only show games with ROM files (default: True)
    """
    db = SessionLocal()
    try:
        games = []

        # Get all ROMs with their connectors and metadata
        roms = db.query(RomModel).all()
        rom_connector_ids = {r.connector_id for r in roms if r.connector_id}

        for rom in roms:
            metadata = rom.game_metadata or (rom.connector.game_metadata if rom.connector else None)
            games.append(_rom_to_list_item(rom, metadata))

        # Get connectors without ROMs (if including connectors)
        if include_connectors:
            connectors = db.query(ConnectorModel).filter(
                ~ConnectorModel.id.in_(rom_connector_ids) if rom_connector_ids else True
            ).all()

            for connector in connectors:
                games.append(_connector_to_list_item(connector))

        # Sort: trainable first, then playable, then connector-only, alphabetically within
        def sort_key(g):
            status_order = {"trainable": 0, "playable": 1, "connector_only": 2}
            return (status_order.get(g.status, 3), g.display_name.lower())

        games.sort(key=sort_key)
        return games
    finally:
        db.close()


@router.get("/roms/sync/status", response_model=SyncStatusResponse)
def get_sync_status():
    """Get current sync status with detailed breakdown."""
    db = SessionLocal()
    try:
        from sqlalchemy import func

        # Count ROMs
        total_roms = db.query(func.count(RomModel.id)).scalar() or 0
        roms_with_connector = db.query(func.count(RomModel.id)).filter(
            RomModel.connector_id.isnot(None)
        ).scalar() or 0
        roms_without_connector = total_roms - roms_with_connector

        # Count connectors
        total_connectors = db.query(func.count(ConnectorModel.id)).scalar() or 0
        db.query(func.count(ConnectorModel.id)).filter(
            ConnectorModel.metadata_id.isnot(None)
        ).scalar() or 0

        # Get connector IDs that have ROMs linked to them
        rom_connector_ids = db.query(RomModel.connector_id).filter(
            RomModel.connector_id.isnot(None)
        ).all()
        rom_connector_ids_set = {r.connector_id for r in rom_connector_ids}
        connectors_without_rom = db.query(func.count(ConnectorModel.id)).filter(
            ~ConnectorModel.id.in_(rom_connector_ids_set) if rom_connector_ids_set else True
        ).scalar() or 0

        # Metadata stats
        with_igdb = db.query(func.count(GameMetadataModel.id)).filter(
            GameMetadataModel.igdb_id.isnot(None)
        ).scalar() or 0
        with_name = db.query(func.count(GameMetadataModel.id)).filter(
            GameMetadataModel.name.isnot(None)
        ).scalar() or 0
        with_rating = db.query(func.count(GameMetadataModel.id)).filter(
            GameMetadataModel.rating.isnot(None)
        ).scalar() or 0
        with_developer = db.query(func.count(GameMetadataModel.id)).filter(
            GameMetadataModel.developer.isnot(None)
        ).scalar() or 0
        with_summary = db.query(func.count(GameMetadataModel.id)).filter(
            GameMetadataModel.summary.isnot(None)
        ).scalar() or 0
        with_year = db.query(func.count(GameMetadataModel.id)).filter(
            GameMetadataModel.release_date.isnot(None)
        ).scalar() or 0
        with_genres = db.query(func.count(GameMetadataModel.id)).filter(
            GameMetadataModel.genres.isnot(None)
        ).scalar() or 0

        # Thumbnail stats
        with_thumbnail = db.query(func.count(GameMetadataModel.id)).filter(
            GameMetadataModel.thumbnail_status == "synced"
        ).scalar() or 0

        # Missing thumbnails = items without IGDB cover that still need LibRetro lookup
        # (items with cover_url already tried IGDB during main sync)
        missing_thumbnails = db.query(func.count(GameMetadataModel.id)).filter(
            GameMetadataModel.thumbnail_status != "synced",
            GameMetadataModel.cover_url.is_(None),  # No IGDB cover available
            GameMetadataModel.name.isnot(None),
        ).scalar() or 0

        # Sync status stats
        synced = db.query(func.count(GameMetadataModel.id)).filter(
            GameMetadataModel.sync_status == "synced"
        ).scalar() or 0
        pending_connectors = db.query(func.count(ConnectorModel.id)).filter(
            ConnectorModel.metadata_id.is_(None)
        ).scalar() or 0
        pending_roms = db.query(func.count(RomModel.id)).filter(
            RomModel.metadata_id.is_(None),
            RomModel.connector_id.is_(None)
        ).scalar() or 0
        pending = pending_connectors + pending_roms
        failed = db.query(func.count(GameMetadataModel.id)).filter(
            GameMetadataModel.sync_status == "failed"
        ).scalar() or 0

        progress = rom_sync.sync_progress

        return SyncStatusResponse(
            is_syncing=rom_sync.is_syncing,
            current=progress.get("current"),
            completed=progress.get("completed", 0),
            # Game counts
            total=total_roms + connectors_without_rom,
            total_connectors=total_connectors,
            total_roms=total_roms,
            trainable=roms_with_connector,
            playable_only=roms_without_connector,
            connector_only=connectors_without_rom,
            # Sync status
            synced=synced,
            pending=pending,
            failed=failed,
            # Metadata coverage
            with_igdb=with_igdb,
            with_name=with_name,
            with_year=with_year,
            with_rating=with_rating,
            with_developer=with_developer,
            with_summary=with_summary,
            with_genres=with_genres,
            # Thumbnail
            with_thumbnail=with_thumbnail,
            missing_thumbnails=missing_thumbnails,
        )
    finally:
        db.close()


@router.post("/roms/sync")
def trigger_sync(
    background_tasks: BackgroundTasks,
    include_unmatched_connectors: bool = Query(
        False,
        description="Also sync metadata for connectors without ROM files"
    ),
):
    """Trigger metadata sync for all pending items."""
    if rom_sync.is_syncing:
        raise HTTPException(status_code=409, detail="Sync already in progress")

    background_tasks.add_task(
        rom_sync.sync_all_pending,
        include_unmatched_connectors=include_unmatched_connectors
    )
    return {"message": "Sync started"}


@router.post("/roms/sync/thumbnails")
def resync_thumbnails(background_tasks: BackgroundTasks):
    """Re-sync thumbnails from LibRetro for items where IGDB has no cover."""
    if rom_sync.is_syncing:
        raise HTTPException(status_code=409, detail="Sync already in progress")

    # Count items that sync_missing_thumbnails will actually process:
    # Items with name, no thumbnail yet, and no IGDB cover
    db = SessionLocal()
    try:
        count = db.query(GameMetadataModel).filter(
            GameMetadataModel.name.isnot(None),
            GameMetadataModel.thumbnail_status != "synced",
            GameMetadataModel.cover_url.is_(None),  # No IGDB cover - will try LibRetro
        ).count()
    finally:
        db.close()

    if count == 0:
        return {"message": "No items need LibRetro thumbnail lookup", "count": 0}

    background_tasks.add_task(rom_sync.sync_missing_thumbnails)
    return {"message": f"LibRetro thumbnail lookup started for {count} items", "count": count}


@router.post("/roms/import")
async def import_roms(request: RomImportRequest, background_tasks: BackgroundTasks):
    """
    Import ROMs from a directory.
    Registers new ROMs and triggers background sync for metadata/thumbnails.
    """
    import_path = request.path
    if not import_path:
        config = load_config()
        import_path = config.roms_path

    if not import_path:
        raise HTTPException(
            status_code=400, detail="Import path not provided and no default configured"
        )

    # Import into stable-retro (copies ROM files that match known hashes)
    count = await asyncio.to_thread(rom_scanner.import_roms, import_path)

    # Scan and register new ROMs + connectors
    items_to_sync = await rom_sync.scan_and_register_roms(user_roms_path=import_path)

    # Trigger background sync for metadata and thumbnails
    if items_to_sync:
        background_tasks.add_task(rom_sync.sync_all_pending)

    return {
        "message": f"Import completed. {count} ROM(s) imported, {len(items_to_sync)} queued for metadata sync.",
        "imported": count,
        "queued_for_sync": len(items_to_sync),
        "syncing": len(items_to_sync) > 0,
    }


@router.get("/roms/import/stream")
async def import_roms_stream(path: str | None = None, skip_retro_import: bool = False):
    """
    SSE endpoint for streaming import progress.
    Returns real-time progress updates during ROM import.
    """
    import time

    print(f"[SSE] import_roms_stream called with path={path}, skip_retro_import={skip_retro_import}")

    import_path = path
    if not import_path:
        config = load_config()
        import_path = config.roms_path
        print(f"[SSE] Using config roms_path: {import_path}")

    if not import_path:
        print("[SSE] ERROR: No import path provided")

        async def error_stream() -> AsyncGenerator[dict, None]:
            yield {"event": "error", "data": json.dumps({"message": "Import path not provided"})}

        return EventSourceResponse(error_stream())

    print(f"[SSE] Starting import stream for path: {import_path}")

    async def import_stream() -> AsyncGenerator[dict, None]:
        progress_queue: asyncio.Queue[dict] = asyncio.Queue()

        def make_callback(phase: str):
            """Create a progress callback that puts events into the queue."""

            def callback(current: int, total: int, message: str):
                try:
                    progress_queue.put_nowait({
                        "event": "progress",
                        "data": json.dumps({
                            "phase": phase,
                            "current": current,
                            "total": total,
                            "message": message,
                        }),
                    })
                except Exception as e:
                    print(f"[SSE] Progress queue error: {e}")

            return callback

        try:
            # Phase 1: Import into stable-retro (optional)
            count = 0
            if skip_retro_import:
                print("[SSE] Phase 1: SKIPPED (skip_retro_import=True)")
                yield {
                    "event": "start",
                    "data": json.dumps({"phase": "import", "message": "Skipping stable-retro import..."}),
                }
                yield {
                    "event": "complete",
                    "data": json.dumps({"phase": "import", "result": {"imported": 0, "skipped": True}}),
                }
            else:
                print("[SSE] Phase 1: Starting stable-retro import...")
                start_time = time.time()
                yield {
                    "event": "start",
                    "data": json.dumps({"phase": "import", "message": "Importing ROMs into stable-retro..."}),
                }
                count = await asyncio.to_thread(rom_scanner.import_roms, import_path)
                elapsed = time.time() - start_time
                print(f"[SSE] Phase 1 complete: imported {count} ROMs in {elapsed:.2f}s")
                yield {
                    "event": "complete",
                    "data": json.dumps({"phase": "import", "result": {"imported": count}}),
                }

            # Phase 2: Scan connectors
            print("[SSE] Phase 2: Starting connector scan...")
            start_time = time.time()
            yield {
                "event": "start",
                "data": json.dumps({"phase": "scan_connectors", "message": "Scanning stable-retro connectors..."}),
            }

            async def scan_connectors_with_progress():
                loop = asyncio.get_event_loop()
                callback = make_callback("scan_connectors")

                def run_scan():
                    print("[SSE] Running list_connectors in thread...")
                    result = rom_scanner.list_connectors(progress_callback=callback)
                    print(f"[SSE] list_connectors returned {len(result)} connectors")
                    return result

                return await loop.run_in_executor(None, run_scan)

            connectors = await scan_connectors_with_progress()
            elapsed = time.time() - start_time
            print(f"[SSE] Phase 2 complete: found {len(connectors)} connectors in {elapsed:.2f}s")

            # Drain progress queue
            while not progress_queue.empty():
                try:
                    yield progress_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

            yield {
                "event": "complete",
                "data": json.dumps({"phase": "scan_connectors", "result": {"count": len(connectors)}}),
            }

            # Phase 3: Scan user ROM folder
            print(f"[SSE] Phase 3: Starting folder scan of {import_path}...")
            start_time = time.time()
            yield {
                "event": "start",
                "data": json.dumps({"phase": "scan_folder", "message": f"Scanning ROM folder: {import_path}"}),
            }

            async def scan_folder_with_progress():
                loop = asyncio.get_event_loop()
                callback = make_callback("scan_folder")

                def run_scan():
                    print("[SSE] Running scan_rom_folder in thread...")
                    result = rom_scanner.scan_rom_folder(import_path, progress_callback=callback)
                    print(f"[SSE] scan_rom_folder returned {len(result)} ROMs")
                    return result

                return await loop.run_in_executor(None, run_scan)

            user_roms = await scan_folder_with_progress()
            elapsed = time.time() - start_time
            print(f"[SSE] Phase 3 complete: found {len(user_roms)} user ROMs in {elapsed:.2f}s")

            # Drain progress queue
            while not progress_queue.empty():
                try:
                    yield progress_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

            yield {
                "event": "complete",
                "data": json.dumps({"phase": "scan_folder", "result": {"count": len(user_roms)}}),
            }

            # Phase 4: Register in database
            print("[SSE] Phase 4: Starting database registration...")
            start_time = time.time()
            yield {
                "event": "start",
                "data": json.dumps({"phase": "register", "message": "Registering in database..."}),
            }

            items_to_sync = await rom_sync.scan_and_register_roms(
                user_roms_path=import_path,
                connectors=connectors,
                user_roms=user_roms,
            )
            elapsed = time.time() - start_time
            print(f"[SSE] Phase 4 complete: {len(items_to_sync)} items to sync in {elapsed:.2f}s")

            yield {
                "event": "complete",
                "data": json.dumps({"phase": "register", "result": {"queued_for_sync": len(items_to_sync)}}),
            }

            # Start background sync if needed
            if items_to_sync:
                print(f"[SSE] Starting background sync for {len(items_to_sync)} items...")
                asyncio.create_task(_run_background_sync())

            # Final done event
            print("[SSE] All phases complete, sending done event")
            yield {
                "event": "done",
                "data": json.dumps({
                    "imported": count,
                    "connectors": len(connectors),
                    "user_roms": len(user_roms),
                    "queued_for_sync": len(items_to_sync),
                    "syncing": len(items_to_sync) > 0,
                }),
            }

        except Exception as e:
            import traceback
            print(f"[SSE] ERROR: {e}")
            print(f"[SSE] Traceback: {traceback.format_exc()}")
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(import_stream())


async def _run_background_sync():
    """Run metadata sync in background."""
    try:
        await rom_sync.sync_all_pending()
    except Exception as e:
        print(f"[SYNC] Background sync error: {e}")


@router.post("/roms/scan")
async def scan_roms(background_tasks: BackgroundTasks):
    """
    Scan stable-retro for connectors and user's ROM folder.
    Registers new items and triggers background sync for metadata/thumbnails.
    """
    config = load_config()
    user_roms_path = config.roms_path if config.roms_path else None

    items_to_sync = await rom_sync.scan_and_register_roms(user_roms_path=user_roms_path)

    if items_to_sync:
        background_tasks.add_task(rom_sync.sync_all_pending)

    return {
        "message": f"Scan completed. {len(items_to_sync)} item(s) queued for metadata sync.",
        "queued_for_sync": len(items_to_sync),
        "syncing": len(items_to_sync) > 0,
    }


@router.get("/roms/{item_id}", response_model=GameResponse)
def get_game(item_id: str):
    """Get complete game details by ID (can be ROM ID or connector ID)."""
    db = SessionLocal()
    try:
        # Try to find as ROM first
        rom = db.query(RomModel).filter(RomModel.id == item_id).first()
        if rom:
            metadata = rom.game_metadata or (rom.connector.game_metadata if rom.connector else None)
            return _rom_to_full_response(rom, metadata)

        # Try to find as connector
        connector = db.query(ConnectorModel).filter(ConnectorModel.id == item_id).first()
        if connector:
            return _connector_to_full_response(connector)

        raise HTTPException(status_code=404, detail="Game not found")
    finally:
        db.close()


@router.get("/roms/{item_id}/states")
def get_game_states(item_id: str):
    """Get available save states for a game."""
    db = SessionLocal()
    try:
        # Try to find as ROM with connector
        rom = db.query(RomModel).filter(RomModel.id == item_id).first()
        if rom and rom.connector:
            return rom.connector.states or []

        # Try to find as connector
        connector = db.query(ConnectorModel).filter(ConnectorModel.id == item_id).first()
        if connector:
            # Refresh states from stable-retro
            details = rom_scanner.get_game_details(connector.id)
            if details:
                connector.states = details.get("states", [])
                db.commit()
            return connector.states or []

        raise HTTPException(status_code=404, detail="Game not found")
    finally:
        db.close()


@router.post("/roms/{item_id}/sync")
async def sync_single_game(item_id: str, force: bool = False):
    """Sync metadata for a specific game."""
    from ..services.rom_sync import clean_game_name_for_search

    db = SessionLocal()
    try:
        # Find item (ROM or connector)
        rom = db.query(RomModel).filter(RomModel.id == item_id).first()
        connector = db.query(ConnectorModel).filter(ConnectorModel.id == item_id).first() if not rom else None

        if not rom and not connector:
            raise HTTPException(status_code=404, detail="Game not found")

        item = rom or connector
        item_type = "rom" if rom else "connector"

        # Skip if already synced (unless force)
        if not force and item.metadata_id:
            return {"message": "Already synced", "status": "synced"}

        # Determine search name
        if item_type == "rom" and rom.connector_id:
            search_name = clean_game_name_for_search(rom.connector_id)
        elif item_type == "connector":
            search_name = clean_game_name_for_search(connector.id)
        else:
            search_name = item.display_name

        config = load_config()
        if not config.igdb_client_id or not config.igdb_client_secret:
            raise HTTPException(status_code=400, detail="IGDB credentials not configured")

        success = await rom_sync._sync_metadata_for_item(
            item_type, item_id, item.system, search_name,
            config.igdb_client_id, config.igdb_client_secret,
        )

        if success:
            return {"message": "Sync complete", "status": "synced"}
        raise HTTPException(status_code=500, detail="Sync failed")
    finally:
        db.close()


@router.post("/roms/{item_id}/resync")
async def resync_game_with_correction(item_id: str, request: ResyncRequest):
    """Manual correction: Re-sync game with specific IGDB ID or thumbnail name."""
    if request.igdb_id:
        success = await rom_sync.resync_with_igdb_id(item_id, request.igdb_id)
        if not success:
            raise HTTPException(status_code=500, detail="IGDB resync failed")

    return {"message": "Resync complete"}


@router.get("/roms/{item_id}/search-igdb")
async def search_igdb_for_game(item_id: str, query: str | None = None):
    """Search IGDB for manual correction candidates."""
    candidates = await rom_sync.search_igdb_candidates(item_id, query)
    return {"candidates": candidates}


# =============================================================================
# Helpers
# =============================================================================


def _get_thumbnail_url(metadata: GameMetadataModel | None) -> str | None:
    """Get thumbnail URL from metadata."""
    if not metadata:
        return None
    if metadata.thumbnail_path:
        return f"/files/{metadata.thumbnail_path}"
    return None


def _rom_to_list_item(rom: RomModel, metadata: GameMetadataModel | None) -> GameListItem:
    """Convert ROM to list item."""
    has_connector = rom.connector_id is not None
    connector = rom.connector

    return GameListItem(
        id=rom.id,
        system=rom.system,
        display_name=metadata.name if metadata else rom.display_name,
        has_rom=True,
        has_connector=has_connector,
        status=derive_game_status(True, has_connector),
        connector_id=rom.connector_id,
        states=connector.states if connector else [],
        sync_status=metadata.sync_status if metadata else "pending",
        rating=metadata.rating if metadata else None,
        genres=metadata.genres or [] if metadata else [],
        release_date=metadata.release_date if metadata else None,
        developer=metadata.developer if metadata else None,
        thumbnail_url=_get_thumbnail_url(metadata),
    )


def _connector_to_list_item(connector: ConnectorModel) -> GameListItem:
    """Convert connector (without ROM) to list item."""
    metadata = connector.game_metadata

    return GameListItem(
        id=connector.id,
        system=connector.system,
        display_name=metadata.name if metadata else connector.display_name,
        has_rom=False,
        has_connector=True,
        status=GameStatus.CONNECTOR_ONLY,
        connector_id=connector.id,
        states=connector.states or [],
        sync_status=metadata.sync_status if metadata else "pending",
        rating=metadata.rating if metadata else None,
        genres=metadata.genres or [] if metadata else [],
        release_date=metadata.release_date if metadata else None,
        developer=metadata.developer if metadata else None,
        thumbnail_url=_get_thumbnail_url(metadata),
    )


def _rom_to_full_response(rom: RomModel, metadata: GameMetadataModel | None) -> GameResponse:
    """Convert ROM to full response."""
    has_connector = rom.connector_id is not None
    connector = rom.connector

    return GameResponse(
        id=rom.id,
        system=rom.system,
        display_name=metadata.name if metadata else rom.display_name,
        has_rom=True,
        has_connector=has_connector,
        status=derive_game_status(True, has_connector),
        connector_id=rom.connector_id,
        states=connector.states if connector else [],
        sync_status=metadata.sync_status if metadata else "pending",
        sync_error=metadata.sync_error if metadata else None,
        synced_at=metadata.updated_at if metadata else None,
        igdb_id=metadata.igdb_id if metadata else None,
        igdb_name=metadata.name if metadata else None,
        summary=metadata.summary if metadata else None,
        storyline=metadata.storyline if metadata else None,
        rating=metadata.rating if metadata else None,
        rating_count=metadata.rating_count if metadata else None,
        genres=metadata.genres or [] if metadata else [],
        themes=metadata.themes or [] if metadata else [],
        game_modes=metadata.game_modes or [] if metadata else [],
        player_perspectives=metadata.player_perspectives or [] if metadata else [],
        platforms=metadata.platforms or [] if metadata else [],
        release_date=metadata.release_date if metadata else None,
        developer=metadata.developer if metadata else None,
        publisher=metadata.publisher if metadata else None,
        cover_url=metadata.cover_url if metadata else None,
        screenshot_urls=metadata.screenshot_urls or [] if metadata else [],
        thumbnail_url=_get_thumbnail_url(metadata),
        thumbnail_status=metadata.thumbnail_status if metadata else "pending",
    )


def _connector_to_full_response(connector: ConnectorModel) -> GameResponse:
    """Convert connector (without ROM) to full response."""
    metadata = connector.game_metadata

    return GameResponse(
        id=connector.id,
        system=connector.system,
        display_name=metadata.name if metadata else connector.display_name,
        has_rom=False,
        has_connector=True,
        status=GameStatus.CONNECTOR_ONLY,
        connector_id=connector.id,
        states=connector.states or [],
        sync_status=metadata.sync_status if metadata else "pending",
        sync_error=metadata.sync_error if metadata else None,
        synced_at=metadata.updated_at if metadata else None,
        igdb_id=metadata.igdb_id if metadata else None,
        igdb_name=metadata.name if metadata else None,
        summary=metadata.summary if metadata else None,
        storyline=metadata.storyline if metadata else None,
        rating=metadata.rating if metadata else None,
        rating_count=metadata.rating_count if metadata else None,
        genres=metadata.genres or [] if metadata else [],
        themes=metadata.themes or [] if metadata else [],
        game_modes=metadata.game_modes or [] if metadata else [],
        player_perspectives=metadata.player_perspectives or [] if metadata else [],
        platforms=metadata.platforms or [] if metadata else [],
        release_date=metadata.release_date if metadata else None,
        developer=metadata.developer if metadata else None,
        publisher=metadata.publisher if metadata else None,
        cover_url=metadata.cover_url if metadata else None,
        screenshot_urls=metadata.screenshot_urls or [] if metadata else [],
        thumbnail_url=_get_thumbnail_url(metadata),
        thumbnail_status=metadata.thumbnail_status if metadata else "pending",
    )
