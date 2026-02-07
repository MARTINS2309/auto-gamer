import { useParams, Link } from "@tanstack/react-router"
import { Page, PageContent, PageHeader, PageTitle } from "@/components/ui/page"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useRunDetails } from "@/hooks"
import { RunDetailsHeader } from "@/components/runs/run-details-header"
import { RunStatsGrid } from "@/components/runs/run-stats-grid"
import { RunChartsSection } from "@/components/runs/run-charts-section"
import { RunConfiguration } from "@/components/runs/run-configuration"
import { RunFrameViewer } from "@/components/runs/run-frame-viewer"

export function RunDetailPage() {
  const { runId } = useParams({ from: "/runs/$runId" })
  const {
    run,
    isLoading,
    currentMetrics,
    history,
    error,
    isRunning,
    isConnected,
    frame,
    episodeCount,
    metricsLoaded,
  } = useRunDetails(runId)

  if (isLoading) {
    return (
      <Page>
        <PageHeader>
          <PageTitle>Loading...</PageTitle>
        </PageHeader>
        <PageContent>
          <p className="text-muted-foreground">Loading run...</p>
        </PageContent>
      </Page>
    )
  }

  if (error || !run) {
    const is404 = error && "status" in error && (error as { status?: number }).status === 404
    return (
      <Page>
        <PageHeader>
          <PageTitle>{is404 ? "Run Not Found" : "Error"}</PageTitle>
        </PageHeader>
        <PageContent className="space-y-4">
          <p className="text-destructive">
            {is404
              ? `No run found with ID "${runId}"`
              : error?.message ?? "Failed to load run"}
          </p>
          <Button variant="outline" size="sm" asChild>
            <Link to="/runs">Back to Runs</Link>
          </Button>
        </PageContent>
      </Page>
    )
  }

  return (
    <Page>
      <RunDetailsHeader run={run} />

      <PageContent className="space-y-6">
        {isRunning && !isConnected && (
          <div className="border border-destructive bg-destructive/10 px-4 py-2 text-sm text-destructive flex items-center gap-2">
            <span className="size-2 bg-destructive animate-pulse" />
            Live connection lost — metrics may be stale
          </div>
        )}

        <RunStatsGrid run={run} metrics={currentMetrics} episodeCount={isRunning ? episodeCount : undefined} isLoading={!metricsLoaded} />

        {isRunning && (
          <RunFrameViewer frame={frame} />
        )}

        <RunChartsSection history={history} />

        <RunConfiguration run={run} />

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
      </PageContent>
    </Page>
  )
}
