import json
import os
import shutil
import traceback
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..models.db import AgentModel, RomModel, RunMetricModel, RunModel, RunStatus, SessionLocal
from ..models.schemas import (
    ActionSpace,
    MetricPoint,
    ObservationType,
    RunCreate,
    RunResponse,
    RunUpdate,
)
from ..services.run_manager import manager as run_manager
from ..training.runner import find_latest_checkpoint
from .config import load_config

router = APIRouter()


def get_run_or_404(run_id: str, db: Session) -> RunModel:
    run = db.query(RunModel).filter(RunModel.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


def _enrich_run(run: RunModel, db: Session) -> RunModel:
    """Add agent_name, opponent_agent_name, and metrics summary to run for response serialization."""
    if run.agent_id:
        agent = db.query(AgentModel).filter(AgentModel.id == run.agent_id).first()
        run.agent_name = agent.name if agent else None  # type: ignore[attr-defined]
    else:
        run.agent_name = None  # type: ignore[attr-defined]
    if run.opponent_agent_id:
        opp = db.query(AgentModel).filter(AgentModel.id == run.opponent_agent_id).first()
        run.opponent_agent_name = opp.name if opp else None  # type: ignore[attr-defined]
    else:
        run.opponent_agent_name = None  # type: ignore[attr-defined]

    # Game display name and thumbnail from ROM
    rom = db.query(RomModel).filter(RomModel.id == run.rom).first()
    run.game_name = rom.display_name if rom else None  # type: ignore[attr-defined]
    thumbnail_path = rom.game_metadata.thumbnail_path if rom and rom.game_metadata else None
    run.game_thumbnail_url = f"/files/{thumbnail_path}" if thumbnail_path else None  # type: ignore[attr-defined]

    # Metrics summary from latest metric row
    latest = (
        db.query(RunMetricModel)
        .filter(RunMetricModel.run_id == run.id)
        .order_by(RunMetricModel.step.desc())
        .first()
    )
    if latest:
        run.latest_step = latest.step  # type: ignore[attr-defined]
        run.best_reward = latest.best_reward  # type: ignore[attr-defined]
        run.avg_reward = latest.avg_reward  # type: ignore[attr-defined]
    else:
        run.latest_step = None  # type: ignore[attr-defined]
        run.best_reward = None  # type: ignore[attr-defined]
        run.avg_reward = None  # type: ignore[attr-defined]

    return run


def find_agent_latest_model(agent_id: str, db: Session) -> str | None:
    """Find the most recent model file from any completed/stopped run of this agent."""
    latest_run = (
        db.query(RunModel)
        .filter(
            RunModel.agent_id == agent_id,
            RunModel.status.in_([RunStatus.COMPLETED.value, RunStatus.STOPPED.value]),
        )
        .order_by(RunModel.completed_at.desc())
        .first()
    )
    if not latest_run:
        return None

    checkpoint_path, _ = find_latest_checkpoint(latest_run.id)
    return checkpoint_path


@router.post("/runs", response_model=RunResponse)
def create_run(run_in: RunCreate, background_tasks: BackgroundTasks):
    db = SessionLocal()
    try:
        # Resolve ROM ID to connector/game name for retro
        target_game = run_in.rom
        run_rom_model = db.query(RomModel).filter(RomModel.id == run_in.rom).first()
        if run_rom_model and run_rom_model.connector_id:
            target_game = run_rom_model.connector_id

        # We should validate that the ROM and State actually exist before creating a run
        # This matches the implied requirement of a robust system
        try:
            import stable_retro as retro

            if target_game not in retro.data.list_games():
                raise HTTPException(
                    status_code=400, detail=f"ROM '{target_game}' (from {run_in.rom}) not found in retro system"
                )
            if run_in.state and run_in.state not in retro.data.list_states(target_game):
                # Might be a custom state path? For now enforce retro states
                # Check if it looks like a file path
                if not (
                    run_in.state.endswith(".state") or run_in.state == "Start"
                ):  # Start is implicit sometimes
                    raise HTTPException(
                        status_code=400, detail=f"State '{run_in.state}' not found for this ROM"
                    )
        except ImportError:
            pass  # Skip validation if retro not installed locally (e.g. testing)

        # Validate agent (required)
        agent = db.query(AgentModel).filter(AgentModel.id == run_in.agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        if run_in.algorithm.value != agent.algorithm:
            raise HTTPException(
                status_code=400,
                detail=f"Run algorithm ({run_in.algorithm.value}) must match agent algorithm ({agent.algorithm})",
            )
        if run_in.rom != agent.game_id:
            raise HTTPException(
                status_code=400,
                detail=f"ROM '{run_in.rom}' does not match agent's game '{agent.game_id}'",
            )
        # Force observation_type and action_space from agent
        run_in.observation_type = ObservationType(agent.observation_type)
        run_in.action_space = ActionSpace(agent.action_space)
        # Find latest model weights for this agent
        agent_model_path = find_agent_latest_model(agent.id, db)

        # Validate opponent agent (optional, for self-play)
        opponent_model_path = None
        opponent_algorithm = None
        if run_in.opponent_agent_id:
            opponent_agent = db.query(AgentModel).filter(
                AgentModel.id == run_in.opponent_agent_id
            ).first()
            if not opponent_agent:
                raise HTTPException(status_code=404, detail="Opponent agent not found")
            if opponent_agent.observation_type != agent.observation_type:
                raise HTTPException(
                    status_code=400, detail="Opponent observation_type must match training agent"
                )
            if opponent_agent.action_space != agent.action_space:
                raise HTTPException(
                    status_code=400, detail="Opponent action_space must match training agent"
                )
            if agent.observation_type != "image":
                raise HTTPException(
                    status_code=400, detail="Self-play currently requires image observations"
                )
            opponent_model_path = find_agent_latest_model(run_in.opponent_agent_id, db)
            if not opponent_model_path:
                raise HTTPException(
                    status_code=400, detail="Opponent agent has no trained model yet"
                )
            opponent_algorithm = opponent_agent.algorithm

        new_run = RunModel(
            id=str(uuid.uuid4()), status=RunStatus.PENDING.value, **run_in.model_dump()
        )

        db.add(new_run)
        db.commit()
        db.refresh(new_run)

        # Start run in background (manager starts process)
        try:
            config_dict = run_in.model_dump()

            # Use resolved game name for execution
            config_dict["rom"] = target_game

            # Inject global defaults
            global_config = load_config()
            config_dict["device"] = global_config.default_device

            # Load agent's latest weights if available
            if agent_model_path:
                config_dict["resume_from"] = agent_model_path
                config_dict["resumed_steps"] = 0  # Fresh step counter for new run

            # Self-play: inject opponent model path
            if opponent_model_path:
                config_dict["opponent_model_path"] = opponent_model_path
                config_dict["opponent_algorithm"] = opponent_algorithm

            # Ensure ID is passed for logging setup
            config_dict["id"] = new_run.id
            run_manager.start_run(new_run.id, config_dict)
        except Exception as e:
            new_run.status = RunStatus.FAILED.value
            new_run.error = str(e)
            db.commit()
            raise HTTPException(status_code=500, detail=f"Failed to start run: {e}")

        _enrich_run(new_run, db)
        return new_run
    finally:
        db.close()


@router.get("/runs", response_model=list[RunResponse])
def list_runs(status: str = None, agent_id: str = None, skip: int = 0, limit: int = 100):
    """List runs with optional filtering."""
    db = SessionLocal()
    try:
        query = db.query(RunModel)
        if status:
            query = query.filter(RunModel.status == status)
        if agent_id:
            query = query.filter(RunModel.agent_id == agent_id)

        # Sort by created_at desc
        query = query.order_by(RunModel.created_at.desc())

        runs = query.offset(skip).limit(limit).all()
        for run in runs:
            _enrich_run(run, db)
        return runs
    finally:
        db.close()


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run_details(run_id: str):
    db = SessionLocal()
    try:
        run = get_run_or_404(run_id, db)
        _enrich_run(run, db)
        return run
    finally:
        db.close()


@router.patch("/runs/{run_id}", response_model=RunResponse)
def update_run(run_id: str, run_update: RunUpdate):
    """Update run configuration. Only allowed if run is PAUSED or PENDING."""
    db = SessionLocal()
    try:
        run = get_run_or_404(run_id, db)

        # Check status
        if run.status not in [
            RunStatus.PAUSED.value,
            RunStatus.PENDING.value,
            RunStatus.STOPPED.value,
        ]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot update run in '{run.status}' state. Must be PAUSED, PENDING or STOPPED.",
            )

        if run_update.hyperparams:
            # Update hyperparams
            # Since hyperparams is typically a dict or JSON in DB
            # We need to merge or replace. Pydantic models will replace via assignment if schema matches.
            # But wait, run.hyperparams in DB might be a dict (JSON).
            # We will replace it entirely with the new valid schema dump.
            run.hyperparams = run_update.hyperparams.model_dump()

        db.commit()
        db.refresh(run)
        return run
    finally:
        db.close()


@router.delete("/runs/{run_id}", status_code=204)
def delete_run(run_id: str):
    """Delete a run and its data."""
    db = SessionLocal()
    try:
        run = get_run_or_404(run_id, db)

        # If running, stop it first
        if run.status == RunStatus.RUNNING.value:
            run_manager.stop_run(run_id)

        # Delete from DB
        db.delete(run)
        db.commit()

        # Clean up file artifacts
        try:
            run_dir = f"./data/runs/{run_id}"
            if os.path.exists(run_dir):
                shutil.rmtree(run_dir)
        except Exception as e:
            print(f"Error cleaning up run directory: {e}")

        return None
    finally:
        db.close()


@router.post("/runs/{run_id}/resume", response_model=RunResponse)
def resume_run(run_id: str):
    """Resume a stopped/failed run from its latest checkpoint."""
    db = SessionLocal()
    try:
        run = get_run_or_404(run_id, db)

        if run.status not in [RunStatus.STOPPED.value, RunStatus.FAILED.value, RunStatus.COMPLETED.value]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume run in '{run.status}' state. Must be stopped, failed, or completed.",
            )

        config = {
            "rom": run.rom,
            "state": run.state,
            "algorithm": run.algorithm,
            "hyperparams": run.hyperparams if isinstance(run.hyperparams, dict) else {},
            "n_envs": run.n_envs,
            "max_steps": run.max_steps,
            "id": run.id,
        }

        # Resolve ROM to connector for retro
        run_rom_model = db.query(RomModel).filter(RomModel.id == run.rom).first()
        if run_rom_model and run_rom_model.connector_id:
            config["rom"] = run_rom_model.connector_id

        global_config = load_config()
        config["device"] = global_config.default_device

        # Self-play: resolve opponent model fresh (opponent may have trained more)
        if run.opponent_agent_id:
            opp_model = find_agent_latest_model(run.opponent_agent_id, db)
            opp_agent = db.query(AgentModel).filter(
                AgentModel.id == run.opponent_agent_id
            ).first()
            if opp_model and opp_agent:
                config["opponent_model_path"] = opp_model
                config["opponent_algorithm"] = opp_agent.algorithm

        try:
            run_manager.resume_run(run.id, config)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        db.refresh(run)
        return run
    finally:
        db.close()


