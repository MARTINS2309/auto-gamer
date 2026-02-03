import { useState } from "react"
import { Image, X } from "lucide-react"
import { Dialog, DialogContent, DialogClose } from "@/components/ui/dialog"
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselPrevious,
  CarouselNext,
} from "@/components/ui/carousel"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface ScreenshotGalleryProps {
  screenshots: string[]
  gameName: string
  variant?: "compact" | "full"
  maxThumbnails?: number
  className?: string
}

export function ScreenshotGallery({
  screenshots,
  gameName,
  variant = "full",
  maxThumbnails = 4,
  className,
}: ScreenshotGalleryProps) {
  const [lightboxOpen, setLightboxOpen] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)

  if (!screenshots || screenshots.length === 0) return null

  const displayScreenshots = screenshots.slice(0, maxThumbnails)
  const remainingCount = screenshots.length - maxThumbnails

  const openLightbox = (index: number) => {
    setCurrentIndex(index)
    setLightboxOpen(true)
  }

  return (
    <>
      <div className={cn("space-y-2", className)}>
        <h4 className="text-sm font-semibold flex items-center gap-2">
          <Image className="size-4" />
          Screenshots
        </h4>
        <div className="grid grid-cols-2 gap-2">
          {displayScreenshots.map((url, i) => (
            <button
              key={i}
              type="button"
              onClick={() => openLightbox(i)}
              className="relative aspect-video rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-800 cursor-pointer group"
            >
              <img
                src={url}
                alt={`${gameName} screenshot ${i + 1}`}
                className="w-full h-full object-cover transition-transform group-hover:scale-105"
                loading="lazy"
              />
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
            </button>
          ))}
        </div>
        {remainingCount > 0 && (
          <button
            type="button"
            onClick={() => openLightbox(maxThumbnails)}
            className="text-xs text-primary hover:underline"
          >
            +{remainingCount} more screenshots
          </button>
        )}
      </div>

      <Dialog open={lightboxOpen} onOpenChange={setLightboxOpen}>
        <DialogContent
          className="max-w-4xl w-full p-0 bg-black/95 border-none"
          showCloseButton={false}
        >
          <DialogClose asChild>
            <Button
              variant="ghost"
              size="icon"
              className="absolute top-4 right-4 z-50 text-white hover:bg-white/10"
            >
              <X className="size-6" />
            </Button>
          </DialogClose>

          <Carousel
            className="w-full"
            opts={{ startIndex: currentIndex, loop: true }}
          >
            <CarouselContent>
              {screenshots.map((url, i) => (
                <CarouselItem key={i}>
                  <div className="flex items-center justify-center p-4">
                    <img
                      src={url}
                      alt={`${gameName} screenshot ${i + 1}`}
                      className="max-h-[80vh] w-auto object-contain"
                    />
                  </div>
                </CarouselItem>
              ))}
            </CarouselContent>
            <CarouselPrevious className="left-4" />
            <CarouselNext className="right-4" />
          </Carousel>

          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-white/70 text-sm">
            {currentIndex + 1} / {screenshots.length}
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
