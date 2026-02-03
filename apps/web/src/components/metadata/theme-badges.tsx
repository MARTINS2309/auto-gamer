import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

interface ThemeBadgesProps {
  themes: string[]
  variant?: "compact" | "full"
  maxDisplay?: number
  className?: string
}

export function ThemeBadges({
  themes,
  variant = "full",
  maxDisplay = 2,
  className,
}: ThemeBadgesProps) {
  if (!themes || themes.length === 0) return null

  const displayThemes = variant === "compact" ? themes.slice(0, maxDisplay) : themes
  const remainingCount = themes.length - maxDisplay

  return (
    <div className={cn("flex flex-wrap gap-1.5", className)}>
      {displayThemes.map((theme) => (
        <Badge
          key={theme}
          variant="outline"
          className="text-xs text-muted-foreground border-muted-foreground/30"
        >
          {theme}
        </Badge>
      ))}
      {variant === "compact" && remainingCount > 0 && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant="outline" className="text-xs text-muted-foreground">
              +{remainingCount}
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            {themes.slice(maxDisplay).join(", ")}
          </TooltipContent>
        </Tooltip>
      )}
    </div>
  )
}
