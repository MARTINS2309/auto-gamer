"""
IGDB (Internet Game Database) API Service.

Uses Twitch OAuth2 for authentication.
Docs: https://api-docs.igdb.com/
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx

# Token cache
_token_cache: dict[str, Any] = {
    "access_token": None,
    "expires_at": None,
}


@dataclass
class GameMetadata:
    """Structured game metadata from IGDB."""

    igdb_id: int
    name: str
    summary: str | None = None
    storyline: str | None = None
    rating: float | None = None
    rating_count: int | None = None
    genres: list[str] = None
    themes: list[str] = None
    game_modes: list[str] = None
    player_perspectives: list[str] = None
    platforms: list[str] = None
    release_date: str | None = None
    developer: str | None = None
    publisher: str | None = None
    cover_url: str | None = None
    screenshot_urls: list[str] = None

    def __post_init__(self):
        if self.genres is None:
            self.genres = []
        if self.themes is None:
            self.themes = []
        if self.game_modes is None:
            self.game_modes = []
        if self.player_perspectives is None:
            self.player_perspectives = []
        if self.platforms is None:
            self.platforms = []
        if self.screenshot_urls is None:
            self.screenshot_urls = []


async def get_access_token(client_id: str, client_secret: str) -> str | None:
    """Get OAuth2 access token from Twitch."""
    global _token_cache

    # Check cache
    if _token_cache["access_token"] and _token_cache["expires_at"]:
        if datetime.utcnow() < _token_cache["expires_at"]:
            return str(_token_cache["access_token"])

    # Get new token
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, params=params)
            if response.status_code == 200:
                data = response.json()
                _token_cache["access_token"] = data["access_token"]
                # Token typically expires in ~60 days, but refresh at 50 days
                _token_cache["expires_at"] = datetime.utcnow() + timedelta(days=50)
                print(
                    f"[IGDB] Got new access token, expires in {data.get('expires_in', 0)} seconds"
                )
                return str(data["access_token"])
            else:
                print(f"[IGDB] Failed to get token: {response.status_code} {response.text}")
        except Exception as e:
            print(f"[IGDB] Error getting token: {e}")

    return None


class SearchResult:
    """Result of an IGDB search - distinguishes between not_found and errors."""

    def __init__(
        self, metadata: GameMetadata | None = None, not_found: bool = False, error: bool = False
    ):
        self.metadata = metadata
        self.not_found = not_found  # Game genuinely doesn't exist in IGDB
        self.error = error  # API error (rate limit, network, etc.) - should retry later


async def search_game(
    name: str, client_id: str, client_secret: str, platform_filter: str | None = None
) -> SearchResult:
    """
    Search for a game by name and return metadata.

    Args:
        name: Game name to search
        client_id: IGDB/Twitch Client ID
        client_secret: IGDB/Twitch Client Secret
        platform_filter: Optional platform name to filter (e.g., "Sega Genesis")

    Returns:
        SearchResult with metadata if found, not_found=True if game doesn't exist,
        or error=True if there was an API error (should retry later).
    """
    token = await get_access_token(client_id, client_secret)
    if not token:
        return SearchResult(error=True)

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}",
    }

    # IGDB search with version_parent = null to exclude editions/remasters
    query = f'''search "{name}";
fields name, summary, storyline, rating, rating_count,
       genres.name, themes.name, game_modes.name, player_perspectives.name,
       platforms.name, first_release_date,
       involved_companies.company.name, involved_companies.developer, involved_companies.publisher,
       cover.url, screenshots.url;
where version_parent = null;
limit 20;'''

    print(f"[IGDB] Searching: '{name}' (platform: {platform_filter})")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.igdb.com/v4/games", headers=headers, content=query, timeout=10.0
            )

            if response.status_code == 200:
                results = response.json()
                if not results:
                    print(f"[IGDB] No results for: {name}")
                    return SearchResult(not_found=True)

                print(f"[IGDB] Found {len(results)} results")

                # Use shared scoring logic
                best_game = _select_best_game(results, name, platform_filter)

                if best_game:
                    print(f"[IGDB] Selected: {best_game.get('name')}")
                    return SearchResult(metadata=_parse_game_response(best_game))
                else:
                    # Fallback to first result
                    return SearchResult(metadata=_parse_game_response(results[0]))
            elif response.status_code == 429:
                print("[IGDB] Rate limited (429) - will retry later")
                return SearchResult(error=True)
            else:
                print(f"[IGDB] Search failed: {response.status_code} {response.text}")
                return SearchResult(error=True)

        except Exception as e:
            print(f"[IGDB] Error searching: {e}")
            return SearchResult(error=True)


async def get_game_by_id(igdb_id: int, client_id: str, client_secret: str) -> GameMetadata | None:
    """Get game metadata by IGDB ID."""
    token = await get_access_token(client_id, client_secret)
    if not token:
        return None

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}",
    }

    query = f"""
        fields name, summary, storyline, rating, rating_count,
               genres.name, themes.name, game_modes.name, player_perspectives.name,
               platforms.name, first_release_date,
               involved_companies.company.name, involved_companies.developer, involved_companies.publisher,
               cover.url, screenshots.url;
        where id = {igdb_id};
    """

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.igdb.com/v4/games", headers=headers, content=query, timeout=10.0
            )

            if response.status_code == 200:
                results = response.json()
                if results:
                    return _parse_game_response(results[0])

        except Exception as e:
            print(f"[IGDB] Error fetching game {igdb_id}: {e}")

    return None


def _parse_game_response(game: dict[str, Any]) -> GameMetadata:
    """Parse IGDB API response into GameMetadata."""
    # Extract company info
    developer = None
    publisher = None
    for company in game.get("involved_companies", []):
        company_name = company.get("company", {}).get("name")
        if company.get("developer") and not developer:
            developer = company_name
        if company.get("publisher") and not publisher:
            publisher = company_name

    # Parse release date
    release_date = None
    if "first_release_date" in game:
        try:
            release_date = datetime.fromtimestamp(game["first_release_date"]).strftime("%Y-%m-%d")
        except Exception:
            pass

    # Parse cover URL (IGDB returns thumb size, convert to bigger)
    cover_url = None
    if game.get("cover", {}).get("url"):
        cover_url = game["cover"]["url"].replace("t_thumb", "t_cover_big")
        if not cover_url.startswith("http"):
            cover_url = "https:" + cover_url

    # Parse screenshots
    screenshot_urls = []
    for ss in game.get("screenshots", []):
        url = ss.get("url", "")
        if url:
            url = url.replace("t_thumb", "t_screenshot_big")
            if not url.startswith("http"):
                url = "https:" + url
            screenshot_urls.append(url)

    return GameMetadata(
        igdb_id=game["id"],
        name=game["name"],
        summary=game.get("summary"),
        storyline=game.get("storyline"),
        rating=game.get("rating"),
        rating_count=game.get("rating_count"),
        genres=[g["name"] for g in game.get("genres", [])],
        themes=[t["name"] for t in game.get("themes", [])],
        game_modes=[m["name"] for m in game.get("game_modes", [])],
        player_perspectives=[p["name"] for p in game.get("player_perspectives", [])],
        platforms=[p["name"] for p in game.get("platforms", [])],
        release_date=release_date,
        developer=developer,
        publisher=publisher,
        cover_url=cover_url,
        screenshot_urls=screenshot_urls,
    )


# Platform mapping from our system IDs to IGDB platform names
PLATFORM_MAP = {
    "Nes": "Nintendo Entertainment System",
    "Snes": "Super Nintendo Entertainment System",
    "N64": "Nintendo 64",
    "GameBoy": "Game Boy",
    "Gb": "Game Boy",
    "Gbc": "Game Boy Color",
    "Gba": "Game Boy Advance",
    "NintendoDS": "Nintendo DS",
    "Nds": "Nintendo DS",
    "Genesis": "Sega Genesis",
    "MegaDrive": "Sega Mega Drive",
    "Sms": "Sega Master System",
    "MasterSystem": "Sega Master System",
    "GameGear": "Sega Game Gear",
    "Gg": "Sega Game Gear",
    "Saturn": "Sega Saturn",
    "Dreamcast": "Dreamcast",
    "Atari2600": "Atari 2600",
    "Atari5200": "Atari 5200",
    "Atari7800": "Atari 7800",
    "Psx": "PlayStation",
    "PlayStation": "PlayStation",
    "Psp": "PlayStation Portable",
    "Arcade": "Arcade",
    "PCEngine": "TurboGrafx-16",
    "TurboGrafx16": "TurboGrafx-16",
    "NeoGeo": "Neo Geo",
}


def get_igdb_platform(system: str) -> str | None:
    """Map our system ID to IGDB platform name."""
    return PLATFORM_MAP.get(system)


# =============================================================================
# Scoring Logic (shared between single and batch searches)
# =============================================================================


def _normalize_name(name: str) -> str:
    """Normalize name for comparison - remove articles, punctuation, extra spaces."""
    import re
    n = name.lower()
    n = n.replace("the", "").replace("  ", " ")
    # Remove punctuation that varies between versions (dots, apostrophes, colons)
    n = re.sub(r"[.:'\"!?]", "", n)
    # Normalize spaces
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _score_game_result(
    game: dict[str, Any], search_name: str, platform_filter: str | None = None
) -> int:
    """Score a game result based on name and platform match."""
    name_lower = _normalize_name(search_name)
    r_name = _normalize_name(game.get("name", ""))
    r_platforms = [p.get("name", "").lower() for p in game.get("platforms", [])]

    score = 0
    platform_matched = False

    # Platform match is critical for retro games
    if platform_filter:
        pf_lower = platform_filter.lower()
        for p in r_platforms:
            # Genesis/Mega Drive matching
            if "genesis" in pf_lower and ("genesis" in p or "mega drive" in p):
                score += 100
                platform_matched = True
                break
            # NES/Famicom matching
            if "nintendo entertainment system" in pf_lower and (
                "nes" in p or "famicom" in p or "nintendo entertainment" in p
            ):
                score += 100
                platform_matched = True
                break
            # SNES/Super Famicom matching
            if "super nintendo" in pf_lower and (
                "snes" in p or "super famicom" in p or "super nintendo" in p
            ):
                score += 100
                platform_matched = True
                break
            # Direct match for other platforms
            if pf_lower in p or p in pf_lower:
                score += 100
                platform_matched = True
                break

        # No platform match = big penalty
        if not platform_matched:
            score -= 80

    # Name matching - exact match is best
    if r_name == name_lower:
        score += 200  # Exact match is very important
    elif name_lower in r_name and len(r_name) < len(name_lower) * 1.5:
        score += 100  # Close match
    elif r_name in name_lower:
        score += 50

    # Penalize fan games, hacks, mods (usually have extra words)
    if "hack" in r_name or "mod" in r_name or "another" in r_name:
        score -= 100
    if len(r_name) > len(name_lower) * 2:
        score -= 30

    # Penalize non-retro platforms when searching for retro games
    modern_platforms = [
        "pc (microsoft windows)",
        "playstation 3",
        "playstation 4",
        "xbox 360",
        "xbox one",
        "wii u",
        "switch",
    ]
    if platform_filter and any(mp in r_platforms for mp in modern_platforms):
        # Only penalize if the retro platform is NOT also present
        if not platform_matched:
            score -= 50

    return score


def _select_best_game(
    results: list[dict[str, Any]], search_name: str, platform_filter: str | None = None
) -> dict[str, Any] | None:
    """Select the best matching game from search results."""
    best_game = None
    best_score = -1

    for r in results:
        score = _score_game_result(r, search_name, platform_filter)
        if score > best_score:
            best_score = score
            best_game = r

    return best_game


# =============================================================================
# Rate Limiting
# =============================================================================

# IGDB allows 4 requests/second - use lock to ensure global rate limiting
_rate_limit_lock = asyncio.Lock()
_RATE_LIMIT_DELAY = 0.35  # 350ms between requests = ~2.8 req/sec (extra safe)
_last_request_time: float = 0


async def _rate_limited_request() -> None:
    """Wait for rate limit before making a request."""
    global _last_request_time
    async with _rate_limit_lock:
        now = asyncio.get_event_loop().time()
        elapsed = now - _last_request_time
        if elapsed < _RATE_LIMIT_DELAY:
            await asyncio.sleep(_RATE_LIMIT_DELAY - elapsed)
        _last_request_time = asyncio.get_event_loop().time()


# =============================================================================
# Name Cleaning & Variants
# =============================================================================


def _generate_search_variants(name: str) -> list[str]:
    """Generate alternative search queries for a game name."""
    import re

    variants = [name]  # Original name first

    # Remove "The" prefix/suffix
    no_the = name.replace("The ", "").replace(" The", "")
    if no_the != name and no_the not in variants:
        variants.append(no_the)

    # Remove common subtitle separators and everything after
    for sep in [" - ", ": ", " – ", " — "]:
        if sep in name:
            base = name.split(sep)[0].strip()
            if base and base not in variants:
                variants.append(base)

    # Remove parenthetical content (region codes, etc.)
    no_parens = re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()
    no_parens = re.sub(r"\s+", " ", no_parens)  # Clean up double spaces
    if no_parens != name and no_parens not in variants:
        variants.append(no_parens)

    # Remove version numbers like "v1.0", "Rev A"
    no_version = re.sub(r"\s*[vV]\d+\.?\d*\s*", " ", name).strip()
    no_version = re.sub(r"\s*Rev\s*[A-Z0-9]+\s*", " ", no_version, flags=re.IGNORECASE).strip()
    no_version = re.sub(r"\s+", " ", no_version)
    if no_version != name and no_version not in variants:
        variants.append(no_version)

    # Add common romanization alternatives (e.g., "2" -> "II")
    if " 2" in name:
        variant = name.replace(" 2", " II")
        if variant not in variants:
            variants.append(variant)
    if " 3" in name:
        variant = name.replace(" 3", " III")
        if variant not in variants:
            variants.append(variant)
    if " 4" in name:
        variant = name.replace(" 4", " IV")
        if variant not in variants:
            variants.append(variant)

    # Try without spaces for compound words (only short names)
    no_spaces = name.replace(" ", "")
    if no_spaces != name and len(no_spaces) < 15 and no_spaces not in variants:
        variants.append(no_spaces)

    return variants[:5]  # Max 5 variants


# =============================================================================
# PHASE 1: DISCOVERY - Find IGDB game IDs by searching
# =============================================================================


@dataclass
class DiscoveryRequest:
    """Request for discovering a single game's IGDB ID."""

    search_name: str  # Name to search for
    platform_filter: str | None = None  # IGDB platform name (e.g., "Sega Genesis")
    internal_id: str | None = None  # Our internal ID (ROM id, connector id) for tracking
    system: str | None = None  # Our internal system ID for tracking


