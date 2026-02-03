import { z } from "zod"

// =============================================================================
// Enums
// =============================================================================

export const RunStatusSchema = z.enum([
  "pending",
  "running",
  "paused",
  "completed",
  "failed",
  "stopped",
])
export type RunStatus = z.infer<typeof RunStatusSchema>

export const AlgorithmSchema = z.enum(["PPO", "A2C", "DQN"])
export type Algorithm = z.infer<typeof AlgorithmSchema>

export const DeviceSchema = z.enum(["cuda", "cpu"])
export type Device = z.infer<typeof DeviceSchema>

export const ObservationTypeSchema = z.enum(["image", "ram"])
export type ObservationType = z.infer<typeof ObservationTypeSchema>

export const ActionSpaceSchema = z.enum(["filtered", "discrete", "multi_binary"])
export type ActionSpace = z.infer<typeof ActionSpaceSchema>

export const RewardShapingSchema = z.enum(["default"])
export type RewardShaping = z.infer<typeof RewardShapingSchema>

// =============================================================================
// ROM Schemas
// =============================================================================

export const RomSchema = z.object({
  id: z.string(),
  name: z.string(),
  system: z.string(),
  playable: z.boolean().optional().default(false),
  states: z.array(z.string()).optional(),
})
export type Rom = z.infer<typeof RomSchema>

export const RomListSchema = z.array(RomSchema)

export const RomImportResponseSchema = z.object({
  message: z.string(),
  imported: z.number(),
})
export type RomImportResponse = z.infer<typeof RomImportResponseSchema>

// =============================================================================
// Run Schemas
// =============================================================================

// Hyperparams schema matching backend defaults with constraints
export const RunHyperparamsSchema = z.object({
  learning_rate: z.number().min(1e-7).max(1).default(0.0003),
  n_steps: z.number().int().min(1).max(16384).default(2048),
  batch_size: z.number().int().min(1).max(1024).default(64),
  n_epochs: z.number().int().min(1).max(100).default(10),
  gamma: z.number().min(0).max(1).default(0.99),
  gae_lambda: z.number().min(0).max(1).default(0.95),
  clip_range: z.number().min(0).max(1).default(0.2),
  ent_coef: z.number().min(0).max(1).default(0.0),
  vf_coef: z.number().min(0).max(1).default(0.5),
  max_grad_norm: z.number().min(0).max(10).default(0.5),
})
export type RunHyperparams = z.infer<typeof RunHyperparamsSchema>

// Run response schema matching backend RunResponse
export const RunSchema = z.object({
  id: z.string().uuid(),
  rom: z.string().min(1),
  state: z.string().min(1),
  algorithm: AlgorithmSchema,
  hyperparams: RunHyperparamsSchema,
  n_envs: z.number().int().min(1).max(64),
  max_steps: z.number().int().min(1).max(100_000_000),
  checkpoint_interval: z.number().int().min(1000).max(10_000_000),
  frame_capture_interval: z.number().int().min(1).max(100_000),
  reward_shaping: RewardShapingSchema,
  observation_type: ObservationTypeSchema,
  action_space: ActionSpaceSchema,
  status: RunStatusSchema,
  created_at: z.string().datetime(),
  started_at: z.string().datetime().nullable().optional(),
  completed_at: z.string().datetime().nullable().optional(),
  pid: z.number().int().positive().nullable().optional(),
  error: z.string().nullable().optional(),
})
export type Run = z.infer<typeof RunSchema>

export const RunListSchema = z.array(RunSchema)

// Default hyperparams values
export const DEFAULT_HYPERPARAMS = {
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
}

