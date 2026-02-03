import { Zap, Trophy, TrendingUp, Activity, Clock, BarChart3 } from "lucide-react"
import { formatDuration, intervalToDuration } from "date-fns"
import { StatTile } from "@/components/shared"
import type { Run, RunMetrics } from "@/lib/schemas"

interface RunStatsGridProps {
    run: Run
    metrics: RunMetrics
}

export function RunStatsGrid({ run, metrics }: RunStatsGridProps) {
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
                value={metrics.best_reward}
                icon={Trophy}
                color="text-chart-1"
            />
            <StatTile
                label="Avg Reward"
                value={metrics.avg_reward.toFixed(1)}
                icon={TrendingUp}
            />
            <StatTile
                label="FPS"
                value={metrics.fps.toFixed(1)}
                icon={Activity}
            />
            <StatTile
                label="Elapsed"
                value={elapsed ? formatDuration(elapsed, { format: ["hours", "minutes"] }) || "< 1m" : "--"}
                icon={Clock}
            />
            <StatTile
                label="Episodes"
                value="--"
                icon={BarChart3}
            />
        </div>
    )
}
