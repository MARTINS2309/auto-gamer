import { useQuery } from "@tanstack/react-query"
import { api, type Run } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Play, Square, Activity, Clock, Trophy, Zap, Plus } from "lucide-react"
import { Link } from "@tanstack/react-router"
import { formatDistanceToNow } from "date-fns"

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

function StatCard({
  title,
  value,
  icon: Icon,
  color,
}: {
  title: string
  value: string | number
  icon: React.ElementType
  color?: string
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-mono-sm tracking-stat text-muted-foreground flex items-center gap-2">
          <Icon className={`size-4 ${color || ""}`} />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className={`text-3xl font-semibold ${color || ""}`}>{value}</p>
      </CardContent>
    </Card>
  )
}

export function DashboardPage() {
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ["runs"],
    queryFn: api.runs.list,
    refetchInterval: 5000,
  })

  const activeRuns = runs.filter((r) => r.status === "running")
  const totalSteps = runs.reduce((acc, r) => acc + r.steps, 0)
  const bestReward = Math.max(...runs.map((r) => r.best_reward), 0)

  const recentActivity = runs
    .slice(0, 10)
    .map((run) => ({
      id: run.id,
      type: run.status,
      message: `${run.rom_name} - ${run.state}`,
      time: run.started_at || run.created_at,
    }))

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-muted-foreground">Training overview</p>
        </div>
        <Link to="/roms">
          <Button>
            <Plus className="size-4" />
            New Run
          </Button>
        </Link>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 stagger-children">
        <StatCard
          title="Active Runs"
          value={activeRuns.length}
          icon={Activity}
          color="text-primary"
        />
        <StatCard
          title="Total Steps"
          value={totalSteps.toLocaleString()}
          icon={Zap}
        />
        <StatCard
          title="Best Reward"
          value={bestReward}
          icon={Trophy}
          color="text-chart-1"
        />
        <StatCard
          title="Uptime"
          value="--"
          icon={Clock}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Runs Table */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Active Runs</span>
              {activeRuns.length > 1 && (
                <Button variant="destructive" size="sm">
                  <Square className="size-3" />
                  Stop All
                </Button>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="text-muted-foreground">Loading...</p>
            ) : activeRuns.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Play className="size-8 mx-auto mb-2 opacity-50" />
                <p>No active runs</p>
                <Link to="/roms" className="text-primary hover:underline text-sm">
                  Start a new run
                </Link>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ROM</TableHead>
                    <TableHead>State</TableHead>
                    <TableHead>Algorithm</TableHead>
                    <TableHead className="text-right">Steps</TableHead>
                    <TableHead className="text-right">FPS</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {activeRuns.map((run) => (
                    <TableRow key={run.id}>
                      <TableCell className="font-medium">
                        <Link
                          to="/runs/$runId"
                          params={{ runId: run.id }}
                          className="hover:text-primary"
                        >
                          {run.rom_name}
                        </Link>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {run.state}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{run.algorithm}</Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {run.steps.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {run.fps.toFixed(1)}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon-xs"
                          onClick={() => api.runs.stop(run.id)}
                        >
                          <Square className="size-3" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Activity Feed */}
        <Card>
          <CardHeader>
            <CardTitle>Activity</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-80">
              <div className="px-6 pb-6 space-y-3">
                {recentActivity.length === 0 ? (
                  <p className="text-muted-foreground text-center py-4">
                    No recent activity
                  </p>
                ) : (
                  recentActivity.map((activity) => (
                    <div
                      key={activity.id}
                      className="flex items-start gap-3 text-sm"
                    >
                      <StatusBadge status={activity.type as Run["status"]} />
                      <div className="flex-1 min-w-0">
                        <p className="truncate">{activity.message}</p>
                        <p className="text-muted-foreground text-xs">
                          {formatDistanceToNow(new Date(activity.time), {
                            addSuffix: true,
                          })}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
