import { ScrollArea } from "@/components/ui/scroll-area"
import { StatusBadge } from "@/components/shared"
import { formatDistanceToNow } from "date-fns"
import type { Run, RunStatus } from "@/lib/schemas"

interface ActivityItem {
  id: string
  status: RunStatus
  message: string
  time: string
}

function runToActivity(run: Run): ActivityItem {
  return {
    id: run.id,
    status: run.status,
    message: `${run.rom} - ${run.state}`,
    time: run.started_at || run.created_at,
  }
}

interface ActivityFeedProps {
  runs: Run[]
  limit?: number
}

export function ActivityFeed({ runs, limit = 10 }: ActivityFeedProps) {
  const activities = runs.slice(0, limit).map(runToActivity)

  if (activities.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-4">
        No recent activity
      </p>
    )
  }

  return (
    <ScrollArea className="h-80">
      <div className="px-6 pb-6 space-y-3">
        {activities.map((activity) => (
          <div key={activity.id} className="flex items-start gap-3 text-sm">
            <StatusBadge status={activity.status} />
            <div className="flex-1 min-w-0">
              <p className="truncate">{activity.message}</p>
              <p className="text-muted-foreground text-xs">
                {formatDistanceToNow(new Date(activity.time), { addSuffix: true })}
              </p>
            </div>
          </div>
        ))}
      </div>
    </ScrollArea>
  )
}
