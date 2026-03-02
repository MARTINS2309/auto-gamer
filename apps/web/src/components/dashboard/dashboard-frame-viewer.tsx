import { useEffect, useRef, useState } from "react"
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
  const { metrics, frameBufferRef } = useRunMetrics(runId, true)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const ctxRef = useRef<WebGLContext | null>(null)
  const lastGenRef = useRef(0)
  const rafRef = useRef(0)
  const [hasFrame, setHasFrame] = useState(false)
  const hasFrameRef = useRef(false)

  // Init WebGL + rAF render loop — access frameBufferRef.current only inside rAF
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = initWebGL(canvas)
    ctxRef.current = ctx

    function render() {
      const fb = frameBufferRef.current
      if (!fb) { rafRef.current = requestAnimationFrame(render); return }
      const gen = fb.generation
      if (gen !== lastGenRef.current && fb.envFrames[0]) {
        lastGenRef.current = gen
        if (!hasFrameRef.current) { hasFrameRef.current = true; setHasFrame(true) }
        const glCtx = ctxRef.current
        if (glCtx && canvas) {
          const { gl } = glCtx
          const w = fb.width
          const h = fb.height
          if (w > 0 && h > 0) {
            if (canvas.width !== w || canvas.height !== h) {
              canvas.width = w
              canvas.height = h
              gl.viewport(0, 0, w, h)
            }
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, w, h, 0, gl.RGB, gl.UNSIGNED_BYTE, fb.envFrames[0])
            gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
          }
        }
      }
      rafRef.current = requestAnimationFrame(render)
    }

    rafRef.current = requestAnimationFrame(render)

    return () => {
      cancelAnimationFrame(rafRef.current)
      if (ctx) destroyWebGL(ctx)
      ctxRef.current = null
    }
  }, [frameBufferRef])

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
