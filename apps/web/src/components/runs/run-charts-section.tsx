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
    const hasKLDivergence = history.some(m => m.details?.["train/approx_kl"] !== undefined);
    const hasExplainedVariance = history.some(m => m.details?.["train/explained_variance"] !== undefined);
    const hasLearningRate = history.some(m => m.details?.["train/learning_rate"] !== undefined);

    // Helper to extract data stream handling sparse updates
    // (SB3 metrics might come less frequently than frames)
    // Actually we should just filter for points where it exists
    const getStream = (key: string): number[] => {
        return history
            .map(m => m.details?.[key])
            .filter(v => typeof v === 'number') as number[]
    }

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
                <CardHeader>
                    <CardTitle className="text-sm">Episode Reward (Mean)</CardTitle>
                </CardHeader>
                <CardContent className="h-60 pt-4">
                    <MetricsChart
                        data={history.map((m) => m.avg_reward ?? 0)}
                        color="bg-chart-1"
                        className="items-end"
                        label="Reward"
                    />
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-sm">FPS Over Time</CardTitle>
                </CardHeader>
                <CardContent className="h-60 pt-4">
                    <MetricsChart
                        data={history.map((m) => m.fps ?? 0)}
                        color="bg-chart-4"
                        className="items-end"
                        label="FPS"
                    />
                </CardContent>
            </Card>

            {hasValueLoss && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm">Value Loss</CardTitle>
                    </CardHeader>
                    <CardContent className="h-60 pt-4">
                        <MetricsChart
                            data={getStream("train/value_loss")}
                            color="bg-orange-500"
                            className="items-end"
                            label="Value Loss"
                        />
                    </CardContent>
                </Card>
            )}

            {hasPolicyLoss && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm">Policy Gradient Loss</CardTitle>
                    </CardHeader>
                    <CardContent className="h-60 pt-4">
                        <MetricsChart
                            data={getStream("train/policy_gradient_loss")}
                            color="bg-blue-500"
                            className="items-end"
                            label="Policy Loss"
                        />
                    </CardContent>
                </Card>
            )}

            {hasEntropy && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm">Entropy Loss</CardTitle>
                    </CardHeader>
                    <CardContent className="h-60 pt-4">
                        <MetricsChart
                            data={getStream("train/entropy_loss")}
                            color="bg-purple-500"
                            className="items-end"
                            label="Entropy"
                        />
                    </CardContent>
                </Card>
            )}

            {hasKLDivergence && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm">Approx KL Divergence</CardTitle>
                    </CardHeader>
                    <CardContent className="h-60 pt-4">
                        <MetricsChart
                            data={getStream("train/approx_kl")}
                            color="bg-indigo-500"
                            className="items-end"
                            label="KL Div"
                        />
                    </CardContent>
                </Card>
            )}

            {hasExplainedVariance && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm">Explained Variance</CardTitle>
                    </CardHeader>
                    <CardContent className="h-60 pt-4">
                        <MetricsChart
                            data={getStream("train/explained_variance")}
                            color="bg-cyan-500"
                            className="items-end"
                            label="Variance"
                        />
                    </CardContent>
                </Card>
            )}

            {hasLearningRate && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm">Learning Rate</CardTitle>
                    </CardHeader>
                    <CardContent className="h-60 pt-4">
                        <MetricsChart
                            data={getStream("train/learning_rate")}
                            color="bg-teal-500"
                            className="items-end"
                            label="LR"
                        />
                    </CardContent>
                </Card>
            )}
        </div>
    )
}
