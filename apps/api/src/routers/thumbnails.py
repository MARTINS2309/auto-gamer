"""
Thumbnail proxy and cache service.

Multi-layer lookup strategy:
1. Check local image cache (permanent)
2. Check name mapping from SQLite DB
3. Exact match with region variants
4. Fuzzy match against LibRetro index
5. (Future) ScreenScraper API via ROM SHA1
"""

import re
import json
import hashlib
from pathlib import Path
from typing import Optional, List, Tuple
from urllib.parse import quote
from difflib import SequenceMatcher
from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException, Response, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..models.db import SessionLocal, ThumbnailMapping, ThumbnailFailure

router = APIRouter(prefix="/thumbnails")

# =============================================================================
# Configuration
# =============================================================================

DATA_DIR = Path(__file__).parent.parent.parent / "data"
CACHE_DIR = DATA_DIR / "thumbnail_cache"
INDEX_DIR = DATA_DIR / "thumbnail_index"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

# LibRetro sources
LIBRETRO_CDN = "https://thumbnails.libretro.com"
GITHUB_API = "https://api.github.com/repos/libretro-thumbnails"

# System name mapping (our identifiers -> LibRetro folder names)
SYSTEM_MAP = {
    # Nintendo
    "Nes": "Nintendo - Nintendo Entertainment System",
    "Snes": "Nintendo - Super Nintendo Entertainment System",
    "N64": "Nintendo - Nintendo 64",
    "GameBoy": "Nintendo - Game Boy",
    "Gb": "Nintendo - Game Boy",
    "Gbc": "Nintendo - Game Boy Color",
    "Gba": "Nintendo - Game Boy Advance",
    "NintendoDS": "Nintendo - Nintendo DS",
    "Nds": "Nintendo - Nintendo DS",
    # Sega
    "Genesis": "Sega - Mega Drive - Genesis",
    "MegaDrive": "Sega - Mega Drive - Genesis",
    "Sms": "Sega - Master System - Mark III",
    "MasterSystem": "Sega - Master System - Mark III",
    "GameGear": "Sega - Game Gear",
    "Gg": "Sega - Game Gear",
    "Saturn": "Sega - Saturn",
    "Dreamcast": "Sega - Dreamcast",
    "Scd": "Sega - Mega-CD - Sega CD",
    "SegaCD": "Sega - Mega-CD - Sega CD",
    "32x": "Sega - 32X",
    # Atari
    "Atari2600": "Atari - 2600",
    "Atari5200": "Atari - 5200",
    "Atari7800": "Atari - 7800",
    "AtariLynx": "Atari - Lynx",
    "Lynx": "Atari - Lynx",
    "AtariJaguar": "Atari - Jaguar",
    "Jaguar": "Atari - Jaguar",
    # Sony
    "Psx": "Sony - PlayStation",
    "PlayStation": "Sony - PlayStation",
    "Psp": "Sony - PlayStation Portable",
    # Other
    "Arcade": "FBNeo - Arcade Games",
    "PCEngine": "NEC - PC Engine - TurboGrafx 16",
    "TurboGrafx16": "NEC - PC Engine - TurboGrafx 16",
    "NeoGeo": "SNK - Neo Geo",
    "Ngp": "SNK - Neo Geo Pocket",
    "NeoGeoPocket": "SNK - Neo Geo Pocket",
    "Wonderswan": "Bandai - WonderSwan",
    "Ws": "Bandai - WonderSwan",
}

