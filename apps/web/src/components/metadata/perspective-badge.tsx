import { Eye, UserCircle, Compass, ArrowRightLeft, FileText, Headphones, Glasses } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface PerspectiveBadgeProps {
  perspectives: string[]
  variant?: "compact" | "full"
  className?: string
}

const PERSPECTIVE_ICONS: Record<string, LucideIcon> = {
  "First person": Eye,
  "Third person": UserCircle,
  "Bird view / Isometric": Compass,
  "Bird view": Compass,
  "Isometric": Compass,
  "Side view": ArrowRightLeft,
  "Text": FileText,
  "Auditory": Headphones,
  "Virtual Reality": Glasses,
  "VR": Glasses,
}

function getPerspectiveIcon(perspective: string): LucideIcon {
  return PERSPECTIVE_ICONS[perspective] || Eye
}

export function PerspectiveBadge({
  perspectives,
  variant = "full",
  className,
}: PerspectiveBadgeProps) {
  if (!perspectives || perspectives.length === 0) return null

  if (variant === "compact") {
    return (
      <div className={cn("flex items-center gap-1", className)}>
        {perspectives.map((perspective) => {
          const Icon = getPerspectiveIcon(perspective)
          return (
            <Tooltip key={perspective}>
              <TooltipTrigger asChild>
                <span className="text-muted-foreground">
                  <Icon className="size-4" />
                </span>
              </TooltipTrigger>
              <TooltipContent>{perspective}</TooltipContent>
            </Tooltip>
          )
        })}
      </div>
    )
  }

  return (
    <div className={cn("flex flex-wrap gap-1.5", className)}>
      {perspectives.map((perspective) => {
        const Icon = getPerspectiveIcon(perspective)
        return (
          <Badge key={perspective} variant="outline" className="text-xs text-muted-foreground">
            <Icon className="size-3 mr-1" />
            {perspective}
          </Badge>
        )
      })}
    </div>
  )
}
