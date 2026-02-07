import { Zap, Trophy, TrendingUp, Activity, Clock, BarChart3 } from "lucide-react"
import { formatDuration, intervalToDuration } from "date-fns"
import { StatTile } from "@/components/shared"
import { Skeleton } from "@/components/ui/skeleton"
import type { Run, RunMetrics } from "@/lib/schemas"

interface RunStatsGridProps {
    run: Run
    metrics: RunMetrics
    episodeCount?: number
    isLoading?: boolean
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

export function RunStatsGrid({ run, metrics, episodeCount, isLoading }: RunStatsGridProps) {
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
                label="FPS"
                value={(metrics.fps ?? 0).toFixed(1)}
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
                icon={BarChart3}
            />
        </div>
    )
}
