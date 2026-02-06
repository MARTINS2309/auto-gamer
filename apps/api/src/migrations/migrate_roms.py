"""
Migration: Populate ROM table from existing data.

1. Create new Roms table (if not exists)
2. Scan stable-retro to get ROM list
3. Migrate data from GameMetadataCache
4. Migrate data from ThumbnailMapping
5. Keep old tables (not renamed - they may still be in use)

Run with:
    cd apps/api
    python -m src.migrations.migrate_roms
"""

import hashlib
import re

# Ensure we can import from the app
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.db import GameMetadataCache, RomModel, SessionLocal, ThumbnailMapping, engine
from src.services.rom_scanner import rom_scanner


def clean_display_name(game_id: str) -> str:
    """Clean game ID into display name."""
    name = re.sub(r"-[A-Za-z0-9]+-v\d+$", "", game_id)
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    name = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", name)
    name = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", name)
    return name


def get_thumbnail_cache_key(system: str, game: str) -> str:
    """Generate cache key for thumbnail."""
    key = f"{system}:{game}:boxart"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def migrate():
    print("[MIGRATE] Starting ROM data migration...")

    # Step 1: Ensure Roms table exists
    print("[MIGRATE] Creating Roms table if not exists...")
    RomModel.__table__.create(engine, checkfirst=True)

    db = SessionLocal()
    try:
        # Step 2: Scan stable-retro for all ROMs
        print("[MIGRATE] Scanning stable-retro...")
        scanned_roms = rom_scanner.list_games()
        print(f"[MIGRATE] Found {len(scanned_roms)} ROMs in stable-retro")

        # Step 3: Load existing metadata cache
        metadata_cache = {}
        try:
            rows = db.query(GameMetadataCache).all()
            for row in rows:
                key = f"{row.system}:{row.game_id}"
                metadata_cache[key] = row
            print(f"[MIGRATE] Loaded {len(metadata_cache)} cached metadata entries")
        except Exception as e:
            print(f"[MIGRATE] No metadata cache to migrate: {e}")

        # Step 4: Load thumbnail mappings
        thumbnail_cache = {}
        try:
            rows = db.query(ThumbnailMapping).all()
            for row in rows:
                key = f"{row.system}:{row.game_id}"
                thumbnail_cache[key] = row
            print(f"[MIGRATE] Loaded {len(thumbnail_cache)} thumbnail mappings")
        except Exception as e:
            print(f"[MIGRATE] No thumbnail mappings to migrate: {e}")

        # Step 5: Get existing ROM IDs
        existing_ids = {r.id for r in db.query(RomModel.id).all()}
        print(f"[MIGRATE] {len(existing_ids)} ROMs already in database")

        # Step 6: Create ROM entries with migrated data
        migrated = 0
        updated = 0
        for rom_data in scanned_roms:
            rom_id = rom_data["id"]
            system = rom_data["system"]
            key = f"{system}:{rom_id}"

            # Check if already exists
            existing = db.query(RomModel).filter(RomModel.id == rom_id).first()

            if existing:
                # Update playable status
                if existing.playable != rom_data["playable"]:
                    existing.playable = rom_data["playable"]
                    updated += 1

                # If metadata not synced, try to apply cached data
                if existing.sync_status == "pending" and key in metadata_cache:
                    meta = metadata_cache[key]
                    if meta.source != "not_found":
                        _apply_metadata(existing, meta)
                        existing.sync_status = "synced"
                        existing.synced_at = meta.updated_at or meta.created_at
                        updated += 1

                # If thumbnail not synced, try to apply cached mapping
                if existing.thumbnail_status == "pending" and key in thumbnail_cache:
                    thumb = thumbnail_cache[key]
                    _apply_thumbnail(existing, thumb, system, rom_id)
                    updated += 1

                continue

            # Create new ROM entry
            rom = RomModel(
                id=rom_id,
                system=system,
                playable=rom_data["playable"],
                states=[],
                display_name=clean_display_name(rom_id),
                sync_status="pending",
                thumbnail_status="pending",
            )

            # Apply cached metadata if exists
            if key in metadata_cache:
                meta = metadata_cache[key]
                if meta.source != "not_found":
                    _apply_metadata(rom, meta)
                    rom.sync_status = "synced"
                    rom.synced_at = meta.updated_at or meta.created_at
                else:
                    # Mark as failed if it was not_found
                    rom.sync_status = "failed"
                    rom.sync_error = "Not found in IGDB"

            # Apply thumbnail mapping if exists
            if key in thumbnail_cache:
                thumb = thumbnail_cache[key]
                _apply_thumbnail(rom, thumb, system, rom_id)

            db.add(rom)
            migrated += 1

        db.commit()
        print(f"[MIGRATE] Created {migrated} new ROM entries, updated {updated}")

        # Step 7: Summary
        total = db.query(RomModel).count()
        synced = db.query(RomModel).filter(RomModel.sync_status == "synced").count()
        pending = db.query(RomModel).filter(RomModel.sync_status == "pending").count()
        failed = db.query(RomModel).filter(RomModel.sync_status == "failed").count()

        print("\n[MIGRATE] Migration complete!")
        print(f"  Total ROMs: {total}")
        print(f"  Synced: {synced}")
        print(f"  Pending: {pending}")
        print(f"  Failed: {failed}")
        print("\nRun 'POST /api/roms/sync' to sync pending ROMs.")

    finally:
        db.close()


def _apply_metadata(rom: RomModel, meta: GameMetadataCache):
    """Apply cached metadata to ROM model."""
    rom.igdb_id = meta.igdb_id
    rom.igdb_name = meta.name
    rom.display_name = meta.name or rom.display_name
    rom.summary = meta.summary
    rom.storyline = meta.storyline
    rom.rating = meta.rating
    rom.rating_count = meta.rating_count
    rom.genres = meta.genres
    rom.themes = meta.themes
    rom.game_modes = meta.game_modes
    rom.player_perspectives = meta.player_perspectives
    rom.platforms = meta.platforms
    rom.release_date = meta.release_date
    rom.developer = meta.developer
    rom.publisher = meta.publisher
    rom.cover_url = meta.cover_url
    rom.screenshot_urls = meta.screenshot_urls


def _apply_thumbnail(rom: RomModel, thumb: ThumbnailMapping, system: str, rom_id: str):
    """Apply thumbnail mapping to ROM model."""
    rom.libretro_name = thumb.libretro_name
    rom.thumbnail_match_type = thumb.match_type
    rom.thumbnail_match_score = thumb.match_score

    # Check if cached file exists
    cache_key = get_thumbnail_cache_key(system, rom_id)
    cache_path = (
        Path(__file__).parent.parent.parent / "data" / "thumbnail_cache" / f"{cache_key}.png"
    )

    if cache_path.exists():
        rom.thumbnail_path = f"thumbnail_cache/{cache_key}.png"
        rom.thumbnail_status = "synced"
    else:
        rom.thumbnail_status = "pending"


if __name__ == "__main__":
    migrate()