// Run creation schema matching backend RunCreate/RunConfig
export const RunCreateSchema = z.object({
  rom: z.string().min(1, "ROM is required"),
  state: z.string().min(1, "State is required"),
  algorithm: AlgorithmSchema.default("PPO"),
  hyperparams: RunHyperparamsSchema.default(DEFAULT_HYPERPARAMS),
  n_envs: z.number().int().min(1).max(64).default(1),
  max_steps: z.number().int().min(1).max(100_000_000).default(1_000_000),
  checkpoint_interval: z.number().int().min(1000).max(10_000_000).default(50_000),
  frame_capture_interval: z.number().int().min(1).max(100_000).default(10_000),
  reward_shaping: RewardShapingSchema.default("default"),
  observation_type: ObservationTypeSchema.default("image"),
  action_space: ActionSpaceSchema.default("filtered"),
})
export type RunCreate = z.infer<typeof RunCreateSchema>
export type RunCreateInput = z.input<typeof RunCreateSchema>

export const RunMetricsSchema = z.object({
  step: z.number().int().min(0),
  timestamp: z.number().min(0).optional(),
  reward: z.number(),
  avg_reward: z.number(),
  best_reward: z.number(),
  fps: z.number().min(0),
  loss: z.number().optional(),
  epsilon: z.number().min(0).max(1).optional(),
})
export type RunMetrics = z.infer<typeof RunMetricsSchema>

export const RunWsMessageSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("metrics"), data: RunMetricsSchema }),
  z.object({ type: z.literal("status"), status: RunStatusSchema }),
  z.object({ type: z.literal("error"), error: z.string() }),
])
export type RunWsMessage = z.infer<typeof RunWsMessageSchema>

// =============================================================================
// Config Schemas
// =============================================================================

export const ConfigSchema = z.object({
  default_device: DeviceSchema,
  max_concurrent_runs: z.number().int().min(1).max(16),
  storage_path: z.string().min(1),
  roms_path: z.string().min(1).nullable().optional(),
  default_algorithm: AlgorithmSchema,
  default_hyperparams: RunHyperparamsSchema.optional(),
})
export type Config = z.infer<typeof ConfigSchema>

export const ConfigUpdateSchema = ConfigSchema.partial()
export type ConfigUpdate = z.infer<typeof ConfigUpdateSchema>

// =============================================================================
// Emulator Schema
// =============================================================================

export const EmulatorListSchema = z.array(z.string())
export type EmulatorList = z.infer<typeof EmulatorListSchema>

// =============================================================================
// Activity Event Types
// =============================================================================

export const ActivityEventTypeSchema = z.enum([
  "run_started",
  "run_stopped",
  "run_completed",
  "run_failed",
  "milestone_reward",
  "milestone_steps",
])
export type ActivityEventType = z.infer<typeof ActivityEventTypeSchema>

export const ActivityEventSchema = z.object({
  id: z.string(),
  type: ActivityEventTypeSchema,
  runId: z.string(),
  runName: z.string(),
  timestamp: z.string(),
  message: z.string(),
  data: z.record(z.string(), z.unknown()).optional(),
})
export type ActivityEvent = z.infer<typeof ActivityEventSchema>

// Milestone thresholds
export const REWARD_MILESTONES = [0, 10, 50, 100, 250, 500, 1000] as const
export const STEP_MILESTONES = [10_000, 50_000, 100_000, 500_000, 1_000_000] as const

// =============================================================================
// Derived Types & Utilities
// =============================================================================

export const RUN_STATUS_VARIANTS: Record<
  RunStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  running: "default",
  paused: "secondary",
  completed: "secondary",
  failed: "destructive",
  stopped: "outline",
  pending: "outline",
}

export function isRunActive(run: Run): boolean {
  return run.status === "running"
}

export function isRunTerminal(run: Run): boolean {
  return ["completed", "failed", "stopped"].includes(run.status)
}

export function formatSteps(steps: number): string {
  if (steps >= 1_000_000) {
    return `${(steps / 1_000_000).toFixed(1)}M`
  }
  if (steps >= 1_000) {
    return `${(steps / 1_000).toFixed(1)}K`
  }
  return steps.toLocaleString()
}
