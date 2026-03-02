import { useMemo, useEffect } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { LabelWithTooltip, HyperparamSlider, LogHyperparamSlider, DiscreteHyperparamSlider, formatCompact } from "./common"
import type { Algorithm, PPOHyperparams, A2CHyperparams, DQNHyperparams, SACHyperparams, TD3Hyperparams, DDPGHyperparams } from "@/lib/schemas"

type AnyHyperparams = Partial<PPOHyperparams & A2CHyperparams & DQNHyperparams & SACHyperparams & TD3Hyperparams & DDPGHyperparams>

interface HyperparametersCardProps {
    algorithm: Algorithm
    hparams: AnyHyperparams
    onChange?: (key: string, value: number | boolean) => void
    readOnly?: boolean
}

export function HyperparametersCard({ algorithm, hparams, onChange, readOnly = false }: HyperparametersCardProps) {
    const safeOnChange = onChange ?? (() => { })
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
                    {algorithm === "PPO" && <PPOParams hparams={hparams} onChange={safeOnChange} readOnly={readOnly} />}
                    {algorithm === "A2C" && <A2CParams hparams={hparams} onChange={safeOnChange} readOnly={readOnly} />}
                    {algorithm === "DQN" && <DQNParams hparams={hparams} onChange={safeOnChange} readOnly={readOnly} />}
                    {algorithm === "SAC" && <SACParams hparams={hparams} onChange={safeOnChange} readOnly={readOnly} />}
                    {algorithm === "TD3" && <TD3Params hparams={hparams} onChange={safeOnChange} readOnly={readOnly} />}
                    {algorithm === "DDPG" && <DDPGParams hparams={hparams} onChange={safeOnChange} readOnly={readOnly} />}
                </CardContent>
            </Card>
        </div>
    )
}

// =============================================================================
// Helpers
// =============================================================================

const PPO_N_STEPS_VALUES = [32, 64, 128, 256, 512, 1024, 2048, 4096, 8192] as const
// Shared off-policy discrete value sets (DQN, SAC, TD3, DDPG)
const BUFFER_SIZE_VALUES = [1_000, 5_000, 10_000, 50_000, 100_000, 500_000, 1_000_000, 2_000_000, 5_000_000, 10_000_000] as const
const LEARNING_STARTS_VALUES = [0, 50, 100, 200, 500, 1_000, 2_000, 5_000, 10_000, 25_000, 50_000, 100_000] as const
const GRADIENT_STEPS_VALUES = [-1, 1, 2, 4, 8, 16, 32] as const
const DQN_BATCH_SIZE_VALUES = [16, 32, 64, 128, 256, 512] as const
const DQN_TARGET_UPDATE_VALUES = [100, 500, 1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000] as const
const OFFPOLICY_BATCH_SIZE_VALUES = [32, 64, 128, 256, 512, 1024] as const
const SAC_TARGET_UPDATE_VALUES = [1, 2, 4, 8, 16, 32, 64] as const

function getValidBatchSizes(nSteps: number): number[] {
    const candidates = [4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192]
    const valid = candidates.filter(c => c <= nSteps && nSteps % c === 0)
    return valid.length > 0 ? valid : [nSteps]
}

function formatGradientSteps(n: number): string {
    return n === -1 ? "Auto" : n.toString()
}

function SectionHelp({ children }: { children: React.ReactNode }) {
    return <p className="text-xs text-muted-foreground -mt-2">{children}</p>
}

// =============================================================================
// PPO Parameters
// =============================================================================

