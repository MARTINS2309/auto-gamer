import { useState, useEffect } from "react"
import { fetchThumbnail } from "@/lib/thumbnails"

interface UseThumbnailResult {
  url: string | null
  loading: boolean
  error: boolean
}

/**
 * Hook to fetch and cache a game thumbnail.
 */
export function useThumbnail(
  gameName: string | undefined,
  system: string | undefined,
  type: "boxart" | "snap" | "title" = "boxart"
): UseThumbnailResult {
  const [url, setUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!gameName || !system) {
      setUrl(null)
      setLoading(false)
      setError(false)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(false)

    fetchThumbnail(gameName, system, type)
      .then((result) => {
        if (cancelled) return
        setUrl(result)
        setError(result === null)
        setLoading(false)
      })
      .catch(() => {
        if (cancelled) return
        setUrl(null)
        setError(true)
        setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [gameName, system, type])

  return { url, loading, error }
}
