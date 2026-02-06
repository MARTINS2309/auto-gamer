import { useEffect, useRef, useState } from "react"
import { Monitor, MonitorOff, Square } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { initWebGL, destroyWebGL } from "@/lib/webgl"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"
const WS_BASE = API_BASE.replace(/^http/, "ws")

interface PlayFrameViewerProps {
  sessionId: string
  gameName: string
  onStop: () => void
  isStopping?: boolean
}

export function PlayFrameViewer({
  sessionId,
  gameName,
  onStop,
  isStopping,
}: PlayFrameViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [status, setStatus] = useState<"connecting" | "live" | "ended">("connecting")

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = initWebGL(canvas)
    if (!ctx) return
    const { gl } = ctx

    let hasFrame = false

    const ws = new WebSocket(`${WS_BASE}/ws/play/frames/${sessionId}`)
    ws.binaryType = "arraybuffer"

    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        // Text message — JSON control (status updates)
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === "status" && msg.status === "ended") {
            setStatus("ended")
          }
        } catch { /* ignore */ }
        return
      }

      // Binary message — raw RGB pixels with 4-byte header [u16 LE width][u16 LE height]
      const buf = event.data as ArrayBuffer
      if (buf.byteLength < 4) return

      const view = new DataView(buf)
      const w = view.getUint16(0, true)
      const h = view.getUint16(2, true)
      const expectedSize = 4 + w * h * 3
      if (buf.byteLength < expectedSize) return

      const pixels = new Uint8Array(buf, 4, w * h * 3)

      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w
        canvas.height = h
        gl.viewport(0, 0, w, h)
      }

      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, w, h, 0, gl.RGB, gl.UNSIGNED_BYTE, pixels)
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)

      if (!hasFrame) {
        hasFrame = true
        setStatus("live")
      }
    }

    ws.onclose = () => {
      if (!hasFrame) setStatus("ended")
    }

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close()
      }
      destroyWebGL(ctx)
    }
  }, [sessionId])

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Monitor className="size-4" />
          <span className="font-medium text-sm truncate max-w-[200px]">{gameName}</span>
          {status === "live" && (
            <Badge variant="destructive" className="text-xs animate-pulse">
              LIVE
            </Badge>
          )}
          {status === "ended" && (
            <Badge variant="secondary" className="text-xs">
              ENDED
            </Badge>
          )}
        </div>
        {status !== "ended" && (
          <Button
            variant="destructive"
            size="sm"
            onClick={onStop}
            disabled={isStopping}
          >
            <Square className="size-3 mr-1" />
            {isStopping ? "Stopping..." : "Stop"}
          </Button>
        )}
      </div>

      {/* WebGL Canvas */}
      <div className="relative overflow-hidden crt-inset aspect-4/3" style={{ backgroundColor: "#000" }}>
        <canvas
          ref={canvasRef}
          className="w-full h-full"
          style={{ imageRendering: "pixelated" }}
        />

        {status !== "live" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground">
            <MonitorOff className="size-8 mb-2 opacity-50" />
            <p className="text-sm">
              {status === "ended" ? "Session ended" : "Connecting..."}
            </p>
          </div>
        )}

        {status === "live" && (
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
