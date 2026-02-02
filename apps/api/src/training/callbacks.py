from stable_baselines3.common.callbacks import BaseCallback
import os
import json
import time
import multiprocessing

import cv2
import base64
import numpy as np

class BroadcastingCallback(BaseCallback):
    def __init__(self, queue: multiprocessing.Queue, check_freq: int = 1000, frame_freq: int = 5000):
        super().__init__(verbose=0)
        self.queue = queue
        self.check_freq = check_freq
        self.frame_freq = frame_freq
        self.last_time = time.time()
        self.last_step = 0

    def _on_step(self) -> bool:
        # Frame Capture
        if self.n_calls % self.frame_freq == 0:
             try:
                # Capture frame from the first env
                # self.training_env is a VecEnv. render() returns array of frames if mode='rgb_array'
                frames = self.training_env.render() # Returns list of arrays or single array depending on VecEnv
                
                if isinstance(frames, list) or (isinstance(frames, np.ndarray) and len(frames.shape) == 4):
                     frame = frames[0] # Take first env
                else:
                     frame = frames

                if frame is not None:
                    # Resize for web (reduce bandwidth)
                    frame = cv2.resize(frame, (320, 240))
                    # Encode to JPEG
                    _, buffer = cv2.imencode('.jpg', frame)
                    b64_str = base64.b64encode(buffer).decode('utf-8')
                    
                    self.queue.put({
                        "type": "frame", 
                        "data": b64_str,
                        "timestamp": time.time()
                    })
             except Exception as e:
                 print(f"Error capturing frame: {e}")

        # Metrics
        if self.n_calls % self.check_freq == 0:
            # Calculate FPS
            current_time = time.time()
            dt = current_time - self.last_time
            d_steps = self.num_timesteps - self.last_step
            fps = d_steps / dt if dt > 0 else 0
            
            self.last_time = current_time
            self.last_step = self.num_timesteps

            # Get infos
            # infos is a list of dicts, one per env
            infos = self.locals.get("infos", [])
            
            # Simple aggregation (average reward if available, etc)
            # This depends on what wrappers are used. 
            # Usually Monitor wrapper puts 'episode' info in 'infos'
            
            avg_reward = 0.0
            ep_len = 0
            ep_count = 0
            
            for info in infos:
                if "episode" in info:
                    avg_reward += info["episode"]["r"]
                    ep_len += info["episode"]["l"]
                    ep_count += 1
            
            # If no episode finished this step, we might track running reward?
            # For now just send what we have.
            
            metric = {
                "type": "metric",
                "step": self.num_timesteps,
                "timestamp": current_time,
                "fps": fps,
                # "loss": ... (hard to get from callback without custom logging)
            }
            
            if ep_count > 0:
                metric["reward"] = avg_reward / ep_count
                metric["avg_reward"] = avg_reward / ep_count # smooth this in frontend or separate tracker
            
            self.queue.put(metric)
            
        return True
