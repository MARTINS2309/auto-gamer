import asyncio
import json
import multiprocessing
import os
import queue  # Import standard queue for Empty exception
import signal
import threading
from datetime import datetime

from ..models.db import RunMetricModel, RunModel, RunStatus, SessionLocal
from ..training.runner import training_worker
from .ws_manager import manager as ws_manager


class RunManager:
    def __init__(self):
        self.active_runs: dict[str, tuple[multiprocessing.Process, multiprocessing.Queue]] = {}
        self.shared_values: dict[str, dict] = {}  # run_id -> {"frame_freq": Value}
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

            # Create Queue and shared values
            q: multiprocessing.Queue[dict] = multiprocessing.Queue()
            default_frame_freq = max(1, config.get("frame_capture_interval", 30))
            shared_frame_freq = multiprocessing.Value("i", default_frame_freq)
            shared_focused_env = multiprocessing.Value("i", -1)
            self.shared_values[run_id] = {
                "frame_freq": shared_frame_freq,
                "focused_env": shared_focused_env,
            }

            # Start Process
            process = multiprocessing.Process(
                target=training_worker,
                args=(run_id, config, q, shared_frame_freq, shared_focused_env),
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
                self.shared_values.pop(run_id, None)

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

                    # Binary frame tuples: ("frame_bytes", header + jpeg_bytes)
                    if isinstance(msg, tuple) and msg[0] == "frame_bytes":
                        self._emit_binary(run_id, msg[1])
                        continue

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

                        self._emit_event(run_id, msg)

                        if status in ["completed", "failed", "stopped"]:
                            break
                    elif msg_type == "episode":
                        # Forward episode completion events to WebSocket
                        # Update best reward tracker
                        ep_best = msg.get("best_reward", -float("inf"))
                        if ep_best > best_reward:
                            best_reward = ep_best
                        self._emit_event(run_id, msg)

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

    def set_frame_freq(self, run_id: str, freq: int):
        """Update frame capture frequency for a running training process."""
        freq = max(1, min(freq, 1000))
        with self.lock:
            vals = self.shared_values.get(run_id)
            if vals and "frame_freq" in vals:
                vals["frame_freq"].value = freq
                print(f"[RunManager] Set frame_freq={freq} for run {run_id}")

    def get_frame_freq(self, run_id: str) -> int | None:
        with self.lock:
            vals = self.shared_values.get(run_id)
            if vals and "frame_freq" in vals:
                return int(vals["frame_freq"].value)
        return None

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

    def set_focused_env(self, run_id: str, env_index: int):
        """Update which env is focused for a running training process."""
        with self.lock:
            vals = self.shared_values.get(run_id)
            if vals and "focused_env" in vals:
                vals["focused_env"].value = env_index
                print(f"[RunManager] Set focused_env={env_index} for run {run_id}")

    def _emit_event(self, run_id: str, msg: dict):
        if self.loop and ws_manager:
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(run_id, msg), self.loop)
        else:
            print(
                f"[Monitor] Cannot emit event: loop={self.loop is not None}, ws_manager={ws_manager is not None}"
            )

    def _emit_binary(self, run_id: str, data: bytes):
        if self.loop and ws_manager:
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast_bytes(run_id, data), self.loop)


manager = RunManager()