function PPOParams({
    hparams,
    onChange,
    readOnly
}: {
    hparams: AnyHyperparams;
    onChange: (key: string, value: number | boolean) => void
    readOnly: boolean
}) {
    const nSteps = hparams.n_steps ?? 2048
    const validBatchSizes = useMemo(() => getValidBatchSizes(nSteps), [nSteps])

    // Auto-correct batch_size when n_steps changes and current value becomes invalid
    const batchSize = hparams.batch_size ?? 64
    useEffect(() => {
        if (!validBatchSizes.includes(batchSize)) {
            const nearest = validBatchSizes.reduce((best, v) =>
                Math.abs(v - batchSize) < Math.abs(best - batchSize) ? v : best
            , validBatchSizes[0])
            onChange("batch_size", nearest)
        }
    }, [validBatchSizes, batchSize, onChange])

    return (
        <>
            {/* Optimization */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Optimization</h4>
                <SectionHelp>Core learning parameters. These control how fast and how far into the future the agent learns.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8 bg-secondary/20 p-4">
                    <LogHyperparamSlider
                        label="Learning Rate"
                        value={hparams.learning_rate ?? 0.0003}
                        min={1e-5} max={1e-2}
                        onChange={(v) => onChange("learning_rate", v)}
                        tooltip="Step size for gradient descent. Recommended: 1e-4 to 5e-4. Use lower values (3e-5 to 1e-4) for image-based observations. Too high causes instability, too low is slow."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Gamma (Discount Factor)"
                        value={hparams.gamma ?? 0.99}
                        min={0.8} max={0.9999} step={0.0001}
                        onChange={(v) => onChange("gamma", v)}
                        tooltip="How much the agent values future vs immediate rewards. Recommended: 0.99 for long games like Pokemon, 0.9-0.95 for short episodes. Higher = more farsighted but harder to train."
                        formatValue={(v) => v.toFixed(4)}
                        readOnly={readOnly}
                    />
                </div>
            </div>

            {/* Policy Updates */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Policy Updates</h4>
                <SectionHelp>Control how aggressively the policy changes each update. Overly aggressive updates destabilize training.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <HyperparamSlider
                        label="Clip Range"
                        value={hparams.clip_range ?? 0.2}
                        min={0.05} max={0.5} step={0.01}
                        onChange={(v) => onChange("clip_range", v)}
                        tooltip="PPO's signature parameter — limits how much the policy can change per update. Recommended: 0.1-0.3. Default 0.2 works well for most tasks. Lower = more conservative, stable updates."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Entropy Coeff"
                        value={hparams.ent_coef ?? 0.0}
                        min={0.0} max={0.1} step={0.001}
                        onChange={(v) => onChange("ent_coef", v)}
                        tooltip="Bonus for exploring diverse actions. Recommended: 0.0 for most cases. Increase to 0.01-0.05 if the agent converges to a single repeated action too early. Too high prevents learning a focused strategy."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Value Function Coeff"
                        value={hparams.vf_coef ?? 0.5}
                        min={0.1} max={1.0} step={0.1}
                        onChange={(v) => onChange("vf_coef", v)}
                        tooltip="Weight of value function loss relative to policy loss. Recommended: 0.25-1.0. Default 0.5. Reduce if value loss dominates and policy stops improving."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Max Grad Norm"
                        value={hparams.max_grad_norm ?? 0.5}
                        min={0.1} max={5.0} step={0.1}
                        onChange={(v) => onChange("max_grad_norm", v)}
                        tooltip="Clips gradients to prevent exploding updates. Recommended: 0.3-1.0. Default 0.5. Increase if training is too slow, decrease if you see NaN losses."
                    />
                </div>
            </div>

            {/* Rollout Config */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Rollout Configuration</h4>
                <SectionHelp>How much experience is collected before each update. Larger rollouts = more stable but slower iteration.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <DiscreteHyperparamSlider
                        label="N Steps (Rollout Length)"
                        value={nSteps}
                        values={PPO_N_STEPS_VALUES}
                        onChange={(v) => onChange("n_steps", v)}
                        tooltip="Steps collected per environment before each update. Recommended: 1024-4096 for games. Default 2048. More steps = less variance but slower learning cycles. Must be large enough to capture meaningful reward signals."
                        readOnly={readOnly}
                    />
                    <DiscreteHyperparamSlider
                        label="Batch Size"
                        value={batchSize}
                        values={validBatchSizes}
                        onChange={(v) => onChange("batch_size", v)}
                        tooltip="Minibatch size for gradient updates. Must divide N Steps evenly. Recommended: 64-256. Larger = smoother gradients, smaller = more noise (can help escape local optima). Valid options update automatically when N Steps changes."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="N Epochs"
                        value={hparams.n_epochs ?? 10}
                        min={1} max={50} step={1}
                        onChange={(v) => onChange("n_epochs", v)}
                        tooltip="How many times to reuse each rollout buffer for training. Recommended: 3-30. Default 10. More epochs = better data efficiency but risks overfitting to the current batch. Reduce if training becomes unstable."
                    />
                    <HyperparamSlider
                        label="GAE Lambda"
                        value={hparams.gae_lambda ?? 0.95}
                        min={0.8} max={1.0} step={0.01}
                        onChange={(v) => onChange("gae_lambda", v)}
                        tooltip="Generalized Advantage Estimation bias-variance tradeoff. Recommended: 0.9-0.99. Default 0.95. Lower = more biased but less noisy advantage estimates. 1.0 = Monte Carlo returns (high variance)."
                    />
                </div>
            </div>

            {/* Advanced */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Advanced</h4>
                <SectionHelp>Toggle features that affect training stability and exploration behavior.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="flex items-center justify-between p-4 bg-secondary/20">
                        <LabelWithTooltip tooltip="Normalize advantages to zero mean and unit variance before each update. Recommended: ON. Almost always helps stability. Only disable for debugging.">
                            Normalize Advantage
                        </LabelWithTooltip>
                        <Switch
                            checked={hparams.normalize_advantage ?? true}
                            onCheckedChange={(v) => onChange("normalize_advantage", v)}
                        />
                    </div>
                    <div className="flex items-center justify-between p-4 bg-secondary/20">
                        <LabelWithTooltip tooltip="Generalized State-Dependent Exploration — replaces random noise with learned exploration. Recommended: OFF for discrete actions (retro games). Only useful for continuous action spaces.">
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

function A2CParams({
    hparams,
    onChange,
    readOnly
}: {
    hparams: AnyHyperparams;
    onChange: (key: string, value: number | boolean) => void
    readOnly: boolean
}) {
    return (
        <>
            {/* Optimization */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Optimization</h4>
                <SectionHelp>A2C uses higher learning rates than PPO since it doesn't have clipping to constrain updates.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8 bg-secondary/20 p-4">
                    <LogHyperparamSlider
                        label="Learning Rate"
                        value={hparams.learning_rate ?? 0.0007}
                        min={1e-5} max={1e-2}
                        onChange={(v) => onChange("learning_rate", v)}
                        tooltip="Step size for gradient descent. Recommended: 3e-4 to 1e-3. Default 7e-4 (higher than PPO). A2C is more sensitive to this — too high causes divergence, too low wastes compute."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Gamma (Discount Factor)"
                        value={hparams.gamma ?? 0.99}
                        min={0.8} max={0.9999} step={0.0001}
                        onChange={(v) => onChange("gamma", v)}
                        tooltip="How much the agent values future vs immediate rewards. Recommended: 0.99 for long games, 0.9-0.95 for short episodes. Same tradeoffs as PPO."
                        formatValue={(v) => v.toFixed(4)}
                        readOnly={readOnly}
                    />
                </div>
            </div>

            {/* Policy Updates */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Policy Updates</h4>
                <SectionHelp>A2C lacks PPO's clipping, so these coefficients are the main levers for training stability.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <HyperparamSlider
                        label="Entropy Coeff"
                        value={hparams.ent_coef ?? 0.0}
                        min={0.0} max={0.1} step={0.001}
                        onChange={(v) => onChange("ent_coef", v)}
                        tooltip="Bonus for diverse actions. Recommended: 0.0-0.01. A2C benefits more from entropy than PPO because it lacks clipping. Try 0.01 if the agent collapses to a single action."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Value Function Coeff"
                        value={hparams.vf_coef ?? 0.5}
                        min={0.1} max={1.0} step={0.1}
                        onChange={(v) => onChange("vf_coef", v)}
                        tooltip="Weight of value function loss. Recommended: 0.25-1.0. Default 0.5. If value loss dominates training, try lowering this."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Max Grad Norm"
                        value={hparams.max_grad_norm ?? 0.5}
                        min={0.1} max={5.0} step={0.1}
                        onChange={(v) => onChange("max_grad_norm", v)}
                        tooltip="Gradient clipping threshold. Recommended: 0.3-1.0. Default 0.5. Critical for A2C stability since it doesn't have PPO's clipping."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="GAE Lambda"
                        value={hparams.gae_lambda ?? 1.0}
                        min={0.8} max={1.0} step={0.01}
                        onChange={(v) => onChange("gae_lambda", v)}
                        tooltip="GAE bias-variance tradeoff. Recommended: 0.9-1.0. Default 1.0 (pure Monte Carlo returns, no bias reduction). Try 0.95 if training is noisy — same as PPO default."
                        readOnly={readOnly}
                    />
                </div>
            </div>

            {/* Rollout Config */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Rollout Configuration</h4>
                <SectionHelp>A2C typically uses much smaller rollouts than PPO, updating more frequently with less data per step.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <HyperparamSlider
                        label="N Steps"
                        value={hparams.n_steps ?? 5}
                        min={1} max={100} step={1}
                        onChange={(v) => onChange("n_steps", v)}
                        tooltip="Steps per environment before each update. Recommended: 5-20. Default 5 (much smaller than PPO's 2048). A2C works best with frequent small updates. Increase if training is too noisy."
                        readOnly={readOnly}
                    />
                    <LogHyperparamSlider
                        label="RMSProp Epsilon"
                        value={hparams.rms_prop_eps ?? 1e-5}
                        min={1e-8} max={1e-3}
                        onChange={(v) => onChange("rms_prop_eps", v)}
                        tooltip="Numerical stability constant for RMSProp optimizer. Recommended: 1e-5 to 1e-4. Default 1e-5. Rarely needs tuning unless you see NaN values."
                        readOnly={readOnly}
                    />
                </div>
            </div>

            {/* Advanced */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Advanced</h4>
                <SectionHelp>Optimizer choice and exploration features. RMSProp is standard for A2C.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="flex items-center justify-between p-4 bg-secondary/20">
                        <LabelWithTooltip tooltip="Use RMSprop optimizer instead of Adam. Recommended: ON. A2C was designed with RMSprop. Adam can work but may require different learning rates.">
                            Use RMSprop
                        </LabelWithTooltip>
                        <Switch
                            checked={hparams.use_rms_prop ?? true}
                            onCheckedChange={(v) => onChange("use_rms_prop", v)}
                            disabled={readOnly}
                        />
                    </div>
                    <div className="flex items-center justify-between p-4 bg-secondary/20">
                        <LabelWithTooltip tooltip="Normalize advantages to zero mean/unit variance. Recommended: OFF for A2C (default). Can help in some environments — experiment to see.">
                            Normalize Advantage
                        </LabelWithTooltip>
                        <Switch
                            checked={hparams.normalize_advantage ?? false}
                            onCheckedChange={(v) => onChange("normalize_advantage", v)}
                            disabled={readOnly}
                        />
                    </div>
                    <div className="flex items-center justify-between p-4 bg-secondary/20">
                        <LabelWithTooltip tooltip="Generalized State-Dependent Exploration. Recommended: OFF for discrete actions (retro games). Only useful for continuous action spaces.">
                            Use SDE
                        </LabelWithTooltip>
                        <Switch
                            checked={hparams.use_sde ?? false}
                            onCheckedChange={(v) => onChange("use_sde", v)}
                            disabled={readOnly}
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

function DQNParams({ hparams, onChange, readOnly }: { hparams: AnyHyperparams; onChange: (key: string, value: number | boolean) => void; readOnly?: boolean }) {
    return (
        <>
            {/* Optimization */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Optimization</h4>
                <SectionHelp>DQN learns Q-values (expected reward per action) and picks the best one. Lower learning rates than policy gradient methods.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8 bg-secondary/20 p-4">
                    <LogHyperparamSlider
                        label="Learning Rate"
                        value={hparams.learning_rate ?? 0.0001}
                        min={1e-5} max={1e-2}
                        onChange={(v) => onChange("learning_rate", v)}
                        tooltip="Step size for gradient descent. Recommended: 1e-4 to 5e-4. Default 1e-4. DQN typically uses lower rates than PPO/A2C. Too high causes Q-value divergence."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Gamma (Discount Factor)"
                        value={hparams.gamma ?? 0.99}
                        min={0.8} max={0.9999} step={0.0001}
                        onChange={(v) => onChange("gamma", v)}
                        tooltip="Discount for future rewards. Recommended: 0.99 for most games. Lower (0.95) for short episodes. Critical for Q-learning — affects the scale of Q-values directly."
                        formatValue={(v) => v.toFixed(4)}
                        readOnly={readOnly}
                    />
                </div>
            </div>

            {/* Replay Buffer */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Replay Buffer</h4>
                <SectionHelp>DQN's key advantage: stores past experiences and replays them for training. Larger buffer = more diverse training data but more memory.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <DiscreteHyperparamSlider
                        label="Buffer Size"
                        value={hparams.buffer_size ?? 1_000_000}
                        values={BUFFER_SIZE_VALUES}
                        onChange={(v) => onChange("buffer_size", v)}
                        tooltip="Maximum experiences stored for replay. Recommended: 100K-1M. Default 1M. Larger buffers give more diverse training samples but use more RAM. For image observations, 100K-500K may be needed to fit in memory."
                        formatValue={formatCompact}
                        readOnly={readOnly}
                    />
                    <DiscreteHyperparamSlider
                        label="Batch Size"
                        value={hparams.batch_size ?? 32}
                        values={DQN_BATCH_SIZE_VALUES}
                        onChange={(v) => onChange("batch_size", v)}
                        tooltip="Experiences sampled per gradient update. Recommended: 32-128. Default 32. Larger batches give smoother gradients but slower updates. 64-128 can improve stability."
                        readOnly={readOnly}
                    />
                    <DiscreteHyperparamSlider
                        label="Learning Starts"
                        value={hparams.learning_starts ?? 100}
                        values={LEARNING_STARTS_VALUES}
                        onChange={(v) => onChange("learning_starts", v)}
                        tooltip="Random steps collected before training begins. Recommended: 1K-50K. Default 100. Higher values fill the buffer with diverse experiences first, preventing early overfitting. Use 10K-50K for complex environments."
                        formatValue={formatCompact}
                        readOnly={readOnly}
                    />
                </div>
            </div>

            {/* Training */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Training</h4>
                <SectionHelp>Controls how often updates happen and how the target network tracks the main network.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <HyperparamSlider
                        label="Train Frequency"
                        value={hparams.train_freq ?? 4}
                        min={1} max={32} step={1}
                        onChange={(v) => onChange("train_freq", v)}
                        tooltip="Gradient update every N environment steps. Recommended: 1-8. Default 4. Lower = more updates per step (slower but more thorough). 1 is common for Atari-style games."
                        readOnly={readOnly}
                    />
                    <DiscreteHyperparamSlider
                        label="Gradient Steps"
                        value={hparams.gradient_steps ?? 1}
                        values={GRADIENT_STEPS_VALUES}
                        onChange={(v) => onChange("gradient_steps", v)}
                        tooltip="Gradient updates per training step. Recommended: 1. Auto (-1) matches train_freq. Higher values do more updates per data collection but can cause overfitting to replay buffer."
                        formatValue={formatGradientSteps}
                        readOnly={readOnly}
                    />
                    <DiscreteHyperparamSlider
                        label="Target Update Interval"
                        value={hparams.target_update_interval ?? 10_000}
                        values={DQN_TARGET_UPDATE_VALUES}
                        onChange={(v) => onChange("target_update_interval", v)}
                        tooltip="Steps between hard target network copies. Recommended: 1K-10K. Default 10K. More frequent updates track the latest Q-values but can destabilize learning. Works with Tau — when Tau=1.0 this is a hard copy."
                        formatValue={formatCompact}
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Tau (Soft Update)"
                        value={hparams.tau ?? 1.0}
                        min={0} max={1} step={0.01}
                        onChange={(v) => onChange("tau", v)}
                        tooltip="Target network update blending. Recommended: 1.0 (hard update) or 0.005-0.01 (soft update). Default 1.0 = full copy at each target_update_interval. Soft updates (small tau) are smoother but need interval=1."
                        readOnly={readOnly}
                    />
                </div>
            </div>

            {/* Exploration */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Exploration (e-greedy)</h4>
                <SectionHelp>DQN explores by taking random actions with probability epsilon, decaying from initial to final over a fraction of training.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <HyperparamSlider
                        label="Initial Epsilon"
                        value={hparams.exploration_initial_eps ?? 1.0}
                        min={0} max={1} step={0.01}
                        onChange={(v) => onChange("exploration_initial_eps", v)}
                        tooltip="Starting random action probability. Recommended: 1.0 (always). Ensures full exploration at the start. Only lower this if resuming a pre-trained model."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Final Epsilon"
                        value={hparams.exploration_final_eps ?? 0.05}
                        min={0} max={1} step={0.01}
                        onChange={(v) => onChange("exploration_final_eps", v)}
                        tooltip="Minimum random action probability after decay. Recommended: 0.01-0.1. Default 0.05 (5% random actions). Some residual randomness prevents the agent from getting permanently stuck."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Exploration Fraction"
                        value={hparams.exploration_fraction ?? 0.1}
                        min={0} max={1} step={0.01}
                        onChange={(v) => onChange("exploration_fraction", v)}
                        tooltip="Fraction of total training over which epsilon decays. Recommended: 0.05-0.3. Default 0.1 (first 10% of training). Longer exploration for complex environments with sparse rewards."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Max Grad Norm"
                        value={hparams.max_grad_norm ?? 10.0}
                        min={1} max={20} step={0.5}
                        onChange={(v) => onChange("max_grad_norm", v)}
                        tooltip="Gradient clipping threshold. Recommended: 5-15. Default 10 (higher than PPO/A2C). DQN Q-values can have larger gradients. Reduce if you see loss spikes."
                        readOnly={readOnly}
                    />
                </div>
            </div>
        </>
    )
}

// =============================================================================
// SAC Parameters (Soft Actor-Critic) — continuous action spaces only
// =============================================================================

function SACParams({ hparams, onChange, readOnly }: { hparams: AnyHyperparams; onChange: (key: string, value: number | boolean) => void; readOnly?: boolean }) {
    const entCoefAuto = hparams.ent_coef_auto ?? true
    const targetEntropyAuto = hparams.target_entropy_auto ?? true

    return (
        <>
            {/* Optimization */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Optimization</h4>
                <SectionHelp>SAC uses one learning rate for all three networks (actor, critic, entropy). Generally stable across a wide range.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8 bg-secondary/20 p-4">
                    <LogHyperparamSlider
                        label="Learning Rate"
                        value={hparams.learning_rate ?? 0.0003}
                        min={1e-5} max={1e-2}
                        onChange={(v) => onChange("learning_rate", v)}
                        tooltip="Shared Adam learning rate for actor, critic, and entropy networks. Recommended: 1e-4 to 1e-3. Default 3e-4. SAC is relatively robust to this value."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Gamma (Discount Factor)"
                        value={hparams.gamma ?? 0.99}
                        min={0.8} max={0.9999} step={0.0001}
                        onChange={(v) => onChange("gamma", v)}
                        tooltip="Discount for future rewards. Recommended: 0.99 for most tasks. Same principles as other algorithms — higher for long-horizon tasks."
                        formatValue={(v) => v.toFixed(4)}
                        readOnly={readOnly}
                    />
                </div>
            </div>

            {/* Replay Buffer */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Replay Buffer</h4>
                <SectionHelp>Off-policy replay buffer. SAC's entropy bonus provides built-in exploration, so the buffer fills with diverse data naturally.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <DiscreteHyperparamSlider
                        label="Buffer Size"
                        value={hparams.buffer_size ?? 1_000_000}
                        values={BUFFER_SIZE_VALUES}
                        onChange={(v) => onChange("buffer_size", v)}
                        tooltip="Maximum stored experiences. Recommended: 100K-1M. Default 1M. Larger is better for sample efficiency but uses more memory."
                        formatValue={formatCompact}
                        readOnly={readOnly}
                    />
                    <DiscreteHyperparamSlider
                        label="Batch Size"
                        value={hparams.batch_size ?? 256}
                        values={OFFPOLICY_BATCH_SIZE_VALUES}
                        onChange={(v) => onChange("batch_size", v)}
                        tooltip="Experiences per gradient update. Recommended: 128-512. Default 256. SAC uses larger batches than DQN. Bigger = more stable but slower per update."
                        readOnly={readOnly}
                    />
                    <DiscreteHyperparamSlider
                        label="Learning Starts"
                        value={hparams.learning_starts ?? 100}
                        values={LEARNING_STARTS_VALUES}
                        onChange={(v) => onChange("learning_starts", v)}
                        tooltip="Random steps before training. Recommended: 100-10K. Default 100. Can be lower than DQN since SAC's entropy provides exploration. Increase for complex environments."
                        formatValue={formatCompact}
                        readOnly={readOnly}
                    />
                </div>
            </div>

            {/* Training */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Training</h4>
                <SectionHelp>SAC typically trains every step with soft target updates — the most data-efficient configuration.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <HyperparamSlider
                        label="Train Frequency"
                        value={hparams.train_freq ?? 1}
                        min={1} max={32} step={1}
                        onChange={(v) => onChange("train_freq", v)}
                        tooltip="Gradient update every N steps. Recommended: 1 (every step). Default 1. This is standard for SAC and maximizes sample efficiency. Increase only if compute-limited."
                        readOnly={readOnly}
                    />
                    <DiscreteHyperparamSlider
                        label="Gradient Steps"
                        value={hparams.gradient_steps ?? 1}
                        values={GRADIENT_STEPS_VALUES}
                        onChange={(v) => onChange("gradient_steps", v)}
                        tooltip="Gradient updates per train step. Recommended: 1. Auto (-1) matches train_freq. Higher values can accelerate learning early but risk instability."
                        formatValue={formatGradientSteps}
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Tau (Soft Update)"
                        value={hparams.tau ?? 0.005}
                        min={0.001} max={0.1} step={0.001}
                        onChange={(v) => onChange("tau", v)}
                        tooltip="Polyak averaging for target networks: target = tau*main + (1-tau)*target. Recommended: 0.001-0.02. Default 0.005. Smaller = slower but more stable target tracking."
                        readOnly={readOnly}
                    />
                    <DiscreteHyperparamSlider
                        label="Target Update Interval"
                        value={hparams.target_update_interval ?? 1}
                        values={SAC_TARGET_UPDATE_VALUES}
                        onChange={(v) => onChange("target_update_interval", v)}
                        tooltip="Steps between target network updates. Recommended: 1 (every step). Default 1. With soft updates (small tau), updating every step is standard. Only increase if tau is large."
                        readOnly={readOnly}
                    />
                </div>
            </div>

            {/* Entropy */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Entropy Regularization</h4>
                <SectionHelp>SAC's key innovation: maximizes reward AND action entropy. Auto-tuning learns the optimal exploration-exploitation balance.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                        <div className="flex items-center justify-between p-4 bg-secondary/20">
                            <LabelWithTooltip tooltip="Automatically learn the entropy coefficient (temperature alpha). Recommended: ON. This is SAC's key feature — it adapts exploration throughout training. Only disable for debugging or if you know the optimal value.">
                                Auto Entropy Tuning
                            </LabelWithTooltip>
                            <Switch
                                checked={entCoefAuto}
                                onCheckedChange={(v) => onChange("ent_coef_auto", v)}
                                disabled={readOnly}
                            />
                        </div>
                        {!entCoefAuto && (
                            <HyperparamSlider
                                label="Entropy Coeff"
                                value={hparams.ent_coef ?? 0.1}
                                min={0.001} max={1.0} step={0.01}
                                onChange={(v) => onChange("ent_coef", v)}
                                tooltip="Fixed entropy weight when auto-tuning is off. Recommended: 0.05-0.2 for most tasks. Higher = more exploration, lower = more exploitation. Auto mode typically converges to 0.01-0.2."
                                readOnly={readOnly}
                            />
                        )}
                    </div>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between p-4 bg-secondary/20">
                            <LabelWithTooltip tooltip="Automatically compute target entropy as -dim(action_space). Recommended: ON. The heuristic works well for most environments. Only disable to override for unusual action spaces.">
                                Auto Target Entropy
                            </LabelWithTooltip>
                            <Switch
                                checked={targetEntropyAuto}
                                onCheckedChange={(v) => onChange("target_entropy_auto", v)}
                                disabled={readOnly}
                            />
                        </div>
                        {!targetEntropyAuto && (
                            <HyperparamSlider
                                label="Target Entropy"
                                value={hparams.target_entropy ?? -1.0}
                                min={-10} max={0} step={0.1}
                                onChange={(v) => onChange("target_entropy", v)}
                                tooltip="Target entropy for alpha tuning. Recommended: -dim(action_space) (auto default). More negative = less exploration. Typical values: -1 to -6 depending on action dimensionality."
                                readOnly={readOnly}
                            />
                        )}
                    </div>
                </div>
            </div>

            {/* Advanced */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Advanced</h4>
                <SectionHelp>Alternative exploration methods. SAC's entropy bonus usually provides sufficient exploration without SDE.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="flex items-center justify-between p-4 bg-secondary/20">
                        <LabelWithTooltip tooltip="Generalized State-Dependent Exploration — learned exploration noise correlated with state. Recommended: OFF for most cases. SAC's entropy already handles exploration. Enable for locomotion tasks where coordinated noise helps.">
                            Use SDE
                        </LabelWithTooltip>
                        <Switch
                            checked={hparams.use_sde ?? false}
                            onCheckedChange={(v) => onChange("use_sde", v)}
                            disabled={readOnly}
                        />
                    </div>
                    <div className="flex items-center justify-between p-4 bg-secondary/20">
                        <LabelWithTooltip tooltip="Use gSDE during the warmup phase (before learning_starts). Recommended: OFF. Only relevant if Use SDE is ON. Adds structured exploration to the initial random data collection.">
                            Use SDE at Warmup
                        </LabelWithTooltip>
                        <Switch
                            checked={hparams.use_sde_at_warmup ?? false}
                            onCheckedChange={(v) => onChange("use_sde_at_warmup", v)}
                            disabled={readOnly}
                        />
                    </div>
                </div>
            </div>
        </>
    )
}

// =============================================================================
// TD3 Parameters (Twin Delayed DDPG) — continuous action spaces only
// =============================================================================

function TD3Params({ hparams, onChange, readOnly }: { hparams: AnyHyperparams; onChange: (key: string, value: number | boolean) => void; readOnly?: boolean }) {
    return (
        <>
            {/* Optimization */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Optimization</h4>
                <SectionHelp>TD3 uses a higher default learning rate than SAC. It has no entropy tuning — exploration comes from action noise.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8 bg-secondary/20 p-4">
                    <LogHyperparamSlider
                        label="Learning Rate"
                        value={hparams.learning_rate ?? 0.001}
                        min={1e-5} max={1e-2}
                        onChange={(v) => onChange("learning_rate", v)}
                        tooltip="Adam learning rate for actor and critic networks. Recommended: 5e-4 to 3e-3. Default 1e-3 (higher than SAC). TD3's delayed updates tolerate higher rates."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Gamma (Discount Factor)"
                        value={hparams.gamma ?? 0.99}
                        min={0.8} max={0.9999} step={0.0001}
                        onChange={(v) => onChange("gamma", v)}
                        tooltip="Discount for future rewards. Recommended: 0.99 for most continuous control tasks. Same tradeoffs as other algorithms."
                        formatValue={(v) => v.toFixed(4)}
                        readOnly={readOnly}
                    />
                </div>
            </div>

            {/* Replay Buffer */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Replay Buffer</h4>
                <SectionHelp>Same off-policy replay structure as DQN and SAC. Buffer diversity depends on action noise quality.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <DiscreteHyperparamSlider
                        label="Buffer Size"
                        value={hparams.buffer_size ?? 1_000_000}
                        values={BUFFER_SIZE_VALUES}
                        onChange={(v) => onChange("buffer_size", v)}
                        tooltip="Maximum stored experiences. Recommended: 100K-1M. Default 1M. Same as SAC — larger is better for diversity."
                        formatValue={formatCompact}
                        readOnly={readOnly}
                    />
                    <DiscreteHyperparamSlider
                        label="Batch Size"
                        value={hparams.batch_size ?? 256}
                        values={OFFPOLICY_BATCH_SIZE_VALUES}
                        onChange={(v) => onChange("batch_size", v)}
                        tooltip="Experiences per gradient update. Recommended: 128-512. Default 256. Matches SAC. Larger batches help twin critics converge consistently."
                        readOnly={readOnly}
                    />
                    <DiscreteHyperparamSlider
                        label="Learning Starts"
                        value={hparams.learning_starts ?? 100}
                        values={LEARNING_STARTS_VALUES}
                        onChange={(v) => onChange("learning_starts", v)}
                        tooltip="Random steps before training. Recommended: 100-10K. Default 100. TD3 relies on action noise for exploration, so some initial random data helps."
                        formatValue={formatCompact}
                        readOnly={readOnly}
                    />
                </div>
            </div>

            {/* Training */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Training</h4>
                <SectionHelp>Standard off-policy training loop. TD3's innovations are in the policy smoothing section below.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <HyperparamSlider
                        label="Train Frequency"
                        value={hparams.train_freq ?? 1}
                        min={1} max={32} step={1}
                        onChange={(v) => onChange("train_freq", v)}
                        tooltip="Gradient update every N steps. Recommended: 1 (every step). Default 1. Standard for continuous control off-policy methods."
                        readOnly={readOnly}
                    />
                    <DiscreteHyperparamSlider
                        label="Gradient Steps"
                        value={hparams.gradient_steps ?? 1}
                        values={GRADIENT_STEPS_VALUES}
                        onChange={(v) => onChange("gradient_steps", v)}
                        tooltip="Gradient updates per train step. Recommended: 1. Auto (-1) matches train_freq. Keep at 1 for stable training."
                        formatValue={formatGradientSteps}
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Tau (Soft Update)"
                        value={hparams.tau ?? 0.005}
                        min={0.001} max={0.1} step={0.001}
                        onChange={(v) => onChange("tau", v)}
                        tooltip="Polyak averaging for target networks. Recommended: 0.001-0.02. Default 0.005. Same as SAC — smaller is more stable."
                        readOnly={readOnly}
                    />
                </div>
            </div>

            {/* Policy Smoothing — TD3's key innovations */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Policy Smoothing (TD3 Innovations)</h4>
                <SectionHelp>TD3's three tricks over DDPG: twin critics (automatic), delayed actor updates, and target action smoothing.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <HyperparamSlider
                        label="Policy Delay"
                        value={hparams.policy_delay ?? 2}
                        min={1} max={10} step={1}
                        onChange={(v) => onChange("policy_delay", v)}
                        tooltip="Update actor (policy) every N critic updates. Recommended: 2 (original paper). Delays let the critic converge before the actor follows, reducing overestimation. 1 = same as DDPG (no delay)."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Target Policy Noise"
                        value={hparams.target_policy_noise ?? 0.2}
                        min={0} max={1} step={0.01}
                        onChange={(v) => onChange("target_policy_noise", v)}
                        tooltip="Gaussian noise std added to target actions. Recommended: 0.1-0.5. Default 0.2. Smooths the Q-function to prevent the actor from exploiting narrow peaks. Higher = more smoothing."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Target Noise Clip"
                        value={hparams.target_noise_clip ?? 0.5}
                        min={0} max={2} step={0.05}
                        onChange={(v) => onChange("target_noise_clip", v)}
                        tooltip="Clips target policy noise to this range [-clip, +clip]. Recommended: 0.3-1.0. Default 0.5. Should be larger than target_policy_noise. Prevents extreme noise from corrupting target values."
                        readOnly={readOnly}
                    />
                </div>
            </div>
        </>
    )
}

// =============================================================================
// DDPG Parameters (Deep Deterministic Policy Gradient) — continuous only
// =============================================================================

function DDPGParams({ hparams, onChange, readOnly }: { hparams: AnyHyperparams; onChange: (key: string, value: number | boolean) => void; readOnly?: boolean }) {
    return (
        <>
            {/* Optimization */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Optimization</h4>
                <SectionHelp>DDPG is TD3 without the stability improvements. Consider using TD3 or SAC instead for better results.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8 bg-secondary/20 p-4">
                    <LogHyperparamSlider
                        label="Learning Rate"
                        value={hparams.learning_rate ?? 0.001}
                        min={1e-5} max={1e-2}
                        onChange={(v) => onChange("learning_rate", v)}
                        tooltip="Adam learning rate. Recommended: 5e-4 to 3e-3. Default 1e-3. Same as TD3. DDPG can be more sensitive to this value since it lacks TD3's stabilization tricks."
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Gamma (Discount Factor)"
                        value={hparams.gamma ?? 0.99}
                        min={0.8} max={0.9999} step={0.0001}
                        onChange={(v) => onChange("gamma", v)}
                        tooltip="Discount for future rewards. Recommended: 0.99. Q-value overestimation (DDPG's weakness) gets worse with higher gamma."
                        formatValue={(v) => v.toFixed(4)}
                        readOnly={readOnly}
                    />
                </div>
            </div>

            {/* Replay Buffer */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Replay Buffer</h4>
                <SectionHelp>DDPG relies heavily on replay buffer diversity since its deterministic policy doesn't explore on its own.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <DiscreteHyperparamSlider
                        label="Buffer Size"
                        value={hparams.buffer_size ?? 1_000_000}
                        values={BUFFER_SIZE_VALUES}
                        onChange={(v) => onChange("buffer_size", v)}
                        tooltip="Maximum stored experiences. Recommended: 100K-1M. Default 1M. A diverse buffer is critical for DDPG since it has no built-in exploration mechanism."
                        formatValue={formatCompact}
                        readOnly={readOnly}
                    />
                    <DiscreteHyperparamSlider
                        label="Batch Size"
                        value={hparams.batch_size ?? 256}
                        values={OFFPOLICY_BATCH_SIZE_VALUES}
                        onChange={(v) => onChange("batch_size", v)}
                        tooltip="Experiences per gradient update. Recommended: 64-256. Default 256. Can use smaller batches than SAC/TD3 since there's only one critic."
                        readOnly={readOnly}
                    />
                    <DiscreteHyperparamSlider
                        label="Learning Starts"
                        value={hparams.learning_starts ?? 100}
                        values={LEARNING_STARTS_VALUES}
                        onChange={(v) => onChange("learning_starts", v)}
                        tooltip="Random steps before training. Recommended: 1K-10K. Consider higher values than SAC/TD3 to build a diverse initial buffer, since DDPG's deterministic policy limits exploration."
                        formatValue={formatCompact}
                        readOnly={readOnly}
                    />
                </div>
            </div>

            {/* Training */}
            <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Training</h4>
                <SectionHelp>Same soft-update training loop as SAC/TD3. DDPG is simpler — no twin critics, no delayed updates, no target smoothing.</SectionHelp>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <HyperparamSlider
                        label="Train Frequency"
                        value={hparams.train_freq ?? 1}
                        min={1} max={32} step={1}
                        onChange={(v) => onChange("train_freq", v)}
                        tooltip="Gradient update every N steps. Recommended: 1. Default 1. Standard for off-policy continuous control."
                        readOnly={readOnly}
                    />
                    <DiscreteHyperparamSlider
                        label="Gradient Steps"
                        value={hparams.gradient_steps ?? 1}
                        values={GRADIENT_STEPS_VALUES}
                        onChange={(v) => onChange("gradient_steps", v)}
                        tooltip="Gradient updates per train step. Recommended: 1. Keep low — DDPG is already prone to overestimation, and more gradient steps can amplify this."
                        formatValue={formatGradientSteps}
                        readOnly={readOnly}
                    />
                    <HyperparamSlider
                        label="Tau (Soft Update)"
                        value={hparams.tau ?? 0.005}
                        min={0.001} max={0.1} step={0.001}
                        onChange={(v) => onChange("tau", v)}
                        tooltip="Polyak averaging for target network. Recommended: 0.001-0.02. Default 0.005. Critical for DDPG stability since it lacks TD3's other stabilization tricks. Err on the lower side."
                        readOnly={readOnly}
                    />
                </div>
            </div>
        </>
    )
}
