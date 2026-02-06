import { useState, useRef, useEffect } from "react"
import { useForm, type UseFormReturn } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Plus, HelpCircle } from "lucide-react"
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
import { Input } from "@/components/ui/input"
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip"
import { useRoms, useCreateRun, useRomStates } from "@/hooks"
import { RunCreateSchema, DEFAULT_HYPERPARAMS } from "@/lib/schemas"
import type { RunCreateInput } from "@/lib/schemas"
import { HyperparametersCard } from "@/components/config/hyperparameters-card"
import type { Algorithm } from "@/lib/schemas"

interface NewRunDialogProps {
    trigger?: React.ReactNode
    initialValues?: Partial<RunCreateInput>
    open?: boolean
    onOpenChange?: (open: boolean) => void
}

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
                                <SelectItem key={state} value={state}>
                                    {state}
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

export function NewRunDialog({ trigger, initialValues, open: controlledOpen, onOpenChange }: NewRunDialogProps) {
    const [internalOpen, setInternalOpen] = useState(false)
    const open = controlledOpen ?? internalOpen
    const setOpen = (value: boolean) => {
        setInternalOpen(value)
        onOpenChange?.(value)
    }
    const { data: roms = [] } = useRoms()
    const createRun = useCreateRun()

    const form = useForm<RunCreateInput>({
        resolver: zodResolver(RunCreateSchema),
        defaultValues: {
            algorithm: "PPO",
            max_steps: 1_000_000,
            n_envs: 8,
            hyperparams: DEFAULT_HYPERPARAMS,
            checkpoint_interval: 50_000,
            frame_capture_interval: 10_000,
            ...initialValues
        },
    })

    // Reset form when controlled open changes with new initialValues
    const prevOpenRef = useRef(false)
    useEffect(() => {
        if (open && !prevOpenRef.current && initialValues) {
            form.reset({
                algorithm: "PPO",
                max_steps: 1_000_000,
                n_envs: 8,
                hyperparams: DEFAULT_HYPERPARAMS,
                checkpoint_interval: 50_000,
                frame_capture_interval: 10_000,
                ...initialValues,
            })
        }
        prevOpenRef.current = open
    }, [open, initialValues, form])

    // Filter trainable roms (has ROM + connector)
    const trainableRoms = roms.filter(r => r.has_rom && r.has_connector)
    const selectedRom = form.watch("rom")
    // ROM data now includes all metadata directly
    const activeRom = roms.find(r => r.id === selectedRom)

    const onSubmit = (values: RunCreateInput) => {
        createRun.mutate(values, {
            onSuccess: () => {
                setOpen(false)
                form.reset()
            }
        })
    }

    const currentHParams = form.watch("hyperparams")
    const selectedAlgorithm = form.watch("algorithm") as Algorithm

    const handleHParamChange = (key: string, value: number | boolean) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        form.setValue(`hyperparams.${key}` as any, value, { shouldDirty: true, shouldValidate: true })
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
                        Configure the environment, algorithm, and hyperparameters.
                    </DialogDescription>
                </DialogHeader>

                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">

                        {activeRom && (
                            <div className="flex gap-4 p-4 border bg-muted/50">
                                {activeRom.thumbnail_url && (
                                    <img
                                        src={activeRom.thumbnail_url}
                                        alt={activeRom.display_name}
                                        className="w-24 h-32 object-cover shadow"
                                    />
                                )}
                                <div className="space-y-2">
                                    <h3 className="font-semibold text-lg">{activeRom.display_name}</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {activeRom.genres?.slice(0, 3).map(g => (
                                            <span key={g} className="text-xs px-2 py-1 bg-background border">
                                                {g}
                                            </span>
                                        ))}
                                        {activeRom.rating && (
                                            <span className="text-xs px-2 py-1 bg-chart-3/20 text-chart-3 border border-chart-3/30">
                                                ★ {Math.round(activeRom.rating)}%
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <FormField
                                control={form.control}
                                name="rom"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Game (ROM)</FormLabel>
                                        <Select onValueChange={field.onChange} value={field.value}>
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

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <FormField
                                control={form.control}
                                name="algorithm"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Algorithm</FormLabel>
                                        <Select onValueChange={field.onChange} value={field.value}>
                                            <FormControl>
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Select algorithm" />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                <SelectItem value="PPO">PPO</SelectItem>
                                                <SelectItem value="DQN">DQN</SelectItem>
                                                <SelectItem value="A2C">A2C</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="n_envs"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>
                                            Parallel Envs
                                            <TooltipProvider>
                                                <Tooltip>
                                                    <TooltipTrigger><HelpCircle className="w-3 h-3 ml-1 inline text-muted-foreground" /></TooltipTrigger>
                                                    <TooltipContent>Number of parallel game instances. Speeds up training.</TooltipContent>
                                                </Tooltip>
                                            </TooltipProvider>
                                        </FormLabel>
                                        <FormControl>
                                            <Input type="number" {...field} onChange={e => field.onChange(parseInt(e.target.value) || 0)} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="max_steps"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Total Steps</FormLabel>
                                        <FormControl>
                                            <Input type="number" step={1000} {...field} onChange={e => field.onChange(parseInt(e.target.value) || 0)} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <div className="border p-4 bg-muted/50">
                            <HyperparametersCard
                                algorithm={selectedAlgorithm}
                                hparams={currentHParams || DEFAULT_HYPERPARAMS}
                                onChange={handleHParamChange}
                            />
                        </div>

                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                                Cancel
                            </Button>
                            <Button type="submit" disabled={createRun.isPending}>
                                {createRun.isPending ? "Starting..." : "Start Training"}
                            </Button>
                        </DialogFooter>
                    </form>
                </Form>
            </DialogContent>
        </Dialog>
    )
}
