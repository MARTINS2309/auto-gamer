import { Zap, Trophy, TrendingUp, Activity, Clock, BarChart3 } from "lucide-react"
import { formatDuration, intervalToDuration } from "date-fns"
import { StatTile } from "@/components/shared"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import type { Run, RunMetrics } from "@/lib/schemas"

interface RunStatsGridProps {
    run: Run
    metrics: RunMetrics
    episodeCount?: number
    isLoading?: boolean
    phase?: string | null
    history?: RunMetrics[]
}

function StatTileSkeleton() {
    return (
        <div className="flex items-center gap-3 p-4 border">
            <Skeleton className="size-5" />
            <div className="space-y-2">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-6 w-24" />
            </div>
        </div>
    )
}

export function RunStatsGrid({ run, metrics, episodeCount, isLoading, phase, history }: RunStatsGridProps) {
    if (isLoading) {
        return (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-0 border bg-background">
                {Array.from({ length: 6 }, (_, i) => (
                    <StatTileSkeleton key={i} />
                ))}
            </div>
        )
    }

    const elapsed = run.started_at
        ? intervalToDuration({
            start: new Date(run.started_at),
            end: run.completed_at ? new Date(run.completed_at) : new Date(),
        })
        : null

    // Use rollout FPS when available (excludes training time), fall back to wall FPS
    const displayFps = metrics.rollout_fps ?? metrics.fps ?? 0

    // Episode throughput: ep/min from recent 5-minute window
    let epPerMin: string | undefined
    if (history && history.length > 1 && run.status === "running") {
        const now = history[history.length - 1].timestamp
        const windowStart = now - 300 // 5 minutes
        const recentEpisodes = history.filter(m => m.type === "episode" && m.timestamp >= windowStart)
        if (recentEpisodes.length >= 2) {
            const dt = now - recentEpisodes[0].timestamp
            if (dt > 0) {
                epPerMin = `~${(recentEpisodes.length / (dt / 60)).toFixed(1)} ep/min`
            }
        }
    }

    // Phase time breakdown: percentage of time spent in rollout vs training
    const rolloutTime = metrics.cumulative_rollout_time
    const trainingTime = metrics.cumulative_training_time
    const phaseBreakdown = rolloutTime != null && trainingTime != null && (rolloutTime + trainingTime) > 0
        ? `${Math.round((rolloutTime / (rolloutTime + trainingTime)) * 100)}% rollout`
        : undefined

    return (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-0 border bg-background">
            <StatTile
                label="Total Steps"
                value={metrics.step.toLocaleString()}
                icon={Zap}
            />
            <StatTile
                label="Best Reward"
                value={metrics.best_reward ?? "--"}
                icon={Trophy}
                color="text-chart-1"
            />
            <StatTile
                label="Avg Reward"
                value={metrics.avg_reward?.toFixed(1) ?? "--"}
                icon={TrendingUp}
            />
            <StatTile
                label={
                    <span className="flex items-center gap-1.5">
                        {metrics.rollout_fps != null ? "Rollout FPS" : "FPS"}
                        {phase && run.status === "running" && (
                            <Badge
                                variant={phase === "rollout" ? "default" : "secondary"}
                                className="text-[10px] px-1 py-0 h-4 font-normal"
                            >
                                {phase === "rollout" ? "Collecting" : "Training"}
                            </Badge>
                        )}
                    </span>
                }
                value={displayFps.toFixed(0)}
                subValue={phaseBreakdown}
                icon={Activity}
            />
            <StatTile
                label="Elapsed"
                value={elapsed ? formatDuration(elapsed, { format: ["hours", "minutes"] }) || "< 1m" : "--"}
                icon={Clock}
            />
            <StatTile
                label="Episodes"
                value={episodeCount != null ? episodeCount.toLocaleString() : "--"}
                subValue={epPerMin}
                icon={BarChart3}
            />
        </div>
    )
}
