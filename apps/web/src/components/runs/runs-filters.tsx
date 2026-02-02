import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog"
import { Search, Square, Trash2 } from "lucide-react"

interface RunsFiltersProps {
  search: string
  onSearchChange: (value: string) => void
  statusFilter: string
  onStatusFilterChange: (value: string) => void
}

export function RunsFilters({
  search,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
}: RunsFiltersProps) {
  return (
    <div className="flex items-center gap-4 flex-wrap">
      <div className="relative flex-1 min-w-64">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Input
          placeholder="Search runs..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-9"
        />
      </div>

      <ToggleGroup
        type="single"
        value={statusFilter}
        onValueChange={(v) => v && onStatusFilterChange(v)}
      >
        <ToggleGroupItem value="all">All</ToggleGroupItem>
        <ToggleGroupItem value="running">Running</ToggleGroupItem>
        <ToggleGroupItem value="completed">Completed</ToggleGroupItem>
        <ToggleGroupItem value="failed">Failed</ToggleGroupItem>
        <ToggleGroupItem value="stopped">Stopped</ToggleGroupItem>
      </ToggleGroup>
    </div>
  )
}

interface BulkActionsProps {
  selectedCount: number
  onStop: () => void
  onDelete: () => void
}

export function BulkActions({ selectedCount, onStop, onDelete }: BulkActionsProps) {
  if (selectedCount === 0) return null

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-muted-foreground">
        {selectedCount} selected
      </span>
      <Button variant="outline" size="sm" onClick={onStop}>
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
            <AlertDialogTitle>Delete {selectedCount} runs?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. All run data will be permanently deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={onDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
