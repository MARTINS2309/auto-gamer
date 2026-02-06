import { z } from "zod"
import type { components } from "./api-types"

/**
 * Zod schemas for runtime API response validation.
 *
 * Uses `satisfies z.ZodType<Partial<API[...]>>` pattern to:
 * 1. Validate at compile-time that schema matches API structure
 * 2. Keep Zod's precise inferred types (with defaults, etc.)
 * 3. Allow minor field-level differences (Partial relaxes exact match)
 *
 * To regenerate API types: pnpm generate-types
 * Types auto-regenerate on API server restart.
 */

// API type aliases for cleaner access
type API = components["schemas"]

// Compile-time assertion: ensures Zod output is assignable to API type
// Usage: export type _Check = Assert<z.infer<typeof Schema>, Partial<API["Type"]>>
type Assert<T extends U, U> = T

// =============================================================================
// Enums (re-export API types, Zod for runtime validation)
// =============================================================================

export const RunStatusSchema = z.enum([
  "pending",
  "running",
  "paused",
  "completed",
  "failed",
  "stopped",
])
export type RunStatus = API["RunStatus"]

export const AlgorithmSchema = z.enum(["PPO", "A2C", "DQN"])
export type Algorithm = API["Algorithm"]

export const DeviceSchema = z.enum(["auto", "cuda", "cpu"])
export type Device = API["Device"]

export const ObservationTypeSchema = z.enum(["image", "ram"])
export type ObservationType = API["ObservationType"]

export const ActionSpaceSchema = z.enum(["filtered", "discrete", "multi_binary"])
export type ActionSpace = API["ActionSpace"]

export const RewardShapingSchema = z.enum(["default"])
export type RewardShaping = API["RewardShaping"]

// =============================================================================
// Game Library Schemas (Union of ROMs + Connectors)
// =============================================================================

/**
 * Game status based on ROM and connector availability:
 * - playable: Has ROM, can play manually
 * - trainable: Has ROM + connector, can train AI
 * - connector_only: Has connector but no ROM (need to acquire)
 */
export const GameStatusSchema = z.enum(["playable", "trainable", "connector_only"])
export type GameStatus = z.infer<typeof GameStatusSchema>

export const SyncStatusSchema = z.enum(["pending", "syncing", "synced", "failed", "manual"])
export type SyncStatus = z.infer<typeof SyncStatusSchema>

export const ThumbnailStatusSchema = z.enum(["pending", "synced", "failed"])
export type ThumbnailStatus = z.infer<typeof ThumbnailStatusSchema>

// Lightweight list item for grid view
export const GameListItemSchema = z.object({
  id: z.string(),
  system: z.string(),
  display_name: z.string(),
  // Availability flags
  has_rom: z.boolean(),      // User owns this ROM
  has_connector: z.boolean(), // Connector exists for training
  status: GameStatusSchema,   // Derived: playable | trainable | connector_only
  // Connector info (if available)
  connector_id: z.string().nullable().optional(), // Link to stable-retro connector
  states: z.array(z.string()).default([]), // Available save states for training
  // Metadata sync
  sync_status: SyncStatusSchema,
  // Essential metadata for cards
  rating: z.number().nullable().optional(),
  genres: z.array(z.string()).default([]),
  release_date: z.string().nullable().optional(),
  developer: z.string().nullable().optional(),
  // Thumbnail
  thumbnail_url: z.string().nullable().optional(),
})
export type GameListItem = z.infer<typeof GameListItemSchema>

// Legacy alias for backwards compatibility
export const RomListItemSchema = GameListItemSchema
export type RomListItem = GameListItem

