"""
Migration: Separate ROMs, Connectors, and Metadata into distinct tables.

This restructures the database from a flattened model to a normalized model:
- roms: User's local ROM files (identified by SHA1 hash)
- connectors: stable-retro connectors (for AI training)
- game_metadata: IGDB metadata (linked to both)

Run with:
    cd apps/api
    python -m src.migrations.migrate_to_separated_tables
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text

from src.models.db import SessionLocal, engine


def table_exists(conn, table_name: str) -> bool:
    """Check if a table exists."""
    result = conn.execute(
        text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    )
    return result.fetchone() is not None


def get_columns(conn, table_name: str) -> set[str]:
    """Get column names for a table."""
    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
    return {row[1] for row in result.fetchall()}


def migrate():
    print("[MIGRATE] Restructuring database to separate ROMs, Connectors, and Metadata...")
    print("=" * 60)

    with engine.connect() as conn:
        # =====================================================================
        # Step 1: Create connectors table if it doesn't exist
        # =====================================================================
        if not table_exists(conn, "connectors"):
            print("\n[MIGRATE] Creating connectors table...")
            conn.execute(text("""
                CREATE TABLE connectors (
                    id VARCHAR PRIMARY KEY,
                    system VARCHAR NOT NULL,
                    display_name VARCHAR NOT NULL,
                    sha1_hash VARCHAR(40),
                    states JSON DEFAULT '[]',
                    has_rom BOOLEAN DEFAULT 0,
                    metadata_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(metadata_id) REFERENCES game_metadata(id)
                )
            """))
            conn.execute(text("CREATE INDEX ix_connectors_id ON connectors(id)"))
            conn.execute(text("CREATE INDEX ix_connectors_system ON connectors(system)"))
            conn.execute(text("CREATE INDEX ix_connectors_sha1_hash ON connectors(sha1_hash)"))
            conn.execute(text("CREATE INDEX ix_connectors_sha1_system ON connectors(sha1_hash, system)"))
            conn.commit()
            print("[MIGRATE] connectors table created successfully")
        else:
            print("[MIGRATE] connectors table already exists")

        # =====================================================================
        # Step 2: Migrate existing ROMs data to connectors table
        # =====================================================================
        roms_columns = get_columns(conn, "roms")

        # Check if we need to migrate data from old roms table
        if "connector_id" in roms_columns and "has_connector" in roms_columns:
            print("\n[MIGRATE] Migrating connector data from roms table...")

            # Get all connector-based entries from the old roms table
            result = conn.execute(text("""
                SELECT id, system, display_name, states, playable, created_at, updated_at
                FROM roms
                WHERE has_connector = 1 OR connector_id IS NOT NULL
            """))
            old_connectors = result.fetchall()

            # Check existing connectors
            existing = conn.execute(text("SELECT id FROM connectors"))
            existing_ids = {row[0] for row in existing.fetchall()}

            migrated = 0
            for row in old_connectors:
                rom_id, system, display_name, states, playable, created_at, updated_at = row

                # Use connector_id if available, otherwise use rom_id for connector-type entries
                connector_id = rom_id
                if connector_id not in existing_ids:
                    conn.execute(
                        text("""
                            INSERT INTO connectors (id, system, display_name, states, has_rom, created_at, updated_at)
                            VALUES (:id, :system, :name, :states, :has_rom, :created, :updated)
                        """),
                        {
                            "id": connector_id,
                            "system": system,
                            "name": display_name,
                            "states": states or "[]",
                            "has_rom": bool(playable),
                            "created": created_at,
                            "updated": updated_at,
                        },
                    )
                    migrated += 1

            conn.commit()
            print(f"[MIGRATE] Migrated {migrated} connectors")

        # =====================================================================
        # Step 3: Update roms table structure
        # =====================================================================
        print("\n[MIGRATE] Updating roms table structure...")

        # Add new columns if missing
        if "sha1_hash" not in roms_columns:
            conn.execute(text("ALTER TABLE roms ADD COLUMN sha1_hash VARCHAR(40)"))
            conn.commit()
            print("[MIGRATE] Added sha1_hash column")

        if "file_name" not in roms_columns:
            conn.execute(text("ALTER TABLE roms ADD COLUMN file_name VARCHAR"))
            conn.commit()
            print("[MIGRATE] Added file_name column")

        if "file_size" not in roms_columns:
            conn.execute(text("ALTER TABLE roms ADD COLUMN file_size INTEGER"))
            conn.commit()
            print("[MIGRATE] Added file_size column")

        # Update connector_id to point to connectors table properly
        if "connector_id" not in roms_columns:
            conn.execute(text("ALTER TABLE roms ADD COLUMN connector_id VARCHAR"))
            conn.commit()
            print("[MIGRATE] Added connector_id column")

        if "metadata_id" not in roms_columns:
            conn.execute(text("ALTER TABLE roms ADD COLUMN metadata_id INTEGER"))
            conn.commit()
            print("[MIGRATE] Added metadata_id column")

        # =====================================================================
        # Step 4: Update game_metadata table structure
        # =====================================================================
        print("\n[MIGRATE] Updating game_metadata table structure...")
        metadata_columns = get_columns(conn, "game_metadata")

        if "sha1_hash" not in metadata_columns:
            conn.execute(text("ALTER TABLE game_metadata ADD COLUMN sha1_hash VARCHAR(40)"))
            conn.commit()
            print("[MIGRATE] Added sha1_hash to game_metadata")

        if "sync_status" not in metadata_columns:
            conn.execute(text("ALTER TABLE game_metadata ADD COLUMN sync_status VARCHAR DEFAULT 'pending'"))
            conn.commit()
            print("[MIGRATE] Added sync_status to game_metadata")

        if "sync_error" not in metadata_columns:
            conn.execute(text("ALTER TABLE game_metadata ADD COLUMN sync_error VARCHAR"))
            conn.commit()
            print("[MIGRATE] Added sync_error to game_metadata")

        if "libretro_name" not in metadata_columns:
            conn.execute(text("ALTER TABLE game_metadata ADD COLUMN libretro_name VARCHAR"))
            conn.commit()
            print("[MIGRATE] Added libretro_name to game_metadata")

        if "thumbnail_match_type" not in metadata_columns:
            conn.execute(text("ALTER TABLE game_metadata ADD COLUMN thumbnail_match_type VARCHAR"))
            conn.commit()
            print("[MIGRATE] Added thumbnail_match_type to game_metadata")

        if "thumbnail_match_score" not in metadata_columns:
            conn.execute(text("ALTER TABLE game_metadata ADD COLUMN thumbnail_match_score REAL"))
            conn.commit()
            print("[MIGRATE] Added thumbnail_match_score to game_metadata")

        if "thumbnail_path" not in metadata_columns:
            conn.execute(text("ALTER TABLE game_metadata ADD COLUMN thumbnail_path VARCHAR"))
            conn.commit()
            print("[MIGRATE] Added thumbnail_path to game_metadata")

        if "thumbnail_status" not in metadata_columns:
            conn.execute(text("ALTER TABLE game_metadata ADD COLUMN thumbnail_status VARCHAR DEFAULT 'pending'"))
            conn.commit()
            print("[MIGRATE] Added thumbnail_status to game_metadata")

        # Create indexes if they don't exist
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_metadata_sha1_system ON game_metadata(sha1_hash, system)"))
            conn.commit()
        except Exception:
            pass

    # =========================================================================
    # Step 5: Summary
    # =========================================================================
    print("\n" + "=" * 60)
    print("[MIGRATE] Migration complete!")

    db = SessionLocal()
    try:
        from sqlalchemy import func

        from src.models.db import ConnectorModel, GameMetadataModel, RomModel

        roms_count = db.query(func.count(RomModel.id)).scalar() or 0
        connectors_count = db.query(func.count(ConnectorModel.id)).scalar() or 0
        metadata_count = db.query(func.count(GameMetadataModel.id)).scalar() or 0

        print("\nDatabase summary:")
        print(f"  ROMs:       {roms_count}")
        print(f"  Connectors: {connectors_count}")
        print(f"  Metadata:   {metadata_count}")
    except Exception as e:
        print(f"[MIGRATE] Error getting summary: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
