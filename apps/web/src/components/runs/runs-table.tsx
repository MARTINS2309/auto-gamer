import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Square, Copy, ExternalLink } from "lucide-react"
import { Link } from "@tanstack/react-router"
import { formatDistanceToNow } from "date-fns"
import { toast } from "sonner"
import { StatusBadge } from "@/components/shared"
import type { Run } from "@/lib/schemas"
import { useRoms, useGameMetadata } from "@/hooks"

interface RunsTableProps {
  runs: Run[]
  isLoading: boolean
  selected: Set<string>
  onToggleSelect: (id: string) => void
  onToggleSelectAll: () => void
  onStopRun: (id: string) => void
}

function copyId(id: string) {
  navigator.clipboard.writeText(id)
  toast.success("Run ID copied")
}

function RunRow({
  run,
  isSelected,
  onToggleSelect,
  onStopRun
}: {
  run: Run
  isSelected: boolean
  onToggleSelect: (id: string) => void
  onStopRun: (id: string) => void
}) {
  const { data: roms = [] } = useRoms()
  const rom = roms.find(r => r.id === run.rom)
  const { data: metadata } = useGameMetadata(
    rom?.system ?? null,
    rom?.id ?? null
  )

  const displayName = metadata?.name ?? rom?.name ?? run.rom

  return (
    <TableRow>
      <TableCell>
        <Checkbox
          checked={isSelected}
          onCheckedChange={() => onToggleSelect(run.id)}
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
      <TableCell className="font-medium">
        <div className="flex items-center gap-2">
          {metadata?.cover_url && (
            <img
              src={metadata.cover_url}
              alt={metadata.name}
              className="w-8 h-10 object-cover rounded shadow-sm hidden sm:block"
            />
          )}
          <span className="truncate max-w-[200px]" title={`${displayName} (${rom?.system ?? "Unknown"})`}>{displayName}</span>
        </div>
      </TableCell>
      <TableCell className="text-muted-foreground">{run.state}</TableCell>
      <TableCell>
        <Badge variant="outline">{run.algorithm}</Badge>
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
              onClick={() => onStopRun(run.id)}
            >
              <Square className="size-3" />
            </Button>
          )}
        </div>
      </TableCell>
    </TableRow>
  )
}

export function RunsTable({
  runs,
  isLoading,
  selected,
  onToggleSelect,
  onToggleSelectAll,
  onStopRun,
}: RunsTableProps) {
  if (isLoading) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        Loading runs...
      </div>
    )
  }

  if (runs.length === 0) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        No runs found
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-10">
            <Checkbox
              checked={selected.size === runs.length && runs.length > 0}
              onCheckedChange={onToggleSelectAll}
            />
          </TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Run ID</TableHead>
          <TableHead>Game</TableHead>
          <TableHead>State</TableHead>
          <TableHead>Algorithm</TableHead>
          <TableHead>Started</TableHead>
          <TableHead></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {runs.map((run) => (
          <RunRow
            key={run.id}
            run={run}
            isSelected={selected.has(run.id)}
            onToggleSelect={onToggleSelect}
            onStopRun={onStopRun}
          />
        ))}
      </TableBody>
    </Table>
  )
}
