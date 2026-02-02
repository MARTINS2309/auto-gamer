import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api, type Run } from "@/lib/api"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog"
import { Search, Square, Trash2, Copy, ExternalLink } from "lucide-react"
import { Link } from "@tanstack/react-router"
import { formatDistanceToNow } from "date-fns"
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

export function RunsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const { data: runs = [], isLoading } = useQuery({
    queryKey: ["runs"],
    queryFn: api.runs.list,
    refetchInterval: 5000,
  })

  const stopRun = useMutation({
    mutationFn: api.runs.stop,
    onSuccess: () => {
      toast.success("Run stopped")
      queryClient.invalidateQueries({ queryKey: ["runs"] })
    },
  })

  const deleteRun = useMutation({
    mutationFn: api.runs.delete,
    onSuccess: () => {
      toast.success("Run deleted")
      queryClient.invalidateQueries({ queryKey: ["runs"] })
    },
  })

  const filteredRuns = runs.filter((run) => {
    const matchesSearch =
      run.rom_name.toLowerCase().includes(search.toLowerCase()) ||
      run.id.toLowerCase().includes(search.toLowerCase())
    const matchesStatus =
      statusFilter === "all" || run.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const toggleSelect = (id: string) => {
    const next = new Set(selected)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
    }
    setSelected(next)
  }

  const toggleSelectAll = () => {
    if (selected.size === filteredRuns.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(filteredRuns.map((r) => r.id)))
    }
  }

  const handleBulkStop = () => {
    selected.forEach((id) => {
      const run = runs.find((r) => r.id === id)
      if (run?.status === "running") {
        stopRun.mutate(id)
      }
    })
    setSelected(new Set())
  }

  const handleBulkDelete = () => {
    selected.forEach((id) => deleteRun.mutate(id))
    setSelected(new Set())
  }

  const copyId = (id: string) => {
    navigator.clipboard.writeText(id)
    toast.success("Run ID copied")
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold">Runs</h1>
        <p className="text-muted-foreground">All training runs</p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="relative flex-1 min-w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            placeholder="Search runs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        <ToggleGroup
          type="single"
          value={statusFilter}
          onValueChange={(v) => v && setStatusFilter(v)}
        >
          <ToggleGroupItem value="all">All</ToggleGroupItem>
          <ToggleGroupItem value="running">Running</ToggleGroupItem>
          <ToggleGroupItem value="completed">Completed</ToggleGroupItem>
          <ToggleGroupItem value="failed">Failed</ToggleGroupItem>
          <ToggleGroupItem value="stopped">Stopped</ToggleGroupItem>
        </ToggleGroup>

        {/* Bulk actions */}
        {selected.size > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {selected.size} selected
            </span>
            <Button variant="outline" size="sm" onClick={handleBulkStop}>
              <Square className="size-3" />
              Stop
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" size="sm">
                  <Trash2 className="size-3" />
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
                  <AlertDialogAction onClick={handleBulkDelete}>
                    Delete
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        )}
      </div>

      {/* Runs Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground">
              Loading runs...
            </div>
          ) : filteredRuns.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              No runs found
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <Checkbox
                      checked={selected.size === filteredRuns.length && filteredRuns.length > 0}
                      onCheckedChange={toggleSelectAll}
                    />
                  </TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Run ID</TableHead>
                  <TableHead>ROM</TableHead>
                  <TableHead>State</TableHead>
                  <TableHead>Algorithm</TableHead>
                  <TableHead className="text-right">Steps</TableHead>
                  <TableHead className="text-right">Best</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRuns.map((run) => (
                  <TableRow key={run.id}>
                    <TableCell>
                      <Checkbox
                        checked={selected.has(run.id)}
                        onCheckedChange={() => toggleSelect(run.id)}
                      />
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={run.status} />
                    </TableCell>
                    <TableCell>
                      <button
                        onClick={() => copyId(run.id)}
                        className="font-mono text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
                      >
                        {run.id.slice(0, 8)}...
                        <Copy className="size-3" />
                      </button>
                    </TableCell>
                    <TableCell className="font-medium">{run.rom_name}</TableCell>
                    <TableCell className="text-muted-foreground">{run.state}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{run.algorithm}</Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {run.steps.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-mono text-chart-1">
                      {run.best_reward}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {run.started_at
                        ? formatDistanceToNow(new Date(run.started_at), { addSuffix: true })
                        : "--"}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Link to="/runs/$runId" params={{ runId: run.id }}>
                          <Button variant="ghost" size="icon-xs">
                            <ExternalLink className="size-3" />
                          </Button>
                        </Link>
                        {run.status === "running" && (
                          <Button
                            variant="ghost"
                            size="icon-xs"
                            onClick={() => stopRun.mutate(run.id)}
                          >
                            <Square className="size-3" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Footer */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>{filteredRuns.length} runs</span>
        <Button variant="outline" size="sm" disabled>
          Export CSV
        </Button>
      </div>
    </div>
  )
}
