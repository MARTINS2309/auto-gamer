from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import uuid
import os
import json
import traceback

from ..models.db import get_db, RunModel, RunStatus, RunMetricModel
from ..models.schemas import RunCreate, RunResponse, MetricPoint, RunUpdate
from ..services.run_manager import manager as run_manager
from .config import load_config

router = APIRouter()

def get_run_or_404(run_id: str, db: Session) -> RunModel:
    run = db.query(RunModel).filter(RunModel.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@router.post("/runs", response_model=RunResponse)
async def create_run(run_in: RunCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Create DB entry
    
    # We should validate that the ROM and State actually exist before creating a run
    # This matches the implied requirement of a robust system
    try:
        import stable_retro as retro
        if run_in.rom not in retro.data.list_games():
             raise HTTPException(status_code=400, detail=f"ROM '{run_in.rom}' not found in retro system")
        if run_in.state and run_in.state not in retro.data.list_states(run_in.rom):
             # Might be a custom state path? For now enforce retro states
             # Check if it looks like a file path
             if not (run_in.state.endswith('.state') or run_in.state == "Start"): # Start is implicit sometimes
                raise HTTPException(status_code=400, detail=f"State '{run_in.state}' not found for this ROM")
    except ImportError:
        pass # Skip validation if retro not installed locally (e.g. testing)

    new_run = RunModel(
        id=str(uuid.uuid4()),
        status=RunStatus.PENDING.value,
        **run_in.model_dump()
    )

    db.add(new_run)
    db.commit()
    db.refresh(new_run)
    
    # Start run in background (manager starts process)
    try:
        config_dict = run_in.model_dump()
        
        # Inject global defaults
        global_config = load_config()
        config_dict['device'] = global_config.default_device
        
        # Ensure ID is passed for logging setup
        config_dict['id'] = new_run.id 
        run_manager.start_run(new_run.id, config_dict)
    except Exception as e:
        new_run.status = RunStatus.FAILED.value
        new_run.error = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to start run: {e}")
    
    return new_run

@router.get("/runs", response_model=List[RunResponse])
async def list_runs(
    status: str = None, 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """List runs with optional filtering."""
    query = db.query(RunModel)
    if status:
        query = query.filter(RunModel.status == status)
    
    # Sort by created_at desc
    query = query.order_by(RunModel.created_at.desc())
    
    return query.offset(skip).limit(limit).all()

@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run_details(run_id: str, db: Session = Depends(get_db)):
    return get_run_or_404(run_id, db)

@router.patch("/runs/{run_id}", response_model=RunResponse)
async def update_run(run_id: str, run_update: RunUpdate, db: Session = Depends(get_db)):
    """Update run configuration. Only allowed if run is PAUSED or PENDING."""
    run = get_run_or_404(run_id, db)
    
    # Check status
    if run.status not in [RunStatus.PAUSED.value, RunStatus.PENDING.value, RunStatus.STOPPED.value]:
        raise HTTPException(status_code=400, detail=f"Cannot update run in '{run.status}' state. Must be PAUSED, PENDING or STOPPED.")

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

@router.delete("/runs/{run_id}", status_code=204)
async def delete_run(run_id: str, db: Session = Depends(get_db)):
    """Delete a run and its data."""
    run = get_run_or_404(run_id, db)
    
    # Setup for model cleanup
    import shutil
    import os
    
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

@router.post("/runs/{run_id}/resume", response_model=RunResponse)
async def resume_run(run_id: str, db: Session = Depends(get_db)):
    """Resume a paused run - not fully implemented in runner yet, essentially a restart or no-op."""
    run = get_run_or_404(run_id, db)
    # TODO: Implement resume logic in RunManager
    # For now, just mark it as running if it was paused?
    # SB3 doesn't support easy pause/resume without save/load cycle.
    # return {"message": "Resume not fully implemented yet"}
    
    # Just return the run object to satisfy frontend schema
    return run

@router.post("/runs/{run_id}/stop", response_model=RunResponse)
async def stop_run(run_id: str, db: Session = Depends(get_db)):
    run = get_run_or_404(run_id, db)
    run_manager.stop_run(run_id)
    db.refresh(run)
    return run

@router.get("/runs/{run_id}/metrics", response_model=List[MetricPoint])
async def get_run_metrics(run_id: str, db: Session = Depends(get_db)):
    """
    Get historical metrics for a run.
    Now fetches primarily from DB, falls back to file if empty (legacy support).
    """
    # Check if run exists
    run = db.query(RunModel).filter(RunModel.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Try DB first
    db_metrics = db.query(RunMetricModel).filter(RunMetricModel.run_id == run_id).order_by(RunMetricModel.step).all()
    if db_metrics:
        return db_metrics
        
    # Fallback to file for older runs
    metrics_file = os.path.join("data", "runs", run_id, "metrics.jsonl")
    
    if not os.path.exists(metrics_file):
        return []
        
    metrics = []
    try:
        with open(metrics_file, "r") as f:
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
