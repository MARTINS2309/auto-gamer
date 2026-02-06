import { useState, useCallback, useRef, useEffect } from "react"
import { Monitor, MonitorOff, Grid3X3 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { initWebGL, destroyWebGL, renderBlobFrame, type WebGLContext } from "@/lib/webgl"
import type { FrameInfo } from "@/lib/api"

interface TrainingFrameViewerProps {
  gridFrame: FrameInfo | null
  focusedFrame: FrameInfo | null
  focusedEnv: number
  onFocusEnv: (idx: number) => void
  className?: string
  onFrameFreqChange?: (freq: number) => void
}

export function TrainingFrameViewer({
  gridFrame,
  focusedFrame,
  focusedEnv,
  onFocusEnv,
  className = "",
  onFrameFreqChange,
}: TrainingFrameViewerProps) {
  const [sliderValue, setSliderValue] = useState(30)

  // Main canvas (shows focused env or grid)
  const mainCanvasRef = useRef<HTMLCanvasElement>(null)
  const mainCtxRef = useRef<WebGLContext | null>(null)

  // Mini grid canvas (only visible in focus mode)
  const miniCanvasRef = useRef<HTMLCanvasElement>(null)
  const miniCtxRef = useRef<WebGLContext | null>(null)

  const nEnvs = gridFrame?.nEnvs ?? focusedFrame?.nEnvs ?? 0
  const isFocusMode = focusedEnv >= 0
  const hasAnyFrame = gridFrame !== null || focusedFrame !== null

  // Init/destroy main WebGL context
  useEffect(() => {
    const canvas = mainCanvasRef.current
    if (!canvas) return
    const ctx = initWebGL(canvas)
    mainCtxRef.current = ctx
    return () => {
      if (ctx) destroyWebGL(ctx)
      mainCtxRef.current = null
    }
  }, [])

  // Init/destroy mini WebGL context
  useEffect(() => {
    const canvas = miniCanvasRef.current
    if (!canvas) return
    const ctx = initWebGL(canvas)
    miniCtxRef.current = ctx
    return () => {
      if (ctx) destroyWebGL(ctx)
      miniCtxRef.current = null
    }
  }, [])

  // Render main canvas: focused env when in focus mode, grid otherwise
  useEffect(() => {
    const ctx = mainCtxRef.current
    const canvas = mainCanvasRef.current
    if (!ctx || !canvas) return

    const frame = isFocusMode ? (focusedFrame ?? gridFrame) : gridFrame
    if (!frame) return
    renderBlobFrame(ctx, canvas, frame.blob)
  }, [isFocusMode, focusedFrame, gridFrame])

  // Render mini grid canvas (only when in focus mode)
  useEffect(() => {
    if (!isFocusMode) return
    const ctx = miniCtxRef.current
    const canvas = miniCanvasRef.current
    if (!ctx || !canvas || !gridFrame) return
    renderBlobFrame(ctx, canvas, gridFrame.blob)
  }, [isFocusMode, gridFrame])

  // Click handler for grid canvas — map click position to env index
  const handleGridClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (nEnvs <= 1) return
      const canvas = e.currentTarget
      const rect = canvas.getBoundingClientRect()
      const x = (e.clientX - rect.left) / rect.width
      const y = (e.clientY - rect.top) / rect.height

      const cols = Math.ceil(Math.sqrt(nEnvs))
      const rows = Math.ceil(nEnvs / cols)
      const col = Math.floor(x * cols)
      const row = Math.floor(y * rows)
      const envIdx = row * cols + col

      if (envIdx >= 0 && envIdx < nEnvs) {
        onFocusEnv(envIdx)
      }
    },
    [nEnvs, onFocusEnv]
  )

  const handleSliderChange = useCallback(
    (values: number[]) => {
      const freq = values[0]
      setSliderValue(freq)
      onFrameFreqChange?.(freq)
    },
    [onFrameFreqChange]
  )

  const estimatedFps = sliderValue > 0 ? Math.round(2000 / sliderValue) : 0
  const fpsLabel = estimatedFps > 60 ? "max" : `~${estimatedFps}`

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Monitor className="size-4" />
            Training View
          </CardTitle>
          <div className="flex items-center gap-2">
            {nEnvs > 1 && (
              <Badge variant="secondary" className="text-xs gap-1">
                <Grid3X3 className="size-3" />
                {nEnvs} envs
              </Badge>
            )}
            {isFocusMode && (
              <Badge variant="outline" className="text-xs">
                ENV #{focusedEnv}
              </Badge>
            )}
            {hasAnyFrame && (
              <Badge variant="outline" className="text-xs">
                LIVE
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Main canvas */}
        <div
          className="relative overflow-hidden crt-inset aspect-4/3"
          style={{ backgroundColor: "#000" }}
        >
          <canvas
            ref={mainCanvasRef}
            onClick={!isFocusMode && nEnvs > 1 ? handleGridClick : undefined}
            className="w-full h-full object-contain"
            style={{ cursor: !isFocusMode && nEnvs > 1 ? "pointer" : "default" }}
          />

          {!hasAnyFrame && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground">
              <MonitorOff className="size-8 mb-2 opacity-50" />
              <p className="text-sm">Waiting for frames...</p>
            </div>
          )}

          {/* Scanline overlay */}
          {hasAnyFrame && (
            <div
              className="absolute inset-0 pointer-events-none opacity-10"
              style={{
                background:
                  "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.3) 2px, rgba(0,0,0,0.3) 4px)",
              }}
            />
          )}
        </div>

        {/* Env selector buttons — only in focus mode with multiple envs */}
        {isFocusMode && nEnvs > 1 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {Array.from({ length: nEnvs }, (_, i) => (
              <Button
                key={i}
                size="sm"
                variant={i === focusedEnv ? "default" : "outline"}
                className="h-6 px-2 text-xs"
                onClick={() => onFocusEnv(i === focusedEnv ? -1 : i)}
              >
                {i}
              </Button>
            ))}
            <Button
              size="sm"
              variant="outline"
              className="h-6 px-2 text-xs"
              onClick={() => onFocusEnv(-1)}
            >
              <Grid3X3 className="size-3 mr-1" />
              Grid
            </Button>
          </div>
        )}

        {/* Mini grid — only in focus mode */}
        {isFocusMode && nEnvs > 1 && (
          <div
            className="mt-2 overflow-hidden crt-inset"
            style={{ backgroundColor: "#000", height: 150 }}
          >
            <canvas
              ref={miniCanvasRef}
              onClick={handleGridClick}
              className="w-full h-full object-contain"
              style={{ cursor: "pointer" }}
            />
          </div>
        )}

        {/* Frame rate control */}
        {onFrameFreqChange && (
          <div className="mt-3 space-y-1">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Frame rate</span>
              <span>
                {fpsLabel} fps (every {sliderValue} steps)
              </span>
            </div>
            <Slider
              value={[sliderValue]}
              onValueChange={handleSliderChange}
              min={1}
              max={120}
              step={1}
            />
            <div className="flex justify-between text-[10px] text-muted-foreground/60">
              <span>faster</span>
              <span>slower</span>
            </div>
          </div>
        )}

        {(gridFrame?.timestamp || focusedFrame?.timestamp) && (
          <p className="text-xs text-muted-foreground mt-2 text-right">
            Last update:{" "}
            {new Date(
              ((focusedFrame?.timestamp ?? gridFrame?.timestamp) as number) * 1000
            ).toLocaleTimeString()}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
