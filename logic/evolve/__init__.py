"""
Evolve - Evolutionary knowledge system.

Modules:
- genome: KnowledgeGenome for heritable knowledge
- evolution: Population management and selection

Allows parallel runs with different genomes, inheriting successful strategies.
"""

from .genome import KnowledgeGenome, GenomeStats
from .evolution import MemoryEvolution