// Full game response with all metadata
export const GameSchema = z.object({
  id: z.string(),
  system: z.string(),
  display_name: z.string(),
  // Availability flags
  has_rom: z.boolean(),       // User owns this ROM
  has_connector: z.boolean(), // Connector exists for training
  status: GameStatusSchema,   // Derived: playable | trainable | connector_only
  // Connector info
  connector_id: z.string().nullable().optional(), // Link to stable-retro connector
  states: z.array(z.string()).default([]), // Available save states
  // Sync status
  sync_status: SyncStatusSchema,
  sync_error: z.string().nullable().optional(),
  synced_at: z.string().nullable().optional(),
  // IGDB Metadata
  igdb_id: z.number().int().nullable().optional(),
  igdb_name: z.string().nullable().optional(),
  summary: z.string().nullable().optional(),
  storyline: z.string().nullable().optional(),
  rating: z.number().nullable().optional(),
  rating_count: z.number().int().nullable().optional(),
  genres: z.array(z.string()).default([]),
  themes: z.array(z.string()).default([]),
  game_modes: z.array(z.string()).default([]),
  player_perspectives: z.array(z.string()).default([]),
  platforms: z.array(z.string()).default([]),
  release_date: z.string().nullable().optional(),
  developer: z.string().nullable().optional(),
  publisher: z.string().nullable().optional(),
  cover_url: z.string().nullable().optional(),
  screenshot_urls: z.array(z.string()).default([]),
  // Thumbnail
  thumbnail_url: z.string().nullable().optional(),
  thumbnail_status: ThumbnailStatusSchema.default("pending"),
})
export type Game = z.infer<typeof GameSchema>

// Legacy aliases for backwards compatibility
export const RomSchema = GameSchema
export type Rom = Game

// Sync status response with detailed metadata breakdown
export const RomSyncStatusSchema = z.object({
  is_syncing: z.boolean(),
  current: z.string().nullable().optional(),
  completed: z.number().int().default(0),

  // Game counts by category
  total: z.number().int().default(0),
  total_connectors: z.number().int().default(0),
  total_roms: z.number().int().default(0), // User's ROM files
  trainable: z.number().int().default(0),
  playable_only: z.number().int().default(0),
  connector_only: z.number().int().default(0),

  // Sync status
  synced: z.number().int().default(0),
  pending: z.number().int().default(0),
  failed: z.number().int().default(0),

  // Metadata coverage
  with_igdb: z.number().int().default(0),
  with_name: z.number().int().default(0),
  with_year: z.number().int().default(0),
  with_rating: z.number().int().default(0),
  with_developer: z.number().int().default(0),
  with_summary: z.number().int().default(0),
  with_genres: z.number().int().default(0),

  // Thumbnail coverage
  with_thumbnail: z.number().int().default(0),
  missing_thumbnails: z.number().int().default(0),
})
export type RomSyncStatus = z.infer<typeof RomSyncStatusSchema>

// Metadata Response
export const GameMetadataResponseSchema = z.object({
  game_id: z.string(),
  system: z.string(),
  name: z.string(),
  summary: z.string().nullable().optional(),
  storyline: z.string().nullable().optional(),
  rating: z.number().nullable().optional(),
  rating_count: z.number().int().nullable().optional(),
  genres: z.array(z.string()).default([]),
  themes: z.array(z.string()).default([]),
  game_modes: z.array(z.string()).default([]),
  player_perspectives: z.array(z.string()).default([]),
  platforms: z.array(z.string()).default([]),
  release_date: z.string().nullable().optional(),
  developer: z.string().nullable().optional(),
  publisher: z.string().nullable().optional(),
  cover_url: z.string().nullable().optional(),
  screenshot_urls: z.array(z.string()).default([]),
  players: z.string().nullable().optional(),
  estimated_playtime: z.number().int().nullable().optional(),
  source: z.string(),
  cached: z.boolean().default(true),
})
export type GameMetadataResponse = API["GameMetadataResponse"]

export const MetadataStatsSchema = z.object({
  total_cached: z.number().int(),
  by_source: z.record(z.string(), z.number().int()),
})
export type MetadataStats = z.infer<typeof MetadataStatsSchema>

// IGDB search candidate for manual correction
export const IGDBCandidateSchema = z.object({
  id: z.number().int(),
  name: z.string(),
  cover_url: z.string().nullable().optional(),
  release_date: z.string().nullable().optional(),
  platforms: z.array(z.string()).default([]),
})
export type IGDBCandidate = z.infer<typeof IGDBCandidateSchema>

export const RomListSchema = z.array(RomListItemSchema)
export const RomListItemListSchema = z.array(RomListItemSchema)

export const RomImportResponseSchema = z.object({
  message: z.string(),
  imported: z.number(),
  queued_for_sync: z.number().optional(),
  syncing: z.boolean().optional(),
})
export type RomImportResponse = z.infer<typeof RomImportResponseSchema>

