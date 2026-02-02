import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Plus, Square, Activity, Clock, Trophy, Zap } from "lucide-react"
import { Link } from "@tanstack/react-router"
import { useRuns, useStopRun, useRunStats } from "@/hooks"
import { StatCard } from "@/components/shared"
import { ActiveRunsTable, ActivityFeed } from "@/components/dashboard"

export function DashboardPage() {
  const { data: runs = [], isLoading } = useRuns()
  const stopRun = useStopRun()
  const stats = useRunStats(runs)

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
          value={stats.activeCount}
          icon={Activity}
          color="text-primary"
        />
        <StatCard
          title="Total Steps"
          value={stats.totalSteps.toLocaleString()}
          icon={Zap}
        />
        <StatCard
          title="Best Reward"
          value={stats.bestReward}
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
              {stats.activeCount > 1 && (
                <Button variant="destructive" size="sm">
                  <Square className="size-3" />
                  Stop All
                </Button>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ActiveRunsTable
              runs={stats.activeRuns}
              isLoading={isLoading}
              onStopRun={(id) => stopRun.mutate(id)}
            />
          </CardContent>
        </Card>

        {/* Activity Feed */}
        <Card>
          <CardHeader>
            <CardTitle>Activity</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ActivityFeed runs={runs} limit={10} />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
