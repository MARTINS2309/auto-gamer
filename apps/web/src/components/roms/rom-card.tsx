import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Play, Gamepad2 } from "lucide-react"
import { useThumbnail } from "@/hooks"
import type { Rom } from "@/lib/schemas"

interface RomCardProps {
  rom: Rom
  onSelect: () => void
}

export function RomCard({ rom, onSelect }: RomCardProps) {
  const { url: thumbnailUrl, loading } = useThumbnail(rom.name, rom.system, "boxart")

  return (
    <Card
      className="cursor-pointer hover:shadow-lg transition-all hover:scale-[1.02] overflow-hidden group"
      onClick={onSelect}
    >
      {/* Thumbnail Area */}
      <div className="relative aspect-[4/3] bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-900 overflow-hidden">
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt={rom.name}
            className="w-full h-full object-cover transition-transform group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            {loading ? (
              <div className="w-8 h-8 border-2 border-slate-300 dark:border-slate-600 border-t-slate-500 dark:border-t-slate-400 rounded-full animate-spin" />
            ) : (
              <Gamepad2 className="w-12 h-12 text-slate-300 dark:text-slate-600" />
            )}
          </div>
        )}

        {/* System Badge Overlay */}
        <Badge
          variant="secondary"
          className="absolute top-2 right-2 bg-black/60 text-white border-0 text-xs"
        >
          {rom.system}
        </Badge>
      </div>

      {/* Content */}
      <CardContent className="p-3 space-y-2">
        <h3 className="font-medium text-sm truncate" title={rom.name}>
          {cleanDisplayName(rom.name)}
        </h3>
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            {rom.playable ? "Playable" : "Not configured"}
          </span>
          <Button
            size="sm"
            variant="default"
            className="h-7 text-xs"
            onClick={(e) => {
              e.stopPropagation()
              onSelect()
            }}
          >
            <Play className="size-3 mr-1" />
            Train
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Clean up ROM name for display.
 * Removes system suffix and version number.
 */
function cleanDisplayName(name: string): string {
  // Remove "-System-v0" suffix pattern
  return name.replace(/-[A-Za-z0-9]+-v\d+$/, "")
}
