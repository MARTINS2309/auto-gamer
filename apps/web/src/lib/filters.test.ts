import { describe, it, expect } from "vitest"
import { filterRuns } from "./filters"
import type { RunStatus } from "./schemas"

interface TestRun {
  id: string
  rom: string
  status: RunStatus
  algorithm: string
}

const createRuns = (): TestRun[] => [
  { id: "run-001", rom: "Pokemon FireRed", status: "running", algorithm: "PPO" },
  { id: "run-002", rom: "Pokemon Emerald", status: "completed", algorithm: "DQN" },
  { id: "run-003", rom: "Super Mario Bros", status: "failed", algorithm: "PPO" },
  { id: "run-004", rom: "Pokemon Crystal", status: "running", algorithm: "A2C" },
  { id: "run-005", rom: "Zelda", status: "stopped", algorithm: "PPO" },
]

describe("filterRuns", () => {
  describe("search filtering", () => {
    it("filters by rom (case insensitive)", () => {
      const runs = createRuns()
      const result = filterRuns(runs, "pokemon", "all")
      expect(result).toHaveLength(3)
      expect(result.every((r) => r.rom.toLowerCase().includes("pokemon"))).toBe(true)
    })

    it("filters by id", () => {
      const runs = createRuns()
      const result = filterRuns(runs, "run-001", "all")
      expect(result).toHaveLength(1)
      expect(result[0].id).toBe("run-001")
    })

    it("filters by partial id", () => {
      const runs = createRuns()
      const result = filterRuns(runs, "00", "all")
      expect(result).toHaveLength(5)
    })

    it("is case insensitive for rom", () => {
      const runs = createRuns()
      expect(filterRuns(runs, "POKEMON", "all")).toHaveLength(3)
      expect(filterRuns(runs, "Pokemon", "all")).toHaveLength(3)
      expect(filterRuns(runs, "pokemon", "all")).toHaveLength(3)
    })

    it("is case insensitive for id", () => {
      const runs = createRuns()
      expect(filterRuns(runs, "RUN-001", "all")).toHaveLength(1)
      expect(filterRuns(runs, "Run-001", "all")).toHaveLength(1)
    })

    it("returns all runs when search is empty", () => {
      const runs = createRuns()
      expect(filterRuns(runs, "", "all")).toHaveLength(5)
    })

    it("returns empty array when no matches", () => {
      const runs = createRuns()
      expect(filterRuns(runs, "nonexistent", "all")).toHaveLength(0)
    })
  })

  describe("status filtering", () => {
    it("filters by running status", () => {
      const runs = createRuns()
      const result = filterRuns(runs, "", "running")
      expect(result).toHaveLength(2)
      expect(result.every((r) => r.status === "running")).toBe(true)
    })

    it("filters by completed status", () => {
      const runs = createRuns()
      const result = filterRuns(runs, "", "completed")
      expect(result).toHaveLength(1)
      expect(result[0].status).toBe("completed")
    })

    it("filters by failed status", () => {
      const runs = createRuns()
      const result = filterRuns(runs, "", "failed")
      expect(result).toHaveLength(1)
      expect(result[0].status).toBe("failed")
    })

    it("filters by stopped status", () => {
      const runs = createRuns()
      const result = filterRuns(runs, "", "stopped")
      expect(result).toHaveLength(1)
      expect(result[0].status).toBe("stopped")
    })

    it("returns all when status is 'all'", () => {
      const runs = createRuns()
      expect(filterRuns(runs, "", "all")).toHaveLength(5)
    })
  })

  describe("combined filtering", () => {
    it("combines search and status filters", () => {
      const runs = createRuns()
      const result = filterRuns(runs, "pokemon", "running")
      expect(result).toHaveLength(2)
      expect(result.every((r) => r.rom.toLowerCase().includes("pokemon"))).toBe(true)
      expect(result.every((r) => r.status === "running")).toBe(true)
    })

    it("returns empty when no runs match both filters", () => {
      const runs = createRuns()
      expect(filterRuns(runs, "zelda", "running")).toHaveLength(0)
    })

    it("handles empty array input", () => {
      expect(filterRuns([], "test", "running")).toEqual([])
    })
  })

  describe("type preservation", () => {
    it("preserves additional properties on runs", () => {
      interface ExtendedRun extends TestRun {
        extra: string
      }
      const runs: ExtendedRun[] = [
        { id: "run-001", rom: "Pokemon", status: "running", algorithm: "PPO", extra: "data" },
      ]
      const result = filterRuns(runs, "", "all")
      expect(result[0].extra).toBe("data")
    })
  })
})
