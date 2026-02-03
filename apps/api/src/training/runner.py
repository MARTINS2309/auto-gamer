import gymnasium as gym
import retro
from stable_baselines3 import PPO, A2C, DQN
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.utils import set_random_seed
import multiprocessing
import os
import traceback
import torch

from .wrappers import make_retro_env
from .callbacks import BroadcastingCallback

def training_worker(run_id: str, config: dict, queue: multiprocessing.Queue):
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
        
        # Create env function
        def make_env():
            return make_retro_env(rom, state, 
                                  observation_type=config.get("observation_type", "image"),
                                  action_space=config.get("action_space", "filtered"))
        
        # Create VecEnv
        # Note: SubprocVecEnv can fail when running in certain contexts (e.g., uvicorn)
        # due to "daemonic processes are not allowed to have children" restriction.
        # Fall back to DummyVecEnv which runs in a single process.
        if n_envs > 1:
            try:
                env = SubprocVecEnv([make_env for _ in range(n_envs)])
            except AssertionError as e:
                if "daemonic" in str(e):
                    print(f"[{run_id}] SubprocVecEnv failed (daemonic restriction), using DummyVecEnv")
                    env = DummyVecEnv([make_env for _ in range(n_envs)])
                else:
                    raise
        else:
            env = DummyVecEnv([make_env])
            
        # Select Algorithm
        ALGO_MAP = {
            "PPO": PPO,
            "A2C": A2C,
            "DQN": DQN
        }
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
            "buffer_size": hyperparams.get("buffer_size", 1_000_000), # DQN specific
            "learning_starts": hyperparams.get("learning_starts", 50000), # DQN specific
            "train_freq": hyperparams.get("train_freq", 4), # DQN specific
            "gradient_steps": hyperparams.get("gradient_steps", 1), # DQN specific
            "target_update_interval": hyperparams.get("target_update_interval", 10000), # DQN specific
            "exploration_fraction": hyperparams.get("exploration_fraction", 0.1), # DQN specific
            "exploration_initial_eps": hyperparams.get("exploration_initial_eps", 1.0), # DQN specific
            "exploration_final_eps": hyperparams.get("exploration_final_eps", 0.05), # DQN specific
        }
        
        # Filter kwargs based on AlgoClass
        import inspect
        sig = inspect.signature(AlgoClass.__init__)
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
        
        model = AlgoClass("CnnPolicy", env, device=device, **model_kwargs)
        
        # Callbacks
        # Configurable frequencies
        # metric_freq: How often to send stats (steps). Default 1000 (~16s at 60fps)
        metric_freq = max(1, 1000 // n_envs)
        
        # frame_freq: How often to send frames (steps). Default 60 (~1s at 60fps)
        # Note: If frame streaming is crucial, this should be lower, but affects performance.
        frame_freq = max(1, config.get("frame_capture_interval", 60) // n_envs)
        
        callback = BroadcastingCallback(queue, check_freq=metric_freq, frame_freq=frame_freq)
        
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
            if 'env' in locals():
                env.close()
        except:
            pass
