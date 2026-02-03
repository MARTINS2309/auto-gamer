import { Card, CardContent } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { ConfigUpdate } from "@/lib/schemas"

interface AlgorithmDefaultsCardProps {
    formData: ConfigUpdate
    onChange: (field: keyof ConfigUpdate, value: any) => void
}

export function AlgorithmDefaultsCard({ formData, onChange }: AlgorithmDefaultsCardProps) {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
                <h3 className="text-lg font-medium mb-1">Default Algorithm</h3>
                <p className="text-sm text-muted-foreground">Select the baseline RL algorithm used when creating new runs.</p>
            </div>
            <Card className="lg:col-span-2">
                <CardContent className="pt-6">
                    <div className="space-y-4">
                        <div className="flex items-center gap-4">
                            <Select
                                value={formData.default_algorithm}
                                onValueChange={(v) => onChange("default_algorithm", v)}
                            >
                                <SelectTrigger className="w-[200px]">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="PPO">PPO (Proximal Policy Optimization)</SelectItem>
                                    <SelectItem value="DQN">DQN (Deep Q-Network)</SelectItem>
                                    <SelectItem value="A2C">A2C (Advantage Actor Critic)</SelectItem>
                                </SelectContent>
                            </Select>
                            <div className="text-sm text-muted-foreground">
                                {formData.default_algorithm === "PPO" && "Best for continuous or complex discrete action spaces. Stable and reliable."}
                                {formData.default_algorithm === "DQN" && "Classic algorithm for discrete actions. Sample efficient but can be unstable."}
                                {formData.default_algorithm === "A2C" && "Synchronous version of A3C. faster than PPO but often less sample efficient."}
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
