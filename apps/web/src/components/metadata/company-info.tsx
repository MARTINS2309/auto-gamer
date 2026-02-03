import { Building2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface CompanyInfoProps {
  developer?: string | null
  publisher?: string | null
  variant?: "compact" | "full"
  className?: string
}

export function CompanyInfo({
  developer,
  publisher,
  variant = "full",
  className,
}: CompanyInfoProps) {
  if (!developer && !publisher) return null

  if (variant === "compact") {
    return (
      <span className={cn("text-xs text-muted-foreground truncate", className)}>
        {developer || publisher}
      </span>
    )
  }

  const showPublisher = publisher && publisher !== developer

  return (
    <div className={cn("space-y-1", className)}>
      {developer && (
        <div className="flex items-center gap-2 text-sm">
          <Building2 className="size-4 text-muted-foreground shrink-0" />
          <span className="text-muted-foreground">Developer:</span>
          <span className="text-foreground">{developer}</span>
        </div>
      )}
      {showPublisher && (
        <div className="flex items-center gap-2 text-sm">
          <Building2 className="size-4 text-muted-foreground shrink-0" />
          <span className="text-muted-foreground">Publisher:</span>
          <span className="text-foreground">{publisher}</span>
        </div>
      )}
    </div>
  )
}
