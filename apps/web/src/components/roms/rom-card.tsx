import { useState, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AspectRatio } from "@/components/ui/aspect-ratio"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { Gamepad2, Star } from "lucide-react"
import { getConsoleIconUrl, getSystemDisplayName } from "@/lib/console-icons"
import type { RomListItem } from "@/lib/schemas"

interface RomCardProps {
  rom: RomListItem
  onSelect: () => void
}

export function RomCard({ rom, onSelect }: RomCardProps) {
  const [imageLoading, setImageLoading] = useState(true)
  const [imageFailed, setImageFailed] = useState(false)

  const thumbnailUrl = rom.thumbnail_url
  const rating = rom.rating ? Math.round(rom.rating) : null
  const showFallback = !thumbnailUrl || imageFailed || imageLoading

  // Build meta items from available data, prioritized
  const metaItems = useMemo(() => {
    const items: string[] = []

    // Year is high value
    const year = rom.release_date?.split("-")[0]
    if (year) items.push(year)

    // Primary genre
    if (rom.genres?.[0]) items.push(rom.genres[0])

    // Developer as fallback
    if (rom.developer && items.length < 2) items.push(rom.developer)

    // Second genre if we still have room
    if (rom.genres?.[1] && items.length < 3) items.push(rom.genres[1])

    return items
  }, [rom.release_date, rom.genres, rom.developer])

  return (
    <Card
      className="cursor-pointer hover:shadow-lg transition-all duration-200 hover:-translate-y-1 overflow-hidden group p-0 gap-0"
      onClick={onSelect}
    >
      <CardHeader className="relative p-0">
        <AspectRatio ratio={3 / 4} className="overflow-hidden">
          {/* Background */}
          <Skeleton className="absolute inset-0 animate-none" />

          {/* Image */}
          {thumbnailUrl && !imageFailed && (
            <img
              src={thumbnailUrl}
              alt={rom.display_name}
              className="absolute inset-0 w-full h-full object-contain p-3 transition-transform duration-300 group-hover:scale-105"
              loading="lazy"
              onError={() => {
                setImageFailed(true)
                setImageLoading(false)
              }}
              onLoad={() => setImageLoading(false)}
            />
          )}

          {/* Loading/Fallback overlay */}
          {showFallback && (
            <Skeleton className="absolute inset-0 flex items-center justify-center animate-none">
              {imageLoading && thumbnailUrl ? (
                <Spinner className="size-8" />
              ) : (
                <Gamepad2 className="size-12 text-muted-foreground/40" />
              )}
            </Skeleton>
          )}

          {/* Badges */}
          <CardContent className="absolute top-0 left-0 right-0 flex justify-between items-start p-2">
            {rating && (
              <Badge variant="secondary" className="backdrop-blur-sm text-xs">
                <Star className="size-3 fill-primary text-primary" />
                {rating}
              </Badge>
            )}
            <Badge
              variant="secondary"
              className="backdrop-blur-sm text-xs ml-auto"
              title={getSystemDisplayName(rom.system)}
            >
              {getConsoleIconUrl(rom.system) && (
                <img
                  src={getConsoleIconUrl(rom.system)}
                  alt={rom.system}
                  className="size-4 dark:invert"
                />
              )}
              {getSystemDisplayName(rom.system)}
            </Badge>
          </CardContent>
        </AspectRatio>
      </CardHeader>

      <CardContent className="p-3 space-y-1">
        <CardTitle
          className="text-xl leading-tight line-clamp-2 min-h-12"
          title={rom.display_name}
        >
          {rom.display_name}
        </CardTitle>

        {metaItems.length > 0 && (
          <CardDescription className="text-xs truncate">
            {metaItems.join(" · ")}
          </CardDescription>
        )}
      </CardContent>
    </Card>
  )
}
