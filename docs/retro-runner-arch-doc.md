# RETRO RUNNER — Architecture & Design Document

**Project:** Local React frontend for managing stable-retro integrated emulator runs with ROM selection  
**Stack:** Vite + React + TypeScript, shadcn/ui (custom retro theme), TailwindCSS, local Python/FastAPI backend  
**Scope:** Local-only, single-user, developer tool  

---

## 1. UI Framework: shadcn/ui

### Theme Strategy

We use shadcn's built-in variant system (`variant="default"`, `variant="destructive"`, `variant="secondary"`, `variant="outline"`, `variant="ghost"`) for all component styling — no one-off color classes like `text-green-500` or `bg-red-900` anywhere in the codebase. But the underlying CSS variables that power those variants are fully overridden in `globals.css` to enforce a retro CRT / terminal dashboard aesthetic across the entire app.

This means: every `Button variant="default"` automatically gets our phosphor green. Every `Badge variant="destructive"` gets our CRT red. The design system stays clean and variant-driven — the palette underneath is just ours instead of Zinc.

### Design Direction

The visual language is **CRT terminal meets mission control**. Think green phosphor monitors, dark scan-line backgrounds, amber warning readouts. Not pixel-art retro — more like the aesthetic of monitoring equipment in an 80s NASA control room or an old oscilloscope display. Deep near-black backgrounds, high-contrast data, terminal greens and ambers as the primary accent palette.

Light mode exists as a "daytime" variant — not a white corporate theme but a washed-out CRT look. Think a terminal in a bright room: warm off-white background with the same green/amber accents muted down. Still reads as retro, just with the lights on.

### Variant Usage Convention

Every component uses shadcn variants. The retro palette underneath makes them feel right:

| Meaning | shadcn Variant | Visual Result (Dark) | Visual Result (Light) |
|---------|---------------|---------------------|----------------------|
| Primary action | `variant="default"` | Phosphor green button | Muted green on warm white |
| Secondary action | `variant="secondary"` | Dim terminal grey | Warm stone grey |
| Danger / stop / error | `variant="destructive"` | CRT red / scan-line red | Muted brick red |
| Low emphasis | `variant="ghost"` | Transparent, green text on hover | Transparent, dark text on hover |
| Neutral / outlined | `variant="outline"` | Thin border, terminal grey | Thin border, warm grey |
| Status: running | Badge `variant="default"` | Green badge, pulsing | Green badge |
| Status: completed | Badge `variant="secondary"` | Dim grey badge | Stone badge |
| Status: failed | Badge `variant="destructive"` | Red badge | Brick red badge |
| Status: paused | Badge `variant="outline"` | Outlined, amber-ish border | Outlined, warm border |

### globals.css — Full Variable Override + Structural Styles

This is the single source of truth for the retro aesthetic. We override every shadcn CSS variable in both `:root` (light) and `.dark` to push the entire component library into our palette. Non-color structural styles (font, scrollbars, animations, density helpers) sit alongside.

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap');

@layer base {

  /* ═══════════════════════════════════════════════════════
     LIGHT MODE — "CRT in a bright room"
     Warm off-white backgrounds, muted green/amber accents,
     washed-out phosphor feel. Not corporate white — papery,
     aged, like a terminal printout left in the sun.
     ═══════════════════════════════════════════════════════ */
  :root {
    /* Backgrounds: warm off-white, slight yellow cast */
    --background: 40 20% 96%;           /* warm parchment white */
    --foreground: 160 10% 15%;          /* near-black with green undertone */

    /* Cards / elevated surfaces: slightly cooler than bg */
    --card: 40 15% 93%;
    --card-foreground: 160 10% 15%;

    /* Popovers / dropdowns */
    --popover: 40 15% 93%;
    --popover-foreground: 160 10% 15%;

    /* Primary: muted phosphor green */
    --primary: 152 60% 28%;
    --primary-foreground: 40 20% 96%;

    /* Secondary: warm stone grey */
    --secondary: 35 10% 85%;
    --secondary-foreground: 160 10% 25%;

    /* Muted: desaturated warm */
    --muted: 35 10% 88%;
    --muted-foreground: 160 5% 45%;

    /* Accent: light amber wash */
    --accent: 38 40% 88%;
    --accent-foreground: 30 50% 25%;

    /* Destructive: aged brick red */
    --destructive: 0 55% 42%;
    --destructive-foreground: 40 20% 96%;

    /* Borders & inputs: warm grey lines */
    --border: 35 12% 82%;
    --input: 35 12% 82%;
    --ring: 152 60% 28%;

    /* Chart palette */
    --chart-1: 152 60% 28%;            /* green — rewards */
    --chart-2: 0 55% 42%;              /* red — loss */
    --chart-3: 35 70% 50%;             /* amber — epsilon */
    --chart-4: 200 30% 45%;            /* steel blue — FPS */
    --chart-5: 280 25% 45%;            /* muted purple — secondary metric */

    /* Sidebar (if used) */
    --sidebar: 40 15% 93%;
    --sidebar-foreground: 160 10% 15%;
    --sidebar-primary: 152 60% 28%;
    --sidebar-primary-foreground: 40 20% 96%;
    --sidebar-accent: 38 40% 88%;
    --sidebar-accent-foreground: 30 50% 25%;
    --sidebar-border: 35 12% 82%;
    --sidebar-ring: 152 60% 28%;

    --radius: 0.4rem;
  }

  /* ═══════════════════════════════════════════════════════
     DARK MODE — "The real thing"
     Deep blue-black CRT void, phosphor green primary,
     amber warnings, scan-line red for errors. High contrast
     data on near-black. This is the default working mode.
     ═══════════════════════════════════════════════════════ */
  .dark {
    /* Backgrounds: deep CRT black with slight blue cast */
    --background: 220 25% 5%;           /* near-black, cold blue undertone */
    --foreground: 155 15% 85%;          /* soft green-grey text */

    /* Cards: slightly lifted from void */
    --card: 220 20% 7%;
    --card-foreground: 155 15% 85%;

    /* Popovers */
    --popover: 220 20% 7%;
    --popover-foreground: 155 15% 85%;

    /* Primary: phosphor green — the hero colour */
    --primary: 152 80% 48%;
    --primary-foreground: 220 25% 5%;

    /* Secondary: terminal grey */
    --secondary: 215 15% 14%;
    --secondary-foreground: 155 10% 65%;

    /* Muted: dim CRT grey */
    --muted: 215 15% 14%;
    --muted-foreground: 155 5% 50%;

    /* Accent: amber / phosphor orange */
    --accent: 38 70% 18%;
    --accent-foreground: 38 80% 70%;

    /* Destructive: CRT scan-line red */
    --destructive: 0 70% 50%;
    --destructive-foreground: 0 0% 98%;

    /* Borders: barely visible grid lines */
    --border: 215 15% 12%;
    --input: 215 15% 14%;
    --ring: 152 80% 48%;

    /* Chart palette — vivid on dark */
    --chart-1: 152 80% 48%;            /* phosphor green — rewards */
    --chart-2: 0 70% 50%;              /* CRT red — loss */
    --chart-3: 38 85% 55%;             /* amber — epsilon */
    --chart-4: 200 50% 55%;            /* cool blue — FPS */
    --chart-5: 280 40% 60%;            /* soft purple — secondary */

    /* Sidebar */
    --sidebar: 220 25% 4%;
    --sidebar-foreground: 155 15% 85%;
    --sidebar-primary: 152 80% 48%;
    --sidebar-primary-foreground: 220 25% 5%;
    --sidebar-accent: 38 70% 18%;
    --sidebar-accent-foreground: 38 80% 70%;
    --sidebar-border: 215 15% 12%;
    --sidebar-ring: 152 80% 48%;
  }

  /* ── Typography ── */
  body {
    font-family: 'JetBrains Mono', monospace;
    font-feature-settings: 'liga' 1, 'calt' 1;
    -webkit-font-smoothing: antialiased;
  }

  * {
    line-height: 1.5;
  }

  /* ── Scrollbars ── */
  ::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }
  ::-webkit-scrollbar-track {
    background: transparent;
  }
  ::-webkit-scrollbar-thumb {
    border-radius: 3px;
    background: hsl(var(--muted));
  }
  ::-webkit-scrollbar-thumb:hover {
    background: hsl(var(--muted-foreground));
  }
}

/* ═══════════════════════════════════════════════════════════
   CRT OVERLAY SYSTEM
   Three fixed layers that sit over the entire app:
   1. Scanlines — horizontal line pattern
   2. Vignette  — darkened edges like a curved CRT tube
   3. Glow bar  — a single bright band that drifts down
                   the screen like a slow refresh artifact

   All layers are pointer-events: none and use z-index
   stacking on a shared .crt-overlay container. Toggle
   the entire system by adding/removing .crt-enabled
   on <body>. Each layer can also be toggled individually.
   ═══════════════════════════════════════════════════════════ */

