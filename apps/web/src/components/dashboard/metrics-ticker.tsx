import { useMemo } from "react"
import type { Run, RunMetrics } from "@/lib/schemas"
import { useRoms } from "@/hooks"

interface MetricsTickerProps {
  runs: Run[]
  metricsMap: Map<string, RunMetrics>
}

export function MetricsTicker({ runs, metricsMap }: MetricsTickerProps) {
  const { data: roms = [] } = useRoms()

  const tickerEntries = useMemo(() => {
    return runs.map((run) => {
      const rom = roms.find((r) => r.id === run.rom)
      const name = rom?.display_name ?? run.rom
      const m = metricsMap.get(run.id)
      return {
        id: run.id,
        name,
        reward: m?.best_reward ?? 0,
        fps: m?.fps ?? 0,
        steps: m?.step ?? 0,
      }
    })
  }, [runs, roms, metricsMap])

  if (tickerEntries.length === 0) {
    return (
      <div className="bg-muted h-10 flex items-center justify-center">
        <span className="text-sm text-muted-foreground">
          Waiting for training...
        </span>
      </div>
    )
  }

  const animationDuration = `${Math.max(tickerEntries.length * 8, 16)}s`

  const renderEntries = () =>
    tickerEntries.map((entry) => (
      <span key={entry.id} className="whitespace-nowrap">
        <span className="text-primary font-semibold">{entry.name}</span>
        <span className="text-muted-foreground"> · Reward: </span>
        <span className="text-primary">{entry.reward.toFixed(1)}</span>
        <span className="text-muted-foreground"> · FPS: </span>
        <span className="text-primary">{entry.fps.toFixed(0)}</span>
        <span className="text-muted-foreground"> · Steps: </span>
        <span className="text-primary">{entry.steps.toLocaleString()}</span>
        <span className="text-muted-foreground mx-4">|</span>
      </span>
    ))

  return (
    <div className="bg-muted h-10 overflow-hidden flex items-center">
      <div
        className="flex whitespace-nowrap text-sm"
        style={{
          animation: `ticker-scroll ${animationDuration} linear infinite`,
        }}
      >
        {/* Render twice for seamless loop */}
        {renderEntries()}
        {renderEntries()}
      </div>
    </div>
  )
}
