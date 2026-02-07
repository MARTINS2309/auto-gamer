import multiprocessing
import time

import numpy as np
from stable_baselines3.common.callbacks import BaseCallback


class BroadcastingCallback(BaseCallback):
    def __init__(
        self,
        queue: multiprocessing.Queue,
        check_freq: int = 1000,
        frame_freq: int = 30,
    ):
        super().__init__(verbose=0)
        self.queue = queue
        self.check_freq = check_freq
        self.frame_freq = frame_freq
        self.last_time = time.time()
        self.last_step = 0

        # Trackers
        self.episode_rewards: list[float] = []
        self.episode_lengths: list[int] = []
        self.best_reward = -float("inf")
        self._frame_debug_count = 0

    def _on_step(self) -> bool:
        # Check for episode completions every step and report immediately
        infos = self.locals.get("infos", [])
        for info in infos:
            if "episode" in info:
                ep_reward = info["episode"]["r"]
                ep_len = info["episode"]["l"]
                self.episode_rewards.append(ep_reward)
                self.episode_lengths.append(ep_len)

                if ep_reward > self.best_reward:
                    self.best_reward = ep_reward

                self.queue.put({
                    "type": "episode",
                    "step": self.num_timesteps,
                    "timestamp": time.time(),
                    "reward": ep_reward,
                    "length": ep_len,
                    "best_reward": self.best_reward,
                })

        # Frame capture — use env_method for both DummyVecEnv and SubprocVecEnv
        if self.n_calls % 5 == 0:
            try:
                results = self.training_env.env_method("render", indices=[0])
                frame = results[0] if results else None

                if self._frame_debug_count < 5:
                    self._frame_debug_count += 1
                    print(
                        f"[FrameDebug #{self._frame_debug_count}] "
                        f"vec_env={type(self.training_env).__name__}, "
                        f"frame={type(frame).__name__}"
                        f"{'(' + 'x'.join(map(str, frame.shape)) + ')' if hasattr(frame, 'shape') else ''}"
                        f", n_calls={self.n_calls}",
                        flush=True,
                    )

                if frame is not None:
                    frame = np.ascontiguousarray(frame, dtype=np.uint8)
                    h, w = frame.shape[:2]
                    header = w.to_bytes(2, "little") + h.to_bytes(2, "little")
                    self.queue.put(("frame_bytes", header + frame.tobytes()))
            except Exception as e:
                if self._frame_debug_count < 5:
                    self._frame_debug_count += 1
                    print(f"[FrameDebug] ERROR: {e}", flush=True)

        # Metrics reporting
        if self.n_calls % self.check_freq == 0:
            now = time.time()
            dt = now - self.last_time
            d_steps = self.num_timesteps - self.last_step
            fps = d_steps / dt if dt > 0 else 0

            self.last_time = now
            self.last_step = self.num_timesteps

            if self.episode_rewards:
                avg_reward = sum(self.episode_rewards) / len(self.episode_rewards)
                last_reward = self.episode_rewards[-1]
            else:
                avg_reward = 0.0
                last_reward = 0.0

            self.episode_rewards = []

            self.queue.put({
                "type": "metric",
                "step": self.num_timesteps,
                "timestamp": now,
                "fps": fps,
                "reward": last_reward,
                "avg_reward": avg_reward,
                "best_reward": max(self.best_reward, -9999),
            })

        return True
