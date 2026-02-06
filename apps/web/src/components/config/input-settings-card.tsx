import { useState, useEffect, useRef, useCallback, useMemo } from "react"
import { Keyboard, Gamepad2, RotateCcw, Wand2 } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"
import type { InputConfig, KeyboardMapping, ControllerConfig } from "@/lib/schemas"
import { CONTROLLER_COMPONENTS, SNESController } from "@/components/roms/controller-svgs"

// =============================================================================
// Constants
// =============================================================================

const SYSTEM_BUTTONS: Record<string, string[]> = {
  nes: ["up", "down", "left", "right", "a", "b", "start", "select"],
  snes: ["up", "down", "left", "right", "a", "b", "x", "y", "l", "r", "start", "select"],
  genesis: ["up", "down", "left", "right", "a", "b", "c", "x", "y", "z_btn", "start"],
  gba: ["up", "down", "left", "right", "a", "b", "l", "r", "start", "select"],
  gb: ["up", "down", "left", "right", "a", "b", "start", "select"],
  atari2600: ["up", "down", "left", "right", "a", "start", "select"],
  pce: ["up", "down", "left", "right", "a", "b", "start", "select"],
}

const SYSTEM_DISPLAY_NAMES: Record<string, string> = {
  nes: "NES",
  snes: "SNES",
  genesis: "Genesis",
  gba: "GBA",
  gb: "Game Boy",
  atari2600: "Atari 2600",
  pce: "PC Engine",
}

const SYSTEM_STORAGE_KEYS: Record<string, string> = {
  nes: "Nes",
  snes: "Snes",
  genesis: "Genesis",
  gba: "Gba",
  gb: "Gb",
  atari2600: "Atari2600",
  pce: "PCEngine",
}

const BUTTON_LABELS: Record<string, string> = {
  up: "Up",
  down: "Down",
  left: "Left",
  right: "Right",
  a: "A",
  b: "B",
  c: "C",
  x: "X",
  y: "Y",
  z_btn: "Z",
  l: "L",
  r: "R",
  start: "Start",
  select: "Select",
}

const DEFAULT_CONTROLLER: Required<ControllerConfig> = {
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
}

// Map system button names → controller config field names
const BUTTON_TO_FIELD: Record<string, keyof ControllerConfig> = {
  a: "a_button",
  b: "b_button",
  c: "c_button",
  x: "x_button",
  y: "y_button",
  z_btn: "z_button",
  l: "l_button",
  r: "r_button",
  start: "start_button",
  select: "select_button",
}

// =============================================================================
// Gamepad brand detection & button names
// =============================================================================

type GamepadBrand = "xbox" | "playstation" | "nintendo" | "generic"

function detectGamepadBrand(id: string): GamepadBrand {
  const lower = id.toLowerCase()
  if (lower.includes("045e") || lower.includes("xbox")) return "xbox"
  if (lower.includes("054c") || lower.includes("playstation") || lower.includes("dualshock") || lower.includes("dualsense")) return "playstation"
  if (lower.includes("057e") || lower.includes("nintendo") || lower.includes("pro controller") || lower.includes("joy-con")) return "nintendo"
  return "generic"
}

// Standard gamepad button names per brand (indices 0–16)
// Uses Unicode symbols for compact display in SVG labels
const GAMEPAD_BUTTON_NAMES: Record<GamepadBrand, string[]> = {
  xbox: ["A", "B", "X", "Y", "LB", "RB", "LT", "RT", "\u229E", "\u2630", "L3", "R3", "\u2191", "\u2193", "\u2190", "\u2192", "\u2302"],
  playstation: ["\u2715", "\u25CB", "\u25A1", "\u25B3", "L1", "R1", "L2", "R2", "\u2B06", "\u2630", "L3", "R3", "\u2191", "\u2193", "\u2190", "\u2192", "PS"],
  nintendo: ["B", "A", "Y", "X", "L", "R", "ZL", "ZR", "\u2212", "+", "L3", "R3", "\u2191", "\u2193", "\u2190", "\u2192", "\u2302"],
  generic: ["0", "1", "2", "3", "LB", "RB", "LT", "RT", "\u25C0", "\u25B6", "L3", "R3", "\u2191", "\u2193", "\u2190", "\u2192", "\u2302"],
}

