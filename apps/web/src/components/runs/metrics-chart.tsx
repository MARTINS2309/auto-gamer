import type { HTMLAttributes } from "react"

interface MetricsChartProps extends HTMLAttributes<HTMLDivElement> {
    data: number[]
    color: string
    maxValue?: number
    label?: string
}

export function MetricsChart({ data, color, maxValue, label, className, ...props }: MetricsChartProps) {
    if (data.length === 0) {
        return <span className="text-muted-foreground text-sm">No data yet</span>
    }

    // Filter out crazy values or keep them? 
    // Stable Baselines can report -inf rewards or huge FPS
    // Let's rely on auto-scaling mostly.

    // Auto scale min and max
    const validData = data.filter(n => !isNaN(n) && isFinite(n));
    if (validData.length === 0) return <span className="text-muted-foreground text-sm">No valid data</span>

    const computedMax = Math.max(...validData)
    const computedMin = Math.min(...validData)

    // Determine range
    const range = computedMax - computedMin;
    // Add 10% padding
    const effectiveMax = maxValue ?? (computedMax + (range * 0.1))
    const effectiveMin = computedMin - (range * 0.1)

    const displayRange = effectiveMax - effectiveMin

    // Ensure we only show last 100 points
    const recentData = data.slice(-100)

    return (
        <div className={`w-full h-full flex items-end gap-px group relative ${className}`} {...props}>
            {/* Simple tooltip overlay using group-hover could be added here, but keeping it simple for now */}

            {recentData.map((value, i) => {
                // Calculate percentage height relative to min/max
                // If range is 0 (all values same), show 50% height
                let percent = 50;
                if (displayRange > 0.000001) {
                    percent = ((value - effectiveMin) / displayRange) * 100;
                }

                // Clamp
                percent = Math.max(0, Math.min(100, percent));

                return (
                    <div
                        key={i}
                        className={`flex-1 ${color} min-w-px transition-all duration-300 ease-out hover:brightness-110 relative`}
                        style={{ height: `${percent}%` }}
                        title={`${label ? label + ': ' : ''}${value.toFixed(4)}`}
                    />
                )
            })}
            <div className="absolute top-0 right-0 text-[10px] text-muted-foreground bg-background/80 px-1">
                Max: {computedMax.toFixed(2)}
            </div>
            <div className="absolute bottom-0 right-0 text-[10px] text-muted-foreground bg-background/80 px-1">
                Min: {computedMin.toFixed(2)}
            </div>
        </div>
    )
}