@dataclass
class DiscoveryResult:
    """Result of discovery phase - just the IGDB ID (or not found/error)."""

    igdb_id: int | None = None
    igdb_name: str | None = None  # Name as it appears in IGDB (for logging)
    not_found: bool = False  # Game genuinely not in IGDB
    error: bool = False  # API error - should retry later


async def _discover_single(
    name: str,
    client_id: str,
    client_secret: str,
    platform_filter: str | None = None,
) -> DiscoveryResult:
    """
    Search IGDB for a game and return its ID.

    This is a lightweight search - we only need the ID, not full metadata.
    """
    await _rate_limited_request()

    print(f"[IGDB:DISCOVERY] Searching: '{name}' (platform: {platform_filter})")

    token = await get_access_token(client_id, client_secret)
    if not token:
        print("[IGDB:DISCOVERY] ERROR: Failed to get access token")
        return DiscoveryResult(error=True)

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}",
    }

    # Minimal fields - just need id, name, and platforms for scoring
    query = f'''search "{name}";
fields id, name, platforms.name;
where version_parent = null;
limit 20;'''

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.igdb.com/v4/games", headers=headers, content=query, timeout=10.0
            )

            if response.status_code == 200:
                results = response.json()
                print(f"[IGDB:DISCOVERY] Got {len(results)} results for '{name}'")

                if not results:
                    print(f"[IGDB:DISCOVERY] No results for '{name}'")
                    return DiscoveryResult(not_found=True)

                # Log all candidates for debugging
                for i, r in enumerate(results[:5]):  # Top 5
                    platforms = [p.get("name", "?") for p in r.get("platforms", [])]
                    score = _score_game_result(r, name, platform_filter)
                    print(f"[IGDB:DISCOVERY]   #{i+1}: '{r.get('name')}' (id={r['id']}, platforms={platforms[:3]}, score={score})")

                # Use scoring to pick best match
                best_game = _select_best_game(results, name, platform_filter)
                if best_game:
                    print(f"[IGDB:DISCOVERY] Selected: '{best_game.get('name')}' (id={best_game['id']})")
                    return DiscoveryResult(
                        igdb_id=best_game["id"], igdb_name=best_game.get("name")
                    )

                # Fallback to first result
                print(f"[IGDB:DISCOVERY] Fallback to first: '{results[0].get('name')}' (id={results[0]['id']})")
                return DiscoveryResult(
                    igdb_id=results[0]["id"], igdb_name=results[0].get("name")
                )

            elif response.status_code == 429:
                print(f"[IGDB:DISCOVERY] ERROR: Rate limited (429) for '{name}'")
                return DiscoveryResult(error=True)
            else:
                print(f"[IGDB:DISCOVERY] ERROR: HTTP {response.status_code} for '{name}': {response.text[:200]}")
                return DiscoveryResult(error=True)

        except httpx.TimeoutException:
            print(f"[IGDB:DISCOVERY] ERROR: Timeout for '{name}'")
            return DiscoveryResult(error=True)
        except Exception as e:
            print(f"[IGDB:DISCOVERY] ERROR: Exception for '{name}': {type(e).__name__}: {e}")
            return DiscoveryResult(error=True)


