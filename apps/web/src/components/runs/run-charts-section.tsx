import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { MetricsChart } from "./metrics-chart"
import type { RunMetrics } from "@/lib/schemas"

interface RunChartsSectionProps {
    history: RunMetrics[]
}

export function RunChartsSection({ history }: RunChartsSectionProps) {
    // Check for availability of advanced metrics
    const hasValueLoss = history.some(m => m.details?.["train/value_loss"] !== undefined);
    const hasPolicyLoss = history.some(m => m.details?.["train/policy_gradient_loss"] !== undefined);
    const hasEntropy = history.some(m => m.details?.["train/entropy_loss"] !== undefined);

    // Helper to extract data stream handling sparse updates
    // (SB3 metrics might come less frequently than frames)
    // Actually we should just filter for points where it exists
    const getStream = (key: string): number[] => {
        return history
            .filter(m => m.details?.[key] !== undefined)
            .map(m => m.details![key] as number)
    }

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
                <CardHeader>
                    <CardTitle className="text-sm">Episode Reward (Mean)</CardTitle>
                </CardHeader>
                <CardContent className="h-60 flex items-center justify-center pt-2">
                    <MetricsChart
                        data={history.map((m) => m.avg_reward || m.reward)}
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

            {hasValueLoss && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm">Value Loss</CardTitle>
                    </CardHeader>
                    <CardContent className="h-60 flex items-center justify-center pt-2">
                        <MetricsChart
                            data={getStream("train/value_loss")}
                            color="bg-orange-500"
                            className="items-end"
                        />
                    </CardContent>
                </Card>
            )}

            {hasPolicyLoss && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm">Policy Gradient Loss</CardTitle>
                    </CardHeader>
                    <CardContent className="h-60 flex items-center justify-center pt-2">
                        <MetricsChart
                            data={getStream("train/policy_gradient_loss")}
                            color="bg-blue-500"
                            className="items-end"
                        />
                    </CardContent>
                </Card>
            )}

            {hasEntropy && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm">Entropy Loss</CardTitle>
                    </CardHeader>
                    <CardContent className="h-60 flex items-center justify-center pt-2">
                        <MetricsChart
                            data={getStream("train/entropy_loss")}
                            color="bg-purple-500"
                            className="items-end"
                        />
                    </CardContent>
                </Card>
            )}
        </div>
    )
}