# LibRetro folder name -> GitHub repo name
GITHUB_REPO_MAP = {
    "Nintendo - Nintendo Entertainment System": "Nintendo_-_Nintendo_Entertainment_System",
    "Nintendo - Super Nintendo Entertainment System": "Nintendo_-_Super_Nintendo_Entertainment_System",
    "Nintendo - Nintendo 64": "Nintendo_-_Nintendo_64",
    "Nintendo - Game Boy": "Nintendo_-_Game_Boy",
    "Nintendo - Game Boy Color": "Nintendo_-_Game_Boy_Color",
    "Nintendo - Game Boy Advance": "Nintendo_-_Game_Boy_Advance",
    "Nintendo - Nintendo DS": "Nintendo_-_Nintendo_DS",
    "Sega - Mega Drive - Genesis": "Sega_-_Mega_Drive_-_Genesis",
    "Sega - Master System - Mark III": "Sega_-_Master_System_-_Mark_III",
    "Sega - Game Gear": "Sega_-_Game_Gear",
    "Sega - Saturn": "Sega_-_Saturn",
    "Sega - Dreamcast": "Sega_-_Dreamcast",
    "Sega - Mega-CD - Sega CD": "Sega_-_Mega-CD_-_Sega_CD",
    "Sega - 32X": "Sega_-_32X",
    "Atari - 2600": "Atari_-_2600",
    "Atari - 5200": "Atari_-_5200",
    "Atari - 7800": "Atari_-_7800",
    "Atari - Lynx": "Atari_-_Lynx",
    "Atari - Jaguar": "Atari_-_Jaguar",
    "Sony - PlayStation": "Sony_-_PlayStation",
    "Sony - PlayStation Portable": "Sony_-_PlayStation_Portable",
    "FBNeo - Arcade Games": "FBNeo_-_Arcade_Games",
    "NEC - PC Engine - TurboGrafx 16": "NEC_-_PC_Engine_-_TurboGrafx_16",
    "SNK - Neo Geo": "SNK_-_Neo_Geo",
    "SNK - Neo Geo Pocket": "SNK_-_Neo_Geo_Pocket",
    "Bandai - WonderSwan": "Bandai_-_WonderSwan",
}

# Region variants to try (in order of preference)
REGION_VARIANTS = [
    "(USA)",
    "(World)",
    "(USA, Europe)",
    "(Europe)",
    "(USA, Japan)",
    "(Japan, USA)",
    "(Japan)",
    "(Europe, Australia)",
    "(USA, Australia)",
    "",  # No region suffix
]

# In-memory caches (loaded from DB on startup)
_cache_key_map: dict[str, str] = {}  # For debugging: cache_key -> "system:game:type"
_system_indexes: dict[str, List[str]] = {}  # system -> list of available thumbnails
_mappings_cache: dict[str, str] = {}  # "system:game_id" -> libretro_name
_failures_cache: set[str] = set()  # "system:game_id" for known failures


# =============================================================================
# Database Helpers
# =============================================================================

def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Caller must close


def load_mappings_to_memory():
    """Load all mappings from DB into memory cache on startup."""
    global _mappings_cache, _failures_cache
    db = SessionLocal()
    try:
        # Load successful mappings
        mappings = db.query(ThumbnailMapping).all()
        for m in mappings:
            _mappings_cache[f"{m.system}:{m.game_id}"] = m.libretro_name
        print(f"[THUMB] Loaded {len(mappings)} name mappings from DB")

        # Load failures
        failures = db.query(ThumbnailFailure).all()
        for f in failures:
            _failures_cache.add(f"{f.system}:{f.game_id}")
        print(f"[THUMB] Loaded {len(failures)} known failures from DB")
    except Exception as e:
        print(f"[THUMB] Error loading from DB: {e}")
    finally:
        db.close()


def save_mapping_to_db(system: str, game_id: str, libretro_name: str, match_type: str, match_score: Optional[float] = None):
    """Save a successful mapping to the database."""
    db = SessionLocal()
    try:
        # Check if exists
        existing = db.query(ThumbnailMapping).filter(
            ThumbnailMapping.system == system,
            ThumbnailMapping.game_id == game_id
        ).first()

        if existing:
            # Update existing
            existing.libretro_name = libretro_name
            existing.match_type = match_type
            existing.match_score = match_score
        else:
            # Create new
            mapping = ThumbnailMapping(
                system=system,
                game_id=game_id,
                libretro_name=libretro_name,
                match_type=match_type,
                match_score=match_score
            )
            db.add(mapping)

        db.commit()
        _mappings_cache[f"{system}:{game_id}"] = libretro_name
        print(f"[THUMB] Saved mapping to DB: {game_id} -> {libretro_name} ({match_type})")
    except Exception as e:
        print(f"[THUMB] Error saving mapping to DB: {e}")
        db.rollback()
    finally:
        db.close()


