"""
MemoryEvolution - Manages populations of knowledge genomes.

Handles:
- Population management (save/load genomes)
- Selection (pick best performers)
- Crossover (combine successful genomes)
- Tournament selection for parallel runs

Reference: docs/plan.md - RL training support
"""

import json
import random
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

from .genome import KnowledgeGenome, GenomeStats


class MemoryEvolution:
    """
    Evolutionary system for knowledge genomes.
    """

    def __init__(self, population_dir: Path = None):
        self.population_dir = population_dir or Path("data/genomes")
        self.population_dir.mkdir(parents=True, exist_ok=True)

        self.hall_of_fame_dir = self.population_dir / "hall_of_fame"
        self.hall_of_fame_dir.mkdir(exist_ok=True)

        self.current_population: List[KnowledgeGenome] = []
        self.generation = 0
        self.total_runs = 0

        self._load_population()

    def _load_population(self):
        """Load all genomes from disk."""
        self.current_population = []
        for path in self.population_dir.glob("*.json"):
            if path.stem != "population_meta":
                try:
                    genome = KnowledgeGenome.load(path)
                    self.current_population.append(genome)
                except Exception as e:
                    print(f"Failed to load genome {path}: {e}")

        # Load hall of fame too
        for path in self.hall_of_fame_dir.glob("*.json"):
            try:
                genome = KnowledgeGenome.load(path)
                if genome not in self.current_population:
                    self.current_population.append(genome)
            except Exception:
                pass

        # Load meta info
        meta_path = self.population_dir / "population_meta.json"
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
                self.generation = meta.get("generation", 0)
                self.total_runs = meta.get("total_runs", 0)

        print(f"Loaded {len(self.current_population)} genomes (gen {self.generation}, {self.total_runs} runs)")

    def _save_meta(self):
        """Save population metadata."""
        meta_path = self.population_dir / "population_meta.json"
        with open(meta_path, "w") as f:
            json.dump({
                "generation": self.generation,
                "total_runs": self.total_runs,
                "population_size": len(self.current_population),
                "updated_at": datetime.now().isoformat(),
            }, f, indent=2)

    def save_genome(self, genome: KnowledgeGenome):
        """Save a genome to disk."""
        path = self.population_dir / f"{genome.id}.json"
        genome.save(path)

        # Check if it belongs in hall of fame (top 10 ever)
        self._update_hall_of_fame(genome)

    def _update_hall_of_fame(self, genome: KnowledgeGenome):
        """Add to hall of fame if worthy."""
        hof_genomes = []
        for path in self.hall_of_fame_dir.glob("*.json"):
            try:
                hof_genomes.append(KnowledgeGenome.load(path))
            except Exception:
                pass

        hof_genomes.append(genome)
        hof_genomes.sort(key=lambda g: g.fitness(), reverse=True)

        # Keep top 10
        for i, g in enumerate(hof_genomes[:10]):
            g.save(self.hall_of_fame_dir / f"{g.id}.json")

        # Remove others from hall of fame
        for g in hof_genomes[10:]:
            hof_path = self.hall_of_fame_dir / f"{g.id}.json"
            if hof_path.exists():
                hof_path.unlink()

    def get_genome(self, genome_id: str = None) -> KnowledgeGenome:
        """
        Get a genome for a new run.
        If no id specified, selects based on fitness with exploration.
        """
        if genome_id:
            for g in self.current_population:
                if g.id == genome_id:
                    return g
            # Try to load from disk
            path = self.population_dir / f"{genome_id}.json"
            if path.exists():
                return KnowledgeGenome.load(path)

        # No population yet - create first genome
        if not self.current_population:
            genome = KnowledgeGenome()
            self.current_population.append(genome)
            self.save_genome(genome)
            return genome

        # Tournament selection with exploration
        return self._tournament_select()

    def _tournament_select(self, tournament_size: int = 3) -> KnowledgeGenome:
        """Select a genome using tournament selection."""
        # 20% chance to explore (random selection or new mutation)
        if random.random() < 0.2:
            if random.random() < 0.5 and self.current_population:
                # Mutate a random genome
                parent = random.choice(self.current_population)
                return parent.mutate()
            else:
                # Completely random
                return random.choice(self.current_population) if self.current_population else KnowledgeGenome()

        # Tournament selection (exploitation)
        if len(self.current_population) < tournament_size:
            tournament = self.current_population[:]
        else:
            tournament = random.sample(self.current_population, tournament_size)

        # Pick best from tournament
        return max(tournament, key=lambda g: g.fitness())

    def get_genomes_for_parallel(self, count: int) -> List[KnowledgeGenome]:
        """
        Get multiple diverse genomes for parallel runs.
        Mix of: best performers, mutations, crossovers, and exploration.
        """
        if not self.current_population:
            # Bootstrap with random genomes
            return [KnowledgeGenome() for _ in range(count)]

        genomes = []
        sorted_pop = sorted(self.current_population, key=lambda g: g.fitness(), reverse=True)

        # Strategy mix for parallel runs:
        # 30% - top performers (exploitation)
        # 30% - mutations of top performers
        # 20% - crossovers
        # 20% - exploration (random or new)

        n_exploit = max(1, int(count * 0.3))
        n_mutate = max(1, int(count * 0.3))
        n_crossover = max(1, int(count * 0.2))
        n_explore = count - n_exploit - n_mutate - n_crossover

        # Top performers
        for i in range(min(n_exploit, len(sorted_pop))):
            genomes.append(sorted_pop[i])

        # Mutations
        for _ in range(n_mutate):
            parent = self._tournament_select()
            genomes.append(parent.mutate())

        # Crossovers
        for _ in range(n_crossover):
            if len(sorted_pop) >= 2:
                p1 = self._tournament_select()
                p2 = self._tournament_select()
                genomes.append(KnowledgeGenome.crossover(p1, p2))
            else:
                genomes.append(KnowledgeGenome())

        # Exploration
        for _ in range(n_explore):
            genomes.append(KnowledgeGenome())

        return genomes[:count]

    def complete_run(self, genome: KnowledgeGenome, stats: GenomeStats):
        """
        Called when a run completes. Updates genome stats and saves.
        """
        self.total_runs += 1

        # Merge stats
        genome.stats.total_steps += stats.total_steps
        genome.stats.battles_won += stats.battles_won
        genome.stats.battles_lost += stats.battles_lost
        genome.stats.pokemon_caught += stats.pokemon_caught
        genome.stats.badges_earned += stats.badges_earned
        genome.stats.deaths += stats.deaths
        genome.stats.distance_traveled += stats.distance_traveled
        genome.stats.unique_maps_visited = max(genome.stats.unique_maps_visited, stats.unique_maps_visited)
        genome.stats.max_money = max(genome.stats.max_money, stats.max_money)
        genome.stats.playtime_seconds += stats.playtime_seconds

        # Add to population if not already there
        if genome not in self.current_population:
            self.current_population.append(genome)

        # Save
        self.save_genome(genome)
        self._save_meta()

        print(f"Run {self.total_runs}: {genome} - fitness {genome.fitness():.1f}")

    def evolve_generation(self, keep_top: int = 5, offspring_per_parent: int = 2):
        """
        Create a new generation from current population.
        """
        if not self.current_population:
            return

        self.generation += 1

        # Sort by fitness
        sorted_pop = sorted(self.current_population, key=lambda g: g.fitness(), reverse=True)

        # Keep top performers
        survivors = sorted_pop[:keep_top]

        # Create offspring
        new_genomes = list(survivors)  # Copy survivors

        for parent in survivors:
            for _ in range(offspring_per_parent):
                if random.random() < 0.7:
                    # Mutation
                    child = parent.mutate()
                else:
                    # Crossover with another survivor
                    other = random.choice(survivors)
                    child = KnowledgeGenome.crossover(parent, other)

                new_genomes.append(child)
                self.save_genome(child)

        self.current_population = new_genomes
        self._save_meta()

        print(f"Generation {self.generation}: {len(new_genomes)} genomes")

    def get_stats(self) -> dict:
        """Get population statistics."""
        if not self.current_population:
            return {"generation": 0, "population": 0, "total_runs": self.total_runs}

        fitnesses = [g.fitness() for g in self.current_population]
        return {
            "generation": self.generation,
            "population": len(self.current_population),
            "total_runs": self.total_runs,
            "best_fitness": max(fitnesses),
            "avg_fitness": sum(fitnesses) / len(fitnesses),
            "worst_fitness": min(fitnesses),
        }

    def get_lineage(self, genome_id: str) -> List[str]:
        """Get ancestry chain for a genome."""
        lineage = [genome_id]

        current_id = genome_id
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)

            # Find genome
            genome = None
            for g in self.current_population:
                if g.id == current_id:
                    genome = g
                    break

            if not genome:
                path = self.population_dir / f"{current_id}.json"
                if path.exists():
                    try:
                        genome = KnowledgeGenome.load(path)
                    except Exception:
                        break

            if genome and genome.parent_ids:
                current_id = genome.parent_ids[0]  # Follow first parent
                lineage.append(current_id)
            else:
                break

        return lineage
