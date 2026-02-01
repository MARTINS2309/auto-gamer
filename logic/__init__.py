"""
Logic modules for Pokemon AI.

Organized by function:
- consume: Get data from the game (screen, memory, state)
- plan: Make decisions and strategy
- act: Execute actions (inputs)
- review: Analyze and learn
- paths: Central directory configuration
"""

from . import paths
from . import consume
from . import plan
from . import act
from . import review
