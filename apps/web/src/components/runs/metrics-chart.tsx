import type { HTMLAttributes } from "react"

interface MetricsChartProps extends HTMLAttributes<HTMLDivElement> {
    data: number[]
    color: string
    maxValue?: number
}

export function MetricsChart({ data, color, maxValue, className, ...props }: MetricsChartProps) {
    if (data.length === 0) {
        return <span className="text-muted-foreground text-sm">No data yet</span>
    }

    // Calculate max value for scaling, ensure at least 1 to avoid division by zero
    const max = maxValue ?? (Math.max(...data) || 1)
    // Ensure we only show last 100 points
    const recentData = data.slice(-100)

    return (
        <div className={`w-full h-full flex items-end gap-px ${className}`} {...props}>
            {recentData.map((value, i) => (
                <div
                    key={i}
                    className={`flex-1 ${color} min-w-px transition-all duration-300 ease-out`}
                    style={{ height: `${Math.max(5, (value / max) * 100)}%` }}
                />
            ))}
        </div>
    )
}
