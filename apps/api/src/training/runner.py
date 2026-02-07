import multiprocessing
import os
import sys
import traceback

import torch
from stable_baselines3 import A2C, DQN, PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.logger import CSVOutputFormat, HumanOutputFormat, Logger
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

from .callbacks import BroadcastingCallback
from .logging_utils import QueueWriter
from .wrappers import make_retro_env


def find_latest_checkpoint(run_id: str) -> tuple[str | None, int]:
    """Find the latest checkpoint for a run. Returns (path, step) or (None, 0)."""
    checkpoint_dir = f"./data/runs/{run_id}/checkpoints"
    final_path = f"./data/runs/{run_id}/final_model.zip"

    # Prefer final_model if it exists (completed run)
    if os.path.exists(final_path):
        # Extract step count from the run's metrics
        import json
        metrics_file = f"./data/runs/{run_id}/metrics.jsonl"
        last_step = 0
        if os.path.exists(metrics_file):
            with open(metrics_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            last_step = max(last_step, data.get("step", 0))
                        except json.JSONDecodeError:
                            continue
        return final_path, last_step

    if not os.path.exists(checkpoint_dir):
        return None, 0

    # Find latest checkpoint by step number
    best_path = None
    best_step = 0
    for fname in os.listdir(checkpoint_dir):
        if fname.endswith(".zip") and fname.startswith("rl_model_"):
            try:
                step = int(fname.replace("rl_model_", "").replace("_steps.zip", ""))
                if step > best_step:
                    best_step = step
                    best_path = os.path.join(checkpoint_dir, fname.replace(".zip", ""))
            except ValueError:
                continue

    return best_path, best_step


def training_worker(
    run_id: str,
    config: dict,
    queue: multiprocessing.Queue,
):
    """
    Worker function to run the training loop in a separate process.
    """
    try:
        # Notify start
        queue.put({"type": "status", "status": "running"})

        # Unpack config
        rom = config.get("rom")
        state = config.get("state")
        algo_name = config.get("algorithm", "PPO")
        hyperparams = config.get("hyperparams", {})
        n_envs = config.get("n_envs", 1)
        total_timesteps = config.get("max_steps", 100_000)

        # Recording setup - only record from first env to avoid disk bloat
        enable_recording = config.get("record_bk2", True)
        record_dir = f"./data/runs/{run_id}/recordings" if enable_recording else None
        if record_dir:
            os.makedirs(record_dir, exist_ok=True)

        # Create env functions - first env gets recording enabled
        def make_env_with_record():
            return make_retro_env(
                rom,
                state,
                observation_type=config.get("observation_type", "image"),
                action_space=config.get("action_space", "filtered"),
                record_dir=record_dir,
            )

        def make_env_no_record():
            return make_retro_env(
                rom,
                state,
                observation_type=config.get("observation_type", "image"),
                action_space=config.get("action_space", "filtered"),
                record_dir=None,
            )

        # Create VecEnv
        # Note: SubprocVecEnv can fail when running in certain contexts (e.g., uvicorn)
        # due to "daemonic processes are not allowed to have children" restriction.
        # Fall back to DummyVecEnv which runs in a single process.
        env: SubprocVecEnv | DummyVecEnv
        if n_envs > 1:
            # First env records, rest don't
            env_fns = [make_env_with_record] + [make_env_no_record] * (n_envs - 1)
            try:
                env = SubprocVecEnv(env_fns)
            except AssertionError as e:
                if "daemonic" in str(e):
                    print(
                        f"[{run_id}] SubprocVecEnv failed (daemonic restriction), using DummyVecEnv"
                    )
                    env = DummyVecEnv(env_fns)
                else:
                    raise
        else:
            env = DummyVecEnv([make_env_with_record])

        # Select Algorithm
        ALGO_MAP: dict[str, type[PPO] | type[A2C] | type[DQN]] = {"PPO": PPO, "A2C": A2C, "DQN": DQN}
        AlgoClass = ALGO_MAP.get(algo_name, PPO)

        # Init Model
        # Map hyperparams to kwargs.
        # Note: hyperparams dict structure must match SB3 expected args.
        all_kwargs = {
            "verbose": 1,
            "tensorboard_log": f"./data/runs/{run_id}/logs",
            "learning_rate": hyperparams.get("learning_rate", 3e-4),
            "n_steps": hyperparams.get("n_steps", 2048),
            "batch_size": hyperparams.get("batch_size", 64),
            "n_epochs": hyperparams.get("n_epochs", 10),
            "gamma": hyperparams.get("gamma", 0.99),
            "gae_lambda": hyperparams.get("gae_lambda", 0.95),
            "clip_range": hyperparams.get("clip_range", 0.2),
            "ent_coef": hyperparams.get("ent_coef", 0.0),
            "vf_coef": hyperparams.get("vf_coef", 0.5),
            "max_grad_norm": hyperparams.get("max_grad_norm", 0.5),
            "buffer_size": hyperparams.get("buffer_size", 1_000_000),  # DQN specific
            "learning_starts": hyperparams.get("learning_starts", 50000),  # DQN specific
            "train_freq": hyperparams.get("train_freq", 4),  # DQN specific
            "gradient_steps": hyperparams.get("gradient_steps", 1),  # DQN specific
            "target_update_interval": hyperparams.get(
                "target_update_interval", 10000
            ),  # DQN specific
            "exploration_fraction": hyperparams.get("exploration_fraction", 0.1),  # DQN specific
            "exploration_initial_eps": hyperparams.get(
                "exploration_initial_eps", 1.0
            ),  # DQN specific
            "exploration_final_eps": hyperparams.get("exploration_final_eps", 0.05),  # DQN specific
        }

        # Filter kwargs based on AlgoClass
        import inspect

        sig = inspect.signature(AlgoClass)
        model_kwargs = {k: v for k, v in all_kwargs.items() if k in sig.parameters}

        # Allow extra kwargs that might be in **kwargs of init if needed, but safer to be explicit
        # PPO/A2C/DQN usually have explicit args.

        # Device detection/selection
        requested_device = config.get("device", "auto")
        if requested_device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        else:
            device = requested_device

        print(f"[{run_id}] Using device: {device}")

        # Configure Custom Logger
        log_dir = f"./data/runs/{run_id}/logs"
        os.makedirs(log_dir, exist_ok=True)

        # Define output formats: Stdout, CSV, and our QueueWriter for the frontend
        output_formats = [
            HumanOutputFormat(sys.stdout),
            CSVOutputFormat(os.path.join(log_dir, "progress.csv")),
            QueueWriter(queue),
        ]

        custom_logger = Logger(log_dir, output_formats)

        # Debug: verify output_formats
        print(f"[{run_id}] Logger output_formats: {custom_logger.output_formats}", flush=True)
        for i, fmt in enumerate(custom_logger.output_formats):
            print(f"[{run_id}]   [{i}] {type(fmt).__name__}: {fmt}", flush=True)

        # Check for resume: load from checkpoint if available
        resume_path = config.get("resume_from")
        resumed_steps = 0
        if resume_path:
            print(f"[{run_id}] Resuming from checkpoint: {resume_path}")
            model = AlgoClass.load(resume_path, env=env, device=device)
            resumed_steps = config.get("resumed_steps", 0)
            print(f"[{run_id}] Loaded checkpoint at step {resumed_steps}")
        else:
            model = AlgoClass("CnnPolicy", env, device=device, **model_kwargs)

        model.set_logger(custom_logger)

        # Callbacks
        metric_freq = max(1, config.get("metric_interval", 100) // n_envs)
        frame_freq = max(1, config.get("frame_capture_interval", 60) // n_envs)

        checkpoint_dir = f"./data/runs/{run_id}/checkpoints"
        os.makedirs(checkpoint_dir, exist_ok=True)
        checkpoint_freq = max(1, config.get("checkpoint_interval", 50_000) // n_envs)

        broadcast_cb = BroadcastingCallback(
            queue,
            check_freq=metric_freq,
            frame_freq=frame_freq,
        )
        checkpoint_cb = CheckpointCallback(
            save_freq=checkpoint_freq,
            save_path=checkpoint_dir,
            name_prefix="rl_model",
            verbose=0,
        )

        # Learn — remaining steps if resuming
        remaining_steps = int(total_timesteps) - resumed_steps
        if remaining_steps <= 0:
            print(f"[{run_id}] Already completed all {total_timesteps} steps")
            queue.put({"type": "status", "status": "completed"})
            return
        model.learn(total_timesteps=remaining_steps, callback=[broadcast_cb, checkpoint_cb])

        # Save final model
        save_path = f"./data/runs/{run_id}/final_model"
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        model.save(save_path)

        queue.put({"type": "status", "status": "completed"})

    except Exception as e:
        traceback.print_exc()
        queue.put({"type": "error", "error": str(e)})
        queue.put({"type": "status", "status": "failed"})
    finally:
        try:
            if "env" in locals():
                env.close()
        except Exception:
            pass
