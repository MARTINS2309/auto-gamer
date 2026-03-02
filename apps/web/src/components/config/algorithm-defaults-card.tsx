import { Card, CardContent } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle, CheckCircle2, Star } from "lucide-react"
import type { Algorithm, ConfigUpdate } from "@/lib/schemas"

// =============================================================================
// Algorithm metadata — strengths, weaknesses, action space support
// =============================================================================

interface AlgorithmInfo {
    name: string
    fullName: string
    type: "on-policy" | "off-policy"
    actionSpaces: ("discrete" | "continuous" | "multi_discrete" | "multi_binary")[]
    description: string
    strengths: string[]
    weaknesses: string[]
    recommendation?: string
}

const ALGORITHM_INFO: Record<Algorithm, AlgorithmInfo> = {
    PPO: {
        name: "PPO",
        fullName: "Proximal Policy Optimization",
        type: "on-policy",
        actionSpaces: ["discrete", "continuous", "multi_discrete", "multi_binary"],
        description: "The most versatile RL algorithm. Clips policy updates to prevent large destabilizing changes. Works with all action space types and scales well with parallel environments.",
        strengths: [
            "Works with all action space types",
            "Stable training with good defaults",
            "Scales well with parallel environments",
        ],
        weaknesses: [
            "Less sample-efficient than off-policy methods",
            "Requires many environment interactions",
        ],
        recommendation: "Recommended starting point for most tasks",
    },
    A2C: {
        name: "A2C",
        fullName: "Advantage Actor Critic",
        type: "on-policy",
        actionSpaces: ["discrete", "continuous", "multi_discrete", "multi_binary"],
        description: "Synchronous variant of A3C. Simpler and faster per-step than PPO but typically less stable and more sensitive to hyperparameters.",
        strengths: [
            "Fast wall-clock training time",
            "Works with all action space types",
            "Simple implementation",
        ],
        weaknesses: [
            "Less stable than PPO",
            "Very sensitive to hyperparameters",
            "Often inferior final performance",
        ],
    },
    DQN: {
        name: "DQN",
        fullName: "Deep Q-Network",
        type: "off-policy",
        actionSpaces: ["discrete"],
        description: "Classic value-based algorithm with experience replay buffer. Most sample-efficient option for discrete action spaces like retro games.",
        strengths: [
            "Most sample-efficient for discrete actions",
            "Experience replay improves data reuse",
            "Well-understood and battle-tested",
        ],
        weaknesses: [
            "Discrete actions only",
            "Slower wall-clock than PPO with parallel envs",
            "Can overestimate Q-values",
        ],
    },
    SAC: {
        name: "SAC",
        fullName: "Soft Actor-Critic",
        type: "off-policy",
        actionSpaces: ["continuous"],
        description: "State-of-the-art for continuous control. Maximizes both expected reward and entropy, providing automatic exploration-exploitation balance with learnable temperature.",
        strengths: [
            "Automatic entropy tuning",
            "Very sample-efficient",
            "Stable and robust training",
        ],
        weaknesses: [
            "Continuous actions only",
            "More computationally expensive",
            "Larger memory footprint (replay buffer)",
        ],
    },
    TD3: {
        name: "TD3",
        fullName: "Twin Delayed DDPG",
        type: "off-policy",
        actionSpaces: ["continuous"],
        description: "Improved DDPG with three key innovations: twin critics to reduce overestimation, delayed policy updates, and target policy smoothing.",
        strengths: [
            "Reduced overestimation bias",
            "More stable than DDPG",
            "Good continuous control performance",
        ],
        weaknesses: [
            "Continuous actions only",
            "Requires careful action noise tuning",
            "Deterministic policy needs explicit exploration",
        ],
    },
    DDPG: {
        name: "DDPG",
        fullName: "Deep Deterministic Policy Gradient",
        type: "off-policy",
        actionSpaces: ["continuous"],
        description: "Foundational off-policy algorithm for continuous control. Extends DQN ideas to continuous actions. Generally superseded by TD3 and SAC.",
        strengths: [
            "Simple off-policy continuous control",
            "Sample-efficient via replay buffer",
        ],
        weaknesses: [
            "Continuous actions only",
            "Inferior to TD3 and SAC in benchmarks",
            "Prone to overestimation and instability",
        ],
    },
}

/**
 * Retro/emulated games always use discrete action spaces (button presses).
 * Continuous-only algorithms (SAC, TD3, DDPG) are incompatible.
 */
