import { z } from "zod"
import {
  RomSchema,
  RomListSchema,
  RomImportResponseSchema,
  RunSchema,
  RunListSchema,
  RunCreateSchema,
  ConfigSchema,
  EmulatorListSchema,
  type Rom,
  type Run,
  type RunCreate,
  type RunMetrics,
  type RunStatus,
  type Config,
  type ConfigUpdate,
  type RomImportResponse,
} from "./schemas"

// =============================================================================
// Configuration
// =============================================================================

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"
const WS_BASE = API_BASE.replace(/^http/, "ws")

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
      const error = await res.text()
      throw new ApiError(error || res.statusText, res.status)
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
    list: (): Promise<Rom[]> => request("/api/roms", RomListSchema),

    get: (id: string): Promise<Rom> => request(`/api/roms/${id}`, RomSchema),

    getStates: (id: string): Promise<string[]> =>
      request(`/api/roms/${id}/states`, z.array(z.string())),

    import: (path: string): Promise<RomImportResponse> =>
      request("/api/roms/import", RomImportResponseSchema, {
        method: "POST",
        body: JSON.stringify({ path }),
      }),
  },

  runs: {
    list: (): Promise<Run[]> => request("/api/runs", RunListSchema),

    get: (id: string): Promise<Run> => request(`/api/runs/${id}`, RunSchema),

    create: (data: Partial<RunCreate> & { rom: string; state: string }): Promise<Run> => {
      // Parse to validate and apply defaults
      const validated = RunCreateSchema.parse(data)
      return request("/api/runs", RunSchema, {
        method: "POST",
        body: JSON.stringify(validated),
      })
    },

    stop: (id: string): Promise<Run> =>
      request(`/api/runs/${id}/stop`, RunSchema, { method: "POST" }),

    delete: (id: string): Promise<void> =>
      requestVoid(`/api/runs/${id}`, { method: "DELETE" }),
  },

  emulators: {
    list: (): Promise<string[]> => request("/api/emulators", EmulatorListSchema),
  },

  config: {
    get: (): Promise<Config> => request("/api/config", ConfigSchema),

    update: (data: ConfigUpdate): Promise<Config> =>
      request("/api/config", ConfigSchema, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
  },
}

// =============================================================================
// WebSocket
// =============================================================================

export interface RunWebSocketCallbacks {
  onMetrics?: (metrics: RunMetrics) => void
  onStatus?: (status: RunStatus) => void
  onError?: (error: string) => void
  onConnectionError?: (event: Event) => void
}

export function createRunWebSocket(
  runId: string,
  callbacks: RunWebSocketCallbacks
): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/ws/runs/${runId}`)

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)

      // Handle metrics message (has step field)
      if ("step" in data) {
        callbacks.onMetrics?.(data)
      }
      // Handle status message
      else if (data.type === "status") {
        callbacks.onStatus?.(data.status)
      }
      // Handle error message
      else if (data.type === "error") {
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

export type { Rom, Run, RunCreate, RunMetrics, RunStatus, Config, ConfigUpdate, RomImportResponse }
export { ApiError as ApiClientError }
