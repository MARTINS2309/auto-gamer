import multiprocessing
import os
import sys
import traceback

import torch
from stable_baselines3 import A2C, DQN, PPO
from stable_baselines3.common.logger import CSVOutputFormat, HumanOutputFormat, Logger
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

from .callbacks import BroadcastingCallback
from .logging_utils import QueueWriter
from .wrappers import make_retro_env


def training_worker(
    run_id: str,
    config: dict,
    queue: multiprocessing.Queue,
    shared_frame_freq: "multiprocessing.sharedctypes.Synchronized[int] | None" = None,
    shared_focused_env: "multiprocessing.sharedctypes.Synchronized[int] | None" = None,
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
        ALGO_MAP = {"PPO": PPO, "A2C": A2C, "DQN": DQN}
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

        model = AlgoClass("CnnPolicy", env, device=device, **model_kwargs)
        model.set_logger(custom_logger)

        # Debug: verify logger was set correctly
        print(f"[{run_id}] After set_logger - model._custom_logger: {model._custom_logger}", flush=True)
        print(f"[{run_id}] model.logger.output_formats: {model.logger.output_formats}", flush=True)
        for i, fmt in enumerate(model.logger.output_formats):
            print(f"[{run_id}]   [{i}] {type(fmt).__name__}", flush=True)

        # Callbacks
        # Configurable frequencies
        # metric_freq: How often to send stats (steps). Default 100 for smoother updates
        metric_freq = max(1, config.get("metric_interval", 100) // n_envs)

        # frame_freq: How often to send frames (steps). Default 60 (~1s at 60fps)
        # Note: If frame streaming is crucial, this should be lower, but affects performance.
        frame_freq = max(1, config.get("frame_capture_interval", 60) // n_envs)

        callback = BroadcastingCallback(
            queue,
            check_freq=metric_freq,
            frame_freq=frame_freq,
            shared_frame_freq=shared_frame_freq,
            shared_focused_env=shared_focused_env,
        )

        # Learn
        model.learn(total_timesteps=int(total_timesteps), callback=callback)

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
