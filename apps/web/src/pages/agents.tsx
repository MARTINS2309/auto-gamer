import { useState } from "react"
import { Bot, Trash2, Play } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Page,
  PageHeader,
  PageTitle,
  PageDescription,
  PageActions,
  PageContent,
} from "@/components/ui/page"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { useAgents, useDeleteAgent } from "@/hooks"
import { formatSteps, type Agent } from "@/lib/schemas"
import { NewAgentDialog } from "@/components/agents/new-agent-dialog"
import { NewRunDialog } from "@/components/runs/new-run-dialog"

export function AgentsPage() {
  const { data: agents = [], isLoading } = useAgents()
  const deleteAgent = useDeleteAgent()
  const [selectedAgentForRun, setSelectedAgentForRun] = useState<Agent | null>(null)
  const [newRunOpen, setNewRunOpen] = useState(false)

  const handleTrainAgent = (agent: Agent) => {
    setSelectedAgentForRun(agent)
    setNewRunOpen(true)
  }

  return (
    <Page>
      <PageHeader className="flex-row items-center justify-between">
        <div>
          <PageTitle>Agents</PageTitle>
          <PageDescription>
            {agents.length} agent{agents.length !== 1 ? "s" : ""} &middot; Persistent models that learn across training runs
          </PageDescription>
        </div>
        <PageActions>
          <NewAgentDialog />
        </PageActions>
      </PageHeader>

      <PageContent>
        {isLoading ? (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              Loading agents...
            </CardContent>
          </Card>
        ) : agents.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center space-y-4">
              <Bot className="w-12 h-12 mx-auto text-muted-foreground" />
              <div>
                <h3 className="text-lg font-semibold">No agents yet</h3>
                <p className="text-muted-foreground">
                  Create an agent to start accumulating learning across training runs.
                </p>
              </div>
              <NewAgentDialog
                trigger={<Button>Create your first agent</Button>}
              />
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>All Agents</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Game</TableHead>
                    <TableHead>Algorithm</TableHead>
                    <TableHead className="text-right">Runs</TableHead>
                    <TableHead className="text-right">Total Steps</TableHead>
                    <TableHead className="text-right">Best Reward</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {agents.map((agent) => (
                    <TableRow key={agent.id}>
                      <TableCell>
                        <div className="space-y-1">
                          <span className="font-medium">{agent.name}</span>
                          {agent.description && (
                            <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                              {agent.description}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {agent.game_name ?? agent.game_id}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{agent.algorithm}</Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {agent.total_runs}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatSteps(agent.total_steps)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {agent.best_reward != null
                          ? agent.best_reward.toFixed(1)
                          : <span className="text-muted-foreground">--</span>}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleTrainAgent(agent)}
                            title="Start training run"
                          >
                            <Play className="w-4 h-4" />
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                title="Delete agent"
                              >
                                <Trash2 className="w-4 h-4 text-destructive" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Delete Agent</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Delete &quot;{agent.name}&quot;? Existing training runs will be kept but unlinked from this agent.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction
                                  onClick={() => deleteAgent.mutate(agent.id)}
                                >
                                  Delete
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </PageContent>

      {/* NewRunDialog pre-selected with agent */}
      <NewRunDialog
        open={newRunOpen}
        onOpenChange={setNewRunOpen}
        initialValues={
          selectedAgentForRun
            ? { agent_id: selectedAgentForRun.id, algorithm: selectedAgentForRun.algorithm, rom: selectedAgentForRun.game_id }
            : undefined
        }
      />
    </Page>
  )
}
