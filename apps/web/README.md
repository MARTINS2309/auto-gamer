## Retro Runner — Web App

Local-only React UI for managing stable-retro emulator runs, configuring FastAPI backend, and visualizing live training metrics with a CRT-inspired shadcn/ui theme.

### Stack
- Vite + React + TypeScript
- shadcn/ui + TailwindCSS (retro CRT theme via globals.css overrides)
- TanStack Query for REST state
- WebSockets for live metrics/frames
- Custom canvas charts (requestAnimationFrame + ref buffers)
- Backend: FastAPI + stable-retro + Stable Baselines3 + SQLite

### Key Pages
- **Dashboard:** Active runs table with live WS metrics, stat cards, activity feed.
- **ROM Library:** Filterable ROM grid, platform toggles, detail sheet, start run CTA.
- **Run Manager:** Full history table with filters/sort, bulk stop/delete, CSV export.
- **Run Detail:** Live charts (reward, loss, epsilon, FPS), checkpoints, frames, config JSON.
- **Emulator Config:** Cores, ROM directories, defaults, integration settings.

### Theme Highlights
- Variant-only styling (`variant="default|secondary|destructive|outline|ghost"`), all colors from CSS vars.
- CRT overlays: scanlines, vignette, glow bar toggled via `body.crt-enabled`.
- Page/element transitions: CRT power-on/off metaphors (`animate-page-enter/exit`, `animate-phosphor-in`, etc.).

### Data Flow
- REST (fetch wrapper) for ROMs, runs, config, emulators.
- WebSockets `/ws/runs/{id}` for metrics/status/frames; messages route into ref buffers and TanStack Query cache.
- Metrics: useRef buffer + rAF redraw; stat tiles updated at 1Hz via `queryClient.setQueryData`.

### Backend API (essential endpoints)
- `GET /api/roms`, `GET /api/roms/{id}`
- `POST /api/runs` (start), `GET /api/runs`, `GET /api/runs/{id}`
- `POST /api/runs/{id}/stop|pause|resume`, `DELETE /api/runs/{id}`
- `GET /api/emulators`, `GET/PUT /api/config`
- `WS /ws/runs/{id}` → metrics/status/frame events

### Dev Setup
```bash
pnpm install
pnpm dev           # frontend at http://localhost:5173

# backend (in ../backend)
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Ensure CORS allows `http://localhost:5173` (configured in FastAPI). Frontend expects backend at `http://localhost:8000`.

### Repo Structure (web)
- `src/pages`: Dashboard, RomLibrary, RunManager, RunDetail, EmulatorConfig
- `src/components/domain`: StatusBadge, Sparkline, MetricChart, NewRunDialog, etc.
- `src/contexts/WebSocketContext.tsx`: WS connection pool + message routing
- `src/hooks/useLiveMetrics.ts`: ref buffer + rAF canvas loop
- `src/lib/queryClient.ts`, `src/lib/queryKeys.ts`: TanStack Query setup
- `src/globals.css`: full theme overrides + CRT overlays + animations

### Status → Badge variants
- running → `default` + `animate-live`
- completed → `secondary`
- failed → `destructive`
- paused/queued → `outline` (queued also `text-muted-foreground`)

### Notes
- Charts are canvas-based; do not pipe high-frequency metrics through React state.
- Keep shadcn components on variants; no one-off Tailwind color classes.
