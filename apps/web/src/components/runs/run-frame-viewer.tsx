import { useEffect, useRef, useState, useCallback } from "react"
import { Monitor, MonitorOff, Brain, Play, Pause, Radio } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { GameRenderer, DVRController } from "@/lib/game-renderer"
import type { FrameBuffer } from "@/lib/api"
import type { RunMetrics } from "@/lib/schemas"

const MAX_VISIBLE_ENVS = 16

const SPEED_OPTIONS = [0.25, 0.5, 1, 2, 4] as const

// Cap drawing at 30fps to smooth WS bursts
const DISPLAY_INTERVAL_MS = 1000 / 30

const TRAINING_STATS: { key: string; label: string; format?: (v: number) => string }[] = [
  { key: "train/value_loss", label: "VALUE LOSS", format: v => v.toFixed(4) },
  { key: "train/policy_gradient_loss", label: "POLICY LOSS", format: v => v.toFixed(6) },
  { key: "train/entropy_loss", label: "ENTROPY", format: v => v.toFixed(4) },
  { key: "train/approx_kl", label: "KL DIV", format: v => v.toFixed(6) },
  { key: "train/explained_variance", label: "EXPL VAR", format: v => v.toFixed(4) },
  { key: "train/learning_rate", label: "LR", format: v => v.toExponential(2) },
  { key: "train/clip_fraction", label: "CLIP FRAC", format: v => v.toFixed(4) },
]

interface RunFrameViewerProps {
  frameBufferRef: React.RefObject<FrameBuffer>
  phase?: string | null
  metrics?: RunMetrics | null
  captureFps?: number
  className?: string
}

