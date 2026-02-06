/**
 * Retro console controller SVG components with button position overlays
 */

import type { KeyboardMapping } from "@/lib/schemas"

// Format key for display
function formatKey(key: string | null | undefined): string {
  if (!key) return ""
  const keyMap: Record<string, string> = {
    UP: "↑",
    DOWN: "↓",
    LEFT: "←",
    RIGHT: "→",
    RETURN: "↵",
    RSHIFT: "⇧",
    LSHIFT: "⇧",
    SPACE: "␣",
  }
  return keyMap[key] || key.toUpperCase()
}

// Button label component
function ButtonLabel({
  x,
  y,
  label,
  size = "normal",
}: {
  x: number
  y: number
  label: string
  size?: "small" | "normal" | "large"
}) {
  if (!label) return null
  const fontSize = size === "small" ? 9 : size === "large" ? 14 : 11
  return (
    <text
      x={x}
      y={y}
      textAnchor="middle"
      dominantBaseline="central"
      className="fill-primary font-mono font-bold"
      style={{ fontSize }}
    >
      {label}
    </text>
  )
}

interface ControllerProps {
  mapping: KeyboardMapping
  className?: string
}

// NES Controller - rectangular brick with face plate detail
export function NESController({ mapping, className = "" }: ControllerProps) {
  return (
    <svg viewBox="0 0 240 80" className={className} aria-label="NES Controller">
      {/* Controller body */}
      <rect x="4" y="4" width="232" height="72" rx="8" className="fill-muted stroke-border" strokeWidth="2" />
      {/* Dark top strip (characteristic NES two-tone) */}
      <rect x="6" y="6" width="228" height="22" rx="6" className="fill-muted-foreground/8" />
      {/* Inner face plate */}
      <rect x="14" y="14" width="212" height="52" rx="3" className="fill-muted-foreground/4" />

      {/* D-pad */}
      <rect x="32" y="22" width="14" height="36" rx="2" className="fill-muted-foreground/40" />
      <rect x="21" y="33" width="36" height="14" rx="2" className="fill-muted-foreground/40" />
      <ButtonLabel x={39} y={28} label={formatKey(mapping.up)} size="small" />
      <ButtonLabel x={39} y={52} label={formatKey(mapping.down)} size="small" />
      <ButtonLabel x={27} y={40} label={formatKey(mapping.left)} size="small" />
      <ButtonLabel x={51} y={40} label={formatKey(mapping.right)} size="small" />

      {/* Select/Start - angled pills */}
      <rect x="90" y="42" width="24" height="10" rx="5" className="fill-muted-foreground/30" transform="rotate(-12 102 47)" />
      <rect x="122" y="42" width="24" height="10" rx="5" className="fill-muted-foreground/30" transform="rotate(-12 134 47)" />
      <text x="100" y="56" textAnchor="middle" className="fill-muted-foreground text-[6px]">SELECT</text>
      <text x="134" y="56" textAnchor="middle" className="fill-muted-foreground text-[6px]">START</text>
      <ButtonLabel x={100} y={44} label={formatKey(mapping.select)} size="small" />
      <ButtonLabel x={134} y={44} label={formatKey(mapping.start)} size="small" />

      {/* B & A buttons */}
      <circle cx="175" cy="40" r="13" className="fill-destructive/40" />
      <circle cx="207" cy="40" r="13" className="fill-destructive/40" />
      <ButtonLabel x={175} y={40} label={formatKey(mapping.b)} />
      <ButtonLabel x={207} y={40} label={formatKey(mapping.a)} />
      <text x="175" y="58" textAnchor="middle" className="fill-muted-foreground text-[6px]">B</text>
      <text x="207" y="58" textAnchor="middle" className="fill-muted-foreground text-[6px]">A</text>
    </svg>
  )
}

