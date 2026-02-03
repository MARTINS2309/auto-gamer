import { useParams } from "@tanstack/react-router"
import { Page, PageContent, PageHeader, PageTitle } from "@/components/ui/page"
import { Progress } from "@/components/ui/progress"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useRunDetails } from "@/hooks"
import { RunDetailsHeader } from "@/components/runs/run-details-header"
import { RunStatsGrid } from "@/components/runs/run-stats-grid"
import { RunChartsSection } from "@/components/runs/run-charts-section"
import { RunConfiguration } from "@/components/runs/run-configuration"

export function RunDetailPage() {
  const { runId } = useParams({ from: "/runs/$runId" })
  const { run, isLoading, currentMetrics, history, error, isRunning } = useRunDetails(runId)

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
    return (
      <Page>
        <PageHeader>
          <PageTitle>Not Found</PageTitle>
        </PageHeader>
        <PageContent>
          <p className="text-destructive">Run not found</p>
        </PageContent>
      </Page>
    )
  }

  return (
    <Page>
      <RunDetailsHeader run={run} />

      <PageContent className="space-y-6">
        <RunStatsGrid run={run} metrics={currentMetrics} />

        {isRunning && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Training Progress</span>
              <span className="text-xs text-muted-foreground">
                {Math.floor((currentMetrics.step / run.max_steps) * 100)}% ({currentMetrics.step.toLocaleString()} / {run.max_steps.toLocaleString()})
              </span>
            </div>
            <Progress value={(currentMetrics.step / run.max_steps) * 100} />
          </div>
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
