import asyncio
import json
import multiprocessing
import os
import queue  # Import standard queue for Empty exception
import signal
import threading
from datetime import datetime

from ..models.db import AgentModel, RunMetricModel, RunModel, RunStatus, SessionLocal
from ..training.runner import find_latest_checkpoint, training_worker
from .ws_manager import manager as ws_manager


class RunManager:
    def __init__(self):
        self.active_runs: dict[str, tuple[multiprocessing.Process, multiprocessing.Queue]] = {}
        self.lock = threading.Lock()
        self.loop = None
        # Ensure 'spawn' is used for stability
        try:
            multiprocessing.set_start_method("spawn")
        except RuntimeError:
            pass  # Already set

    def set_loop(self, loop):
        self.loop = loop

    def start_run(self, run_id: str, config: dict):
        with self.lock:
            if run_id in self.active_runs:
                raise Exception("Run already active")

            # Create Queue
            q: multiprocessing.Queue[dict] = multiprocessing.Queue()

            # Start Process
            process = multiprocessing.Process(
                target=training_worker,
                args=(run_id, config, q),
                daemon=False,
            )
            process.start()

            self.active_runs[run_id] = (process, q)

            # Update DB status + store PID for orphan cleanup
            db = SessionLocal()
            try:
                run = db.query(RunModel).filter(RunModel.id == run_id).first()
                if run:
                    run.status = RunStatus.RUNNING.value
                    run.started_at = datetime.utcnow()
                    run.pid = process.pid
                    db.commit()
            finally:
                db.close()

        # Start Monitoring Thread (outside lock to avoid holding it long, though thread start is fast)
        thread = threading.Thread(target=self._monitor_run, args=(run_id, q, process), daemon=True)
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

    def resume_run(self, run_id: str, config: dict) -> int:
        """Resume a stopped/failed run from its latest checkpoint.
        Returns the step count being resumed from, or raises if no checkpoint found.
        """
        checkpoint_path, resumed_steps = find_latest_checkpoint(run_id)
        if not checkpoint_path:
            raise Exception(f"No checkpoint found for run {run_id}")

        config["resume_from"] = checkpoint_path
        config["resumed_steps"] = resumed_steps

        self.start_run(run_id, config)
        return resumed_steps

    def _monitor_run(self, run_id: str, q: multiprocessing.Queue, process: multiprocessing.Process):
        """Background thread to monitor queue from subprocess."""
        print(f"[Monitor] Starting monitor thread for run {run_id}")
        db = SessionLocal()

        # Setup metrics file
        run_dir = f"./data/runs/{run_id}"
        os.makedirs(run_dir, exist_ok=True)
        metrics_file = os.path.join(run_dir, "metrics.jsonl")
        print(f"[Monitor] Metrics file: {metrics_file}")

        best_reward = -float("inf")

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
                        break  # Removed from active

                try:
                    # Blocking get with timeout
                    # Note: multiprocessing.Queue.get raises queue.Empty
                    msg = q.get(timeout=1.0)

                    # Binary frame tuples: ("frame_bytes", header + rgb_bytes)
                    # Drain queue to skip stale frames — only send the latest
                    if isinstance(msg, tuple) and msg[0] == "frame_bytes":
                        latest_frame = msg[1]
                        skipped = 0
                        while True:
                            try:
                                peek = q.get_nowait()
                                if isinstance(peek, tuple) and peek[0] == "frame_bytes":
                                    latest_frame = peek[1]
                                    skipped += 1
                                else:
                                    # Not a frame — put it back and stop draining
                                    # We can't put back into a mp.Queue, so process it below
                                    msg = peek
                                    break
                            except queue.Empty:
                                msg = None
                                break
                        self._emit_binary(run_id, latest_frame)
                        if msg is None:
                            continue
                        # Fall through to process the non-frame msg we pulled out

                    msg_type = msg.get("type")
                    print(f"[Monitor] Received message type={msg_type} for run {run_id}")

                    if msg_type == "metric":
                        print(
                            f"[Monitor] Broadcasting metric: step={msg.get('step')}, fps={msg.get('fps')}"
                        )

                        # Update local tracker
                        rec_best = msg.get("best_reward", -float("inf"))
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
                        raw_data = msg.get("data", {})

                        # Data should already be serialized by QueueWriter, but double-check
                        def to_python(v):
                            if hasattr(v, "item"):  # numpy scalar
                                return v.item()
                            return v

                        data = {k: to_python(v) for k, v in raw_data.items()}

                        # Debug: log received keys by category
                        train_keys = [k for k in data.keys() if k.startswith("train/")]
                        rollout_keys = [k for k in data.keys() if k.startswith("rollout/")]
                        time_keys = [k for k in data.keys() if k.startswith("time/")]
                        print(f"[Monitor] SB3 Metric received: step={msg.get('step')}, total_keys={len(data)}")
                        print(f"  train_keys ({len(train_keys)}): {train_keys}")
                        print(f"  rollout_keys ({len(rollout_keys)}): {rollout_keys}")
                        print(f"  time_keys ({len(time_keys)}): {time_keys}")

                        # Extract loss metrics from SB3 data
                        # PPO/A2C use train/loss or train/value_loss
                        # DQN uses train/loss
                        loss = data.get("train/loss") or data.get("train/value_loss")
                        # DQN epsilon exploration
                        epsilon = data.get("rollout/exploration_rate")

                        normalized = {
                            "type": "metric",
                            "step": msg.get("step"),
                            "timestamp": msg.get("timestamp"),
                            "fps": data.get("time/fps", 0),
                            "avg_reward": data.get("rollout/ep_rew_mean", 0),
                            "reward": data.get("rollout/ep_rew_mean", 0),  # Use mean as current
                            "best_reward": best_reward,
                            "loss": loss,
                            "epsilon": epsilon,
                            "details": data,
                        }

                        print(f"[Monitor] Normalized metric: fps={normalized['fps']}, loss={normalized['loss']}, details_keys={len(data)}")
                        self._emit_event(run_id, normalized)

                        # Save to File (for legacy backup/easy debug)
                        try:
                            with open(metrics_file, "a") as f:
                                f.write(json.dumps(normalized) + "\n")
                        except Exception as e:
                            print(f"[Monitor] Failed to save metric to file: {e}")

                        # Save to DB
                        try:
                            db_metric = RunMetricModel(
                                run_id=run_id,
                                step=normalized["step"],
                                timestamp=normalized["timestamp"],
                                reward=normalized["reward"],
                                avg_reward=normalized["avg_reward"],
                                best_reward=normalized["best_reward"],
                                fps=normalized["fps"],
                                loss=normalized.get("loss"),
                                epsilon=normalized.get("epsilon"),
                                details=normalized["details"],
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

                            # Update agent stats on terminal status
                            if status in ["completed", "stopped"] and db_run.agent_id:
                                self._update_agent_stats(db, db_run.agent_id, best_reward)

                        self._emit_event(run_id, msg)

                        if status in ["completed", "failed", "stopped"]:
                            break
                    elif msg_type == "episode":
                        # Forward episode completion events to WebSocket
                        ep_best = msg.get("best_reward", -float("inf"))
                        if ep_best > best_reward:
                            best_reward = ep_best
                        self._emit_event(run_id, msg)

                        # Persist to JSONL so episode count survives page refresh
                        try:
                            with open(metrics_file, "a") as f:
                                f.write(json.dumps(msg) + "\n")
                        except Exception:
                            pass

                    elif msg_type == "phase":
                        # Forward phase transitions to WebSocket clients
                        self._emit_event(run_id, msg)

                    elif msg_type == "recording_index":
                        # Persist episode-to-BK2 mapping
                        index_file = os.path.join(run_dir, "recordings", "episode_index.json")
                        try:
                            os.makedirs(os.path.dirname(index_file), exist_ok=True)
                            episodes = msg.get("episodes", [])
                            is_complete = msg.get("complete", False)

                            if is_complete:
                                with open(index_file, "w") as f:
                                    json.dump({"episodes": episodes, "complete": True}, f)
                            else:
                                existing: dict = {"episodes": []}
                                if os.path.exists(index_file):
                                    with open(index_file) as f:
                                        existing = json.load(f)
                                existing["episodes"].extend(episodes)
                                with open(index_file, "w") as f:
                                    json.dump(existing, f)
                        except Exception as e:
                            print(f"[Monitor] Failed to save recording index: {e}")

                    elif msg_type == "error":
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


    def cleanup_all(self):
        """Terminate all active training processes (called on shutdown)."""
        with self.lock:
            run_ids = list(self.active_runs.keys())

        for run_id in run_ids:
            print(f"[RunManager] Shutting down run {run_id}")
            self.stop_run(run_id)

        print(f"[RunManager] Shutdown complete, stopped {len(run_ids)} run(s)")

    def cleanup_orphans(self):
        """Find runs marked 'running' in DB with no live process, kill orphans and mark stopped."""
        db = SessionLocal()
        try:
            stale_runs = (
                db.query(RunModel)
                .filter(RunModel.status == RunStatus.RUNNING.value)
                .all()
            )

            for run in stale_runs:
                pid = int(run.pid) if run.pid else None
                alive = False

                if pid:
                    try:
                        os.kill(pid, 0)  # Check if process exists
                        alive = True
                    except OSError:
                        pass

                if alive and pid:
                    # Process exists but we don't manage it -- kill it
                    print(f"[RunManager] Killing orphaned process PID={pid} for run {run.id}")
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except OSError:
                        pass

                # Mark as stopped regardless
                run.status = RunStatus.STOPPED.value
                run.completed_at = datetime.utcnow()
                run.error = "Orphaned process cleaned up on server restart"
                print(f"[RunManager] Marked orphaned run {run.id} as stopped (PID={pid})")

            if stale_runs:
                db.commit()
                print(f"[RunManager] Cleaned up {len(stale_runs)} orphaned run(s)")
            else:
                print("[RunManager] No orphaned runs found")
        finally:
            db.close()

    def _emit_event(self, run_id: str, msg: dict):
        if self.loop and ws_manager:
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(run_id, msg), self.loop)
        else:
            print(
                f"[Monitor] Cannot emit event: loop={self.loop is not None}, ws_manager={ws_manager is not None}"
            )

    def _update_agent_stats(self, db, agent_id: str, run_best_reward: float):
        """Update an agent's aggregate stats after a run completes."""
        try:
            agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
            if not agent:
                return

            # Recount from DB for accuracy
            agent.total_runs = (
                db.query(RunModel)
                .filter(
                    RunModel.agent_id == agent_id,
                    RunModel.status.in_(["completed", "stopped"]),
                )
                .count()
            )

            # Sum the max step per run for cumulative total
            from sqlalchemy import func
            subq = (
                db.query(
                    RunMetricModel.run_id,
                    func.max(RunMetricModel.step).label("max_step"),
                )
                .join(RunModel, RunMetricModel.run_id == RunModel.id)
                .filter(
                    RunModel.agent_id == agent_id,
                    RunModel.status.in_(["completed", "stopped"]),
                )
                .group_by(RunMetricModel.run_id)
                .subquery()
            )
            cumulative_steps = db.query(func.sum(subq.c.max_step)).scalar()
            agent.total_steps = cumulative_steps or 0

            # Update best reward
            if run_best_reward > (agent.best_reward or float("-inf")):
                agent.best_reward = run_best_reward

            db.commit()
        except Exception as e:
            print(f"[RunManager] Failed to update agent stats for {agent_id}: {e}")
            db.rollback()

    def _emit_binary(self, run_id: str, data: bytes):
        if self.loop and ws_manager:
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast_bytes(run_id, data), self.loop)


manager = RunManager()
