import { useParams } from "@tanstack/react-router"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog"
import { Square, Trash2, Copy, ChevronDown, Zap, Trophy, TrendingUp, Clock, Activity, BarChart3 } from "lucide-react"
import { formatDuration, intervalToDuration } from "date-fns"
import { toast } from "sonner"
import { useRun, useStopRun, useDeleteRun, useRunMetrics } from "@/hooks"
import { StatusBadge, StatTile } from "@/components/shared"
import type { RunMetrics } from "@/lib/schemas"

function MetricsChart({ data, color, maxValue }: { data: number[]; color: string; maxValue?: number }) {
  if (data.length === 0) {
    return <span className="text-muted-foreground">No data yet</span>
  }

  const max = maxValue ?? (Math.max(...data) || 1)

  return (
    <div className="w-full h-full flex items-end gap-px">
      {data.slice(-100).map((value, i) => (
        <div
          key={i}
          className={`flex-1 ${color} min-w-px`}
          style={{ height: `${Math.max(5, (value / max) * 100)}%` }}
        />
      ))}
    </div>
  )
}

export function RunDetailPage() {
  const { runId } = useParams({ from: "/runs/$runId" })

  const { data: run, isLoading } = useRun(runId)
  const stopRun = useStopRun()
  const deleteRun = useDeleteRun()

  const isRunning = run?.status === "running"
  const { metrics: liveMetrics, history } = useRunMetrics(runId, isRunning)

  const copyId = () => {
    navigator.clipboard.writeText(runId)
    toast.success("Run ID copied")
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Loading run...</p>
      </div>
    )
  }

  if (!run) {
    return (
      <div className="p-6">
        <p className="text-destructive">Run not found</p>
      </div>
    )
  }

  // Metrics come from WebSocket when running, otherwise show placeholder
  const currentMetrics: RunMetrics = liveMetrics || {
    step: 0,
    reward: 0,
    avg_reward: 0,
    best_reward: 0,
    fps: 0,
  }

  const elapsed = run.started_at
    ? intervalToDuration({
        start: new Date(run.started_at),
        end: run.completed_at ? new Date(run.completed_at) : new Date(),
      })
    : null

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">{run.rom}</h1>
            <StatusBadge status={run.status} />
            <Badge variant="outline">{run.algorithm}</Badge>
          </div>
          <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
            <span>{run.state}</span>
            <button onClick={copyId} className="flex items-center gap-1 hover:text-foreground">
              <Copy className="size-3" />
              {runId.slice(0, 8)}...
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isRunning && (
            <Button
              variant="outline"
              onClick={() => stopRun.mutate(runId)}
              disabled={stopRun.isPending}
            >
              <Square className="size-4" />
              Stop
            </Button>
          )}
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive">
                <Trash2 className="size-4" />
                Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this run?</AlertDialogTitle>
                <AlertDialogDescription>
                  This action cannot be undone. All run data will be permanently deleted.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={() => deleteRun.mutate(runId)}>
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-0 border">
        <StatTile
          label="Total Steps"
          value={currentMetrics.step.toLocaleString()}
          icon={Zap}
        />
        <StatTile
          label="Best Reward"
          value={currentMetrics.best_reward}
          icon={Trophy}
          color="text-chart-1"
        />
        <StatTile
          label="Avg Reward"
          value={currentMetrics.avg_reward.toFixed(1)}
          icon={TrendingUp}
        />
        <StatTile
          label="FPS"
          value={currentMetrics.fps.toFixed(1)}
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

      {/* Progress */}
      {isRunning && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Training Progress</span>
            <span className="font-mono">{currentMetrics.step.toLocaleString()} steps</span>
          </div>
          <Progress value={Math.min((currentMetrics.step / 1000000) * 100, 100)} />
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Episode Reward</CardTitle>
          </CardHeader>
          <CardContent className="h-60 flex items-center justify-center">
            <MetricsChart data={history.map((m) => m.reward)} color="bg-chart-1" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">FPS Over Time</CardTitle>
          </CardHeader>
          <CardContent className="h-60 flex items-center justify-center">
            <MetricsChart data={history.map((m) => m.fps)} color="bg-chart-4" maxValue={60} />
          </CardContent>
        </Card>
      </div>

      {/* Config */}
      <Collapsible>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" className="w-full justify-between">
            Configuration
            <ChevronDown className="size-4" />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <Card className="mt-2">
            <CardContent className="pt-6">
              <pre className="text-xs font-mono overflow-auto">
                {JSON.stringify(
                  {
                    rom: run.rom,
                    state: run.state,
                    algorithm: run.algorithm,
                    hyperparams: run.hyperparams,
                    max_steps: run.max_steps,
                    n_envs: run.n_envs,
                    created_at: run.created_at,
                    started_at: run.started_at,
                  },
                  null,
                  2
                )}
              </pre>
            </CardContent>
          </Card>
        </CollapsibleContent>
      </Collapsible>

      {/* Error display */}
      {run.error && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-sm font-mono text-destructive whitespace-pre-wrap">
              {run.error}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
