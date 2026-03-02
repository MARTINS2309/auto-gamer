import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Plus } from "lucide-react"
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
import { Textarea } from "@/components/ui/textarea"
import { useCreateAgent, useRoms } from "@/hooks"
import { AgentCreateSchema, DEFAULT_HYPERPARAMS } from "@/lib/schemas"
import type { AgentCreateInput, Algorithm } from "@/lib/schemas"
import { HyperparametersCard } from "@/components/config/hyperparameters-card"

interface NewAgentDialogProps {
  trigger?: React.ReactNode
  open?: boolean
  onOpenChange?: (open: boolean) => void
  onCreated?: (agent: { id: string; name: string; algorithm: string; game_id: string; observation_type: string; action_space: string }) => void
}

export function NewAgentDialog({ trigger, open: controlledOpen, onOpenChange, onCreated }: NewAgentDialogProps) {
  const [internalOpen, setInternalOpen] = useState(false)
  const open = controlledOpen ?? internalOpen
  const setOpen = (value: boolean) => {
    setInternalOpen(value)
    onOpenChange?.(value)
  }
  const createAgent = useCreateAgent()
  const { data: roms = [] } = useRoms()
  const trainableRoms = roms.filter(r => r.has_rom && r.has_connector)

  const form = useForm<AgentCreateInput>({
    resolver: zodResolver(AgentCreateSchema),
    defaultValues: {
      name: "",
      description: "",
      algorithm: "PPO",
      game_id: "",
      hyperparams: DEFAULT_HYPERPARAMS,
      observation_type: "image",
      action_space: "filtered",
    },
  })

  const selectedAlgorithm = form.watch("algorithm") as Algorithm
  const currentHParams = form.watch("hyperparams")

  const handleHParamChange = (key: string, value: number | boolean) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form.setValue(`hyperparams.${key}` as any, value, { shouldDirty: true, shouldValidate: true })
  }

  const onSubmit = (values: AgentCreateInput) => {
    createAgent.mutate(values, {
      onSuccess: (agent) => {
        setOpen(false)
        form.reset()
        onCreated?.({ id: agent.id, name: agent.name, algorithm: agent.algorithm, game_id: agent.game_id, observation_type: agent.observation_type, action_space: agent.action_space })
      },
    })
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            New Agent
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Agent</DialogTitle>
          <DialogDescription>
            Agents persist across training runs. The algorithm and architecture cannot be changed after creation.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Agent Name</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., Pokemon Explorer v1" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="game_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Game</FormLabel>
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
                        <SelectItem value="SAC">SAC</SelectItem>
                        <SelectItem value="TD3">TD3</SelectItem>
                        <SelectItem value="DDPG">DDPG</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description (optional)</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="What is this agent for?"
                      className="resize-none"
                      rows={2}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="observation_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Observation Type</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="image">Image (84x84 grayscale)</SelectItem>
                        <SelectItem value="ram">RAM</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="action_space"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Action Space</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="filtered">Filtered (recommended)</SelectItem>
                        <SelectItem value="discrete">Discrete</SelectItem>
                        <SelectItem value="multi_binary">Multi-Binary</SelectItem>
                      </SelectContent>
                    </Select>
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
              <Button type="submit" disabled={createAgent.isPending}>
                {createAgent.isPending ? "Creating..." : "Create Agent"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
