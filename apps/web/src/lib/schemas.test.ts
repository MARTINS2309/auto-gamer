import { describe, it, expect } from "vitest"
import {
  RunStatusSchema,
  GameSchema,
  RunSchema,
  RunCreateSchema,
  RunMetricsSchema,
  ConfigSchema,
  RUN_STATUS_VARIANTS,
  isRunActive,
  isRunTerminal,
  formatSteps,
  type Run,
} from "./schemas"

// =============================================================================
// Schema Validation Tests
// =============================================================================

describe("RunStatusSchema", () => {
  it("accepts valid statuses", () => {
    const validStatuses = ["pending", "running", "completed", "failed", "stopped"]
    validStatuses.forEach((status) => {
      expect(RunStatusSchema.parse(status)).toBe(status)
    })
  })

  it("rejects invalid status", () => {
    expect(() => RunStatusSchema.parse("invalid")).toThrow()
    expect(() => RunStatusSchema.parse("")).toThrow()
    expect(() => RunStatusSchema.parse(123)).toThrow()
  })
})

describe("GameSchema (RomSchema)", () => {
  it("parses valid game with ROM and connector", () => {
    const game = {
      id: "game-123",
      display_name: "Pokemon FireRed",
      system: "gba",
      has_rom: true,
      has_connector: true,
      status: "trainable",
      states: ["start", "mid-game"],
      sync_status: "synced",
    }
    const result = GameSchema.parse(game)
    expect(result.has_rom).toBe(true)
    expect(result.has_connector).toBe(true)
    expect(result.status).toBe("trainable")
  })

  it("parses game with ROM only (playable)", () => {
    const game = {
      id: "game-123",
      display_name: "Pokemon FireRed",
      system: "gba",
      has_rom: true,
      has_connector: false,
      status: "playable",
      sync_status: "synced",
    }
    const result = GameSchema.parse(game)
    expect(result.has_rom).toBe(true)
    expect(result.has_connector).toBe(false)
    expect(result.status).toBe("playable")
    expect(result.states).toEqual([]) // default
  })

  it("parses connector-only game", () => {
    const game = {
      id: "game-123",
      display_name: "Pokemon FireRed",
      system: "gba",
      has_rom: false,
      has_connector: true,
      status: "connector_only",
      sync_status: "pending",
    }
    const result = GameSchema.parse(game)
    expect(result.has_rom).toBe(false)
    expect(result.has_connector).toBe(true)
    expect(result.status).toBe("connector_only")
  })

  it("rejects missing required fields", () => {
    expect(() => GameSchema.parse({ id: "123" })).toThrow()
    expect(() => GameSchema.parse({ id: "123", display_name: "Test" })).toThrow()
  })
})

describe("RunSchema", () => {
  const validRun = {
    id: "550e8400-e29b-41d4-a716-446655440000", // Valid UUID
    rom: "pokemon-firered",
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
    status: "running",
    created_at: "2024-01-01T00:00:00Z",
  }

  it("parses valid run", () => {
    expect(RunSchema.parse(validRun)).toEqual(validRun)
  })

  it("handles nullable optional fields", () => {
    const run = {
      ...validRun,
      started_at: "2024-01-01T00:01:00Z",
      completed_at: null,
      pid: 12345,
      error: null,
    }
    const result = RunSchema.parse(run)
    expect(result.started_at).toBe("2024-01-01T00:01:00Z")
    expect(result.completed_at).toBeNull()
    expect(result.pid).toBe(12345)
    expect(result.error).toBeNull()
  })

  it("rejects invalid status in run", () => {
    expect(() => RunSchema.parse({ ...validRun, status: "invalid" })).toThrow()
  })

  it("rejects missing required fields", () => {
    const { id: _id, ...noId } = validRun
    expect(() => RunSchema.parse(noId)).toThrow()
  })
})

describe("RunCreateSchema", () => {
  it("parses valid run creation data with minimal fields", () => {
    const data = { rom: "pokemon-firered", state: "start" }
    const result = RunCreateSchema.parse(data)
    expect(result.rom).toBe("pokemon-firered")
    expect(result.state).toBe("start")
    expect(result.algorithm).toBe("PPO") // default
    expect(result.n_envs).toBe(1) // default
    expect(result.max_steps).toBe(1_000_000) // default
  })

  it("applies all defaults correctly", () => {
    const data = { rom: "pokemon-firered", state: "start" }
    const result = RunCreateSchema.parse(data)
    expect(result.hyperparams).toEqual({
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
    })
  })

  it("rejects empty rom", () => {
    expect(() => RunCreateSchema.parse({ rom: "", state: "start" })).toThrow()
  })

  it("rejects empty state", () => {
    expect(() => RunCreateSchema.parse({ rom: "rom-123", state: "" })).toThrow()
  })
})

