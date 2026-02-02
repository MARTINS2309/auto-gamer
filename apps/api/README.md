## Retro Runner API (FastAPI)

Local-only backend for managing stable-retro emulator training runs. Serves REST + WebSocket for the Vite/React frontend.

### Stack
- FastAPI (HTTP + WebSocket)
- SQLite (runs metadata) + per-run JSONL/frames on disk
- stable-retro + Stable Baselines3 (training subprocesses)

### Quick start
```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Frontend expects CORS at `http://localhost:5173` (already configured).

### Config
- `config.yaml` — ROM dirs, defaults
- `data/runs/{run_id}/` — metrics.jsonl, checkpoints/, frames/
- `runs.db` — run metadata

### REST endpoints (prefix `/api`)
| Method | Path | Purpose |
|---|---|---|
| GET | `/roms` | List discovered ROMs |
| GET | `/roms/{id}` | ROM detail + states |
| POST | `/runs` | Start a run |
| GET | `/runs` | List runs (filters) |
| GET | `/runs/{id}` | Run detail |
| POST | `/runs/{id}/stop` | Graceful stop |
| POST | `/runs/{id}/pause` | Checkpoint + stop |
| POST | `/runs/{id}/resume` | Resume from checkpoint |
| DELETE | `/runs/{id}` | Delete run + data |
| GET | `/runs/{id}/metrics` | Full metric history |
| GET | `/runs/{id}/checkpoints` | Model checkpoints |
| GET | `/runs/{id}/frames` | Recent frames |
| GET | `/emulators` | Available cores |
| GET/PUT | `/config` | Global config |

### WebSocket
- Path: `/ws/runs/{id}`
- Server → client payloads: `{ type: "metrics" | "status" | "frame" | "episode" | "error" | "complete", run_id, data }`
- Client → server: `{ action: "stop" | "pause" | "screenshot" }`

### Run flow
1) POST `/api/runs` with ROM/state/algorithm/hyperparams
2) Backend spawns training subprocess (stable-retro + SB3)
3) Metrics emitted to Queue → JSONL append → WebSocket broadcast
4) Status/episode/error/complete messages update SQLite + WS
5) Stop/pause/resume hit POST endpoints; stop uses shared Event

### Example curl
```bash
curl -X POST http://localhost:8000/api/runs \
	-H 'Content-Type: application/json' \
	-d '{
		"rom": "SonicTheHedgehog-Genesis",
		"state": "GreenHillZone.Act1",
		"algorithm": "PPO",
		"hyperparams": {"learning_rate":0.0003,"n_steps":2048,"batch_size":64,"n_epochs":10,"gamma":0.99,"clip_range":0.2},
		"n_envs": 8,
		"max_steps": 1000000,
		"checkpoint_interval": 50000,
		"frame_capture_interval": 10000,
		"reward_shaping": "default",
		"observation_type": "image",
		"action_space": "filtered"
	}'
```

### Directory sketch
```
apps/api/
├── app/
│   ├── main.py             # FastAPI app, CORS, routers
│   ├── routers/            # roms, runs, config, emulators, ws
│   ├── services/           # run_engine, rom_scanner, metrics_store, ws_manager
│   ├── training/           # runner, wrappers, callbacks
│   └── models/             # schemas, db
├── data/
│   ├── runs/{id}/          # metrics.jsonl, checkpoints/, frames/
│   └── files/              # Static mount (/files)
├── config.yaml
├── runs.db
└── requirements.txt
```

### Notes
- CORS allows `http://localhost:5173`
- Runs execute as subprocesses (`multiprocessing.Process`); queue reader bridges to WS and DB
- Metrics should be consumed via WebSocket; REST `/metrics` is for full history export