async def discover_game(
    name: str,
    client_id: str,
    client_secret: str,
    platform_filter: str | None = None,
    try_variants: bool = True,
) -> DiscoveryResult:
    """
    Discover a game's IGDB ID by searching with name variants.

    Phase 1 of the two-phase approach:
    - Try original name first
    - If not found, try cleaned variants (no region codes, subtitles, etc.)
    - Use platform filter to pick best match when multiple results

    Args:
        name: Game name to search
        client_id: IGDB/Twitch Client ID
        client_secret: IGDB/Twitch Client Secret
        platform_filter: IGDB platform name (e.g., "Sega Genesis")
        try_variants: Whether to try alternate name forms if not found

    Returns:
        DiscoveryResult with igdb_id if found, not_found=True if exhausted all variants,
        or error=True if API error occurred.
    """
    search_names = _generate_search_variants(name) if try_variants else [name]

    for variant in search_names:
        result = await _discover_single(variant, client_id, client_secret, platform_filter)

        if result.igdb_id:
            print(f"[IGDB] Discovered: '{name}' -> {result.igdb_id} ({result.igdb_name})")
            return result

        if result.error:
            # API error - stop trying variants, return error
            return result

        # Not found with this variant - try next

    print(f"[IGDB] Not found: '{name}' (tried {len(search_names)} variants)")
    return DiscoveryResult(not_found=True)


