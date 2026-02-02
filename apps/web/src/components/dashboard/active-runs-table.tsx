import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Play, Square } from "lucide-react"
import { Link } from "@tanstack/react-router"
import type { Run } from "@/lib/schemas"

interface ActiveRunsTableProps {
  runs: Run[]
  isLoading: boolean
  onStopRun: (id: string) => void
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
        <Link to="/roms" className="text-primary hover:underline text-sm">
          Start a new run
        </Link>
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>ROM</TableHead>
          <TableHead>State</TableHead>
          <TableHead>Algorithm</TableHead>
          <TableHead></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {runs.map((run) => (
          <TableRow key={run.id}>
            <TableCell className="font-medium">
              <Link
                to="/runs/$runId"
                params={{ runId: run.id }}
                className="hover:text-primary"
              >
                {run.rom}
              </Link>
            </TableCell>
            <TableCell className="text-muted-foreground">{run.state}</TableCell>
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
        ))}
      </TableBody>
    </Table>
  )
}