@router.post("/runs/{run_id}/stop", response_model=RunResponse)
def stop_run(run_id: str):
    db = SessionLocal()
    try:
        run = get_run_or_404(run_id, db)
        run_manager.stop_run(run_id)
        db.refresh(run)
        return run
    finally:
        db.close()


@router.get("/runs/{run_id}/metrics", response_model=list[MetricPoint])
def get_run_metrics(run_id: str, limit: int = 2000, offset: int = 0):
    """
    Get historical metrics for a run.
    Now fetches primarily from DB, falls back to file if empty (legacy support).

    Args:
        limit: Max metrics to return (default 2000, 0 = all)
        offset: Skip first N metrics
    """
    db = SessionLocal()
    try:
        # Check if run exists
        run = db.query(RunModel).filter(RunModel.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        # Try DB first
        query = (
            db.query(RunMetricModel)
            .filter(RunMetricModel.run_id == run_id)
            .order_by(RunMetricModel.step)
        )
        if offset > 0:
            query = query.offset(offset)
        if limit > 0:
            query = query.limit(limit)
        db_metrics = query.all()
        if db_metrics:
            return db_metrics
    finally:
        db.close()

    # Fallback to file for older runs
    metrics_file = os.path.join("data", "runs", run_id, "metrics.jsonl")

    if not os.path.exists(metrics_file):
        return []

    metrics = []
    try:
        with open(metrics_file) as f:
            for line in f:
                if line.strip():
                    try:
                        metrics.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"Error reading metrics for run {run_id}: {e}")
        traceback.print_exc()
        return []

    # Apply pagination to file-based metrics
    if offset > 0:
        metrics = metrics[offset:]
    if limit > 0:
        metrics = metrics[:limit]

    return metrics


