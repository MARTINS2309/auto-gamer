"""
Migration: Add has_rom and has_connector columns.

1. Add has_rom and has_connector columns
2. Populate from existing playable column:
   - has_rom = playable (ROM file exists)
   - has_connector = True (all existing ROMs came from stable-retro connectors)

Run with:
    cd apps/api
    python -m src.migrations.migrate_has_rom_connector
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text

from src.models.db import RomModel, SessionLocal, engine


def migrate():
    print("[MIGRATE] Adding has_rom and has_connector columns...")

    # Step 1: Add columns if they don't exist
    with engine.connect() as conn:
        # Check if columns exist
        result = conn.execute(text("PRAGMA table_info(roms)"))
        columns = {row[1] for row in result.fetchall()}

        if "has_rom" not in columns:
            print("[MIGRATE] Adding has_rom column...")
            conn.execute(text("ALTER TABLE roms ADD COLUMN has_rom BOOLEAN DEFAULT 0"))
            conn.commit()
        else:
            print("[MIGRATE] has_rom column already exists")

        if "has_connector" not in columns:
            print("[MIGRATE] Adding has_connector column...")
            conn.execute(text("ALTER TABLE roms ADD COLUMN has_connector BOOLEAN DEFAULT 0"))
            conn.commit()
        else:
            print("[MIGRATE] has_connector column already exists")

    # Step 2: Populate columns from existing data
    db = SessionLocal()
    try:
        roms = db.query(RomModel).all()
        updated = 0

        for rom in roms:
            # All existing ROMs came from stable-retro, so they have connectors
            # has_rom is derived from playable (ROM file exists)
            if rom.has_connector is None or not rom.has_connector:
                rom.has_connector = True
                updated += 1
            if rom.has_rom is None:
                rom.has_rom = rom.playable
                updated += 1

        if updated:
            db.commit()
            print(f"[MIGRATE] Updated {updated} ROM entries")

        # Summary
        total = db.query(RomModel).count()
        with_rom = db.query(RomModel).filter(RomModel.has_rom == True).count()  # noqa: E712
        with_connector = db.query(RomModel).filter(RomModel.has_connector == True).count()  # noqa: E712

        print("\n[MIGRATE] Migration complete!")
        print(f"  Total ROMs: {total}")
        print(f"  With ROM file: {with_rom}")
        print(f"  With connector: {with_connector}")

    finally:
        db.close()


if __name__ == "__main__":
    migrate()
