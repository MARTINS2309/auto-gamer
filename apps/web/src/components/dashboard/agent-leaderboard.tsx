import { Link } from "@tanstack/react-router"
import { Bot } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { useAgents } from "@/hooks"
import { formatSteps } from "@/lib/schemas"
import { NewAgentDialog } from "@/components/agents/new-agent-dialog"

const RANK_COLORS = [
  "text-chart-1",  // #1
  "text-chart-2",  // #2
  "text-chart-3",  // #3
  "text-chart-4",  // #4
  "text-chart-5",  // #5
]

export function AgentLeaderboard() {
  const { data: agents = [], isLoading } = useAgents()

  // Sort by best_reward descending, nulls last
  const sorted = [...agents].sort((a, b) => {
    if (a.best_reward == null && b.best_reward == null) return 0
    if (a.best_reward == null) return 1
    if (b.best_reward == null) return -1
    return b.best_reward - a.best_reward
  })

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="w-5 h-5" />
            Agent Leaderboard
          </CardTitle>
        </CardHeader>
        <CardContent className="py-8 text-center text-muted-foreground">
          Loading...
        </CardContent>
      </Card>
    )
  }

  if (agents.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="w-5 h-5" />
            Agent Leaderboard
          </CardTitle>
        </CardHeader>
        <CardContent className="py-8 text-center space-y-3">
          <p className="text-muted-foreground">No agents yet. Create one to get started.</p>
          <NewAgentDialog
            trigger={<Button variant="outline" size="sm">Create Agent</Button>}
          />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Bot className="w-5 h-5" />
          Agent Leaderboard
        </CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link to="/agents">View all</Link>
        </Button>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">#</TableHead>
              <TableHead>Agent</TableHead>
              <TableHead>Game</TableHead>
              <TableHead>Algorithm</TableHead>
              <TableHead className="text-right">Best Reward</TableHead>
              <TableHead className="text-right">Steps</TableHead>
              <TableHead className="text-right">Runs</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.slice(0, 10).map((agent, idx) => (
              <TableRow key={agent.id}>
                <TableCell>
                  <span className={`font-bold tabular-nums ${RANK_COLORS[idx] ?? "text-muted-foreground"}`}>
                    {idx + 1}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="font-medium">{agent.name}</span>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {agent.game_name ?? agent.game_id}
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-xs">{agent.algorithm}</Badge>
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {agent.best_reward != null
                    ? agent.best_reward.toFixed(1)
                    : <span className="text-muted-foreground">--</span>}
                </TableCell>
                <TableCell className="text-right tabular-nums text-muted-foreground">
                  {formatSteps(agent.total_steps)}
                </TableCell>
                <TableCell className="text-right tabular-nums text-muted-foreground">
                  {agent.total_runs}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