function getButtonName(brand: GamepadBrand, index: number): string {
  return GAMEPAD_BUTTON_NAMES[brand][index] ?? `#${index}`
}

// =============================================================================
// Key name utilities
// =============================================================================

/** Convert browser KeyboardEvent.code to pyglet-compatible key name */
function browserKeyToPyglet(e: KeyboardEvent): string | null {
  if (e.code === "Escape") return null

  if (e.code.startsWith("Key")) return e.code.slice(3)
  if (e.code.startsWith("Digit")) return e.code.slice(5)

  const map: Record<string, string> = {
    ArrowUp: "UP",
    ArrowDown: "DOWN",
    ArrowLeft: "LEFT",
    ArrowRight: "RIGHT",
    Enter: "RETURN",
    NumpadEnter: "ENTER",
    ShiftLeft: "LSHIFT",
    ShiftRight: "RSHIFT",
    ControlLeft: "LCTRL",
    ControlRight: "RCTRL",
    AltLeft: "LALT",
    AltRight: "RALT",
    Tab: "TAB",
    Space: "SPACE",
    Backspace: "BACKSPACE",
    CapsLock: "CAPSLOCK",
    Comma: "COMMA",
    Period: "PERIOD",
    Slash: "SLASH",
    Semicolon: "SEMICOLON",
    Quote: "APOSTROPHE",
    BracketLeft: "BRACKETLEFT",
    BracketRight: "BRACKETRIGHT",
    Backslash: "BACKSLASH",
    Minus: "MINUS",
    Equal: "EQUAL",
    Backquote: "GRAVE",
  }
  return map[e.code] ?? e.code
}

/** Display-friendly label for a pyglet key name */
function displayKey(key: string | null | undefined): string {
  if (!key) return "—"
  const display: Record<string, string> = {
    UP: "↑", DOWN: "↓", LEFT: "←", RIGHT: "→",
    RETURN: "Enter", RSHIFT: "R Shift", LSHIFT: "L Shift",
    SPACE: "Space", TAB: "Tab", ESCAPE: "Esc",
    BACKSPACE: "⌫", LCTRL: "L Ctrl", RCTRL: "R Ctrl",
    LALT: "L Alt", RALT: "R Alt", CAPSLOCK: "Caps",
    COMMA: ",", PERIOD: ".", SLASH: "/",
    SEMICOLON: ";", APOSTROPHE: "'", MINUS: "-", EQUAL: "=",
    GRAVE: "`", BRACKETLEFT: "[", BRACKETRIGHT: "]", BACKSLASH: "\\",
  }
  return display[key.toUpperCase()] ?? key.toUpperCase()
}

// =============================================================================
// Key Capture Input
// =============================================================================

function KeyCaptureInput({
  value,
  onChange,
  label,
}: {
  value: string | null | undefined
  onChange: (key: string) => void
  label: string
}) {
  const [capturing, setCapturing] = useState(false)

  useEffect(() => {
    if (!capturing) return
    const handler = (e: KeyboardEvent) => {
      e.preventDefault()
      e.stopPropagation()
      const key = browserKeyToPyglet(e)
      if (key) onChange(key)
      setCapturing(false)
    }
    const blur = () => setCapturing(false)
    window.addEventListener("keydown", handler, true)
    window.addEventListener("blur", blur)
    return () => {
      window.removeEventListener("keydown", handler, true)
      window.removeEventListener("blur", blur)
    }
  }, [capturing, onChange])

  return (
    <div className="space-y-1">
      <Label className="text-xs">{label}</Label>
      <button
        type="button"
        onClick={() => setCapturing(true)}
        className={cn(
          "flex h-8 w-full items-center justify-center border font-mono text-sm transition-all",
          capturing
            ? "border-primary bg-primary/10 text-primary animate-pulse"
            : "border-input bg-background hover:bg-accent hover:text-accent-foreground",
        )}
      >
        {capturing ? "..." : displayKey(value)}
      </button>
    </div>
  )
}

// =============================================================================
// Gamepad Capture Input
// =============================================================================