def save_failure_to_db(system: str, game_id: str):
    """Record a failed lookup in the database."""
    db = SessionLocal()
    try:
        # Check if exists
        existing = db.query(ThumbnailFailure).filter(
            ThumbnailFailure.system == system,
            ThumbnailFailure.game_id == game_id
        ).first()

        if existing:
            existing.attempts += 1
            existing.last_attempt = datetime.utcnow()
        else:
            failure = ThumbnailFailure(
                system=system,
                game_id=game_id
            )
            db.add(failure)

        db.commit()
        _failures_cache.add(f"{system}:{game_id}")
    except Exception as e:
        print(f"[THUMB] Error saving failure to DB: {e}")
        db.rollback()
    finally:
        db.close()


def get_mapping_from_cache(system: str, game_id: str) -> Optional[str]:
    """Get a known name mapping from memory cache."""
    return _mappings_cache.get(f"{system}:{game_id}")


def is_known_failure(system: str, game_id: str) -> bool:
    """Check if a game is a known lookup failure."""
    return f"{system}:{game_id}" in _failures_cache


# =============================================================================
# System Index Management (still uses file cache for large indexes)
# =============================================================================

def get_index_path(system: str) -> Path:
    """Get path to cached index file for a system."""
    safe_name = system.replace(" ", "_").replace("-", "_")
    return INDEX_DIR / f"{safe_name}.json"


async def fetch_system_index(libretro_system: str) -> Optional[List[str]]:
    """Fetch thumbnail index for a system from GitHub API."""
    github_repo = GITHUB_REPO_MAP.get(libretro_system)
    if not github_repo:
        print(f"[THUMB] No GitHub repo mapping for: {libretro_system}")
        return None

    url = f"{GITHUB_API}/{github_repo}/contents/Named_Boxarts"
    print(f"[THUMB] Fetching index from: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    names = [
                        item["name"][:-4]  # Remove .png
                        for item in data
                        if item.get("name", "").endswith(".png")
                    ]
                    print(f"[THUMB] Fetched {len(names)} thumbnails for {libretro_system}")
                    return names
            else:
                print(f"[THUMB] Failed to fetch index: {response.status_code}")
        except Exception as e:
            print(f"[THUMB] Error fetching index: {e}")

    return None


async def get_system_index(system: str) -> List[str]:
    """Get the thumbnail index for a system (cached)."""
    libretro_system = get_libretro_system(system)
    if not libretro_system:
        return []

    # Check memory cache
    if libretro_system in _system_indexes:
        return _system_indexes[libretro_system]

    # Check disk cache
    index_path = get_index_path(libretro_system)
    if index_path.exists():
        try:
            with open(index_path) as f:
                names = json.load(f)
            _system_indexes[libretro_system] = names
            print(f"[THUMB] Loaded {len(names)} names from cached index for {system}")
            return names
        except Exception as e:
            print(f"[THUMB] Error loading cached index: {e}")

    # Fetch from GitHub
    names = await fetch_system_index(libretro_system)
    if names:
        try:
            with open(index_path, 'w') as f:
                json.dump(names, f)
        except Exception as e:
            print(f"[THUMB] Error caching index: {e}")

        _system_indexes[libretro_system] = names
        return names

    return []


# =============================================================================
# Name Matching
# =============================================================================

def get_libretro_system(system: str) -> Optional[str]:
    """Map our system ID to LibRetro folder name."""
    if system in SYSTEM_MAP:
        return SYSTEM_MAP[system]
    for key, value in SYSTEM_MAP.items():
        if key.lower() == system.lower():
            return value
    return None


