import { useState, useEffect, useRef, useCallback, useMemo } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api, createRunWebSocket, type RunWebSocketCallbacks, type FrameInfo } from "@/lib/api"
import type { Run, RunCreateInput, RunMetrics } from "@/lib/schemas"
import { toast } from "sonner"
import { formatDuration, intervalToDuration } from "date-fns"
import { useNavigate } from "@tanstack/react-router"

export const runKeys = {
  all: ["runs"] as const,
  detail: (id: string) => ["run", id] as const,
}

export function useRuns(options?: { refetchInterval?: number | false }) {
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
  // Disable refetching - this is for display purposes, not live monitoring
  const { data: runs = [] } = useRuns({ refetchInterval: false })

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
    mutationFn: (data: RunCreateInput) => api.runs.create(data),
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

export function useResumeRun() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.runs.resume,
    onSuccess: (_, runId) => {
      toast.success("Run resumed")
      queryClient.invalidateQueries({ queryKey: runKeys.detail(runId) })
      queryClient.invalidateQueries({ queryKey: runKeys.all })
    },
    onError: (error) => {
      toast.error(`Failed to resume run: ${error.message}`)
    },
  })
}

export function useDeleteRun() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.runs.delete,
    onSuccess: () => {
      toast.success("Run deleted")
      queryClient.invalidateQueries({ queryKey: runKeys.all })
    },
    onError: (error) => {
      toast.error(`Failed to delete run: ${error.message}`)
    },
  })
}

export function useUpdateRun() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (variables: { id: string; updates: { hyperparams: Record<string, unknown> } }) =>
      api.runs.update(variables.id, variables.updates),
    onSuccess: (run) => {
      toast.success("Run updated")
      queryClient.setQueryData(runKeys.detail(run.id), run)
      queryClient.invalidateQueries({ queryKey: runKeys.all })
    },
    onError: (error) => {
      toast.error(`Failed to update run: ${error.message}`)
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
  /** Grid frame (env_index=0xFF) from training env */
  gridFrame: FrameInfo | null
  /** Focused single-env frame (env_index=0-254) */
  focusedFrame: FrameInfo | null
  /** Which env is focused (-1 = grid mode) */
  focusedEnv: number
  /** Set which env to focus (-1 = grid mode) */
  setFocusedEnv: (envIndex: number) => void
  /** Send a command to change frame capture frequency (steps between captures) */
  setFrameFreq: (freq: number) => void
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
  const [gridFrame, setGridFrame] = useState<FrameInfo | null>(null)
  const [focusedFrame, setFocusedFrame] = useState<FrameInfo | null>(null)
  const [focusedEnv, setFocusedEnvState] = useState(-1)

  // 1. Load historical metrics on mount
  useEffect(() => {
    let mounted = true
    api.runs.metrics(runId)
      .then((data) => {
        if (!mounted) return
        setHistory(data)
        if (data.length > 0) {
          setMetrics(data[data.length - 1])
        }
      })
      .catch((err) => {
        console.error("Failed to load metrics history:", err)
      })
    return () => { mounted = false }
  }, [runId])

  useEffect(() => {
    if (!isRunning) {
      wsRef.current?.close()
      return
    }

    const callbacks: RunWebSocketCallbacks = {
      onMetrics: (data) => {
        const m: RunMetrics = {
          step: data.step,
          timestamp: data.timestamp ?? Date.now() / 1000,
          reward: data.reward,
          avg_reward: data.avg_reward,
          best_reward: data.best_reward,
          fps: data.fps,
          loss: data.loss,
          epsilon: data.epsilon,
          details: data.details,
          type: data.type ?? "metric",
        }
        setMetrics(m)
        // Append to history, keeping it reasonable size?
        // Actually, for charts we want full history, but in memory might get large.
        // For now, let's keep it growing.
        setHistory((prev) => [...prev, m])
      },
      onFrame: (frame) => {
        if (frame.envIndex === 0xFF) {
          setGridFrame(frame)
        } else {
          setFocusedFrame(frame)
        }
      },
      onStatus: () => {
        queryClient.invalidateQueries({ queryKey: runKeys.detail(runId) })
      },
      onError: (error) => {
        toast.error(`Run error: ${error}`)
      },
      onConnectionError: () => {
        // toast.error("WebSocket connection lost")
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

  const setFrameFreq = useCallback((freq: number) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: "set_frame_freq", value: freq }))
    }
  }, [])

  const setFocusedEnv = useCallback((envIndex: number) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: "set_focused_env", value: envIndex }))
    }
    setFocusedEnvState(envIndex)
    if (envIndex === -1) setFocusedFrame(null)
  }, [])

  return { metrics, history, isConnected, gridFrame, focusedFrame, focusedEnv, setFocusedEnv, setFrameFreq }
}

// =============================================================================
// Aggregated Metrics Hook for Dashboard
// =============================================================================

export interface AggregatedMetrics {
  totalSteps: number
  bestReward: number
  avgFps: number
}

