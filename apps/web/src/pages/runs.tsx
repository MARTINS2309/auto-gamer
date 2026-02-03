import { useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Page, PageHeader, PageTitle, PageDescription, PageContent } from "@/components/ui/page"
import { useRuns, useStopRun, useBulkDeleteRuns } from "@/hooks"
import { RunsTable, RunsFilters, BulkActions, filterRuns } from "@/components/runs"
import { NewRunDialog } from "@/components/runs/new-run-dialog"
import type { Run } from "@/lib/schemas"

function useRunSelection(filteredRuns: Run[]) {
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const toggleSelect = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }, [])

  const toggleSelectAll = useCallback(() => {
    setSelected((prev) => {
      if (prev.size === filteredRuns.length) {
        return new Set()
      }
      return new Set(filteredRuns.map((r) => r.id))
    })
  }, [filteredRuns])

  const clearSelection = useCallback(() => {
    setSelected(new Set())
  }, [])

  return { selected, toggleSelect, toggleSelectAll, clearSelection }
}

export function RunsPage() {
  const { data: runs = [], isLoading } = useRuns()
  const stopRun = useStopRun()
  const bulkDelete = useBulkDeleteRuns()

  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")

  const filteredRuns = filterRuns(runs, search, statusFilter)
  const { selected, toggleSelect, toggleSelectAll, clearSelection } = useRunSelection(filteredRuns)

  const handleBulkStop = () => {
    selected.forEach((id) => {
      const run = runs.find((r) => r.id === id)
      if (run?.status === "running") {
        stopRun.mutate(id)
      }
    })
    clearSelection()
  }

  const handleBulkDelete = () => {
    bulkDelete.mutate([...selected])
    clearSelection()
  }

  return (
    <Page>
      <PageHeader>
        <div>
          <PageTitle>Runs</PageTitle>
          <PageDescription>All training runs</PageDescription>
        </div>
        <NewRunDialog />
      </PageHeader>

      <PageContent className="space-y-6">
        {/* Filters & Bulk Actions */}
        <div className="flex items-center gap-4 flex-wrap">
          <RunsFilters
            search={search}
            onSearchChange={setSearch}
            statusFilter={statusFilter}
            onStatusFilterChange={setStatusFilter}
          />
          <BulkActions
            selectedCount={selected.size}
            onStop={handleBulkStop}
            onDelete={handleBulkDelete}
          />
        </div>

        {/* Runs Table */}
        <Card>
          <CardContent className="p-0">
            <RunsTable
              runs={filteredRuns}
              isLoading={isLoading}
              selected={selected}
              onToggleSelect={toggleSelect}
              onToggleSelectAll={toggleSelectAll}
              onStopRun={(id) => stopRun.mutate(id)}
            />
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{filteredRuns.length} runs</span>
          <Button variant="outline" size="sm" disabled>
            Export CSV
          </Button>
        </div>
      </PageContent>
    </Page>
  )
}
