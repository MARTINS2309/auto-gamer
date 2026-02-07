import { useState } from "react"
import { Link } from "@tanstack/react-router"
import { Activity, Gauge, Trophy, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Page, PageHeader, PageTitle, PageDescription, PageActions, PageContent } from "@/components/ui/page"
import { useRuns, useRunStats, useAggregatedRunMetrics, useRoms } from "@/hooks"
import { StatCard } from "@/components/shared"
import {
  ActivityFeed,
  DashboardFrameViewer,
  NoSignalHero,
  MetricsTicker,
  FeaturedRomCarousel,
} from "@/components/dashboard"
import { NewRunDialog } from "@/components/runs/new-run-dialog"

export function DashboardPage() {
  const { data: runs = [] } = useRuns()
  const { data: roms = [] } = useRoms()
  const stats = useRunStats(runs)
  const { aggregated, metricsMap } = useAggregatedRunMetrics(
    stats.activeRuns.map((r) => r.id)
  )

  // For opening NewRunDialog with a pre-selected ROM from the carousel
  const [selectedRomId, setSelectedRomId] = useState<string | null>(null)
  const [newRunOpen, setNewRunOpen] = useState(false)

  const handleSelectRom = (romId: string) => {
    setSelectedRomId(romId)
    setNewRunOpen(true)
  }

  return (
    <Page>
      <PageHeader className="flex-row items-center justify-between">
        <div>
          <PageTitle>Live Arena</PageTitle>
          <PageDescription>
            {stats.activeCount > 0
              ? `${stats.activeCount} agent${stats.activeCount !== 1 ? "s" : ""} training`
              : "No active training"}
          </PageDescription>
        </div>
        <PageActions>
          <NewRunDialog />
        </PageActions>
      </PageHeader>

      <PageContent className="space-y-6">
        {/* Hero: Live Frame Grid or No Signal */}
        {stats.activeCount > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 stagger-children">
            {stats.activeRuns.slice(0, 4).map((run) => {
              const rom = roms.find((r) => r.id === run.rom)
              return (
                <DashboardFrameViewer
                  key={run.id}
                  runId={run.id}
                  gameName={rom?.display_name ?? run.rom}
                  algorithm={run.algorithm}
                  thumbnailUrl={rom?.thumbnail_url}
                />
              )
            })}
          </div>
        ) : (
          <NoSignalHero />
        )}

        {/* Metrics Ticker */}
        <MetricsTicker runs={stats.activeRuns} metricsMap={metricsMap} />

        {/* Bottom: ROM Carousel + Feed (3/5) | Stat Cards (2/5) */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="lg:col-span-3 space-y-6">
            <FeaturedRomCarousel
              roms={roms}
              onSelectRom={handleSelectRom}
            />
            <Card>
              <CardHeader>
                <CardTitle>Activity</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <ActivityFeed runs={runs} roms={roms} limit={8} />
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-2 space-y-3">
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
              title="Avg FPS"
              value={aggregated.avgFps > 0 ? aggregated.avgFps.toFixed(0) : "--"}
              icon={Gauge}
              color="text-chart-3"
            />

            {/* Nav links */}
            <div className="flex flex-col gap-2 pt-2">
              <Button variant="outline" asChild>
                <Link to="/runs">View All Runs</Link>
              </Button>
              <Button variant="outline" asChild>
                <Link to="/roms">Browse Library</Link>
              </Button>
            </div>
          </div>
        </div>
      </PageContent>

      {/* NewRunDialog triggered by ROM carousel selection */}
      <NewRunDialog
        open={newRunOpen}
        onOpenChange={setNewRunOpen}
        initialValues={selectedRomId ? { rom: selectedRomId } : undefined}
      />
    </Page>
  )
}
