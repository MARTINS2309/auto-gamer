import { z } from "zod"
import type { paths, operations, components } from "./api-types"
import {
  RomSchema,
  RomListSchema,
  RomImportResponseSchema,
  RomScanResponseSchema,
  RomSyncStatusSchema,
  GameMetadataResponseSchema,
  MetadataStatsSchema,
  IGDBCandidateSchema,
  RunSchema,
  RunListSchema,
  RunCreateSchema,
  RunMetricsSchema,
  RecordingSchema,
  AgentSchema,
  AgentListSchema,
  AgentCreateSchema,
  GameStateSchema,
  ConfigSchema,
  EmulatorListSchema,
  PlaySessionResponseSchema,
  PlaySessionInfoSchema,
  DirectoryListResponseSchema,
  PathValidationResponseSchema,
  type Rom,
  type RomListItem,
  type Run,
  type RunCreate,
  type RunCreateInput,
  type RunMetrics,
  type RunStatus,
  type Recording,
  type Agent,
  type AgentCreateInput,
  type AgentUpdate,
  type Config,
  type ConfigUpdate,
  type RomImportResponse,
  type RomScanResponse,
  type RomSyncStatus,
  type GameMetadataResponse,
  type MetadataStats,
  type IGDBCandidate,
  type PlaySessionResponse,
  type PlaySessionInfo,
  type DirectoryListResponse,
  type PathValidationResponse,
} from "./schemas"

// =============================================================================
// API Type Helpers - Extract types from OpenAPI spec
// =============================================================================

/** Extract successful response type from an operation */
type ApiResponse<Op> = Op extends {
  responses: { 200: { content: { "application/json": infer R } } }
}
  ? R
  : Op extends { responses: { 204: unknown } }
    ? void
    : never

/** Extract request body type from an operation */
type ApiRequestBody<Op> = Op extends {
  requestBody: { content: { "application/json": infer B } }
}
  ? B
  : never

/** Extract path parameters from an operation */
type ApiPathParams<Op> = Op extends { parameters: { path: infer P } } ? P : Record<string, never>

/** Extract query parameters from an operation */
type ApiQueryParams<Op> = Op extends { parameters: { query?: infer Q } } ? Q : Record<string, never>

// Re-export for use in hooks/components
export type { paths, operations, components }
export type { ApiResponse, ApiRequestBody, ApiPathParams, ApiQueryParams }

// =============================================================================
// Configuration
// =============================================================================

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"
const WS_BASE = API_BASE.replace(/^http/, "ws")

// =============================================================================
// SSE Types
// =============================================================================

export interface ImportProgressEvent {
  phase: string
  current?: number
  total?: number
  message?: string
  result?: Record<string, unknown>
}

export interface ImportStreamCallbacks {
  onStart?: (phase: string, message: string) => void
  onProgress?: (phase: string, current: number, total: number, message: string) => void
  onComplete?: (phase: string, result: Record<string, unknown>) => void
  onDone?: (result: {
    imported: number
    connectors: number
    user_roms: number
    queued_for_sync: number
    syncing: boolean
  }) => void
  onError?: (message: string) => void
}

// =============================================================================
// API Client
// =============================================================================

export class ApiError extends Error {
  status?: number
  code?: string

  constructor(message: string, status?: number, code?: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.code = code
  }
}

async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  options?: RequestInit
): Promise<T> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    })

    if (!res.ok) {
      const text = await res.text()
      let message = text || res.statusText
      let code: string | undefined
      try {
        const parsed = JSON.parse(text)
        message = parsed.detail || message
        code = parsed.code
      } catch { /* not JSON */ }
      throw new ApiError(message, res.status, code)
    }

    const data = await res.json()
    return schema.parse(data)
  } catch (err) {
    if (err instanceof ApiError) throw err
    if (err instanceof z.ZodError) {
      console.error("API response validation failed:", err.issues)
      throw new ApiError(`Invalid API response: ${err.issues[0]?.message}`)
    }
    if (err instanceof TypeError && err.message.includes("fetch")) {
      throw new ApiError("API server not available. Start the API with: pnpm dev:api", undefined, "NETWORK_ERROR")
    }
    throw err
  }
}

