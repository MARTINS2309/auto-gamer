/**
 * Thumbnail Service
 *
 * Uses backend proxy to fetch game artwork (avoids CORS issues).
 * Backend caches images permanently on disk.
 */

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

/**
 * Get thumbnail URL for a game via backend proxy.
 */
export function getThumbnailUrl(
  gameName: string,
  system: string,
  type: "boxart" | "snap" | "title" = "boxart"
): string {
  const encodedSystem = encodeURIComponent(system)
  const encodedGame = encodeURIComponent(gameName)
  return `${API_BASE}/api/thumbnails/${encodedSystem}/${encodedGame}?type=${type}`
}

/**
 * Clear the server-side thumbnail cache.
 */
export async function clearThumbnailCache(): Promise<{ cleared: number }> {
  const response = await fetch(`${API_BASE}/api/thumbnails/cache`, {
    method: "DELETE",
  })
  if (!response.ok) {
    throw new Error("Failed to clear cache")
  }
  return response.json()
}

/**
 * Get thumbnail cache statistics.
 */
export async function getCacheStats(): Promise<{
  count: number
  size_bytes: number
  size_mb: number
  failed_lookups: number
}> {
  const response = await fetch(`${API_BASE}/api/thumbnails/cache/stats`)
  if (!response.ok) {
    throw new Error("Failed to get cache stats")
  }
  return response.json()
}