@router.get("/runs/{run_id}/recordings")
def list_run_recordings(run_id: str, sort: str = "reward"):
    """List BK2 recording files for a run, enriched with episode rewards when available.

    Args:
        sort: Sort order — "reward" (best first, default) or "time" (newest first)
    """
    db = SessionLocal()
    try:
        get_run_or_404(run_id, db)
    finally:
        db.close()

    recordings_dir = Path(f"./data/runs/{run_id}/recordings")
    if not recordings_dir.exists():
        return []

    # Load episode index if available (maps BK2 sequence → reward/length/step)
    episode_map: dict[int, dict] = {}
    index_file = recordings_dir / "episode_index.json"
    if index_file.exists():
        try:
            with open(index_file) as f:
                index_data = json.load(f)
            for ep in index_data.get("episodes", []):
                seq = ep.get("seq")
                if seq is not None:
                    episode_map[seq] = ep
        except Exception as e:
            print(f"[Recordings] Failed to load episode index for {run_id}: {e}")

    recordings = []
    for f in recordings_dir.glob("*.bk2"):
        stat = f.stat()
        entry: dict = {
            "filename": f.name,
            "size": stat.st_size,
            "created_at": stat.st_mtime,
            "episode_seq": None,
            "reward": None,
            "length": None,
            "step": None,
        }

        # Try to extract sequence number from filename (e.g. GameName-000003.bk2)
        stem = f.stem  # e.g. "SuperMarioWorld-Snes-v0-Start-000003"
        parts = stem.rsplit("-", 1)
        if len(parts) == 2 and parts[1].isdigit():
            seq = int(parts[1])
            entry["episode_seq"] = seq
            if seq in episode_map:
                ep = episode_map[seq]
                entry["reward"] = ep.get("reward")
                entry["length"] = ep.get("length")
                entry["step"] = ep.get("step")

        recordings.append(entry)

    # Sort: by reward (best first, nulls last) or by time (newest first)
    if sort == "reward":
        recordings.sort(
            key=lambda x: (x["reward"] is not None, x["reward"] or 0),
            reverse=True,
        )
    else:
        recordings.sort(key=lambda x: float(x["created_at"]), reverse=True)

    return recordings


@router.get("/runs/{run_id}/recordings/{filename}")
def get_run_recording(run_id: str, filename: str):
    """Download a specific BK2 recording file."""
    db = SessionLocal()
    try:
        get_run_or_404(run_id, db)
    finally:
        db.close()

    # Validate filename to prevent path traversal
    recordings_dir = Path(f"./data/runs/{run_id}/recordings").resolve()
    file_path = (recordings_dir / filename).resolve()

    # Ensure resolved path is within the allowed directory
    if not file_path.is_relative_to(recordings_dir):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not file_path.exists() or file_path.suffix != ".bk2":
        raise HTTPException(status_code=404, detail="Recording not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )
