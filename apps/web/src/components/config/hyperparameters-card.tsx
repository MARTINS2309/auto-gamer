import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { LabelWithTooltip, HyperparamSlider } from "./common"
import type { Algorithm, PPOHyperparams, A2CHyperparams, DQNHyperparams } from "@/lib/schemas"

type AnyHyperparams = Partial<PPOHyperparams & A2CHyperparams & DQNHyperparams>

interface HyperparametersCardProps {
    algorithm: Algorithm
    hparams: AnyHyperparams
    onChange: (key: string, value: number | boolean) => void
}

export function HyperparametersCard({ algorithm, hparams, onChange }: HyperparametersCardProps) {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
                <h3 className="text-lg font-medium mb-1">Hyperparameters</h3>
                <p className="text-sm text-muted-foreground">
                    Fine-tune the mathematics of the agent. These are advanced settings that significantly affect convergence.
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                    Showing parameters for <span className="font-semibold">{algorithm}</span>
                </p>
            </div>
            <Card className="lg:col-span-2">
                <CardContent className="space-y-8 pt-6">
                    {algorithm === "PPO" && <PPOParams hparams={hparams} onChange={onChange} />}
                    {algorithm === "A2C" && <A2CParams hparams={hparams} onChange={onChange} />}
                    {algorithm === "DQN" && <DQNParams hparams={hparams} onChange={onChange} />}
                </CardContent>
            </Card>
        </div>
    )
}

// =============================================================================
// PPO Parameters
// =============================================================================