describe("RunMetricsSchema", () => {
  it("parses valid metrics", () => {
    const metrics = {
      step: 1000,
      timestamp: 1704067200.0, // Required timestamp
      reward: 50.5,
      avg_reward: 45.0,
      best_reward: 100.0,
      fps: 60.0,
      loss: 0.05,
      epsilon: 0.1,
    }
    const result = RunMetricsSchema.parse(metrics)
    expect(result.step).toBe(1000)
    expect(result.timestamp).toBe(1704067200.0)
    expect(result.reward).toBe(50.5)
  })

  it("accepts missing optional fields", () => {
    const metrics = {
      step: 1000,
      timestamp: 1704067200.0, // Required
      reward: 50.5,
      avg_reward: 45.0,
      best_reward: 100.0,
      fps: 60.0,
    }
    const result = RunMetricsSchema.parse(metrics)
    expect(result.loss).toBeUndefined()
    expect(result.epsilon).toBeUndefined()
  })
})

describe("ConfigSchema", () => {
  it("parses valid config", () => {
    const config = {
      default_algorithm: "PPO",
      default_device: "cuda",
      storage_path: "/data/runs",
      max_concurrent_runs: 4, // Required field
    }
    expect(ConfigSchema.parse(config)).toEqual(config)
  })

  it("rejects missing fields", () => {
    expect(() => ConfigSchema.parse({ default_algorithm: "PPO" })).toThrow()
  })
})

// =============================================================================
// Utility Function Tests
// =============================================================================

describe("RUN_STATUS_VARIANTS", () => {
  it("maps all statuses to valid variants", () => {
    expect(RUN_STATUS_VARIANTS.running).toBe("default")
    expect(RUN_STATUS_VARIANTS.completed).toBe("secondary")
    expect(RUN_STATUS_VARIANTS.failed).toBe("destructive")
    expect(RUN_STATUS_VARIANTS.stopped).toBe("outline")
    expect(RUN_STATUS_VARIANTS.pending).toBe("outline")
  })
})

// Helper to create Run objects for utility function tests
const createTestRun = (status: string): Run => ({
  id: "550e8400-e29b-41d4-a716-446655440000", // Valid UUID
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
  status: status as Run["status"],
  created_at: "2024-01-01T00:00:00Z",
})

describe("isRunActive", () => {
  it("returns true for running status", () => {
    expect(isRunActive(createTestRun("running"))).toBe(true)
  })

  it("returns false for non-running statuses", () => {
    expect(isRunActive(createTestRun("pending"))).toBe(false)
    expect(isRunActive(createTestRun("completed"))).toBe(false)
    expect(isRunActive(createTestRun("failed"))).toBe(false)
    expect(isRunActive(createTestRun("stopped"))).toBe(false)
  })
})

describe("isRunTerminal", () => {
  it("returns true for terminal statuses", () => {
    expect(isRunTerminal(createTestRun("completed"))).toBe(true)
    expect(isRunTerminal(createTestRun("failed"))).toBe(true)
    expect(isRunTerminal(createTestRun("stopped"))).toBe(true)
  })

  it("returns false for non-terminal statuses", () => {
    expect(isRunTerminal(createTestRun("pending"))).toBe(false)
    expect(isRunTerminal(createTestRun("running"))).toBe(false)
  })
})

describe("formatSteps", () => {
  it("formats millions with M suffix", () => {
    expect(formatSteps(1_000_000)).toBe("1.0M")
    expect(formatSteps(1_500_000)).toBe("1.5M")
    expect(formatSteps(10_000_000)).toBe("10.0M")
    expect(formatSteps(1_234_567)).toBe("1.2M")
  })

  it("formats thousands with K suffix", () => {
    expect(formatSteps(1_000)).toBe("1.0K")
    expect(formatSteps(1_500)).toBe("1.5K")
    expect(formatSteps(999_999)).toBe("1000.0K")
    expect(formatSteps(50_000)).toBe("50.0K")
  })

  it("formats small numbers with locale string", () => {
    expect(formatSteps(0)).toBe("0")
    expect(formatSteps(1)).toBe("1")
    expect(formatSteps(999)).toBe("999")
  })
})
