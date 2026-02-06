import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"

export const metadataKeys = {
    game: (system: string, gameId: string) => ["metadata", "game", system, gameId] as const,
    batch: (games: Array<{ game_id: string; system: string }>) => ["metadata", "batch", games] as const,
}

export function useGameMetadata(system: string | null, gameId: string | null) {
    return useQuery({
        queryKey: metadataKeys.game(system!, gameId!),
        queryFn: () => api.metadata.get(system!, gameId!),
        enabled: !!system && !!gameId,
        staleTime: 1000 * 60 * 60, // 1 hour
    })
}

export function useBatchMetadata(games: Array<{ game_id: string; system: string }>) {
    return useQuery({
        queryKey: metadataKeys.batch(games),
        queryFn: () => api.metadata.batch(games),
        enabled: games.length > 0,
        staleTime: 1000 * 60 * 60, // 1 hour
    })
}
