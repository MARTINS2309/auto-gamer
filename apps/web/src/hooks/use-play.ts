import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { toast } from "sonner"

/**
 * Hook to start a play session
 */
export function useStartPlaySession() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ romId, state, players }: { romId: string; state?: string; players?: number }) =>
      api.play.start(romId, state, players),
    onSuccess: (data) => {
      toast.success(data.message)
      queryClient.invalidateQueries({ queryKey: ["play-sessions"] })
    },
    onError: (error) => {
      toast.error(`Failed to start game: ${error.message}`)
    },
  })
}

/**
 * Hook to stop a play session
 */
export function useStopPlaySession() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (sessionId: string) => api.play.stop(sessionId),
    onSuccess: () => {
      toast.success("Play session stopped")
      queryClient.invalidateQueries({ queryKey: ["play-sessions"] })
    },
    onError: (error) => {
      toast.error(`Failed to stop session: ${error.message}`)
    },
  })
}

/**
 * Hook to get a play session
 */
export function usePlaySession(sessionId: string | null) {
  return useQuery({
    queryKey: ["play-session", sessionId],
    queryFn: () => api.play.get(sessionId!),
    enabled: !!sessionId,
    refetchInterval: 5000, // Refresh every 5 seconds to check if still alive
  })
}

/**
 * Hook to list all play sessions
 */
export function usePlaySessions() {
  return useQuery({
    queryKey: ["play-sessions"],
    queryFn: () => api.play.list(),
    refetchInterval: 5000, // Refresh every 5 seconds
  })
}
