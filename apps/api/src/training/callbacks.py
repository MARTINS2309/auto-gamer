import multiprocessing
import time

import cv2
import numpy as np
from stable_baselines3.common.callbacks import BaseCallback


class BroadcastingCallback(BaseCallback):
    def __init__(
        self,
        queue: multiprocessing.Queue,
        check_freq: int = 1000,
        frame_freq: int = 30,
        grid_mode: bool = True,
        max_grid_envs: int = 16,
        shared_frame_freq: "multiprocessing.sharedctypes.Synchronized[int] | None" = None,
        shared_focused_env: "multiprocessing.sharedctypes.Synchronized[int] | None" = None,
    ):
        super().__init__(verbose=0)
        self.queue = queue
        self.check_freq = check_freq
        self.frame_freq = frame_freq
        self.shared_frame_freq = shared_frame_freq
        self.shared_focused_env = shared_focused_env
        self.grid_mode = grid_mode
        self.max_grid_envs = max_grid_envs
        self.last_time = time.time()
        self.last_step = 0

        # Trackers
        self.episode_rewards: list[float] = []
        self.episode_lengths: list[int] = []
        self.best_reward = -float("inf")

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

                # Send episode completion event immediately
                self.queue.put({
                    "type": "episode",
                    "step": self.num_timesteps,
                    "timestamp": time.time(),
                    "reward": ep_reward,
                    "length": ep_len,
                    "best_reward": self.best_reward,
                })

        # Frame Capture — read dynamic frequency from shared memory if available
        freq = self.shared_frame_freq.value if self.shared_frame_freq else self.frame_freq
        focused_env = self.shared_focused_env.value if self.shared_focused_env else -1

        if freq > 0:
            self._maybe_send_frames(freq, focused_env)

        # Metrics Reporting
        if self.n_calls % self.check_freq == 0:
            current_time = time.time()
            dt = current_time - self.last_time
            d_steps = self.num_timesteps - self.last_step
            fps = d_steps / dt if dt > 0 else 0

            self.last_time = current_time
            self.last_step = self.num_timesteps

            if len(self.episode_rewards) > 0:
                avg_reward = sum(self.episode_rewards) / len(self.episode_rewards)
                last_reward = self.episode_rewards[-1]
            else:
                avg_reward = 0.0
                last_reward = 0.0

            self.episode_rewards = []

            metric = {
                "type": "metric",
                "step": self.num_timesteps,
                "timestamp": current_time,
                "fps": fps,
                "reward": last_reward,
                "avg_reward": avg_reward,
                "best_reward": max(self.best_reward, -9999),
            }

            self.queue.put(metric)

        return True

    def _maybe_send_frames(self, freq: int, focused_env: int) -> None:
        """Decide which frames to send and emit them as binary JPEG tuples."""
        send_focused = False
        send_grid = False

        if focused_env >= 0:
            # Focused mode: focused env at frame_freq, grid at frame_freq * 5
            if self.n_calls % freq == 0:
                send_focused = True
            grid_freq = freq * 5
            if grid_freq > 0 and self.n_calls % grid_freq == 0:
                send_grid = True
        else:
            # Grid-only mode: grid at frame_freq
            if self.n_calls % freq == 0:
                send_grid = True

        if not send_focused and not send_grid:
            return

        try:
            frames = self.training_env.render()

            if frames is None and hasattr(self.training_env, "envs"):
                rendered = [env.render() for env in self.training_env.envs]
                rendered = [f for f in rendered if f is not None]
                frames = rendered if rendered else None  # type: ignore[assignment]

            if frames is None:
                return

            # Debug logging
            if self.n_calls == freq or self.n_calls % 1000 == 0:
                frame_info = f"type={type(frames)}"
                if isinstance(frames, np.ndarray):
                    frame_info += f", shape={frames.shape}, dtype={frames.dtype}"
                elif isinstance(frames, list):
                    frame_info += f", len={len(frames)}"
                    if len(frames) > 0 and isinstance(frames[0], np.ndarray):
                        frame_info += f", item_shape={frames[0].shape}"
                print(f"[BroadcastingCallback] Frame capture: {frame_info}", flush=True)

            is_multi = isinstance(frames, list) or (
                isinstance(frames, np.ndarray) and len(frames.shape) == 4
            )

            if is_multi:
                n_envs = min(len(frames), self.max_grid_envs)
            else:
                n_envs = 1

            # Single env: just send it directly
            if n_envs == 1:
                frame = frames[0] if is_multi else frames
                self._send_frame(self._ensure_rgb(frame), 0, 1)
                return

            # Multi-env: send focused and/or grid
            if send_focused and 0 <= focused_env < n_envs:
                frame = frames[focused_env]
                self._send_frame(self._ensure_rgb(frame), focused_env, n_envs, quality=70)

            if send_grid and self.grid_mode:
                grid = self._create_grid(frames)
                self._send_frame(grid, 0xFF, n_envs, quality=60)

        except Exception as e:
            if self.n_calls % 1000 == 0:
                import traceback
                print(f"[BroadcastingCallback] Frame capture failed: {e}", flush=True)
                traceback.print_exc()

    def _send_frame(self, frame: np.ndarray, env_index: int, n_envs: int, quality: int = 70) -> None:
        """JPEG-encode a frame and put it on the queue as a binary tuple."""
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        _, buffer = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        header = bytes([env_index & 0xFF, n_envs & 0xFF])
        self.queue.put(("frame_bytes", header + buffer.tobytes()))

    @staticmethod
    def _ensure_rgb(frame: np.ndarray) -> np.ndarray:
        """Ensure frame is uint8 RGB."""
        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        elif frame.shape[2] == 1:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        return frame

    def _create_grid(self, frames: list | np.ndarray) -> np.ndarray:
        """Stitch multiple env frames into a grid layout."""
        frames_arr = np.array(frames)
        n_envs = min(len(frames_arr), self.max_grid_envs)
        frames_arr = frames_arr[:n_envs]

        n_cols = int(np.ceil(np.sqrt(n_envs)))
        n_rows = int(np.ceil(n_envs / n_cols))

        h, w = frames_arr[0].shape[:2]

        target_width = 640
        scale = target_width / (w * n_cols)
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = [cv2.resize(f, (new_w, new_h)) for f in frames_arr]

        while len(resized) < n_rows * n_cols:
            resized.append(np.zeros((new_h, new_w, 3), dtype=np.uint8))

        rows = []
        for r in range(n_rows):
            row_frames = resized[r * n_cols : (r + 1) * n_cols]
            rows.append(np.hstack(row_frames))
        grid = np.vstack(rows)

        return self._ensure_rgb(grid)
