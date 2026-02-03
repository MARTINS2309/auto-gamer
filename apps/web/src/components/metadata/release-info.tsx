import { Calendar } from "lucide-react"
import { cn } from "@/lib/utils"

interface ReleaseInfoProps {
  releaseDate?: string | null
  variant?: "compact" | "full"
  className?: string
}

function formatFullDate(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    })
  } catch {
    return dateStr
  }
}

function getRelativeTime(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    const now = new Date()
    const diffYears = now.getFullYear() - date.getFullYear()

    if (diffYears === 0) return "This year"
    if (diffYears === 1) return "1 year ago"
    return `${diffYears} years ago`
  } catch {
    return ""
  }
}

export function ReleaseInfo({
  releaseDate,
  variant = "compact",
  className,
}: ReleaseInfoProps) {
  if (!releaseDate) return null

  const year = releaseDate.split("-")[0]

  if (variant === "compact") {
    return (
      <span
        className={cn(
          "text-xs text-muted-foreground flex items-center gap-0.5",
          className
        )}
      >
        <Calendar className="size-3" />
        {year}
      </span>
    )
  }

  return (
    <div className={cn("flex items-center gap-2 text-sm", className)}>
      <Calendar className="size-4 text-muted-foreground shrink-0" />
      <span className="text-foreground">{formatFullDate(releaseDate)}</span>
      <span className="text-muted-foreground">({getRelativeTime(releaseDate)})</span>
    </div>
  )
}
