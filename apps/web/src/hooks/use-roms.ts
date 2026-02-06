import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { toast } from "sonner"

export const romKeys = {
  all: (includeConnectors?: boolean) => ["roms", { includeConnectors }] as const,
  detail: (id: string) => ["rom", id] as const,
  states: (id: string) => ["rom", id, "states"] as const,
  syncStatus: ["roms", "sync", "status"] as const,
  igdbSearch: (id: string, query?: string) => ["rom", id, "igdb-search", query] as const,
}

// =============================================================================
// ROM Queries
// =============================================================================

export function useRoms(includeConnectors: boolean = true) {
  return useQuery({
    queryKey: romKeys.all(includeConnectors),
    queryFn: () => api.roms.list(includeConnectors),
  })
}

export function useRom(id: string | null) {
  return useQuery({
    queryKey: romKeys.detail(id!),
    queryFn: () => api.roms.get(id!),
    enabled: !!id,
  })
}

export function useRomStates(id: string | null) {
  return useQuery({
    queryKey: romKeys.states(id!),
    queryFn: () => api.roms.getStates(id!),
    enabled: !!id,
  })
}

// =============================================================================
// Sync Queries & Mutations
// =============================================================================

export function useSyncStatus() {
  return useQuery({
    queryKey: romKeys.syncStatus,
    queryFn: api.roms.syncStatus,
    refetchInterval: (query) => {
      // Poll every 2s while syncing, otherwise every 30s
      return query.state.data?.is_syncing ? 2000 : 30000
    },
  })
}

export function useSyncAll() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (includeUnmatchedConnectors: boolean = false) =>
      api.roms.syncAll(includeUnmatchedConnectors),
    onSuccess: () => {
      toast.success("Sync started")
      queryClient.invalidateQueries({ queryKey: romKeys.syncStatus })
    },
    onError: (error) => {
      toast.error(`Sync failed: ${error.message}`)
    },
  })
}

export function useSyncThumbnails() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.roms.syncThumbnails,
    onSuccess: (result) => {
      if (result.count > 0) {
        toast.success(`Thumbnail sync started for ${result.count} ROMs`)
      } else {
        toast.info("No ROMs need thumbnail resync")
      }
      queryClient.invalidateQueries({ queryKey: romKeys.syncStatus })
    },
    onError: (error) => {
      toast.error(`Thumbnail sync failed: ${error.message}`)
    },
  })
}

export function useSyncRom() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, force = false }: { id: string; force?: boolean }) =>
      api.roms.syncOne(id, force),
    onSuccess: (_result, { id }) => {
      toast.success("ROM synced")
      queryClient.invalidateQueries({ queryKey: romKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: ["roms"] })
      queryClient.invalidateQueries({ queryKey: romKeys.syncStatus })
    },
    onError: (error) => {
      toast.error(`Sync failed: ${error.message}`)
    },
  })
}

// =============================================================================
// Import & Scan Mutations
// =============================================================================

export function useImportRoms() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (path?: string) => api.roms.import(path),
    onSuccess: (result) => {
      const queued = result.queued_for_sync ?? 0
      const msg = queued > 0
        ? `Imported ${result.imported} ROM(s), ${queued} queued for sync`
        : `Imported ${result.imported} ROM(s)`
      toast.success(msg)
      if (result.syncing) {
        toast.info("Background sync started for metadata")
      }
      queryClient.invalidateQueries({ queryKey: ["roms"] })
      queryClient.invalidateQueries({ queryKey: romKeys.syncStatus })
    },
    onError: (error) => {
      toast.error(`Import failed: ${error.message}`)
    },
  })
}

export function useScanRoms() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.roms.scan,
    onSuccess: (result) => {
      toast.success(`Scan complete: ${result.queued_for_sync} ROM(s) queued for sync`)
      if (result.syncing) {
        toast.info("Background sync started for metadata")
      }
      queryClient.invalidateQueries({ queryKey: ["roms"] })
      queryClient.invalidateQueries({ queryKey: romKeys.syncStatus })
    },
    onError: (error) => {
      toast.error(`Scan failed: ${error.message}`)
    },
  })
}

// =============================================================================
// Manual Correction Mutations
// =============================================================================

export function useResyncRom() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { igdb_id?: number; libretro_name?: string } }) =>
      api.roms.resync(id, data),
    onSuccess: (_result, { id }) => {
      toast.success("ROM metadata updated")
      queryClient.invalidateQueries({ queryKey: romKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: ["roms"] })
    },
    onError: (error) => {
      toast.error(`Resync failed: ${error.message}`)
    },
  })
}

export function useSearchIGDB(romId: string | null, query?: string) {
  return useQuery({
    queryKey: romKeys.igdbSearch(romId!, query),
    queryFn: () => api.roms.searchIGDB(romId!, query),
    enabled: !!romId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })
}

// =============================================================================
// Utility Functions (moved from use-metadata.ts)
// =============================================================================

/**
 * Format rating as percentage.
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
