import { useState, useEffect, useRef, useCallback, useMemo } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api, createRunWebSocket, type RunWebSocketCallbacks, type FrameBuffer } from "@/lib/api"
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
    queryFn: () => api.runs.list(),
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
  /** Mutable frame buffer ref — written by WS handler, read by rAF loops in canvas components. Access .current only in effects/rAF, never during render. */
  frameBufferRef: React.RefObject<FrameBuffer>
  /** Number of completed episodes */
  episodeCount: number
  /** Whether historical metrics have finished loading */
  metricsLoaded: boolean
  /** Current training phase: "rollout" | "training" | null (off-policy) */
  phase: string | null
}

export function useRunMetrics(
  runId: string,
  isRunning: boolean
): UseRunMetricsResult {
  const queryClient = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef(0)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [metrics, setMetrics] = useState<RunMetrics | null>(null)
  const [history, setHistory] = useState<RunMetrics[]>([])
  const [wsIsOpen, setWsIsOpen] = useState(false)
  // Mutable frame buffer — bypasses React state entirely for zero-GC rendering
  // Ring capacity: ~600 frames. At 15fps capture ≈ 40s buffer. Memory grows lazily (~100MB at SNES res).
  const RING_CAPACITY = 600
  const frameBufferRef = useRef<FrameBuffer>({
    width: 0, height: 0, envCount: 0, envFrames: [], generation: 0,
    ring: new Array(RING_CAPACITY), ringHead: 0, ringSize: 0, ringCapacity: RING_CAPACITY, ringGeneration: 0,
  })
  const [episodeCount, setEpisodeCount] = useState(0)
  const [metricsLoadedFor, setMetricsLoadedFor] = useState<string | null>(null)
  const [phase, setPhase] = useState<string | null>(null)
  // metricsLoaded is true once the initial fetch completes for the current runId
  const metricsLoaded = metricsLoadedFor === runId

  // 1. Load historical metrics on mount
  useEffect(() => {
    let mounted = true
    api.runs.metrics(runId)
      .then((data) => {
        if (!mounted) return
        setHistory(data.length > 2000 ? data.slice(-2000) : data)
        if (data.length > 0) {
          setMetrics(data[data.length - 1])
        }
        // Restore episode count from persisted history
        const episodes = data.filter((m) => m.type === "episode").length
        if (episodes > 0) setEpisodeCount(episodes)
        setMetricsLoadedFor(runId)
      })
      .catch((err) => {
        console.error("Failed to load metrics history:", err)
        if (mounted) setMetricsLoadedFor(runId) // Mark loaded even on error to avoid infinite skeleton
      })
    return () => { mounted = false }
  }, [runId])

  useEffect(() => {
    if (!isRunning) {
      wsRef.current?.close()
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current)
      return
    }

    let disposed = false

    function connect() {
      if (disposed) return

      const callbacks: RunWebSocketCallbacks = {
        // Mutable frame buffer — WS handler writes directly, no React state updates
        frameBuffer: frameBufferRef.current,
        onMetrics: (data) => {
          const m: RunMetrics = {
            step: data.step,
            timestamp: data.timestamp ?? Date.now() / 1000,
            reward: data.reward,
            avg_reward: data.avg_reward,
            best_reward: data.best_reward,
            fps: data.fps,
            rollout_fps: data.rollout_fps,
            phase: data.phase,
            cumulative_rollout_time: data.cumulative_rollout_time,
            cumulative_training_time: data.cumulative_training_time,
            loss: data.loss,
            epsilon: data.epsilon,
            details: data.details,
            type: data.type ?? "metric",
          }
          setMetrics(m)
          setHistory((prev) => {
            const next = [...prev, m]
            return next.length > 2000 ? next.slice(-2000) : next
          })

          // Update phase from metric data when present
          if (m.phase) setPhase(m.phase)

          if (data.type === "episode") {
            setEpisodeCount((prev) => prev + 1)
          }
        },
        onPhase: (p) => {
          // Normalize: "rollout_end"/"training_end" are transient, map to next phase
          if (p === "training_end") setPhase("rollout")
          else if (p === "rollout_end") setPhase("training")
          else setPhase(p)
        },
        onStatus: () => {
          queryClient.invalidateQueries({ queryKey: runKeys.detail(runId) })
        },
        onError: (error) => {
          toast.error(`Run error: ${error}`)
        },
        onConnectionError: () => {
          toast.warning("Live connection lost — reconnecting...")
        },
      }

      const ws = createRunWebSocket(runId, callbacks)
      wsRef.current = ws

      ws.onopen = () => {
        setWsIsOpen(true)
        retryRef.current = 0
      }

      ws.onclose = () => {
        setWsIsOpen(false)
        if (disposed) return
        // Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 30s
        const delay = Math.min(1000 * Math.pow(2, retryRef.current), 30000)
        retryRef.current += 1
        retryTimerRef.current = setTimeout(connect, delay)
      }
    }

    connect()

    return () => {
      disposed = true
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current)
      wsRef.current?.close()
    }
  }, [runId, isRunning, queryClient])

  // Derive isConnected: only connected when running AND websocket is open
  const isConnected = isRunning && wsIsOpen

  return { metrics, history, isConnected, frameBufferRef, episodeCount, metricsLoaded, phase }
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
              rollout_fps: data.rollout_fps,
              phase: data.phase,
              cumulative_rollout_time: data.cumulative_rollout_time,
              cumulative_training_time: data.cumulative_training_time,
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
  }
}
