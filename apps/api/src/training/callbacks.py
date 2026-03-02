import multiprocessing
import time

import numpy as np
from stable_baselines3.common.callbacks import BaseCallback

# On-policy algorithms that have distinct rollout/training phases
ON_POLICY_ALGOS = {"PPO", "A2C"}


class BroadcastingCallback(BaseCallback):
    def __init__(
        self,
        queue: multiprocessing.Queue,
        check_freq: int = 1000,
        frame_fps: int = 15,
        algo_name: str = "PPO",
        n_envs: int = 1,
    ):
        super().__init__(verbose=0)
        self.queue = queue
        self.check_freq = check_freq
        self.algo_name = algo_name
        self._n_envs = n_envs
        self.last_time = time.time()
        self.last_step = 0

        # Trackers
        self.episode_rewards: list[float] = []
        self.episode_lengths: list[int] = []
        self.best_reward = -float("inf")
        self._frame_debug_count = 0

        # Frame throttle — adaptive: scale down with more envs to avoid bandwidth bloat
        effective_fps = max(3, frame_fps // max(1, n_envs // 2))
        self._frame_interval = 1.0 / effective_fps
        self._last_frame_time = 0.0

        # Phase tracking (on-policy only)
        self._has_phases = algo_name in ON_POLICY_ALGOS
        self._current_phase: str = "rollout"
        self._rollout_start_time = 0.0
        self._training_start_time = 0.0
        self._cumulative_rollout_time = 0.0
        self._cumulative_training_time = 0.0
        # For rollout-only FPS: track time spent in training between metric reports
        self._training_time_in_period = 0.0
        self._period_training_start = 0.0

        # Episode-to-recording mapping (env 0 only, for BK2 correlation)
        self._env0_episode_count = 0
        self._episode_recordings: list[dict] = []

    # ── Phase hooks (called by SB3 for on-policy algos) ──────────────

    def _on_rollout_start(self) -> None:
        if not self._has_phases:
            return
        self._current_phase = "rollout"
        self._rollout_start_time = time.time()
        self.queue.put({
            "type": "phase",
            "phase": "rollout",
            "timestamp": self._rollout_start_time,
        })

    def _on_rollout_end(self) -> None:
        if not self._has_phases:
            return
        now = time.time()
        duration = now - self._rollout_start_time
        self._cumulative_rollout_time += duration
        self.queue.put({
            "type": "phase",
            "phase": "rollout_end",
            "timestamp": now,
            "duration": round(duration, 3),
        })

    def _on_training_start(self) -> None:
        if not self._has_phases:
            return
        self._current_phase = "training"
        self._training_start_time = time.time()
        self._period_training_start = self._training_start_time
        self.queue.put({
            "type": "phase",
            "phase": "training",
            "timestamp": self._training_start_time,
        })

    def _on_training_end(self) -> None:
        if not self._has_phases:
            return
        now = time.time()
        duration = now - self._training_start_time
        self._cumulative_training_time += duration
        self._training_time_in_period += duration
        self._current_phase = "rollout"  # about to start next rollout
        self.queue.put({
            "type": "phase",
            "phase": "training_end",
            "timestamp": now,
            "duration": round(duration, 3),
        })

        # Send final recording index on training end
        if self._episode_recordings:
            self.queue.put({
                "type": "recording_index",
                "episodes": self._episode_recordings,
                "complete": True,
            })

    # ── Main step callback ───────────────────────────────────────────

    def _on_step(self) -> bool:
        # Check for episode completions every step and report immediately
        infos = self.locals.get("infos", [])
        for env_idx, info in enumerate(infos):
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
                    "env_index": env_idx,
                })

                # Track env-0 episodes for BK2 recording correlation
                if env_idx == 0:
                    self._episode_recordings.append({
                        "seq": self._env0_episode_count,
                        "reward": float(ep_reward),
                        "length": int(ep_len),
                        "step": self.num_timesteps,
                    })
                    self._env0_episode_count += 1

        # Frame capture — time-based throttle, all envs
        now_frame = time.time()
        if now_frame - self._last_frame_time >= self._frame_interval:
            try:
                n = self.training_env.num_envs
                indices = list(range(n))
                results = self.training_env.env_method("render", indices=indices)
                frames = [r for r in results if r is not None]

                if self._frame_debug_count < 5:
                    self._frame_debug_count += 1
                    print(
                        f"[FrameDebug #{self._frame_debug_count}] "
                        f"vec_env={type(self.training_env).__name__}, "
                        f"n_envs={n}, frames_got={len(frames)}"
                        f"{'(' + 'x'.join(map(str, frames[0].shape)) + ')' if frames else ''}"
                        f", n_calls={self.n_calls}",
                        flush=True,
                    )

                if frames:
                    self._last_frame_time = now_frame
                    h, w = frames[0].shape[:2]
                    # Protocol: [n_envs:u8][width:u16LE][height:u16LE][env0_pixels][env1_pixels]...
                    header = bytes([len(frames)]) + w.to_bytes(2, "little") + h.to_bytes(2, "little")
                    pixel_data = b"".join(
                        np.ascontiguousarray(f, dtype=np.uint8).tobytes() for f in frames
                    )
                    self.queue.put(("frame_bytes", header + pixel_data))
            except Exception as e:
                if self._frame_debug_count < 5:
                    self._frame_debug_count += 1
                    print(f"[FrameDebug] ERROR: {e}", flush=True)

        # Metrics reporting
        if self.n_calls % self.check_freq == 0:
            now = time.time()
            dt = now - self.last_time
            d_steps = self.num_timesteps - self.last_step
            wall_fps = d_steps / dt if dt > 0 else 0

            # Rollout FPS: exclude training time from the period
            rollout_fps = None
            if self._has_phases:
                rollout_dt = dt - self._training_time_in_period
                rollout_fps = d_steps / rollout_dt if rollout_dt > 0 else wall_fps
                self._training_time_in_period = 0.0  # reset for next period

            self.last_time = now
            self.last_step = self.num_timesteps

            if self.episode_rewards:
                avg_reward = sum(self.episode_rewards) / len(self.episode_rewards)
                last_reward = self.episode_rewards[-1]
            else:
                avg_reward = 0.0
                last_reward = 0.0

            self.episode_rewards = []

            msg: dict = {
                "type": "metric",
                "step": self.num_timesteps,
                "timestamp": now,
                "fps": wall_fps,
                "reward": last_reward,
                "avg_reward": avg_reward,
                "best_reward": max(self.best_reward, -9999),
            }

            if self._has_phases:
                msg["rollout_fps"] = rollout_fps
                msg["phase"] = self._current_phase
                msg["cumulative_rollout_time"] = round(self._cumulative_rollout_time, 2)
                msg["cumulative_training_time"] = round(self._cumulative_training_time, 2)

            self.queue.put(msg)

        return True
