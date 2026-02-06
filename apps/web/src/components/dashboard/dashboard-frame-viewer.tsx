import { useEffect, useRef } from "react"
import { Link } from "@tanstack/react-router"
import { MonitorOff } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AspectRatio } from "@/components/ui/aspect-ratio"
import { useRunMetrics } from "@/hooks"

interface DashboardFrameViewerProps {
  runId: string
  gameName: string
  algorithm: string
  thumbnailUrl?: string | null
}

export function DashboardFrameViewer({
  runId,
  gameName,
  algorithm,
  thumbnailUrl,
}: DashboardFrameViewerProps) {
  const { metrics, gridFrame, focusedFrame, setFrameFreq } = useRunMetrics(runId, true)
  const imgRef = useRef<HTMLImageElement>(null)
  const prevUrlRef = useRef<string | null>(null)

  // Set a moderate frame frequency for the dashboard
  useEffect(() => {
    setFrameFreq(10)
  }, [setFrameFreq])

  // Update img src directly via ref (avoids setState-in-effect lint rule)
  const frame = gridFrame ?? focusedFrame
  const blob = frame?.blob ?? null
  useEffect(() => {
    if (!blob || !imgRef.current) return
    if (prevUrlRef.current) URL.revokeObjectURL(prevUrlRef.current)
    const url = URL.createObjectURL(blob)
    prevUrlRef.current = url
    imgRef.current.src = url
    return () => {
      if (prevUrlRef.current) {
        URL.revokeObjectURL(prevUrlRef.current)
        prevUrlRef.current = null
      }
    }
  }, [blob])

  const hasFrame = frame !== null
  const bestReward = metrics?.best_reward ?? 0
  const fps = metrics?.fps ?? 0

  return (
    <Link to="/runs/$runId" params={{ runId }} className="block group">
      <Card className="overflow-hidden p-0 crt-inset" style={{ backgroundColor: "#000" }}>
        <AspectRatio ratio={4 / 3} className="relative">
          {/* Frame or waiting state */}
          {hasFrame ? (
            <img
              ref={imgRef}
              alt={`${gameName} training`}
              className="absolute inset-0 w-full h-full object-contain"
            />
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground">
              <MonitorOff className="size-8 mb-2 opacity-50" />
              <p className="text-sm">Waiting for frames...</p>
            </div>
          )}

          {/* CRT scanline overlay */}
          {hasFrame && (
            <div
              className="absolute inset-0 pointer-events-none opacity-10"
              style={{
                background:
                  "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.3) 2px, rgba(0,0,0,0.3) 4px)",
              }}
            />
          )}

          {/* Top-left: game thumbnail */}
          {thumbnailUrl && (
            <img
              src={thumbnailUrl}
              alt={gameName}
              className="absolute top-2 left-2 w-6 h-8 object-cover shadow-md opacity-80 group-hover:opacity-100 transition-opacity"
            />
          )}

          {/* Top-right: reward badge */}
          {metrics && (
            <Badge
              variant="outline"
              className="absolute top-2 right-2 bg-background/60 text-primary animate-live text-xs"
            >
              {bestReward.toFixed(1)}
            </Badge>
          )}

          {/* Bottom: info bar */}
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-background/80 to-transparent p-3 pt-8">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-sm font-semibold text-primary-foreground truncate">
                  {gameName}
                </span>
                <Badge variant="secondary" className="text-xs shrink-0">
                  {algorithm}
                </Badge>
              </div>
              {fps > 0 && (
                <span className="text-xs text-muted-foreground shrink-0">
                  {fps.toFixed(0)} fps
                </span>
              )}
            </div>
          </div>
        </AspectRatio>
      </Card>
    </Link>
  )
}