// SNES Controller - unified dog-bone silhouette
export function SNESController({ mapping, className = "" }: ControllerProps) {
  return (
    <svg viewBox="0 0 240 90" className={className} aria-label="SNES Controller">
      {/* Controller body - single smooth path with integrated grips */}
      <path
        d="M 64,12 L 176,12 C 204,12 228,26 228,45 C 228,64 204,78 176,78 L 64,78 C 36,78 12,64 12,45 C 12,26 36,12 64,12 Z"
        className="fill-muted stroke-border"
        strokeWidth="2"
      />

      {/* L/R shoulders */}
      <rect x="50" y="4" width="30" height="8" rx="3" className="fill-muted-foreground/35" />
      <rect x="160" y="4" width="30" height="8" rx="3" className="fill-muted-foreground/35" />
      <ButtonLabel x={65} y={8} label={formatKey(mapping.l)} size="small" />
      <ButtonLabel x={175} y={8} label={formatKey(mapping.r)} size="small" />

      {/* D-pad */}
      <rect x="36" y="30" width="12" height="30" rx="2" className="fill-muted-foreground/40" />
      <rect x="27" y="39" width="30" height="12" rx="2" className="fill-muted-foreground/40" />
      <ButtonLabel x={42} y={35} label={formatKey(mapping.up)} size="small" />
      <ButtonLabel x={42} y={55} label={formatKey(mapping.down)} size="small" />
      <ButtonLabel x={32} y={45} label={formatKey(mapping.left)} size="small" />
      <ButtonLabel x={52} y={45} label={formatKey(mapping.right)} size="small" />

      {/* Select/Start */}
      <rect x="100" y="48" width="16" height="7" rx="3" className="fill-muted-foreground/30" />
      <rect x="124" y="48" width="16" height="7" rx="3" className="fill-muted-foreground/30" />
      <ButtonLabel x={108} y={51} label={formatKey(mapping.select)} size="small" />
      <ButtonLabel x={132} y={51} label={formatKey(mapping.start)} size="small" />

      {/* Face buttons - diamond */}
      <circle cx="186" cy="30" r="9" style={{ fill: "rgba(59,130,246,0.5)" }} />
      <circle cx="172" cy="45" r="9" style={{ fill: "rgba(34,197,94,0.5)" }} />
      <circle cx="200" cy="45" r="9" style={{ fill: "rgba(239,68,68,0.5)" }} />
      <circle cx="186" cy="60" r="9" style={{ fill: "rgba(234,179,8,0.5)" }} />
      <ButtonLabel x={186} y={30} label={formatKey(mapping.x)} size="small" />
      <ButtonLabel x={172} y={45} label={formatKey(mapping.y)} size="small" />
      <ButtonLabel x={200} y={45} label={formatKey(mapping.a)} size="small" />
      <ButtonLabel x={186} y={60} label={formatKey(mapping.b)} size="small" />
      <text x="186" y="18" textAnchor="middle" className="fill-muted-foreground text-[5px]">X</text>
      <text x="160" y="47" textAnchor="middle" className="fill-muted-foreground text-[5px]">Y</text>
      <text x="212" y="47" textAnchor="middle" className="fill-muted-foreground text-[5px]">A</text>
      <text x="186" y="73" textAnchor="middle" className="fill-muted-foreground text-[5px]">B</text>
    </svg>
  )
}