async def discover_games_batch(
    requests: list[DiscoveryRequest],
    client_id: str,
    client_secret: str,
    try_variants: bool = True,
) -> dict[str, DiscoveryResult]:
    """
    Discover IGDB IDs for multiple games.

    This is rate-limited and sequential (one search at a time).
    Use this to build up a list of IDs, then batch_fetch_metadata() for the actual data.

    Args:
        requests: List of DiscoveryRequest objects
        client_id: IGDB/Twitch Client ID
        client_secret: IGDB/Twitch Client Secret
        try_variants: Whether to try alternate name forms if not found

    Returns:
        Dict mapping internal_id to DiscoveryResult
    """
    if not requests:
        return {}

    print(f"[IGDB] Discovering {len(requests)} games...")
    results: dict[str, DiscoveryResult] = {}
    found = 0
    errors = 0

    for i, req in enumerate(requests):
        result = await discover_game(
            req.search_name,
            client_id,
            client_secret,
            req.platform_filter,
            try_variants,
        )

        key = req.internal_id or req.search_name
        results[key] = result

        if result.igdb_id:
            found += 1
        elif result.error:
            errors += 1

        # Progress logging every 10 items
        if (i + 1) % 10 == 0 or i == len(requests) - 1:
            print(f"[IGDB] Discovery progress: {i + 1}/{len(requests)} (found: {found}, errors: {errors})")

    print(f"[IGDB] Discovery complete: {found}/{len(requests)} found, {errors} errors")
    return results


