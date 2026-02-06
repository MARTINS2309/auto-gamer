import multiprocessing
import sys
import time
from typing import Any

import numpy as np
from stable_baselines3.common.logger import KVWriter


def _to_serializable(value: Any) -> Any:
    """Convert numpy types and other non-JSON-serializable types to Python natives."""
    if value is None:
        return None
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (int, float, str, bool)):
        return value
    # Fallback: try to convert to float
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


class QueueWriter(KVWriter):
    """
    A custom SB3 Logger writer that sends metrics to a multiprocessing.Queue.
    This allows the web frontend to receive the detailed training stats (losses, fps, etc).
    """

    def __init__(self, queue: multiprocessing.Queue):
        self.queue = queue
        self._call_count = 0
        # Print to stderr to ensure visibility even with buffering
        print("[QueueWriter] Initialized!", file=sys.stderr, flush=True)
        print(f"[QueueWriter] isinstance(self, KVWriter): {isinstance(self, KVWriter)}", file=sys.stderr, flush=True)
        print(f"[QueueWriter] KVWriter base: {KVWriter}", file=sys.stderr, flush=True)
        print(f"[QueueWriter] self.__class__.__mro__: {self.__class__.__mro__}", file=sys.stderr, flush=True)

    def write(
        self,
        key_values: dict[str, Any],
        key_excluded: dict[str, tuple[str, ...]],
        step: int = 0,
    ) -> None:
        try:
            self._call_count += 1
            print(f"[QueueWriter] write() CALLED #{self._call_count}", file=sys.stderr, flush=True)

            # Convert all values to JSON-serializable types
            serialized_data = {}
            for k, v in key_values.items():
                try:
                    serialized_data[k] = _to_serializable(v)
                except Exception as e:
                    print(f"[QueueWriter] Failed to serialize {k}: {e}", file=sys.stderr, flush=True)
                    serialized_data[k] = str(v)

            # Debug logging - categorize keys
            train_keys = [k for k in serialized_data.keys() if k.startswith("train/")]
            rollout_keys = [k for k in serialized_data.keys() if k.startswith("rollout/")]
            time_keys = [k for k in serialized_data.keys() if k.startswith("time/")]

            print(f"[QueueWriter #{self._call_count}] step={step}, total_keys={len(serialized_data)}", file=sys.stderr, flush=True)
            print(f"  train_keys ({len(train_keys)}): {train_keys}", file=sys.stderr, flush=True)
            print(f"  rollout_keys ({len(rollout_keys)}): {rollout_keys}", file=sys.stderr, flush=True)
            print(f"  time_keys ({len(time_keys)}): {time_keys}", file=sys.stderr, flush=True)

            # Send the serialized dictionary
            self.queue.put({
                "type": "sb3_metric",
                "step": step,
                "timestamp": time.time(),
                "data": serialized_data,
            })
            print("[QueueWriter] Message sent to queue", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[QueueWriter] ERROR in write(): {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()

    def close(self) -> None:
        pass
