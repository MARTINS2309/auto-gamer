import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

interface GenreBadgesProps {
  genres: string[]
  variant?: "compact" | "full"
  maxDisplay?: number
  className?: string
}

const GENRE_COLORS: Record<string, string> = {
  "Role-playing (RPG)": "bg-purple-500/20 text-purple-400 border-purple-500/30",
  "RPG": "bg-purple-500/20 text-purple-400 border-purple-500/30",
  "Action": "bg-red-500/20 text-red-400 border-red-500/30",
  "Adventure": "bg-blue-500/20 text-blue-400 border-blue-500/30",
  "Platform": "bg-orange-500/20 text-orange-400 border-orange-500/30",
  "Platformer": "bg-orange-500/20 text-orange-400 border-orange-500/30",
  "Strategy": "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  "Puzzle": "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
  "Sport": "bg-lime-500/20 text-lime-400 border-lime-500/30",
  "Sports": "bg-lime-500/20 text-lime-400 border-lime-500/30",
  "Racing": "bg-amber-500/20 text-amber-400 border-amber-500/30",
  "Shooter": "bg-rose-500/20 text-rose-400 border-rose-500/30",
  "Fighting": "bg-red-600/20 text-red-500 border-red-600/30",
  "Simulation": "bg-sky-500/20 text-sky-400 border-sky-500/30",
  "Arcade": "bg-pink-500/20 text-pink-400 border-pink-500/30",
}

function getGenreColor(genre: string): string {
  return GENRE_COLORS[genre] || "bg-secondary text-secondary-foreground"
}

export function GenreBadges({
  genres,
  variant = "full",
  maxDisplay = 2,
  className,
}: GenreBadgesProps) {
  if (!genres || genres.length === 0) return null

  const displayGenres = variant === "compact" ? genres.slice(0, maxDisplay) : genres
  const remainingCount = genres.length - maxDisplay

  return (
    <div className={cn("flex flex-wrap gap-1.5", className)}>
      {displayGenres.map((genre) => (
        <Badge
          key={genre}
          variant="outline"
          className={cn("text-xs", getGenreColor(genre))}
        >
          {genre}
        </Badge>
      ))}
      {variant === "compact" && remainingCount > 0 && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant="outline" className="text-xs">
              +{remainingCount}
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            {genres.slice(maxDisplay).join(", ")}
          </TooltipContent>
        </Tooltip>
      )}
    </div>
  )
}
