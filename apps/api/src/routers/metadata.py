"""
Game Metadata Router.

Provides game metadata from cached DB or fetches from external APIs (IGDB, ScreenScraper).
All data is cached in SQLite to minimize API calls.
"""

import asyncio
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models.db import GameMetadataCache, SessionLocal
from ..services.igdb import GameMetadata as IGDBMetadata
from ..services.igdb import (
    GameSearchRequest,
    get_igdb_platform,
    search_game,
    search_games_batch,
)
from .config import load_config

router = APIRouter(prefix="/metadata")

# Track games currently being fetched in background to prevent duplicate fetches
_pending_fetches: set[str] = set()


# =============================================================================
# Response Models
# =============================================================================


class GameMetadataBatchRequest(BaseModel):
    """Request for batch metadata lookup."""

    game_id: str
    system: str


class GameMetadataResponse(BaseModel):
    """Game metadata response."""

    game_id: str
    system: str
    name: str
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
    players: str | None = None
    estimated_playtime: int | None = None
    source: str
    cached: bool = True

    class Config:
        from_attributes = True


# =============================================================================
# Helpers
# =============================================================================

# Known game name aliases (game_id pattern -> IGDB search name)
# Used for regional differences, common misspellings, etc.
GAME_NAME_ALIASES = {
    # Regional name differences
    "CastlevaniaTheNewGeneration": "Castlevania Bloodlines",
    "SuperMarioBros2Japan": "Super Mario Bros The Lost Levels",
    # Compound words that need joining
    "RoboCop": "RoboCop",  # Prevent splitting
    "QuackShot": "QuackShot Starring Donald Duck",
    "ActRaiser": "ActRaiser",
    # Space issues
    "BeamRider": "Beamrider",
    "RiverRaid": "River Raid",
    "MsPacman": "Ms. Pac-Man",
    "JamesBond": "James Bond 007",
    # Japanese games with English releases
    "ChackNPop": "Chack'n Pop",
    "TwinBee": "TwinBee",
    # Specific fixes
    "XKaliber2097": "X-Kaliber 2097",
    "ChaseHQII": "Chase H.Q. II",
    "SolDeace": "Sol-Deace",
    "BioMetal": "BioMetal",
    "DevicReign": "Divine Sealing",  # Japanese name
}


def clean_game_name_for_search(game_id: str) -> str:
    """Convert game ID to searchable name."""
    # Remove system and version suffix: "SonicTheHedgehog-Genesis-v0" -> "SonicTheHedgehog"
    base_name = re.sub(r"-[A-Za-z0-9]+-v\d+$", "", game_id)

    # Check for known aliases first (before any transformation)
    for pattern, replacement in GAME_NAME_ALIASES.items():
        if pattern.lower() in base_name.lower().replace(" ", ""):
            return replacement

    name = base_name

    # CamelCase to spaces: "SonicTheHedgehog" -> "Sonic The Hedgehog"
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)

    # Numbers followed by letters: "3Dixie" -> "3 Dixie"
    name = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", name)
    # Letters followed by numbers: "Sonic2" -> "Sonic 2"
    name = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", name)

    # Restore common apostrophe patterns (lost during game ID creation)
    # Various "'n" patterns: Rush'n Attack, Wiz 'n' Liz, Chack'n Pop, Pop'n TwinBee
    name = re.sub(r"(\w)shn\b", r"\1sh'n", name)  # Rush'n
    name = re.sub(r"(\w)shn ", r"\1sh'n ", name)
    name = re.sub(r"(\w)sn\b", r"\1s 'n", name)  # Ghosts 'n
    name = re.sub(r"(\w)sn ", r"\1s 'n ", name)
    name = re.sub(r"(\w)ckn\b", r"\1ck'n", name)  # Chack'n
    name = re.sub(r"(\w)ckn ", r"\1ck'n ", name)
    name = re.sub(r"(\w)zn\b", r"\1z 'n'", name)  # Wiz 'n'
    name = re.sub(r"(\w)zn ", r"\1z 'n' ", name)
    name = re.sub(r"\bPopn\b", "Pop'n", name)  # Pop'n

    # Fix compound words that shouldn't be split
    name = re.sub(r"\bRobo Cop\b", "RoboCop", name)
    name = re.sub(r"\bQuack Shot\b", "QuackShot", name)
    name = re.sub(r"\bAct Raiser\b", "ActRaiser", name)
    name = re.sub(r"\bTwin Bee\b", "TwinBee", name)
    name = re.sub(r"\bBio Metal\b", "BioMetal", name)

    return name