function GamepadCaptureInput({
  value,
  onChange,
  label,
  disabled,
  brand = "generic",
}: {
  value: number
  onChange: (button: number) => void
  label: string
  disabled?: boolean
  brand?: GamepadBrand
}) {
  const [capturing, setCapturing] = useState(false)
  const rafRef = useRef<number>(0)

  useEffect(() => {
    if (!capturing) return

    // Record which buttons are already held so we only detect new presses
    const held = new Set<number>()
    for (const gp of navigator.getGamepads()) {
      if (!gp) continue
      gp.buttons.forEach((btn, i) => { if (btn.pressed) held.add(i) })
    }

    const poll = () => {
      for (const gp of navigator.getGamepads()) {
        if (!gp) continue
        for (let i = 0; i < gp.buttons.length; i++) {
          if (gp.buttons[i].pressed && !held.has(i)) {
            onChange(i)
            setCapturing(false)
            return
          }
        }
      }
      rafRef.current = requestAnimationFrame(poll)
    }
    rafRef.current = requestAnimationFrame(poll)
    return () => cancelAnimationFrame(rafRef.current)
  }, [capturing, onChange])

  // Cancel on escape
  useEffect(() => {
    if (!capturing) return
    const handler = (e: KeyboardEvent) => {
      if (e.code === "Escape") { e.preventDefault(); setCapturing(false) }
    }
    window.addEventListener("keydown", handler, true)
    return () => window.removeEventListener("keydown", handler, true)
  }, [capturing])

  return (
    <div className="space-y-1">
      <Label className="text-xs">{label}</Label>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setCapturing(!capturing)}
        className={cn(
          "flex h-8 w-full items-center justify-center border font-mono text-sm transition-all",
          capturing
            ? "border-primary bg-primary/10 text-primary animate-pulse"
            : "border-input bg-background hover:bg-accent hover:text-accent-foreground",
          disabled && "opacity-50 cursor-not-allowed",
        )}
      >
        {capturing ? "Press..." : getButtonName(brand, value)}
      </button>
    </div>
  )
}

// =============================================================================
// Gamepad Status Hook
// =============================================================================

function useGamepadStatus() {
  const [connected, setConnected] = useState(false)
  const [name, setName] = useState<string | null>(null)
  const [brand, setBrand] = useState<GamepadBrand>("generic")

  useEffect(() => {
    const check = () => {
      for (const gp of navigator.getGamepads()) {
        if (gp?.connected) {
          setConnected(true)
          setName(gp.id)
          setBrand(detectGamepadBrand(gp.id))
          return
        }
      }
      setConnected(false)
      setName(null)
      setBrand("generic")
    }
    check()
    const onConnect = (e: GamepadEvent) => {
      setConnected(true)
      setName(e.gamepad.id)
      setBrand(detectGamepadBrand(e.gamepad.id))
    }
    const onDisconnect = () => check()
    window.addEventListener("gamepadconnected", onConnect)
    window.addEventListener("gamepaddisconnected", onDisconnect)
    return () => {
      window.removeEventListener("gamepadconnected", onConnect)
      window.removeEventListener("gamepaddisconnected", onDisconnect)
    }
  }, [])

  return { connected, name, brand }
}

// =============================================================================
// Guided Key Setup Dialog
// =============================================================================

