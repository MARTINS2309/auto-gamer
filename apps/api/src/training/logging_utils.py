from stable_baselines3.common.logger import KVWriter
import multiprocessing
import time
from typing import Dict, Any, Tuple, Union

class QueueWriter(KVWriter):
    """
    A custom SB3 Logger writer that sends metrics to a multiprocessing.Queue.
    This allows the web frontend to receive the detailed training stats (losses, fps, etc).
    """
    def __init__(self, queue: multiprocessing.Queue):
        self.queue = queue

    def write(self, key_values: Dict[str, Any], key_excluded: Dict[str, Union[str, Tuple[str, ...]]], step: int = 0) -> None:
        # Send the whole dictionary
        self.queue.put({
            "type": "sb3_metric",
            "step": step,
            "timestamp": time.time(),
            "data": key_values
        })

    def close(self) -> None:
        pass
