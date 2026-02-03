import { useState } from "react"
import { cn } from "@/lib/utils"

interface ExpandableTextProps {
  text: string
  title?: string
  maxLines?: number
  className?: string
}

export function ExpandableText({
  text,
  title,
  maxLines = 3,
  className,
}: ExpandableTextProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!text) return null

  const lineClampClass = `line-clamp-${maxLines}`

  return (
    <div className={cn("space-y-2", className)}>
      {title && <h4 className="text-sm font-semibold">{title}</h4>}
      <div className="relative">
        <p
          className={cn(
            "text-sm text-muted-foreground leading-relaxed",
            !isExpanded && lineClampClass
          )}
        >
          {text}
        </p>
        {!isExpanded && (
          <div className="absolute bottom-0 left-0 right-0 h-6 bg-gradient-to-t from-background to-transparent pointer-events-none" />
        )}
      </div>
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="text-xs text-primary hover:underline cursor-pointer"
      >
        {isExpanded ? "Show less" : "Read more"}
      </button>
    </div>
  )
}
