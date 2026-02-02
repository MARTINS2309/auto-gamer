import { z } from "zod"

// =============================================================================
// Enums
// =============================================================================

export const RunStatusSchema = z.enum([
  "pending",
  "running",
  "completed",
  "failed",
  "stopped",
])
export type RunStatus = z.infer<typeof RunStatusSchema>

export const AlgorithmSchema = z.enum(["PPO", "A2C", "DQN"])
export type Algorithm = z.infer<typeof AlgorithmSchema>

export const DeviceSchema = z.enum(["cuda", "cpu"])
export type Device = z.infer<typeof DeviceSchema>

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

export const RunSchema = z.object({
  id: z.string(),
  rom_id: z.string(),
  rom_name: z.string(),
  state: z.string(),
  algorithm: z.string(),
  status: RunStatusSchema,
  steps: z.number(),
  best_reward: z.number(),
  avg_reward: z.number(),
  fps: z.number(),
  created_at: z.string(),
  started_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
  error: z.string().nullable().optional(),
})
export type Run = z.infer<typeof RunSchema>

export const RunListSchema = z.array(RunSchema)

export const RunCreateSchema = z.object({
  rom_id: z.string().min(1, "ROM is required"),
  state: z.string().min(1, "State is required"),
  algorithm: z.string().optional(),
})
export type RunCreate = z.infer<typeof RunCreateSchema>

export const RunMetricsSchema = z.object({
  step: z.number(),
  reward: z.number(),
  avg_reward: z.number(),
  best_reward: z.number(),
  fps: z.number(),
  loss: z.number().optional(),
  epsilon: z.number().optional(),
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
  default_algorithm: z.string(),
  default_device: z.string(),
  storage_path: z.string(),
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
// Derived Types & Utilities
// =============================================================================

export const RUN_STATUS_VARIANTS: Record<
  RunStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  running: "default",
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