@layer components {

  /* ── Container — fixed fullscreen, above content ── */
  .crt-overlay {
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 9999;
    overflow: hidden;
    /* Hidden by default unless body has .crt-enabled */
    display: none;
  }
  body.crt-enabled .crt-overlay {
    display: block;
  }

  /* ── Layer 1: Scanlines ──
     Repeating 2px transparent / 2px tinted bars.
     A very subtle flicker animation shifts opacity
     at irregular intervals to mimic phosphor instability. */
  .crt-scanlines {
    position: absolute;
    inset: 0;
    background: repeating-linear-gradient(
      to bottom,
      transparent 0px,
      transparent 2px,
      hsl(var(--foreground) / 0.03) 2px,
      hsl(var(--foreground) / 0.03) 4px
    );
    animation: crt-flicker 8s steps(1) infinite;
  }

  @keyframes crt-flicker {
    0%   { opacity: 0.9; }
    3%   { opacity: 1; }
    6%   { opacity: 0.85; }
    9%   { opacity: 1; }
    42%  { opacity: 1; }
    44%  { opacity: 0.92; }
    46%  { opacity: 1; }
    78%  { opacity: 1; }
    80%  { opacity: 0.88; }
    82%  { opacity: 1; }
    100% { opacity: 1; }
  }

  /* ── Layer 2: Vignette ──
     Radial gradient that darkens edges and corners,
     simulating the light falloff on a curved CRT tube.
     Stronger in dark mode, barely visible in light. */
  .crt-vignette {
    position: absolute;
    inset: 0;
    background: radial-gradient(
      ellipse 80% 70% at 50% 50%,
      transparent 50%,
      hsl(var(--background) / 0.4) 80%,
      hsl(var(--background) / 0.8) 100%
    );
  }

  /* ── Layer 3: Glow bar ──
     A single horizontal bright band that crawls
     slowly down the screen and wraps. Mimics the
     refresh sweep visible on old CRTs when filmed.
     Very faint — a texture, not a distraction. */
  .crt-glow-bar {
    position: absolute;
    inset: 0;
    background: linear-gradient(
      to bottom,
      transparent 0%,
      hsl(var(--primary) / 0.012) 48%,
      hsl(var(--primary) / 0.04) 50%,
      hsl(var(--primary) / 0.012) 52%,
      transparent 100%
    );
    background-size: 100% 250%;
    animation: crt-glow-sweep 6s linear infinite;
  }

  @keyframes crt-glow-sweep {
    0%   { background-position: 0% 0%; }
    100% { background-position: 0% 250%; }
  }
}


/* ═══════════════════════════════════════════════════════════
   PAGE TRANSITION ANIMATIONS
   Applied to the page wrapper in Shell.tsx when routes
   change. React Router + a transition wrapper component
   applies these classes on mount/unmount.

   The metaphor: switching pages is like changing the
   signal on a CRT monitor. The old signal drops out
   (brief horizontal squeeze + fade), the new one
   materialises (expand from center line + sharpen).
   ═══════════════════════════════════════════════════════════ */

@layer utilities {

  /* ── Page enter: signal lock ──
     Content starts as a bright horizontal line (scaleY 0,
     full brightness) and expands to fill the screen,
     opacity settling to normal. Like a CRT warming up
     or a new input signal locking in. */
  @keyframes page-enter {
    0% {
      transform: scaleY(0.005) scaleX(0.98);
      opacity: 0;
      filter: brightness(2.5);
    }
    30% {
      transform: scaleY(0.5) scaleX(1);
      opacity: 0.7;
      filter: brightness(1.4);
    }
    60% {
      transform: scaleY(0.95) scaleX(1);
      opacity: 0.95;
      filter: brightness(1.1);
    }
    100% {
      transform: scaleY(1) scaleX(1);
      opacity: 1;
      filter: brightness(1);
    }
  }
  .animate-page-enter {
    animation: page-enter 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    transform-origin: center center;
  }

  /* ── Page exit: signal drop ──
     Reverse of enter — collapses to a horizontal line,
     brightness spikes briefly (phosphor afterglow),
     then disappears. Used when navigating away. */
  @keyframes page-exit {
    0% {
      transform: scaleY(1) scaleX(1);
      opacity: 1;
      filter: brightness(1);
    }
    50% {
      transform: scaleY(0.3) scaleX(1);
      opacity: 0.6;
      filter: brightness(1.6);
    }
    100% {
      transform: scaleY(0.005) scaleX(0.95);
      opacity: 0;
      filter: brightness(3);
    }
  }
  .animate-page-exit {
    animation: page-exit 0.2s cubic-bezier(0.55, 0, 1, 0.45) forwards;
    transform-origin: center center;
  }

  /* ── Fast variant for tab switches within a page ──
     Same shape, faster timing — tabs don't need the
     full dramatic effect. */
  .animate-page-enter-fast {
    animation: page-enter 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    transform-origin: center center;
  }
}


/* ═══════════════════════════════════════════════════════════
   COMPONENT-LEVEL TRANSITIONS
   Smaller CRT-flavoured animations for individual
   elements mounting, modals opening, sheets sliding, etc.
   ═══════════════════════════════════════════════════════════ */

@layer utilities {

  /* ── Status pulse (running indicators) ── */
  @keyframes pulse-live {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.35; }
  }
  .animate-live {
    animation: pulse-live 2s ease-in-out infinite;
  }

  /* ── Card / element mount: phosphor warmup ──
     Fades up with a brief brightness flash, like
     a phosphor dot being energised for the first time. */
  @keyframes phosphor-in {
    0% {
      opacity: 0;
      transform: translateY(6px);
      filter: brightness(2);
    }
    40% {
      opacity: 0.8;
      filter: brightness(1.3);
    }
    100% {
      opacity: 1;
      transform: translateY(0);
      filter: brightness(1);
    }
  }
  .animate-phosphor-in {
    animation: phosphor-in 0.3s ease-out forwards;
  }

  /* ── Staggered children ──
     Apply to a container. Each direct child gets a
     progressive delay so cards/rows appear to
     "scan" onto the screen top-to-bottom. */
  .stagger-children > * {
    opacity: 0;
    animation: phosphor-in 0.3s ease-out forwards;
  }
  .stagger-children > *:nth-child(1)  { animation-delay: 0ms; }
  .stagger-children > *:nth-child(2)  { animation-delay: 40ms; }
  .stagger-children > *:nth-child(3)  { animation-delay: 80ms; }
  .stagger-children > *:nth-child(4)  { animation-delay: 120ms; }
  .stagger-children > *:nth-child(5)  { animation-delay: 160ms; }
  .stagger-children > *:nth-child(6)  { animation-delay: 200ms; }
  .stagger-children > *:nth-child(7)  { animation-delay: 240ms; }
  .stagger-children > *:nth-child(8)  { animation-delay: 280ms; }
  .stagger-children > *:nth-child(9)  { animation-delay: 320ms; }
  .stagger-children > *:nth-child(10) { animation-delay: 360ms; }
  .stagger-children > *:nth-child(n+11) { animation-delay: 400ms; }

  /* ── Sheet / panel slide-in ── */
  @keyframes slide-in-right {
    from {
      transform: translateX(100%);
      filter: brightness(1.5);
    }
    to {
      transform: translateX(0);
      filter: brightness(1);
    }
  }
  .animate-slide-in-right {
    animation: slide-in-right 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }

  /* ── Dialog / modal: CRT power-on ──
     Starts as a bright horizontal slit and expands.
     Smaller and faster than the page transition. */
  @keyframes dialog-enter {
    0% {
      transform: scaleY(0.01) scaleX(0.7);
      opacity: 0;
      filter: brightness(3);
    }
    50% {
      transform: scaleY(0.8) scaleX(1);
      opacity: 0.9;
      filter: brightness(1.2);
    }
    100% {
      transform: scaleY(1) scaleX(1);
      opacity: 1;
      filter: brightness(1);
    }
  }
  .animate-dialog-enter {
    animation: dialog-enter 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    transform-origin: center center;
  }

  /* ── Dialog exit: CRT power-off ── */
  @keyframes dialog-exit {
    0% {
      transform: scaleY(1) scaleX(1);
      opacity: 1;
      filter: brightness(1);
    }
    60% {
      transform: scaleY(0.2) scaleX(1);
      opacity: 0.5;
      filter: brightness(2);
    }
    100% {
      transform: scaleY(0) scaleX(0.3);
      opacity: 0;
      filter: brightness(4);
    }
  }
  .animate-dialog-exit {
    animation: dialog-exit 0.15s cubic-bezier(0.55, 0, 1, 0.45) forwards;
    transform-origin: center center;
  }

  /* ── Notification toast: signal blip ──
     Quick flash-in from the right edge. */
  @keyframes toast-in {
    0% {
      transform: translateX(30px);
      opacity: 0;
      filter: brightness(2);
    }
    100% {
      transform: translateX(0);
      opacity: 1;
      filter: brightness(1);
    }
  }
  .animate-toast-in {
    animation: toast-in 0.2s ease-out;
  }

  /* ── Chart draw-in: left-to-right reveal ──
     Used on MetricChart mount. A clip-path wipe
     that reveals the chart like a signal being
     traced across the screen. */
  @keyframes chart-trace {
    0% {
      clip-path: inset(0 100% 0 0);
    }
    100% {
      clip-path: inset(0 0 0 0);
    }
  }
  .animate-chart-trace {
    animation: chart-trace 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }

  /* ── Interference glitch — one-shot ──
     A quick horizontal shudder + color offset.
     Trigger programmatically on error events or
     failed run notifications. Not looping. */
  @keyframes interference {
    0%   { transform: translate(0, 0); filter: none; }
    10%  { transform: translate(-3px, 0); filter: hue-rotate(40deg); }
    20%  { transform: translate(2px, 1px); filter: hue-rotate(-30deg); }
    30%  { transform: translate(-1px, -1px); filter: hue-rotate(20deg) saturate(1.5); }
    40%  { transform: translate(3px, 0); filter: hue-rotate(-15deg); }
    50%  { transform: translate(0, 0); filter: none; }
    100% { transform: translate(0, 0); filter: none; }
  }
  .animate-glitch {
    animation: interference 0.4s ease-out;
  }
}


/* ═══════════════════════════════════════════════════════════
   UTILITY CLASSES
   ═══════════════════════════════════════════════════════════ */

