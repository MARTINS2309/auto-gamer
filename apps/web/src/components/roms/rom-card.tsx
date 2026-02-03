import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Play, Gamepad2 } from "lucide-react"
import { useThumbnail } from "@/hooks"
import {
  RatingDisplay,
  GenreBadges,
  ReleaseInfo,
  CompanyInfo,
} from "@/components/metadata"
import type { Rom, GameMetadata } from "@/lib/schemas"

interface RomCardProps {
  rom: Rom
  metadata?: GameMetadata
  onSelect: () => void
}

export function RomCard({ rom, metadata, onSelect }: RomCardProps) {
  // Use rom.id for thumbnail lookup (consistent with metadata correlation)
  const { url, loading, failed, onError, onLoad } = useThumbnail(rom.id, rom.system, "boxart")

  return (
    <Card
      className="cursor-pointer hover:shadow-xl transition-all duration-200 hover:scale-[1.02] hover:-translate-y-0.5 overflow-hidden group border-0 shadow-md"
      onClick={onSelect}
    >
      {/* Thumbnail Area */}
      <div className="relative aspect-4/3 bg-linear-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-900 overflow-hidden">
        {url && !failed && (
          <img
            src={url}
            alt={metadata?.name || rom.name}
            className="w-full h-full object-contain transition-transform duration-300 group-hover:scale-110"
            loading="lazy"
            onError={onError}
            onLoad={onLoad}
          />
        )}

        {/* Fallback overlay - show when no URL, failed, or still loading */}
        {(!url || failed || loading) && (
          <div className="absolute inset-0 flex items-center justify-center">
            {loading && url ? (
              <div className="w-8 h-8 border-2 border-slate-300 dark:border-slate-600 border-t-slate-500 dark:border-t-slate-400 rounded-full animate-spin" />
            ) : (
              <Gamepad2 className="w-16 h-16 text-slate-300 dark:text-slate-600" />
            )}
          </div>
        )}

        {/* Gradient overlay for better text readability */}
        <div className="absolute inset-0 bg-linear-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

        {/* System Badge Overlay */}
        <Badge
          variant="secondary"
          className="absolute top-2 right-2 bg-black/70 text-white border-0 text-xs backdrop-blur-sm"
        >
          {rom.system}
        </Badge>

        {/* Rating Badge (if available) */}
        {metadata?.rating && (
          <Badge
            variant="secondary"
            className="absolute top-2 left-2 bg-black/70 border-0 backdrop-blur-sm"
          >
            <RatingDisplay
              rating={metadata.rating}
              ratingCount={metadata.rating_count}
              variant="compact"
            />
          </Badge>
        )}

        {/* Hover Play Button */}
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            size="lg"
            className="rounded-full size-14 p-0 shadow-lg"
            onClick={(e) => {
              e.stopPropagation()
              onSelect()
            }}
          >
            <Play className="size-6 ml-0.5" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <CardContent className="p-3 space-y-1.5">
        <h3
          className="font-semibold text-sm leading-tight line-clamp-2 min-h-10"
          title={metadata?.name || rom.name}
        >
          {metadata?.name || cleanDisplayName(rom.name)}
        </h3>

        {/* Meta row: genre + year */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 min-w-0">
            <GenreBadges
              genres={metadata?.genres ?? []}
              variant="compact"
              maxDisplay={1}
            />
            <ReleaseInfo
              releaseDate={metadata?.release_date}
              variant="compact"
            />
          </div>
        </div>

        {/* Developer */}
        <CompanyInfo
          developer={metadata?.developer}
          variant="compact"
        />
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
