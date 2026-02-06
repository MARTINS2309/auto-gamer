import { useCallback, useEffect, useRef, useState } from "react"
import { api } from "@/lib/api"
import { toast } from "sonner"

// Browser KeyboardEvent.code → stable-retro button name
const KEY_CODE_TO_BUTTON: Record<string, string> = {
  ArrowUp: "UP",
  ArrowDown: "DOWN",
  ArrowLeft: "LEFT",
  ArrowRight: "RIGHT",
  KeyX: "A",
  KeyZ: "B",
  KeyS: "X",
  KeyA: "Y",
  KeyQ: "L",
  KeyW: "R",
  Enter: "START",
  ShiftRight: "SELECT",
  ShiftLeft: "SELECT",
  KeyD: "C",
  KeyC: "Z",
  Backspace: "MODE",
}

// Standard Gamepad API button index → stable-retro button name
// Uses Nintendo physical layout (bottom=B, right=A) which matches retro consoles
const GAMEPAD_BUTTON_MAP: Record<number, string[]> = {
  0:  ["B"],              // Bottom face (Xbox A / PS Cross)
  1:  ["A"],              // Right face  (Xbox B / PS Circle)
  2:  ["Y"],              // Left face   (Xbox X / PS Square)
  3:  ["X"],              // Top face    (Xbox Y / PS Triangle)
  4:  ["L"],              // Left bumper
  5:  ["R"],              // Right bumper
  6:  ["C"],              // Left trigger  (Genesis C)
  7:  ["Z"],              // Right trigger (Genesis Z)
  8:  ["SELECT", "MODE"], // Back/Select
  9:  ["START"],          // Start
  12: ["UP"],             // D-pad up
  13: ["DOWN"],           // D-pad down
  14: ["LEFT"],           // D-pad left
  15: ["RIGHT"],          // D-pad right
}
const AXIS_DEADZONE = 0.5

interface SessionInfo {
  game_name: string
  system: string
  rom_name: string
  buttons: (string | null)[]
}

interface SearchResult {
  name: string
  num_results: number
  unique: { address: number; type: string } | null
  results: Array<{ address: number; types: string[] }>
}

interface WatchValues {
  [name: string]: number | null
}

interface SavedState {
  name: string
  size: number
}