/* ── Data density helpers ── */
@layer utilities {
  .text-mono-xs {
    font-size: 0.7rem;
    letter-spacing: 0.05em;
  }
  .text-mono-sm {
    font-size: 0.8rem;
  }
  .tracking-stat {
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }
}

/* ── Table density ── */
@layer components {
  .table-dense th,
  .table-dense td {
    padding: 0.4rem 0.75rem;
    font-size: 0.8rem;
  }
}
```

### How the Palette Works Across Components

Because every shadcn component reads from these CSS variables, the retro feel is automatic:

- **`Button variant="default"`** renders with `--primary` bg → phosphor green in dark, muted green in light
- **`Badge variant="destructive"`** uses `--destructive` → CRT red in dark, brick red in light
- **`Card`** uses `--card` bg → slightly lifted from the CRT void in dark, warm parchment in light
- **`Table` borders** use `--border` → barely visible grid lines in dark, warm grey in light
- **`Input` focus ring** uses `--ring` → green glow in both modes
- **`text-muted-foreground`** (Tailwind class) → dim phosphor grey in dark, warm stone in light
- **Chart gridlines** drawn with `hsl(var(--muted))` → natural CRT grid
- **Chart lines** use `--chart-1` through `--chart-5` → the dedicated palette

No component ever needs a custom color class. The variables do all the work.

### shadcn Components Used

| Component | Primary Usage |
|-----------|--------------|
| `Button` | All actions — start, stop, delete, nav, filters |
| `Badge` | Status indicators, platform labels, algorithm tags |
| `Card` | Stat cards, ROM cards, config sections, chart containers |
| `Table` | Run Manager, checkpoints, emulator cores |
| `Dialog` | New Run modal, confirmations |
| `Sheet` | ROM Detail slide-over |
| `Input` | Search, hyperparams, paths |
| `Select` | Algorithm, sort, platform filter |
| `Tabs` | Main navigation |
| `Tooltip` | Truncated text, error previews |
| `Separator` | Section dividers |
| `ScrollArea` | Overflow containers |
| `DropdownMenu` | Row actions |
| `Toggle` / `ToggleGroup` | Platform filters, status filters |
| `Collapsible` | Config panels, advanced settings |
| `Sonner` (toast) | Notifications |
| `Skeleton` | Loading states |
| `Progress` | Run progress bars |
| `Switch` | Boolean settings |
| `Label` | Form labels |
| `Popover` | Date range, info |
| `Command` | Quick search (Cmd+K) |
| `Checkbox` | Bulk selection |

---

## 2. System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────┐
│                   React Frontend                     │
│  Vite + React + shadcn/ui (retro theme)              │
│  localhost:5173                                       │
│                                                      │
│  Pages: Dashboard · ROM Library · Run Manager ·      │
│         Run Detail · Emulator Config                 │
└──────────────────────┬──────────────────────────────┘
                       │  REST / WebSocket
                       ▼
┌─────────────────────────────────────────────────────┐
│               Python Backend (FastAPI)               │
│  localhost:8000                                       │
│                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  Run Engine  │  │  ROM Scanner │  │  Metrics   │  │
│  │  (manages    │  │  (discovers  │  │  Collector │  │
│  │   retro      │  │   ROMs &     │  │  (rewards, │  │
│  │   envs)      │  │   states)    │  │   loss,    │  │
│  │              │  │              │  │   fps)     │  │
│  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │
│         ▼                 ▼                ▼          │
│  ┌─────────────────────────────────────────────────┐ │
│  │              stable-retro (gym-retro)            │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────┐ │
│  │           SQLite (runs.db)                       │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Communication

- **REST API** — CRUD for runs, ROMs, configs
- **WebSocket** (`/ws/runs/{run_id}`) — Live metrics at 1Hz, frame captures at 0.5Hz
- **File serving** — Thumbnails, frames, checkpoints from local filesystem

### Data Flow: Starting a Run

```
User picks ROM → state → algorithm → hyperparams
        │
        ▼  POST /api/runs
Backend validates, writes to SQLite, spawns subprocess
        │
        ▼  WebSocket push per tick
Frontend receives metrics, updates charts + status
        │
        ▼  Completion / stop / crash
Final metrics → DB, status updated, WS closed
```

---

## 3. Backend API Surface

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/roms` | All discovered ROMs with metadata |
| `GET` | `/api/roms/{id}` | ROM detail with states + integration info |
| `GET` | `/api/roms/{id}/states` | Available save states |
| `POST` | `/api/runs` | Start training run |
| `GET` | `/api/runs` | List runs (filter: status, rom, algorithm, date) |
| `GET` | `/api/runs/{id}` | Run detail + latest metrics |
| `POST` | `/api/runs/{id}/stop` | Graceful stop |
| `POST` | `/api/runs/{id}/pause` | Checkpoint + hold |
| `POST` | `/api/runs/{id}/resume` | Resume from checkpoint |
| `DELETE` | `/api/runs/{id}` | Delete run + data |
| `GET` | `/api/runs/{id}/metrics` | Full metric history |
| `GET` | `/api/runs/{id}/checkpoints` | Model checkpoints |
| `GET` | `/api/runs/{id}/frames` | Recent frames |
| `GET` | `/api/emulators` | Available cores |
| `GET` | `/api/config` | Global config |
| `PUT` | `/api/config` | Update config |

### WebSocket

| Path | Direction | Payload |
|------|-----------|---------|
| `/ws/runs/{id}` | Server → Client | `{ step, reward, avgReward, bestReward, loss, epsilon, fps, status }` |
| `/ws/runs/{id}` | Client → Server | `{ action: "stop" \| "pause" \| "screenshot" }` |

### Run Config (POST body)

```json
{
  "rom": "SonicTheHedgehog-Genesis",
  "state": "GreenHillZone.Act1",
  "algorithm": "PPO",
  "hyperparams": {
    "learning_rate": 0.0003,
    "n_steps": 2048,
    "batch_size": 64,
    "n_epochs": 10,
    "gamma": 0.99,
    "clip_range": 0.2
  },
  "n_envs": 8,
  "max_steps": 1000000,
  "checkpoint_interval": 50000,
  "frame_capture_interval": 10000,
  "reward_shaping": "default",
  "observation_type": "image",
  "action_space": "filtered"
}
```

---

## 3b. Backend Architecture — Python / FastAPI

### Why FastAPI

stable-retro and Stable Baselines3 are Python libraries. The training loop, environment wrappers, reward shaping, and checkpoint management all live in Python. FastAPI is the natural choice because it gives us async HTTP + WebSocket support in the same process, Pydantic models for request/response validation (which means the API contract is enforced at the Python layer, not just documented), and native `asyncio` integration for managing concurrent training runs. It's also fast enough for localhost — there's no load balancing or multi-worker concern for a single-user dev tool.

### How the Frontend Connects

```
React (localhost:5173)
   │
   ├─ REST ──────────► FastAPI (localhost:8000/api/*)
   │                      CORS middleware allows localhost:5173
   │                      JSON request/response, Pydantic validated
   │
   ├─ WebSocket ─────► FastAPI (localhost:8000/ws/runs/{id})
   │                      Native FastAPI WebSocket endpoint
   │                      Server pushes JSON messages per tick
   │
   └─ Static files ──► FastAPI (localhost:8000/files/*)
                          Frames, thumbnails, checkpoints served directly
```

**CORS** — FastAPI's `CORSMiddleware` is configured to allow `http://localhost:5173` (the Vite dev server). In production (if you ever package this), both would be served from the same origin and CORS goes away. The middleware is the only thing that makes cross-origin fetch and WebSocket upgrade work from the browser.

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Retro Runner", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for frames, thumbnails, checkpoints
app.mount("/files", StaticFiles(directory="data/files"), name="files")

