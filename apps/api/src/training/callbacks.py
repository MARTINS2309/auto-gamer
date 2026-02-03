from stable_baselines3.common.callbacks import BaseCallback
import os
import json
import time
import multiprocessing

import cv2
import base64
import numpy as np

class BroadcastingCallback(BaseCallback):
    def __init__(self, queue: multiprocessing.Queue, check_freq: int = 1000, frame_freq: int = 60):
        super().__init__(verbose=0)
        self.queue = queue
        self.check_freq = check_freq
        self.frame_freq = frame_freq
        self.last_time = time.time()
        self.last_step = 0
        
        # Trackers
        self.episode_rewards = []
        self.episode_lengths = []
        self.best_reward = -float('inf')
        
    def _on_step(self) -> bool:
        # Check for episode completions every step
        infos = self.locals.get("infos", [])
        for info in infos:
            if "episode" in info:
                ep_reward = info["episode"]["r"]
                ep_len = info["episode"]["l"]
                self.episode_rewards.append(ep_reward)
                self.episode_lengths.append(ep_len)
                
                if ep_reward > self.best_reward:
                    self.best_reward = ep_reward

        # Frame Capture
        if self.n_calls % self.frame_freq == 0:
             try:
                # Capture frame from the first env
                frames = self.training_env.render()
                
                if isinstance(frames, list) or (isinstance(frames, np.ndarray) and len(frames.shape) == 4):
                     frame = frames[0] # Take first env
                else:
                     frame = frames

                if frame is not None:
                    # Resize for web (reduce bandwidth)
                    frame = cv2.resize(frame, (320, 240))
                    # Encode to JPEG (lower quality for speed)
                    _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                    b64_str = base64.b64encode(buffer).decode('utf-8')
                    
                    self.queue.put({
                        "type": "frame", 
                        "data": b64_str,
                        "timestamp": time.time()
                    })
             except Exception as e:
                 # Don't spam logs
                 pass

        # Metrics Reporting
        if self.n_calls % self.check_freq == 0:
            # Calculate FPS
            current_time = time.time()
            dt = current_time - self.last_time
            d_steps = self.num_timesteps - self.last_step
            fps = d_steps / dt if dt > 0 else 0
            
            self.last_time = current_time
            self.last_step = self.num_timesteps

            # Aggregate collected episodes
            if len(self.episode_rewards) > 0:
                avg_reward = sum(self.episode_rewards) / len(self.episode_rewards)
                last_reward = self.episode_rewards[-1]
                # Keep only last 100 for rolling average next time? 
                # Or clear them? Standard is usually "recent".
                # Let's clear them to show "current performance", or keep rolling via deque?
                # SB3 Logger keeps rolling. We will just report the batch average.
                
                # Rolling 100 avg for separate metric if we wanted
                
            else:
                avg_reward = 0.0 # No episodes finished
                last_reward = 0.0
            
            # We clear the list to report "stats since last update" or "recent stats"?
            # If we don't clear, it becomes "all time average".
            # Let's clear to show progress.
            self.episode_rewards = [] 
            
            metric = {
                "type": "metric",
                "step": self.num_timesteps,
                "timestamp": current_time,
                "fps": fps,
                "reward": last_reward,
                "avg_reward": avg_reward, 
                "best_reward": max(self.best_reward, -9999), 
                # Placeholder for loss until we hook into logger
            }
            
            self.queue.put(metric)
            
        return True