function supportsDiscreteActions(algo: Algorithm): boolean {
    return ALGORITHM_INFO[algo].actionSpaces.includes("discrete")
}

// =============================================================================
// Component
// =============================================================================

interface AlgorithmDefaultsCardProps {
    formData: ConfigUpdate
    onChange: (field: keyof ConfigUpdate, value: ConfigUpdate[keyof ConfigUpdate]) => void
}

export function AlgorithmDefaultsCard({ formData, onChange }: AlgorithmDefaultsCardProps) {
    const selected = (formData.default_algorithm ?? "PPO") as Algorithm
    const info = ALGORITHM_INFO[selected]
    const isCompatible = supportsDiscreteActions(selected)

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
                <h3 className="text-lg font-medium mb-1">Default Algorithm</h3>
                <p className="text-sm text-muted-foreground">
                    Select the baseline RL algorithm used when creating new runs.
                </p>
                <div className="mt-3 space-y-2">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Action spaces</p>
                    <p className="text-xs text-muted-foreground">
                        Retro games use <span className="font-semibold">discrete</span> action spaces (button presses: A, B, Up, Down, etc.).
                        Continuous action spaces are for robotics and physics simulations (joint torques, forces).
                    </p>
                </div>
            </div>
            <Card className="lg:col-span-2">
                <CardContent className="pt-6 space-y-5">
                    {/* Selector */}
                    <Select
                        value={selected}
                        onValueChange={(v) => onChange("default_algorithm", v)}
                    >
                        <SelectTrigger className="w-full">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="PPO">PPO &mdash; Proximal Policy Optimization</SelectItem>
                            <SelectItem value="A2C">A2C &mdash; Advantage Actor Critic</SelectItem>
                            <SelectItem value="DQN">DQN &mdash; Deep Q-Network</SelectItem>
                            <SelectItem value="SAC">SAC &mdash; Soft Actor-Critic</SelectItem>
                            <SelectItem value="TD3">TD3 &mdash; Twin Delayed DDPG</SelectItem>
                            <SelectItem value="DDPG">DDPG &mdash; Deep Deterministic Policy Gradient</SelectItem>
                        </SelectContent>
                    </Select>

                    {/* Info panel */}
                    <div className="space-y-4 border p-4">
                        {/* Tags row */}
                        <div className="flex flex-wrap gap-2">
                            <Badge variant={info.type === "on-policy" ? "default" : "secondary"}>
                                {info.type}
                            </Badge>
                            {info.actionSpaces.map((space) => (
                                <Badge key={space} variant="outline">
                                    {space.replace("_", " ")}
                                </Badge>
                            ))}
                            {info.recommendation && (
                                <Badge variant="default" className="gap-1">
                                    <Star className="size-3" />
                                    recommended
                                </Badge>
                            )}
                        </div>

                        {/* Description */}
                        <p className="text-sm text-muted-foreground leading-relaxed">{info.description}</p>

                        {/* Strengths / Weaknesses */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                            <div>
                                <p className="font-medium mb-1.5 flex items-center gap-1.5">
                                    <CheckCircle2 className="size-3.5 text-chart-2" />
                                    Strengths
                                </p>
                                <ul className="space-y-1 text-muted-foreground">
                                    {info.strengths.map((s) => (
                                        <li key={s} className="flex gap-2">
                                            <span className="text-chart-2 shrink-0">+</span>
                                            {s}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                            <div>
                                <p className="font-medium mb-1.5 flex items-center gap-1.5">
                                    <AlertTriangle className="size-3.5 text-chart-4" />
                                    Weaknesses
                                </p>
                                <ul className="space-y-1 text-muted-foreground">
                                    {info.weaknesses.map((w) => (
                                        <li key={w} className="flex gap-2">
                                            <span className="text-chart-4 shrink-0">&minus;</span>
                                            {w}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </div>

                    {/* Compatibility warning */}
                    {!isCompatible && (
                        <div className="flex items-start gap-3 border border-destructive/30 bg-destructive/5 p-3">
                            <AlertTriangle className="size-5 text-chart-4 shrink-0 mt-0.5" />
                            <div className="text-sm">
                                <p className="font-medium text-chart-4">
                                    Not compatible with retro games
                                </p>
                                <p className="text-muted-foreground mt-0.5">
                                    {info.name} only supports continuous action spaces. All emulated retro games use discrete actions (button presses).
                                    This algorithm is available for custom environments with continuous control.
                                </p>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
