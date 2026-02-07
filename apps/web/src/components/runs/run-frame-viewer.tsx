import { useEffect, useRef } from "react"
import { Monitor, MonitorOff } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { initWebGL, destroyWebGL, type WebGLContext } from "@/lib/webgl"
import type { FrameInfo } from "@/lib/api"

interface RunFrameViewerProps {
  frame: FrameInfo | null
  className?: string
}

export function RunFrameViewer({ frame, className = "" }: RunFrameViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const ctxRef = useRef<WebGLContext | null>(null)
  const hasFrame = frame !== null

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

  // Render raw RGB frame directly via texImage2D
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

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Header */}
      <div className="flex items-center gap-2">
        <Monitor className="size-4" />
        <span className="font-medium text-sm">Training View</span>
        {hasFrame && (
          <Badge variant="destructive" className="text-xs animate-pulse">
            LIVE
          </Badge>
        )}
      </div>

      {/* WebGL Canvas */}
      <div className="relative overflow-hidden crt-inset aspect-4/3 max-w-md" style={{ backgroundColor: "#000" }}>
        <canvas
          ref={canvasRef}
          className="w-full h-full"
          style={{ imageRendering: "pixelated" }}
        />

        {!hasFrame && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground">
            <MonitorOff className="size-8 mb-2 opacity-50" />
            <p className="text-sm">Waiting for frames...</p>
          </div>
        )}

        {hasFrame && (
          <div
            className="absolute inset-0 pointer-events-none opacity-10"
            style={{
              background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.3) 2px, rgba(0,0,0,0.3) 4px)",
            }}
          />
        )}
      </div>
    </div>
  )
}