def get_cached_metadata(game_id: str, system: str) -> GameMetadataCache | None:
    """Get cached metadata from DB."""
    db = SessionLocal()
    try:
        return (
            db.query(GameMetadataCache)
            .filter(GameMetadataCache.game_id == game_id, GameMetadataCache.system == system)
            .first()
        )
    finally:
        db.close()


def save_not_found_to_cache(game_id: str, system: str) -> GameMetadataCache:
    """Save a 'not found' marker to prevent repeated API lookups."""
    db = SessionLocal()
    try:
        existing = (
            db.query(GameMetadataCache)
            .filter(GameMetadataCache.game_id == game_id, GameMetadataCache.system == system)
            .first()
        )

        if existing:
            # Don't overwrite valid data with not_found
            if existing.source != "not_found":
                return existing
            # Update timestamp for existing not_found
            existing.updated_at = datetime.utcnow()
            db.commit()
            return existing

        # Create not_found entry with minimal data
        cache_entry = GameMetadataCache(
            game_id=game_id,
            system=system,
            name=clean_game_name_for_search(game_id),  # Use cleaned name as display name
            source="not_found",
        )
        db.add(cache_entry)
        db.commit()
        db.refresh(cache_entry)
        return cache_entry
    finally:
        db.close()


def save_metadata_to_cache(
    game_id: str, system: str, igdb_data: IGDBMetadata, rom_sha1: str | None = None
) -> GameMetadataCache:
    """Save IGDB metadata to cache."""
    db = SessionLocal()
    try:
        # Check if exists
        existing = (
            db.query(GameMetadataCache)
            .filter(GameMetadataCache.game_id == game_id, GameMetadataCache.system == system)
            .first()
        )

        if existing:
            # Update existing
            existing.igdb_id = igdb_data.igdb_id
            existing.name = igdb_data.name
            existing.summary = igdb_data.summary
            existing.storyline = igdb_data.storyline
            existing.rating = igdb_data.rating
            existing.rating_count = igdb_data.rating_count
            existing.genres = igdb_data.genres
            existing.themes = igdb_data.themes
            existing.game_modes = igdb_data.game_modes
            existing.player_perspectives = igdb_data.player_perspectives
            existing.platforms = igdb_data.platforms
            existing.release_date = igdb_data.release_date
            existing.developer = igdb_data.developer
            existing.publisher = igdb_data.publisher
            existing.cover_url = igdb_data.cover_url
            existing.screenshot_urls = igdb_data.screenshot_urls
            existing.source = "igdb"
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new
            cache_entry = GameMetadataCache(
                game_id=game_id,
                system=system,
                rom_sha1=rom_sha1,
                igdb_id=igdb_data.igdb_id,
                name=igdb_data.name,
                summary=igdb_data.summary,
                storyline=igdb_data.storyline,
                rating=igdb_data.rating,
                rating_count=igdb_data.rating_count,
                genres=igdb_data.genres,
                themes=igdb_data.themes,
                game_modes=igdb_data.game_modes,
                player_perspectives=igdb_data.player_perspectives,
                platforms=igdb_data.platforms,
                release_date=igdb_data.release_date,
                developer=igdb_data.developer,
                publisher=igdb_data.publisher,
                cover_url=igdb_data.cover_url,
                screenshot_urls=igdb_data.screenshot_urls,
                source="igdb",
            )
            db.add(cache_entry)
            db.commit()
            db.refresh(cache_entry)
            return cache_entry
    finally:
        db.close()


def db_to_response(cache: GameMetadataCache, from_cache: bool = True) -> GameMetadataResponse:
    """Convert DB model to response."""
    return GameMetadataResponse(
        game_id=cache.game_id,
        system=cache.system,
        name=cache.name,
        summary=cache.summary,
        storyline=cache.storyline,
        rating=cache.rating,
        rating_count=cache.rating_count,
        genres=cache.genres or [],
        themes=cache.themes or [],
        game_modes=cache.game_modes or [],
        player_perspectives=cache.player_perspectives or [],
        platforms=cache.platforms or [],
        release_date=cache.release_date,
        developer=cache.developer,
        publisher=cache.publisher,
        cover_url=cache.cover_url,
        screenshot_urls=cache.screenshot_urls or [],
        players=cache.players,
        estimated_playtime=cache.estimated_playtime,
        source=cache.source,
        cached=from_cache,
    )