export function useConnectorBuilder() {
  const [session, setSession] = useState<SessionInfo | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [screenImage, setScreenImage] = useState<string | null>(null)
  const [frameCount, setFrameCount] = useState(0)
  const [searches, setSearches] = useState<Record<string, SearchResult>>({})
  const [watchValues, setWatchValues] = useState<WatchValues>({})
  const [watches, setWatches] = useState<Record<string, { address: number; type: string }>>({})
  const [savedStates, setSavedStates] = useState<SavedState[]>([])
  const [isPlaying, setIsPlaying] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)
  const playIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const screenIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // --- Keyboard input tracking ---

  const pressedButtonsRef = useRef<Set<string>>(new Set())
  const buttonsRef = useRef<(string | null)[]>([])

  // Keep buttonsRef in sync with session
  useEffect(() => {
    buttonsRef.current = session?.buttons ?? []
  }, [session?.buttons])

  // Build action array from keyboard + gamepad state
  // Array includes null positions (always 0) to match env.action_space indices
  const getAction = useCallback((): number[] => {
    const buttons = buttonsRef.current
    if (buttons.length === 0) return []

    // Start with keyboard pressed buttons
    const active = new Set(pressedButtonsRef.current)

    // Merge gamepad state (polling-based API)
    try {
      const gamepads = navigator.getGamepads()
      for (const gp of gamepads) {
        if (!gp) continue
        // Face buttons, bumpers, triggers, d-pad
        for (const [idxStr, retroNames] of Object.entries(GAMEPAD_BUTTON_MAP)) {
          const idx = Number(idxStr)
          if (gp.buttons[idx]?.pressed) {
            for (const name of retroNames) active.add(name)
          }
        }
        // Left stick as d-pad
        if (gp.axes[0] < -AXIS_DEADZONE) active.add("LEFT")
        if (gp.axes[0] > AXIS_DEADZONE) active.add("RIGHT")
        if (gp.axes[1] < -AXIS_DEADZONE) active.add("UP")
        if (gp.axes[1] > AXIS_DEADZONE) active.add("DOWN")
      }
    } catch { /* Gamepad API not available */ }

    // null positions (placeholder slots in env.buttons) always get 0
    return buttons.map(btn => btn !== null && active.has(btn) ? 1 : 0)
  }, [])

  // Keyboard listeners — active when session exists
  useEffect(() => {
    if (!session) return

    const pressed = pressedButtonsRef.current

    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't capture when typing in an input/textarea
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return

      const button = KEY_CODE_TO_BUTTON[e.code]
      if (button && buttonsRef.current.some(b => b === button)) {
        e.preventDefault()
        pressed.add(button)
      }
    }

    const handleKeyUp = (e: KeyboardEvent) => {
      const button = KEY_CODE_TO_BUTTON[e.code]
      if (button) {
        pressed.delete(button)
      }
    }

    // Clear pressed keys when window loses focus
    const handleBlur = () => {
      pressed.clear()
    }

    document.addEventListener("keydown", handleKeyDown)
    document.addEventListener("keyup", handleKeyUp)
    window.addEventListener("blur", handleBlur)

    return () => {
      document.removeEventListener("keydown", handleKeyDown)
      document.removeEventListener("keyup", handleKeyUp)
      window.removeEventListener("blur", handleBlur)
      pressed.clear()
    }
  }, [session])

  // --- Session lifecycle ---

  const startSession = useCallback(async (romId: string) => {
    setIsStarting(true)
    setStartError(null)
    try {
      // Close any stale session first, then start fresh
      try { await api.builder.close() } catch { /* ignore */ }
      const result = await api.builder.start(romId)
      setSession(result)
      setFrameCount(0)
      setSearches({})
      setWatchValues({})
      setWatches({})
      setSavedStates([])
      // Fetch initial screen
      try {
        const screen = await api.builder.screen()
        setScreenImage(`data:image/jpeg;base64,${screen.image}`)
      } catch { /* ignore */ }
      toast.success(`Builder started for ${result.rom_name}`)
    } catch (e) {
      const msg = (e as Error).message
      setStartError(msg)
      toast.error(`Failed to start builder: ${msg}`)
    } finally {
      setIsStarting(false)
    }
  }, [])

  const closeSession = useCallback(async () => {
    try {
      // Stop play intervals inline
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current)
        playIntervalRef.current = null
      }
      if (screenIntervalRef.current) {
        clearInterval(screenIntervalRef.current)
        screenIntervalRef.current = null
      }
      setIsPlaying(false)
      await api.builder.close()
      setSession(null)
      setScreenImage(null)
      setFrameCount(0)
      setSearches({})
      setWatchValues({})
      setWatches({})
      setSavedStates([])
    } catch (e) {
      toast.error(`Failed to close session: ${(e as Error).message}`)
    }
  }, [])

  // --- Screen ---

  const refreshScreen = useCallback(async () => {
    try {
      const result = await api.builder.screen()
      setScreenImage(`data:image/jpeg;base64,${result.image}`)
    } catch { /* ignore screen errors during polling */ }
  }, [])

  // --- Step ---

  const stepFrames = useCallback(async (frames: number = 1, action?: number[]) => {
    try {
      const actionToSend = action ?? getAction()
      const result = await api.builder.step(frames, actionToSend)
      setFrameCount(result.frame)
      await refreshScreen()
      return result
    } catch (e) {
      toast.error(`Step failed: ${(e as Error).message}`)
      return null
    }
  }, [refreshScreen, getAction])

  // --- Auto-play (step continuously) ---

  const startPlaying = useCallback(() => {
    if (playIntervalRef.current) return
    setIsPlaying(true)
    // Step 5 frames every 50ms (~100fps emulator, ~20fps screen updates)
    playIntervalRef.current = setInterval(async () => {
      try {
        const result = await api.builder.step(5, getAction())
        setFrameCount(result.frame)
      } catch { /* ignore */ }
    }, 50)
    // Screen refresh at ~10fps
    screenIntervalRef.current = setInterval(refreshScreen, 100)
  }, [refreshScreen, getAction])

  const stopPlaying = useCallback(() => {
    setIsPlaying(false)
    if (playIntervalRef.current) {
      clearInterval(playIntervalRef.current)
      playIntervalRef.current = null
    }
    if (screenIntervalRef.current) {
      clearInterval(screenIntervalRef.current)
      screenIntervalRef.current = null
    }
    refreshScreen()
  }, [refreshScreen])

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current)
      if (screenIntervalRef.current) clearInterval(screenIntervalRef.current)
    }
  }, [])

  // --- Search ---

  const searchMemory = useCallback(async (name: string, value: number) => {
    try {
      const result = await api.builder.search(name, value)
      setSearches(prev => ({ ...prev, [name]: result }))
      return result
    } catch (e) {
      toast.error(`Search failed: ${(e as Error).message}`)
      return null
    }
  }, [])

  const deltaSearch = useCallback(async (name: string, op: string, ref: number) => {
    try {
      const result = await api.builder.deltaSearch(name, op, ref)
      setSearches(prev => ({ ...prev, [name]: result }))
      return result
    } catch (e) {
      toast.error(`Delta search failed: ${(e as Error).message}`)
      return null
    }
  }, [])

  const removeSearch = useCallback(async (name: string) => {
    try {
      await api.builder.removeSearch(name)
      setSearches(prev => {
        const next = { ...prev }
        delete next[name]
        return next
      })
    } catch (e) {
      toast.error(`Remove search failed: ${(e as Error).message}`)
    }
  }, [])

  // --- Watches ---

  const addWatch = useCallback(async (name: string, address: number, type: string) => {
    try {
      await api.builder.addWatch(name, address, type)
      setWatches(prev => ({ ...prev, [name]: { address, type } }))
    } catch (e) {
      toast.error(`Add watch failed: ${(e as Error).message}`)
    }
  }, [])

  const removeWatch = useCallback(async (name: string) => {
    try {
      await api.builder.removeWatch(name)
      setWatches(prev => {
        const next = { ...prev }
        delete next[name]
        return next
      })
      setWatchValues(prev => {
        const next = { ...prev }
        delete next[name]
        return next
      })
    } catch (e) {
      toast.error(`Remove watch failed: ${(e as Error).message}`)
    }
  }, [])

  const refreshWatches = useCallback(async () => {
    try {
      const values = await api.builder.readWatches()
      setWatchValues(values)
    } catch { /* ignore */ }
  }, [])

  // --- Rewards & Done Conditions ---

  const addReward = useCallback(async (variable: string, operation: string, reference: number, multiplier: number) => {
    try {
      await api.builder.addReward(variable, operation, reference, multiplier)
      toast.success("Reward added")
    } catch (e) {
      toast.error(`Add reward failed: ${(e as Error).message}`)
    }
  }, [])

  const addDoneCondition = useCallback(async (variable: string, operation: string, reference: number) => {
    try {
      await api.builder.addDoneCondition(variable, operation, reference)
      toast.success("Done condition added")
    } catch (e) {
      toast.error(`Add done condition failed: ${(e as Error).message}`)
    }
  }, [])

  // --- Save states ---

  const saveState = useCallback(async (name: string) => {
    try {
      const result = await api.builder.saveState(name)
      setSavedStates(prev => {
        const existing = prev.findIndex(s => s.name === name)
        if (existing >= 0) {
          const next = [...prev]
          next[existing] = result
          return next
        }
        return [...prev, result]
      })
      toast.success(`State "${name}" saved`)
    } catch (e) {
      toast.error(`Save state failed: ${(e as Error).message}`)
    }
  }, [])

  const loadState = useCallback(async (name: string) => {
    try {
      const result = await api.builder.loadState(name)
      setFrameCount(result.frame)
      await refreshScreen()
      toast.success(`State "${name}" loaded`)
    } catch (e) {
      toast.error(`Load state failed: ${(e as Error).message}`)
    }
  }, [refreshScreen])

  const refreshStates = useCallback(async () => {
    try {
      const states = await api.builder.listStates()
      setSavedStates(states)
    } catch { /* ignore */ }
  }, [])

  // --- Export ---

  const exportConnector = useCallback(async (connectorName?: string) => {
    try {
      const result = await api.builder.export(connectorName)
      toast.success(`Connector exported: ${result.connector_id}`)
      return result
    } catch (e) {
      toast.error(`Export failed: ${(e as Error).message}`)
      return null
    }
  }, [])

  return {
    // State
    session,
    isStarting,
    startError,
    screenImage,
    frameCount,
    searches,
    watchValues,
    watches,
    savedStates,
    isPlaying,

    // Actions
    startSession,
    closeSession,
    stepFrames,
    startPlaying,
    stopPlaying,
    refreshScreen,
    searchMemory,
    deltaSearch,
    removeSearch,
    addWatch,
    removeWatch,
    refreshWatches,
    addReward,
    addDoneCondition,
    saveState,
    loadState,
    refreshStates,
    exportConnector,
  }
}
