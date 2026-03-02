import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { AgentCreateInput, AgentUpdate } from "@/lib/schemas"
import { toast } from "sonner"

export const agentKeys = {
  all: ["agents"] as const,
  detail: (id: string) => ["agent", id] as const,
}

export function useAgents() {
  return useQuery({
    queryKey: agentKeys.all,
    queryFn: () => api.agents.list(),
  })
}

export function useAgent(id: string) {
  return useQuery({
    queryKey: agentKeys.detail(id),
    queryFn: () => api.agents.get(id),
    enabled: !!id,
  })
}

export function useCreateAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: AgentCreateInput) => api.agents.create(data),
    onSuccess: () => {
      toast.success("Agent created")
      queryClient.invalidateQueries({ queryKey: agentKeys.all })
    },
    onError: (error) => {
      toast.error(`Failed to create agent: ${error.message}`)
    },
  })
}

export function useUpdateAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AgentUpdate }) =>
      api.agents.update(id, data),
    onSuccess: (agent) => {
      toast.success("Agent updated")
      queryClient.invalidateQueries({ queryKey: agentKeys.all })
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(agent.id) })
    },
    onError: (error) => {
      toast.error(`Failed to update agent: ${error.message}`)
    },
  })
}

export function useDeleteAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.agents.delete(id),
    onSuccess: () => {
      toast.success("Agent deleted")
      queryClient.invalidateQueries({ queryKey: agentKeys.all })
    },
    onError: (error) => {
      toast.error(`Failed to delete agent: ${error.message}`)
    },
  })
}
