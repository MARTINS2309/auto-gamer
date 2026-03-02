import { useCallback, useEffect, useRef, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { toast } from "sonner"

export function useIntegrationTool() {
  const queryClient = useQueryClient()
  const [isRunning, setIsRunning] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const startPolling = useCallback(() => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const result = await api.integration.status()
        if (!result.running) {
          setIsRunning(false)
          stopPolling()
          // Rescan connectors when tool closes
          await api.integration.rescan()
          queryClient.invalidateQueries({ queryKey: ["roms"] })
          toast.info("Integration tool closed. Rescanning connectors...")
        }
      } catch {
        // Ignore polling errors
      }
    }, 2000)
  }, [stopPolling, queryClient])

  // Cleanup on unmount
  useEffect(() => stopPolling, [stopPolling])

  const launchMutation = useMutation({
    mutationFn: (opts?: { romId?: string; connectorId?: string }) => api.integration.launch(opts),
    onSuccess: (data) => {
      if (data.status === "launched" || data.status === "already_running") {
        setIsRunning(true)
        startPolling()
        toast.success(
          data.status === "already_running"
            ? "Integration tool is already running"
            : "Integration tool launched"
        )
      }
    },
    onError: (error) => {
      toast.error(`Failed to launch integration tool: ${error.message}`)
    },
  })

  const stopMutation = useMutation({
    mutationFn: () => api.integration.stop(),
    onSuccess: () => {
      setIsRunning(false)
      stopPolling()
      toast.success("Integration tool stopped")
    },
  })

  return {
    launch: launchMutation.mutate,
    stop: stopMutation.mutate,
    isRunning,
    isLaunching: launchMutation.isPending,
  }
}
