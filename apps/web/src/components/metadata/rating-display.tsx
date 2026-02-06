import { Star } from "lucide-react"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

interface RatingDisplayProps {
  rating: number | null | undefined
  ratingCount?: number | null
  variant?: "compact" | "full"
  showCount?: boolean
  className?: string
}

function getRatingColor(rating: number): string {
  if (rating >= 80) return "text-chart-2"
  if (rating >= 60) return "text-chart-1"
  if (rating >= 40) return "text-muted-foreground"
  return "text-destructive"
}

function formatRatingPercent(rating: number): string {
  return `${Math.round(rating)}%`
}

export function RatingDisplay({
  rating,
  ratingCount,
  variant = "compact",
  showCount = false,
  className,
}: RatingDisplayProps) {
  if (rating == null) return null

  const colorClass = getRatingColor(rating)

  if (variant === "compact") {
    const content = (
      <span
        className={cn(
          "text-xs flex items-center gap-1",
          colorClass,
          className
        )}
      >
        <Star className="size-3 fill-current" />
        {formatRatingPercent(rating)}
      </span>
    )

    if (ratingCount) {
      return (
        <Tooltip>
          <TooltipTrigger asChild>{content}</TooltipTrigger>
          <TooltipContent>
            {ratingCount.toLocaleString()} ratings
          </TooltipContent>
        </Tooltip>
      )
    }

    return content
  }

  // Full variant - 5 star display
  const filledStars = Math.round(rating / 20)

  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={cn(
              "size-4",
              star <= filledStars
                ? "text-chart-1 fill-chart-1"
                : "text-muted-foreground/30"
            )}
          />
        ))}
        <span className={cn("text-sm font-medium ml-2", colorClass)}>
          {formatRatingPercent(rating)}
        </span>
      </div>
      {showCount && ratingCount && (
        <p className="text-xs text-muted-foreground">
          {ratingCount.toLocaleString()} ratings
        </p>
      )}
    </div>
  )
}
