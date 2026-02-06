"""
Migration: Add connector_id and file_path columns.

1. Add connector_id column - stores stable-retro game ID (e.g., "PokemonFireRed-Gba-v0")
2. Add file_path column - stores path to user ROM files
3. Populate connector_id from existing id for ROMs with connectors

Run with:
    cd apps/api
    python -m src.migrations.migrate_connector_id_file_path
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text

from src.models.db import RomModel, SessionLocal, engine


def migrate():
    print("[MIGRATE] Adding connector_id and file_path columns...")

    # Step 1: Add columns if they don't exist
    with engine.connect() as conn:
        # Check if columns exist
        result = conn.execute(text("PRAGMA table_info(roms)"))
        columns = {row[1] for row in result.fetchall()}

        if "connector_id" not in columns:
            print("[MIGRATE] Adding connector_id column...")
            conn.execute(text("ALTER TABLE roms ADD COLUMN connector_id TEXT"))
            conn.commit()
        else:
            print("[MIGRATE] connector_id column already exists")

        if "file_path" not in columns:
            print("[MIGRATE] Adding file_path column...")
            conn.execute(text("ALTER TABLE roms ADD COLUMN file_path TEXT"))
            conn.commit()
        else:
            print("[MIGRATE] file_path column already exists")

    # Step 2: Populate connector_id from existing id for ROMs with connectors
    # (Old IDs were stable-retro game IDs like "PokemonFireRed-Gba-v0")
    db = SessionLocal()
    try:
        roms = db.query(RomModel).filter(RomModel.has_connector == True).all()  # noqa: E712
        updated = 0

        for rom in roms:
            # If connector_id is not set, use the current id (old format)
            if not rom.connector_id:
                rom.connector_id = rom.id
                updated += 1

        if updated:
            db.commit()
            print(f"[MIGRATE] Set connector_id for {updated} ROM entries")

        # Summary
        total = db.query(RomModel).count()
        with_connector_id = db.query(RomModel).filter(RomModel.connector_id.isnot(None)).count()
        with_file_path = db.query(RomModel).filter(RomModel.file_path.isnot(None)).count()

        print("\n[MIGRATE] Migration complete!")
        print(f"  Total ROMs: {total}")
        print(f"  With connector_id: {with_connector_id}")
        print(f"  With file_path: {with_file_path}")

    finally:
        db.close()


if __name__ == "__main__":
    migrate()