export function RunFrameViewer({ frameBufferRef, phase, metrics, captureFps = 15, className = "" }: RunFrameViewerProps) {
  const [envCount, setEnvCount] = useState(0)
  const [hasFrame, setHasFrame] = useState(false)
  const [frameDims, setFrameDims] = useState<[number, number]>([4, 3])
  const [speed, setSpeed] = useState(1)
  const [isPlaying, setIsPlaying] = useState(true)
  const [isLive, setIsLive] = useState(true)
  // Seek bar state — updated by polling interval, NOT per-rAF tick
  const [seekPosition, setSeekPosition] = useState(1) // 0..1
  const [lagSec, setLagSec] = useState(0)
  const [bufferSec, setBufferSec] = useState(0)
  const seekingRef = useRef(false)

  const containerRef = useRef<HTMLDivElement>(null)
  const rendererRef = useRef<GameRenderer | null>(null)
  const dvrRef = useRef(new DVRController())
  const rafRef = useRef(0)
  const lastTimeRef = useRef(0)
  const lastDrawRef = useRef(0)

  // Keep DVR baseFps in sync with prop
  useEffect(() => {
    dvrRef.current.baseFps = captureFps
  }, [captureFps])

  // GameRenderer lifecycle + rAF render loop
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const renderer = new GameRenderer(container)
    rendererRef.current = renderer

    function render(now: number) {
      const fb = frameBufferRef.current
      const dvr = dvrRef.current

      const dt = lastTimeRef.current > 0 ? Math.min((now - lastTimeRef.current) / 1000, 0.25) : 0
      lastTimeRef.current = now

      if (!fb || fb.width <= 0 || fb.height <= 0) {
        rafRef.current = requestAnimationFrame(render)
        return
      }

      // Advance DVR cursor every tick for smooth timing
      dvr.advance(dt, fb.ringGeneration, fb.ringSize)

      // Throttle GPU drawing to ~30fps
      if (now - lastDrawRef.current < DISPLAY_INTERVAL_MS) {
        rafRef.current = requestAnimationFrame(render)
        return
      }
      lastDrawRef.current = now

      const count = Math.min(fb.envCount || 1, MAX_VISIBLE_ENVS)
      renderer.setLayout(count, fb.width, fb.height)

      // Read from ring buffer (all envs stored per slot) or live envFrames
      const frameSize = fb.width * fb.height * 3
      const ringSlot = fb.ringSize > 0 ? fb.ring[dvr.ringIndex(fb.ringCapacity)] : undefined
      for (let i = 0; i < count; i++) {
        let frameData: Uint8Array | undefined
        if (ringSlot && ringSlot.length >= (i + 1) * frameSize) {
          frameData = ringSlot.subarray(i * frameSize, (i + 1) * frameSize)
        } else {
          frameData = fb.envFrames[i]
        }
        if (frameData) {
          renderer.updateTile(i, frameData, fb.width, fb.height)
        }
      }

      renderer.render()
      rafRef.current = requestAnimationFrame(render)
    }

    rafRef.current = requestAnimationFrame(render)

    return () => {
      cancelAnimationFrame(rafRef.current)
      lastTimeRef.current = 0
      lastDrawRef.current = 0
      renderer.dispose()
      rendererRef.current = null
    }
  }, [frameBufferRef])

  // Poll for structural changes + seek bar position (4x/sec)
  useEffect(() => {
    const id = setInterval(() => {
      const fb = frameBufferRef.current
      if (!fb) return
      if (fb.envCount !== envCount) setEnvCount(fb.envCount)
      if (!hasFrame && fb.generation > 0) setHasFrame(true)
      if (fb.width > 0 && fb.height > 0) setFrameDims([fb.width, fb.height])

      const dvr = dvrRef.current
      const fps = captureFps || 15
      setBufferSec(fb.ringSize / fps)
      setIsLive(dvr.isLive(fb.ringGeneration, fb.ringSize))
      // Only update seek position when user isn't dragging
      if (!seekingRef.current) {
        setSeekPosition(dvr.normalizedPosition(fb.ringGeneration, fb.ringSize))
        setLagSec(dvr.lagSeconds(fb.ringGeneration))
      }
    }, 250)
    return () => clearInterval(id)
  }, [frameBufferRef, envCount, hasFrame, captureFps])

  // ── Event handlers — directly mutate DVR, sync React state for UI ──

  const handleSpeedChange = useCallback((s: number) => {
    dvrRef.current.speed = s
    dvrRef.current.playing = true
    setSpeed(s)
    setIsPlaying(true)
  }, [])

  const handleTogglePlay = useCallback(() => {
    const next = !dvrRef.current.playing
    dvrRef.current.playing = next
    setIsPlaying(next)
  }, [])

  const handleGoLive = useCallback(() => {
    const fb = frameBufferRef.current
    if (!fb) return
    dvrRef.current.goLive(fb.ringGeneration)
    setSpeed(1)
    setIsPlaying(true)
  }, [frameBufferRef])

  const handleSeek = useCallback((pct: number) => {
    const fb = frameBufferRef.current
    if (!fb || fb.ringSize === 0) return
    const oldest = fb.ringGeneration - fb.ringSize
    const newest = fb.ringGeneration - 1
    const gen = oldest + pct * (newest - oldest)
    dvrRef.current.seekTo(gen)
    setIsPlaying(false)
    setSeekPosition(pct)
    setLagSec((newest - gen) / (captureFps || 15))
  }, [frameBufferRef, captureFps])

  const handleSeekStart = useCallback(() => {
    seekingRef.current = true
  }, [])

  const handleSeekEnd = useCallback(() => {
    seekingRef.current = false
  }, [])

  const visibleCount = Math.min(envCount || 1, MAX_VISIBLE_ENVS)
  const isTraining = phase === "training"
  const cols = visibleCount <= 1 ? 1 : visibleCount <= 2 ? 2 : visibleCount <= 4 ? 2 : visibleCount <= 6 ? 3 : 4
  const rows = Math.ceil(visibleCount / cols)

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Header */}
      <div className="flex items-center gap-2">
        {isTraining ? <Brain className="size-4" /> : <Monitor className="size-4" />}
        <span className="font-medium text-sm">
          {isTraining
            ? "Optimizing Weights"
            : `Training View${envCount > 1 ? ` (${envCount} envs)` : ""}`}
        </span>
        {isTraining ? (
          <Badge variant="secondary" className="text-xs animate-pulse">TRAINING</Badge>
        ) : isLive && hasFrame ? (
          <Badge variant="destructive" className="text-xs animate-pulse">LIVE</Badge>
        ) : hasFrame ? (
          <Badge variant="outline" className="text-xs">{speed}x</Badge>
        ) : null}
        {envCount > MAX_VISIBLE_ENVS && (
          <span className="text-xs text-muted-foreground">
            showing {MAX_VISIBLE_ENVS} of {envCount}
          </span>
        )}
      </div>

      {/* Canvas + overlays */}
      <div
        className="relative overflow-hidden crt-inset"
        style={{
          backgroundColor: "#000",
          maxWidth: visibleCount <= 2 ? "28rem" : visibleCount <= 4 ? "32rem" : "48rem",
          aspectRatio: `${cols * frameDims[0]} / ${rows * frameDims[1]}`,
        }}
      >
        <div ref={containerRef} className="absolute inset-0" />

        {visibleCount > 1 && (
          <div
            className="absolute inset-0 pointer-events-none grid"
            style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
          >
            {Array.from({ length: visibleCount }, (_, i) => (
              <div key={i} className="relative">
                <div className="absolute top-0.5 left-0.5 bg-foreground/60 text-background text-[9px] px-1 leading-tight">
                  {i}
                </div>
              </div>
            ))}
          </div>
        )}

        {!hasFrame && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground">
            <MonitorOff className="size-8 mb-2 opacity-50" />
            <p className="text-sm">Waiting for frames...</p>
          </div>
        )}
        {hasFrame && <ScanlineOverlay />}
        {isTraining && hasFrame && isLive && <TrainingOverlay metrics={metrics} />}
      </div>

      {/* Playback controls with seek bar */}
      {hasFrame && (
        <PlaybackControls
          speed={speed}
          isPlaying={isPlaying}
          isLive={isLive}
          seekPosition={seekPosition}
          lagSec={lagSec}
          bufferSec={bufferSec}
          onTogglePlay={handleTogglePlay}
          onSpeedChange={handleSpeedChange}
          onGoLive={handleGoLive}
          onSeek={handleSeek}
          onSeekStart={handleSeekStart}
          onSeekEnd={handleSeekEnd}
        />
      )}
    </div>
  )
}

