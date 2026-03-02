import { useState, useCallback, useMemo } from "react"
import { Download, Search, Square, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  Page,
  PageHeader,
  PageHeaderNav,
  PageHeaderItem,
  PageTitle,
  PageContent,
} from "@/components/ui/page"
import { ButtonGroup, ButtonGroupSeparator } from "@/components/ui/button-group"
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { useRuns, useRoms, useAgents, useStopRun, useBulkDeleteRuns } from "@/hooks"
import { RunsTable, filterRuns } from "@/components/runs"
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
  const { data: roms = [] } = useRoms()
  const { data: agents = [] } = useAgents()
  const stopRun = useStopRun()
  const bulkDelete = useBulkDeleteRuns()

  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [agentFilter, setAgentFilter] = useState("all")
  const [systemFilter, setSystemFilter] = useState("all")

  const romsSystemMap = useMemo(() => {
    return new Map(roms.map((rom) => [rom.id, { system: rom.system }]))
  }, [roms])

  const romsMap = useMemo(() => {
    return new Map(roms.map((rom) => [rom.id, rom]))
  }, [roms])

  const systems = useMemo(() => {
    const sys = new Set(roms.map((r) => r.system).filter(Boolean))
    return Array.from(sys).sort()
  }, [roms])

  // Agents that have runs (for filter dropdown)
  const agentsWithRuns = useMemo(() => {
    const runAgentIds = new Set(runs.map((r) => r.agent_id).filter(Boolean))
    return agents.filter((a) => runAgentIds.has(a.id))
  }, [runs, agents])

  const filteredRuns = filterRuns(
    runs,
    search,
    statusFilter,
    "all",
    romsSystemMap,
    systemFilter,
    agentFilter
  )
  const { selected, toggleSelect, toggleSelectAll, clearSelection } = useRunSelection(filteredRuns)

  const handleBulkStop = () => {
    const toStop = [...selected].filter((id) => {
      const run = runs.find((r) => r.id === id)
      return run?.status === "running"
    })
    if (toStop.length === 0) return
    toStop.forEach((id) => stopRun.mutate(id))
    clearSelection()
  }

  const handleBulkDelete = () => {
    bulkDelete.mutate([...selected], {
      onSuccess: () => clearSelection(),
    })
  }

  const handleExportCsv = useCallback(() => {
    if (filteredRuns.length === 0) return
    const headers = ["id", "rom", "algorithm", "status", "max_steps", "n_envs", "created_at", "started_at", "completed_at", "error"]
    const rows = filteredRuns.map((r) =>
      headers.map((h) => {
        const val = r[h as keyof typeof r]
        if (val == null) return ""
        const str = String(val)
        return str.includes(",") || str.includes('"') ? `"${str.replace(/"/g, '""')}"` : str
      }).join(",")
    )
    const csv = [headers.join(","), ...rows].join("\n")
    const blob = new Blob([csv], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "runs.csv"
    a.click()
    URL.revokeObjectURL(url)
  }, [filteredRuns])

  return (
    <Page>
      <PageHeader hideOnScroll={false}>
        <PageHeaderNav>
          <PageHeaderItem>
            <PageTitle>Runs</PageTitle>
          </PageHeaderItem>

          <PageHeaderItem>
            <ButtonGroup>
              <ButtonGroup>
                <InputGroup>
                  <InputGroupAddon>
                    <Search />
                  </InputGroupAddon>
                  <InputGroupInput
                    placeholder="Search runs..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </InputGroup>
              </ButtonGroup>

              <ButtonGroupSeparator />

              <ButtonGroup>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-36">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    <SelectItem value="running">Running</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                    <SelectItem value="stopped">Stopped</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={agentFilter} onValueChange={setAgentFilter}>
                  <SelectTrigger className="w-44">
                    <SelectValue placeholder="Agent" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Agents</SelectItem>
                    {agentsWithRuns.map((agent) => (
                      <SelectItem key={agent.id} value={agent.id}>
                        {agent.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={systemFilter} onValueChange={setSystemFilter}>
                  <SelectTrigger className="w-36">
                    <SelectValue placeholder="System" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Systems</SelectItem>
                    {systems.map((sys) => (
                      <SelectItem key={sys} value={sys}>
                        {sys}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </ButtonGroup>
            </ButtonGroup>
          </PageHeaderItem>

          <PageHeaderItem className="ml-auto">
            {selected.size > 0 ? (
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground mr-2">
                  {selected.size} selected
                </span>
                <Button variant="outline" size="sm" onClick={handleBulkStop}>
                  <Square className="size-3 mr-2" />
                  Stop
                </Button>

                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="destructive" size="sm">
                      <Trash2 className="size-3 mr-2" />
                      Delete
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Delete {selected.size} runs?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This action cannot be undone. All run data will be permanently deleted.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction onClick={handleBulkDelete}>Delete</AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            ) : (
              <NewRunDialog />
            )}
          </PageHeaderItem>
        </PageHeaderNav>
      </PageHeader>

      <PageContent className="space-y-6">
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
              romsMap={romsMap}
            />
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{filteredRuns.length} runs</span>
          <Button variant="outline" size="sm" onClick={handleExportCsv} disabled={filteredRuns.length === 0}>
            <Download className="size-3 mr-2" />
            Export CSV
          </Button>
        </div>
      </PageContent>
    </Page>
  )
}
