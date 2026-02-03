import { useState, useEffect, useRef, useCallback, useMemo } from "react"
import { createRunWebSocket, type RunWebSocketCallbacks } from "@/lib/api"
import type {
  Run,
  RunMetrics,
  ActivityEvent,
  ActivityEventType,
} from "@/lib/schemas"
import { REWARD_MILESTONES, STEP_MILESTONES } from "@/lib/schemas"

interface MilestoneTracker {
  lastRewardMilestone: number
  lastStepMilestone: number
}

export interface UseActivityFeedOptions {
  runs: Run[]
  limit?: number
}

export interface UseActivityFeedResult {
  events: ActivityEvent[]
  addEvent: (event: Omit<ActivityEvent, "id">) => void
  clearEvents: () => void
  filteredEvents: ActivityEvent[]
  setFilter: (types: ActivityEventType[] | null) => void
  activeFilter: ActivityEventType[] | null
}

export function useActivityFeed({
  runs,
  limit = 50,
}: UseActivityFeedOptions): UseActivityFeedResult {
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [filter, setFilter] = useState<ActivityEventType[] | null>(null)

  // Track milestone thresholds per run to detect crossings
  const milestonesRef = useRef<Map<string, MilestoneTracker>>(new Map())

  // Track WebSocket connections
  const wsMapRef = useRef<Map<string, WebSocket>>(new Map())

  // Track previous run statuses to detect changes
  const prevStatusRef = useRef<Map<string, string>>(new Map())

  const addEvent = useCallback(
    (event: Omit<ActivityEvent, "id">) => {
      const newEvent: ActivityEvent = {
        ...event,
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      }
      setEvents((prev) => [newEvent, ...prev].slice(0, limit))
    },
    [limit]
  )

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  // Detect run status changes
  useEffect(() => {
    for (const run of runs) {
      const prevStatus = prevStatusRef.current.get(run.id)

      if (prevStatus !== run.status) {
        // Status changed
        if (run.status === "running" && prevStatus !== "running") {
          addEvent({
            type: "run_started",
            runId: run.id,
            runName: run.rom,
            timestamp: new Date().toISOString(),
            message: `Started training on ${run.state}`,
          })
        } else if (run.status === "stopped") {
          addEvent({
            type: "run_stopped",
            runId: run.id,
            runName: run.rom,
            timestamp: new Date().toISOString(),
            message: `Training stopped`,
          })
        } else if (run.status === "completed") {
          addEvent({
            type: "run_completed",
            runId: run.id,
            runName: run.rom,
            timestamp: new Date().toISOString(),
            message: `Training completed`,
          })
        } else if (run.status === "failed") {
          addEvent({
            type: "run_failed",
            runId: run.id,
            runName: run.rom,
            timestamp: new Date().toISOString(),
            message: `Training failed: ${run.error || "Unknown error"}`,
          })
        }

        prevStatusRef.current.set(run.id, run.status)
      }
    }
  }, [runs, addEvent])

  // Connect to WebSockets for active runs to detect milestones
  useEffect(() => {
    const activeRuns = runs.filter((r) => r.status === "running")
    const activeIds = new Set(activeRuns.map((r) => r.id))

    // Close connections for inactive runs
    for (const [id, ws] of wsMapRef.current) {
      if (!activeIds.has(id)) {
        ws.close()
        wsMapRef.current.delete(id)
      }
    }

    // Open connections for new active runs
    for (const run of activeRuns) {
      if (!wsMapRef.current.has(run.id)) {
        // Initialize milestone tracker
        if (!milestonesRef.current.has(run.id)) {
          milestonesRef.current.set(run.id, {
            lastRewardMilestone: -Infinity,
            lastStepMilestone: 0,
          })
        }

        const callbacks: RunWebSocketCallbacks = {
          onMetrics: (metrics: RunMetrics) => {
            const tracker = milestonesRef.current.get(run.id)
            if (!tracker) return

            // Check reward milestones
            for (const threshold of REWARD_MILESTONES) {
              if (
                metrics.best_reward >= threshold &&
                tracker.lastRewardMilestone < threshold
              ) {
                addEvent({
                  type: "milestone_reward",
                  runId: run.id,
                  runName: run.rom,
                  timestamp: new Date().toISOString(),
                  message: `Reached ${threshold} reward!`,
                  data: { reward: metrics.best_reward, threshold },
                })
                tracker.lastRewardMilestone = threshold
              }
            }

            // Check step milestones
            for (const threshold of STEP_MILESTONES) {
              if (
                metrics.step >= threshold &&
                tracker.lastStepMilestone < threshold
              ) {
                addEvent({
                  type: "milestone_steps",
                  runId: run.id,
                  runName: run.rom,
                  timestamp: new Date().toISOString(),
                  message: `Reached ${(threshold / 1000).toLocaleString()}K steps!`,
                  data: { steps: metrics.step, threshold },
                })
                tracker.lastStepMilestone = threshold
              }
            }
          },
        }

        const ws = createRunWebSocket(run.id, callbacks)
        wsMapRef.current.set(run.id, ws)
      }
    }

    return () => {
      wsMapRef.current.forEach((ws) => ws.close())
      wsMapRef.current.clear()
    }
  }, [runs, addEvent])

  const filteredEvents = useMemo(() => {
    if (!filter || filter.length === 0) return events
    return events.filter((e) => filter.includes(e.type))
  }, [events, filter])

  return {
    events,
    addEvent,
    clearEvents,
    filteredEvents,
    setFilter,
    activeFilter: filter,
  }
}