function GuidedKeySetupDialog({
  open,
  onOpenChange,
  buttons,
  onComplete,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  buttons: string[]
  onComplete: (mappings: Record<string, string>) => void
}) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [mappings, setMappings] = useState<Record<string, string>>({})
  const [lastCaptured, setLastCaptured] = useState<string | null>(null)
  const advanceTimer = useRef<ReturnType<typeof setTimeout>>(null)

  // Cleanup timers on unmount
  useEffect(() => {
    return () => { if (advanceTimer.current) clearTimeout(advanceTimer.current) }
  }, [])

  const currentButton = buttons[currentIndex]
  const isComplete = currentIndex >= buttons.length

  // Capture keypress for the current button
  useEffect(() => {
    if (!open || isComplete || lastCaptured) return
    const handler = (e: KeyboardEvent) => {
      e.preventDefault()
      e.stopPropagation()
      if (e.code === "Escape") { onOpenChange(false); return }
      const key = browserKeyToPyglet(e)
      if (!key) return
      setMappings(prev => ({ ...prev, [currentButton]: key }))
      setLastCaptured(key)
      advanceTimer.current = setTimeout(() => {
        setCurrentIndex(prev => prev + 1)
        setLastCaptured(null)
      }, 350)
    }
    window.addEventListener("keydown", handler, true)
    return () => window.removeEventListener("keydown", handler, true)
  }, [open, isComplete, currentButton, lastCaptured, onOpenChange])

  const progress = buttons.length > 0 ? (currentIndex / buttons.length) * 100 : 0

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Wand2 className="size-5" />
            Guided Key Setup
          </DialogTitle>
          <DialogDescription>
            Press the key for each button. Escape to cancel.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Progress bar */}
          <div className="space-y-1">
            <div className="w-full bg-muted h-1.5">
              <div
                className="bg-primary h-1.5 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground text-center">
              {currentIndex} / {buttons.length}
            </p>
          </div>

          {!isComplete ? (
            <div className="text-center space-y-4 py-4">
              <p className="text-sm text-muted-foreground">Press the key for</p>
              <p className="text-4xl font-bold tracking-tight">
                {BUTTON_LABELS[currentButton] ?? currentButton}
              </p>
              {lastCaptured ? (
                <Badge variant="outline" className="text-base px-4 py-1">
                  {displayKey(lastCaptured)}
                </Badge>
              ) : (
                <p className="text-sm text-muted-foreground animate-pulse">Listening...</p>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-center text-sm font-medium">All buttons mapped</p>
              <div className="grid grid-cols-2 gap-1.5 text-sm">
                {buttons.map(btn => (
                  <div key={btn} className="flex justify-between items-center px-3 py-1 bg-muted">
                    <span className="text-muted-foreground">{BUTTON_LABELS[btn]}</span>
                    <span className="font-mono text-xs">{displayKey(mappings[btn])}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          {!isComplete ? (
            <>
              <Button variant="ghost" size="sm" onClick={() => { setCurrentIndex(prev => prev + 1); setLastCaptured(null) }}>
                Skip
              </Button>
              <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" size="sm" onClick={() => { setCurrentIndex(0); setMappings({}); setLastCaptured(null) }}>
                Redo
              </Button>
              <Button size="sm" onClick={() => { onComplete(mappings); onOpenChange(false) }}>
                Apply
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// =============================================================================
// Guided Gamepad Setup Dialog
// =============================================================================

function GuidedGamepadSetupDialog({
  open,
  onOpenChange,
  buttons,
  brand,
  onComplete,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  buttons: string[]
  brand: GamepadBrand
  onComplete: (mappings: Record<string, number>) => void
}) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [mappings, setMappings] = useState<Record<string, number>>({})
  const [lastCaptured, setLastCaptured] = useState<number | null>(null)
  const advanceTimer = useRef<ReturnType<typeof setTimeout>>(null)
  const rafRef = useRef<number>(0)

  const bindableButtons = buttons.filter(
    btn => !["up", "down", "left", "right"].includes(btn) && BUTTON_TO_FIELD[btn]
  )

  useEffect(() => {
    return () => {
      if (advanceTimer.current) clearTimeout(advanceTimer.current)
      cancelAnimationFrame(rafRef.current)
    }
  }, [])

  const currentButton = bindableButtons[currentIndex]
  const isComplete = currentIndex >= bindableButtons.length

  // Cancel on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.code === "Escape") { e.preventDefault(); onOpenChange(false) }
    }
    window.addEventListener("keydown", handler, true)
    return () => window.removeEventListener("keydown", handler, true)
  }, [open, onOpenChange])

  // Poll gamepad for new button presses
  useEffect(() => {
    if (!open || isComplete || lastCaptured !== null) return

    const held = new Set<number>()
    for (const gp of navigator.getGamepads()) {
      if (!gp) continue
      gp.buttons.forEach((btn, i) => { if (btn.pressed) held.add(i) })
    }

    const poll = () => {
      for (const gp of navigator.getGamepads()) {
        if (!gp) continue
        for (let i = 0; i < gp.buttons.length; i++) {
          if (gp.buttons[i].pressed && !held.has(i)) {
            setMappings(prev => ({ ...prev, [currentButton]: i }))
            setLastCaptured(i)
            advanceTimer.current = setTimeout(() => {
              setCurrentIndex(prev => prev + 1)
              setLastCaptured(null)
            }, 350)
            return
          }
        }
      }
      rafRef.current = requestAnimationFrame(poll)
    }
    rafRef.current = requestAnimationFrame(poll)
    return () => cancelAnimationFrame(rafRef.current)
  }, [open, isComplete, currentButton, lastCaptured])

  const progress = bindableButtons.length > 0 ? (currentIndex / bindableButtons.length) * 100 : 0

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Wand2 className="size-5" />
            Guided Gamepad Setup
          </DialogTitle>
          <DialogDescription>
            Press the gamepad button for each action. Escape to cancel.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <div className="space-y-1">
            <div className="w-full bg-muted h-1.5">
              <div
                className="bg-primary h-1.5 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground text-center">
              {currentIndex} / {bindableButtons.length}
            </p>
          </div>

          {!isComplete ? (
            <div className="text-center space-y-4 py-4">
              <p className="text-sm text-muted-foreground">Press gamepad button for</p>
              <p className="text-4xl font-bold tracking-tight">
                {BUTTON_LABELS[currentButton] ?? currentButton}
              </p>
              {lastCaptured !== null ? (
                <Badge variant="outline" className="text-base px-4 py-1">
                  {getButtonName(brand, lastCaptured)}
                </Badge>
              ) : (
                <p className="text-sm text-muted-foreground animate-pulse">Listening...</p>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-center text-sm font-medium">All buttons mapped</p>
              <div className="grid grid-cols-2 gap-1.5 text-sm">
                {bindableButtons.map(btn => (
                  <div key={btn} className="flex justify-between items-center px-3 py-1 bg-muted">
                    <span className="text-muted-foreground">{BUTTON_LABELS[btn]}</span>
                    <span className="font-mono text-xs">
                      {mappings[btn] !== undefined ? getButtonName(brand, mappings[btn]) : "\u2014"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          {!isComplete ? (
            <>
              <Button variant="ghost" size="sm" onClick={() => { setCurrentIndex(prev => prev + 1); setLastCaptured(null) }}>
                Skip
              </Button>
              <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" size="sm" onClick={() => { setCurrentIndex(0); setMappings({}); setLastCaptured(null) }}>
                Redo
              </Button>
              <Button size="sm" onClick={() => { onComplete(mappings); onOpenChange(false) }}>
                Apply
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// =============================================================================
// Main Component
// =============================================================================

type NormalizedInputConfig = Required<InputConfig> & {
  controller: Required<ControllerConfig>
}

interface InputSettingsCardProps {
  inputConfig: InputConfig | undefined
  onChange: (config: InputConfig) => void
}

export function InputSettingsCard({ inputConfig, onChange }: InputSettingsCardProps) {
  const [selectedSystem, setSelectedSystem] = useState("snes")
  const [activeTab, setActiveTab] = useState("keyboard")
  const [guidedOpen, setGuidedOpen] = useState(false)
  const [guidedKey, setGuidedKey] = useState(0)

  const config: NormalizedInputConfig = useMemo(() => ({
    keyboard_mappings: inputConfig?.keyboard_mappings ?? {},
    controller: { ...DEFAULT_CONTROLLER, ...inputConfig?.controller },
  }), [inputConfig])

  const storageKey = SYSTEM_STORAGE_KEYS[selectedSystem] ?? selectedSystem
  const currentMapping = config.keyboard_mappings[storageKey] ?? getDefaultMapping(selectedSystem)

  function getDefaultMapping(system: string): KeyboardMapping {
    const defaults: Record<string, Partial<KeyboardMapping>> = {
      nes: { a: "X", b: "Z", start: "RETURN", select: "RSHIFT" },
      snes: { a: "X", b: "Z", x: "S", y: "A", l: "Q", r: "W", start: "RETURN", select: "RSHIFT" },
      genesis: { a: "A", b: "S", c: "D", x: "Z", y: "X", z_btn: "C", start: "RETURN" },
      gba: { a: "X", b: "Z", l: "Q", r: "W", start: "RETURN", select: "RSHIFT" },
      gb: { a: "X", b: "Z", start: "RETURN", select: "RSHIFT" },
      atari2600: { a: "X", start: "RETURN", select: "RSHIFT" },
      pce: { a: "X", b: "Z", start: "RETURN", select: "RSHIFT" },
    }
    return {
      up: "UP",
      down: "DOWN",
      left: "LEFT",
      right: "RIGHT",
      a: "X",
      b: "Z",
      start: "RETURN",
      select: "RSHIFT",
      ...defaults[system],
    } as KeyboardMapping
  }

  const updateKeyboardMapping = useCallback((button: string, key: string) => {
    const newMappings = { ...config.keyboard_mappings }
    newMappings[storageKey] = {
      ...currentMapping,
      [button]: key || null,
    }
    onChange({ ...config, keyboard_mappings: newMappings })
  }, [config, storageKey, currentMapping, onChange])

  function updateController(updates: Partial<ControllerConfig>) {
    onChange({
      ...config,
      controller: { ...config.controller, ...updates },
    })
  }

  function resetSystemMapping() {
    const newMappings = { ...config.keyboard_mappings }
    delete newMappings[storageKey]
    // Reset controller buttons for this system back to defaults
    const controllerResets: Record<string, number> = {}
    for (const btn of systemButtons) {
      const field = BUTTON_TO_FIELD[btn]
      if (field) {
        controllerResets[field] = DEFAULT_CONTROLLER[field] as number
      }
    }
    onChange({
      ...config,
      keyboard_mappings: newMappings,
      controller: { ...config.controller, ...controllerResets },
    })
  }

  function handleGuidedComplete(mappings: Record<string, string>) {
    const newMappings = { ...config.keyboard_mappings }
    newMappings[storageKey] = { ...currentMapping, ...mappings }
    onChange({ ...config, keyboard_mappings: newMappings })
  }

  function handleGuidedGamepadComplete(mappings: Record<string, number>) {
    const updates: Record<string, number> = {}
    for (const [btn, index] of Object.entries(mappings)) {
      const field = BUTTON_TO_FIELD[btn]
      if (field) {
        updates[field] = index
      }
    }
    onChange({
      ...config,
      controller: { ...config.controller, ...updates },
    })
  }

  const systemButtons = SYSTEM_BUTTONS[selectedSystem] ?? SYSTEM_BUTTONS.snes
  const ControllerComponent = CONTROLLER_COMPONENTS[selectedSystem] ?? SNESController
  const gamepad = useGamepadStatus()

  // Build a mapping for the controller tab that shows gamepad button names
  const controllerMapping = useMemo(() => {
    const m: Record<string, string | null> = {
      up: "↑", down: "↓", left: "←", right: "→",
    }
    for (const btn of Object.keys(BUTTON_TO_FIELD)) {
      const field = BUTTON_TO_FIELD[btn]
      if (field) {
        const index = config.controller[field] as number
        m[btn] = getButtonName(gamepad.brand, index)
      }
    }
    return m as unknown as KeyboardMapping
  }, [config.controller, gamepad.brand])

  const previewMapping = activeTab === "controller" ? controllerMapping : currentMapping

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Gamepad2 className="size-5" />
          Input Settings
        </CardTitle>
        <CardDescription>
          Configure keyboard and controller mappings for playing games
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Shared System Selector */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <Label>System</Label>
            <Select value={selectedSystem} onValueChange={setSelectedSystem}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.keys(SYSTEM_BUTTONS).map((sys) => (
                  <SelectItem key={sys} value={sys}>
                    {SYSTEM_DISPLAY_NAMES[sys] || sys}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Badge variant="outline">{SYSTEM_DISPLAY_NAMES[selectedSystem]}</Badge>
        </div>

        {/* Controller Visual Preview */}
        <div className="relative bg-background/50 border p-4 crt-inset">
          <ControllerComponent
            mapping={previewMapping}
            className="w-full h-auto max-h-44"
          />
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <div className="flex items-center justify-between mb-4">
            <TabsList>
              <TabsTrigger value="keyboard" className="gap-2">
                <Keyboard className="size-4" />
                Keyboard
              </TabsTrigger>
              <TabsTrigger value="controller" className="gap-2">
                <Gamepad2 className="size-4" />
                Controller
              </TabsTrigger>
            </TabsList>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => { setGuidedKey(k => k + 1); setGuidedOpen(true) }}>
                <Wand2 className="size-4 mr-1" />
                Guided
              </Button>
              <Button variant="ghost" size="sm" onClick={resetSystemMapping}>
                <RotateCcw className="size-4 mr-1" />
                Reset
              </Button>
            </div>
          </div>

          <TabsContent value="keyboard" className="space-y-4">
            {/* Button Mappings - click to capture */}
            <div className="grid grid-cols-2 gap-4">
              {/* D-Pad */}
              <div className="space-y-2">
                <p className="text-sm font-medium text-muted-foreground">D-Pad</p>
                <div className="grid grid-cols-2 gap-2">
                  {["up", "down", "left", "right"].map((btn) => (
                    <KeyCaptureInput
                      key={btn}
                      label={BUTTON_LABELS[btn]}
                      value={(currentMapping as Record<string, string | null | undefined>)[btn]}
                      onChange={(key) => updateKeyboardMapping(btn, key)}
                    />
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="space-y-2">
                <p className="text-sm font-medium text-muted-foreground">Buttons</p>
                <div className="grid grid-cols-2 gap-2">
                  {systemButtons
                    .filter((btn) => !["up", "down", "left", "right"].includes(btn))
                    .map((btn) => (
                      <KeyCaptureInput
                        key={btn}
                        label={BUTTON_LABELS[btn]}
                        value={(currentMapping as Record<string, string | null | undefined>)[btn]}
                        onChange={(key) => updateKeyboardMapping(btn, key)}
                      />
                    ))}
                </div>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">
              Click any button and press a key to bind it
            </p>
          </TabsContent>

          <TabsContent value="controller" className="space-y-4">
            {/* Enable Controller + Gamepad Status */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Enable Controller</Label>
                <div className="flex items-center gap-2 text-xs">
                  <span className={cn(
                    "size-2",
                    gamepad.connected ? "bg-green-500" : "bg-muted-foreground/30",
                  )} />
                  <span className="text-muted-foreground">
                    {gamepad.connected
                      ? gamepad.name
                      : "No gamepad detected"}
                  </span>
                </div>
              </div>
              <Switch
                checked={config.controller.enabled}
                onCheckedChange={(enabled) => updateController({ enabled })}
              />
            </div>

            {/* Deadzone */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Analog Deadzone</Label>
                <Badge variant="outline">{(config.controller.deadzone * 100).toFixed(0)}%</Badge>
              </div>
              <Slider
                value={[config.controller.deadzone]}
                onValueChange={([v]) => updateController({ deadzone: v })}
                min={0}
                max={0.5}
                step={0.01}
                disabled={!config.controller.enabled}
              />
            </div>

            {/* System-specific Button Mappings */}
            <div className="space-y-2">
              <Label>Button Mappings — {SYSTEM_DISPLAY_NAMES[selectedSystem]}</Label>
              <p className="text-xs text-muted-foreground mb-2">
                Click a button, then press the gamepad button to bind it
              </p>
              <div className="grid grid-cols-4 gap-2">
                {systemButtons
                  .filter((btn) => !["up", "down", "left", "right"].includes(btn))
                  .map((btn) => {
                    const field = BUTTON_TO_FIELD[btn]
                    if (!field) return null
                    return (
                      <GamepadCaptureInput
                        key={field}
                        label={BUTTON_LABELS[btn]}
                        value={config.controller[field] as number}
                        onChange={(val) => updateController({ [field]: val })}
                        disabled={!config.controller.enabled}
                        brand={gamepad.brand}
                      />
                    )
                  })}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>

      {/* Guided Setup Dialog — keyboard or gamepad based on active tab */}
      {activeTab === "keyboard" ? (
        <GuidedKeySetupDialog
          key={guidedKey}
          open={guidedOpen}
          onOpenChange={setGuidedOpen}
          buttons={systemButtons}
          onComplete={handleGuidedComplete}
        />
      ) : (
        <GuidedGamepadSetupDialog
          key={guidedKey}
          open={guidedOpen}
          onOpenChange={setGuidedOpen}
          buttons={systemButtons}
          brand={gamepad.brand}
          onComplete={handleGuidedGamepadComplete}
        />
      )}
    </Card>
  )
}
