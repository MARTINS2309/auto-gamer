from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import uuid

from ..models.db import get_db, RunModel, RunStatus
from ..models.schemas import RunCreate, RunResponse
from ..services.run_manager import manager as run_manager

router = APIRouter()

def get_run_or_404(run_id: str, db: Session) -> RunModel:
    run = db.query(RunModel).filter(RunModel.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@router.post("/runs", response_model=RunResponse)
async def create_run(run_in: RunCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Create DB entry
    new_run = RunModel(
        id=str(uuid.uuid4()),
        status=RunStatus.PENDING.value,
        **run_in.dict() # Dump schema to dict - Pydantic v1 usage, v2 prefers model_dump()
    )
    # Compatibility check (if user has pydantic v2)
    if hasattr(run_in, "model_dump"):
         # Re-create with clean dict
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
        config_dict = run_in.model_dump() if hasattr(run_in, "model_dump") else run_in.dict()
        run_manager.start_run(new_run.id, config_dict)
    except Exception as e:
        new_run.status = RunStatus.FAILED.value
        new_run.error = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to start run: {e}")
    
    return new_run

@router.get("/runs", response_model=List[RunResponse])
async def list_runs(db: Session = Depends(get_db)):
    return db.query(RunModel).order_by(RunModel.created_at.desc()).all()

@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, db: Session = Depends(get_db)):
    return get_run_or_404(run_id, db)

@router.post("/runs/{run_id}/stop")
async def stop_run(run_id: str, db: Session = Depends(get_db)):
    run = get_run_or_404(run_id, db)
    run_manager.stop_run(run_id)
    return {"status": "stopping"}

@router.delete("/runs/{run_id}")
async def delete_run(run_id: str, db: Session = Depends(get_db)):
    run = get_run_or_404(run_id, db)
    
    if run.status == RunStatus.RUNNING.value:
        run_manager.stop_run(run_id)
        
    db.delete(run)
    db.commit()
    return {"status": "deleted"}
