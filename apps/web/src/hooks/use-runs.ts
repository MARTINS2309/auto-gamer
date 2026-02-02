import { useState, useEffect, useRef, useCallback } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api, createRunWebSocket, type RunWebSocketCallbacks } from "@/lib/api"
import type { Run, RunCreate, RunMetrics } from "@/lib/schemas"
import { toast } from "sonner"
import { useNavigate } from "@tanstack/react-router"

export const runKeys = {
  all: ["runs"] as const,
  detail: (id: string) => ["run", id] as const,
}

export function useRuns(options?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: runKeys.all,
    queryFn: api.runs.list,
    refetchInterval: options?.refetchInterval ?? 5000,
  })
}

export function useRun(id: string) {
  return useQuery({
    queryKey: runKeys.detail(id),
    queryFn: () => api.runs.get(id),
    refetchInterval: (query) => {
      const data = query.state.data
      // Only poll if not running (WebSocket handles live updates)
      return data?.status === "running" ? false : 5000
    },
  })
}

export function useRunsByRom(romId: string | null, limit = 5) {
  const { data: runs = [] } = useRuns()

  return romId
    ? runs.filter((r) => r.rom === romId).slice(0, limit)
    : []
}

export function useActiveRuns() {
  const { data: runs = [], ...rest } = useRuns()
  return {
    ...rest,
    data: runs.filter((r) => r.status === "running"),
  }
}

export function useCreateRun() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: (data: RunCreate) => api.runs.create(data),
    onSuccess: (run) => {
      toast.success("Run started")
      queryClient.invalidateQueries({ queryKey: runKeys.all })
      navigate({ to: "/runs/$runId", params: { runId: run.id } })
    },
    onError: (error) => {
      toast.error(`Failed to start run: ${error.message}`)
    },
  })
}

export function useStopRun() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.runs.stop,
    onSuccess: (_, runId) => {
      toast.success("Run stopped")
      queryClient.invalidateQueries({ queryKey: runKeys.detail(runId) })
      queryClient.invalidateQueries({ queryKey: runKeys.all })
    },
    onError: (error) => {
      toast.error(`Failed to stop run: ${error.message}`)
    },
  })
}

export function useDeleteRun() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: api.runs.delete,
    onSuccess: () => {
      toast.success("Run deleted")
      queryClient.invalidateQueries({ queryKey: runKeys.all })
      navigate({ to: "/runs" })
    },
    onError: (error) => {
      toast.error(`Failed to delete run: ${error.message}`)
    },
  })
}

export function useBulkStopRuns() {
  const stopRun = useStopRun()

  return useCallback(
    (runIds: string[], runs: Run[]) => {
      runIds.forEach((id) => {
        const run = runs.find((r) => r.id === id)
        if (run?.status === "running") {
          stopRun.mutate(id)
        }
      })
    },
    [stopRun]
  )
}

export function useBulkDeleteRuns() {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: async (runIds: string[]) => {
      await Promise.all(runIds.map((id) => api.runs.delete(id)))
    },
    onSuccess: () => {
      toast.success("Runs deleted")
      queryClient.invalidateQueries({ queryKey: runKeys.all })
    },
    onError: (error) => {
      toast.error(`Failed to delete runs: ${error.message}`)
    },
  })

  return mutation
}

// =============================================================================
// WebSocket Hook for Live Metrics
// =============================================================================

export interface UseRunMetricsResult {
  metrics: RunMetrics | null
  history: RunMetrics[]
  isConnected: boolean
}

export function useRunMetrics(
  runId: string,
  isRunning: boolean
): UseRunMetricsResult {
  const queryClient = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)
  const [metrics, setMetrics] = useState<RunMetrics | null>(null)
  const [history, setHistory] = useState<RunMetrics[]>([])
  const [wsIsOpen, setWsIsOpen] = useState(false)

  useEffect(() => {
    if (!isRunning) {
      wsRef.current?.close()
      return
    }

    const callbacks: RunWebSocketCallbacks = {
      onMetrics: (data) => {
        const m: RunMetrics = {
          step: data.step,
          reward: data.reward,
          avg_reward: data.avg_reward,
          best_reward: data.best_reward,
          fps: data.fps,
          loss: data.loss,
          epsilon: data.epsilon,
        }
        setMetrics(m)
        setHistory((prev) => [...prev.slice(-500), m])
      },
      onStatus: () => {
        queryClient.invalidateQueries({ queryKey: runKeys.detail(runId) })
      },
      onError: (error) => {
        toast.error(`Run error: ${error}`)
      },
      onConnectionError: () => {
        toast.error("WebSocket connection lost")
      },
    }

    const ws = createRunWebSocket(runId, callbacks)
    wsRef.current = ws

    ws.onopen = () => setWsIsOpen(true)
    ws.onclose = () => setWsIsOpen(false)

    return () => {
      ws.close()
    }
  }, [runId, isRunning, queryClient])

  // Derive isConnected: only connected when running AND websocket is open
  const isConnected = isRunning && wsIsOpen

  return { metrics, history, isConnected }
}

// =============================================================================
// Computed Stats
// =============================================================================

export function useRunStats(runs: Run[]) {
  const activeRuns = runs.filter((r) => r.status === "running")
  const completedRuns = runs.filter((r) => r.status === "completed")
  const failedRuns = runs.filter((r) => r.status === "failed")

  return {
    total: runs.length,
    activeCount: activeRuns.length,
    completedCount: completedRuns.length,
    failedCount: failedRuns.length,
    activeRuns,
  }
}
