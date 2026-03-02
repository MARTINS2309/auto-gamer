import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Square, Copy, Plus } from "lucide-react"
import { Link } from "@tanstack/react-router"
import { formatDistanceToNow } from "date-fns"
import { toast } from "sonner"
import { StatusBadge } from "@/components/shared"
import { NewRunDialog } from "@/components/runs/new-run-dialog"
import { formatSteps } from "@/lib/schemas"
import type { Run, RomListItem } from "@/lib/schemas"

interface RunsTableProps {
  runs: Run[]
  isLoading: boolean
  selected: Set<string>
  onToggleSelect: (id: string) => void
  onToggleSelectAll: () => void
  onStopRun: (id: string) => void
  romsMap?: Map<string, RomListItem>
}

function copyId(id: string) {
  navigator.clipboard.writeText(id)
  toast.success("Run ID copied")
}

function RunRow({
  run,
  isSelected,
  onToggleSelect,
  onStopRun,
  rom,
}: {
  run: Run
  isSelected: boolean
  onToggleSelect: (id: string) => void
  onStopRun: (id: string) => void
  rom: RomListItem | undefined
}) {
  const displayName = run.game_name ?? rom?.display_name ?? run.rom
  const thumbnailUrl = run.game_thumbnail_url ?? rom?.thumbnail_url

  const runLink = { to: "/runs/$runId" as const, params: { runId: run.id } }

  return (
    <TableRow>
      <TableCell>
        <Checkbox
          checked={isSelected}
          onCheckedChange={() => onToggleSelect(run.id)}
        />
      </TableCell>
      <TableCell>
        <Link {...runLink} className="block">
          <StatusBadge status={run.status} />
        </Link>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-1">
          <Link {...runLink} className="font-mono text-xs text-muted-foreground hover:text-foreground">
            {run.id.slice(0, 8)}...
          </Link>
          <button
            onClick={(e) => { e.stopPropagation(); copyId(run.id) }}
            className="text-muted-foreground hover:text-foreground"
          >
            <Copy className="size-3" />
          </button>
        </div>
      </TableCell>
      <TableCell>
        {run.agent_id ? (
          <Link to="/agents" className="block space-y-0.5 hover:text-foreground">
            <span className="font-medium">{run.agent_name ?? "Unknown"}</span>
            <div className="flex items-center gap-1.5">
              <Badge variant="outline" className="text-[10px] px-1 py-0">{run.algorithm}</Badge>
            </div>
          </Link>
        ) : (
          <span className="text-muted-foreground italic">No agent</span>
        )}
      </TableCell>
      <TableCell className="font-medium">
        <Link to="/roms" className="flex items-center gap-2 hover:text-foreground">
          {thumbnailUrl && (
            <img
              src={thumbnailUrl}
              alt={displayName}
              className="w-8 h-10 object-cover shadow-sm"
            />
          )}
          <div className="truncate max-w-[180px]">
            <span title={`${displayName} (${rom?.system ?? "Unknown"})`}>{displayName}</span>
            <div className="text-xs text-muted-foreground">{run.state}</div>
          </div>
        </Link>
      </TableCell>
      <TableCell className="text-right tabular-nums text-sm">
        <Link {...runLink} className="block hover:text-foreground">
          {run.latest_step != null ? formatSteps(run.latest_step) : "--"}
          <span className="text-muted-foreground text-xs"> / {formatSteps(run.max_steps)}</span>
        </Link>
      </TableCell>
      <TableCell className="text-right tabular-nums text-sm">
        <Link {...runLink} className="block hover:text-foreground">
          {run.best_reward != null ? run.best_reward.toFixed(1) : "--"}
        </Link>
      </TableCell>
      <TableCell className="text-muted-foreground text-sm">
        <Link {...runLink} className="block hover:text-foreground">
          {run.started_at
            ? formatDistanceToNow(new Date(run.started_at), { addSuffix: true })
            : "--"}
        </Link>
      </TableCell>
      <TableCell>
        {run.status === "running" && (
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={() => onStopRun(run.id)}
          >
            <Square className="size-3" />
          </Button>
        )}
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
  romsMap,
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
      <div className="p-12 text-center text-muted-foreground space-y-3">
        <p>No runs found</p>
        <NewRunDialog
          trigger={
            <Button variant="outline" size="sm">
              <Plus className="size-4 mr-2" />
              Start your first run
            </Button>
          }
        />
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
          <TableHead>Agent</TableHead>
          <TableHead>Game</TableHead>
          <TableHead className="text-right">Steps</TableHead>
          <TableHead className="text-right">Best Reward</TableHead>
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
            rom={romsMap?.get(run.rom)}
          />
        ))}
      </TableBody>
    </Table>
  )
}