// ── Playback Controls ─────────────────────────────────────────────────

function PlaybackControls({
  speed,
  isPlaying,
  isLive,
  seekPosition,
  lagSec,
  bufferSec,
  onTogglePlay,
  onSpeedChange,
  onGoLive,
  onSeek,
  onSeekStart,
  onSeekEnd,
}: {
  speed: number
  isPlaying: boolean
  isLive: boolean
  seekPosition: number
  lagSec: number
  bufferSec: number
  onTogglePlay: () => void
  onSpeedChange: (speed: number) => void
  onGoLive: () => void
  onSeek: (pct: number) => void
  onSeekStart: () => void
  onSeekEnd: () => void
}) {
  return (
    <div className="space-y-1.5">
      {/* Seek bar */}
      <SeekBar
        position={seekPosition}
        isLive={isLive}
        onSeek={onSeek}
        onSeekStart={onSeekStart}
        onSeekEnd={onSeekEnd}
      />

      {/* Transport controls row */}
      <div className="flex items-center gap-2 text-xs">
        {/* Time offset from live */}
        <span className="tabular-nums text-muted-foreground font-mono w-14 text-right shrink-0">
          {lagSec < 0.5 ? "LIVE" : `-${lagSec.toFixed(1)}s`}
        </span>

        {/* Play / Pause */}
        <button onClick={onTogglePlay} className="p-1 hover:bg-muted transition-colors">
          {isPlaying ? <Pause className="size-3.5" /> : <Play className="size-3.5" />}
        </button>

        {/* Speed chips */}
        <div className="flex items-center gap-px">
          {SPEED_OPTIONS.map(s => (
            <button
              key={s}
              onClick={() => onSpeedChange(s)}
              className={cn(
                "px-1.5 py-0.5 transition-colors font-mono",
                speed === s
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted text-muted-foreground"
              )}
            >
              {s}x
            </button>
          ))}
        </div>

        {/* Go Live */}
        <button
          onClick={onGoLive}
          className={cn(
            "px-2 py-1 flex items-center gap-1 transition-colors",
            isLive
              ? "bg-destructive text-destructive-foreground"
              : "hover:bg-muted text-muted-foreground"
          )}
        >
          <Radio className="size-3" />
          LIVE
        </button>

        {/* Buffer depth */}
        {bufferSec > 0 && (
          <span className="text-muted-foreground ml-auto tabular-nums font-mono">
            {bufferSec.toFixed(0)}s
          </span>
        )}
      </div>
    </div>
  )
}

