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

from ..models.db import SessionLocal, RunModel, RunStatus, RunMetricModel
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
                daemon=False 
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
        """Background thread to monitor queue from subprocess."""
        print(f"[Monitor] Starting monitor thread for run {run_id}")
        db = SessionLocal()

        # Setup metrics file
        run_dir = f"./data/runs/{run_id}"
        os.makedirs(run_dir, exist_ok=True)
        metrics_file = os.path.join(run_dir, "metrics.jsonl")
        print(f"[Monitor] Metrics file: {metrics_file}")
        
        best_reward = -float('inf')

        try:
            while True:
                # Check if process is alive
                with self.lock:
                    if run_id in self.active_runs:
                        proc, _ = self.active_runs[run_id]
                        if not proc.is_alive() and q.empty():
                            # Clean exit double check
                            break
                    else:
                        break # Removed from active
                
                try:
                    # Blocking get with timeout
                    # Note: multiprocessing.Queue.get raises queue.Empty
                    msg = q.get(timeout=1.0)

                    msg_type = msg.get("type")
                    print(f"[Monitor] Received message type={msg_type} for run {run_id}")

                    if msg_type == "metric":
                         print(f"[Monitor] Broadcasting metric: step={msg.get('step')}, fps={msg.get('fps')}")
                         
                         # Update local tracker
                         rec_best = msg.get("best_reward", -float('inf'))
                         if rec_best > best_reward:
                             best_reward = rec_best
                         
                         self._emit_event(run_id, msg)

                         # Save to JSONL
                         try:
                             with open(metrics_file, "a") as f:
                                 f.write(json.dumps(msg) + "\n")
                         except Exception as e:
                             print(f"[Monitor] Failed to save metric: {e}")
                    
                    elif msg_type == "sb3_metric":
                        data = msg.get("data", {})
                        
                        normalized = {
                            "type": "metric",
                            "step": msg.get("step"),
                            "timestamp": msg.get("timestamp"),
                            "fps": data.get("time/fps", 0),
                            "avg_reward": data.get("rollout/ep_rew_mean", 0),
                            "reward": 0, # Placeholder
                            "best_reward": best_reward,
                            "details": data
                        }
                        
                        print(f"[Monitor] SB3 Metric: step={normalized['step']}")
                        self._emit_event(run_id, normalized)
                        
                        # Save to File (for legacy backup/easy debug)
                        try:
                            # print(f"[DEBUG] Writing metric to {metrics_file}")
                            with open(metrics_file, "a") as f:
                                f.write(json.dumps(normalized) + "\n")
                        except Exception as e:
                            print(f"[Monitor] Failed to save metric to file: {e}")

                        # Save to DB
                        try:
                            db_metric = RunMetricModel(
                                run_id=run_id,
                                step=normalized['step'],
                                timestamp=normalized['timestamp'],
                                reward=normalized['reward'],
                                avg_reward=normalized['avg_reward'],
                                best_reward=normalized['best_reward'],
                                fps=normalized['fps'],
                                loss=normalized['loss'],
                                epsilon=normalized['epsilon'],
                                details=normalized['details']
                            )
                            db.add(db_metric)
                            db.commit()
                        except Exception as e:
                             print(f"[Monitor] Failed to save metric to DB: {e}")
                             db.rollback()
                         
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

    def delete_run_data(self, run_id: str):
        """Delete file artifacts for a run."""
        import shutil
        run_dir = f"./data/runs/{run_id}"
        if os.path.exists(run_dir):
            try:
                shutil.rmtree(run_dir)
            except Exception as e:
                print(f"Error deleting run data {run_id}: {e}")

    def _emit_event(self, run_id: str, msg: dict):
        if self.loop and ws_manager:
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(run_id, msg), self.loop)
        else:
            print(f"[Monitor] Cannot emit event: loop={self.loop is not None}, ws_manager={ws_manager is not None}")

manager = RunManager()
