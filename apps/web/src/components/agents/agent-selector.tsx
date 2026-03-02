import { Plus } from "lucide-react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { useAgents } from "@/hooks"
import { formatSteps, type Agent } from "@/lib/schemas"

interface AgentSelectorProps {
  value: string | null | undefined
  onChange: (agentId: string | null, agent: Agent | null) => void
  onCreateNew: () => void
  gameId?: string
}

export function AgentSelector({ value, onChange, onCreateNew, gameId }: AgentSelectorProps) {
  const { data: allAgents = [] } = useAgents()
  const agents = gameId ? allAgents.filter((a) => a.game_id === gameId) : allAgents

  const handleChange = (val: string) => {
    if (val === "__new__") {
      onCreateNew()
      return
    }
    const agent = agents.find((a) => a.id === val) ?? null
    onChange(val, agent)
  }

  return (
    <div className="space-y-2">
      <Select onValueChange={handleChange} value={value ?? ""}>
        <SelectTrigger>
          <SelectValue placeholder="Select an agent" />
        </SelectTrigger>
        <SelectContent>
          {agents.map((agent) => (
            <SelectItem key={agent.id} value={agent.id}>
              <div className="flex items-center gap-2">
                <span>{agent.name}</span>
                <Badge variant="outline" className="text-xs">
                  {agent.algorithm}
                </Badge>
                {agent.game_name && (
                  <span className="text-xs text-muted-foreground">
                    {agent.game_name}
                  </span>
                )}
                {agent.total_runs > 0 && (
                  <span className="text-xs text-muted-foreground">
                    {agent.total_runs} runs &middot; {formatSteps(agent.total_steps)} steps
                  </span>
                )}
              </div>
            </SelectItem>
          ))}
          <SelectItem value="__new__">
            <div className="flex items-center gap-2 text-primary">
              <Plus className="w-3 h-3" />
              <span>Create new agent...</span>
            </div>
          </SelectItem>
        </SelectContent>
      </Select>

      {value && (() => {
        const selected = agents.find((a) => a.id === value)
        if (!selected) return null
        return (
          <div className="flex items-center gap-3 p-2 border bg-muted/50 text-sm">
            <Badge variant="secondary">{selected.algorithm}</Badge>
            <span className="text-muted-foreground">
              {selected.total_runs} run{selected.total_runs !== 1 ? "s" : ""}
            </span>
            <span className="text-muted-foreground">
              {formatSteps(selected.total_steps)} steps
            </span>
            {selected.best_reward != null && (
              <span className="text-muted-foreground">
                Best: {selected.best_reward.toFixed(1)}
              </span>
            )}
          </div>
        )
      })()}
    </div>
  )
}
