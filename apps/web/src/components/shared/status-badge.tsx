import { Badge } from "@/components/ui/badge"
import { RUN_STATUS_VARIANTS, type RunStatus } from "@/lib/schemas"

interface StatusBadgeProps {
  status: RunStatus
  animate?: boolean
}

export function StatusBadge({ status, animate = true }: StatusBadgeProps) {
  return (
    <Badge
      variant={RUN_STATUS_VARIANTS[status]}
      className={animate && status === "running" ? "animate-live" : ""}
    >
      {status}
    </Badge>
  )
}
