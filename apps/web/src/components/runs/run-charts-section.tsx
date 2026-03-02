import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { MetricsChart } from "./metrics-chart"
import { useRuns } from "@/hooks"
import { api } from "@/lib/api"
import type { RunMetrics } from "@/lib/schemas"

const WINDOW_OPTIONS = [50, 100, 500, 0] as const
const WINDOW_LABELS: Record<number, string> = { 50: "50", 100: "100", 500: "500", 0: "All" }

interface RunChartsSectionProps {
    history: RunMetrics[]
    /** Current run ID — excluded from comparison picker */
    runId?: string
    /** Current run's rom — used to filter sibling runs for comparison */
    rom?: string
}

export function RunChartsSection({ history, runId, rom }: RunChartsSectionProps) {
    const [windowSize, setWindowSize] = useState<number>(100)
    const [comparisonRunId, setComparisonRunId] = useState<string | null>(null)

    // Fetch all runs for the comparison picker (only same rom, exclude current)
    const { data: allRuns = [] } = useRuns({ refetchInterval: false })
    const siblingRuns = useMemo(
        () => allRuns.filter(r => r.rom === rom && r.id !== runId),
        [allRuns, rom, runId]
    )

    // Fetch comparison run's metrics
    const { data: comparisonHistory } = useQuery({
        queryKey: ["run-comparison-metrics", comparisonRunId],
        queryFn: () => api.runs.metrics(comparisonRunId!),
        enabled: !!comparisonRunId,
        staleTime: 60_000,
    })

    // Check for availability of advanced metrics (from SB3 logger)
    const hasValueLoss = history.some(m => m.details?.["train/value_loss"] !== undefined);
    const hasPolicyLoss = history.some(m => m.details?.["train/policy_gradient_loss"] !== undefined);
    const hasEntropy = history.some(m => m.details?.["train/entropy_loss"] !== undefined);
    const hasKLDivergence = history.some(m => m.details?.["train/approx_kl"] !== undefined);
    const hasExplainedVariance = history.some(m => m.details?.["train/explained_variance"] !== undefined);
    const hasLearningRate = history.some(m => m.details?.["train/learning_rate"] !== undefined);
    const hasLoss = history.some(m => m.loss !== undefined && m.loss !== null);
    const hasRolloutFps = history.some(m => m.rollout_fps !== undefined && m.rollout_fps !== null);

    // Step array for all history entries
    const allSteps = useMemo(() => history.map(m => m.step), [history])

    // Helper to extract data+steps stream — filters nulls while keeping step alignment
    const getStreamWithSteps = (key: string): { data: number[]; steps: number[] } => {
        const data: number[] = []
        const steps: number[] = []
        for (let i = 0; i < history.length; i++) {
            const v = history[i].details?.[key]
            if (v === undefined || v === null) continue
            const num = typeof v === 'number' ? v : parseFloat(v as string)
            if (isNaN(num)) continue
            data.push(num)
            steps.push(history[i].step)
        }
        return { data, steps }
    }

    // Phase transition markers — detect where phase changes
    const phaseMarkers = useMemo(() => {
        const markers: { index: number; phase: string }[] = []
        let lastPhase: string | null = null
        for (let i = 0; i < history.length; i++) {
            const p = history[i].phase
            if (p && p !== lastPhase) {
                markers.push({ index: i, phase: p })
                lastPhase = p
            }
        }
        return markers
    }, [history])

    // Convergence detection: has best_reward improved in last 50 data points?
    const isPlateaued = useMemo(() => {
        if (history.length < 60) return false
        const recent = history.slice(-50)
        const older = history.slice(-60, -50)
        const recentBest = Math.max(...recent.map(m => m.best_reward ?? -Infinity))
        const olderBest = Math.max(...older.map(m => m.best_reward ?? -Infinity))
        return recentBest <= olderBest
    }, [history])

    // Filter out zeros for reward charts (zeros mean no episodes completed yet)
    const avgRewards = history.map((m) => m.avg_reward ?? 0)
    const bestRewards = history.map((m) => m.best_reward ?? 0)
    const hasRewardData = avgRewards.some(r => r !== 0) || bestRewards.some(r => r !== 0)

    // FPS stream with steps (filter zeros for rollout fps)
    const fpsData = hasRolloutFps
        ? (() => {
            const data: number[] = []
            const steps: number[] = []
            for (let i = 0; i < history.length; i++) {
                const v = history[i].rollout_fps
                if (v != null && v > 0) { data.push(v); steps.push(history[i].step) }
            }
            return { data, steps }
        })()
        : { data: history.map(m => m.fps ?? 0), steps: allSteps }

    // Loss stream with steps
    const lossData = hasLoss
        ? (() => {
            const data: number[] = []
            const steps: number[] = []
            for (let i = 0; i < history.length; i++) {
                const v = history[i].loss
                if (v != null && v !== 0) { data.push(v); steps.push(history[i].step) }
            }
            return { data, steps }
        })()
        : { data: [], steps: [] }

    // Comparison data
    const cmpAvgRewards = comparisonHistory?.map(m => m.avg_reward ?? 0)
    const cmpBestRewards = comparisonHistory?.map(m => m.best_reward ?? 0)

    return (
        <div className="space-y-3">
            {/* Chart toolbar */}
            <div className="flex items-center gap-4 flex-wrap">
                <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">Window:</span>
                    {WINDOW_OPTIONS.map(size => (
                        <button
                            key={size}
                            className={`text-xs px-2 py-0.5 border transition-colors ${
                                windowSize === size
                                    ? "bg-primary text-primary-foreground border-primary"
                                    : "bg-background text-muted-foreground border-border hover:text-foreground"
                            }`}
                            onClick={() => setWindowSize(size)}
                        >
                            {WINDOW_LABELS[size]}
                        </button>
                    ))}
                </div>

                {siblingRuns.length > 0 && (
                    <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">Compare:</span>
                        <Select
                            value={comparisonRunId ?? "none"}
                            onValueChange={(v) => setComparisonRunId(v === "none" ? null : v)}
                        >
                            <SelectTrigger className="h-7 w-48 text-xs">
                                <SelectValue placeholder="Select run..." />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="none">None</SelectItem>
                                {siblingRuns.map(r => (
                                    <SelectItem key={r.id} value={r.id}>
                                        {r.algorithm} — {r.best_reward?.toFixed(1) ?? "?"} ({r.status})
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Episode Reward (Mean)</CardTitle>
                        {!hasRewardData && (
                            <CardDescription className="text-xs">
                                Waiting for episodes to complete...
                            </CardDescription>
                        )}
                    </CardHeader>
                    <CardContent className="h-60 pt-4">
                        <MetricsChart
                            data={avgRewards}
                            steps={allSteps}
                            color="bg-chart-1"
                            className="items-end"
                            label="Avg Reward"
                            windowSize={windowSize}
                            phaseMarkers={phaseMarkers}
                            comparisonData={cmpAvgRewards}
                        />
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <div className="flex items-center gap-2">
                            <CardTitle className="text-sm">Best Reward</CardTitle>
                            {isPlateaued && (
                                <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 text-muted-foreground">
                                    Plateau
                                </Badge>
                            )}
                        </div>
                    </CardHeader>
                    <CardContent className="h-60 pt-4">
                        <MetricsChart
                            data={bestRewards}
                            steps={allSteps}
                            color="bg-chart-2"
                            className="items-end"
                            label="Best"
                            windowSize={windowSize}
                            phaseMarkers={phaseMarkers}
                            comparisonData={cmpBestRewards}
                        />
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm">
                            {hasRolloutFps ? "Rollout FPS (excl. training)" : "FPS Over Time"}
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="h-60 pt-4">
                        <MetricsChart
                            data={fpsData.data}
                            steps={fpsData.steps}
                            color="bg-chart-4"
                            className="items-end"
                            label={hasRolloutFps ? "Rollout FPS" : "FPS"}
                            windowSize={windowSize}
                            phaseMarkers={phaseMarkers}
                        />
                    </CardContent>
                </Card>

                {hasLoss && (
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm">Training Loss</CardTitle>
                        </CardHeader>
                        <CardContent className="h-60 pt-4">
                            <MetricsChart
                                data={lossData.data}
                                steps={lossData.steps}
                                color="bg-chart-3"
                                className="items-end"
                                label="Loss"
                                windowSize={windowSize}
                                phaseMarkers={phaseMarkers}
                            />
                        </CardContent>
                    </Card>
                )}

                {hasValueLoss && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-sm">Value Loss</CardTitle>
                        </CardHeader>
                        <CardContent className="h-60 pt-4">
                            <MetricsChart
                                {...getStreamWithSteps("train/value_loss")}
                                color="bg-chart-3"
                                className="items-end"
                                label="Value Loss"
                                windowSize={windowSize}
                            />
                        </CardContent>
                    </Card>
                )}

                {hasPolicyLoss && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-sm">Policy Gradient Loss</CardTitle>
                        </CardHeader>
                        <CardContent className="h-60 pt-4">
                            <MetricsChart
                                {...getStreamWithSteps("train/policy_gradient_loss")}
                                color="bg-chart-4"
                                className="items-end"
                                label="Policy Loss"
                                windowSize={windowSize}
                            />
                        </CardContent>
                    </Card>
                )}

                {hasEntropy && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-sm">Entropy Loss</CardTitle>
                        </CardHeader>
                        <CardContent className="h-60 pt-4">
                            <MetricsChart
                                {...getStreamWithSteps("train/entropy_loss")}
                                color="bg-chart-5"
                                className="items-end"
                                label="Entropy"
                                windowSize={windowSize}
                            />
                        </CardContent>
                    </Card>
                )}

                {hasKLDivergence && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-sm">Approx KL Divergence</CardTitle>
                        </CardHeader>
                        <CardContent className="h-60 pt-4">
                            <MetricsChart
                                {...getStreamWithSteps("train/approx_kl")}
                                color="bg-chart-2"
                                className="items-end"
                                label="KL Div"
                                windowSize={windowSize}
                            />
                        </CardContent>
                    </Card>
                )}

                {hasExplainedVariance && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-sm">Explained Variance</CardTitle>
                        </CardHeader>
                        <CardContent className="h-60 pt-4">
                            <MetricsChart
                                {...getStreamWithSteps("train/explained_variance")}
                                color="bg-chart-4"
                                className="items-end"
                                label="Variance"
                                windowSize={windowSize}
                            />
                        </CardContent>
                    </Card>
                )}

                {hasLearningRate && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-sm">Learning Rate</CardTitle>
                        </CardHeader>
                        <CardContent className="h-60 pt-4">
                            <MetricsChart
                                {...getStreamWithSteps("train/learning_rate")}
                                color="bg-chart-3"
                                className="items-end"
                                label="LR"
                                windowSize={windowSize}
                            />
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    )
}
