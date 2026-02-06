import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { MetricsChart } from "./metrics-chart"
import type { RunMetrics } from "@/lib/schemas"

interface RunChartsSectionProps {
    history: RunMetrics[]
}

export function RunChartsSection({ history }: RunChartsSectionProps) {
    // Debug: collect ALL unique detail keys across ALL metrics
    const allDetailKeys = new Set<string>()
    history.forEach(m => {
        if (m.details) {
            Object.keys(m.details).forEach(k => allDetailKeys.add(k))
        }
    })
    if (allDetailKeys.size > 0) {
        console.log("[Charts] All detail keys across history:", Array.from(allDetailKeys))
    }

    // Check for availability of advanced metrics (from SB3 logger)
    const hasValueLoss = history.some(m => m.details?.["train/value_loss"] !== undefined);
    const hasPolicyLoss = history.some(m => m.details?.["train/policy_gradient_loss"] !== undefined);
    const hasEntropy = history.some(m => m.details?.["train/entropy_loss"] !== undefined);
    const hasKLDivergence = history.some(m => m.details?.["train/approx_kl"] !== undefined);
    const hasExplainedVariance = history.some(m => m.details?.["train/explained_variance"] !== undefined);
    const hasLearningRate = history.some(m => m.details?.["train/learning_rate"] !== undefined);
    const hasLoss = history.some(m => m.loss !== undefined && m.loss !== null);

    // Helper to extract data stream - converts strings/any to numbers
    const getStream = (key: string): number[] => {
        return history
            .map(m => {
                const v = m.details?.[key]
                if (v === undefined || v === null) return null
                const num = typeof v === 'number' ? v : parseFloat(v)
                return isNaN(num) ? null : num
            })
            .filter((v): v is number => v !== null)
    }

    // Filter out zeros for reward charts (zeros mean no episodes completed yet)
    const avgRewards = history.map((m) => m.avg_reward ?? 0)
    const bestRewards = history.map((m) => m.best_reward ?? 0)
    const hasRewardData = avgRewards.some(r => r !== 0) || bestRewards.some(r => r !== 0)

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Episode Reward (Mean)</CardTitle>
                    {!hasRewardData && (
                        <CardDescription className="text-xs">
                            Waiting for episodes to complete...
                        </CardDescription>
                    )}
                </CardHeader>
                <CardContent className="h-60 pt-4">
                    <MetricsChart
                        data={avgRewards}
                        color="bg-chart-1"
                        className="items-end"
                        label="Avg Reward"
                    />
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Best Reward</CardTitle>
                </CardHeader>
                <CardContent className="h-60 pt-4">
                    <MetricsChart
                        data={bestRewards}
                        color="bg-chart-2"
                        className="items-end"
                        label="Best"
                    />
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="pb-2">
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

            {hasLoss && (
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Training Loss</CardTitle>
                    </CardHeader>
                    <CardContent className="h-60 pt-4">
                        <MetricsChart
                            data={history.map((m) => m.loss ?? 0).filter(v => v !== 0)}
                            color="bg-orange-500"
                            className="items-end"
                            label="Loss"
                        />
                    </CardContent>
                </Card>
            )}

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
