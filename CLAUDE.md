# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pokemon AI agent that learns to play Pokemon FireRed through vision-based scene detection, evolutionary learning, and reinforcement learning. Uses mGBA emulator with socket communication for screen capture and input.

## Development Approach

**No backwards compatibility**: When developing features, stub what is not compatible and work on it incrementally rather than maintaining backwards-compat shims.

## Commands

```powershell
# Setup
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run
python app.py                    # Start dashboard UI
python test_components.py        # Run component tests

# External services (must be running)
ollama serve                     # Start local LLM server
ollama pull llava:7b             # Pull vision model
```

## Architecture

```
app.py              → Tkinter dashboard (entry point)
components/         → UI components (ControlBar, ActivityLog, etc.)
logic/
├── runner.py       → AgentRunner orchestrates the main loop
├── act/            → Emulator interaction (input, socket, action blocks)
├── consume/        → Data capture (screen, memory, state)
├── evolve/         → Genetic algorithm (genome, evolution)
├── learn/          → Post-run analysis and learning
└── review/         → AI feedback and logging
data/               → Runtime data (logs, screenshots, genomes, action_blocks)
```

## Key Patterns

- **Event queue communication**: UI and logic decoupled via Python queues
- **Socket-based capture**: Preferred over MSS for screen capture (works when minimized)
- **Action blocks**: Pre-scripted JSON sequences in `data/action_blocks/` for deterministic game sections (intro, menus)
- **Post-hoc learning**: AI reviews completed runs, doesn't slow gameplay
- **Genome-based evolution**: Learning weights stored in `data/genomes/`

## External Dependencies

- **Ollama + LLaVA**: Vision model for scene detection (runs on GPU)
- **mGBA**: GBA emulator with socket scripting support
- **Pokemon FireRed ROM**: User-provided

## Settings

`RunnerSettings` in `logic/runner.py` controls:
- `stride`: Frames between decisions
- `batch_size`: Actions per log entry
- `turbo`: Fast-forward mode
- `use_learning`: Enable learning
- `auto_launch`: Auto-start emulator
