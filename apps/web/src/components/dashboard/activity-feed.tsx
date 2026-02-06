import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { formatDistanceToNow } from "date-fns"
import {
  Filter,
  Play,
  Square,
  Trophy,
  Zap,
  AlertCircle,
  CheckCircle,
} from "lucide-react"
import type { Run, ActivityEventType, ActivityEvent } from "@/lib/schemas"
import { useActivityFeed } from "@/hooks/use-activity"
import { useStopRun, useResumeRun, useRoms } from "@/hooks"

interface ActivityFeedProps {
  runs: Run[]
  limit?: number
}

const EVENT_ICONS: Record<ActivityEventType, React.ElementType> = {
  run_started: Play,
  run_stopped: Square,
  run_completed: CheckCircle,
  run_failed: AlertCircle,
  milestone_reward: Trophy,
  milestone_steps: Zap,
}

const EVENT_COLORS: Record<ActivityEventType, string> = {
  run_started: "text-chart-1",
  run_stopped: "text-muted-foreground",
  run_completed: "text-primary",
  run_failed: "text-destructive",
  milestone_reward: "text-chart-2",
  milestone_steps: "text-chart-4",
}

const FILTER_LABELS: Record<ActivityEventType, string> = {
  run_started: "Run Started",
  run_stopped: "Run Stopped",
  run_completed: "Run Completed",
  run_failed: "Run Failed",
  milestone_reward: "Reward Milestones",
  milestone_steps: "Step Milestones",
}

const ALL_EVENT_TYPES: ActivityEventType[] = [
  "run_started",
  "run_stopped",
  "run_completed",
  "run_failed",
  "milestone_reward",
  "milestone_steps",
]

function ActivityItem({
  event,
  runs,
  stopRun,
  resumeRun
}: {
  event: ActivityEvent
  runs: Run[]
  stopRun: ReturnType<typeof useStopRun>
  resumeRun: ReturnType<typeof useResumeRun>
}) {
  const Icon = EVENT_ICONS[event.type]
  const color = EVENT_COLORS[event.type]

  const run = runs.find((r) => r.id === event.runId)
  const runStatus = run?.status ?? null

  // ROM data now includes all metadata directly
  const { data: roms = [] } = useRoms()
  const romId = run?.rom || event.runName // Fallback if run not found but we have name
  const rom = roms.find(r => r.id === romId)

  const displayName = rom?.display_name ?? event.runName
  const thumbnailUrl = rom?.thumbnail_url

  return (
    <div
      className="flex items-start gap-3 text-sm group"
    >
      <div className="mt-0.5 relative">
        <Icon className={`size-4 ${color}`} />
        {thumbnailUrl && (
          <img
            src={thumbnailUrl}
            alt={displayName}
            className="absolute -top-1 -left-1 w-6 h-6 object-cover opacity-0 group-hover:opacity-100 transition-opacity"
          />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <p className="font-medium truncate" title={displayName}>{displayName}</p>
        <p className="text-muted-foreground truncate">
          {event.message}
        </p>
        <p className="text-muted-foreground text-xs">
          {formatDistanceToNow(new Date(event.timestamp), {
            addSuffix: true,
          })}
        </p>
      </div>

      {/* Quick actions - show on hover */}
      <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
        {runStatus === "running" && (
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={() => stopRun.mutate(event.runId)}
            title="Stop run"
          >
            <Square className="size-3" />
          </Button>
        )}
        {runStatus === "stopped" && (
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={() => resumeRun.mutate(event.runId)}
            title="Resume run"
          >
            <Play className="size-3" />
          </Button>
        )}
      </div>
    </div>
  )
}

export function ActivityFeed({ runs, limit = 50 }: ActivityFeedProps) {
  const { filteredEvents, activeFilter, setFilter } = useActivityFeed({
    runs,
    limit,
  })

  const stopRun = useStopRun()
  const resumeRun = useResumeRun()

  const toggleFilter = (type: ActivityEventType) => {
    if (!activeFilter) {
      setFilter([type])
    } else if (activeFilter.includes(type)) {
      const newFilter = activeFilter.filter((t) => t !== type)
      setFilter(newFilter.length > 0 ? newFilter : null)
    } else {
      setFilter([...activeFilter, type])
    }
  }

  if (filteredEvents.length === 0) {
    return (
      <div className="p-4">
        <FilterDropdown
          activeFilter={activeFilter}
          toggleFilter={toggleFilter}
        />
        <p className="text-muted-foreground text-center py-4">
          No recent activity
        </p>
      </div>
    )
  }

  return (
    <div>
      <div className="px-4 pb-2">
        <FilterDropdown
          activeFilter={activeFilter}
          toggleFilter={toggleFilter}
        />
      </div>
      <ScrollArea className="h-80">
        <div className="px-6 pb-6 space-y-3">
          {filteredEvents.map((event) => (
            <ActivityItem
              key={event.id}
              event={event}
              runs={runs}
              stopRun={stopRun}
              resumeRun={resumeRun}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}

function FilterDropdown({
  activeFilter,
  toggleFilter,
}: {
  activeFilter: ActivityEventType[] | null
  toggleFilter: (type: ActivityEventType) => void
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="xs" className="gap-2">
          <Filter className="size-3" />
          Filter
          {activeFilter && (
            <Badge variant="secondary" className="ml-1 text-xs px-1">
              {activeFilter.length}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        {ALL_EVENT_TYPES.map((type) => (
          <DropdownMenuCheckboxItem
            key={type}
            checked={!activeFilter || activeFilter.includes(type)}
            onCheckedChange={() => toggleFilter(type)}
          >
            {FILTER_LABELS[type]}
          </DropdownMenuCheckboxItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