// Genesis 6-Button Controller
export function GenesisController({ mapping, className = "" }: ControllerProps) {
  return (
    <svg viewBox="0 0 260 85" className={className} aria-label="Genesis Controller">
      {/* Controller body - wide rounded */}
      <path
        d="M25 42 C25 18 45 12 70 12 L190 12 C215 12 235 18 235 42 C235 66 215 72 190 72 L70 72 C45 72 25 66 25 42"
        className="fill-muted stroke-border"
        strokeWidth="2"
      />
      {/* Left grip */}
      <ellipse cx="25" cy="42" rx="16" ry="24" className="fill-muted stroke-border" strokeWidth="2" />
      {/* Right grip */}
      <ellipse cx="235" cy="42" rx="16" ry="24" className="fill-muted stroke-border" strokeWidth="2" />

      {/* D-pad */}
      <rect x="44" y="27" width="11" height="30" rx="1" className="fill-muted-foreground/40" />
      <rect x="35" y="36" width="29" height="12" rx="1" className="fill-muted-foreground/40" />
      <ButtonLabel x={49} y={32} label={formatKey(mapping.up)} size="small" />
      <ButtonLabel x={49} y={52} label={formatKey(mapping.down)} size="small" />
      <ButtonLabel x={40} y={42} label={formatKey(mapping.left)} size="small" />
      <ButtonLabel x={58} y={42} label={formatKey(mapping.right)} size="small" />

      {/* Start */}
      <ellipse cx="130" cy="55" rx="14" ry="6" className="fill-muted-foreground/30" />
      <ButtonLabel x={130} y={55} label={formatKey(mapping.start)} size="small" />
      <text x="130" y="67" textAnchor="middle" className="fill-muted-foreground text-[5px]">START</text>

      {/* Top row X Y Z */}
      <circle cx="155" cy="28" r="8" className="fill-muted-foreground/25" />
      <circle cx="180" cy="28" r="8" className="fill-muted-foreground/25" />
      <circle cx="205" cy="28" r="8" className="fill-muted-foreground/25" />
      <ButtonLabel x={155} y={28} label={formatKey(mapping.x)} size="small" />
      <ButtonLabel x={180} y={28} label={formatKey(mapping.y)} size="small" />
      <ButtonLabel x={205} y={28} label={formatKey(mapping.z_btn)} size="small" />
      <text x="155" y="17" textAnchor="middle" className="fill-muted-foreground text-[5px]">X</text>
      <text x="180" y="17" textAnchor="middle" className="fill-muted-foreground text-[5px]">Y</text>
      <text x="205" y="17" textAnchor="middle" className="fill-muted-foreground text-[5px]">Z</text>

      {/* Bottom row A B C */}
      <circle cx="155" cy="50" r="10" className="fill-muted-foreground/35" />
      <circle cx="180" cy="50" r="10" className="fill-muted-foreground/35" />
      <circle cx="205" cy="50" r="10" className="fill-muted-foreground/35" />
      <ButtonLabel x={155} y={50} label={formatKey(mapping.a)} size="small" />
      <ButtonLabel x={180} y={50} label={formatKey(mapping.b)} size="small" />
      <ButtonLabel x={205} y={50} label={formatKey(mapping.c)} size="small" />
      <text x="155" y="65" textAnchor="middle" className="fill-muted-foreground text-[5px]">A</text>
      <text x="180" y="65" textAnchor="middle" className="fill-muted-foreground text-[5px]">B</text>
      <text x="205" y="65" textAnchor="middle" className="fill-muted-foreground text-[5px]">C</text>
    </svg>
  )
}

