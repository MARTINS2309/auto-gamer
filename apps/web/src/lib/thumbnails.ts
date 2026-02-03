/**
 * LibRetro Thumbnails Service
 *
 * Fetches and caches game artwork from the LibRetro thumbnails repository.
 * https://github.com/libretro-thumbnails
 */

// =============================================================================
// System Mapping
// =============================================================================

const SYSTEM_MAP: Record<string, string> = {
  // Nintendo
  "Nes": "Nintendo - Nintendo Entertainment System",
  "Snes": "Nintendo - Super Nintendo Entertainment System",
  "N64": "Nintendo - Nintendo 64",
  "GameBoy": "Nintendo - Game Boy",
  "Gb": "Nintendo - Game Boy",
  "Gbc": "Nintendo - Game Boy Color",
  "Gba": "Nintendo - Game Boy Advance",
  "NintendoDS": "Nintendo - Nintendo DS",
  "Nds": "Nintendo - Nintendo DS",

  // Sega
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

  // Atari
  "Atari2600": "Atari - 2600",
  "Atari5200": "Atari - 5200",
  "Atari7800": "Atari - 7800",
  "AtariLynx": "Atari - Lynx",
  "Lynx": "Atari - Lynx",
  "AtariJaguar": "Atari - Jaguar",
  "Jaguar": "Atari - Jaguar",

  // Sony
  "Psx": "Sony - PlayStation",
  "PlayStation": "Sony - PlayStation",
  "Psp": "Sony - PlayStation Portable",

  // Other
  "Arcade": "FBNeo - Arcade Games",
  "PCEngine": "NEC - PC Engine - TurboGrafx 16",
  "TurboGrafx16": "NEC - PC Engine - TurboGrafx 16",
  "NeoGeo": "SNK - Neo Geo",
  "Ngp": "SNK - Neo Geo Pocket",
  "NeoGeoPocket": "SNK - Neo Geo Pocket",
  "Wonderswan": "Bandai - WonderSwan",
  "Ws": "Bandai - WonderSwan",
}

// =============================================================================
// IndexedDB Cache
// =============================================================================

const DB_NAME = "auto-gamer-thumbnails"
const DB_VERSION = 1
const STORE_NAME = "images"

interface CachedImage {
  key: string
  blob: Blob
  timestamp: number
}

let dbPromise: Promise<IDBDatabase> | null = null

function openDB(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise

  dbPromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)

    request.onerror = () => reject(request.error)
    request.onsuccess = () => resolve(request.result)

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "key" })
      }
    }
  })

  return dbPromise
}

async function getCachedImage(key: string): Promise<string | null> {
  try {
    const db = await openDB()
    return new Promise((resolve) => {
      const tx = db.transaction(STORE_NAME, "readonly")
      const store = tx.objectStore(STORE_NAME)
      const request = store.get(key)

      request.onsuccess = () => {
        const result = request.result as CachedImage | undefined
        if (result?.blob) {
          resolve(URL.createObjectURL(result.blob))
        } else {
          resolve(null)
        }
      }
      request.onerror = () => resolve(null)
    })
  } catch {
    return null
  }
}

async function cacheImage(key: string, blob: Blob): Promise<void> {
  try {
    const db = await openDB()
    const tx = db.transaction(STORE_NAME, "readwrite")
    const store = tx.objectStore(STORE_NAME)

    const entry: CachedImage = {
      key,
      blob,
      timestamp: Date.now(),
    }

    store.put(entry)
  } catch {
    // Silently fail - cache is optional
  }
}

// Track failed URLs to avoid repeated requests
const failedUrls = new Set<string>()

// =============================================================================
// URL Generation
// =============================================================================

/**
 * Clean game name for LibRetro URL format.
 * Converts CamelCase to spaces and handles special characters.
 */