export const RomScanResponseSchema = z.object({
  message: z.string(),
  queued_for_sync: z.number(),
  syncing: z.boolean(),
})
export type RomScanResponse = z.infer<typeof RomScanResponseSchema>

// =============================================================================
// Run Schemas
// =============================================================================

// =============================================================================
// Algorithm-Specific Hyperparameters (from SB3 documentation)
// https://stable-baselines3.readthedocs.io/en/master/
// =============================================================================

export const PPOHyperparamsSchema = z.object({
  learning_rate: z.number().positive().default(0.0003),
  n_steps: z.number().int().min(1).default(2048),
  batch_size: z.number().int().min(1).default(64),
  n_epochs: z.number().int().min(1).default(10),
  gamma: z.number().min(0).max(1).default(0.99),
  gae_lambda: z.number().min(0).max(1).default(0.95),
  clip_range: z.number().min(0).max(1).default(0.2),
  clip_range_vf: z.number().min(0).max(1).nullable().optional(),
  normalize_advantage: z.boolean().default(true),
  ent_coef: z.number().min(0).default(0.0),
  vf_coef: z.number().min(0).default(0.5),
  max_grad_norm: z.number().min(0).default(0.5),
  use_sde: z.boolean().default(false),
  sde_sample_freq: z.number().int().min(-1).default(-1),
  target_kl: z.number().positive().nullable().optional(),
})
export type PPOHyperparams = z.infer<typeof PPOHyperparamsSchema>

export const A2CHyperparamsSchema = z.object({
  learning_rate: z.number().positive().default(0.0007),
  n_steps: z.number().int().min(1).default(5),
  gamma: z.number().min(0).max(1).default(0.99),
  gae_lambda: z.number().min(0).max(1).default(1.0),
  ent_coef: z.number().min(0).default(0.0),
  vf_coef: z.number().min(0).default(0.5),
  max_grad_norm: z.number().min(0).default(0.5),
  rms_prop_eps: z.number().positive().default(1e-5),
  use_rms_prop: z.boolean().default(true),
  use_sde: z.boolean().default(false),
  sde_sample_freq: z.number().int().min(-1).default(-1),
  normalize_advantage: z.boolean().default(false),
})
export type A2CHyperparams = z.infer<typeof A2CHyperparamsSchema>

export const DQNHyperparamsSchema = z.object({
  learning_rate: z.number().positive().default(0.0001),
  buffer_size: z.number().int().min(1).default(1_000_000),
  learning_starts: z.number().int().min(0).default(100),
  batch_size: z.number().int().min(1).default(32),
  tau: z.number().min(0).max(1).default(1.0),
  gamma: z.number().min(0).max(1).default(0.99),
  train_freq: z.number().int().min(1).default(4),
  gradient_steps: z.number().int().min(-1).default(1),
  target_update_interval: z.number().int().min(1).default(10_000),
  exploration_fraction: z.number().min(0).max(1).default(0.1),
  exploration_initial_eps: z.number().min(0).max(1).default(1.0),
  exploration_final_eps: z.number().min(0).max(1).default(0.05),
  max_grad_norm: z.number().min(0).default(10.0),
})
export type DQNHyperparams = z.infer<typeof DQNHyperparamsSchema>

// Legacy compatibility - maps to PPO defaults
export const RunHyperparamsSchema = z.object({
  learning_rate: z.number().positive().default(0.0003),
  n_steps: z.number().int().min(1).default(2048),
  batch_size: z.number().int().min(1).default(64),
  n_epochs: z.number().int().min(1).default(10),
  gamma: z.number().min(0).max(1).default(0.99),
  gae_lambda: z.number().min(0).max(1).default(0.95),
  clip_range: z.number().min(0).max(1).default(0.2),
  ent_coef: z.number().min(0).default(0.0),
  vf_coef: z.number().min(0).default(0.5),
  max_grad_norm: z.number().min(0).default(0.5),
})
export type RunHyperparams = API["RunHyperparams"]

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
  created_at: z.string(), // ISO datetime string from Python
  started_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
  pid: z.number().int().positive().nullable().optional(),
  error: z.string().nullable().optional(),
})
export type Run = Assert<z.infer<typeof RunSchema>, Partial<API["RunResponse"]>>

export const RunListSchema = z.array(RunSchema)