def clean_game_name(name: str) -> str:
    """Clean game name for LibRetro URL format."""
    # Remove version suffix like "-Snes-v0"
    cleaned = re.sub(r'-[A-Za-z0-9]+-v\d+$', '', name)

    # CamelCase to spaces: "SuperMarioWorld" -> "Super Mario World"
    cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
    cleaned = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', cleaned)

    # Numbers: "World2" -> "World 2"
    cleaned = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', cleaned)

    # Common abbreviations
    cleaned = re.sub(r'\bBros\b', 'Bros.', cleaned)
    cleaned = re.sub(r'\bDr\b', 'Dr.', cleaned)
    cleaned = re.sub(r'\bMr\b', 'Mr.', cleaned)
    cleaned = re.sub(r'\bMs\b', 'Ms.', cleaned)
    cleaned = re.sub(r'\bVs\b', 'Vs.', cleaned)
    cleaned = re.sub(r'\bSt\b', 'St.', cleaned)

    # Replace disallowed characters
    cleaned = re.sub(r'[&*/:"`<>?\\|]', '_', cleaned)

    return cleaned


def normalize_for_comparison(name: str) -> str:
    """Normalize a name for fuzzy comparison."""
    # Remove region suffix like (USA), (Japan), etc.
    normalized = re.sub(r'\s*\([^)]+\)\s*$', '', name)
    # Lowercase
    normalized = normalized.lower()
    # Remove punctuation and extra spaces
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def fuzzy_match(target: str, candidates: List[str], threshold: float = 0.7) -> List[Tuple[str, float]]:
    """Find fuzzy matches for a target name in a list of candidates."""
    target_norm = normalize_for_comparison(target)
    matches = []

    for candidate in candidates:
        candidate_norm = normalize_for_comparison(candidate)
        ratio = SequenceMatcher(None, target_norm, candidate_norm).ratio()

        if ratio >= threshold:
            matches.append((candidate, ratio))

    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


async def find_best_match(game: str, system: str) -> Tuple[Optional[str], str, Optional[float]]:
    """
    Find the best matching LibRetro thumbnail name for a game.
    Returns: (libretro_name, match_type, match_score)
    """
    cleaned_name = clean_game_name(game)
    print(f"[THUMB] Finding match for: {game} -> {cleaned_name}")

    index = await get_system_index(system)
    if not index:
        print(f"[THUMB] No index available for system: {system}")
        return None, "none", None

    # Try exact match first (with regions)
    for region in REGION_VARIANTS:
        full_name = f"{cleaned_name} {region}".strip() if region else cleaned_name
        if full_name in index:
            print(f"[THUMB] Exact match: {full_name}")
            return full_name, "exact", 1.0

    # Fuzzy match (threshold 0.75 to avoid false positives like "YarsRevenge" -> "Custer's Revenge")
    matches = fuzzy_match(cleaned_name, index, threshold=0.75)
    if matches:
        best_match, score = matches[0]
        print(f"[THUMB] Fuzzy match: {cleaned_name} -> {best_match} (score: {score:.2f})")

        # Prefer USA region if multiple matches have same score
        usa_matches = [m for m, s in matches if "(USA)" in m and s == score]
        if usa_matches:
            best_match = usa_matches[0]

        return best_match, "fuzzy", score

    print(f"[THUMB] No match found for: {cleaned_name}")
    return None, "none", None


# =============================================================================
# Image Fetching
# =============================================================================

def get_cache_key(system: str, game: str, thumb_type: str) -> str:
    """Generate a unique cache key for a thumbnail."""
    key = f"{system}:{game}:{thumb_type}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def get_cache_path(cache_key: str) -> Path:
    """Get the cache file path for a key."""
    return CACHE_DIR / f"{cache_key}.png"


async def fetch_image(libretro_system: str, libretro_name: str, thumb_type: str = "boxart") -> Optional[bytes]:
    """Fetch an image from LibRetro CDN."""
    folder = {
        "boxart": "Named_Boxarts",
        "snap": "Named_Snaps",
        "title": "Named_Titles",
    }.get(thumb_type, "Named_Boxarts")

    encoded_system = quote(libretro_system)
    encoded_name = quote(libretro_name)
    url = f"{LIBRETRO_CDN}/{encoded_system}/{folder}/{encoded_name}.png"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url)
            print(f"[THUMB] Fetch {url} -> {response.status_code}")
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "image" in content_type:
                    return response.content
        except httpx.RequestError as e:
            print(f"[THUMB] Request error: {e}")

    return None


