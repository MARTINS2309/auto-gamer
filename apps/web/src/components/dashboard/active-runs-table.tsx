import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Play, Square } from "lucide-react"
import { Link } from "@tanstack/react-router"
import type { Run } from "@/lib/schemas"
import { NewRunDialog } from "@/components/runs/new-run-dialog"
import { useRoms, useGameMetadata } from "@/hooks"

interface ActiveRunsTableProps {
  runs: Run[]
  isLoading: boolean
  onStopRun: (id: string) => void
}

function ActiveRunRow({ run, onStopRun }: { run: Run, onStopRun: (id: string) => void }) {
  const { data: roms = [] } = useRoms()
  const rom = roms.find(r => r.id === run.rom)
  const { data: metadata } = useGameMetadata(
    rom?.system ?? null,
    rom?.id ?? null
  )

  return (
    <TableRow>
      <TableCell className="font-medium">
        <div className="flex items-center gap-3">
          {metadata?.cover_url ? (
            <img
              src={metadata.cover_url}
              alt={metadata.name}
              className="w-8 h-10 object-cover rounded shadow-sm"
            />
          ) : (
            <div className="w-8 h-10 bg-muted rounded flex items-center justify-center text-xs text-muted-foreground">
              ?
            </div>
          )}
          <div className="flex flex-col">
            <Link
              to="/runs/$runId"
              params={{ runId: run.id }}
              className="hover:text-primary font-semibold"
            >
              {metadata?.name ?? rom?.name ?? run.rom}
            </Link>
            <span className="text-xs text-muted-foreground truncate max-w-[150px]">
              {run.id}
            </span>
          </div>
        </div>
      </TableCell>
      <TableCell className="text-muted-foreground capitalize">{run.state ?? run.status}</TableCell>
      <TableCell>
        <Badge variant="outline">{run.algorithm}</Badge>
      </TableCell>
      <TableCell>
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={() => onStopRun(run.id)}
        >
          <Square className="size-3" />
        </Button>
      </TableCell>
    </TableRow>
  )
}

export function ActiveRunsTable({ runs, isLoading, onStopRun }: ActiveRunsTableProps) {
  if (isLoading) {
    return <p className="text-muted-foreground">Loading...</p>
  }

  if (runs.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Play className="size-8 mx-auto mb-2 opacity-50" />
        <p>No active runs</p>
        <NewRunDialog
          trigger={
            <Button variant="link" className="text-primary hover:underline text-sm p-0 h-auto">
              Start a new run
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
          <TableHead>Game</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Algorithm</TableHead>
          <TableHead></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {runs.map((run) => (
          <ActiveRunRow key={run.id} run={run} onStopRun={onStopRun} />
        ))}
      </TableBody>
    </Table>
  )
}
