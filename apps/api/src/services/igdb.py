"""
IGDB (Internet Game Database) API Service.

Uses Twitch OAuth2 for authentication.
Docs: https://api-docs.igdb.com/
"""

import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio

# Token cache
_token_cache: Dict[str, Any] = {
    "access_token": None,
    "expires_at": None,
}


@dataclass
class GameMetadata:
    """Structured game metadata from IGDB."""
    igdb_id: int
    name: str
    summary: Optional[str] = None
    storyline: Optional[str] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    genres: List[str] = None
    themes: List[str] = None
    game_modes: List[str] = None
    player_perspectives: List[str] = None
    platforms: List[str] = None
    release_date: Optional[str] = None
    developer: Optional[str] = None
    publisher: Optional[str] = None
    cover_url: Optional[str] = None
    screenshot_urls: List[str] = None

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


async def get_access_token(client_id: str, client_secret: str) -> Optional[str]:
    """Get OAuth2 access token from Twitch."""
    global _token_cache

    # Check cache
    if _token_cache["access_token"] and _token_cache["expires_at"]:
        if datetime.utcnow() < _token_cache["expires_at"]:
            return _token_cache["access_token"]

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
                print(f"[IGDB] Got new access token, expires in {data.get('expires_in', 0)} seconds")
                return data["access_token"]
            else:
                print(f"[IGDB] Failed to get token: {response.status_code} {response.text}")
        except Exception as e:
            print(f"[IGDB] Error getting token: {e}")

    return None


async def search_game(
    name: str,
    client_id: str,
    client_secret: str,
    platform_filter: Optional[str] = None
) -> Optional[GameMetadata]:
    """
    Search for a game by name and return metadata.

    Args:
        name: Game name to search
        client_id: IGDB/Twitch Client ID
        client_secret: IGDB/Twitch Client Secret
        platform_filter: Optional platform name to filter (e.g., "Sega Genesis")
    """
    token = await get_access_token(client_id, client_secret)
    if not token:
        return None

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
                "https://api.igdb.com/v4/games",
                headers=headers,
                content=query,
                timeout=10.0
            )

            if response.status_code == 200:
                results = response.json()
                if not results:
                    print(f"[IGDB] No results for: {name}")
                    return None

                print(f"[IGDB] Found {len(results)} results")

                # Use shared scoring logic
                best_game = _select_best_game(results, name, platform_filter)

                if best_game:
                    print(f"[IGDB] Selected: {best_game.get('name')}")
                    return _parse_game_response(best_game)
                else:
                    # Fallback to first result
                    return _parse_game_response(results[0])
            else:
                print(f"[IGDB] Search failed: {response.status_code} {response.text}")

        except Exception as e:
            print(f"[IGDB] Error searching: {e}")

    return None


async def get_game_by_id(
    igdb_id: int,
    client_id: str,
    client_secret: str
) -> Optional[GameMetadata]:
    """Get game metadata by IGDB ID."""
    token = await get_access_token(client_id, client_secret)
    if not token:
        return None

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}",
    }

    query = f'''
        fields name, summary, storyline, rating, rating_count,
               genres.name, themes.name, game_modes.name, player_perspectives.name,
               platforms.name, first_release_date,
               involved_companies.company.name, involved_companies.developer, involved_companies.publisher,
               cover.url, screenshots.url;
        where id = {igdb_id};
    '''

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.igdb.com/v4/games",
                headers=headers,
                content=query,
                timeout=10.0
            )

            if response.status_code == 200:
                results = response.json()
                if results:
                    return _parse_game_response(results[0])

        except Exception as e:
            print(f"[IGDB] Error fetching game {igdb_id}: {e}")

    return None


def _parse_game_response(game: Dict[str, Any]) -> GameMetadata:
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
        except:
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


def get_igdb_platform(system: str) -> Optional[str]:
    """Map our system ID to IGDB platform name."""
    return PLATFORM_MAP.get(system)


# =============================================================================
# Scoring Logic (shared between single and batch searches)
# =============================================================================

def _score_game_result(
    game: Dict[str, Any],
    search_name: str,
    platform_filter: Optional[str] = None
) -> int:
    """Score a game result based on name and platform match."""
    name_lower = search_name.lower().replace("the", "").replace("  ", " ").strip()
    r_name = game.get("name", "").lower().replace("the", "").replace("  ", " ").strip()
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
            if "nintendo entertainment system" in pf_lower and ("nes" in p or "famicom" in p or "nintendo entertainment" in p):
                score += 100
                platform_matched = True
                break
            # SNES/Super Famicom matching
            if "super nintendo" in pf_lower and ("snes" in p or "super famicom" in p or "super nintendo" in p):
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
    modern_platforms = ["pc (microsoft windows)", "playstation 3", "playstation 4", "xbox 360", "xbox one", "wii u", "switch"]
    if platform_filter and any(mp in r_platforms for mp in modern_platforms):
        # Only penalize if the retro platform is NOT also present
        if not platform_matched:
            score -= 50

    return score


