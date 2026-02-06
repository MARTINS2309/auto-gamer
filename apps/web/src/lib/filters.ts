import type { RunStatus } from "./schemas"

export function filterRuns<T extends { rom: string; id: string; status: RunStatus; algorithm: string }>(
  runs: T[],
  search: string,
  statusFilter: string | "all",
  algorithmFilter: string | "all" = "all",
  romsMap?: Map<string, { system: string }> | null,
  systemFilter: string | "all" = "all"
): T[] {
  return runs.filter((run) => {
    const matchesSearch =
      run.rom.toLowerCase().includes(search.toLowerCase()) ||
      run.id.toLowerCase().includes(search.toLowerCase())

    const matchesStatus = statusFilter === "all" || run.status === statusFilter

    const matchesAlgorithm = algorithmFilter === "all" || run.algorithm === algorithmFilter

    let matchesSystem = true
    if (systemFilter !== "all" && romsMap) {
      const rom = romsMap.get(run.rom)
      matchesSystem = rom?.system === systemFilter
    }

    return matchesSearch && matchesStatus && matchesAlgorithm && matchesSystem
  })
}
