import { useCallback, useEffect, useRef, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api, ApiError } from "@/lib/api"
import { toast } from "sonner"
import type { KeyboardMapping } from "@/lib/schemas"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"
const WS_BASE = API_BASE.replace(/^http/, "ws")

/**
 * Hook to start a play session.
 * Automatically forwards browser keyboard + gamepad input to the session via WebSocket.
 */
export function useStartPlaySession(keyboardMapping?: KeyboardMapping | null) {
  const queryClient = useQueryClient()
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)

  // Auto-forward keyboard + gamepad when a session is active
  useInputForwarding(activeSessionId, keyboardMapping)

  const mutation = useMutation({
    mutationFn: ({ romId, state, players }: { romId: string; state?: string; players?: number }) => {
      console.log("[Play] Starting play session:", { romId, state, players })
      return api.play.start(romId, state, players)
    },
    onSuccess: (data) => {
      console.log("[Play] Session started successfully:", data)
      setActiveSessionId(data.session_id)
      toast.success(data.message)
      queryClient.invalidateQueries({ queryKey: ["play-sessions"] })
    },
    onError: (error) => {
      console.error("[Play] Failed to start session:", error)
      if (error instanceof ApiError && error.code === "NEEDS_CONNECTOR") {
        toast.error("This game needs a connector before it can be played.", {
          action: {
            label: "Open Integration Tool",
            onClick: () => { api.integration.launch().catch(() => {}) },
          },
        })
      } else {
        toast.error(`Failed to start game: ${error.message}`)
      }
    },
  })

  const clearSession = useCallback(() => setActiveSessionId(null), [])

  return { ...mutation, activeSessionId, clearSession }
}

/**
 * Hook to stop a play session
 */
export function useStopPlaySession() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (sessionId: string) => api.play.stop(sessionId),
    onSuccess: () => {
      toast.success("Play session stopped")
      queryClient.invalidateQueries({ queryKey: ["play-sessions"] })
    },
    onError: (error) => {
      toast.error(`Failed to stop session: ${error.message}`)
    },
  })
}

/**
 * Hook to get a play session
 */
export function usePlaySession(sessionId: string | null) {
  return useQuery({
    queryKey: ["play-session", sessionId],
    queryFn: () => api.play.get(sessionId!),
    enabled: !!sessionId,
    refetchInterval: 5000, // Refresh every 5 seconds to check if still alive
  })
}

/**
 * Hook to list all play sessions
 */
export function usePlaySessions() {
  return useQuery({
    queryKey: ["play-sessions"],
    queryFn: () => api.play.list(),
    refetchInterval: 5000, // Refresh every 5 seconds
  })
}

/**
 * Hook to receive streamed play session frames via WebSocket.
 */
