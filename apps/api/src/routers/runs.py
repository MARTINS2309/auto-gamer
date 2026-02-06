import json
import os
import shutil
import traceback
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..models.db import RomModel, RunMetricModel, RunModel, RunStatus, SessionLocal
from ..models.schemas import MetricPoint, RunCreate, RunResponse, RunUpdate
from ..services.run_manager import manager as run_manager
from .config import load_config

router = APIRouter()


def get_run_or_404(run_id: str, db: Session) -> RunModel:
    run = db.query(RunModel).filter(RunModel.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


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

            # Ensure ID is passed for logging setup
            config_dict["id"] = new_run.id
            run_manager.start_run(new_run.id, config_dict)
        except Exception as e:
            new_run.status = RunStatus.FAILED.value
            new_run.error = str(e)
            db.commit()
            raise HTTPException(status_code=500, detail=f"Failed to start run: {e}")

        return new_run
    finally:
        db.close()


@router.get("/runs", response_model=list[RunResponse])
def list_runs(status: str = None, skip: int = 0, limit: int = 100):
    """List runs with optional filtering."""
    db = SessionLocal()
    try:
        query = db.query(RunModel)
        if status:
            query = query.filter(RunModel.status == status)

        # Sort by created_at desc
        query = query.order_by(RunModel.created_at.desc())

        return query.offset(skip).limit(limit).all()
    finally:
        db.close()


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run_details(run_id: str):
    db = SessionLocal()
    try:
        return get_run_or_404(run_id, db)
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
    """Resume a paused run - not fully implemented in runner yet, essentially a restart or no-op."""
    db = SessionLocal()
    try:
        run = get_run_or_404(run_id, db)
        # TODO: Implement resume logic in RunManager
        # For now, just mark it as running if it was paused?
        # SB3 doesn't support easy pause/resume without save/load cycle.
        # return {"message": "Resume not fully implemented yet"}

        # Just return the run object to satisfy frontend schema
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
def get_run_metrics(run_id: str):
    """
    Get historical metrics for a run.
    Now fetches primarily from DB, falls back to file if empty (legacy support).
    """
    db = SessionLocal()
    try:
        # Check if run exists
        run = db.query(RunModel).filter(RunModel.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        # Try DB first
        db_metrics = (
            db.query(RunMetricModel)
            .filter(RunMetricModel.run_id == run_id)
            .order_by(RunMetricModel.step)
            .all()
        )
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

    return metrics


@router.get("/runs/{run_id}/recordings")
def list_run_recordings(run_id: str):
    """List BK2 recording files for a run."""
    db = SessionLocal()
    try:
        get_run_or_404(run_id, db)
    finally:
        db.close()

    recordings_dir = Path(f"./data/runs/{run_id}/recordings")
    if not recordings_dir.exists():
        return []

    recordings = []
    for f in recordings_dir.glob("*.bk2"):
        stat = f.stat()
        recordings.append({
            "filename": f.name,
            "size": stat.st_size,
            "created_at": stat.st_mtime,
        })

    # Sort by creation time, newest first
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
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = Path(f"./data/runs/{run_id}/recordings/{filename}")
    if not file_path.exists() or not file_path.suffix == ".bk2":
        raise HTTPException(status_code=404, detail="Recording not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )
