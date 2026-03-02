import { useState, useRef, useEffect } from "react"
import { useForm, type UseFormReturn } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Plus, ChevronDown, Info } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Badge } from "@/components/ui/badge"
import { useRoms, useCreateRun, useRomStates, useAgents } from "@/hooks"
import { RunCreateSchema, DEFAULT_HYPERPARAMS, getDefaultHyperparams, formatSteps } from "@/lib/schemas"
import type { RunCreateInput, Agent, Algorithm } from "@/lib/schemas"
import { HyperparametersCard } from "@/components/config/hyperparameters-card"
import { DiscreteHyperparamSlider, formatCompact } from "@/components/config/common"
import { AgentSelector } from "@/components/agents/agent-selector"
import { NewAgentDialog } from "@/components/agents/new-agent-dialog"
import { Label } from "@/components/ui/label"

interface NewRunDialogProps {
    trigger?: React.ReactNode
    initialValues?: Partial<RunCreateInput>
    open?: boolean
    onOpenChange?: (open: boolean) => void
}

const MAX_STEPS_VALUES = [100_000, 250_000, 500_000, 1_000_000, 2_000_000, 5_000_000, 10_000_000, 50_000_000, 100_000_000] as const
const N_ENVS_VALUES = [1, 2, 4, 8, 16, 32, 64] as const
const CHECKPOINT_INTERVAL_VALUES = [5_000, 10_000, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000] as const
const FRAME_FPS_VALUES = [3, 5, 10, 15, 30, 60] as const

function StateSelector({ form, romId }: { form: UseFormReturn<RunCreateInput>, romId: string }) {
    const { data: states = [], isLoading } = useRomStates(romId)

    return (
        <FormField
            control={form.control}
            name="state"
            render={({ field }) => (
                <FormItem>
                    <FormLabel>Start State</FormLabel>
                    <Select
                        onValueChange={field.onChange}
                        value={field.value}
                        disabled={!romId || isLoading}
                    >
                        <FormControl>
                            <SelectTrigger>
                                <SelectValue placeholder={isLoading ? "Loading..." : "Select start state"} />
                            </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                            {states.length === 0 && <SelectItem value="Start">Start</SelectItem>}
                            {states.map((state) => (
                                <SelectItem key={state.name} value={state.name}>
                                    <div className="flex items-center gap-2">
                                        {state.name}
                                        {state.multiplayer && (
                                            <Badge variant="outline" className="text-xs">2P</Badge>
                                        )}
                                    </div>
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <FormMessage />
                </FormItem>
            )}
        />
    )
}

function OpponentSelector({ form, selectedAgent }: { form: UseFormReturn<RunCreateInput>, selectedAgent: Agent }) {
    const { data: agents = [] } = useAgents()
    const opponentId = form.watch("opponent_agent_id")

    // Filter: same game, different agent, must have at least 1 run (needs trained weights)
    const eligible = agents.filter(a =>
        a.id !== selectedAgent.id &&
        a.game_id === selectedAgent.game_id &&
        a.total_runs > 0
    )

    if (eligible.length === 0) return null

    return (
        <div className="space-y-3">
            <Label className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                Opponent (Self-Play)
            </Label>
            <Select
                value={opponentId ?? "__none__"}
                onValueChange={(v) => {
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    form.setValue("opponent_agent_id" as any, v === "__none__" ? null : v, { shouldDirty: true })
                }}
            >
                <SelectTrigger>
                    <SelectValue placeholder="No opponent (solo training)" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="__none__">
                        <span className="text-muted-foreground">No opponent (solo training)</span>
                    </SelectItem>
                    {eligible.map((agent) => (
                        <SelectItem key={agent.id} value={agent.id}>
                            <div className="flex items-center gap-2">
                                <span>{agent.name}</span>
                                <Badge variant="outline" className="text-xs">
                                    {agent.algorithm}
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                    {formatSteps(agent.total_steps)} steps
                                </span>
                            </div>
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
            {opponentId && (() => {
                const opp = agents.find(a => a.id === opponentId)
                if (!opp) return null
                return (
                    <div className="flex items-center gap-3 p-2 border bg-muted/50 text-sm">
                        <Badge variant="secondary">{opp.algorithm}</Badge>
                        <span className="text-muted-foreground">
                            {formatSteps(opp.total_steps)} steps
                        </span>
                        {opp.best_reward != null && (
                            <span className="text-muted-foreground">
                                Best: {opp.best_reward.toFixed(1)}
                            </span>
                        )}
                        <span className="text-xs text-muted-foreground ml-auto">
                            Frozen weights as Player 2
                        </span>
                    </div>
                )
            })()}
        </div>
    )
}

export function NewRunDialog({ trigger, initialValues, open: controlledOpen, onOpenChange }: NewRunDialogProps) {
    const [internalOpen, setInternalOpen] = useState(false)
    const open = controlledOpen ?? internalOpen
    const setOpen = (value: boolean) => {
        setInternalOpen(value)
        onOpenChange?.(value)
    }
    const { data: roms = [] } = useRoms()
    const createRun = useCreateRun()
    const [newAgentOpen, setNewAgentOpen] = useState(false)
    const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)

    const form = useForm<RunCreateInput>({
        resolver: zodResolver(RunCreateSchema),
        defaultValues: {
            max_steps: 1_000_000,
            n_envs: 8,
            hyperparams: DEFAULT_HYPERPARAMS,
            checkpoint_interval: 50_000,
            frame_fps: 15,
            ...initialValues
        },
    })

    // Reset form when controlled open changes with new initialValues
    const prevOpenRef = useRef(false)
    useEffect(() => {
        if (open && !prevOpenRef.current && initialValues) {
            form.reset({
                max_steps: 1_000_000,
                n_envs: 8,
                hyperparams: DEFAULT_HYPERPARAMS,
                checkpoint_interval: 50_000,
                frame_fps: 15,
                ...initialValues,
            })
            setSelectedAgent(null)
        }
        prevOpenRef.current = open
    }, [open, initialValues, form])

    // Filter trainable roms (has ROM + connector)
    const trainableRoms = roms.filter(r => r.has_rom && r.has_connector)
    const selectedRom = form.watch("rom")
    const activeRom = roms.find(r => r.id === selectedRom)

    const onSubmit = (values: RunCreateInput) => {
        createRun.mutate(values, {
            onSuccess: () => {
                setOpen(false)
                form.reset()
                setSelectedAgent(null)
            }
        })
    }

    const { data: statesForRom = [] } = useRomStates(selectedRom)
    const selectedStateName = form.watch("state")
    const selectedStateInfo = statesForRom.find(s => s.name === selectedStateName)
    const isMultiplayerState = selectedStateInfo?.multiplayer ?? false

    const currentHParams = form.watch("hyperparams")
    const selectedAlgorithm = (selectedAgent?.algorithm ?? "PPO") as Algorithm
    const hasAgent = selectedAgent !== null

    const handleHParamChange = (key: string, value: number | boolean) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        form.setValue(`hyperparams.${key}` as any, value, { shouldDirty: true, shouldValidate: true })
    }

    const handleAgentChange = (agentId: string | null, agent: Agent | null) => {
        setSelectedAgent(agent)
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        form.setValue("agent_id" as any, agentId, { shouldDirty: true })
        if (agent) {
            form.setValue("algorithm", agent.algorithm as Algorithm)
            form.setValue("observation_type", agent.observation_type)
            form.setValue("action_space", agent.action_space)
            form.setValue("rom", agent.game_id)
            if (agent.hyperparams) {
                form.setValue("hyperparams", agent.hyperparams as RunCreateInput["hyperparams"])
            } else {
                form.setValue("hyperparams", getDefaultHyperparams(agent.algorithm as Algorithm) as RunCreateInput["hyperparams"])
            }
        }
    }

    const handleAgentCreated = (created: { id: string; name: string; algorithm: string; game_id: string; observation_type: string; action_space: string }) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        form.setValue("agent_id" as any, created.id, { shouldDirty: true })
        form.setValue("algorithm", created.algorithm as Algorithm)
        form.setValue("observation_type", created.observation_type as RunCreateInput["observation_type"])
        form.setValue("action_space", created.action_space as RunCreateInput["action_space"])
        form.setValue("rom", created.game_id)
        const defaults = getDefaultHyperparams(created.algorithm as Algorithm)
        form.setValue("hyperparams", defaults as RunCreateInput["hyperparams"])
        setSelectedAgent({
            id: created.id,
            name: created.name,
            algorithm: created.algorithm as Algorithm,
            game_id: created.game_id,
            game_name: null,
            total_steps: 0,
            total_runs: 0,
            best_reward: null,
            observation_type: created.observation_type as Agent["observation_type"],
            action_space: created.action_space as Agent["action_space"],
            hyperparams: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        })
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                {trigger || (
                    <Button>
                        <Plus className="w-4 h-4 mr-2" />
                        New Run
                    </Button>
                )}
            </DialogTrigger>
            <DialogContent className="sm:max-w-[900px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Start New Training Run</DialogTitle>
                    <DialogDescription>
                        Select an agent and configure training parameters.
                    </DialogDescription>
                </DialogHeader>

                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">

                        {/* Section 1: Agent */}
                        <div className="space-y-3">
                            <Label className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Agent</Label>
                            <AgentSelector
                                value={form.watch("agent_id")}
                                onChange={handleAgentChange}
                                onCreateNew={() => setNewAgentOpen(true)}
                            />
                            {hasAgent && (
                                <div className="flex items-center gap-2 flex-wrap">
                                    <Badge variant="secondary">{selectedAgent.algorithm}</Badge>
                                    <Badge variant="outline">{selectedAgent.observation_type}</Badge>
                                    <Badge variant="outline">{selectedAgent.action_space}</Badge>
                                </div>
                            )}
                        </div>

                        {/* Section 1.5: Opponent (Self-Play, optional — only for multiplayer states) */}
                        {hasAgent && isMultiplayerState && (
                            <OpponentSelector
                                form={form}
                                selectedAgent={selectedAgent}
                            />
                        )}

                        {/* Section 2: Game */}
                        <div className="space-y-3">
                            <Label className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                                Game{hasAgent ? " (locked to agent)" : ""}
                            </Label>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <FormField
                                    control={form.control}
                                    name="rom"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>ROM</FormLabel>
                                            <Select onValueChange={field.onChange} value={field.value} disabled={hasAgent}>
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Select a game" />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    {trainableRoms.map((rom) => (
                                                        <SelectItem key={rom.id} value={rom.id}>
                                                            {rom.display_name} ({rom.system})
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <StateSelector form={form} romId={selectedRom} />
                            </div>
                            {activeRom && (
                                <div className="flex gap-4 p-3 border bg-muted/50">
                                    {activeRom.thumbnail_url && (
                                        <img
                                            src={activeRom.thumbnail_url}
                                            alt={activeRom.display_name}
                                            className="w-20 h-28 object-cover shadow"
                                        />
                                    )}
                                    <div className="space-y-1.5">
                                        <h3 className="font-semibold">{activeRom.display_name}</h3>
                                        <div className="flex flex-wrap gap-1.5">
                                            {activeRom.genres?.slice(0, 3).map(g => (
                                                <span key={g} className="text-xs px-2 py-0.5 bg-background border">
                                                    {g}
                                                </span>
                                            ))}
                                            {activeRom.rating && (
                                                <span className="text-xs px-2 py-0.5 bg-chart-3/20 text-chart-3 border border-chart-3/30">
                                                    ★ {Math.round(activeRom.rating)}%
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Section 3: Training */}
                        <div className="space-y-4">
                            <Label className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Training</Label>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-6">
                                <DiscreteHyperparamSlider
                                    label="Total Steps"
                                    value={form.watch("max_steps") ?? 1_000_000}
                                    values={MAX_STEPS_VALUES}
                                    onChange={(v) => form.setValue("max_steps", v, { shouldDirty: true })}
                                    tooltip="Total training steps across all environments. More steps = longer training but potentially better results."
                                    formatValue={formatCompact}
                                />
                                <DiscreteHyperparamSlider
                                    label="Parallel Envs"
                                    value={form.watch("n_envs") ?? 8}
                                    values={N_ENVS_VALUES}
                                    onChange={(v) => form.setValue("n_envs", v, { shouldDirty: true })}
                                    tooltip="Number of parallel game instances. More envs = faster data collection but more VRAM/RAM usage."
                                    formatValue={(v) => v.toString()}
                                />
                            </div>
                        </div>

                        {/* Section 4: Advanced (collapsible) */}
                        <Collapsible>
                            <CollapsibleTrigger asChild>
                                <Button variant="ghost" type="button" className="w-full justify-between px-0 hover:bg-transparent">
                                    <Label className="text-sm font-semibold uppercase tracking-wider text-muted-foreground cursor-pointer">Advanced</Label>
                                    <ChevronDown className="size-4 text-muted-foreground" />
                                </Button>
                            </CollapsibleTrigger>
                            <CollapsibleContent>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-6 pt-2">
                                    <DiscreteHyperparamSlider
                                        label="Checkpoint Interval"
                                        value={form.watch("checkpoint_interval") ?? 50_000}
                                        values={CHECKPOINT_INTERVAL_VALUES}
                                        onChange={(v) => form.setValue("checkpoint_interval", v, { shouldDirty: true })}
                                        tooltip="Save model weights every N steps. Lower = more frequent saves (more disk usage), higher = less overhead."
                                        formatValue={formatCompact}
                                    />
                                    <DiscreteHyperparamSlider
                                        label="Frame FPS"
                                        value={form.watch("frame_fps") ?? 15}
                                        values={FRAME_FPS_VALUES}
                                        onChange={(v) => form.setValue("frame_fps", v, { shouldDirty: true })}
                                        tooltip="Target frames per second streamed to the UI during training. Higher = smoother video but more bandwidth. Automatically scaled down with more parallel envs."
                                        formatValue={(v) => `${v} fps`}
                                    />
                                </div>
                            </CollapsibleContent>
                        </Collapsible>

                        {/* Section 5: Hyperparameters (collapsible) */}
                        <Collapsible>
                            <CollapsibleTrigger asChild>
                                <Button variant="ghost" type="button" className="w-full justify-between px-0 hover:bg-transparent">
                                    <Label className="text-sm font-semibold uppercase tracking-wider text-muted-foreground cursor-pointer">Hyperparameters</Label>
                                    <ChevronDown className="size-4 text-muted-foreground" />
                                </Button>
                            </CollapsibleTrigger>
                            <CollapsibleContent>
                                <div className="space-y-4 pt-2">
                                    <div className="flex items-start gap-2 p-3 border bg-muted/50 text-sm text-muted-foreground">
                                        <Info className="size-4 mt-0.5 shrink-0" />
                                        <span>Defaults from agent. Changes apply to this run only.</span>
                                    </div>
                                    <HyperparametersCard
                                        algorithm={selectedAlgorithm}
                                        hparams={currentHParams || DEFAULT_HYPERPARAMS}
                                        onChange={handleHParamChange}
                                    />
                                </div>
                            </CollapsibleContent>
                        </Collapsible>

                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                                Cancel
                            </Button>
                            <Button type="submit" disabled={createRun.isPending || !hasAgent}>
                                {createRun.isPending ? "Starting..." : "Start Training"}
                            </Button>
                        </DialogFooter>
                    </form>
                </Form>
            </DialogContent>

            {/* Nested dialog for creating a new agent */}
            <NewAgentDialog
                open={newAgentOpen}
                onOpenChange={setNewAgentOpen}
                onCreated={handleAgentCreated}
            />
        </Dialog>
    )
}
