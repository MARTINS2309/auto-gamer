import { useState, useCallback } from "react"
import { ChevronDown, Save, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Separator } from "@/components/ui/separator"
import type { Run, RunHyperparams } from "@/lib/schemas"
import { DEFAULT_HYPERPARAMS, formatSteps } from "@/lib/schemas"
import { useUpdateRun } from "@/hooks/use-runs"
import { HyperparametersCard } from "@/components/config/hyperparameters-card"

interface RunConfigurationProps {
    run: Run
}

function LabelValue({ label, value }: { label: string, value: React.ReactNode }) {
    return (
        <div className="flex flex-col space-y-1.5">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</span>
            <span className="font-mono text-sm font-medium">{value}</span>
        </div>
    )
}

function GeneralConfig({ run }: { run: Run }) {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
                <h3 className="text-lg font-medium mb-1">General Settings</h3>
                <p className="text-sm text-muted-foreground">
                    Basic configuration for the environment and training loop.
                </p>
            </div>
            <Card className="lg:col-span-2">
                <CardContent className="pt-6 grid grid-cols-1 md:grid-cols-2 gap-y-6 gap-x-4">
                    {run.agent_name && <LabelValue label="Agent" value={run.agent_name} />}
                    {run.opponent_agent_name && <LabelValue label="Opponent Agent" value={run.opponent_agent_name} />}
                    <LabelValue label="Algorithm" value={run.algorithm} />
                    <LabelValue label="Observation Type" value={run.observation_type} />
                    <LabelValue label="Action Space" value={run.action_space} />
                    <LabelValue label="ROM" value={run.rom} />
                    <LabelValue label="Initial State" value={run.state} />
                    <LabelValue label="Max Steps" value={run.max_steps.toLocaleString()} />
                    <LabelValue label="Parallel Envs" value={run.n_envs} />
                    <LabelValue label="Checkpoint Interval" value={formatSteps(run.checkpoint_interval)} />
                    <LabelValue label="Frame FPS" value={`${run.frame_fps} fps`} />
                    <LabelValue label="Created At" value={new Date(run.created_at).toLocaleString()} />
                </CardContent>
            </Card>
        </div>
    )
}

export function RunConfiguration({ run }: RunConfigurationProps) {
    const initialHparams: RunHyperparams = run.hyperparams ?? DEFAULT_HYPERPARAMS
    const [hparams, setHparams] = useState<RunHyperparams>(initialHparams)
    const updateRun = useUpdateRun()

    // Check if run is in a state that allows editing (PAUSED, PENDING, STOPPED)
    const isEditable = ["paused", "pending", "stopped"].includes(run.status);

    // Check for dirty state
    const isDirty = JSON.stringify(hparams) !== JSON.stringify(run.hyperparams)

    const handleHparamChange = useCallback((key: string, value: number | boolean) => {
        setHparams(prev => ({ ...prev, [key]: value }))
    }, [])

    const handleSave = () => {
        if (!isEditable) return;
        updateRun.mutate({
            id: run.id,
            updates: { hyperparams: hparams }
        })
    }

    return (
        <Collapsible>
            <CollapsibleTrigger asChild>
                <Button variant="ghost" className="w-full justify-between">
                    Configuration
                    <ChevronDown className="size-4" />
                </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
                <div className="py-4 space-y-8">
                    <GeneralConfig run={run} />

                    <Separator />

                    <div className="relative">
                        <HyperparametersCard
                            algorithm={run.algorithm}
                            hparams={hparams}
                            onChange={handleHparamChange}
                            readOnly={!isEditable}
                        />

                        {isEditable && isDirty && (
                            <div className="absolute top-0 right-0 -mt-12 lg:mt-0 lg:right-6 flex justify-end">
                                <Button onClick={handleSave} disabled={updateRun.isPending} size="sm">
                                    {updateRun.isPending ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Saving...
                                        </>
                                    ) : (
                                        <>
                                            <Save className="mr-2 h-4 w-4" />
                                            Save Changes
                                        </>
                                    )}
                                </Button>
                            </div>
                        )}
                    </div>
                </div>
            </CollapsibleContent>
        </Collapsible>
    )
}