def _select_best_game(
    results: List[Dict[str, Any]],
    search_name: str,
    platform_filter: Optional[str] = None
) -> Optional[Dict[str, Any]]:
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
# Multi-Query Batch Search (up to 10 games per request)
# =============================================================================

@dataclass
class GameSearchRequest:
    """Request for a single game in a batch search."""
    search_name: str  # Name to search for
    platform_filter: Optional[str] = None  # IGDB platform name
    game_id: Optional[str] = None  # Our internal game ID (for tracking)
    system: Optional[str] = None  # Our internal system ID (for tracking)


# Rate limiting: IGDB allows 4 requests/second
# Use an asyncio lock to ensure only one request at a time across all tasks
_rate_limit_lock = asyncio.Lock()
_RATE_LIMIT_DELAY = 0.35  # 350ms between requests = ~2.8 req/sec (extra safe)
_last_request_time: float = 0


def _generate_search_variants(name: str) -> List[str]:
    """Generate alternative search queries for a game name."""
    variants = [name]  # Original name first

    # Remove "The" prefix/suffix
    no_the = name.replace("The ", "").replace(" The", "")
    if no_the != name:
        variants.append(no_the)

    # Remove common subtitle separators and everything after
    for sep in [" - ", ": ", " – "]:
        if sep in name:
            base = name.split(sep)[0]
            if base not in variants:
                variants.append(base)

    # Try without spaces for compound words
    no_spaces = name.replace(" ", "")
    if no_spaces != name and len(no_spaces) < 20:  # Don't do this for long names
        variants.append(no_spaces)

    # Add common romanization alternatives (e.g., "2" -> "II")
    if " 2" in name:
        variants.append(name.replace(" 2", " II"))
    if " 3" in name:
        variants.append(name.replace(" 3", " III"))

    return variants[:4]  # Max 4 variants to not spam API


async def _rate_limited_search(
    name: str,
    client_id: str,
    client_secret: str,
    platform_filter: Optional[str] = None,
    try_variants: bool = False  # Disabled by default for batch - too many API calls
) -> Optional[GameMetadata]:
    """Search with rate limiting and optional fallback search variants."""
    global _last_request_time

    search_names = _generate_search_variants(name) if try_variants else [name]

    for search_name in search_names:
        # Use lock to ensure only one request at a time globally
        async with _rate_limit_lock:
            # Rate limit - wait if needed
            now = asyncio.get_event_loop().time()
            elapsed = now - _last_request_time
            if elapsed < _RATE_LIMIT_DELAY:
                await asyncio.sleep(_RATE_LIMIT_DELAY - elapsed)

            _last_request_time = asyncio.get_event_loop().time()

            result = await search_game(search_name, client_id, client_secret, platform_filter)

        if result:
            return result

        # If this variant didn't work, try next (only if variants enabled)

    return None


async def search_games_batch(
    requests: List[GameSearchRequest],
    client_id: str,
    client_secret: str,
) -> Dict[str, Optional[GameMetadata]]:
    """
    Search for multiple games with rate limiting.

    Uses sequential requests with 300ms delays to stay under IGDB's 4 req/sec limit.
    Results are cached in SQLite, so subsequent requests are instant.

    Args:
        requests: List of GameSearchRequest objects
        client_id: IGDB/Twitch Client ID
        client_secret: IGDB/Twitch Client Secret

    Returns:
        Dict mapping game_id to GameMetadata (or None if not found)
    """
    if not requests:
        return {}

    print(f"[IGDB] Batch searching {len(requests)} games (rate limited)...")

    results_map: Dict[str, Optional[GameMetadata]] = {}
    found_count = 0

    for i, req in enumerate(requests):
        result = await _rate_limited_search(
            req.search_name,
            client_id,
            client_secret,
            req.platform_filter
        )

        results_map[req.game_id] = result

        if result:
            found_count += 1
            print(f"[IGDB]   [{i+1}/{len(requests)}] {req.search_name} -> {result.name}")
        else:
            print(f"[IGDB]   [{i+1}/{len(requests)}] {req.search_name} -> Not found")

    print(f"[IGDB] Batch complete: {found_count} / {len(requests)} found")
    return results_map