// Game Boy - portrait handheld with characteristic details
export function GameBoyController({ mapping, className = "" }: ControllerProps) {
  return (
    <svg viewBox="0 0 100 160" className={className} aria-label="Game Boy">
      {/* Body - rounded rectangle */}
      <rect x="6" y="4" width="88" height="152" rx="10" className="fill-muted stroke-border" strokeWidth="2" />

      {/* Screen bezel - recessed area */}
      <rect x="14" y="14" width="72" height="56" rx="4" className="fill-background/50 stroke-border/20" strokeWidth="1" />
      {/* Screen */}
      <rect x="22" y="22" width="56" height="40" rx="2" className="fill-muted-foreground/12" />
      {/* Power LED */}
      <circle cx="18" cy="78" r="2" className="fill-primary/30" />

      {/* D-pad */}
      <rect x="22" y="84" width="10" height="28" rx="2" className="fill-muted-foreground/40" />
      <rect x="13" y="93" width="28" height="10" rx="2" className="fill-muted-foreground/40" />
      <ButtonLabel x={27} y={89} label={formatKey(mapping.up)} size="small" />
      <ButtonLabel x={27} y={107} label={formatKey(mapping.down)} size="small" />
      <ButtonLabel x={18} y={98} label={formatKey(mapping.left)} size="small" />
      <ButtonLabel x={36} y={98} label={formatKey(mapping.right)} size="small" />

      {/* A & B - diagonal */}
      <circle cx="80" cy="90" r="10" className="fill-destructive/35" />
      <circle cx="62" cy="102" r="10" className="fill-destructive/35" />
      <ButtonLabel x={80} y={90} label={formatKey(mapping.a)} size="small" />
      <ButtonLabel x={62} y={102} label={formatKey(mapping.b)} size="small" />
      <text x="80" y="105" textAnchor="middle" className="fill-muted-foreground text-[5px]">A</text>
      <text x="62" y="117" textAnchor="middle" className="fill-muted-foreground text-[5px]">B</text>

      {/* Select/Start - angled */}
      <rect x="30" y="128" width="16" height="6" rx="3" className="fill-muted-foreground/30" transform="rotate(-25 38 131)" />
      <rect x="52" y="128" width="16" height="6" rx="3" className="fill-muted-foreground/30" transform="rotate(-25 60 131)" />
      <ButtonLabel x={37} y={133} label={formatKey(mapping.select)} size="small" />
      <ButtonLabel x={59} y={130} label={formatKey(mapping.start)} size="small" />

      {/* Speaker grille */}
      <line x1="68" y1="126" x2="84" y2="120" className="stroke-muted-foreground/15" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="68" y1="131" x2="84" y2="125" className="stroke-muted-foreground/15" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="68" y1="136" x2="84" y2="130" className="stroke-muted-foreground/15" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="68" y1="141" x2="84" y2="135" className="stroke-muted-foreground/15" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="68" y1="146" x2="84" y2="140" className="stroke-muted-foreground/15" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

// GBA - wide horizontal handheld with integrated wing grips
export function GBAController({ mapping, className = "" }: ControllerProps) {
  return (
    <svg viewBox="0 0 240 80" className={className} aria-label="Game Boy Advance">
      {/* Body - single smooth path with integrated grips */}
      <path
        d="M 56,10 L 184,10 C 210,10 230,22 230,40 C 230,58 210,70 184,70 L 56,70 C 30,70 10,58 10,40 C 10,22 30,10 56,10 Z"
        className="fill-muted stroke-border"
        strokeWidth="2"
      />

      {/* L/R shoulders */}
      <rect x="44" y="2" width="28" height="8" rx="3" className="fill-muted-foreground/35" />
      <rect x="168" y="2" width="28" height="8" rx="3" className="fill-muted-foreground/35" />
      <ButtonLabel x={58} y={6} label={formatKey(mapping.l)} size="small" />
      <ButtonLabel x={182} y={6} label={formatKey(mapping.r)} size="small" />

      {/* Screen */}
      <rect x="82" y="16" width="76" height="48" rx="3" className="fill-background/70" />
      <rect x="88" y="21" width="64" height="38" rx="2" className="fill-muted-foreground/15" />

      {/* D-pad */}
      <rect x="32" y="27" width="10" height="26" rx="2" className="fill-muted-foreground/40" />
      <rect x="24" y="35" width="26" height="10" rx="2" className="fill-muted-foreground/40" />
      <ButtonLabel x={37} y={32} label={formatKey(mapping.up)} size="small" />
      <ButtonLabel x={37} y={48} label={formatKey(mapping.down)} size="small" />
      <ButtonLabel x={29} y={40} label={formatKey(mapping.left)} size="small" />
      <ButtonLabel x={45} y={40} label={formatKey(mapping.right)} size="small" />

      {/* A & B - diagonal */}
      <circle cx="204" cy="30" r="9" className="fill-destructive/35" />
      <circle cx="188" cy="44" r="9" className="fill-destructive/35" />
      <ButtonLabel x={204} y={30} label={formatKey(mapping.a)} size="small" />
      <ButtonLabel x={188} y={44} label={formatKey(mapping.b)} size="small" />
      <text x="204" y="44" textAnchor="middle" className="fill-muted-foreground text-[5px]">A</text>
      <text x="188" y="58" textAnchor="middle" className="fill-muted-foreground text-[5px]">B</text>

      {/* Select/Start */}
      <rect x="106" y="66" width="12" height="4" rx="2" className="fill-muted-foreground/30" />
      <rect x="122" y="66" width="12" height="4" rx="2" className="fill-muted-foreground/30" />
      <ButtonLabel x={112} y={68} label={formatKey(mapping.select)} size="small" />
      <ButtonLabel x={128} y={68} label={formatKey(mapping.start)} size="small" />
    </svg>
  )
}

// Atari 2600 Joystick
export function AtariController({ mapping, className = "" }: ControllerProps) {
  return (
    <svg viewBox="0 0 100 130" className={className} aria-label="Atari 2600 Joystick">
      {/* Base */}
      <rect x="10" y="75" width="80" height="45" rx="4" className="fill-muted stroke-border" strokeWidth="2" />

      {/* Joystick shaft */}
      <rect x="42" y="30" width="16" height="50" rx="2" className="fill-muted-foreground/50" />

      {/* Joystick ball */}
      <circle cx="50" cy="24" r="18" className="fill-destructive/30 stroke-border" strokeWidth="2" />

      {/* Direction labels */}
      <ButtonLabel x={50} y={5} label={formatKey(mapping.up)} />
      <ButtonLabel x={50} y={43} label={formatKey(mapping.down)} />
      <ButtonLabel x={28} y={24} label={formatKey(mapping.left)} />
      <ButtonLabel x={72} y={24} label={formatKey(mapping.right)} />

      {/* Fire button */}
      <circle cx="50" cy="97" r="12" className="fill-destructive/40" />
      <ButtonLabel x={50} y={97} label={formatKey(mapping.a)} size="large" />
      <text x="50" y="115" textAnchor="middle" className="fill-muted-foreground text-[6px]">FIRE</text>
    </svg>
  )
}

// PC Engine / TurboGrafx-16
export function PCEngineController({ mapping, className = "" }: ControllerProps) {
  return (
    <svg viewBox="0 0 200 70" className={className} aria-label="PC Engine Controller">
      {/* Controller body - oval pill */}
      <rect x="8" y="10" width="184" height="50" rx="25" className="fill-muted stroke-border" strokeWidth="2" />

      {/* D-pad */}
      <rect x="36" y="20" width="10" height="30" rx="1" className="fill-muted-foreground/40" />
      <rect x="27" y="29" width="28" height="12" rx="1" className="fill-muted-foreground/40" />
      <ButtonLabel x={41} y={25} label={formatKey(mapping.up)} size="small" />
      <ButtonLabel x={41} y={45} label={formatKey(mapping.down)} size="small" />
      <ButtonLabel x={32} y={35} label={formatKey(mapping.left)} size="small" />
      <ButtonLabel x={50} y={35} label={formatKey(mapping.right)} size="small" />

      {/* Select/Run */}
      <rect x="80" y="30" width="16" height="10" rx="5" className="fill-muted-foreground/30" />
      <rect x="104" y="30" width="16" height="10" rx="5" className="fill-muted-foreground/30" />
      <ButtonLabel x={88} y={35} label={formatKey(mapping.select)} size="small" />
      <ButtonLabel x={112} y={35} label={formatKey(mapping.start)} size="small" />
      <text x="88" y="48" textAnchor="middle" className="fill-muted-foreground text-[5px]">SEL</text>
      <text x="112" y="48" textAnchor="middle" className="fill-muted-foreground text-[5px]">RUN</text>

      {/* II & I buttons */}
      <circle cx="145" cy="35" r="12" className="fill-muted-foreground/40" />
      <circle cx="175" cy="35" r="12" className="fill-muted-foreground/40" />
      <ButtonLabel x={145} y={35} label={formatKey(mapping.b)} />
      <ButtonLabel x={175} y={35} label={formatKey(mapping.a)} />
      <text x="145" y="53" textAnchor="middle" className="fill-muted-foreground text-[5px]">II</text>
      <text x="175" y="53" textAnchor="middle" className="fill-muted-foreground text-[5px]">I</text>
    </svg>
  )
}

// eslint-disable-next-line react-refresh/only-export-components -- constant map of controller components
export const CONTROLLER_COMPONENTS: Record<
  string,
  React.ComponentType<ControllerProps>
> = {
  nes: NESController,
  snes: SNESController,
  genesis: GenesisController,
  gb: GameBoyController,
  gbc: GameBoyController,
  gba: GBAController,
  atari2600: AtariController,
  pce: PCEngineController,
  tg16: PCEngineController,
}