async function requestVoid(path: string, options?: RequestInit): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    })

    if (!res.ok) {
      const error = await res.text()
      throw new ApiError(error || res.statusText, res.status)
    }
  } catch (err) {
    if (err instanceof ApiError) throw err
    if (err instanceof TypeError && err.message.includes("fetch")) {
      throw new ApiError("API server not available. Start the API with: pnpm dev:api", undefined, "NETWORK_ERROR")
    }
    throw err
  }
}

// =============================================================================
// API Methods
// =============================================================================

export const api = {
  roms: {
    list: (includeConnectors: boolean = true): Promise<RomListItem[]> => {
      const params = new URLSearchParams({ include_connectors: String(includeConnectors) })
      return request(`/api/roms?${params}`, RomListSchema)
    },

    get: (id: string): Promise<Rom> => request(`/api/roms/${id}`, RomSchema),

    getStates: (id: string) =>
      request(`/api/roms/${id}/states`, z.array(GameStateSchema)),

    import: (path?: string): Promise<RomImportResponse> =>
      request("/api/roms/import", RomImportResponseSchema, {
        method: "POST",
        body: JSON.stringify({ path }),
      }),

    scan: (): Promise<RomScanResponse> =>
      request("/api/roms/scan", RomScanResponseSchema, { method: "POST" }),

    // Sync operations
    syncStatus: (): Promise<RomSyncStatus> =>
      request("/api/roms/sync/status", RomSyncStatusSchema),

    syncAll: (includeUnmatchedConnectors: boolean = false): Promise<{ message: string }> => {
      const params = new URLSearchParams({ include_unmatched_connectors: String(includeUnmatchedConnectors) })
      return request(`/api/roms/sync?${params}`, z.object({ message: z.string() }), { method: "POST" })
    },

    syncThumbnails: (): Promise<{ message: string; count: number }> =>
      request("/api/roms/sync/thumbnails", z.object({ message: z.string(), count: z.number() }), { method: "POST" }),

    syncOne: (id: string, force: boolean = false): Promise<{ message: string; status: string }> =>
      request(
        `/api/roms/${id}/sync?force=${force}`,
        z.object({ message: z.string(), status: z.string() }),
        { method: "POST" }
      ),

    // Manual correction
    resync: (id: string, data: { igdb_id?: number; libretro_name?: string }): Promise<{ message: string }> =>
      request(`/api/roms/${id}/resync`, z.object({ message: z.string() }), {
        method: "POST",
        body: JSON.stringify(data),
      }),

    searchIGDB: (id: string, query?: string): Promise<{ candidates: IGDBCandidate[] }> => {
      const params = query ? `?query=${encodeURIComponent(query)}` : ""
      return request(
        `/api/roms/${id}/search-igdb${params}`,
        z.object({ candidates: z.array(IGDBCandidateSchema) })
      )
    },

    /**
     * Stream ROM import progress via SSE.
     * Returns an AbortController to cancel the stream.
     */
    importStream: (
      path: string | undefined,
      callbacks: ImportStreamCallbacks,
      options?: { skipRetroImport?: boolean }
    ): AbortController => {
      const controller = new AbortController()
      const params = new URLSearchParams()
      if (path) params.set("path", path)
      // Skip retro import by default - it's slow and memory-heavy
      if (options?.skipRetroImport !== false) params.set("skip_retro_import", "true")
      const url = `${API_BASE}/api/roms/import/stream?${params.toString()}`

      const eventSource = new EventSource(url)

      eventSource.addEventListener("start", (event) => {
        const data = JSON.parse(event.data)
        callbacks.onStart?.(data.phase, data.message)
      })

      eventSource.addEventListener("progress", (event) => {
        const data = JSON.parse(event.data)
        callbacks.onProgress?.(data.phase, data.current, data.total, data.message)
      })

      eventSource.addEventListener("complete", (event) => {
        const data = JSON.parse(event.data)
        callbacks.onComplete?.(data.phase, data.result)
      })

      eventSource.addEventListener("done", (event) => {
        const data = JSON.parse(event.data)
        callbacks.onDone?.(data)
        eventSource.close()
      })

      eventSource.addEventListener("error", (event) => {
        if (event instanceof MessageEvent) {
          const data = JSON.parse(event.data)
          callbacks.onError?.(data.message)
        } else {
          callbacks.onError?.("Connection error")
        }
        eventSource.close()
      })

      // Handle EventSource errors (connection issues)
      eventSource.onerror = () => {
        callbacks.onError?.("Connection lost")
        eventSource.close()
      }

      // Allow aborting the stream
      controller.signal.addEventListener("abort", () => {
        eventSource.close()
      })

      return controller
    },
  },

  agents: {
    list: (sortBy?: string): Promise<Agent[]> => {
      const params = sortBy ? `?sort_by=${sortBy}` : ""
      return request(`/api/agents${params}`, AgentListSchema)
    },

    get: (id: string): Promise<Agent> => request(`/api/agents/${id}`, AgentSchema),

    create: (data: AgentCreateInput): Promise<Agent> => {
      const validated = AgentCreateSchema.parse(data)
      return request("/api/agents", AgentSchema, {
        method: "POST",
        body: JSON.stringify(validated),
      })
    },

    update: (id: string, data: AgentUpdate): Promise<Agent> =>
      request(`/api/agents/${id}`, AgentSchema, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    delete: (id: string): Promise<void> =>
      requestVoid(`/api/agents/${id}`, { method: "DELETE" }),
  },

  runs: {
    list: (agentId?: string): Promise<Run[]> => {
      const params = agentId ? `?agent_id=${agentId}` : ""
      return request(`/api/runs${params}`, RunListSchema)
    },

    get: (id: string): Promise<Run> => request(`/api/runs/${id}`, RunSchema),

    create: (data: RunCreateInput): Promise<Run> => {
      // Parse to validate and apply defaults
      const validated = RunCreateSchema.parse(data)
      return request("/api/runs", RunSchema, {
        method: "POST",
        body: JSON.stringify(validated),
      })
    },

    stop: (id: string): Promise<Run> =>
      request(`/api/runs/${id}/stop`, RunSchema, { method: "POST" }),

    update: (id: string, updates: { hyperparams: Record<string, unknown> }): Promise<Run> =>
      request(`/api/runs/${id}`, RunSchema, {
        method: "PATCH",
        body: JSON.stringify(updates)
      }),

    resume: (id: string): Promise<Run> =>
      request(`/api/runs/${id}/resume`, RunSchema, { method: "POST" }), // Assuming backend returns RunSchema or similar

    delete: (id: string): Promise<void> =>
      requestVoid(`/api/runs/${id}`, { method: "DELETE" }),

    metrics: (id: string): Promise<RunMetrics[]> =>
      request(`/api/runs/${id}/metrics`, z.array(RunMetricsSchema)),

    recordings: (id: string): Promise<Recording[]> =>
      request(`/api/runs/${id}/recordings`, z.array(RecordingSchema)),
  },

  emulators: {
    list: (): Promise<string[]> => request("/api/emulators", EmulatorListSchema),
  },

  metadata: {
    get: (system: string, gameId: string): Promise<GameMetadataResponse> =>
      request(`/api/metadata/game/${system}/${gameId}`, GameMetadataResponseSchema),

    batch: (games: Array<{ game_id: string; system: string }>): Promise<GameMetadataResponse[]> =>
      request("/api/metadata/batch", z.array(GameMetadataResponseSchema), {
        method: "POST",
        body: JSON.stringify(games),
      }),

    stats: (): Promise<MetadataStats> =>
      request("/api/metadata/stats", MetadataStatsSchema),

    cached: (limit: number = 50, offset: number = 0): Promise<GameMetadataResponse[]> => {
      const params = new URLSearchParams({
        limit: String(limit),
        offset: String(offset),
      })
      return request(`/api/metadata/cached?${params}`, z.array(GameMetadataResponseSchema))
    },
  },

  config: {
    get: (): Promise<Config> => request("/api/config", ConfigSchema),

    update: (data: ConfigUpdate): Promise<Config> =>
      request("/api/config", ConfigSchema, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
  },

  play: {
    start: (romId: string, state?: string, players?: number): Promise<PlaySessionResponse> => {
      const params = new URLSearchParams()
      if (state) params.append("state", state)
      if (players && players > 1) params.append("players", String(players))
      const query = params.toString() ? `?${params.toString()}` : ""
      return request(`/api/play/${romId}${query}`, PlaySessionResponseSchema, {
        method: "POST",
      })
    },

    stop: (sessionId: string): Promise<void> =>
      requestVoid(`/api/play/${sessionId}`, { method: "DELETE" }),

    get: (sessionId: string): Promise<PlaySessionInfo> =>
      request(`/api/play/${sessionId}`, PlaySessionInfoSchema),

    list: (): Promise<PlaySessionInfo[]> =>
      request("/api/play", z.array(PlaySessionInfoSchema)),
  },

  filesystem: {
    list: (path: string = "~", showHidden: boolean = false, dirsOnly: boolean = true): Promise<DirectoryListResponse> => {
      const params = new URLSearchParams({
        path,
        show_hidden: String(showHidden),
        dirs_only: String(dirsOnly),
      })
      return request(`/api/filesystem/list?${params}`, DirectoryListResponseSchema)
    },

    home: (): Promise<{ path: string }> =>
      request("/api/filesystem/home", z.object({ path: z.string() })),

    validate: (path: string, mustExist: boolean = false, mustBeDir: boolean = false): Promise<PathValidationResponse> => {
      const params = new URLSearchParams({
        path,
        must_exist: String(mustExist),
        must_be_dir: String(mustBeDir),
      })
      return request(`/api/filesystem/validate?${params}`, PathValidationResponseSchema)
    },
  },

  integration: {
    launch: (opts?: { romId?: string; connectorId?: string }) =>
      request("/api/integration/launch", z.object({
        status: z.string(),
        pid: z.number().optional(),
        message: z.string().optional(),
      }), { method: "POST", body: JSON.stringify({ rom_id: opts?.romId, connector_id: opts?.connectorId }) }),

    status: () =>
      request("/api/integration/status", z.object({
        running: z.boolean(),
        pid: z.number().optional(),
        exit_code: z.number().optional(),
      })),

    stop: () =>
      requestVoid("/api/integration/stop", { method: "POST" }),

    rescan: () =>
      requestVoid("/api/integration/rescan", { method: "POST" }),
  },
}

// =============================================================================
// WebSocket
// =============================================================================

export interface FrameInfo {
  width: number
  height: number
  /** Pixels for the first env (backward compat) */
  pixels: Uint8Array
  /** Number of envs in this frame message */
  envCount: number
  /** Per-env pixel arrays */
  envFrames: Uint8Array[]
}

/** Mutable frame buffer for zero-allocation rendering. Written by WS handler, read by rAF loops. */
export interface FrameBuffer {
  width: number
  height: number
  envCount: number
  /** Stable per-env pixel buffers — data is copied in, not replaced */
  envFrames: Uint8Array[]
  /** Incremented each WS frame — canvases compare to detect new data */
  generation: number
  // ── Ring buffer for all-env playback ──
  /** Circular buffer of all-env frame snapshots (lazily allocated per slot) */
  ring: (Uint8Array | undefined)[]
  /** Next write position in ring (0..ringCapacity-1) */
  ringHead: number
  /** Number of valid frames currently in the ring (0..ringCapacity) */
  ringSize: number
  /** Maximum frames the ring can hold */
  ringCapacity: number
  /** Monotonically increasing counter — total frames ever pushed to ring */
  ringGeneration: number
}

export interface RunWebSocketCallbacks {
  onMetrics?: (metrics: RunMetrics) => void
  onFrame?: (frame: FrameInfo) => void
  /** Mutable frame buffer — WS handler writes directly, no React state */
  frameBuffer?: FrameBuffer
  onPhase?: (phase: string, timestamp: number) => void
  onStatus?: (status: RunStatus) => void
  onError?: (error: string) => void
  onConnectionError?: (event: Event) => void
}

export function createRunWebSocket(
  runId: string,
  callbacks: RunWebSocketCallbacks
): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/ws/runs/${runId}`)
  ws.binaryType = "arraybuffer"

  ws.onmessage = (event) => {
    try {
      // Binary message = multi-env RGB frames
      // Protocol: [n_envs:u8][width:u16LE][height:u16LE][env0_pixels][env1_pixels]...
      if (event.data instanceof ArrayBuffer) {
        const buf = event.data as ArrayBuffer
        if (buf.byteLength < 5) return
        const view = new DataView(buf)
        const nEnvs = view.getUint8(0)
        const w = view.getUint16(1, true)
        const h = view.getUint16(3, true)
        const frameSize = w * h * 3
        if (nEnvs < 1 || nEnvs > 64 || buf.byteLength < 5 + nEnvs * frameSize) return

        // Fast path: write into mutable FrameBuffer (no React state, no allocation)
        const fb = callbacks.frameBuffer
        if (fb) {
          fb.width = w
          fb.height = h
          fb.envCount = nEnvs
          // Resize env buffers only when dimensions or count change
          if (fb.envFrames.length !== nEnvs || fb.envFrames[0]?.length !== frameSize) {
            fb.envFrames = Array.from({ length: nEnvs }, () => new Uint8Array(frameSize))
          }
          // Copy pixel data into stable buffers (avoids creating new typed array views)
          const src = new Uint8Array(buf)
          for (let i = 0; i < nEnvs; i++) {
            fb.envFrames[i].set(src.subarray(5 + i * frameSize, 5 + (i + 1) * frameSize))
          }
          fb.generation++

          // Push ALL envs into ring buffer for playback (scrubbing works for every env)
          if (fb.ringCapacity > 0 && nEnvs > 0) {
            const totalSize = nEnvs * frameSize
            const slot = fb.ring[fb.ringHead]
            if (!slot || slot.length !== totalSize) {
              fb.ring[fb.ringHead] = new Uint8Array(totalSize)
            }
            const dst = fb.ring[fb.ringHead]!
            for (let i = 0; i < nEnvs; i++) {
              dst.set(fb.envFrames[i], i * frameSize)
            }
            fb.ringHead = (fb.ringHead + 1) % fb.ringCapacity
            if (fb.ringSize < fb.ringCapacity) fb.ringSize++
            fb.ringGeneration++
          }

          return
        }

        // Fallback: callback-based (legacy path)
        const envFrames: Uint8Array[] = []
        for (let i = 0; i < nEnvs; i++) {
          envFrames.push(new Uint8Array(buf, 5 + i * frameSize, frameSize))
        }
        callbacks.onFrame?.({
          width: w,
          height: h,
          pixels: envFrames[0],
          envCount: nEnvs,
          envFrames,
        })
        return
      }

      // Text message = JSON (metrics, status, phase, error)
      const data = JSON.parse(event.data)

      if ("step" in data) {
        callbacks.onMetrics?.(data)
      } else if (data.type === "phase") {
        callbacks.onPhase?.(data.phase, data.timestamp)
      } else if (data.type === "status") {
        callbacks.onStatus?.(data.status)
      } else if (data.type === "error") {
        callbacks.onError?.(data.error)
      }
    } catch {
      console.error("Failed to parse WebSocket message:", event.data)
    }
  }

  ws.onerror = (event) => {
    console.error("WebSocket error:", event)
    callbacks.onConnectionError?.(event)
  }

  return ws
}

// =============================================================================
// Re-exports
// =============================================================================

export type {
  Rom,
  RomListItem,
  Run,
  RunCreate,
  RunMetrics,
  RunStatus,
  Recording,
  Agent,
  AgentCreateInput,
  AgentUpdate,
  Config,
  ConfigUpdate,
  RomImportResponse,
  RomScanResponse,
  RomSyncStatus,
  GameMetadataResponse,
  MetadataStats,
  IGDBCandidate,
  PlaySessionResponse,
  PlaySessionInfo,
  DirectoryListResponse,
  PathValidationResponse,
}
export { ApiError as ApiClientError }
