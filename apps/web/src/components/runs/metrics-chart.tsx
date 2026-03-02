import { useState, useCallback } from "react"
import type { HTMLAttributes } from "react"

interface MetricsChartProps extends HTMLAttributes<HTMLDivElement> {
    data: number[]
    color: string
    maxValue?: number
    label?: string
    /** Step numbers aligned 1:1 with data — shown in hover tooltip */
    steps?: number[]
    /** Number of most-recent points to display (0 = all). Default: 100 */
    windowSize?: number
    /** Comparison data series rendered behind primary at reduced opacity */
    comparisonData?: number[]
    /** Phase transition markers */
    phaseMarkers?: { index: number; phase: string }[]
}

export function MetricsChart({
    data,
    color,
    maxValue,
    label,
    steps,
    windowSize = 100,
    comparisonData,
    phaseMarkers,
    className,
    ...props
}: MetricsChartProps) {
    const [hoverIndex, setHoverIndex] = useState<number | null>(null)

    const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        const rect = e.currentTarget.getBoundingClientRect()
        const x = e.clientX - rect.left
        const pct = x / rect.width
        setHoverIndex(pct)
    }, [])

    const handleMouseLeave = useCallback(() => {
        setHoverIndex(null)
    }, [])

    if (data.length === 0) {
        return <span className="text-muted-foreground text-sm">No data yet</span>
    }

    const validData = data.filter(n => !isNaN(n) && isFinite(n));
    if (validData.length === 0) return <span className="text-muted-foreground text-sm">No valid data</span>

    const computedMax = Math.max(...validData)
    const computedMin = Math.min(...validData)

    const range = computedMax - computedMin;
    const effectiveMax = maxValue ?? (computedMax + (range * 0.1))
    const effectiveMin = computedMin - (range * 0.1)

    const displayRange = effectiveMax - effectiveMin

    const recentData = windowSize > 0 ? data.slice(-windowSize) : data
    const recentSteps = steps ? (windowSize > 0 ? steps.slice(-windowSize) : steps) : undefined
    const recentComparison = comparisonData ? (windowSize > 0 ? comparisonData.slice(-windowSize) : comparisonData) : undefined

    // Compute phase markers within the visible window
    const windowStart = windowSize > 0 ? Math.max(0, data.length - windowSize) : 0
    const visibleMarkers = phaseMarkers?.filter(m => m.index >= windowStart && m.index < windowStart + recentData.length)
        .map(m => ({ ...m, index: m.index - windowStart }))

    const hoverIdx = hoverIndex !== null ? Math.max(0, Math.min(recentData.length - 1, Math.floor(hoverIndex * recentData.length))) : null
    const hoverValue = hoverIdx !== null ? recentData[hoverIdx] : null
    const hoverStep = hoverIdx !== null && recentSteps ? recentSteps[hoverIdx] : null

    // For large datasets, drop gaps and transitions to avoid overflow + layout thrash
    const dense = recentData.length > 150

    return (
        <div
            className={`w-full h-full flex items-end group relative overflow-hidden ${dense ? '' : 'gap-px'} ${className}`}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            {...props}
        >
            {/* Comparison bars (behind) */}
            {recentComparison && recentComparison.map((value, i) => {
                let percent = 50;
                if (displayRange > 0.000001) {
                    percent = ((value - effectiveMin) / displayRange) * 100;
                }
                percent = Math.max(0, Math.min(100, percent));
                return (
                    <div
                        key={`cmp-${i}`}
                        className="absolute bottom-0 bg-muted-foreground/20"
                        style={{
                            height: `${percent}%`,
                            left: `${(i / recentData.length) * 100}%`,
                            width: `${100 / recentData.length}%`,
                        }}
                    />
                )
            })}

            {/* Primary bars */}
            {recentData.map((value, i) => {
                let percent = 50;
                if (displayRange > 0.000001) {
                    percent = ((value - effectiveMin) / displayRange) * 100;
                }
                percent = Math.max(0, Math.min(100, percent));

                return (
                    <div
                        key={i}
                        className={`flex-1 min-w-0 ${color} ${
                            dense ? '' : 'min-w-px transition-all duration-150 ease-out'
                        } ${i === hoverIdx ? 'brightness-125' : ''}`}
                        style={{ height: `${percent}%` }}
                    />
                )
            })}

            {/* Phase markers */}
            {visibleMarkers?.map((marker, i) => (
                <div
                    key={`phase-${i}`}
                    className="absolute top-0 bottom-0 w-px pointer-events-none"
                    style={{
                        left: `${((marker.index + 0.5) / recentData.length) * 100}%`,
                        backgroundColor: marker.phase === "rollout" ? "var(--color-chart-1)" : "var(--color-chart-3)",
                        opacity: 0.4,
                    }}
                />
            ))}

            {/* Crosshair vertical line */}
            {hoverIdx !== null && (
                <div
                    className="absolute top-0 bottom-0 w-px bg-primary/60 pointer-events-none"
                    style={{
                        left: `${((hoverIdx + 0.5) / recentData.length) * 100}%`
                    }}
                />
            )}

            {/* Value overlay */}
            {hoverValue !== null && hoverIdx !== null && (
                <div
                    className="absolute pointer-events-none bg-background/90 border border-primary px-2 py-1 text-xs font-semibold z-10"
                    style={{
                        left: `${((hoverIdx + 0.5) / recentData.length) * 100}%`,
                        top: '4px',
                        transform: hoverIdx > recentData.length * 0.6 ? 'translateX(-100%)' : 'translateX(0)',
                    }}
                >
                    {hoverStep != null && (
                        <span className="text-muted-foreground">Step {hoverStep.toLocaleString()} | </span>
                    )}
                    <span className="text-muted-foreground">{label}: </span>
                    <span className="text-primary">{hoverValue.toFixed(4)}</span>
                </div>
            )}

            {/* Min/Max labels — hidden during hover */}
            {hoverIdx === null && (
                <>
                    <div className="absolute top-0 right-0 text-[10px] text-muted-foreground bg-background/80 px-1 pointer-events-none">
                        {computedMax.toFixed(2)}
                    </div>
                    <div className="absolute bottom-0 right-0 text-[10px] text-muted-foreground bg-background/80 px-1 pointer-events-none">
                        {computedMin.toFixed(2)}
                    </div>
                </>
            )}
        </div>
    )
}