# =============================================================================
# PHASE 2: BATCH FETCH - Get metadata for known IGDB IDs
# =============================================================================


async def batch_fetch_metadata(
    igdb_ids: list[int],
    client_id: str,
    client_secret: str,
    batch_size: int = 10,
) -> dict[int, GameMetadata | None]:
    """
    Fetch full metadata for multiple games by their IGDB IDs.

    Phase 2 of the two-phase approach:
    - Uses IGDB's ability to fetch multiple games by ID in one request
    - Much faster than searching (one request per batch vs one per game)

    Args:
        igdb_ids: List of IGDB game IDs to fetch
        client_id: IGDB/Twitch Client ID
        client_secret: IGDB/Twitch Client Secret
        batch_size: Number of IDs per request (max 10 recommended)

    Returns:
        Dict mapping igdb_id to GameMetadata (or None if fetch failed)
    """
    if not igdb_ids:
        print("[IGDB:BATCH] No IDs to fetch")
        return {}

    num_batches = (len(igdb_ids) + batch_size - 1) // batch_size
    print(f"[IGDB:BATCH] Fetching metadata for {len(igdb_ids)} games in {num_batches} batches...")

    token = await get_access_token(client_id, client_secret)
    if not token:
        print("[IGDB:BATCH] ERROR: Failed to get access token")
        return {id: None for id in igdb_ids}

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}",
    }

    results: dict[int, GameMetadata | None] = {}

    # Process in batches
    for batch_num, batch_start in enumerate(range(0, len(igdb_ids), batch_size)):
        batch = igdb_ids[batch_start : batch_start + batch_size]

        await _rate_limited_request()

        # Build query for multiple IDs
        ids_str = ",".join(str(id) for id in batch)
        query = f"""
fields name, summary, storyline, rating, rating_count,
       genres.name, themes.name, game_modes.name, player_perspectives.name,
       platforms.name, first_release_date,
       involved_companies.company.name, involved_companies.developer, involved_companies.publisher,
       cover.url, screenshots.url;
where id = ({ids_str});
limit {batch_size};
"""

        print(f"[IGDB:BATCH] Batch {batch_num + 1}/{num_batches}: fetching IDs {batch}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://api.igdb.com/v4/games",
                    headers=headers,
                    content=query,
                    timeout=15.0,
                )

                if response.status_code == 200:
                    games = response.json()
                    print(f"[IGDB:BATCH] Batch {batch_num + 1}: got {len(games)} games")

                    for game in games:
                        metadata = _parse_game_response(game)
                        results[metadata.igdb_id] = metadata
                        print(f"[IGDB:BATCH]   - {metadata.igdb_id}: '{metadata.name}' (cover: {bool(metadata.cover_url)})")

                    # Mark any IDs in this batch not returned as None
                    returned_ids = {g["id"] for g in games}
                    missing = [id for id in batch if id not in returned_ids]
                    if missing:
                        print(f"[IGDB:BATCH] WARNING: IDs not returned: {missing}")
                    for id in batch:
                        if id not in returned_ids:
                            results[id] = None

                elif response.status_code == 429:
                    print(f"[IGDB:BATCH] ERROR: Rate limited (429) on batch {batch_num + 1}")
                    for id in batch:
                        results[id] = None
                else:
                    print(f"[IGDB:BATCH] ERROR: HTTP {response.status_code} on batch {batch_num + 1}: {response.text[:200]}")
                    for id in batch:
                        results[id] = None

            except httpx.TimeoutException:
                print(f"[IGDB:BATCH] ERROR: Timeout on batch {batch_num + 1}")
                for id in batch:
                    results[id] = None
            except Exception as e:
                print(f"[IGDB:BATCH] ERROR: Exception on batch {batch_num + 1}: {type(e).__name__}: {e}")
                for id in batch:
                    results[id] = None

        # Progress
        fetched = batch_start + len(batch)
        success = sum(1 for v in results.values() if v is not None)
        print(f"[IGDB] Batch fetch progress: {fetched}/{len(igdb_ids)} (success: {success})")

    return results


