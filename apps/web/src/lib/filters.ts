import type { RunStatus } from "./schemas"

export function filterRuns<T extends { rom: string; id: string; status: RunStatus }>(
  runs: T[],
  search: string,
  statusFilter: string
): T[] {
  return runs.filter((run) => {
    const matchesSearch =
      run.rom.toLowerCase().includes(search.toLowerCase()) ||
      run.id.toLowerCase().includes(search.toLowerCase())
    const matchesStatus = statusFilter === "all" || run.status === statusFilter
    return matchesSearch && matchesStatus
  })
}
