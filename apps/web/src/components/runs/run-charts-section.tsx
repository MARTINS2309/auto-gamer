import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { MetricsChart } from "./metrics-chart"
import type { RunMetrics } from "@/lib/schemas"

interface RunChartsSectionProps {
    history: RunMetrics[]
}

export function RunChartsSection({ history }: RunChartsSectionProps) {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
                <CardHeader>
                    <CardTitle className="text-sm">Episode Reward</CardTitle>
                </CardHeader>
                <CardContent className="h-60 flex items-center justify-center pt-2">
                    <MetricsChart
                        data={history.map((m) => m.reward)}
                        color="bg-chart-1"
                        className="items-end"
                    />
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-sm">FPS Over Time</CardTitle>
                </CardHeader>
                <CardContent className="h-60 flex items-center justify-center pt-2">
                    <MetricsChart
                        data={history.map((m) => m.fps)}
                        color="bg-chart-4"
                        maxValue={60}
                        className="items-end"
                    />
                </CardContent>
            </Card>
        </div>
    )
}