export function usePlayFrames(sessionId: string | null) {
  const [frameData, setFrameData] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [sessionEnded, setSessionEnded] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!sessionId) return

    const wsUrl = `${WS_BASE}/ws/play/frames/${sessionId}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      setSessionEnded(false)
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === "frame") {
          setFrameData(msg.data)
        } else if (msg.type === "status" && msg.status === "ended") {
          setSessionEnded(true)
        }
      } catch {
        // ignore parse errors
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
    }

    ws.onerror = () => {
      setIsConnected(false)
    }

    return () => {
      setFrameData(null)
      setIsConnected(false)
      setSessionEnded(false)
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close()
      }
      wsRef.current = null
    }
  }, [sessionId])

  return { frameData, isConnected, sessionEnded }
}

// =============================================================================
// Browser Input Forwarding (Keyboard + Gamepad)
// =============================================================================

// Config button name → retro button names (mirrors BUTTON_MAP in interactive_custom.py)
const CONFIG_TO_RETRO: Record<string, string[]> = {
  up: ["UP"],
  down: ["DOWN"],
  left: ["LEFT"],
  right: ["RIGHT"],
  a: ["A", "BUTTON"],
  b: ["B"],
  c: ["C"],
  x: ["X"],
  y: ["Y"],
  z_btn: ["Z"],
  l: ["L"],
  r: ["R"],
  start: ["START", "RESET"],
  select: ["SELECT", "MODE"],
}

// Map a KeyboardMapping → { browserKey → retroButtonNames[] }
// The mapping has config field names as keys and keyboard key names as values.
// Key names are like "x", "z", "UP", "RETURN", "RSHIFT".
function buildKeyToRetroMap(mapping: KeyboardMapping): Map<string, string[]> {
  const result = new Map<string, string[]>()
  for (const [configBtn, keyName] of Object.entries(mapping)) {
    if (!keyName) continue
    const retroNames = CONFIG_TO_RETRO[configBtn]
    if (!retroNames) continue
    // Normalize key name to match KeyboardEvent.key
    const browserKey = normalizeToBrowserKey(keyName)
    const existing = result.get(browserKey)
    if (existing) {
      existing.push(...retroNames)
    } else {
      result.set(browserKey, [...retroNames])
    }
  }
  return result
}

// Convert config key names (e.g. "RETURN", "RSHIFT", "UP", "x") to KeyboardEvent.key values
function normalizeToBrowserKey(keyName: string): string {
  const map: Record<string, string> = {
    RETURN: "Enter",
    ENTER: "Enter",
    RSHIFT: "Shift",
    LSHIFT: "Shift",
    SPACE: " ",
    TAB: "Tab",
    UP: "ArrowUp",
    DOWN: "ArrowDown",
    LEFT: "ArrowLeft",
    RIGHT: "ArrowRight",
    ESCAPE: "Escape",
    BACKSPACE: "Backspace",
  }
  return map[keyName.toUpperCase()] ?? keyName.toLowerCase()
}

// Standard Gamepad API button index → retro button names
const GAMEPAD_BUTTON_MAP: Record<number, string[]> = {
  0: ["B"],               // A / Cross (bottom)
  1: ["A", "BUTTON"],     // B / Circle (right)
  2: ["Y"],               // X / Square (left)
  3: ["X"],               // Y / Triangle (top)
  4: ["L"],               // Left bumper
  5: ["R"],               // Right bumper
  8: ["SELECT", "MODE"],  // Back / Select
  9: ["START", "RESET"],  // Start
  12: ["UP"],             // D-pad up
  13: ["DOWN"],           // D-pad down
  14: ["LEFT"],           // D-pad left
  15: ["RIGHT"],          // D-pad right
}

const STICK_DEADZONE = 0.5

let _gpDebugLogged = false

function readGamepadButtons(): string[] {
  const gamepads = navigator.getGamepads()
  let gp: Gamepad | null = null
  for (const g of gamepads) {
    if (g) { gp = g; break }
  }

  if (!_gpDebugLogged) {
    _gpDebugLogged = true
    const summary = Array.from(gamepads).map((g, i) =>
      g ? `[${i}] ${g.id} (${g.buttons.length} buttons, ${g.axes.length} axes, mapping=${g.mapping})` : `[${i}] null`
    )
    console.log("[Input] navigator.getGamepads():", summary)
    if (gp) console.log("[Input] Using gamepad at index", gamepads.indexOf(gp))
  }

  if (!gp) return []

  const pressed: string[] = []
  for (const [idx, retroNames] of Object.entries(GAMEPAD_BUTTON_MAP)) {
    const btn = gp.buttons[Number(idx)]
    if (btn?.pressed) pressed.push(...retroNames)
  }

  if (gp.axes.length >= 2) {
    if (gp.axes[0] < -STICK_DEADZONE) pressed.push("LEFT")
    if (gp.axes[0] > STICK_DEADZONE) pressed.push("RIGHT")
    if (gp.axes[1] < -STICK_DEADZONE) pressed.push("UP")
    if (gp.axes[1] > STICK_DEADZONE) pressed.push("DOWN")
  }

  return pressed
}

/**
 * Forwards browser keyboard + gamepad input over WebSocket to the play subprocess.
 */
export function useInputForwarding(sessionId: string | null, keyboardMapping?: KeyboardMapping | null) {
  const wsRef = useRef<WebSocket | null>(null)
  const rafRef = useRef<number>(0)
  const lastSentRef = useRef<string>("")
  const keysDownRef = useRef<Set<string>>(new Set())

  useEffect(() => {
    if (!sessionId) return

    // Build keyboard key → retro buttons map
    const keysDown = keysDownRef.current
    const keyToRetro = keyboardMapping ? buildKeyToRetroMap(keyboardMapping) : new Map<string, string[]>()

    if (keyToRetro.size > 0) {
      console.log("[Input] Keyboard mapping active:", Object.fromEntries(keyToRetro))
    }

    // Keyboard handlers
    const onKeyDown = (e: KeyboardEvent) => {
      // Don't capture when typing in inputs
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (keyToRetro.has(e.key)) {
        e.preventDefault()
        keysDown.add(e.key)
      }
    }
    const onKeyUp = (e: KeyboardEvent) => {
      keysDown.delete(e.key)
    }
    const onBlur = () => {
      keysDown.clear()
    }
    window.addEventListener("keydown", onKeyDown)
    window.addEventListener("keyup", onKeyUp)
    window.addEventListener("blur", onBlur)

    // Gamepad events
    const onConnect = (e: GamepadEvent) => {
      console.log("[Input] gamepadconnected:", e.gamepad.id)
      _gpDebugLogged = false
    }
    const onDisconnect = (e: GamepadEvent) => {
      console.log("[Input] gamepaddisconnected:", e.gamepad.id)
    }
    window.addEventListener("gamepadconnected", onConnect)
    window.addEventListener("gamepaddisconnected", onDisconnect)

    const wsUrl = `${WS_BASE}/ws/play/gamepad/${sessionId}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log("[Input] WebSocket connected for session", sessionId)
      _gpDebugLogged = false

      let sendCount = 0
      const poll = () => {
        if (ws.readyState !== WebSocket.OPEN) return

        // Merge keyboard + gamepad
        const buttons = new Set<string>()

        // Keyboard
        for (const key of keysDown) {
          const retro = keyToRetro.get(key)
          if (retro) retro.forEach(b => buttons.add(b))
        }

        // Gamepad
        for (const b of readGamepadButtons()) {
          buttons.add(b)
        }

        const arr = [...buttons]
        const key = arr.join(",")

        if (key !== lastSentRef.current) {
          lastSentRef.current = key
          ws.send(JSON.stringify(arr))
          sendCount++
          if (sendCount <= 10 || (arr.length > 0 && sendCount <= 50)) {
            console.log("[Input] Sent:", arr)
          }
        }

        rafRef.current = requestAnimationFrame(poll)
      }
      rafRef.current = requestAnimationFrame(poll)
    }

    ws.onclose = (e) => console.log("[Input] WebSocket closed:", e.code, e.reason)
    ws.onerror = (e) => console.warn("[Input] WebSocket error:", e)

    return () => {
      window.removeEventListener("keydown", onKeyDown)
      window.removeEventListener("keyup", onKeyUp)
      window.removeEventListener("blur", onBlur)
      window.removeEventListener("gamepadconnected", onConnect)
      window.removeEventListener("gamepaddisconnected", onDisconnect)
      cancelAnimationFrame(rafRef.current)
      lastSentRef.current = ""
      keysDown.clear()
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close()
      }
      wsRef.current = null
    }
  }, [sessionId, keyboardMapping])
}

/** @deprecated Use useInputForwarding instead */
export const useGamepadForwarding = (sessionId: string | null) => useInputForwarding(sessionId)
