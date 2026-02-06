import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Gamepad2, Play } from "lucide-react"
import { useConfig } from "@/hooks"
import type { KeyboardMapping } from "@/lib/schemas"
import { CONTROLLER_COMPONENTS, SNESController } from "./controller-svgs"

// Default mappings if config not loaded
function getDefaultMapping(system: string): KeyboardMapping {
  const defaults: Record<string, Partial<KeyboardMapping>> = {
    nes: { a: "x", b: "z", start: "RETURN", select: "RSHIFT" },
    snes: { a: "x", b: "z", x: "s", y: "a", l: "q", r: "w", start: "RETURN", select: "RSHIFT" },
    genesis: { a: "a", b: "s", c: "d", x: "z", y: "x", z_btn: "c", start: "RETURN" },
    gba: { a: "x", b: "z", l: "q", r: "w", start: "RETURN", select: "RSHIFT" },
    gb: { a: "x", b: "z", start: "RETURN", select: "RSHIFT" },
    gbc: { a: "x", b: "z", start: "RETURN", select: "RSHIFT" },
    atari2600: { a: "x", start: "RETURN", select: "RSHIFT" },
    pce: { a: "x", b: "z", start: "RETURN", select: "RSHIFT" },
    tg16: { a: "x", b: "z", start: "RETURN", select: "RSHIFT" },
  }
  return {
    up: "UP",
    down: "DOWN",
    left: "LEFT",
    right: "RIGHT",
    a: "x",
    b: "z",
    x: null,
    y: null,
    l: null,
    r: null,
    start: "RETURN",
    select: null,
    c: null,
    z_btn: null,
    ...defaults[system.toLowerCase()],
  }
}

// Map display keys (lowercase) to storage keys (capitalized, matching backend/DB)
const SYSTEM_STORAGE_KEYS: Record<string, string> = {
  nes: "Nes",
  snes: "Snes",
  genesis: "Genesis",
  gba: "Gba",
  gb: "Gb",
  gbc: "Gb",
  atari2600: "Atari2600",
  pce: "PCEngine",
  tg16: "PCEngine",
}

// System display names
const SYSTEM_NAMES: Record<string, string> = {
  nes: "Nintendo Entertainment System",
  snes: "Super Nintendo",
  genesis: "Sega Genesis",
  gb: "Game Boy",
  gbc: "Game Boy Color",
  gba: "Game Boy Advance",
  atari2600: "Atari 2600",
  pce: "PC Engine",
  tg16: "TurboGrafx-16",
}

interface PlayKeybindsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  system: string
  gameName: string
  onLaunch: () => void
  isLaunching?: boolean
}

export function PlayKeybindsDialog({
  open,
  onOpenChange,
  system,
  gameName,
  onLaunch,
  isLaunching = false,
}: PlayKeybindsDialogProps) {
  const { data: config } = useConfig()

  // Get keyboard mapping for this system
  const systemKey = system.toLowerCase()
  const storageKey = SYSTEM_STORAGE_KEYS[systemKey] ?? system
  const mapping = config?.input?.keyboard_mappings?.[storageKey] ?? getDefaultMapping(systemKey)

  // Get the controller component for this system
  const ControllerComponent = CONTROLLER_COMPONENTS[systemKey] ?? SNESController

  const handleLaunch = () => {
    onLaunch()
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Gamepad2 className="size-5" />
            Controls
          </DialogTitle>
          <DialogDescription>
            Keyboard controls for <span className="font-medium text-foreground">{gameName}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* System Badge */}
          <div className="flex items-center gap-2">
            <Badge variant="outline">{system.toUpperCase()}</Badge>
            <span className="text-sm text-muted-foreground">
              {SYSTEM_NAMES[systemKey] || system}
            </span>
          </div>

          {/* Visual Controller */}
          <div className="relative bg-background/50 border p-4 crt-inset">
            <ControllerComponent
              mapping={mapping}
              className="w-full h-auto max-h-50"
            />
          </div>

          {/* Legend */}
          <div className="text-xs text-muted-foreground space-y-1">
            <p className="flex items-center gap-2">
              <span className="inline-block w-4 h-4 bg-muted-foreground/30" />
              Button positions show your keyboard keys
            </p>
            <p>Arrow keys: ↑ ↓ ← → &nbsp;|&nbsp; Enter: ↵ &nbsp;|&nbsp; Shift: ⇧</p>
          </div>

          {/* Controller Info */}
          {config?.input?.controller?.enabled && (
            <div className="text-xs text-muted-foreground border-t pt-3">
              <span className="flex items-center gap-1">
                <Gamepad2 className="size-3" />
                Controller enabled - XInput compatible gamepads supported
              </span>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleLaunch} disabled={isLaunching}>
            <Play className="size-4 mr-2" />
            {isLaunching ? "Launching..." : "Launch Game"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
