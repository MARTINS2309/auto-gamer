"""
ROM Sync Orchestrator.

Handles the complete sync pipeline with separated tables:
1. Connectors table: Sync from stable-retro
2. ROMs table: Scan user's ROM folder
3. Metadata table: Fetch from IGDB, link to connectors/ROMs via hash

Designed for:
- Initial sync when ROMs are added
- Manual re-sync triggered by user
- Background batch processing
"""

import asyncio
import hashlib
import re
from pathlib import Path
from typing import Any

from ..models.db import ConnectorModel, GameMetadataModel, RomModel, SessionLocal
from ..routers.config import load_config
from .igdb import (
    _RATE_LIMIT_DELAY,
    DiscoveryRequest,
    GameMetadata,
    _rate_limit_lock,
    batch_fetch_metadata,
    discover_games_batch,
    get_game_by_id,
    get_igdb_platform,
    search_game,
)
from .rom_scanner import rom_scanner

# =============================================================================
# Constants
# =============================================================================

DATA_DIR = Path(__file__).parent.parent.parent / "data"
THUMBNAIL_CACHE_DIR = DATA_DIR / "thumbnail_cache"
THUMBNAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Name Cleaning
# =============================================================================

GAME_NAME_ALIASES = {
    "CastlevaniaTheNewGeneration": "Castlevania Bloodlines",
    "SuperMarioBros2Japan": "Super Mario Bros The Lost Levels",
    "RoboCop": "RoboCop",
    "QuackShot": "QuackShot Starring Donald Duck",
    "ActRaiser": "ActRaiser",
    "BeamRider": "Beamrider",
    "RiverRaid": "River Raid",
    "MsPacman": "Ms. Pac-Man",
    "JamesBond": "James Bond 007",
    "ChackNPop": "Chack'n Pop",
    "TwinBee": "TwinBee",
    "XKaliber2097": "X-Kaliber 2097",
    "ChaseHQII": "Chase H.Q. II",
    "SolDeace": "Sol-Deace",
    "BioMetal": "BioMetal",
}


def clean_game_name_for_search(game_id: str) -> str:
    """Convert game ID to searchable name."""
    base_name = re.sub(r"-[A-Za-z0-9]+-v\d+$", "", game_id)

    for pattern, replacement in GAME_NAME_ALIASES.items():
        if pattern.lower() in base_name.lower().replace(" ", ""):
            return replacement

    name = base_name
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    name = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", name)
    name = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", name)

    # Apostrophe patterns
    name = re.sub(r"(\w)shn\b", r"\1sh'n", name)
    name = re.sub(r"(\w)shn ", r"\1sh'n ", name)
    name = re.sub(r"(\w)sn\b", r"\1s 'n", name)
    name = re.sub(r"(\w)sn ", r"\1s 'n ", name)
    name = re.sub(r"(\w)ckn\b", r"\1ck'n", name)
    name = re.sub(r"(\w)ckn ", r"\1ck'n ", name)
    name = re.sub(r"\bPopn\b", "Pop'n", name)

    # Compound words
    name = re.sub(r"\bRobo Cop\b", "RoboCop", name)
    name = re.sub(r"\bQuack Shot\b", "QuackShot", name)
    name = re.sub(r"\bAct Raiser\b", "ActRaiser", name)
    name = re.sub(r"\bTwin Bee\b", "TwinBee", name)
    name = re.sub(r"\bBio Metal\b", "BioMetal", name)

    return name


def clean_display_name(game_id: str) -> str:
    """Clean game ID into display name (without apostrophe/compound fixes)."""
    name = re.sub(r"-[A-Za-z0-9]+-v\d+$", "", game_id)
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    name = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", name)
    name = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", name)
    return name


# =============================================================================
# Thumbnail Helpers
# =============================================================================


def get_thumbnail_cache_key(system: str, game: str, thumb_type: str = "boxart") -> str:
    """Generate a unique cache key for a thumbnail."""
    key = f"{system}:{game}:{thumb_type}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def get_thumbnail_cache_path(cache_key: str) -> Path:
    """Get the cache file path for a key."""
    return THUMBNAIL_CACHE_DIR / f"{cache_key}.png"


# =============================================================================
# Sync Orchestrator
# =============================================================================


