import { Link } from "@tanstack/react-router"
import { Plus, Square, Activity, Clock, Trophy, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Page, PageHeader, PageTitle, PageDescription, PageActions, PageContent } from "@/components/ui/page"
import { useRuns, useStopRun, useRunStats, useBulkStopRuns, useAggregatedRunMetrics } from "@/hooks"
import { StatCard } from "@/components/shared"
import { ActiveRunsTable, ActivityFeed } from "@/components/dashboard"

export function DashboardPage() {
  const { data: runs = [], isLoading } = useRuns()
  const stopRun = useStopRun()
  const bulkStop = useBulkStopRuns()
  const stats = useRunStats(runs)
  const { aggregated } = useAggregatedRunMetrics(stats.activeRuns.map((r) => r.id))

  return (
    <Page>
      <PageHeader className="flex-row items-center justify-between">
        <div>
          <PageTitle>Dashboard</PageTitle>
          <PageDescription>Training overview</PageDescription>
        </div>
        <PageActions>
          <Button asChild>
            <Link to="/roms">
              <Plus className="size-4" />
              New Run
            </Link>
          </Button>
        </PageActions>
      </PageHeader>

      <PageContent className="space-y-6">
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
            value={aggregated.totalSteps.toLocaleString()}
            icon={Zap}
          />
          <StatCard
            title="Best Reward"
            value={aggregated.bestReward}
            icon={Trophy}
            color="text-chart-1"
          />
          <StatCard
            title="Uptime"
            value={stats.uptime ?? "--"}
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
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => bulkStop(stats.activeRuns.map(r => r.id), runs)}
                  >
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
      </PageContent>
    </Page>
  )
}