# =============================================================================
# COMBINED: Discover + Fetch in one call (convenience wrapper)
# =============================================================================


@dataclass
class GameSearchRequest:
    """Request for a single game in a batch search."""

    search_name: str  # Name to search for
    platform_filter: str | None = None  # IGDB platform name
    game_id: str | None = None  # Our internal game ID (for tracking)
    system: str | None = None  # Our internal system ID (for tracking)


async def search_games_batch(
    requests: list[GameSearchRequest],
    client_id: str,
    client_secret: str,
) -> dict[str, SearchResult]:
    """
    Search for multiple games - combines discovery and fetch phases.

    This is the original API preserved for backwards compatibility.
    For better control, use discover_games_batch() then batch_fetch_metadata().

    Args:
        requests: List of GameSearchRequest objects
        client_id: IGDB/Twitch Client ID
        client_secret: IGDB/Twitch Client Secret

    Returns:
        Dict mapping game_id to SearchResult (check .metadata, .not_found, .error)
    """
    if not requests:
        return {}

    print(f"[IGDB] Batch searching {len(requests)} games (two-phase approach)...")

    # Phase 1: Discovery
    discovery_requests = [
        DiscoveryRequest(
            search_name=r.search_name,
            platform_filter=r.platform_filter,
            internal_id=r.game_id,
            system=r.system,
        )
        for r in requests
    ]

    discovery_results = await discover_games_batch(
        discovery_requests, client_id, client_secret, try_variants=True
    )

    # Collect IDs that were found
    id_map: dict[str, int] = {}  # internal_id -> igdb_id
    igdb_ids: list[int] = []
    for game_id, disc in discovery_results.items():
        if disc.igdb_id:
            id_map[game_id] = disc.igdb_id
            if disc.igdb_id not in igdb_ids:
                igdb_ids.append(disc.igdb_id)

    # Phase 2: Batch fetch metadata for found games
    metadata_map: dict[int, GameMetadata | None] = {}
    if igdb_ids:
        metadata_map = await batch_fetch_metadata(igdb_ids, client_id, client_secret)

    # Build final results
    results: dict[str, SearchResult] = {}
    for req in requests:
        game_id = req.game_id or req.search_name  # Fallback to search_name if no game_id
        disc = discovery_results.get(game_id)

        if disc is None:
            results[game_id] = SearchResult(error=True)
        elif disc.error:
            results[game_id] = SearchResult(error=True)
        elif disc.not_found:
            results[game_id] = SearchResult(not_found=True)
        elif disc.igdb_id:
            metadata = metadata_map.get(disc.igdb_id)
            if metadata:
                results[game_id] = SearchResult(metadata=metadata)
            else:
                # Had ID but fetch failed
                results[game_id] = SearchResult(error=True)
        else:
            results[game_id] = SearchResult(not_found=True)

    found_count = sum(1 for r in results.values() if r.metadata)
    print(f"[IGDB] Batch complete: {found_count}/{len(requests)} with metadata")
    return results