class RomSyncOrchestrator:
    """
    Orchestrates ROM sync operations with separated tables.

    Usage:
        orchestrator = RomSyncOrchestrator()
        await orchestrator.sync_connectors()  # Sync stable-retro connectors
        await orchestrator.sync_roms("/path/to/roms")  # Sync user's ROM files
        await orchestrator.sync_all_metadata()  # Fetch IGDB metadata
    """

    def __init__(self):
        self._is_syncing = False
        self._sync_progress = {"total": 0, "completed": 0, "current": None}

    @property
    def is_syncing(self) -> bool:
        return self._is_syncing

    @property
    def sync_progress(self) -> dict[str, Any]:
        return self._sync_progress.copy()

    # =========================================================================
    # Connector Sync (from stable-retro)
    # =========================================================================

    async def sync_connectors(
        self, connectors: list[dict[str, Any]] | None = None,
        progress_callback: Any | None = None,
    ) -> dict[str, int]:
        """
        Sync connectors from stable-retro.
        Populates the connectors table with game definitions.
        """
        db = SessionLocal()
        try:
            if connectors is None:
                connectors = await asyncio.to_thread(rom_scanner.list_connectors)
            print(f"[SYNC] Processing {len(connectors)} stable-retro connectors")

            existing_ids = {c.id for c in db.query(ConnectorModel.id).all()}
            stats = {"added": 0, "updated": 0, "skipped": 0}
            total = len(connectors)

            for i, connector_data in enumerate(connectors):
                connector_id = connector_data["id"]
                system = connector_data["system"]
                sha1_hash = connector_data.get("sha1_hash")
                has_rom = connector_data.get("has_rom", False)
                states = connector_data.get("states", [])
                display_name = connector_data.get("display_name", clean_display_name(connector_id))

                if connector_id in existing_ids:
                    # Update existing connector
                    connector = db.query(ConnectorModel).filter(ConnectorModel.id == connector_id).first()
                    if connector:
                        changed = False
                        if connector.has_rom != has_rom:
                            connector.has_rom = has_rom
                            changed = True
                        if connector.states != states:
                            connector.states = states
                            changed = True
                        if sha1_hash and connector.sha1_hash != sha1_hash:
                            connector.sha1_hash = sha1_hash
                            changed = True
                        if changed:
                            stats["updated"] += 1
                        else:
                            stats["skipped"] += 1
                else:
                    # Create new connector
                    connector = ConnectorModel(
                        id=connector_id,
                        system=system,
                        display_name=display_name,
                        sha1_hash=sha1_hash,
                        states=states,
                        has_rom=has_rom,
                    )
                    db.add(connector)
                    stats["added"] += 1

                # Progress callback
                if progress_callback and (i + 1) % 100 == 0:
                    await progress_callback(i + 1, total, f"Processed {i + 1}/{total} connectors")

            db.commit()
            print(f"[SYNC] Connectors: {stats}")
            return stats
        finally:
            db.close()

    # =========================================================================
    # ROM Sync (user's files)
    # =========================================================================

    async def sync_roms(
        self,
        user_roms_path: str | None = None,
        user_roms: list[dict[str, Any]] | None = None,
        progress_callback: Any | None = None,
    ) -> dict[str, int]:
        """
        Sync user's ROM files.
        Scans the folder and populates the roms table.
        Links to connectors via SHA1 hash.
        """
        db = SessionLocal()
        try:
            if user_roms is None and user_roms_path:
                user_roms = await asyncio.to_thread(rom_scanner.scan_rom_folder, user_roms_path)
            elif user_roms is None:
                user_roms = []

            print(f"[SYNC] Processing {len(user_roms)} user ROM files")

            existing_hashes = {r.sha1_hash: r for r in db.query(RomModel).all() if r.sha1_hash}
            # Get known hashes from stable-retro for connector matching
            known_hashes = await asyncio.to_thread(self._get_known_hashes)

            # Also build connector lookup by SHA1
            connector_by_hash: dict[str, str] = {}
            for connector in db.query(ConnectorModel).all():
                if connector.sha1_hash:
                    connector_by_hash[str(connector.sha1_hash)] = connector.id

            stats = {"added": 0, "updated": 0, "linked": 0, "skipped": 0}
            total = len(user_roms)

            for i, rom_data in enumerate(user_roms):
                sha1_hash = rom_data.get("sha1_hash")
                system = rom_data["system"]
                file_path = rom_data.get("file_path")
                file_name = rom_data.get("file_name", Path(file_path).name if file_path else None)
                file_size = rom_data.get("file_size")
                display_name = rom_data.get("display_name", rom_data.get("name", "Unknown"))

                # Use SHA1 hash as base for ROM ID
                rom_id = f"{sha1_hash[:8]}-{system}" if sha1_hash else rom_data["id"]

                # Try to find matching connector via hash
                connector_id = None
                if sha1_hash:
                    # First check our connector table
                    if sha1_hash in connector_by_hash:
                        connector_id = connector_by_hash[sha1_hash]
                    # Fallback to stable-retro known hashes
                    elif sha1_hash in known_hashes:
                        connector_id = known_hashes[sha1_hash]

                # Check if we already have this ROM by hash
                if sha1_hash and sha1_hash in existing_hashes:
                    rom = existing_hashes[sha1_hash]
                    changed = False
                    if file_path and rom.file_path != file_path:
                        rom.file_path = file_path
                        changed = True
                    if connector_id and rom.connector_id != connector_id:
                        rom.connector_id = connector_id
                        stats["linked"] += 1
                        changed = True
                    if changed:
                        stats["updated"] += 1
                    else:
                        stats["skipped"] += 1
                else:
                    # Create new ROM
                    rom = RomModel(
                        id=rom_id,
                        sha1_hash=sha1_hash,
                        system=system,
                        file_path=file_path,
                        file_name=file_name,
                        file_size=file_size,
                        display_name=display_name,
                        connector_id=connector_id,
                    )
                    db.add(rom)
                    if sha1_hash:
                        existing_hashes[sha1_hash] = rom
                    stats["added"] += 1
                    if connector_id:
                        stats["linked"] += 1

                # Progress callback every 10 items
                if progress_callback and (i + 1) % 10 == 0:
                    await progress_callback(i + 1, total, f"Processed {i + 1}/{total} ROMs")

            db.commit()
            print(f"[SYNC] ROMs: {stats}")
            return stats
        finally:
            db.close()

    def _get_known_hashes(self) -> dict[str, str]:
        """Get SHA1 -> connector_id mapping from stable-retro."""
        try:
            import retro
            known = retro.data.get_known_hashes()
            # known is dict of sha1 -> (game_id, ext, path)
            return {sha1: game_id for sha1, (game_id, _, _) in known.items()}
        except Exception as e:
            print(f"[SYNC] Could not get known hashes: {e}")
            return {}

    # =========================================================================
    # Metadata Sync (IGDB)
    # =========================================================================

    async def sync_all_metadata(
        self,
        batch_size: int = 10,
        include_unmatched_connectors: bool = False,
        progress_callback: Any | None = None,
    ) -> dict[str, int]:
        """
        Sync metadata for ROMs (and optionally connectors without ROMs).

        Uses two-phase IGDB approach:
        1. Discovery: Search IGDB for game IDs (rate-limited, sequential)
        2. Batch Fetch: Fetch full metadata for all discovered IDs (batched)

        Args:
            batch_size: Number of items per metadata batch request
            include_unmatched_connectors: If True, also sync connectors that don't have ROM files
            progress_callback: Optional callback for progress updates
        """
        if self._is_syncing:
            return {"error": "Sync already in progress"}  # type: ignore[dict-item]

        self._is_syncing = True
        stats = {"synced": 0, "failed": 0, "not_found": 0}

        try:
            config = load_config()
            if not config.igdb_client_id or not config.igdb_client_secret:
                print("[SYNC] IGDB credentials not configured, skipping metadata sync")
                return stats

            db = SessionLocal()

            # Collect items needing sync
            items_to_sync: list[tuple[str, str, str, str]] = []  # (type, id, system, search_name)

            # Priority 1: ROMs linked to connectors (trainable games)
            roms_with_connectors = db.query(RomModel).filter(
                RomModel.metadata_id.is_(None),
                RomModel.connector_id.isnot(None)
            ).all()
            for r in roms_with_connectors:
                connector = db.query(ConnectorModel).filter(ConnectorModel.id == r.connector_id).first()
                search_name = clean_game_name_for_search(connector.id) if connector else r.display_name
                items_to_sync.append(("rom", r.id, r.system, search_name))

            # Priority 2: ROMs without connectors (playable only)
            roms_without_connectors = db.query(RomModel).filter(
                RomModel.metadata_id.is_(None),
                RomModel.connector_id.is_(None)
            ).all()
            for r in roms_without_connectors:
                items_to_sync.append(("rom", r.id, r.system, r.display_name))

            # Priority 3: Connectors without ROMs (only if enabled)
            if include_unmatched_connectors:
                linked_connector_ids = {r.connector_id for r in db.query(RomModel.connector_id).filter(
                    RomModel.connector_id.isnot(None)
                ).all()}

                connectors_without_roms = db.query(ConnectorModel).filter(
                    ConnectorModel.metadata_id.is_(None),
                    ~ConnectorModel.id.in_(linked_connector_ids) if linked_connector_ids else True
                ).all()
                for c in connectors_without_roms:
                    items_to_sync.append(("connector", c.id, c.system, clean_game_name_for_search(c.id)))

            db.close()

            if not items_to_sync:
                print("[SYNC] No items need metadata sync")
                return stats

            self._sync_progress = {"total": len(items_to_sync), "completed": 0, "current": "Discovery phase"}  # type: ignore[dict-item]
            print(f"[SYNC] Starting two-phase metadata sync for {len(items_to_sync)} items")
            print("[SYNC] Items breakdown:")
            rom_count = sum(1 for t, _, _, _ in items_to_sync if t == "rom")
            connector_count = sum(1 for t, _, _, _ in items_to_sync if t == "connector")
            print(f"[SYNC]   - ROMs: {rom_count}")
            print(f"[SYNC]   - Connectors: {connector_count}")

            # =================================================================
            # PHASE 1: Discovery - Find IGDB IDs for all items
            # =================================================================
            print("[SYNC] ========== PHASE 1: DISCOVERY ==========")
            if progress_callback:
                await progress_callback("metadata", 0, len(items_to_sync), "Phase 1: Discovering IGDB IDs...")

            discovery_requests = [
                DiscoveryRequest(
                    search_name=search_name,
                    platform_filter=get_igdb_platform(system),
                    internal_id=f"{item_type}:{item_id}",
                    system=system,
                )
                for item_type, item_id, system, search_name in items_to_sync
            ]

            discovery_results = await discover_games_batch(
                discovery_requests,
                config.igdb_client_id,
                config.igdb_client_secret,
                try_variants=True,
            )

            # Build mapping of igdb_id -> list of internal_ids (multiple items may map to same IGDB game)
            igdb_id_to_items: dict[int, list[str]] = {}
            for internal_id, result in discovery_results.items():
                if result.igdb_id:
                    if result.igdb_id not in igdb_id_to_items:
                        igdb_id_to_items[result.igdb_id] = []
                    igdb_id_to_items[result.igdb_id].append(internal_id)
                elif result.not_found:
                    stats["not_found"] += 1

            unique_igdb_ids = list(igdb_id_to_items.keys())
            print("[SYNC] Phase 1 complete:")
            print(f"[SYNC]   - discovery_results count: {len(discovery_results)}")
            print(f"[SYNC]   - discovery_results sample keys: {list(discovery_results.keys())[:3]}")
            print(f"[SYNC]   - igdb_id_to_items count: {len(igdb_id_to_items)}")
            print(f"[SYNC]   - Unique IGDB IDs found: {len(unique_igdb_ids)}")
            print(f"[SYNC]   - Not found in IGDB: {stats['not_found']}")
            errors_in_discovery = sum(1 for r in discovery_results.values() if r.error)
            print(f"[SYNC]   - Errors during discovery: {errors_in_discovery}")
            # Show sample mappings to verify data flow
            for _i, (igdb_id, internal_ids) in enumerate(list(igdb_id_to_items.items())[:3]):
                print(f"[SYNC]   - Sample: igdb_id={igdb_id} -> {internal_ids[:2]}")

            # =================================================================
            # PHASE 2: Batch Fetch - Get full metadata for discovered IDs
            # =================================================================
            print("[SYNC] ========== PHASE 2: BATCH FETCH ==========")
            if progress_callback:
                await progress_callback("metadata", 0, len(unique_igdb_ids), "Phase 2: Fetching metadata...")

            self._sync_progress["current"] = "Batch fetch phase"

            metadata_map: dict[int, GameMetadata | None] = {}
            if unique_igdb_ids:
                metadata_map = await batch_fetch_metadata(
                    unique_igdb_ids,
                    config.igdb_client_id,
                    config.igdb_client_secret,
                    batch_size=batch_size,
                )

            successful_fetches = sum(1 for v in metadata_map.values() if v is not None)
            failed_fetches = sum(1 for v in metadata_map.values() if v is None)
            print("[SYNC] Phase 2 complete:")
            print(f"[SYNC]   - metadata_map count: {len(metadata_map)}")
            print(f"[SYNC]   - metadata_map sample keys: {list(metadata_map.keys())[:5]}")
            print(f"[SYNC]   - Metadata fetched: {successful_fetches}")
            print(f"[SYNC]   - Fetch failures: {failed_fetches}")
            # Verify keys match between igdb_id_to_items and metadata_map
            matching_keys = set(igdb_id_to_items.keys()) & set(metadata_map.keys())
            print(f"[SYNC]   - Keys matching igdb_id_to_items: {len(matching_keys)}/{len(igdb_id_to_items)}")

            # =================================================================
            # PHASE 3: Store metadata and link to ROMs/connectors
            # =================================================================
            print("[SYNC] ========== PHASE 3: STORE METADATA ==========")
            if progress_callback:
                await progress_callback("metadata", 0, len(items_to_sync), "Phase 3: Storing metadata...")

            self._sync_progress["current"] = "Storing metadata"

            # Debug: Show Phase 3 inputs
            print("[SYNC:STORE] Phase 3 inputs:")
            print(f"[SYNC:STORE]   - metadata_map entries: {len(metadata_map)}")
            print(f"[SYNC:STORE]   - igdb_id_to_items entries: {len(igdb_id_to_items)}")
            print(f"[SYNC:STORE]   - items_to_sync count: {len(items_to_sync)}")

            # Debug: Show first few mappings
            for _i, (igdb_id, internal_ids) in enumerate(list(igdb_id_to_items.items())[:5]):
                print(f"[SYNC:STORE]   - igdb_id={igdb_id} -> internal_ids={internal_ids}")

            db = SessionLocal()
            processed_igdb_ids = 0  # Track for summary logging

            try:
                # Build lookup from internal_id to (type, id, system)
                item_lookup = {
                    f"{item_type}:{item_id}": (item_type, item_id, system)
                    for item_type, item_id, system, _ in items_to_sync
                }

                # Process each discovered IGDB game
                for igdb_id, igdb_metadata in metadata_map.items():
                    processed_igdb_ids += 1
                    if processed_igdb_ids <= 3:
                        print(f"[SYNC:STORE] Processing IGDB {igdb_id}: metadata={igdb_metadata is not None}")

                    if not igdb_metadata:
                        # Fetch failed for this ID
                        failed_items = igdb_id_to_items.get(igdb_id, [])
                        print(f"[SYNC:STORE] IGDB {igdb_id}: fetch failed, marking {len(failed_items)} items as failed")
                        for _internal_id in failed_items:
                            stats["failed"] += 1
                        continue

                    # Get the system from the first item (all should be same system for same IGDB ID)
                    internal_ids = igdb_id_to_items.get(igdb_id, [])
                    if processed_igdb_ids <= 3:
                        print(f"[SYNC:STORE]   igdb_id={igdb_id} (type={type(igdb_id).__name__}) -> internal_ids={internal_ids}")
                    if not internal_ids:
                        print(f"[SYNC:STORE] WARNING: IGDB {igdb_id} has no mapped items (keys sample: {list(igdb_id_to_items.keys())[:5]})")
                        continue

                    first_item = item_lookup.get(internal_ids[0])
                    if processed_igdb_ids <= 3:
                        print(f"[SYNC:STORE]   first_item={first_item}, lookup_keys_sample={list(item_lookup.keys())[:3]}")
                    if not first_item:
                        print(f"[SYNC:STORE] WARNING: Could not find item info for {internal_ids[0]}")
                        continue
                    _, _, system = first_item

                    # Check if we already have this metadata in DB (avoid duplicates)
                    existing_metadata = db.query(GameMetadataModel).filter(
                        GameMetadataModel.igdb_id == igdb_id,
                        GameMetadataModel.system == system,
                    ).first()

                    # Get item_id from first_item for game_id (legacy field, but NOT NULL in DB)
                    _, first_item_id, _ = first_item

                    if existing_metadata:
                        metadata_id = existing_metadata.id
                        print(f"[SYNC:STORE] IGDB {igdb_id} '{igdb_metadata.name}': using existing metadata (id={metadata_id})")
                    else:
                        # Create new metadata entry
                        new_metadata = GameMetadataModel(
                            game_id=first_item_id,  # Legacy field, but NOT NULL in DB
                            system=system,
                            igdb_id=igdb_metadata.igdb_id,
                            name=igdb_metadata.name,
                            summary=igdb_metadata.summary,
                            storyline=igdb_metadata.storyline,
                            rating=igdb_metadata.rating,
                            rating_count=igdb_metadata.rating_count,
                            genres=igdb_metadata.genres,
                            themes=igdb_metadata.themes,
                            game_modes=igdb_metadata.game_modes,
                            player_perspectives=igdb_metadata.player_perspectives,
                            platforms=igdb_metadata.platforms,
                            release_date=igdb_metadata.release_date,
                            developer=igdb_metadata.developer,
                            publisher=igdb_metadata.publisher,
                            cover_url=igdb_metadata.cover_url,
                            screenshot_urls=igdb_metadata.screenshot_urls,
                            sync_status="synced",
                            source="igdb",
                        )
                        db.add(new_metadata)
                        db.flush()
                        metadata_id = new_metadata.id
                        print(f"[SYNC:STORE] IGDB {igdb_id} '{igdb_metadata.name}': created new metadata (id={metadata_id})")

                    # Link all items that map to this IGDB ID
                    for internal_id in internal_ids:
                        item_info = item_lookup.get(internal_id)
                        if not item_info:
                            print(f"[SYNC:STORE] WARNING: Could not find item info for {internal_id}")
                            continue
                        item_type, item_id, _ = item_info

                        if item_type == "rom":
                            rom = db.query(RomModel).filter(RomModel.id == item_id).first()
                            if rom and not rom.metadata_id:
                                rom.metadata_id = metadata_id
                                stats["synced"] += 1
                                print(f"[SYNC:STORE]   Linked ROM '{item_id}' -> metadata {metadata_id}")
                            elif rom:
                                print(f"[SYNC:STORE]   ROM '{item_id}' already has metadata")
                            else:
                                print(f"[SYNC:STORE]   WARNING: ROM '{item_id}' not found in DB")
                        else:
                            connector = db.query(ConnectorModel).filter(ConnectorModel.id == item_id).first()
                            if connector and not connector.metadata_id:
                                connector.metadata_id = metadata_id
                                stats["synced"] += 1
                                print(f"[SYNC:STORE]   Linked connector '{item_id}' -> metadata {metadata_id}")
                            elif connector:
                                print(f"[SYNC:STORE]   Connector '{item_id}' already has metadata")
                            else:
                                print(f"[SYNC:STORE]   WARNING: Connector '{item_id}' not found in DB")

                db.commit()
                print("[SYNC:STORE] Database commit successful")
                print(f"[SYNC:STORE] Final stats: synced={stats['synced']}, failed={stats['failed']}, not_found={stats['not_found']}")
            except Exception as e:
                print(f"[SYNC:STORE] ERROR: Database error: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                db.rollback()
                raise
            finally:
                db.close()

            self._sync_progress["completed"] = len(items_to_sync)
            self._sync_progress["current"] = None
            print(f"[SYNC] Metadata sync complete: {stats}")
            print(f"[SYNC] Summary: processed {processed_igdb_ids} IGDB IDs from metadata_map")
            return stats

        finally:
            self._is_syncing = False

    async def _sync_metadata_for_item(
        self,
        item_type: str,
        item_id: str,
        system: str,
        search_name: str,
        client_id: str,
        client_secret: str,
    ) -> bool:
        """Sync metadata for a single connector or ROM."""
        db = SessionLocal()
        try:
            platform_filter = get_igdb_platform(system)
            print(f"[SYNC] Searching IGDB: {search_name} ({platform_filter})")

            async with _rate_limit_lock:
                await asyncio.sleep(_RATE_LIMIT_DELAY)
                result = await search_game(search_name, client_id, client_secret, platform_filter)

            if result.metadata:
                # Create or update metadata entry
                metadata = GameMetadataModel(
                    system=system,
                    igdb_id=result.metadata.igdb_id,
                    name=result.metadata.name,
                    summary=result.metadata.summary,
                    storyline=result.metadata.storyline,
                    rating=result.metadata.rating,
                    rating_count=result.metadata.rating_count,
                    genres=result.metadata.genres,
                    themes=result.metadata.themes,
                    game_modes=result.metadata.game_modes,
                    player_perspectives=result.metadata.player_perspectives,
                    platforms=result.metadata.platforms,
                    release_date=result.metadata.release_date,
                    developer=result.metadata.developer,
                    publisher=result.metadata.publisher,
                    cover_url=result.metadata.cover_url,
                    screenshot_urls=result.metadata.screenshot_urls,
                    sync_status="synced",
                    source="igdb",
                )
                db.add(metadata)
                db.flush()  # Get the ID

                # Link to connector or ROM
                if item_type == "connector":
                    connector = db.query(ConnectorModel).filter(ConnectorModel.id == item_id).first()
                    if connector:
                        connector.metadata_id = metadata.id
                else:
                    rom = db.query(RomModel).filter(RomModel.id == item_id).first()
                    if rom:
                        rom.metadata_id = metadata.id

                db.commit()

                # Note: Thumbnail sync is done in step 4 (sync_missing_thumbnails)
                print(f"[SYNC] IGDB found: {item_id} -> {result.metadata.name}")
                return True
            else:
                print(f"[SYNC] IGDB not found: {search_name}")
                return True  # Not an error, just no IGDB entry

        except Exception as e:
            print(f"[SYNC] Error syncing metadata for {item_id}: {e}")
            return False
        finally:
            db.close()

    async def _sync_thumbnail(self, db, metadata: GameMetadataModel) -> bool:
        """Fetch and cache thumbnail for metadata entry."""
        import httpx

        from ..routers.thumbnails import fetch_image, find_best_match, get_libretro_system

        try:
            # Try IGDB cover first
            if metadata.cover_url:
                print(f"[SYNC] Trying IGDB cover for metadata {metadata.id}")
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.get(metadata.cover_url)
                        if response.status_code == 200:
                            content_type = response.headers.get("content-type", "")
                            ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else "png"

                            cache_key = get_thumbnail_cache_key(metadata.system, str(metadata.id), "boxart")
                            cache_path = get_thumbnail_cache_path(cache_key)
                            cache_path = cache_path.with_suffix(f".{ext}")
                            cache_path.write_bytes(response.content)
                            metadata.thumbnail_path = f"thumbnail_cache/{cache_key}.{ext}"
                            metadata.thumbnail_status = "synced"
                            metadata.thumbnail_match_type = "igdb_cover"
                            print(f"[SYNC] IGDB cover cached for metadata {metadata.id}")
                            return True
                except Exception as e:
                    print(f"[SYNC] IGDB cover download failed for metadata {metadata.id}: {e}")

            # Fallback: Try LibRetro
            libretro_system = get_libretro_system(metadata.system)
            if libretro_system and metadata.name:
                print(f"[SYNC] Trying LibRetro for: {metadata.name}")

                best_match, match_type, score = await find_best_match(metadata.name, metadata.system)

                if best_match:
                    metadata.libretro_name = best_match
                    metadata.thumbnail_match_type = match_type
                    metadata.thumbnail_match_score = score

                    image_data = await fetch_image(libretro_system, best_match, "boxart")
                    if image_data:
                        cache_key = get_thumbnail_cache_key(metadata.system, str(metadata.id), "boxart")
                        cache_path = get_thumbnail_cache_path(cache_key)
                        cache_path.write_bytes(image_data)
                        metadata.thumbnail_path = f"thumbnail_cache/{cache_key}.png"
                        metadata.thumbnail_status = "synced"
                        print(f"[SYNC] LibRetro thumbnail cached for metadata {metadata.id}")
                        return True

            metadata.thumbnail_status = "failed"
            return False

        except Exception as e:
            print(f"[SYNC] Thumbnail error for metadata {metadata.id}: {e}")
            metadata.thumbnail_status = "failed"
            return False

    # =========================================================================
    # Combined Sync Operations
    # =========================================================================

    async def full_sync(
        self,
        user_roms_path: str | None = None,
        include_unmatched_connectors: bool = False,
        progress_callback: Any | None = None,
    ) -> dict[str, Any]:
        """
        Complete sync pipeline:
        1. Sync connectors from stable-retro (get SHA1 hashes)
        2. Scan ROM folder, compute SHA1, correlate to connectors
        3. Sync IGDB metadata for ROMs (and optionally connectors)
        4. Sync thumbnails for items with metadata but missing images

        Args:
            user_roms_path: Path to user's ROM folder
            include_unmatched_connectors: Also sync metadata for connectors without ROMs
            progress_callback: Optional callback for progress updates
        """
        stats = {
            "connectors": {"added": 0, "updated": 0, "skipped": 0},
            "roms": {"added": 0, "updated": 0, "linked": 0, "skipped": 0},
            "metadata": {"synced": 0, "failed": 0},
            "thumbnails": {"synced": 0, "failed": 0},
        }

        # Step 1: Sync connectors from stable-retro
        print("[SYNC] Step 1: Syncing connectors from stable-retro...")
        if progress_callback:
            await progress_callback("connectors", 0, 0, "Syncing connectors...")
        connector_stats = await self.sync_connectors(progress_callback=progress_callback)
        stats["connectors"] = connector_stats

        # Step 2: Scan ROM folder, compute SHA1, correlate to connectors
        if user_roms_path:
            print(f"[SYNC] Step 2: Scanning ROM folder: {user_roms_path}")
            if progress_callback:
                await progress_callback("roms", 0, 0, "Scanning ROM folder...")
            rom_stats = await self.sync_roms(user_roms_path, progress_callback=progress_callback)
            stats["roms"] = rom_stats

        # Step 3: Sync IGDB metadata for ROMs (and optionally connectors)
        print("[SYNC] Step 3: Syncing IGDB metadata...")
        if progress_callback:
            await progress_callback("metadata", 0, 0, "Syncing metadata from IGDB...")
        metadata_stats = await self.sync_all_metadata(
            include_unmatched_connectors=include_unmatched_connectors,
            progress_callback=progress_callback,
        )
        stats["metadata"] = metadata_stats

        # Step 4: Sync thumbnails for items with metadata but missing images
        print("[SYNC] Step 4: Syncing missing thumbnails...")
        if progress_callback:
            await progress_callback("thumbnails", 0, 0, "Syncing thumbnails...")
        thumbnail_stats = await self.sync_missing_thumbnails(progress_callback=progress_callback)
        stats["thumbnails"] = thumbnail_stats

        print(f"[SYNC] Full sync complete: {stats}")
        return stats

    async def sync_missing_thumbnails(
        self,
        progress_callback: Any | None = None,
    ) -> dict[str, int]:
        """
        Sync thumbnails from LibRetro for items where IGDB has no cover.

        This is called by the "Fetch Thumbnails" button and only targets items where:
        - Has metadata (name exists)
        - No thumbnail yet (thumbnail_status != 'synced')
        - IGDB confirmed no cover (cover_url IS NULL)

        IGDB covers are already fetched during the main sync, so this only tries LibRetro.
        """
        from ..routers.thumbnails import fetch_image, find_best_match, get_libretro_system

        stats = {"synced": 0, "failed": 0, "skipped": 0}

        db = SessionLocal()
        try:
            # Only target items where IGDB has no cover (already tried during main sync)
            items = db.query(GameMetadataModel).filter(
                GameMetadataModel.name.isnot(None),
                GameMetadataModel.thumbnail_status != "synced",
                GameMetadataModel.cover_url.is_(None),  # IGDB confirmed no cover
            ).all()

            print(f"[SYNC:LIBRETRO] Fetching LibRetro thumbnails for {len(items)} items (no IGDB cover)")
            total = len(items)

            for i, metadata in enumerate(items):
                if progress_callback:
                    await progress_callback("thumbnails", i + 1, total, f"LibRetro: {metadata.name}")

                # Only try LibRetro (skip IGDB - we know it doesn't have a cover)
                libretro_system = get_libretro_system(metadata.system)
                if not libretro_system or not metadata.name:
                    stats["skipped"] += 1
                    continue

                try:
                    best_match, match_type, score = await find_best_match(metadata.name, metadata.system)

                    if best_match:
                        image_data = await fetch_image(libretro_system, best_match, "boxart")
                        if image_data:
                            cache_key = get_thumbnail_cache_key(metadata.system, str(metadata.id), "boxart")
                            cache_path = get_thumbnail_cache_path(cache_key)
                            cache_path.write_bytes(image_data)

                            metadata.thumbnail_path = f"thumbnail_cache/{cache_key}.png"
                            metadata.thumbnail_status = "synced"
                            metadata.libretro_name = best_match
                            metadata.thumbnail_match_type = match_type
                            metadata.thumbnail_match_score = score
                            stats["synced"] += 1
                            print(f"[SYNC:LIBRETRO] Found: {metadata.name} -> {best_match}")
                        else:
                            metadata.thumbnail_status = "failed"
                            stats["failed"] += 1
                    else:
                        metadata.thumbnail_status = "failed"
                        stats["failed"] += 1

                except Exception as e:
                    print(f"[SYNC:LIBRETRO] Error for {metadata.name}: {e}")
                    metadata.thumbnail_status = "failed"
                    stats["failed"] += 1

                # Commit periodically
                if (i + 1) % 10 == 0:
                    db.commit()

            db.commit()
            print(f"[SYNC:LIBRETRO] Complete: {stats}")
            return stats
        finally:
            db.close()

    async def scan_and_register_roms(
        self,
        user_roms_path: str | None = None,
        connectors: list[dict[str, Any]] | None = None,
        user_roms: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """
        Sync connectors + ROMs (Steps 1-2).
        Returns list of items that need metadata sync.
        """
        # Step 1: Sync connectors
        await self.sync_connectors(connectors)

        # Step 2: Sync user ROMs
        await self.sync_roms(user_roms_path, user_roms)

        # Return count of ROMs needing metadata sync
        db = SessionLocal()
        try:
            # ROMs without metadata
            roms_needing_sync = db.query(RomModel.id).filter(
                RomModel.metadata_id.is_(None)
            ).all()

            print(f"[SYNC] {len(roms_needing_sync)} ROMs need metadata sync")
            return [r.id for r in roms_needing_sync]
        finally:
            db.close()

    async def sync_all_pending(
        self,
        batch_size: int = 10,
        include_unmatched_connectors: bool = False,
    ) -> dict[str, int]:
        """Sync all pending metadata and thumbnails."""
        # Sync metadata
        metadata_stats = await self.sync_all_metadata(batch_size, include_unmatched_connectors)

        # Then sync thumbnails
        thumbnail_stats = await self.sync_missing_thumbnails()

        return {
            "synced": metadata_stats.get("synced", 0),
            "failed": metadata_stats.get("failed", 0),
            "thumbnails_synced": thumbnail_stats.get("synced", 0),
            "thumbnails_failed": thumbnail_stats.get("failed", 0),
        }

    # =========================================================================
    # Manual Corrections
    # =========================================================================

    async def resync_with_igdb_id(self, item_id: str, igdb_id: int) -> bool:
        """Manual correction: Re-sync with specific IGDB game ID."""
        db = SessionLocal()
        try:
            config = load_config()
            if not config.igdb_client_id or not config.igdb_client_secret:
                return False

            async with _rate_limit_lock:
                await asyncio.sleep(_RATE_LIMIT_DELAY)
                igdb_metadata = await get_game_by_id(
                    igdb_id, config.igdb_client_id, config.igdb_client_secret
                )

            if not igdb_metadata:
                return False

            # Find the connector or ROM
            connector = db.query(ConnectorModel).filter(ConnectorModel.id == item_id).first()
            rom = db.query(RomModel).filter(RomModel.id == item_id).first() if not connector else None

            if not connector and not rom:
                return False

            item = connector or rom
            system = item.system

            # Check if we already have metadata for this IGDB ID
            existing_metadata = db.query(GameMetadataModel).filter(
                GameMetadataModel.igdb_id == igdb_id,
                GameMetadataModel.system == system
            ).first()

            if existing_metadata:
                # Link to existing metadata
                item.metadata_id = existing_metadata.id
            else:
                # Create new metadata
                metadata = GameMetadataModel(
                    system=system,
                    igdb_id=igdb_metadata.igdb_id,
                    name=igdb_metadata.name,
                    summary=igdb_metadata.summary,
                    storyline=igdb_metadata.storyline,
                    rating=igdb_metadata.rating,
                    rating_count=igdb_metadata.rating_count,
                    genres=igdb_metadata.genres,
                    themes=igdb_metadata.themes,
                    game_modes=igdb_metadata.game_modes,
                    player_perspectives=igdb_metadata.player_perspectives,
                    platforms=igdb_metadata.platforms,
                    release_date=igdb_metadata.release_date,
                    developer=igdb_metadata.developer,
                    publisher=igdb_metadata.publisher,
                    cover_url=igdb_metadata.cover_url,
                    screenshot_urls=igdb_metadata.screenshot_urls,
                    sync_status="manual",
                    source="igdb",
                )
                db.add(metadata)
                db.flush()
                item.metadata_id = metadata.id

                # Sync thumbnail
                await self._sync_thumbnail(db, metadata)

            db.commit()
            print(f"[SYNC] Manual IGDB update: {item_id} -> {igdb_metadata.name}")
            return True

        except Exception as e:
            print(f"[SYNC] Error in manual resync: {e}")
            return False
        finally:
            db.close()

    async def search_igdb_candidates(
        self, item_id: str, query: str | None = None
    ) -> list[dict[str, Any]]:
        """Search IGDB for manual correction candidates."""
        db = SessionLocal()
        try:
            # Find the connector or ROM
            connector = db.query(ConnectorModel).filter(ConnectorModel.id == item_id).first()
            rom = db.query(RomModel).filter(RomModel.id == item_id).first() if not connector else None

            if not connector and not rom:
                return []

            item = connector or rom
            config = load_config()
            if not config.igdb_client_id or not config.igdb_client_secret:
                return []

            search_name = query or clean_game_name_for_search(item_id) if connector else item.display_name
            platform_filter = get_igdb_platform(item.system)

            async with _rate_limit_lock:
                await asyncio.sleep(_RATE_LIMIT_DELAY)
                result = await search_game(
                    search_name, config.igdb_client_id, config.igdb_client_secret, platform_filter
                )

            if result.metadata:
                return [{
                    "id": result.metadata.igdb_id,
                    "name": result.metadata.name,
                    "release_date": result.metadata.release_date,
                    "platforms": result.metadata.platforms,
                    "cover_url": result.metadata.cover_url,
                }]
            return []
        finally:
            db.close()


# Singleton instance
rom_sync = RomSyncOrchestrator()