# =============================================================================
# Routes
# =============================================================================


@router.get("/game/{system}/{game_id}", response_model=GameMetadataResponse)
async def get_game_metadata(system: str, game_id: str, force_refresh: bool = False):
    """
    Get metadata for a game.

    First checks cache, then fetches from IGDB if not cached (and credentials configured).
    """
    from datetime import timedelta

    # Check cache first (unless force refresh)
    if not force_refresh:
        cached = await asyncio.to_thread(get_cached_metadata, game_id, system)
        if cached:
            # Retry not_found entries after 7 days
            if cached.source == "not_found":
                age = datetime.utcnow() - (cached.updated_at or cached.created_at)
                if age < timedelta(days=7):
                    print(f"[META] Not found cache hit: {game_id} (retry in {7 - age.days} days)")
                    return db_to_response(cached, from_cache=True)
                # Older than 7 days - try fetching again
                print(f"[META] Retrying not_found: {game_id}")
            else:
                print(f"[META] Cache hit: {game_id}")
                return db_to_response(cached, from_cache=True)

    # Get config for API credentials
    config = load_config()

    if not config.igdb_client_id or not config.igdb_client_secret:
        raise HTTPException(
            status_code=503,
            detail="IGDB credentials not configured. Set igdb_client_id and igdb_client_secret in config.",
        )

    # Search IGDB
    search_name = clean_game_name_for_search(game_id)
    platform_filter = get_igdb_platform(system)

    print(f"[META] Searching IGDB for: {search_name} (platform: {platform_filter})")

    result = await search_game(
        name=search_name,
        client_id=config.igdb_client_id,
        client_secret=config.igdb_client_secret,
        platform_filter=platform_filter,
    )

    if result.metadata:
        # Cache the result
        cache_entry = await asyncio.to_thread(save_metadata_to_cache, game_id, system, result.metadata)
        print(f"[META] Cached IGDB data for: {game_id} -> {result.metadata.name}")
        return db_to_response(cache_entry, from_cache=False)

    if result.not_found:
        # Only cache as not_found when game genuinely doesn't exist
        cache_entry = await asyncio.to_thread(save_not_found_to_cache, game_id, system)
        print(f"[META] Not found in IGDB: {search_name}")
        return db_to_response(cache_entry, from_cache=False)

    # API error (rate limit, network, etc.) - don't cache, raise error
    print(f"[META] IGDB error for: {search_name} - will retry later")
    raise HTTPException(
        status_code=503, detail="IGDB API temporarily unavailable. Try again later."
    )


@router.get("/stats")
def metadata_stats():
    """Get metadata cache statistics."""
    db = SessionLocal()
    try:
        total = db.query(GameMetadataCache).count()

        # Count by source
        from sqlalchemy import func

        by_source = (
            db.query(GameMetadataCache.source, func.count(GameMetadataCache.id))
            .group_by(GameMetadataCache.source)
            .all()
        )

        return {
            "total_cached": total,
            "by_source": {s: c for s, c in by_source},
        }
    finally:
        db.close()


