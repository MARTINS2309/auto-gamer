import multiprocessing
import threading
import json
import time
import os
import queue # Import standard queue for Empty exception
import asyncio
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.db import SessionLocal, RunModel, RunStatus
from ..models.schemas import MetricPoint
from .ws_manager import manager as ws_manager
from ..training.runner import training_worker

class RunManager:
    def __init__(self):
        self.active_runs: Dict[str, Tuple[multiprocessing.Process, multiprocessing.Queue]] = {}
        self.lock = threading.Lock()
        self.loop = None
        # Ensure 'spawn' is used for stability
        try:
            multiprocessing.set_start_method('spawn')
        except RuntimeError:
            pass # Already set

    def set_loop(self, loop):
        self.loop = loop

    def start_run(self, run_id: str, config: dict):
        with self.lock:
            if run_id in self.active_runs:
                raise Exception("Run already active")

            # Update DB status
            db = SessionLocal()
            try:
                run = db.query(RunModel).filter(RunModel.id == run_id).first()
                if run:
                    run.status = RunStatus.RUNNING.value
                    run.started_at = datetime.utcnow()
                    db.commit()
            finally:
                db.close()

            # Create Queue
            q = multiprocessing.Queue()

            # Start Process
            process = multiprocessing.Process(
                target=training_worker,
                args=(run_id, config, q),
                daemon=True 
            )
            process.start()

            self.active_runs[run_id] = (process, q)

        # Start Monitoring Thread (outside lock to avoid holding it long, though thread start is fast)
        thread = threading.Thread(
            target=self._monitor_run,
            args=(run_id, q, process),
            daemon=True
        )
        thread.start()

    def stop_run(self, run_id: str):
        with self.lock:
            if run_id in self.active_runs:
                process, _ = self.active_runs[run_id]
                if process.is_alive():
                    process.terminate() 
                    process.join(timeout=5)
                    if process.is_alive():
                        process.kill()
                
                if run_id in self.active_runs:
                    del self.active_runs[run_id]

        # DB update
        db = SessionLocal()
        try:
            run = db.query(RunModel).filter(RunModel.id == run_id).first()
            if run:
                run.status = RunStatus.STOPPED.value
                run.completed_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def _monitor_run(self, run_id: str, q: multiprocessing.Queue, process: multiprocessing.Process):
        db = SessionLocal()
        try:
            while True:
                # Check if process died unexpectedly
                if not process.is_alive() and q.empty():
                    break
                
                try:
                    # Blocking get with timeout
                    # Note: multiprocessing.Queue.get raises queue.Empty
                    msg = q.get(timeout=1.0) 
                    
                    msg_type = msg.get("type")
                    
                    if msg_type == "metric":
                         self._emit_event(run_id, msg)
                         
                         # TODO: Save to JSONL here if needed
                         
                    elif msg_type == "status":
                        status = msg.get("status")
                        db_run = db.query(RunModel).filter(RunModel.id == run_id).first()
                        if db_run:
                            db_run.status = status
                            if status in ["completed", "failed"]:
                                db_run.completed_at = datetime.utcnow()
                            if "error" in msg:
                                db_run.error = msg["error"]
                            db.commit()
                        
                        self._emit_event(run_id, msg)
                        
                        if status in ["completed", "failed", "stopped"]:
                            break
                    elif msg_type == "error":
                         # Status update handles error field, but maybe emit specific error event?
                         self._emit_event(run_id, msg)
                            
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Monitor error for {run_id}: {e}")
                    break
                    
        finally:
            db.close()
            pass

    def _emit_event(self, run_id: str, msg: dict):
        if self.loop and ws_manager:
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(run_id, msg), self.loop)

manager = RunManager()
