import { useState, useEffect, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useParams, useNavigate } from "@tanstack/react-router"
import { api, createRunWebSocket, type Run, type RunMetrics } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog"
import { Square, Trash2, Copy, ChevronDown, Zap, Trophy, TrendingUp, Clock, Activity, BarChart3 } from "lucide-react"
import { formatDuration, intervalToDuration } from "date-fns"
import { toast } from "sonner"

function StatusBadge({ status }: { status: Run["status"] }) {
  const variants: Record<Run["status"], "default" | "secondary" | "destructive" | "outline"> = {
    running: "default",
    completed: "secondary",
    failed: "destructive",
    stopped: "outline",
    pending: "outline",
  }

  return (
    <Badge
      variant={variants[status]}
      className={status === "running" ? "animate-live" : ""}
    >
      {status}
    </Badge>
  )
}

function StatTile({
  label,
  value,
  subValue,
  icon: Icon,
  color,
}: {
  label: string
  value: string | number
  subValue?: string
  icon: React.ElementType
  color?: string
}) {
  return (
    <div className="flex items-center gap-3 p-4 border">
      <Icon className={`size-5 ${color || "text-muted-foreground"}`} />
      <div>
        <p className="text-xs text-muted-foreground uppercase tracking-wider">{label}</p>
        <p className={`text-xl font-semibold ${color || ""}`}>{value}</p>
        {subValue && <p className="text-xs text-muted-foreground">{subValue}</p>}
      </div>
    </div>
  )
}

export function RunDetailPage() {
  const { runId } = useParams({ from: "/runs/$runId" })
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)

  const [liveMetrics, setLiveMetrics] = useState<RunMetrics | null>(null)
  const [metricsHistory, setMetricsHistory] = useState<RunMetrics[]>([])

  const { data: run, isLoading } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.runs.get(runId),
    refetchInterval: (query) => {
      const data = query.state.data
      return data?.status === "running" ? false : 5000
    },
  })

  const stopRun = useMutation({
    mutationFn: () => api.runs.stop(runId),
    onSuccess: () => {
      toast.success("Run stopped")
      queryClient.invalidateQueries({ queryKey: ["run", runId] })
      queryClient.invalidateQueries({ queryKey: ["runs"] })
    },
  })

  const deleteRun = useMutation({
    mutationFn: () => api.runs.delete(runId),
    onSuccess: () => {
      toast.success("Run deleted")
      queryClient.invalidateQueries({ queryKey: ["runs"] })
      navigate({ to: "/runs" })
    },
  })

  // WebSocket connection for live metrics
  useEffect(() => {
    if (run?.status !== "running") {
      wsRef.current?.close()
      return
    }

    const ws = createRunWebSocket(
      runId,
      (data) => {
        if ("step" in data) {
          setLiveMetrics(data as RunMetrics)
          setMetricsHistory((prev) => [...prev.slice(-500), data as RunMetrics])
        } else if (data.type === "status") {
          queryClient.invalidateQueries({ queryKey: ["run", runId] })
        } else if (data.type === "error") {
          toast.error(`Run error: ${data.error}`)
        }
      },
      () => {
        toast.error("WebSocket connection lost")
      }
    )

    wsRef.current = ws

    return () => {
      ws.close()
    }
  }, [runId, run?.status, queryClient])

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

  const currentMetrics = liveMetrics || {
    step: run.steps,
    reward: 0,
    avg_reward: run.avg_reward,
    best_reward: run.best_reward,
    fps: run.fps,
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
            <h1 className="text-2xl font-semibold">{run.rom_name}</h1>
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
          {run.status === "running" && (
            <Button variant="outline" onClick={() => stopRun.mutate()} disabled={stopRun.isPending}>
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
                <AlertDialogAction onClick={() => deleteRun.mutate()}>
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
      {run.status === "running" && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Training Progress</span>
            <span className="font-mono">{currentMetrics.step.toLocaleString()} steps</span>
          </div>
          <Progress value={Math.min((currentMetrics.step / 1000000) * 100, 100)} />
        </div>
      )}

      {/* Charts placeholder */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Episode Reward</CardTitle>
          </CardHeader>
          <CardContent className="h-60 flex items-center justify-center text-muted-foreground">
            {metricsHistory.length > 0 ? (
              <div className="w-full h-full flex items-end gap-px">
                {metricsHistory.slice(-100).map((m, i) => (
                  <div
                    key={i}
                    className="flex-1 bg-chart-1 min-w-px"
                    style={{ height: `${Math.max(5, (m.reward / (Math.max(...metricsHistory.map(x => x.reward)) || 1)) * 100)}%` }}
                  />
                ))}
              </div>
            ) : (
              "No data yet"
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">FPS Over Time</CardTitle>
          </CardHeader>
          <CardContent className="h-60 flex items-center justify-center text-muted-foreground">
            {metricsHistory.length > 0 ? (
              <div className="w-full h-full flex items-end gap-px">
                {metricsHistory.slice(-100).map((m, i) => (
                  <div
                    key={i}
                    className="flex-1 bg-chart-4 min-w-px"
                    style={{ height: `${Math.max(5, (m.fps / 60) * 100)}%` }}
                  />
                ))}
              </div>
            ) : (
              "No data yet"
            )}
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
                    rom_id: run.rom_id,
                    rom_name: run.rom_name,
                    state: run.state,
                    algorithm: run.algorithm,
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
