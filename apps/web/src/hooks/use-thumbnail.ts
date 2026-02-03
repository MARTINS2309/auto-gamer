import { useState, useCallback } from "react"
import { getThumbnailUrl } from "@/lib/thumbnails"

interface UseThumbnailResult {
  url: string
  loading: boolean
  failed: boolean
  onError: () => void
  onLoad: () => void
}

/**
 * Hook to get a game thumbnail via the backend proxy.
 * Backend handles caching and LibRetro lookups.
 */
export function useThumbnail(
  gameName: string | undefined,
  system: string | undefined,
  type: "boxart" | "snap" | "title" = "boxart"
): UseThumbnailResult {
  const [failed, setFailed] = useState(false)
  const [loading, setLoading] = useState(true)

  // Always generate URL - let the img element handle success/failure
  const url = gameName && system
    ? getThumbnailUrl(gameName, system, type)
    : ""

  const onError = useCallback(() => {
    setFailed(true)
    setLoading(false)
  }, [])

  const onLoad = useCallback(() => {
    setFailed(false)
    setLoading(false)
  }, [])

  return {
    url,
    loading,
    failed,
    onError,
    onLoad,
  }
}