async def fetch_thumbnail(system: str, game: str, thumb_type: str = "boxart") -> Optional[bytes]:
    """
    Fetch a thumbnail using multi-layer lookup:
    1. Check name mapping cache (from DB)
    2. Find best match (exact or fuzzy)
    3. Fetch from LibRetro
    """
    libretro_system = get_libretro_system(system)
    if not libretro_system:
        print(f"[THUMB] No LibRetro system mapping for: {system}")
        return None

    # Layer 1: Check name mapping cache (from DB)
    known_name = get_mapping_from_cache(system, game)
    if known_name:
        print(f"[THUMB] Using cached mapping: {game} -> {known_name}")
        image = await fetch_image(libretro_system, known_name, thumb_type)
        if image:
            return image

    # Layer 2: Find best match
    best_match, match_type, match_score = await find_best_match(game, system)
    if best_match:
        image = await fetch_image(libretro_system, best_match, thumb_type)
        if image:
            # Save the mapping to DB for future use
            save_mapping_to_db(system, game, best_match, match_type, match_score)
            return image

    # Record failure
    save_failure_to_db(system, game)
    print(f"[THUMB] FAILED: No image found for {game}")
    return None


# =============================================================================
# Routes (static routes MUST come before dynamic routes)
# =============================================================================

@router.delete("/cache")
async def clear_cache():
    """Clear all cached thumbnails and mappings."""
    global _mappings_cache, _failures_cache

    # Clear image files
    img_count = 0
    for file in CACHE_DIR.glob("*.png"):
        try:
            file.unlink()
            img_count += 1
        except IOError:
            pass

    # Clear DB mappings
    db = SessionLocal()
    try:
        map_count = db.query(ThumbnailMapping).delete()
        fail_count = db.query(ThumbnailFailure).delete()
        db.commit()
    except Exception as e:
        print(f"[THUMB] Error clearing DB: {e}")
        db.rollback()
        map_count = 0
        fail_count = 0
    finally:
        db.close()

    # Clear memory caches
    _cache_key_map.clear()
    _mappings_cache.clear()
    _failures_cache.clear()

    return {
        "images_cleared": img_count,
        "mappings_cleared": map_count,
        "failures_cleared": fail_count,
    }


@router.delete("/cache/failures")
async def clear_failures():
    """Clear only failure records (retry failed lookups)."""
    global _failures_cache

    db = SessionLocal()
    try:
        count = db.query(ThumbnailFailure).delete()
        db.commit()
    except Exception as e:
        print(f"[THUMB] Error clearing failures: {e}")
        db.rollback()
        count = 0
    finally:
        db.close()

    _failures_cache.clear()
    return {"failures_cleared": count}


@router.delete("/cache/index")
async def clear_index():
    """Clear cached system indexes (forces re-fetch from GitHub)."""
    global _system_indexes
    count = 0
    for file in INDEX_DIR.glob("*.json"):
        try:
            file.unlink()
            count += 1
        except IOError:
            pass

    _system_indexes.clear()
    return {"index_files_cleared": count}


@router.get("/cache/stats")
async def cache_stats():
    """Get thumbnail cache statistics."""
    files = list(CACHE_DIR.glob("*.png"))
    total_size = sum(f.stat().st_size for f in files)
    index_files = list(INDEX_DIR.glob("*.json"))

    # Get DB counts
    db = SessionLocal()
    try:
        mapping_count = db.query(ThumbnailMapping).count()
        failure_count = db.query(ThumbnailFailure).count()

        # Get match type breakdown
        from sqlalchemy import func
        match_types = db.query(
            ThumbnailMapping.match_type,
            func.count(ThumbnailMapping.id)
        ).group_by(ThumbnailMapping.match_type).all()
        match_breakdown = {mt: count for mt, count in match_types}
    except Exception as e:
        print(f"[THUMB] Error getting stats: {e}")
        mapping_count = len(_mappings_cache)
        failure_count = len(_failures_cache)
        match_breakdown = {}
    finally:
        db.close()

    return {
        "images": {
            "count": len(files),
            "size_bytes": total_size,
            "size_mb": round(total_size / (1024 * 1024), 2),
        },
        "indexes": {
            "cached_systems": len(index_files),
            "loaded_systems": len(_system_indexes),
        },
        "mappings": {
            "total": mapping_count,
            "by_type": match_breakdown,
            "in_memory": len(_mappings_cache),
        },
        "failures": {
            "total": failure_count,
            "in_memory": len(_failures_cache),
        },
    }


