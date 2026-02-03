import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Slider } from "@/components/ui/slider"
import { LabelWithTooltip, HyperparamSlider } from "./common"
import type { RunHyperparams } from "@/lib/schemas"

interface HyperparametersCardProps {
    hparams: Partial<RunHyperparams>
    onChange: (key: keyof RunHyperparams, value: number) => void
}

export function HyperparametersCard({ hparams, onChange }: HyperparametersCardProps) {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
                <h3 className="text-lg font-medium mb-1">Hyperparameters</h3>
                <p className="text-sm text-muted-foreground">
                    Fine-tune the mathematics of the agent. These are advanced settings that significantly affect convergence.
                </p>
            </div>
            <Card className="lg:col-span-2">
                <CardContent className="space-y-8 pt-6">

                    {/* Learning Rate & Schedule */}
                    <div className="space-y-4">
                        <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Optimization</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-secondary/20 p-4 rounded-lg">
                            <div className="space-y-2">
                                <LabelWithTooltip tooltip="Step size for gradient descent. Smaller values are more stable but slower.">
                                    Learning Rate
                                </LabelWithTooltip>
                                <Input
                                    type="number"
                                    step="0.00001"
                                    value={hparams.learning_rate}
                                    onChange={(e) => onChange("learning_rate", parseFloat(e.target.value))}
                                />
                            </div>
                            <div className="space-y-2">
                                <LabelWithTooltip tooltip="Discount factor for future rewards. closer to 1 means agent cares more about long-term goals.">
                                    Gamma (Discount Factor)
                                </LabelWithTooltip>
                                <Slider
                                    min={0.8} max={0.9999} step={0.0001}
                                    value={[hparams.gamma || 0.99]}
                                    onValueChange={(v) => onChange("gamma", v[0])}
                                />
                                <div className="text-right text-xs font-mono text-muted-foreground">{hparams.gamma}</div>
                            </div>
                        </div>
                    </div>

                    {/* PPO Specifics */}
                    <div className="space-y-4">
                        <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Policy Updates</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">

                            <HyperparamSlider
                                label="Clip Range"
                                value={hparams.clip_range || 0.2}
                                min={0.1} max={0.4} step={0.05}
                                onChange={(v) => onChange("clip_range", v)}
                                tooltip="PPO clipping parameter. Prevents the policy from changing too drastically in one update."
                            />

                            <HyperparamSlider
                                label="Entropy Coeff"
                                value={hparams.ent_coef || 0.0}
                                min={0.0} max={0.1} step={0.001}
                                onChange={(v) => onChange("ent_coef", v)}
                                tooltip="Encourages exploration by penalizing certainty. Increase if agent gets stuck in local optima."
                            />

                            <HyperparamSlider
                                label="Value Function Coeff"
                                value={hparams.vf_coef || 0.5}
                                min={0.1} max={1.0} step={0.1}
                                onChange={(v) => onChange("vf_coef", v)}
                                tooltip="Weight of the value function loss relative to the policy loss."
                            />

                            <HyperparamSlider
                                label="Max Grad Norm"
                                value={hparams.max_grad_norm || 0.5}
                                min={0.1} max={5.0} step={0.1}
                                onChange={(v) => onChange("max_grad_norm", v)}
                                tooltip="Gradient clipping threshold to prevent exploding gradients."
                            />
                        </div>
                    </div>

                    {/* Rollout Config */}
                    <div className="space-y-4">
                        <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Rollout Configuration</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                            <div className="space-y-2">
                                <LabelWithTooltip tooltip="Number of steps to run for each environment per update.">
                                    N Steps (Rollout Length)
                                </LabelWithTooltip>
                                <Input
                                    type="number"
                                    step="128"
                                    value={hparams.n_steps || 2048}
                                    onChange={(e) => onChange("n_steps", parseInt(e.target.value))}
                                />
                            </div>

                            <div className="space-y-2">
                                <LabelWithTooltip tooltip="Minibatch size for PPO updates. Must be a factor of n_steps * n_envs.">
                                    Batch Size
                                </LabelWithTooltip>
                                <Input
                                    type="number"
                                    step="32"
                                    value={hparams.batch_size || 64}
                                    onChange={(e) => onChange("batch_size", parseInt(e.target.value))}
                                />
                            </div>

                            <HyperparamSlider
                                label="N Epochs"
                                value={hparams.n_epochs || 10}
                                min={1} max={50} step={1}
                                onChange={(v) => onChange("n_epochs", v)}
                                tooltip="Number of epochs to optimize the surrogate loss using the current rollout buffer."
                            />

                            <HyperparamSlider
                                label="GAE Lambda"
                                value={hparams.gae_lambda || 0.95}
                                min={0.8} max={1.0} step={0.01}
                                onChange={(v) => onChange("gae_lambda", v)}
                                tooltip="Factor for trade-off of bias vs variance for Generalized Advantage Estimator."
                            />

                        </div>
                    </div>

                </CardContent>
            </Card>
        </div>
    )
}
