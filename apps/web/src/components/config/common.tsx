import { HelpCircle } from "lucide-react"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip"

export function LabelWithTooltip({ children, tooltip }: { children: React.ReactNode; tooltip: string }) {
    return (
        <div className="flex items-center gap-2">
            <Label>{children}</Label>
            <TooltipProvider>
                <Tooltip delayDuration={300}>
                    <TooltipTrigger asChild>
                        <HelpCircle className="size-3.5 text-muted-foreground cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">{tooltip}</TooltipContent>
                </Tooltip>
            </TooltipProvider>
        </div>
    )
}

export function HyperparamSlider({
    label,
    value,
    min,
    max,
    step,
    onChange,
    tooltip,
    readOnly = false,
    formatValue,
}: {
    label: string
    value: number
    min: number
    max: number
    step: number
    onChange: (val: number) => void
    tooltip: string
    readOnly?: boolean
    formatValue?: (val: number) => string
}) {
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <LabelWithTooltip tooltip={tooltip}>{label}</LabelWithTooltip>
                <span className="font-mono text-sm text-muted-foreground tabular-nums shrink-0 text-right">
                    {formatValue ? formatValue(value) : value}
                </span>
            </div>
            <Slider
                min={min}
                max={max}
                step={step}
                value={[value]}
                onValueChange={(vals) => onChange(vals[0])}
                disabled={readOnly}
                className={readOnly ? "opacity-50" : ""}
            />
        </div>
    )
}

/** Log-scale slider for values spanning orders of magnitude (learning rate, epsilon, etc.) */
export function LogHyperparamSlider({
    label,
    value,
    min,
    max,
    onChange,
    tooltip,
    readOnly = false,
    formatValue,
}: {
    label: string
    value: number
    min: number
    max: number
    onChange: (val: number) => void
    tooltip: string
    readOnly?: boolean
    formatValue?: (val: number) => string
}) {
    const minLog = Math.log10(min)
    const maxLog = Math.log10(max)
    const resolution = 200

    const logVal = Math.log10(Math.max(value, min))
    const sliderPos = Math.round(((logVal - minLog) / (maxLog - minLog)) * resolution)

    const posToValue = (pos: number) => {
        const log = minLog + (pos / resolution) * (maxLog - minLog)
        const raw = Math.pow(10, log)
        // Round to 2 significant figures
        const d = Math.floor(Math.log10(Math.abs(raw)))
        const factor = Math.pow(10, 1 - d)
        return Math.round(raw * factor) / factor
    }

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <LabelWithTooltip tooltip={tooltip}>{label}</LabelWithTooltip>
                <span className="font-mono text-sm text-muted-foreground tabular-nums shrink-0 text-right">
                    {formatValue ? formatValue(value) : value.toExponential(1)}
                </span>
            </div>
            <Slider
                min={0} max={resolution} step={1}
                value={[sliderPos]}
                onValueChange={(vals) => onChange(posToValue(vals[0]))}
                disabled={readOnly}
                className={readOnly ? "opacity-50" : ""}
            />
        </div>
    )
}

/** Format a number compactly (e.g. 1000 -> "1K", 1000000 -> "1M") */
// eslint-disable-next-line react-refresh/only-export-components
export function formatCompact(n: number): string {
    if (n >= 1_000_000) return `${n / 1_000_000}M`
    if (n >= 1_000) return `${n / 1_000}K`
    return n.toString()
}

/** Slider that snaps to specific discrete allowed values */
export function DiscreteHyperparamSlider({
    label,
    value,
    values,
    onChange,
    tooltip,
    readOnly = false,
    formatValue,
}: {
    label: string
    value: number
    values: readonly number[] | number[]
    onChange: (val: number) => void
    tooltip: string
    readOnly?: boolean
    formatValue?: (val: number) => string
}) {
    let bestIndex = 0
    let bestDist = Infinity
    for (let i = 0; i < values.length; i++) {
        const dist = Math.abs(values[i] - value)
        if (dist < bestDist) {
            bestDist = dist
            bestIndex = i
        }
    }

    const currentValue = values[bestIndex]

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <LabelWithTooltip tooltip={tooltip}>{label}</LabelWithTooltip>
                <span className="font-mono text-sm text-muted-foreground tabular-nums shrink-0 text-right">
                    {formatValue ? formatValue(currentValue) : currentValue}
                </span>
            </div>
            <Slider
                min={0} max={values.length - 1} step={1}
                value={[bestIndex]}
                onValueChange={(vals) => onChange(values[vals[0]])}
                disabled={readOnly}
                className={readOnly ? "opacity-50" : ""}
            />
        </div>
    )
}