@router.get("/cache/mappings")
async def cache_mappings(limit: int = 100, offset: int = 0):
    """Get name mappings from DB (paginated)."""
    db = SessionLocal()
    try:
        total = db.query(ThumbnailMapping).count()
        mappings = db.query(ThumbnailMapping).order_by(
            ThumbnailMapping.created_at.desc()
        ).offset(offset).limit(limit).all()

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "mappings": [
                {
                    "system": m.system,
                    "game_id": m.game_id,
                    "libretro_name": m.libretro_name,
                    "match_type": m.match_type,
                    "match_score": m.match_score,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in mappings
            ],
        }
    finally:
        db.close()


@router.get("/cache/failures")
async def get_failures(limit: int = 100, offset: int = 0):
    """Get failed lookups from DB (paginated)."""
    db = SessionLocal()
    try:
        total = db.query(ThumbnailFailure).count()
        failures = db.query(ThumbnailFailure).order_by(
            ThumbnailFailure.last_attempt.desc()
        ).offset(offset).limit(limit).all()

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "failures": [
                {
                    "system": f.system,
                    "game_id": f.game_id,
                    "attempts": f.attempts,
                    "last_attempt": f.last_attempt.isoformat() if f.last_attempt else None,
                }
                for f in failures
            ],
        }
    finally:
        db.close()


@router.post("/index/refresh/{system}")
async def refresh_system_index(system: str):
    """Force refresh the thumbnail index for a system."""
    libretro_system = get_libretro_system(system)
    if not libretro_system:
        raise HTTPException(status_code=400, detail=f"Unknown system: {system}")

    # Clear cached index
    index_path = get_index_path(libretro_system)
    if index_path.exists():
        index_path.unlink()

    if libretro_system in _system_indexes:
        del _system_indexes[libretro_system]

    # Fetch fresh
    index = await get_system_index(system)
    return {
        "system": system,
        "libretro_system": libretro_system,
        "thumbnail_count": len(index),
    }


# Dynamic route MUST come last
@router.get("/{system}/{game}")
async def get_thumbnail(
    system: str,
    game: str,
    type: str = "boxart"
) -> Response:
    """
    Get a game thumbnail. Uses multi-layer lookup:
    1. Check local image cache
    2. Check name mapping from DB
    3. Exact match with region variants
    4. Fuzzy match against LibRetro index
    """
    if type not in ("boxart", "snap", "title"):
        type = "boxart"

    cache_key = get_cache_key(system, game, type)
    cache_path = get_cache_path(cache_key)

    # Layer 0: Check image cache first
    if cache_path.exists():
        _cache_key_map[cache_key] = f"{system}:{game}:{type}"
        print(f"[THUMB] CACHE HIT: {game} -> {cache_key}")
        return FileResponse(
            cache_path,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=31536000"}
        )

    # Check if known failure (skip expensive lookup)
    if is_known_failure(system, game):
        raise HTTPException(status_code=404, detail="Thumbnail not found (known failure)")

    # Fetch using multi-layer lookup
    image_data = await fetch_thumbnail(system, game, type)

    if image_data is None:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    # Save to cache
    try:
        cache_path.write_bytes(image_data)
        _cache_key_map[cache_key] = f"{system}:{game}:{type}"
        print(f"[THUMB] CACHED: {game} -> {cache_key}")
    except IOError:
        pass

    return Response(
        content=image_data,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=31536000"}
    )


# Load mappings from DB on module import
load_mappings_to_memory()