# Routers
from app.routers import roms, runs, config, emulators, ws
app.include_router(roms.router, prefix="/api/roms", tags=["roms"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(emulators.router, prefix="/api/emulators", tags=["emulators"])
app.include_router(ws.router, prefix="/ws", tags=["websocket"])
```

### Backend Module Layout

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, CORS, router registration
│   ├── routers/
│   │   ├── roms.py              # GET /api/roms, GET /api/roms/{id}
│   │   ├── runs.py              # CRUD for runs — POST, GET, DELETE, stop/pause/resume
│   │   ├── config.py            # GET/PUT /api/config
│   │   ├── emulators.py         # GET /api/emulators
│   │   └── ws.py                # WebSocket endpoint /ws/runs/{id}
│   ├── services/
│   │   ├── rom_scanner.py       # Discovers ROMs + states from configured directories
│   │   ├── run_engine.py        # Spawns/stops/pauses training subprocesses
│   │   ├── metrics_store.py     # Reads/writes metric history to SQLite
│   │   └── ws_manager.py        # Tracks active WS connections, broadcasts messages
│   ├── training/
│   │   ├── runner.py            # The actual training loop (runs in subprocess)
│   │   ├── wrappers.py          # Gym environment wrappers (obs, reward, action)
│   │   └── callbacks.py         # SB3 callbacks for metrics, checkpoints, frames
│   ├── models/
│   │   ├── schemas.py           # Pydantic models for API request/response
│   │   └── db.py                # SQLite connection, table definitions, queries
│   └── config_loader.py         # Reads config.yaml, provides defaults
├── data/
│   ├── runs/                    # Per-run directories (metrics, checkpoints, frames)
│   │   └── {run_id}/
│   │       ├── metrics.jsonl    # Append-only metric log
│   │       ├── checkpoints/     # SB3 model saves
│   │       └── frames/          # Captured PNG frames
│   └── files/                   # Served by StaticFiles mount
├── config.yaml                  # User-editable defaults
├── requirements.txt
└── runs.db                      # SQLite database
```

### Pydantic Models — The API Contract

Every request and response passes through Pydantic. This means the frontend can trust the shape of every JSON response, and the backend rejects malformed requests before any logic runs. These models are the single source of truth for the API contract between React and Python.

```python
# app/models/schemas.py
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"

class AlgorithmType(str, Enum):
    PPO = "PPO"
    A2C = "A2C"
    DQN = "DQN"

class Hyperparams(BaseModel):
    learning_rate: float = 0.0003
    n_steps: int = 2048
    batch_size: int = 64
    n_epochs: int = 10
    gamma: float = 0.99
    clip_range: float = 0.2

class RunCreate(BaseModel):
    """POST /api/runs request body"""
    rom: str
    state: str
    algorithm: AlgorithmType = AlgorithmType.PPO
    hyperparams: Hyperparams = Hyperparams()
    n_envs: int = Field(default=8, ge=1, le=32)
    max_steps: int = Field(default=1_000_000, ge=1000)
    checkpoint_interval: int = 50_000
    frame_capture_interval: int = 10_000
    reward_shaping: str = "default"
    observation_type: str = "image"
    action_space: str = "filtered"

class RunResponse(BaseModel):
    """GET /api/runs/{id} response"""
    id: str
    rom: str
    state: str
    algorithm: AlgorithmType
    status: RunStatus
    hyperparams: Hyperparams
    n_envs: int
    max_steps: int
    total_steps: int = 0
    best_reward: float | None = None
    avg_reward: float | None = None
    fps: float | None = None
    episodes: int = 0
    started_at: datetime
    finished_at: datetime | None = None
    error_message: str | None = None

class RomResponse(BaseModel):
    """GET /api/roms response item"""
    id: str
    name: str
    platform: str
    file_path: str
    file_size: int
    states: list[str]
    region: str | None = None
    last_trained: datetime | None = None
    active_runs: int = 0

class MetricPoint(BaseModel):
    """Single metric tick — sent via WS and stored in metrics.jsonl"""
    step: int
    reward: float
    avg_reward: float
    best_reward: float
    loss: float | None = None
    value_loss: float | None = None
    entropy: float | None = None
    epsilon: float | None = None
    fps: float
    timestamp: float

class WsMessage(BaseModel):
    """Every WebSocket message has a type field for routing"""
    type: str   # "metrics" | "status" | "frame" | "episode" | "error" | "complete"
    run_id: str
    data: dict  # Payload varies by type
```

### Training Subprocess Architecture

Training runs are CPU-intensive and blocking. They can't share the FastAPI async event loop. Each run spawns as a **separate subprocess** using `multiprocessing.Process`. The subprocess runs the stable-retro environment and SB3 training loop. It communicates back to the main FastAPI process via a `multiprocessing.Queue` for metrics and status updates.

```
FastAPI main process (async, handles HTTP + WS)
    │
    ├─ POST /api/runs → run_engine.start_run()
    │       │
    │       ▼
    │   Spawns multiprocessing.Process(target=training.runner.train)
    │       │
    │       ├─ Child process:
    │       │     retro.make(game, state)
    │       │     SB3 algorithm.learn(total_timesteps)
    │       │     SB3 callbacks push MetricPoints to Queue
    │       │
    │       └─ Returns immediately, run_id in response
    │
    ├─ asyncio.Task: queue_reader(run_id)
    │       Polls the Queue in a loop (non-blocking via run_in_executor)
    │       On each MetricPoint:
    │         - Appends to metrics.jsonl
    │         - Broadcasts to all WS clients for this run_id
    │         - Updates SQLite with latest stats
    │
    ├─ POST /api/runs/{id}/stop → run_engine.stop_run()
    │       Sets a shared multiprocessing.Event
    │       Child process checks event in callback, exits cleanly
    │
    └─ WebSocket /ws/runs/{id}
            ws_manager adds connection to run_id's subscriber set
            queue_reader broadcasts to all subscribers
```

**Why subprocesses, not threads?** Python's GIL means threads can't achieve true CPU parallelism for the training loop. `multiprocessing.Process` gives each run its own interpreter and full CPU core access. The Queue is the only coordination point — clean, no shared memory issues.

**Why not Celery / Redis / task queue?** This is a local single-user dev tool. Adding a message broker and worker infrastructure would be massive overkill. A `multiprocessing.Queue` does the same job with zero additional dependencies or processes.

### Run Engine — Process Lifecycle

```python
# app/services/run_engine.py (conceptual)
import multiprocessing as mp
from app.training.runner import train

class RunEngine:
    def __init__(self):
        self.processes: dict[str, mp.Process] = {}
        self.queues: dict[str, mp.Queue] = {}
        self.stop_events: dict[str, mp.Event] = {}

    def start_run(self, run_id: str, config: RunCreate) -> None:
        queue = mp.Queue()
        stop_event = mp.Event()
        process = mp.Process(
            target=train,
            args=(run_id, config.model_dump(), queue, stop_event),
            daemon=True,
        )
        process.start()
        self.processes[run_id] = process
        self.queues[run_id] = queue
        self.stop_events[run_id] = stop_event

    def stop_run(self, run_id: str) -> None:
        if run_id in self.stop_events:
            self.stop_events[run_id].set()  # Signal child to exit

    def pause_run(self, run_id: str) -> None:
        # Pause = checkpoint + stop. Resume = start from checkpoint.
        self.stop_run(run_id)

    def is_alive(self, run_id: str) -> bool:
        return run_id in self.processes and self.processes[run_id].is_alive()
```

### Training Runner — The Subprocess Entry Point

This is the function that runs inside each child process. It sets up the stable-retro environment, wraps it, configures the SB3 algorithm, and starts training. The SB3 callback system pushes metrics to the Queue.

```python
# app/training/runner.py (conceptual)
import retro
from stable_baselines3 import PPO, A2C, DQN
from stable_baselines3.common.vec_env import SubprocVecEnv
from app.training.wrappers import wrap_env
from app.training.callbacks import MetricsCallback, CheckpointCallback, FrameCallback

ALGORITHMS = {"PPO": PPO, "A2C": A2C, "DQN": DQN}

def make_env(game: str, state: str, config: dict):
    """Factory for SubprocVecEnv — each call returns a fresh env."""
    def _init():
        env = retro.make(game=game, state=state)
        env = wrap_env(env, config)  # Observation, reward, action wrappers
        return env
    return _init

def train(run_id: str, config: dict, queue, stop_event):
    """Runs in a child process. Blocks until training completes or stop_event is set."""
    try:
        # Build vectorised environment
        env = SubprocVecEnv([
            make_env(config["rom"], config["state"], config)
            for _ in range(config["n_envs"])
        ])

        # Select algorithm
        AlgClass = ALGORITHMS[config["algorithm"]]
        model = AlgClass(
            "CnnPolicy",
            env,
            learning_rate=config["hyperparams"]["learning_rate"],
            n_steps=config["hyperparams"]["n_steps"],
            batch_size=config["hyperparams"]["batch_size"],
            n_epochs=config["hyperparams"]["n_epochs"],
            gamma=config["hyperparams"]["gamma"],
            clip_range=config["hyperparams"]["clip_range"],
            verbose=0,
        )

        # Callbacks push data through the Queue
        callbacks = [
            MetricsCallback(run_id, queue, stop_event),
            CheckpointCallback(run_id, config["checkpoint_interval"]),
            FrameCallback(run_id, queue, config["frame_capture_interval"]),
        ]

        model.learn(
            total_timesteps=config["max_steps"],
            callback=callbacks,
        )

        # Normal completion
        queue.put({"type": "complete", "run_id": run_id, "data": {}})

    except Exception as e:
        queue.put({"type": "error", "run_id": run_id, "data": {
            "message": str(e),
            "traceback": traceback.format_exc(),
        }})
    finally:
        env.close()
```

### SB3 Callbacks — The Metrics Pipeline

SB3 calls these callbacks at each training step. They're the bridge between the training loop and the rest of the system.

```python
# app/training/callbacks.py (conceptual)
from stable_baselines3.common.callbacks import BaseCallback
import time

class MetricsCallback(BaseCallback):
    """Pushes a MetricPoint to the Queue every N steps."""

    def __init__(self, run_id: str, queue, stop_event, push_interval: int = 1):
        super().__init__()
        self.run_id = run_id
        self.queue = queue
        self.stop_event = stop_event
        self.push_interval = push_interval  # seconds
        self.last_push = 0
        self.best_reward = float("-inf")

    def _on_step(self) -> bool:
        # Check for stop signal
        if self.stop_event.is_set():
            return False  # Stops training

        now = time.time()
        if now - self.last_push >= self.push_interval:
            # Gather metrics from SB3 logger
            reward = self.locals.get("rewards", [0])[-1]
            self.best_reward = max(self.best_reward, reward)

            self.queue.put({
                "type": "metrics",
                "run_id": self.run_id,
                "data": {
                    "step": self.num_timesteps,
                    "reward": float(reward),
                    "avg_reward": float(self.training_env.get_attr("episode_returns")[0][-1])
                        if hasattr(self.training_env, "get_attr") else 0.0,
                    "best_reward": float(self.best_reward),
                    "loss": self.logger.name_to_value.get("train/loss"),
                    "value_loss": self.logger.name_to_value.get("train/value_loss"),
                    "entropy": self.logger.name_to_value.get("train/entropy_loss"),
                    "fps": float(self.num_timesteps / max(now - self.start_time, 1)),
                    "timestamp": now,
                },
            })
            self.last_push = now

        return True  # Continue training

    def _on_training_start(self):
        self.start_time = time.time()
```

### WebSocket Manager — Server-Side Broadcasting

The WS manager tracks which WebSocket connections are subscribed to which run, and broadcasts messages from the Queue reader to all subscribers.

```python
# app/services/ws_manager.py
from fastapi import WebSocket
from collections import defaultdict

class WsManager:
    def __init__(self):
        self.connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, run_id: str, ws: WebSocket):
        await ws.accept()
        self.connections[run_id].add(ws)

    def disconnect(self, run_id: str, ws: WebSocket):
        self.connections[run_id].discard(ws)
        if not self.connections[run_id]:
            del self.connections[run_id]

    async def broadcast(self, run_id: str, message: dict):
        dead = []
        for ws in self.connections.get(run_id, set()):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(run_id, ws)

    def has_subscribers(self, run_id: str) -> bool:
        return bool(self.connections.get(run_id))
```

### WebSocket Endpoint

```python
# app/routers/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

@router.websocket("/runs/{run_id}")
async def run_websocket(websocket: WebSocket, run_id: str):
    await ws_manager.connect(run_id, websocket)
    try:
        while True:
            # Client can send commands (stop, pause, screenshot)
            data = await websocket.receive_json()
            if data.get("action") == "stop":
                run_engine.stop_run(run_id)
            elif data.get("action") == "pause":
                run_engine.pause_run(run_id)
    except WebSocketDisconnect:
        ws_manager.disconnect(run_id, websocket)
```

### Queue Reader — Bridging Subprocess to WebSocket

An async background task reads from each run's Queue and broadcasts to WebSocket subscribers. This is the glue between the child process and the frontend.

```python
# Started as a background task when a run begins
async def queue_reader(run_id: str, queue: mp.Queue):
    """Reads metrics from child process Queue, broadcasts via WS, persists to DB."""
    while True:
        # Non-blocking Queue read via run_in_executor
        try:
            message = await asyncio.get_event_loop().run_in_executor(
                None, lambda: queue.get(timeout=0.5)
            )
        except Empty:
            # Check if process is still alive
            if not run_engine.is_alive(run_id):
                break
            continue

        # Broadcast to all WS subscribers for this run
        await ws_manager.broadcast(run_id, message)

        # Persist to metrics.jsonl
        if message["type"] == "metrics":
            metrics_store.append(run_id, message["data"])

        # Update run status in SQLite
        if message["type"] in ("status", "complete", "error"):
            metrics_store.update_run_status(run_id, message)

        # If run completed or errored, clean up
        if message["type"] in ("complete", "error"):
            metrics_store.finalize_run(run_id, message)
            break
```

### SQLite Database Layer

SQLite stores run metadata and provides the data behind REST list/detail endpoints. Metric time-series data lives in append-only `.jsonl` files on disk (one per run) rather than in SQLite — this avoids write contention and makes it trivial to stream or export. SQLite only stores the summary stats (latest step, best reward, status) that the list views need.

```python
# app/models/db.py (conceptual)
import sqlite3
from contextlib import contextmanager

DB_PATH = "runs.db"

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                rom TEXT NOT NULL,
                state TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                config JSON NOT NULL,
                total_steps INTEGER DEFAULT 0,
                best_reward REAL,
                avg_reward REAL,
                fps REAL,
                episodes INTEGER DEFAULT 0,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                error_message TEXT
            )
        """)

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
```

### ROM Scanner

Walks configured directories looking for ROM files, identifies platforms from file extensions, discovers available save states, and caches results. Re-scan is triggered manually from the frontend or on startup.

```python
# app/services/rom_scanner.py (conceptual)
import retro

class RomScanner:
    def __init__(self, rom_dirs: list[str]):
        self.rom_dirs = rom_dirs
        self._cache: list[dict] | None = None

    def scan(self) -> list[dict]:
        """Discover all ROMs and their available states."""
        roms = []
        for game in retro.data.list_games():
            states = retro.data.list_states(game)
            if not states:
                continue
            info = retro.data.get_game_info(game)
            roms.append({
                "id": game,
                "name": game.replace("-", " "),
                "platform": info.get("platform", "unknown"),
                "states": states,
                "file_path": retro.data.get_romfile_path(game),
            })
        self._cache = roms
        return roms

    def get_roms(self) -> list[dict]:
        if self._cache is None:
            self.scan()
        return self._cache

    def get_rom(self, rom_id: str) -> dict | None:
        return next((r for r in self.get_roms() if r["id"] == rom_id), None)

    def invalidate(self):
        self._cache = None
```

### Python Dependencies

```
# requirements.txt
fastapi>=0.115
uvicorn[standard]>=0.30
pydantic>=2.0
stable-retro>=0.9
stable-baselines3>=2.3
gymnasium>=0.29
torch>=2.0
numpy
Pillow                # Frame capture encoding
pyyaml                # Config file
```

### Running the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`--reload` watches for file changes during development. The frontend's Vite dev server on `:5173` connects to `:8000` via the CORS-allowed origin. Both run simultaneously in separate terminals.

---

## 4. Pages

---

### 4.1 — Dashboard

**Purpose:** At-a-glance operational overview. Landing page. What's running, what's winning, what's broken.

**Vibe:** NASA flight ops for retro games. The CRT void background (`--background`) makes the phosphor green numbers pop. Stat cards sit on `--card` surfaces — just a shade lighter than the void, like raised panels on a control console. Active runs pulse with `animate-live` on their status badges. Step counters tick up in monospace. Sparklines draw themselves in `--chart-1` green, tracing reward trajectories like oscilloscope readouts. The activity feed scrolls like a terminal log — most recent events at top, each stamped with a dim `--muted-foreground` timestamp. In light mode the whole thing softens — parchment backgrounds, muted greens — but the layout and density stay identical. It still reads as "ops dashboard", just with the blinds open.

**Layout:**

- **Top strip** — 4 `Card` components in a row:
  - Active Runs (count, Badge `variant="default"` + `animate-live` if > 0)
  - Total Steps (formatted "2.4M")
  - Best Reward (all-time, ROM name in `text-muted-foreground`)
  - Uptime
  - Each: `text-mono-xs tracking-stat` label, `text-2xl font-bold` value
- **Active Runs** — `Table` with `table-dense`. Columns: ROM, state, algorithm `Badge variant="outline"`, live steps, sparkline (custom SVG using `--chart-1`), FPS, `Button variant="destructive" size="sm"` stop. Row click → Run Detail. Empty state: `Card` with `Button variant="default"` CTA.
- **Activity Feed** — `ScrollArea` list. Each: `Badge` (started = default, completed = secondary, failed = destructive), text, timestamp `text-muted-foreground`. Max ~20 entries.
- **Quick Actions** — "+ New Run" `Button variant="default"` in global nav. "Stop All" `Button variant="destructive" size="sm"` when 2+ active.

**shadcn:** Card, Table, Badge, Button, ScrollArea, Skeleton, Separator

**Requirements:**

- WS to all active runs simultaneously
- Sparklines from last N WS points, not full history
- Live stat updates without full re-render
- Activity feed from DB (persists)
- Graceful empty state
- WS auto-reconnect with backoff
- Responsive: 2×2 cards on narrow, card list on mobile

---

### 4.2 — ROM Library

**Purpose:** Browse and manage ROMs. Pick what game the AI learns.

**Vibe:** A game cartridge shelf rendered as data cards. Each ROM `Card` sits on `--card` — in dark mode they look like labelled cartridge slots in a dark cabinet. Platform badges use variant colours: every platform reads differently through `Badge` variants without custom colors. Search is instant — the `Input` focus ring glows `--ring` (phosphor green), filtering cards in real time like a terminal autocomplete. In light mode the cards are warm parchment tiles with clean typography. The `Sheet` flyout for ROM detail slides in from the right like pulling a cartridge out for inspection — full specs, state list, run history, all in the same monospace typographic system.

**Layout:**

- **Top bar** — `Input` (instant filter), `ToggleGroup` platform chips (only populated platforms, with counts), `Select` sort (name, platform, states, recent).
- **ROM Grid** — Responsive `Card` grid. Each:
  - ROM name `font-semibold`
  - Platform `Badge` (Genesis = default, NES = secondary, SNES = outline — convention consistent)
  - State count `text-muted-foreground`
  - File size + region
  - Last trained `text-muted-foreground`
  - `Button variant="ghost" size="sm"` "Start Run →"
  - Active indicator: `Badge variant="default"` + `animate-live`
- **ROM Detail** — `Sheet` right slide-over:
  - File path (monospace)
  - States as `Badge variant="outline"` chips
  - Integration info in `Collapsible`
  - Past runs `Table`
  - `Button variant="default"` "Start Run"

**shadcn:** Card, Input, Badge, Button, ToggleGroup, Select, Sheet, Table, Collapsible, ScrollArea, Skeleton

**Requirements:**

- Backend discovers ROMs, frontend caches on mount
- Client-side search, no API per keystroke
- Platform tabs show counts
- Virtualised grid for 100+
- Empty state: ROM directory instructions
- Re-scan `Button variant="outline"`
- Active run indicator on cards

---

### 4.3 — Run Manager (All Runs)

**Purpose:** Full run history. Filter, sort, compare, bulk-manage.

**Vibe:** A terminal log viewer. The `Table` dominates — tight rows, monospace text, `table-dense` spacing. `--border` lines are barely visible in dark mode, like faint gridlines on an oscilloscope screen. Status badges are the only colour pops — green default for running, red destructive for failed — everything else is `--foreground` and `--muted-foreground` text. Sorting clicks snap the table instantly. Filters narrow without loading spinners. In light mode the table lines warm up to `--border` parchment strokes, badges soften, but the density and readability stay identical. This page is for power-scrolling through hundreds of runs.

**Layout:**

- **Filter bar** — `ToggleGroup` status (All, Running, Completed, Failed, Paused + counts). `Select` ROM. `Select` algorithm. `Popover` date range. `Input` search. Flex row, wraps.
- **Runs table** — `Table` + `table-dense`:
  - `Checkbox` bulk select
  - Status `Badge`
  - Run ID `text-mono-xs text-muted-foreground` + `Tooltip` full + click-copy
  - ROM, State, Algorithm `Badge variant="outline"`
  - Steps ("245.8K"), Best Reward, Avg Reward, Duration, Started
  - `DropdownMenu` actions: View, Stop, Delete
- **Bulk actions** — On selection: `Button variant="destructive"` "Stop Selected", "Delete Selected" → `Dialog` confirm.
- **Footer** — Pagination, total count, CSV export `Button variant="outline"`

**shadcn:** Table, Badge, Button, ToggleGroup, Select, Input, Popover, DropdownMenu, Dialog, Tooltip, Checkbox

**Requirements:**

- Filters + sort as URL query params
- Sortable columns
- Bulk delete lists affected runs in `Dialog`
- Running runs: live steps via WS
- Failed: error in `Tooltip`
- Row click → `/runs/{id}`
- CSV export
- Keyboard nav

---

### 4.4 — Run Detail

**Purpose:** Deep dive. Full metrics, config, controls, diagnostics.

**Vibe:** The oscilloscope page. Charts are the star — canvas-rendered inside `Card` containers that sit on `--card` backgrounds. In dark mode, chart gridlines in `--muted` look like the etched grid on a CRT oscilloscope faceplate. Reward lines trace in `--chart-1` phosphor green, loss in `--chart-2` red, epsilon in `--chart-3` amber. The crosshair tooltip snaps to data points with a `--border` stroke. Stat tiles at the top show big monospace numbers — the kind you'd see on a seven-segment display if this were physical hardware. When the run is active, the status Badge pulses, FPS ticks, and the charts extend rightward with new data flowing in. When it's done, everything freezes into a clean post-mortem. In light mode the charts soften to muted versions of the same palette, gridlines warm up, but the instrument-panel layout is unchanged.

**Layout:**

- **Header** — ROM `text-xl font-bold`, state, status `Badge` (pulsing if running), algorithm `Badge variant="outline"`, run ID `text-muted-foreground` (copyable). Right: Stop `variant="destructive"`, Pause `variant="outline"`, Resume `variant="default"`, Delete `variant="ghost"`, Duplicate `variant="ghost"`.
- **Stats bar** — 6 `Card` tiles:
  - Total Steps
  - Best Reward ("at step X" `text-muted-foreground`)
  - Avg Reward (last 100 eps)
  - FPS (live or "—")
  - Elapsed Time
  - Episodes
  - `Progress` bar: steps / max_steps, full width below
- **Charts** — Stacked `Card` containers:
  - **Episode Reward** (~240px) — `--chart-1` line + rolling avg
  - **Policy/Value Loss** (~160px) — `--chart-2`
  - **Exploration ε** (~120px) — `--chart-3`
  - **FPS** (~100px) — `--chart-4`
  - Crosshair hover, click-drag zoom, double-click reset
- **Config** — `Collapsible`, monospace JSON, `Button variant="ghost" size="sm"` "Copy JSON"
- **Checkpoints** — `Table` in `Card`: step, timestamp, size, reward. `Button variant="outline" size="sm"` "Resume" → `Dialog`. `Button variant="ghost" size="sm"` "Download".
- **Frame Preview** — Small `Card`, latest frame ~0.5Hz. `Switch` to toggle.
- **Error** — If failed: `Card` with monospace traceback, scrollable.

**shadcn:** Card, Badge, Button, Progress, Table, Collapsible, Dialog, Switch, Tooltip, Separator, Skeleton

**Requirements:**

- WS for live metrics
- Charts handle 200K+ points (downsample, full on zoom)
- Zoom persists during live updates
- CSV metric export
- Config copy as JSON
- Checkpoint resume → `Dialog` confirm
- Frame preview toggleable
- Deep-linkable `/runs/{id}`

---

### 4.5 — Emulator Configuration

**Purpose:** Manage cores, ROM directories, global defaults. The settings page.

**Vibe:** BIOS settings. Structured, sectioned, form-heavy but clean. Each section is a `Card` — in dark mode they're dark panels separated by `Separator` lines that are barely there. `Switch` toggles feel like physical DIP switches on old hardware. `Input` fields have that green `--ring` focus glow. In light mode it reads like a well-typeset technical manual — warm paper, clean labels, functional inputs. It should feel like configuring something that matters, then walking away.

**Layout:**

- **Emulator Cores** — `Card` + `Table`: core name, platform, version, status `Badge` (Ready = default, Missing = destructive, Update = outline), path, `Button variant="outline" size="sm"` "Test"
- **ROM Directories** — `Card`: `Input` per path + ROM count `text-muted-foreground` + `Button variant="ghost" size="icon"` remove. `Button variant="outline"` "Add Directory". `Button variant="secondary"` "Re-scan All".
- **Default Hyperparams** — `Card` 2-col grid: `Select` algorithm, `Input` fields (lr, batch, n_steps, gamma). Pre-fill New Run, always overridable.
- **Integration** — `Card`: `Select` obs type, `Select` action space, `Select` reward shaping + `Input` custom path, `Switch` frame capture + `Input` interval, `Input` checkpoint interval.
- **Backend** — `Card`: `Input` URL, `Input` WS settings, `Select` retention, disabled `Input` DB path, disk usage + `Button variant="outline"` "Clean Up" → `Dialog`.
- **Per-section** — `Button variant="default"` "Save" or auto-save + Sonner toast.

**shadcn:** Card, Table, Badge, Button, Input, Select, Switch, Label, Separator, Dialog, Sonner

**Requirements:**

- Settings in backend config file
- Directory changes → re-scan with `Progress`
- Core "Test" hits endpoint
- Defaults populate modal, don't override explicit
- Inline validation `text-destructive`
- Reset-to-defaults `Button variant="ghost"` per section
- Disk usage + cleanup

---

## 5. Shared Components

### New Run Dialog

`Dialog` from global nav. Three steps:

1. **Pick ROM** — compact card grid, `ToggleGroup` platform, `Input` search
2. **Pick State** — `ToggleGroup` state chips
3. **Configure** — `Select` algorithm, `Input` hyperparams (pre-filled), `Collapsible` advanced

`Button variant="default"` "Launch Run" — disabled until ROM + state selected.

### Status Badge

Maps status → variant:

```
running   → variant="default" + animate-live
completed → variant="secondary"
failed    → variant="destructive"
paused    → variant="outline"
queued    → variant="outline" + text-muted-foreground
```

### Metric Sparkline

Custom SVG, ~40px. Line in `hsl(var(--chart-1))`, fill in `hsl(var(--chart-1) / 0.1)`. No axes.

### Metric Chart (Full)

Custom canvas inside `Card`. Draws using CSS variables:
- Grid: `hsl(var(--muted))`
- Axes: `hsl(var(--muted-foreground))`
- Lines: `hsl(var(--chart-N))` per metric
- Tooltip border: `hsl(var(--border))`

Crosshair, zoom, downsample.

### Quick Command

shadcn `Command`. Cmd+K. Searchable: ROMs, active runs, actions.

### Notifications

`Sonner` toasts, bottom-right, 4s auto-dismiss. Colours follow variant system automatically.

### CRT Overlay System

Three fixed layers rendered inside a `<div className="crt-overlay">` placed as the last child of `Shell.tsx`. The entire system toggles via `body.crt-enabled` — add the class to enable, remove to disable. Stored in user preferences via `ConfigContext`. A `Switch` in the TopBar or Emulator Config page controls it.

**Layer 1: Scanlines** (`crt-scanlines`) — Repeating 2px transparent / 2px tinted horizontal bars. A `crt-flicker` animation irregularly dips opacity at random-looking intervals (3%, 44%, 80% keyframes) to simulate phosphor instability. The flicker uses `steps(1)` timing so it snaps rather than fades — feels electrical, not smooth.

**Layer 2: Vignette** (`crt-vignette`) — Radial gradient from transparent center to darkened edges. Simulates light falloff on a curved CRT tube. Uses `--background` at varying opacity so it adapts to both modes. Stronger in dark (feels like looking into a monitor), subtle in light (just a gentle edge shadow).

**Layer 3: Glow bar** (`crt-glow-bar`) — A faint horizontal bright band in `--primary` that crawls down the screen and wraps on a 6s loop. Simulates the refresh sweep visible when you film a CRT. At 4% max opacity it's a texture, not a distraction — most users won't consciously notice it but it adds subconscious life to the dark mode.

All three layers are `pointer-events: none` and share the same fixed container at `z-index: 9999`. They have zero impact on layout or interaction.

```tsx
// Shell.tsx — last child inside the root wrapper
<div className="crt-overlay">
  <div className="crt-scanlines" />
  <div className="crt-vignette" />
  <div className="crt-glow-bar" />
</div>
```

### Page Transitions

Route changes trigger CRT signal metaphor animations on the page content wrapper:

**Enter (`animate-page-enter`)** — Content materialises from a bright horizontal line (scaleY 0.005, brightness 2.5) and expands to full frame over 350ms. Like a CRT warming up or a new video signal locking in. Uses `cubic-bezier(0.16, 1, 0.3, 1)` for a sharp attack that eases into place.

**Exit (`animate-page-exit`)** — Content collapses back to a horizontal slit with a brightness spike (phosphor afterglow) over 200ms. Exit is deliberately faster than enter — the old page should get out of the way quickly.

**Fast variant (`animate-page-enter-fast`)** — Same shape at 200ms for sub-navigation like tab switches within a page. Tabs don't need the full drama.

Implementation: a `PageTransition` wrapper component in `Shell.tsx` listens to React Router location changes, applies exit class → waits for animation end → swaps content → applies enter class. No library needed — `onAnimationEnd` callbacks handle the sequencing.

### Component Transitions

Smaller CRT-flavoured animations for individual element lifecycle:

| Class | Duration | Use | Effect |
|-------|----------|-----|--------|
| `animate-phosphor-in` | 300ms | Cards, stat tiles, rows mounting | Fade up with brief brightness flash (phosphor energising) |
| `stagger-children` | 40ms gaps | Grid containers, stat card rows, table bodies | Children appear sequentially top-to-bottom, like a CRT scanning rows onto screen |
| `animate-dialog-enter` | 250ms | `Dialog` opening | Bright horizontal slit → expand to full (mini CRT power-on) |
| `animate-dialog-exit` | 150ms | `Dialog` closing | Collapse to slit → brightness spike → gone (CRT power-off) |
| `animate-slide-in-right` | 250ms | `Sheet` panels | Slide from right edge with brief brightness overshoot |
| `animate-toast-in` | 200ms | Sonner toasts | Flash-in from right (signal blip) |
| `animate-chart-trace` | 600ms | MetricChart mount | Clip-path wipe left→right (like a signal being traced across the screen) |
| `animate-glitch` | 400ms | Error events, failed run notifications | Horizontal shudder + hue-rotate offset (interference burst). One-shot, not looping. Trigger programmatically. |
| `animate-live` | 2s loop | Running status badges, active indicators | Slow opacity pulse (phosphor glow cycling) |

### Transition Integration Points

Where each animation gets applied in the component tree:

| Location | Animation | Trigger |
|----------|-----------|---------|
| `Shell.tsx` page wrapper | `animate-page-enter` / `animate-page-exit` | Route change via React Router |
| Dashboard stat card row | `stagger-children` | Page mount |
| Dashboard active runs table rows | `animate-phosphor-in` | Row mount |
| ROM Library card grid | `stagger-children` | Page mount / filter change |
| ROM Detail `Sheet` | `animate-slide-in-right` | Sheet open |
| Run Manager table body | `stagger-children` | Page mount / filter change |
| Run Detail stat tiles | `stagger-children` | Page mount |
| Run Detail chart `Card`s | `animate-chart-trace` | Chart mount |
| New Run `Dialog` | `animate-dialog-enter` / `animate-dialog-exit` | Dialog open/close |
| Delete confirm `Dialog` | `animate-dialog-enter` / `animate-dialog-exit` | Dialog open/close |
| All `Sonner` toasts | `animate-toast-in` | Toast mount |
| Status badges (running) | `animate-live` | Always when status = running |
| Failed run notification | `animate-glitch` on nearest container | On WS status:failed event |
| Run stopped | `animate-glitch` (subtle) | On stop confirmation |

---

## 6. Data Layer

The app has three distinct data patterns that need different tools:

1. **REST state** — ROMs, run history, config, emulator cores. Classic request/response, fetched on page mount, mutated occasionally. The majority of endpoints.
2. **WebSocket streaming** — Live metrics from active runs. Continuous server-push at 1Hz while a run is alive. Multiple simultaneous connections (one per active run). Needs reconnect logic.
3. **High-throughput time-series** — The chart data path on Run Detail. Accumulates 200K+ points over the life of a run, one per second. Cannot flow through React state or the render cycle will choke.

Each pattern gets the right tool. Nothing is over-engineered, nothing is under-served.

### TanStack Query — REST State & Mutations

TanStack Query replaces the originally planned `RunsContext`, `RomsContext`, and `ConfigContext` entirely. Components call `useQuery` with a shared query key and automatically share the same cache — no providers, no reducers, no manual coordination. The value isn't just caching: it's background refetching when you tab back after a long training run, automatic retry on transient failures, loading/error states that map directly to Skeleton/error UI, and mutation invalidation that keeps every view in sync.

**Query configuration:**

```ts
// lib/queryClient.ts
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,        // 30s default — data is local, refetches are cheap
      retry: 1,                  // Localhost: if it fails once, it's probably down
      refetchOnWindowFocus: true, // "Walked away from a training run" scenario
    },
  },
})
```

**Query key structure:**

```ts
// lib/queryKeys.ts
export const queryKeys = {
  roms: {
    all:    ['roms']          as const,
    detail: (id: string) => ['roms', id] as const,
  },
  runs: {
    all:    ['runs']          as const,
    list:   (filters: RunFilters) => ['runs', 'list', filters] as const,
    detail: (id: string) => ['runs', id] as const,
    metrics:(id: string) => ['runs', id, 'metrics'] as const,
  },
  config:   ['config']        as const,
  emulators:['emulators']     as const,
}
```

**Per-resource staleTime overrides:**

| Resource | staleTime | Why |
|----------|-----------|-----|
| ROMs | `Infinity` | Never changes unless you re-scan. Invalidate manually on rescan. |
| Config | `Infinity` | Changes only on explicit save. Invalidate on mutation success. |
| Emulators | `Infinity` | Static after boot. Invalidate on re-scan or test. |
| Runs list | `30_000` (default) | Could change from other runs finishing. WS also pokes cache. |
| Run detail | `10_000` | Active runs get WS updates anyway. Completed runs are static. |

**Mutation invalidation map:**

All mutations use `useMutation` with `onSuccess` invalidations to keep every view consistent:

```ts
// hooks/useRunMutations.ts  (conceptual — each is a separate useMutation)

startRun:    onSuccess → invalidate ['runs'], navigate to new run detail
stopRun:     onSuccess → invalidate ['runs'], invalidate ['runs', id]
pauseRun:    onSuccess → invalidate ['runs', id]
resumeRun:   onSuccess → invalidate ['runs', id]
deleteRun:   onSuccess → invalidate ['runs'], navigate back if on detail
rescanRoms:  onSuccess → invalidate ['roms']
updateConfig:onSuccess → invalidate ['config']
testCore:    onSuccess → invalidate ['emulators']
```

**Optimistic updates** on stop/pause/resume: `onMutate` sets the new status immediately in the cache via `queryClient.setQueryData`, `onError` rolls back. The UI feels instant, the server confirms or corrects.

### WebSocket Layer — react-use-websocket

The `react-use-websocket` library handles connection lifecycle: automatic reconnect with configurable attempts and intervals, a `shouldReconnect` callback for close events, `readyState` tracking exposed as a hook return, and shared socket instances so multiple components subscribing to the same run URL don't open duplicate connections. It also provides `lastJsonMessage` and `sendJsonMessage` to skip manual parse/stringify.

For a localhost developer tool, the native WebSocket API with `reconnecting-websocket` (dependency-free, WebSocket API compatible, handles connection timeouts and message buffering during reconnection) is a lighter alternative. Either works. The architecture doesn't depend on which library sits underneath.

**Connection topology:**

```
WebSocketProvider (app-level)
  │
  ├─ Per-run connection: ws://localhost:8000/ws/runs/{run_id}
  │    Opens when run is active + any component subscribes
  │    Closes when run completes/stops OR all subscribers unmount
  │
  └─ Global connection (optional): ws://localhost:8000/ws/events
       Status change broadcasts for all runs (Dashboard, Run Manager)
       Avoids opening N connections for N active runs on list pages
```

**WebSocket message types and routing:**

Every WS message arrives as JSON with a `type` field. The message handler is the router — it reads the type and dispatches to the right destination:

| Message type | Payload | Destination | Handler |
|-------------|---------|-------------|---------|
| `status` | `{ run_id, status, ... }` | TanStack Query cache | `queryClient.setQueryData(['runs', id], ...)` |
| `metrics` | `{ run_id, step, reward, loss, fps, epsilon, ... }` | Metrics ref buffer | `metricsBufferRef.current.push(point)` |
| `frame` | `{ run_id, base64_frame }` | Frame state (throttled) | `setLatestFrame(data)` at 0.5Hz |
| `episode` | `{ run_id, episode_num, total_reward, steps }` | TanStack Query cache | `queryClient.setQueryData(['runs', id], ...)` |
| `error` | `{ run_id, message, traceback }` | TanStack Query cache + toast | Cache update + Sonner destructive toast |
| `complete` | `{ run_id, final_metrics }` | TanStack Query cache | Cache update, close WS |

The status/episode/error/complete messages write into TanStack Query via `setQueryData` so Dashboard, Run Manager, and Run Detail all see the update without refetching. The metrics messages bypass Query entirely and go straight into the ref buffer (see below).

### High-Throughput Metrics Path — useRef Buffer + requestAnimationFrame

This is the critical performance path. A training run can produce 200K+ metric data points. Pushing each one through React state (`useState` / `useReducer` / TanStack Query `setQueryData`) would trigger a re-render per message — at 1Hz per run that's manageable, but with multiple active runs on the Dashboard or long-running accumulation on Run Detail, it gets wasteful. More importantly, the canvas chart doesn't need React to re-render — it redraws directly.

The pattern: WS messages append to a `useRef` array. A `requestAnimationFrame` loop (or a 100ms `setInterval`) reads from the ref and redraws the canvas. No React state is involved in the hot path. The chart component reads from the ref directly.

```ts
// hooks/useLiveMetrics.ts  (conceptual)

export function useLiveMetrics(runId: string) {
  const bufferRef = useRef<MetricPoint[]>([])
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rafRef = useRef<number>()

  // WS callback — fires on every 'metrics' message
  const onMetric = useCallback((point: MetricPoint) => {
    bufferRef.current.push(point)
  }, [])

  // Animation loop — reads buffer, redraws canvas at ~15fps
  useEffect(() => {
    let lastDraw = 0
    const draw = (timestamp: number) => {
      if (timestamp - lastDraw > 66) {  // ~15fps cap
        drawChart(canvasRef.current, bufferRef.current)
        lastDraw = timestamp
      }
      rafRef.current = requestAnimationFrame(draw)
    }
    rafRef.current = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(rafRef.current!)
  }, [])

  // Also push summary stats into TQ cache at lower frequency
  // so stat tiles (Best Reward, Total Steps, etc.) update via React
  useEffect(() => {
    const interval = setInterval(() => {
      const buf = bufferRef.current
      if (buf.length === 0) return
      const latest = buf[buf.length - 1]
      queryClient.setQueryData(queryKeys.runs.detail(runId), (old) => ({
        ...old,
        latest_step: latest.step,
        best_reward: Math.max(old?.best_reward ?? -Infinity, latest.reward),
        fps: latest.fps,
      }))
    }, 1000)
    return () => clearInterval(interval)
  }, [runId])

  return { bufferRef, canvasRef, onMetric }
}
```

**Key techniques from the real-time dashboard community:**

- **Buffer in a ref, flush on interval** — decouples WS message rate from render rate. The browser handles thousands of messages/sec without choking because no setState is called on the hot path.
- **requestAnimationFrame for canvas** — syncs chart redraws with browser paint cycles. Capped at ~15fps because humans can't perceive sub-66ms updates on a time-series chart, and it keeps CPU headroom for everything else.
- **Downsampling in the draw function** — when the buffer exceeds the canvas pixel width, the draw function picks every Nth point or uses LTTB (Largest Triangle Three Buckets) to reduce to ~1000 visible points. The full buffer is kept for zoom.
- **Summary stats pushed to TQ at 1Hz** — the stat tiles (Best Reward, Total Steps, FPS, etc.) DO need React re-renders, but only once per second. A setInterval reads the latest point from the buffer and pokes the TQ cache, which triggers re-renders only for components subscribed to that query key.
- **Sparklines on the Dashboard** — same pattern, smaller buffer. Each active run card has its own `useLiveMetrics` with a short sliding window (last 60 points). The sparkline SVG re-renders at 1Hz via the TQ cache poke, not per-message.

### What Each Tool Owns

| Concern | Tool | Replaces |
|---------|------|----------|
| ROM list, detail | TanStack Query `useQuery` | `RomsContext` |
| Run list, detail, status | TanStack Query `useQuery` | `RunsContext` |
| Config, emulators | TanStack Query `useQuery` | `ConfigContext` |
| Start/stop/pause/delete | TanStack Query `useMutation` | Manual fetch + dispatch |
| WS connection lifecycle | `react-use-websocket` | Custom `useWebSocket` hook |
| WS message routing | `WebSocketContext` (kept) | Same — still needed as dispatcher |
| WS → status/metadata | `queryClient.setQueryData` | Context dispatch |
| WS → chart metrics | `useRef` buffer + rAF canvas | n/a (new) |
| WS → stat tile updates | `setInterval` → `queryClient.setQueryData` | Context dispatch |
| HTTP client | Native `fetch` wrapper (`lib/api.ts`) | Same |

### Data Flow Diagram — Live Run

```
WebSocket message arrives
         │
         ▼
   Parse JSON, read `type`
         │
         ├─ type: "metrics"
         │       │
         │       ▼
         │   bufferRef.current.push(point)     ← No React state, no re-render
         │       │
         │       ├─ requestAnimationFrame loop reads buffer → redraws canvas
         │       │
         │       └─ 1Hz setInterval reads latest → queryClient.setQueryData
         │                                          → stat tiles re-render
         │
         ├─ type: "status" | "episode" | "complete" | "error"
         │       │
         │       ▼
         │   queryClient.setQueryData(['runs', id], ...)
         │       │
         │       ▼
         │   All subscribed components re-render:
         │     Dashboard active runs table
         │     Run Manager row
         │     Run Detail header + status badge
         │
         └─ type: "frame"
                 │
                 ▼
             setLatestFrame(base64)              ← Throttled to 0.5Hz
                 │
                 ▼
             Frame preview Card re-renders
```

---

## 7. Tech Stack

| Decision | Choice | Why |
|----------|--------|-----|
| Bundler | Vite | Fast HMR, no SSR needed |
| UI | shadcn/ui (custom retro vars) | Variant-driven, theme via CSS vars |
| Styling | TailwindCSS | Ships with shadcn |
| Typography | JetBrains Mono | Monospace dev tool |
| Theme | Custom CSS vars in globals.css | Full control, both modes |
| Charts | Custom canvas + rAF loop | Perf for 200K+ points, themed via CSS vars, bypasses React render |
| Server state | TanStack Query | Shared cache replaces 3 contexts, mutation invalidation, background refetch |
| WS connections | react-use-websocket | Reconnect, shared sockets, readyState tracking |
| Live metrics | useRef buffer + requestAnimationFrame | Decouples WS rate from render rate, feeds canvas directly |
| Routing | React Router | Deep-linking, page transitions |
| HTTP | Native fetch wrapper | Localhost, no interceptors needed |
| Backend | FastAPI | stable-retro/SB3 ecosystem |
| DB | SQLite | Zero config |

---

## 8. File Structure

```
retro-runner/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── RomLibrary.tsx
│   │   │   ├── RunManager.tsx
│   │   │   ├── RunDetail.tsx
│   │   │   └── EmulatorConfig.tsx
│   │   ├── components/
│   │   │   ├── ui/                  # shadcn generated
│   │   │   ├── layout/
│   │   │   │   ├── TopBar.tsx
│   │   │   │   ├── Shell.tsx           # CRT overlay + page transition wrapper
│   │   │   │   └── PageTransition.tsx  # Route change animation sequencer
│   │   │   ├── domain/
│   │   │   │   ├── StatusBadge.tsx
│   │   │   │   ├── Sparkline.tsx
│   │   │   │   ├── MetricChart.tsx
│   │   │   │   ├── NewRunDialog.tsx
│   │   │   │   ├── RomCard.tsx
│   │   │   │   ├── RunRow.tsx
│   │   │   │   ├── ActiveRunCard.tsx
│   │   │   │   └── QuickCommand.tsx
│   │   ├── contexts/
│   │   │   └── WebSocketContext.tsx    # WS connection pool + message routing
│   │   ├── hooks/
│   │   │   ├── useLiveMetrics.ts      # Ref buffer + rAF canvas loop
│   │   │   ├── useRunMutations.ts     # TQ mutations: start/stop/pause/delete
│   │   │   └── useDebounce.ts
│   │   ├── lib/
│   │   │   ├── api.ts                 # Fetch wrapper for REST endpoints
│   │   │   ├── queryClient.ts         # TanStack Query client + defaults
│   │   │   ├── queryKeys.ts           # Centralised query key factory
│   │   │   └── utils.ts
│   │   ├── globals.css              # Theme vars + structural overrides
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── components.json             # shadcn config
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, CORS, router registration
│   │   ├── config_loader.py         # Reads config.yaml, provides defaults
│   │   ├── routers/
│   │   │   ├── roms.py              # GET /api/roms, GET /api/roms/{id}
│   │   │   ├── runs.py              # CRUD for runs
│   │   │   ├── config.py            # GET/PUT /api/config
│   │   │   ├── emulators.py         # GET /api/emulators
│   │   │   └── ws.py                # WebSocket /ws/runs/{id}
│   │   ├── services/
│   │   │   ├── rom_scanner.py       # ROM + state discovery
│   │   │   ├── run_engine.py        # Subprocess lifecycle management
│   │   │   ├── metrics_store.py     # JSONL append + SQLite summary writes
│   │   │   └── ws_manager.py        # WS connection tracking + broadcast
│   │   ├── training/
│   │   │   ├── runner.py            # Subprocess entry point (retro + SB3)
│   │   │   ├── wrappers.py          # Gym env wrappers (obs, reward, action)
│   │   │   └── callbacks.py         # SB3 callbacks → Queue metrics
│   │   └── models/
│   │       ├── schemas.py           # Pydantic request/response models
│   │       └── db.py                # SQLite connection + queries
│   ├── data/
│   │   ├── runs/                    # Per-run dirs: metrics.jsonl, checkpoints/, frames/
│   │   └── files/                   # Served by StaticFiles mount
│   ├── config.yaml
│   ├── requirements.txt
│   └── runs.db
│
└── README.md
```

---

## 9. Implementation Priority

**Phase 1 — Theme + skeleton + data layer:**
shadcn init, paste custom vars into globals.css, install all components, verify both modes render correctly. Install TanStack Query, set up `queryClient.ts` and `queryKeys.ts`, wrap app in `QueryClientProvider`. Install `react-use-websocket`. Backend: ROM scanner + run start/stop + SQLite. Frontend: Dashboard (static data via useQuery), ROM Library, New Run Dialog (useMutation), Run Detail (polling via useQuery).

**Phase 2 — Live:**
WebSocketContext + message routing. `useLiveMetrics` hook with ref buffer + rAF canvas loop. Live Dashboard + Run Detail via WS → setQueryData bridge. Sparklines from sliding window buffers. Run Manager with filters/sort (query key includes filters).

**Phase 3 — Polish:**
Emulator Config. Checkpoints. Frame preview (throttled WS frames). Chart zoom (reads from full buffer, downsamples visible). Bulk mutations. CSV export. Command palette. CRT scanline toggle. Keyboard nav. Optimistic updates on stop/pause/resume.

**Phase 4 — Power features:**
Run comparison overlays. Hyperparam sweep. Reward shaping editor. Run templates.
