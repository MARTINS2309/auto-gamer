import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useRef } from "react"
import { api } from "@/lib/api"
import type { GameMetadata } from "@/lib/schemas"

export const metadataKeys = {
  all: ["metadata"] as const,
  game: (system: string, gameId: string) => ["metadata", system, gameId] as const,
  batch: (ids: string) => ["metadata", "batch", ids] as const,
}

/**
 * Fetch metadata for a single game.
 * Returns cached data from IGDB/ScreenScraper.
 * Prefer using useGameMetadataBatch for multiple games.
 */
export function useGameMetadata(system: string | null, gameId: string | null) {
  return useQuery({
    queryKey: metadataKeys.game(system!, gameId!),
    queryFn: () => api.metadata.get(system!, gameId!),
    enabled: !!system && !!gameId,
    staleTime: 1000 * 60 * 60 * 24, // 24 hours - metadata doesn't change
    gcTime: 1000 * 60 * 60 * 24, // Keep in cache for 24 hours
    retry: false, // Don't retry if game not found
  })
}

/**
 * Batch fetch metadata for multiple games.
 * Populates individual cache entries for each game.
 * Returns a Map for efficient lookup by game_id.
 *
 * Returns cached data immediately. If some games are being fetched
 * in the background, the hook will refetch after a delay to pick up new data.
 */
export function useGameMetadataBatch(games: Array<{ game_id: string; system: string }>) {
  const queryClient = useQueryClient()
  const refetchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Create stable key from sorted game IDs
  const batchKey = useMemo(
    () => games.map(g => `${g.system}:${g.game_id}`).sort().join(","),
    [games]
  )

  const query = useQuery({
    queryKey: metadataKeys.batch(batchKey),
    queryFn: () => api.metadata.batch(games),
    enabled: games.length > 0,
    staleTime: 1000 * 60 * 5, // 5 minutes - allow refetch for background data
    gcTime: 1000 * 60 * 60 * 24,
  })

  // Populate individual cache entries when batch completes
  useEffect(() => {
    if (query.data) {
      for (const metadata of query.data) {
        queryClient.setQueryData(
          metadataKeys.game(metadata.system, metadata.game_id),
          metadata
        )
      }
    }
  }, [query.data, queryClient])

  // If we got fewer results than requested, schedule a refetch to pick up background data
  useEffect(() => {
    if (refetchTimeoutRef.current) {
      clearTimeout(refetchTimeoutRef.current)
      refetchTimeoutRef.current = null
    }

    if (query.data && games.length > 0 && query.data.length < games.length) {
      // Some games are being fetched in background, refetch after 5 seconds
      refetchTimeoutRef.current = setTimeout(() => {
        query.refetch()
      }, 5000)
    }

    return () => {
      if (refetchTimeoutRef.current) {
        clearTimeout(refetchTimeoutRef.current)
      }
    }
  }, [query.data?.length, games.length, query])

  // Return as Map for O(1) lookup
  const metadataMap = useMemo(() => {
    const map = new Map<string, GameMetadata>()
    if (query.data) {
      for (const m of query.data) {
        map.set(m.game_id, m)
      }
    }
    return map
  }, [query.data])

  return {
    ...query,
    metadataMap,
  }
}

/**
 * Format rating as percentage with star display.
 */
export function formatRating(rating: number | null | undefined): string | null {
  if (rating == null) return null
  return `${Math.round(rating)}%`
}

/**
 * Format release year from date string.
 */
export function formatReleaseYear(releaseDate: string | null | undefined): string | null {
  if (!releaseDate) return null
  return releaseDate.split("-")[0]
}