@router.get("/cached", response_model=list[GameMetadataResponse])
def list_cached_metadata(limit: int = 50, offset: int = 0):
    """List all cached game metadata."""
    db = SessionLocal()
    try:
        entries = (
            db.query(GameMetadataCache)
            .order_by(GameMetadataCache.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [db_to_response(e) for e in entries]
    finally:
        db.close()


async def _fetch_uncached_games_background(
    uncached: list[GameMetadataBatchRequest], client_id: str, client_secret: str
):
    """Background task to fetch uncached games from IGDB."""
    global _pending_fetches

    # Track which games we're fetching to prevent duplicate fetches
    game_keys = {f"{g.game_id}:{g.system}" for g in uncached}
    _pending_fetches.update(game_keys)

    try:
        search_requests = [
            GameSearchRequest(
                search_name=clean_game_name_for_search(g.game_id),
                platform_filter=get_igdb_platform(g.system),
                game_id=g.game_id,
                system=g.system,
            )
            for g in uncached
        ]

        # Process in batches of 10 (IGDB multi-query limit)
        for i in range(0, len(search_requests), 10):
            batch = search_requests[i : i + 10]
            try:
                batch_results = await search_games_batch(
                    batch,
                    client_id,
                    client_secret,
                )

                # Cache results based on search outcome
                for req in batch:
                    if not req.game_id or not req.system:
                        continue
                    result = batch_results.get(req.game_id)
                    if result and result.metadata:
                        # Found in IGDB - cache the metadata
                        await asyncio.to_thread(save_metadata_to_cache, req.game_id, req.system, result.metadata)
                    elif result and result.not_found:
                        # Genuinely not found - cache as not_found
                        await asyncio.to_thread(save_not_found_to_cache, req.game_id, req.system)
                    # If error, don't cache - will be retried on next request

                    # Remove from pending as we process each result
                    _pending_fetches.discard(f"{req.game_id}:{req.system}")
            except Exception as e:
                print(f"[META] Background fetch error: {e}")
                # Remove batch from pending on error
                for req in batch:
                    _pending_fetches.discard(f"{req.game_id}:{req.system}")

        print(f"[META] Background fetch complete: {len(uncached)} games processed")
    finally:
        # Ensure we clean up any remaining pending entries
        _pending_fetches -= game_keys


@router.post("/batch", response_model=list[GameMetadataResponse])
async def get_batch_metadata(games: list[GameMetadataBatchRequest]):
    """
    Fetch metadata for multiple games in a single request.

    Returns cached data immediately. Uncached games are fetched in the background
    and will be available on subsequent requests.
    """
    if not games:
        return []

    config = load_config()

    # Check cache in thread to avoid blocking event loop
    def _check_cache():
        results: list[GameMetadataResponse] = []
        uncached: list[GameMetadataBatchRequest] = []
        not_found_count = 0
        for game in games:
            cached = get_cached_metadata(game.game_id, game.system)
            if cached:
                if cached.source == "not_found":
                    not_found_count += 1
                results.append(db_to_response(cached, from_cache=True))
            else:
                uncached.append(game)
        return results, uncached, not_found_count

    results, uncached, not_found_count = await asyncio.to_thread(_check_cache)

    # Filter out games that are already being fetched in background
    truly_uncached = [g for g in uncached if f"{g.game_id}:{g.system}" not in _pending_fetches]
    already_pending = len(uncached) - len(truly_uncached)

    if truly_uncached or already_pending:
        parts = []
        if len(results) - not_found_count > 0:
            parts.append(f"{len(results) - not_found_count} cached")
        if not_found_count > 0:
            parts.append(f"{not_found_count} not_found")
        if already_pending > 0:
            parts.append(f"{already_pending} already fetching")
        if truly_uncached:
            parts.append(f"{len(truly_uncached)} to fetch")
        print(f"[META] Batch: {', '.join(parts)}")

    # Start background fetch for uncached games (non-blocking)
    # Rate limiting is handled by global lock in igdb.py
    # Duplicate prevention is handled by _pending_fetches set
    if truly_uncached and config.igdb_client_id and config.igdb_client_secret:
        asyncio.create_task(
            _fetch_uncached_games_background(
                truly_uncached,
                config.igdb_client_id,
                config.igdb_client_secret,
            )
        )

    return results


@router.delete("/cache")
def clear_metadata_cache():
    """Clear all cached metadata."""
    db = SessionLocal()
    try:
        count = db.query(GameMetadataCache).delete()
        db.commit()
        return {"cleared": count}
    finally:
        db.close()


@router.delete("/cache/{system}/{game_id}")
def delete_cached_metadata(system: str, game_id: str):
    """Delete cached metadata for a specific game."""
    db = SessionLocal()
    try:
        deleted = (
            db.query(GameMetadataCache)
            .filter(GameMetadataCache.game_id == game_id, GameMetadataCache.system == system)
            .delete()
        )
        db.commit()

        if deleted == 0:
            raise HTTPException(status_code=404, detail="Game not found in cache")

        return {"deleted": True}
    finally:
        db.close()


@router.delete("/cache/not-found")
def clear_not_found_cache():
    """Clear all 'not_found' entries to allow re-fetching with improved search."""
    db = SessionLocal()
    try:
        count = db.query(GameMetadataCache).filter(GameMetadataCache.source == "not_found").delete()
        db.commit()
        return {
            "cleared": count,
            "message": f"Cleared {count} not_found entries. They will be re-fetched on next request.",
        }
    finally:
        db.close()
