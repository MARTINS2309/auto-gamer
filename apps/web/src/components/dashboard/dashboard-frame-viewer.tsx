import { useEffect, useRef } from "react"
import { Link } from "@tanstack/react-router"
import { MonitorOff } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AspectRatio } from "@/components/ui/aspect-ratio"
import { useRunMetrics } from "@/hooks"
import { initWebGL, destroyWebGL, type WebGLContext } from "@/lib/webgl"

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
  const { metrics, frame } = useRunMetrics(runId, true)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const ctxRef = useRef<WebGLContext | null>(null)

  // Init/destroy WebGL context
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = initWebGL(canvas)
    ctxRef.current = ctx
    return () => {
      if (ctx) destroyWebGL(ctx)
      ctxRef.current = null
    }
  }, [])

  // Render raw RGB frame
  useEffect(() => {
    const ctx = ctxRef.current
    const canvas = canvasRef.current
    if (!ctx || !canvas || !frame) return

    const { gl } = ctx
    if (canvas.width !== frame.width || canvas.height !== frame.height) {
      canvas.width = frame.width
      canvas.height = frame.height
      gl.viewport(0, 0, frame.width, frame.height)
    }

    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, frame.width, frame.height, 0, gl.RGB, gl.UNSIGNED_BYTE, frame.pixels)
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
  }, [frame])

  const hasFrame = frame !== null
  const bestReward = metrics?.best_reward ?? 0
  const fps = metrics?.fps ?? 0

  return (
    <Link to="/runs/$runId" params={{ runId }} className="block group">
      <Card className="overflow-hidden p-0 crt-inset" style={{ backgroundColor: "#000" }}>
        <AspectRatio ratio={4 / 3} className="relative">
          {/* Frame or waiting state */}
          {hasFrame ? (
            <canvas
              ref={canvasRef}
              className="absolute inset-0 w-full h-full object-contain"
              style={{ imageRendering: "pixelated" }}
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
