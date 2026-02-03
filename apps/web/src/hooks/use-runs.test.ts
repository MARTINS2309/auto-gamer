import { describe, it, expect } from "vitest"
import { useRunStats } from "./use-runs"
import type { Run } from "@/lib/schemas"

// Helper to create mock runs with minimal required fields
function createRun(overrides: Partial<Run> = {}): Run {
  return {
    id: "run-" + Math.random().toString(36).slice(2),
    rom: "test-rom",
    state: "start",
    algorithm: "PPO",
    hyperparams: {
      learning_rate: 0.0003,
      n_steps: 2048,
      batch_size: 64,
      n_epochs: 10,
      gamma: 0.99,
      gae_lambda: 0.95,
      clip_range: 0.2,
      ent_coef: 0.0,
      vf_coef: 0.5,
      max_grad_norm: 0.5,
    },
    n_envs: 1,
    max_steps: 1000000,
    checkpoint_interval: 50000,
    frame_capture_interval: 10000,
    reward_shaping: "default",
    observation_type: "image",
    action_space: "filtered",
    status: "completed",
    created_at: "2024-01-01T00:00:00Z",
    ...overrides,
  }
}

describe("useRunStats", () => {
  it("counts active runs correctly", () => {
    const runs: Run[] = [
      createRun({ status: "running" }),
      createRun({ status: "running" }),
      createRun({ status: "completed" }),
      createRun({ status: "failed" }),
    ]

    const stats = useRunStats(runs)
    expect(stats.activeCount).toBe(2)
    expect(stats.activeRuns).toHaveLength(2)
    expect(stats.activeRuns.every((r) => r.status === "running")).toBe(true)
  })

  it("counts completed runs correctly", () => {
    const runs: Run[] = [
      createRun({ status: "running" }),
      createRun({ status: "completed" }),
      createRun({ status: "completed" }),
      createRun({ status: "failed" }),
    ]

    const stats = useRunStats(runs)
    expect(stats.completedCount).toBe(2)
  })

  it("counts failed runs correctly", () => {
    const runs: Run[] = [
      createRun({ status: "running" }),
      createRun({ status: "completed" }),
      createRun({ status: "failed" }),
      createRun({ status: "failed" }),
      createRun({ status: "failed" }),
    ]

    const stats = useRunStats(runs)
    expect(stats.failedCount).toBe(3)
  })

  it("calculates total correctly", () => {
    const runs: Run[] = [
      createRun({ status: "running" }),
      createRun({ status: "completed" }),
      createRun({ status: "failed" }),
    ]

    const stats = useRunStats(runs)
    expect(stats.total).toBe(3)
  })

  it("handles empty runs array", () => {
    const stats = useRunStats([])
    expect(stats.total).toBe(0)
    expect(stats.activeCount).toBe(0)
    expect(stats.completedCount).toBe(0)
    expect(stats.failedCount).toBe(0)
    expect(stats.activeRuns).toEqual([])
  })

  it("handles all statuses correctly", () => {
    const runs: Run[] = [
      createRun({ status: "pending" }),
      createRun({ status: "running" }),
      createRun({ status: "completed" }),
      createRun({ status: "failed" }),
      createRun({ status: "stopped" }),
    ]

    const stats = useRunStats(runs)
    expect(stats.total).toBe(5)
    expect(stats.activeCount).toBe(1)
    expect(stats.completedCount).toBe(1)
    expect(stats.failedCount).toBe(1)
    expect(stats.activeRuns[0].status).toBe("running")
  })
})