// Default hyperparams by algorithm (from SB3 documentation)
export const DEFAULT_PPO_HYPERPARAMS: PPOHyperparams = {
  learning_rate: 0.0003,
  n_steps: 2048,
  batch_size: 64,
  n_epochs: 10,
  gamma: 0.99,
  gae_lambda: 0.95,
  clip_range: 0.2,
  clip_range_vf: null,
  normalize_advantage: true,
  ent_coef: 0.0,
  vf_coef: 0.5,
  max_grad_norm: 0.5,
  use_sde: false,
  sde_sample_freq: -1,
  target_kl: null,
}

export const DEFAULT_A2C_HYPERPARAMS: A2CHyperparams = {
  learning_rate: 0.0007,
  n_steps: 5,
  gamma: 0.99,
  gae_lambda: 1.0,
  ent_coef: 0.0,
  vf_coef: 0.5,
  max_grad_norm: 0.5,
  rms_prop_eps: 1e-5,
  use_rms_prop: true,
  use_sde: false,
  sde_sample_freq: -1,
  normalize_advantage: false,
}

export const DEFAULT_DQN_HYPERPARAMS: DQNHyperparams = {
  learning_rate: 0.0001,
  buffer_size: 1_000_000,
  learning_starts: 100,
  batch_size: 32,
  tau: 1.0,
  gamma: 0.99,
  train_freq: 4,
  gradient_steps: 1,
  target_update_interval: 10_000,
  exploration_fraction: 0.1,
  exploration_initial_eps: 1.0,
  exploration_final_eps: 0.05,
  max_grad_norm: 10.0,
}

// Legacy compatibility alias
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
export type RunCreate = API["RunCreate"]
export type RunCreateInput = z.input<typeof RunCreateSchema>

export const RunMetricsSchema = z.object({
  step: z.number().int().min(0),
  timestamp: z.number().min(0),
  reward: z.number().nullable(),
  avg_reward: z.number().nullable(),
  best_reward: z.number().nullable(),
  fps: z.number().min(0).nullable(),
  loss: z.number().optional().nullable(),
  epsilon: z.number().min(0).max(1).optional().nullable(),
  details: z.record(z.string(), z.any()).optional().nullable(),
  type: z.string().default("metric"),
})
export type RunMetrics = Assert<z.infer<typeof RunMetricsSchema>, Partial<API["MetricPoint"]>>

export const RunWsMessageSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("metrics"), data: RunMetricsSchema }),
  z.object({ type: z.literal("status"), status: RunStatusSchema }),
  z.object({ type: z.literal("error"), error: z.string() }),
])
export type RunWsMessage = z.infer<typeof RunWsMessageSchema>

// =============================================================================
// Input Configuration Schemas
// =============================================================================

export const KeyboardMappingSchema = z.object({
  up: z.string().default("UP"),
  down: z.string().default("DOWN"),
  left: z.string().default("LEFT"),
  right: z.string().default("RIGHT"),
  a: z.string().default("x"),
  b: z.string().nullable().default("z"),
  x: z.string().nullable().default("s"),
  y: z.string().nullable().default("a"),
  l: z.string().nullable().default("q"),
  r: z.string().nullable().default("w"),
  start: z.string().default("RETURN"),
  select: z.string().nullable().default("RSHIFT"),
  c: z.string().nullable().default(null),
  z_btn: z.string().nullable().default(null),
})
export type KeyboardMapping = API["KeyboardMapping"]

export const ControllerConfigSchema = z.object({
  enabled: z.boolean().default(true),
  deadzone: z.number().min(0).max(0.5).default(0.15),
  a_button: z.number().int().default(0),
  b_button: z.number().int().default(1),
  x_button: z.number().int().default(2),
  y_button: z.number().int().default(3),
  l_button: z.number().int().default(4),
  r_button: z.number().int().default(5),
  start_button: z.number().int().default(7),
  select_button: z.number().int().default(6),
  c_button: z.number().int().default(8),
  z_button: z.number().int().default(9),
})
export type ControllerConfig = API["ControllerConfig"]

export const InputConfigSchema = z.object({
  keyboard_mappings: z.record(z.string(), KeyboardMappingSchema).default({}),
  controller: ControllerConfigSchema.default({
    enabled: true,
    deadzone: 0.15,
    a_button: 0,
    b_button: 1,
    x_button: 2,
    y_button: 3,
    l_button: 4,
    r_button: 5,
    start_button: 7,
    select_button: 6,
    c_button: 8,
    z_button: 9,
  }),
})
export type InputConfig = API["InputConfig"]

