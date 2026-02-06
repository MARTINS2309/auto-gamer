import { useRun, useRunMetrics } from "./use-runs"
import type { RunMetrics } from "@/lib/schemas"

export function useRunDetails(runId: string) {
    const { data: run, isLoading, error } = useRun(runId)
    const isRunning = run?.status === "running"
    const {
        metrics: liveMetrics,
        history,
        gridFrame,
        focusedFrame,
        focusedEnv,
        setFocusedEnv,
        setFrameFreq,
    } = useRunMetrics(runId, isRunning)

    const currentMetrics: RunMetrics = liveMetrics || {
        step: 0,
        timestamp: 0,
        reward: 0,
        avg_reward: 0,
        best_reward: 0,
        fps: 0,
        type: "metric",
    }

    return {
        run,
        isLoading,
        error,
        currentMetrics,
        history,
        isRunning,
        gridFrame,
        focusedFrame,
        focusedEnv,
        setFocusedEnv,
        setFrameFreq,
    }
}