function cleanGameName(name: string): string {
  // Remove version suffix like "-Snes-v0", "-Genesis-v0" etc
  let cleaned = name.replace(/-[A-Za-z0-9]+-v\d+$/, "")

  // Split CamelCase into words with spaces
  // "SuperMarioWorld" -> "Super Mario World"
  // But preserve consecutive capitals like "USA" or "RPG"
  cleaned = cleaned
    .replace(/([a-z])([A-Z])/g, "$1 $2")  // lowercase followed by uppercase
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2")  // multiple uppercase followed by uppercase+lowercase

  // Handle number suffixes: "World2" -> "World 2"
  cleaned = cleaned.replace(/([a-zA-Z])(\d)/g, "$1 $2")

  // Add periods after common abbreviations
  cleaned = cleaned
    .replace(/\bBros\b/g, "Bros.")
    .replace(/\bDr\b/g, "Dr.")
    .replace(/\bMr\b/g, "Mr.")
    .replace(/\bMs\b/g, "Ms.")
    .replace(/\bVs\b/g, "Vs.")
    .replace(/\bSt\b/g, "St.")

  // Handle special game name patterns
  // "StreetFighter2" -> "Street Fighter II" (Roman numerals for some series)
  // But this is tricky, so let's just leave numbers as-is for now

  // Replace characters that LibRetro doesn't allow in filenames
  // Characters: & * / : ` < > ? \ |
  cleaned = cleaned.replace(/[&*/:"`<>?\\|]/g, "_")

  return cleaned
}

// Common region suffixes to try (in order of likelihood for English users)
const REGION_VARIANTS = [
  "(USA)",
  "(World)",
  "(USA, Europe)",
  "(Europe)",
  "(USA, Japan)",
  "(Japan, USA)",
  "(Japan)",
  "(Europe, Australia)",
  "(USA, Australia)",
  "",  // No region suffix - some games might not have one
]

/**
 * Get LibRetro system folder name from our system identifier.
 */
function getLibRetroSystem(system: string): string | null {
  // Try direct match first
  if (SYSTEM_MAP[system]) {
    return SYSTEM_MAP[system]
  }

  // Try case-insensitive match
  const lowerSystem = system.toLowerCase()
  for (const [key, value] of Object.entries(SYSTEM_MAP)) {
    if (key.toLowerCase() === lowerSystem) {
      return value
    }
  }

  return null
}

/**
 * Generate thumbnail URL for a game with optional region suffix.
 */
export function getThumbnailUrl(
  gameName: string,
  system: string,
  type: "boxart" | "snap" | "title" = "boxart",
  regionSuffix: string = ""
): string | null {
  const libRetroSystem = getLibRetroSystem(system)
  if (!libRetroSystem) return null

  let cleanedName = cleanGameName(gameName)
  if (regionSuffix) {
    cleanedName = `${cleanedName} ${regionSuffix}`
  }

  const folder = type === "boxart" ? "Named_Boxarts"
               : type === "snap" ? "Named_Snaps"
               : "Named_Titles"

  // URL encode the system name and game name for the URL
  const encodedSystem = encodeURIComponent(libRetroSystem)
  const encodedName = encodeURIComponent(cleanedName)

  // Use the LibRetro thumbnail server (faster CDN, not GitHub raw)
  return `https://thumbnails.libretro.com/${encodedSystem}/${folder}/${encodedName}.png`
}

// =============================================================================
// Public API
// =============================================================================

export interface ThumbnailResult {
  url: string | null
  loading: boolean
  error: boolean
}

/**
 * Fetch and cache a thumbnail image.
 * Tries multiple region variants until one succeeds.
 * Returns a blob URL for the cached image.
 */
export async function fetchThumbnail(
  gameName: string,
  system: string,
  type: "boxart" | "snap" | "title" = "boxart"
): Promise<string | null> {
  // Check cache first (before trying any network requests)
  const cacheKey = `${system}:${gameName}:${type}`
  const cached = await getCachedImage(cacheKey)
  if (cached) return cached

  // Check if we've already failed all variants for this game
  const failedKey = `${system}:${gameName}:${type}:all`
  if (failedUrls.has(failedKey)) return null

  // Try each region variant until one works
  for (const region of REGION_VARIANTS) {
    const url = getThumbnailUrl(gameName, system, type, region)
    if (!url) continue

    // Skip if we know this specific URL fails
    if (failedUrls.has(url)) continue

    try {
      const response = await fetch(url)
      if (!response.ok) {
        failedUrls.add(url)
        continue
      }

      const blob = await response.blob()

      // Verify it's actually an image
      if (!blob.type.startsWith("image/")) {
        failedUrls.add(url)
        continue
      }

      // Success! Cache it and return
      await cacheImage(cacheKey, blob)
      return URL.createObjectURL(blob)
    } catch {
      failedUrls.add(url)
      continue
    }
  }

  // All variants failed - mark to avoid retrying
  failedUrls.add(failedKey)
  return null
}

/**
 * Clear the thumbnail cache.
 */
export async function clearThumbnailCache(): Promise<void> {
  try {
    const db = await openDB()
    const tx = db.transaction(STORE_NAME, "readwrite")
    const store = tx.objectStore(STORE_NAME)
    store.clear()
    failedUrls.clear()
  } catch {
    // Silently fail
  }
}

/**
 * Get cache statistics.
 */
export async function getCacheStats(): Promise<{ count: number; sizeBytes: number }> {
  try {
    const db = await openDB()
    return new Promise((resolve) => {
      const tx = db.transaction(STORE_NAME, "readonly")
      const store = tx.objectStore(STORE_NAME)
      const request = store.getAll()

      request.onsuccess = () => {
        const items = request.result as CachedImage[]
        const sizeBytes = items.reduce((acc, item) => acc + (item.blob?.size || 0), 0)
        resolve({ count: items.length, sizeBytes })
      }
      request.onerror = () => resolve({ count: 0, sizeBytes: 0 })
    })
  } catch {
    return { count: 0, sizeBytes: 0 }
  }
}
