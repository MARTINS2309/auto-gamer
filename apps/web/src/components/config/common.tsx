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
}: {
    label: string
    value: number
    min: number
    max: number
    step: number
    onChange: (val: number) => void
    tooltip: string
    readOnly?: boolean
}) {
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <LabelWithTooltip tooltip={tooltip}>{label}</LabelWithTooltip>
                <span className="font-mono text-sm text-muted-foreground w-12 text-right">
                    {value}
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