function PPOParams({ hparams, onChange }: { hparams: AnyHyperparams; onChange: (key: string, value: number | boolean) => void }) {
    return (
        <>
            {/* Optimization */}
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
                            value={hparams.learning_rate ?? 0.0003}
                            onChange={(e) => onChange("learning_rate", parseFloat(e.target.value))}
                        />
                    </div>
                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="Discount factor for future rewards. Closer to 1 means agent cares more about long-term goals.">
                            Gamma (Discount Factor)
                        </LabelWithTooltip>
                        <Slider
                            min={0.8} max={0.9999} step={0.0001}
                            value={[hparams.gamma ?? 0.99]}
                            onValueChange={(v) => onChange("gamma", v[0])}
                        />
                        <div className="text-right text-xs font-mono text-muted-foreground">{hparams.gamma ?? 0.99}</div>
                    </div>
                </div>
            </div>

            {/* Policy Updates */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Policy Updates</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <HyperparamSlider
                        label="Clip Range"
                        value={hparams.clip_range ?? 0.2}
                        min={0.05} max={0.5} step={0.01}
                        onChange={(v) => onChange("clip_range", v)}
                        tooltip="PPO clipping parameter. Prevents the policy from changing too drastically in one update."
                    />
                    <HyperparamSlider
                        label="Entropy Coeff"
                        value={hparams.ent_coef ?? 0.0}
                        min={0.0} max={0.1} step={0.001}
                        onChange={(v) => onChange("ent_coef", v)}
                        tooltip="Encourages exploration by penalizing certainty. Increase if agent gets stuck in local optima."
                    />
                    <HyperparamSlider
                        label="Value Function Coeff"
                        value={hparams.vf_coef ?? 0.5}
                        min={0.1} max={1.0} step={0.1}
                        onChange={(v) => onChange("vf_coef", v)}
                        tooltip="Weight of the value function loss relative to the policy loss."
                    />
                    <HyperparamSlider
                        label="Max Grad Norm"
                        value={hparams.max_grad_norm ?? 0.5}
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
                            value={hparams.n_steps ?? 2048}
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
                            value={hparams.batch_size ?? 64}
                            onChange={(e) => onChange("batch_size", parseInt(e.target.value))}
                        />
                    </div>
                    <HyperparamSlider
                        label="N Epochs"
                        value={hparams.n_epochs ?? 10}
                        min={1} max={50} step={1}
                        onChange={(v) => onChange("n_epochs", v)}
                        tooltip="Number of epochs to optimize the surrogate loss using the current rollout buffer."
                    />
                    <HyperparamSlider
                        label="GAE Lambda"
                        value={hparams.gae_lambda ?? 0.95}
                        min={0.8} max={1.0} step={0.01}
                        onChange={(v) => onChange("gae_lambda", v)}
                        tooltip="Factor for trade-off of bias vs variance for Generalized Advantage Estimator."
                    />
                </div>
            </div>

            {/* Advanced */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Advanced</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg">
                        <LabelWithTooltip tooltip="Normalize advantages before policy update. Generally improves stability.">
                            Normalize Advantage
                        </LabelWithTooltip>
                        <Switch
                            checked={hparams.normalize_advantage ?? true}
                            onCheckedChange={(v) => onChange("normalize_advantage", v)}
                        />
                    </div>
                    <div className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg">
                        <LabelWithTooltip tooltip="Use Generalized State-Dependent Exploration. Better for continuous action spaces.">
                            Use SDE
                        </LabelWithTooltip>
                        <Switch
                            checked={hparams.use_sde ?? false}
                            onCheckedChange={(v) => onChange("use_sde", v)}
                        />
                    </div>
                </div>
            </div>
        </>
    )
}

// =============================================================================
// A2C Parameters
// =============================================================================

function A2CParams({ hparams, onChange }: { hparams: AnyHyperparams; onChange: (key: string, value: number | boolean) => void }) {
    return (
        <>
            {/* Optimization */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Optimization</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-secondary/20 p-4 rounded-lg">
                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="Step size for gradient descent. A2C default is higher than PPO.">
                            Learning Rate
                        </LabelWithTooltip>
                        <Input
                            type="number"
                            step="0.00001"
                            value={hparams.learning_rate ?? 0.0007}
                            onChange={(e) => onChange("learning_rate", parseFloat(e.target.value))}
                        />
                    </div>
                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="Discount factor for future rewards.">
                            Gamma (Discount Factor)
                        </LabelWithTooltip>
                        <Slider
                            min={0.8} max={0.9999} step={0.0001}
                            value={[hparams.gamma ?? 0.99]}
                            onValueChange={(v) => onChange("gamma", v[0])}
                        />
                        <div className="text-right text-xs font-mono text-muted-foreground">{hparams.gamma ?? 0.99}</div>
                    </div>
                </div>
            </div>

            {/* Policy Updates */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Policy Updates</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <HyperparamSlider
                        label="Entropy Coeff"
                        value={hparams.ent_coef ?? 0.0}
                        min={0.0} max={0.1} step={0.001}
                        onChange={(v) => onChange("ent_coef", v)}
                        tooltip="Encourages exploration by penalizing certainty."
                    />
                    <HyperparamSlider
                        label="Value Function Coeff"
                        value={hparams.vf_coef ?? 0.5}
                        min={0.1} max={1.0} step={0.1}
                        onChange={(v) => onChange("vf_coef", v)}
                        tooltip="Weight of the value function loss."
                    />
                    <HyperparamSlider
                        label="Max Grad Norm"
                        value={hparams.max_grad_norm ?? 0.5}
                        min={0.1} max={5.0} step={0.1}
                        onChange={(v) => onChange("max_grad_norm", v)}
                        tooltip="Gradient clipping threshold."
                    />
                    <HyperparamSlider
                        label="GAE Lambda"
                        value={hparams.gae_lambda ?? 1.0}
                        min={0.8} max={1.0} step={0.01}
                        onChange={(v) => onChange("gae_lambda", v)}
                        tooltip="GAE lambda. 1.0 = classic advantage (no bias reduction)."
                    />
                </div>
            </div>

            {/* Rollout Config */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Rollout Configuration</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="Number of steps per environment per update. A2C typically uses smaller values.">
                            N Steps
                        </LabelWithTooltip>
                        <Input
                            type="number"
                            step="1"
                            value={hparams.n_steps ?? 5}
                            onChange={(e) => onChange("n_steps", parseInt(e.target.value))}
                        />
                    </div>
                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="RMSProp epsilon for numerical stability.">
                            RMSProp Epsilon
                        </LabelWithTooltip>
                        <Input
                            type="number"
                            step="0.000001"
                            value={hparams.rms_prop_eps ?? 1e-5}
                            onChange={(e) => onChange("rms_prop_eps", parseFloat(e.target.value))}
                        />
                    </div>
                </div>
            </div>

            {/* Advanced */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Advanced</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg">
                        <LabelWithTooltip tooltip="Use RMSprop optimizer instead of Adam. Recommended for A2C.">
                            Use RMSprop
                        </LabelWithTooltip>
                        <Switch
                            checked={hparams.use_rms_prop ?? true}
                            onCheckedChange={(v) => onChange("use_rms_prop", v)}
                        />
                    </div>
                    <div className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg">
                        <LabelWithTooltip tooltip="Normalize advantages before policy update.">
                            Normalize Advantage
                        </LabelWithTooltip>
                        <Switch
                            checked={hparams.normalize_advantage ?? false}
                            onCheckedChange={(v) => onChange("normalize_advantage", v)}
                        />
                    </div>
                    <div className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg">
                        <LabelWithTooltip tooltip="Use Generalized State-Dependent Exploration.">
                            Use SDE
                        </LabelWithTooltip>
                        <Switch
                            checked={hparams.use_sde ?? false}
                            onCheckedChange={(v) => onChange("use_sde", v)}
                        />
                    </div>
                </div>
            </div>
        </>
    )
}

// =============================================================================
// DQN Parameters
// =============================================================================

function DQNParams({ hparams, onChange }: { hparams: AnyHyperparams; onChange: (key: string, value: number | boolean) => void }) {
    return (
        <>
            {/* Optimization */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Optimization</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-secondary/20 p-4 rounded-lg">
                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="Step size for gradient descent.">
                            Learning Rate
                        </LabelWithTooltip>
                        <Input
                            type="number"
                            step="0.00001"
                            value={hparams.learning_rate ?? 0.0001}
                            onChange={(e) => onChange("learning_rate", parseFloat(e.target.value))}
                        />
                    </div>
                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="Discount factor for future rewards.">
                            Gamma (Discount Factor)
                        </LabelWithTooltip>
                        <Slider
                            min={0.8} max={0.9999} step={0.0001}
                            value={[hparams.gamma ?? 0.99]}
                            onValueChange={(v) => onChange("gamma", v[0])}
                        />
                        <div className="text-right text-xs font-mono text-muted-foreground">{hparams.gamma ?? 0.99}</div>
                    </div>
                </div>
            </div>

            {/* Replay Buffer */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Replay Buffer</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="Size of the experience replay buffer.">
                            Buffer Size
                        </LabelWithTooltip>
                        <Input
                            type="number"
                            step="100000"
                            value={hparams.buffer_size ?? 1_000_000}
                            onChange={(e) => onChange("buffer_size", parseInt(e.target.value))}
                        />
                    </div>
                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="Minibatch size for each gradient update.">
                            Batch Size
                        </LabelWithTooltip>
                        <Input
                            type="number"
                            step="8"
                            value={hparams.batch_size ?? 32}
                            onChange={(e) => onChange("batch_size", parseInt(e.target.value))}
                        />
                    </div>
                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="Number of steps before learning starts.">
                            Learning Starts
                        </LabelWithTooltip>
                        <Input
                            type="number"
                            step="100"
                            value={hparams.learning_starts ?? 100}
                            onChange={(e) => onChange("learning_starts", parseInt(e.target.value))}
                        />
                    </div>
                </div>
            </div>

            {/* Training */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Training</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="Update model every N steps.">
                            Train Frequency
                        </LabelWithTooltip>
                        <Input
                            type="number"
                            step="1"
                            value={hparams.train_freq ?? 4}
                            onChange={(e) => onChange("train_freq", parseInt(e.target.value))}
                        />
                    </div>
                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="Gradient steps after each rollout. -1 for auto.">
                            Gradient Steps
                        </LabelWithTooltip>
                        <Input
                            type="number"
                            step="1"
                            value={hparams.gradient_steps ?? 1}
                            onChange={(e) => onChange("gradient_steps", parseInt(e.target.value))}
                        />
                    </div>
                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="Update target network every N steps.">
                            Target Update Interval
                        </LabelWithTooltip>
                        <Input
                            type="number"
                            step="1000"
                            value={hparams.target_update_interval ?? 10_000}
                            onChange={(e) => onChange("target_update_interval", parseInt(e.target.value))}
                        />
                    </div>
                    <HyperparamSlider
                        label="Tau (Soft Update)"
                        value={hparams.tau ?? 1.0}
                        min={0} max={1} step={0.01}
                        onChange={(v) => onChange("tau", v)}
                        tooltip="Soft update coefficient. 1.0 = hard update."
                    />
                </div>
            </div>

            {/* Exploration */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Exploration (ε-greedy)</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <HyperparamSlider
                        label="Initial Epsilon"
                        value={hparams.exploration_initial_eps ?? 1.0}
                        min={0} max={1} step={0.01}
                        onChange={(v) => onChange("exploration_initial_eps", v)}
                        tooltip="Initial random action probability."
                    />
                    <HyperparamSlider
                        label="Final Epsilon"
                        value={hparams.exploration_final_eps ?? 0.05}
                        min={0} max={1} step={0.01}
                        onChange={(v) => onChange("exploration_final_eps", v)}
                        tooltip="Final random action probability."
                    />
                    <HyperparamSlider
                        label="Exploration Fraction"
                        value={hparams.exploration_fraction ?? 0.1}
                        min={0} max={1} step={0.01}
                        onChange={(v) => onChange("exploration_fraction", v)}
                        tooltip="Fraction of training over which exploration decays."
                    />
                    <HyperparamSlider
                        label="Max Grad Norm"
                        value={hparams.max_grad_norm ?? 10.0}
                        min={1} max={20} step={0.5}
                        onChange={(v) => onChange("max_grad_norm", v)}
                        tooltip="Gradient clipping threshold. DQN uses higher default."
                    />
                </div>
            </div>
        </>
    )
}
