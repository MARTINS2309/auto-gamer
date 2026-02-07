import { useState, useCallback } from "react"
import type { HTMLAttributes } from "react"

interface MetricsChartProps extends HTMLAttributes<HTMLDivElement> {
    data: number[]
    color: string
    maxValue?: number
    label?: string
}

export function MetricsChart({ data, color, maxValue, label, className, ...props }: MetricsChartProps) {
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

    const recentData = data.slice(-100)
    const hoverIdx = hoverIndex !== null ? Math.max(0, Math.min(recentData.length - 1, Math.floor(hoverIndex * recentData.length))) : null
    const hoverValue = hoverIdx !== null ? recentData[hoverIdx] : null

    return (
        <div
            className={`w-full h-full flex items-end gap-px group relative ${className}`}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            {...props}
        >
            {recentData.map((value, i) => {
                let percent = 50;
                if (displayRange > 0.000001) {
                    percent = ((value - effectiveMin) / displayRange) * 100;
                }
                percent = Math.max(0, Math.min(100, percent));

                return (
                    <div
                        key={i}
                        className={`flex-1 ${color} min-w-px transition-all duration-150 ease-out ${
                            i === hoverIdx ? 'brightness-125' : ''
                        }`}
                        style={{ height: `${percent}%` }}
                    />
                )
            })}

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
