# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Pokemon AI agent that learns to play Pokemon FireRed. Uses mGBA emulator with Lua socket for game state and input control.

## Development Approach

**No backwards compatibility**: Stub incompatible features and iterate incrementally.

## Architecture

```
auto-gamer/
├── apps/
│   ├── web/              # Vite + React frontend
│   │   └── src/
│   └── api/              # FastAPI + WebSocket backend
│       ├── main.py       # WebSocket server
│       └── mgba_client.py
├── mGBA/
│   └── scripts/
│       └── ai_control.lua  # mGBA socket interface
├── data/                 # Runtime data (gitignored)
└── docs/                 # Documentation
```

## Commands

```bash
# Install dependencies
pnpm install
cd apps/api && pip install -r requirements.txt

# Development
pnpm dev          # Start Vite frontend (port 5173)
pnpm dev:api      # Start FastAPI backend (port 8000)

# Build
pnpm build

# Linting & Formatting
pnpm lint         # Lint both web & api
pnpm typecheck    # Typecheck both web & api
pnpm lint:api     # Lint API only
pnpm format:api   # Format API code
pnpm typecheck:api # Typecheck API only
```

## Communication Flow

```
Frontend (React) ←WebSocket→ Backend (FastAPI) ←TCP Socket→ mGBA (Lua)
     :5173                        :8000                      :8765
```

## mGBA Lua Commands

Key commands available via `ai_control.lua`:
- `FULLSTATE` - Get game state JSON
- `INPUT <key>` - Send input (A, B, UP, DOWN, etc.)
- `RELEASE` - Release all keys
- `RESET` - Reset emulation
- `SAVE/LOAD <slot>` - Save states

## Key Patterns

- **WebSocket streaming**: Real-time state from backend to frontend
- **Async Python**: FastAPI with asyncio for non-blocking mGBA communication
- **Deferred execution**: mGBA Lua defers certain ops to frame callback