// ── Seek Bar ──────────────────────────────────────────────────────────

function SeekBar({
  position,
  isLive,
  onSeek,
  onSeekStart,
  onSeekEnd,
}: {
  position: number
  isLive: boolean
  onSeek: (pct: number) => void
  onSeekStart: () => void
  onSeekEnd: () => void
}) {
  const barRef = useRef<HTMLDivElement>(null)

  const pctFromEvent = (e: React.PointerEvent) => {
    const bar = barRef.current
    if (!bar) return 0
    const rect = bar.getBoundingClientRect()
    return Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
  }

  return (
    <div
      ref={barRef}
      className="relative w-full h-3 bg-muted cursor-pointer group"
      onPointerDown={(e) => {
        (e.target as HTMLElement).setPointerCapture(e.pointerId)
        onSeekStart()
        onSeek(pctFromEvent(e))
      }}
      onPointerMove={(e) => {
        if (e.buttons > 0) onSeek(pctFromEvent(e))
      }}
      onPointerUp={() => onSeekEnd()}
    >
      {/* Buffer fill (behind cursor) */}
      <div
        className="absolute inset-y-0 left-0 bg-primary/20 transition-[width] duration-200"
        style={{ width: `${position * 100}%` }}
      />
      {/* Cursor thumb */}
      <div
        className={cn(
          "absolute top-0 bottom-0 w-0.5 -translate-x-1/2 transition-[left] duration-200",
          isLive ? "bg-destructive" : "bg-primary"
        )}
        style={{ left: `${position * 100}%` }}
      />
      {/* Live edge marker (rightmost pixel) */}
      <div className="absolute right-0 top-0 bottom-0 w-px bg-destructive/50" />
    </div>
  )
}

// ── Training Overlay ──────────────────────────────────────────────────

function TrainingOverlay({ metrics }: { metrics?: RunMetrics | null }) {
  const details = metrics?.details

  const stats = TRAINING_STATS
    .map(({ key, label, format }) => {
      const v = details?.[key]
      if (v === undefined || v === null) return null
      const num = typeof v === "number" ? v : parseFloat(v)
      if (isNaN(num)) return null
      return { label, value: format ? format(num) : num.toFixed(4) }
    })
    .filter(Boolean) as { label: string; value: string }[]

  const step = metrics?.step
  const loss = metrics?.loss

  return (
    <div className="absolute inset-0 flex items-center justify-center">
      <div className="absolute inset-0 bg-background/80" />
      <div className="relative z-10 font-mono text-xs leading-relaxed p-4 space-y-0.5">
        <div className="text-chart-3 font-bold mb-1.5 flex items-center gap-1.5 text-sm">
          <span className="inline-block size-2 bg-chart-3 animate-pulse" />
          GRADIENT DESCENT
        </div>
        {step != null && (
          <div className="text-muted-foreground">
            STEP <span className="text-foreground font-semibold">{step.toLocaleString()}</span>
          </div>
        )}
        {loss != null && (
          <div className="text-muted-foreground">
            LOSS <span className="text-chart-3 font-semibold">{loss.toFixed(4)}</span>
          </div>
        )}
        {stats.length > 0 && <div className="border-t border-muted-foreground/30 my-1.5" />}
        {stats.map(({ label, value }) => (
          <div key={label} className="text-muted-foreground flex justify-between gap-4">
            <span>{label}</span>
            <span className="text-foreground tabular-nums font-medium">{value}</span>
          </div>
        ))}
        {stats.length === 0 && !loss && (
          <div className="text-muted-foreground animate-pulse">Computing gradients...</div>
        )}
      </div>
    </div>
  )
}

// ── Scanline Overlay ──────────────────────────────────────────────────

function ScanlineOverlay() {
  return (
    <div
      className="absolute inset-0 pointer-events-none opacity-10"
      style={{
        background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.3) 2px, rgba(0,0,0,0.3) 4px)",
      }}
    />
  )
}
