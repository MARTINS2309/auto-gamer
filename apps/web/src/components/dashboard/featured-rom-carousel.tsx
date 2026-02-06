import { useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselPrevious,
  CarouselNext,
} from "@/components/ui/carousel"
import { RomCard } from "@/components/roms/rom-card"
import { Gamepad2 } from "lucide-react"
import type { RomListItem } from "@/lib/schemas"

interface FeaturedRomCarouselProps {
  roms: RomListItem[]
  onSelectRom: (romId: string) => void
}

export function FeaturedRomCarousel({
  roms,
  onSelectRom,
}: FeaturedRomCarouselProps) {
  const featured = useMemo(() => {
    return roms
      .filter((r) => r.status === "trainable")
      .sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0))
      .slice(0, 12)
  }, [roms])

  if (featured.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Gamepad2 className="size-4" />
            Featured Games
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-4">
            No trainable games found. Import ROMs to get started.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Gamepad2 className="size-4" />
          Featured Games
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Carousel opts={{ align: "start" }}>
          <CarouselContent className="-ml-4">
            {featured.map((rom) => (
              <CarouselItem
                key={rom.id}
                className="pl-4 basis-1/2 md:basis-1/3 lg:basis-1/4"
              >
                <RomCard
                  rom={rom}
                  onSelect={() => onSelectRom(rom.id)}
                />
              </CarouselItem>
            ))}
          </CarouselContent>
          <CarouselPrevious />
          <CarouselNext />
        </Carousel>
      </CardContent>
    </Card>
  )
}
