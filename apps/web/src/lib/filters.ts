import type { RunStatus } from "./schemas"

export function filterRuns<T extends { rom: string; id: string; status: RunStatus; algorithm: string; agent_id?: string | null; agent_name?: string | null }>(
  runs: T[],
  search: string,
  statusFilter: string | "all",
  algorithmFilter: string | "all" = "all",
  romsMap?: Map<string, { system: string }> | null,
  systemFilter: string | "all" = "all",
  agentFilter: string | "all" = "all"
): T[] {
  return runs.filter((run) => {
    const matchesSearch =
      run.rom.toLowerCase().includes(search.toLowerCase()) ||
      run.id.toLowerCase().includes(search.toLowerCase()) ||
      (run.agent_name?.toLowerCase().includes(search.toLowerCase()) ?? false)

    const matchesStatus = statusFilter === "all" || run.status === statusFilter

    const matchesAlgorithm = algorithmFilter === "all" || run.algorithm === algorithmFilter

    const matchesAgent = agentFilter === "all" || run.agent_id === agentFilter

    let matchesSystem = true
    if (systemFilter !== "all" && romsMap) {
      const rom = romsMap.get(run.rom)
      matchesSystem = rom?.system === systemFilter
    }

    return matchesSearch && matchesStatus && matchesAlgorithm && matchesAgent && matchesSystem
  })
}
