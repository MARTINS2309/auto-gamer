import { User, Users, UserPlus, Globe, LayoutGrid, Swords } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface GameModeBadgesProps {
  gameModes: string[]
  variant?: "compact" | "full"
  className?: string
}

const GAME_MODE_ICONS: Record<string, LucideIcon> = {
  "Single player": User,
  "Multiplayer": Users,
  "Co-operative": UserPlus,
  "Co-op": UserPlus,
  "Split screen": LayoutGrid,
  "Massively Multiplayer Online (MMO)": Globe,
  "MMO": Globe,
  "Battle Royale": Swords,
}

function getGameModeIcon(mode: string): LucideIcon {
  return GAME_MODE_ICONS[mode] || Users
}

export function GameModeBadges({
  gameModes,
  variant = "full",
  className,
}: GameModeBadgesProps) {
  if (!gameModes || gameModes.length === 0) return null

  if (variant === "compact") {
    return (
      <div className={cn("flex items-center gap-1", className)}>
        {gameModes.map((mode) => {
          const Icon = getGameModeIcon(mode)
          return (
            <Tooltip key={mode}>
              <TooltipTrigger asChild>
                <span className="text-muted-foreground">
                  <Icon className="size-4" />
                </span>
              </TooltipTrigger>
              <TooltipContent>{mode}</TooltipContent>
            </Tooltip>
          )
        })}
      </div>
    )
  }

  return (
    <div className={cn("flex flex-wrap gap-1.5", className)}>
      {gameModes.map((mode) => {
        const Icon = getGameModeIcon(mode)
        return (
          <Badge key={mode} variant="outline" className="text-xs">
            <Icon className="size-3 mr-1" />
            {mode}
          </Badge>
        )
      })}
    </div>
  )
}