export const SupportedSystemsSchema = z.object({
  systems: z.array(z.string()),
  buttons: z.record(z.string(), z.array(z.string())),
})
export type SupportedSystems = z.infer<typeof SupportedSystemsSchema>

// =============================================================================
// Config Schemas
// =============================================================================

export const ConfigSchema = z.object({
  default_device: DeviceSchema,
  max_concurrent_runs: z.number().int().min(1).max(16),
  storage_path: z.string().min(1),
  roms_path: z.string().min(1).nullable().optional(),
  recording_path: z.string().min(1).nullable().optional(),
  default_algorithm: AlgorithmSchema,
  default_hyperparams: RunHyperparamsSchema.optional(),
  input: InputConfigSchema.optional(),
})
export type Config = Assert<z.infer<typeof ConfigSchema>, Partial<API["GlobalConfig-Output"]>>

export const ConfigUpdateSchema = ConfigSchema.partial()
export type ConfigUpdate = Partial<Config>

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

// =============================================================================
// Game Status Utilities
// =============================================================================

export const GAME_STATUS_VARIANTS: Record<
  GameStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  trainable: "default",    // Ready for AI training
  playable: "secondary",   // Can play, needs connector for training
  connector_only: "outline", // Need ROM to use
}

export const GAME_STATUS_LABELS: Record<GameStatus, string> = {
  trainable: "Ready to Train",
  playable: "Playable",
  connector_only: "Need ROM",
}

/** Game has ROM - can be played */
export function isPlayable(game: GameListItem | Game): boolean {
  return game.has_rom
}

/** Game has ROM + connector - can train AI */
export function isTrainable(game: GameListItem | Game): boolean {
  return game.has_rom && game.has_connector
}

/** Game has connector but no ROM */
export function isConnectorOnly(game: GameListItem | Game): boolean {
  return game.has_connector && !game.has_rom
}

/** Derive status from flags (for backend or testing) */
export function deriveGameStatus(has_rom: boolean, has_connector: boolean): GameStatus {
  if (has_rom && has_connector) return "trainable"
  if (has_rom) return "playable"
  return "connector_only"
}

// Filter presets for UI
export const GAME_FILTERS = {
  all: () => true,
  playable: (g: GameListItem) => g.has_rom,
  trainable: (g: GameListItem) => g.has_rom && g.has_connector,
  needsConnector: (g: GameListItem) => g.has_rom && !g.has_connector,
  needsRom: (g: GameListItem) => !g.has_rom && g.has_connector,
} as const

// =============================================================================
// Play Session Schemas
// =============================================================================

export const PlaySessionResponseSchema = z.object({
  session_id: z.string(),
  rom_id: z.string(),
  state: z.string().nullable(),
  message: z.string(),
})
export type PlaySessionResponse = API["PlaySessionResponse"]

export const PlaySessionInfoSchema = z.object({
  id: z.string(),
  rom_id: z.string(),
  state: z.string().nullable(),
  started_at: z.string(),
  is_alive: z.boolean(),
})
export type PlaySessionInfo = API["SessionInfoResponse"]

// =============================================================================
// Filesystem Schemas
// =============================================================================

export const DirectoryEntrySchema = z.object({
  name: z.string(),
  path: z.string(),
  is_dir: z.boolean(),
  is_readable: z.boolean(),
})
export type DirectoryEntry = API["DirectoryEntry"]

export const DirectoryListResponseSchema = z.object({
  path: z.string(),
  parent: z.string().nullable(),
  entries: z.array(DirectoryEntrySchema),
})
export type DirectoryListResponse = API["DirectoryListResponse"]

export const PathValidationResponseSchema = z.object({
  valid: z.boolean(),
  error: z.string().nullable().optional(),
  path: z.string(),
  resolved: z.string().nullable().optional(),
  exists: z.boolean().optional(),
  is_dir: z.boolean().optional(),
  is_readable: z.boolean().optional(),
  is_writable: z.boolean().optional(),
})
export type PathValidationResponse = z.infer<typeof PathValidationResponseSchema>
