import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Play } from "lucide-react"
import { Link } from "@tanstack/react-router"
import { StatusBadge } from "@/components/shared"
import type { Rom, Run } from "@/lib/schemas"

interface RomDetailSheetProps {
  rom: Rom | undefined
  isLoading: boolean
  isOpen: boolean
  onClose: () => void
  selectedState: string
  onStateChange: (state: string) => void
  onStartRun: () => void
  isStartingRun: boolean
  recentRuns: Run[]
}

export function RomDetailSheet({
  rom,
  isLoading,
  isOpen,
  onClose,
  selectedState,
  onStateChange,
  onStartRun,
  isStartingRun,
  recentRuns,
}: RomDetailSheetProps) {
  const states = rom?.states ?? []

  return (
    <Sheet open={isOpen} onOpenChange={() => onClose()}>
      <SheetContent className="sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>{rom?.name ?? "Loading..."}</SheetTitle>
          <SheetDescription>
            {rom && <Badge variant="outline">{rom.system}</Badge>}
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {/* State Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Save State</label>
            {isLoading ? (
              <p className="text-sm text-muted-foreground">Loading states...</p>
            ) : states.length === 0 ? (
              <p className="text-sm text-muted-foreground">No save states available</p>
            ) : (
              <Select value={selectedState} onValueChange={onStateChange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select state" />
                </SelectTrigger>
                <SelectContent>
                  {states.map((state) => (
                    <SelectItem key={state} value={state}>
                      {state}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Start Button */}
          <Button
            className="w-full"
            disabled={!selectedState || isStartingRun}
            onClick={onStartRun}
          >
            <Play className="size-4" />
            {isStartingRun ? "Starting..." : "Start Training"}
          </Button>

          {/* Recent Runs */}
          <RecentRunsTable runs={recentRuns} />
        </div>
      </SheetContent>
    </Sheet>
  )
}

function RecentRunsTable({ runs }: { runs: Run[] }) {
  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium">Recent Runs</h4>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>State</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Algorithm</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {runs.length === 0 ? (
            <TableRow>
              <TableCell colSpan={3} className="text-center text-muted-foreground">
                No runs yet
              </TableCell>
            </TableRow>
          ) : (
            runs.map((run) => (
              <TableRow key={run.id}>
                <TableCell>
                  <Link
                    to="/runs/$runId"
                    params={{ runId: run.id }}
                    className="hover:underline"
                  >
                    {run.state}
                  </Link>
                </TableCell>
                <TableCell>
                  <StatusBadge status={run.status} />
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {run.algorithm}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}