export interface UseAggregatedMetricsResult {
  aggregated: AggregatedMetrics
  isConnected: boolean
  connectionCount: number
  metricsMap: Map<string, RunMetrics>
}

export function useAggregatedRunMetrics(
  activeRunIds: string[]
): UseAggregatedMetricsResult {
  const queryClient = useQueryClient()

  // Track WebSocket connections per run
  const wsMapRef = useRef<Map<string, WebSocket>>(new Map())

  // Track metrics per run
  const [metricsMap, setMetricsMap] = useState<Map<string, RunMetrics>>(
    new Map()
  )

  // Track connection status per run
  const [connectedSet, setConnectedSet] = useState<Set<string>>(new Set())

  // Stable reference for activeRunIds to avoid unnecessary effect triggers
  const activeRunIdsJson = JSON.stringify(activeRunIds.sort())

  // Manage connections based on active run IDs
  useEffect(() => {
    const currentIds = new Set(activeRunIds)
    const existingIds = new Set(wsMapRef.current.keys())

    // Close connections for runs no longer active
    for (const id of existingIds) {
      if (!currentIds.has(id)) {
        const ws = wsMapRef.current.get(id)
        ws?.close()
        wsMapRef.current.delete(id)
        setConnectedSet((prev) => {
          const next = new Set(prev)
          next.delete(id)
          return next
        })
        setMetricsMap((prev) => {
          const next = new Map(prev)
          next.delete(id)
          return next
        })
      }
    }

    // Open connections for new active runs
    for (const runId of activeRunIds) {
      if (!wsMapRef.current.has(runId)) {
        const callbacks: RunWebSocketCallbacks = {
          onMetrics: (data) => {
            const m: RunMetrics = {
              step: data.step,
              timestamp: data.timestamp ?? Date.now() / 1000,
              reward: data.reward,
              avg_reward: data.avg_reward,
              best_reward: data.best_reward,
              fps: data.fps,
              loss: data.loss,
              epsilon: data.epsilon,
              type: data.type ?? "metric",
            }
            setMetricsMap((prev) => new Map(prev).set(runId, m))
          },
          onStatus: () => {
            queryClient.invalidateQueries({ queryKey: runKeys.all })
          },
          onError: (error) => {
            console.error(`Run ${runId} error:`, error)
          },
        }

        const ws = createRunWebSocket(runId, callbacks)
        wsMapRef.current.set(runId, ws)

        ws.onopen = () => {
          setConnectedSet((prev) => new Set(prev).add(runId))
        }
        ws.onclose = () => {
          setConnectedSet((prev) => {
            const next = new Set(prev)
            next.delete(runId)
            return next
          })
        }
      }
    }

    // Cleanup on unmount
    return () => {
      // eslint-disable-next-line react-hooks/exhaustive-deps
      const wsMap = wsMapRef.current
      wsMap.forEach((ws) => ws.close())
      wsMap.clear()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeRunIdsJson, queryClient])

  // Compute aggregated metrics
  const aggregated = useMemo<AggregatedMetrics>(() => {
    let totalSteps = 0
    let bestReward = -Infinity
    let totalFps = 0
    let fpsCount = 0

    metricsMap.forEach((metrics) => {
      totalSteps += metrics.step
      if (metrics.best_reward != null && metrics.best_reward > bestReward) {
        bestReward = metrics.best_reward
      }
      if (metrics.fps && metrics.fps > 0) {
        totalFps += metrics.fps
        fpsCount++
      }
    })

    return {
      totalSteps,
      bestReward: bestReward === -Infinity ? 0 : bestReward,
      avgFps: fpsCount > 0 ? totalFps / fpsCount : 0,
    }
  }, [metricsMap])

  return {
    aggregated,
    isConnected: connectedSet.size > 0,
    connectionCount: connectedSet.size,
    metricsMap,
  }
}

// =============================================================================
// Computed Stats
// =============================================================================

export function useRunStats(runs: Run[]) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 60000)
    return () => clearInterval(timer)
  }, [])

  const activeRuns = runs.filter((r) => r.status === "running")
  const completedRuns = runs.filter((r) => r.status === "completed")
  const failedRuns = runs.filter((r) => r.status === "failed")

  // Calculate uptime from earliest active run's started_at
  const uptime = useMemo(() => {
    const startTimes = activeRuns
      .map((r) => (r.started_at ? new Date(r.started_at).getTime() : null))
      .filter((t): t is number => t !== null)
      .sort((a, b) => a - b)

    if (startTimes.length === 0) return null

    const duration = intervalToDuration({
      start: startTimes[0],
      end: now,
    })

    return (
      formatDuration(duration, { format: ["hours", "minutes"] }) || "< 1m"
    )
  }, [activeRuns, now])

  return {
    total: runs.length,
    activeCount: activeRuns.length,
    completedCount: completedRuns.length,
    failedCount: failedRuns.length,
    activeRuns,
    uptime,
    // Placeholder values - real metrics come from WebSocket/aggregated hook
    totalSteps: 0,
    bestReward: 0,
  }
}
