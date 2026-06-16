#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Tuple
from abc import ABC, abstractmethod
from datetime import datetime
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)


@dataclass
class WindowParameters:
    position: np.ndarray
    size: np.ndarray
    transmittance: float = 0.7


@dataclass
class MultiObjectiveFitness:
    objectives: np.ndarray
    uniformity: float
    avg_illuminance: float
    window_efficiency: float

    def dominates(self, other: 'MultiObjectiveFitness') -> bool:
        all_better = np.all(self.objectives >= other.objectives)
        any_better = np.any(self.objectives > other.objectives)
        return all_better and any_better

    def to_single_objective(self, weights: np.ndarray) -> float:
        return float(np.dot(self.objectives, weights))


@dataclass
class PSOParticle:
    position: np.ndarray
    velocity: np.ndarray
    best_position: np.ndarray
    best_fitness: float
    fitness: float = 0.0
    mo_fitness: Optional[MultiObjectiveFitness] = None
    best_mo_fitness: Optional[MultiObjectiveFitness] = None
    crowding_distance: float = 0.0
    rank: int = 0


@dataclass
class OptimizationResult:
    best_solution: List[WindowParameters]
    best_fitness: float
    uniformity: float
    convergence_curve: List[float]
    iterations: int
    avg_illuminance: float
    execution_time: float
    pareto_front: Optional[List[Dict]] = None
    window_efficiency: Optional[float] = None

    def to_dict(self) -> Dict:
        result = {
            'best_solution': [
                {
                    'position': wp.position.tolist(),
                    'size': wp.size.tolist(),
                    'transmittance': float(wp.transmittance)
                }
                for wp in self.best_solution
            ],
            'best_fitness': float(self.best_fitness),
            'uniformity': float(self.uniformity),
            'convergence_curve': [float(x) for x in self.convergence_curve],
            'iterations': int(self.iterations),
            'avg_illuminance': float(self.avg_illuminance),
            'execution_time': float(self.execution_time),
        }
        if self.pareto_front is not None:
            result['pareto_front'] = self.pareto_front
        if self.window_efficiency is not None:
            result['window_efficiency'] = float(self.window_efficiency)
        return result


class ParticleSwarmOptimizer:
    def __init__(
        self,
        fitness_function: Callable[[List[WindowParameters]], Tuple[float, float, float]],
        num_windows: int = 4,
        population_size: int = 30,
        max_iterations: int = 100,
        w: float = 0.7,
        c1: float = 1.5,
        c2: float = 1.5,
        position_bounds: Optional[Tuple[np.ndarray, np.ndarray]] = None,
        size_bounds: Optional[Tuple[np.ndarray, np.ndarray]] = None,
        random_seed: Optional[int] = None,
        use_multi_objective: bool = True,
        objective_weights: Optional[List[float]] = None,
        w_min: float = 0.4,
        w_max: float = 0.9,
        v_max_scale: float = 0.15,
        use_dimension_grouping: bool = True,
        local_search_freq: int = 10,
    ):
        self.fitness_function = fitness_function
        self.num_windows = num_windows
        self.population_size = population_size
        self.max_iterations = max_iterations
        self.w = w
        self.w_min = w_min
        self.w_max = w_max
        self.c1 = c1
        self.c2 = c2
        self.v_max_scale = v_max_scale
        self.position_bounds = position_bounds or (
            np.array([-10, -10, 0.5], dtype=np.float64),
            np.array([10, 10, 5], dtype=np.float64)
        )
        self.size_bounds = size_bounds or (
            np.array([1.0, 1.0], dtype=np.float64),
            np.array([3.0, 2.5], dtype=np.float64)
        )

        self.use_multi_objective = use_multi_objective and num_windows >= 5
        self.objective_weights = np.array(objective_weights or [0.5, 0.3, 0.2])
        self.use_dimension_grouping = use_dimension_grouping and num_windows >= 4
        self.local_search_freq = local_search_freq

        if random_seed is not None:
            np.random.seed(random_seed)

        self.particles: List[PSOParticle] = []
        self.global_best_position: Optional[np.ndarray] = None
        self.global_best_fitness: float = -np.inf
        self.convergence_curve: List[float] = []
        self.pareto_archive: List[PSOParticle] = []

    def _encode_solution_to_particle(self, windows: List[WindowParameters]) -> np.ndarray:
        encoded = []
        for wp in windows:
            encoded.extend(wp.position)
            encoded.extend(wp.size)
            encoded.append(wp.transmittance)
        return np.array(encoded, dtype=np.float64)

    def _particle_to_solution(self, particle_pos: np.ndarray) -> List[WindowParameters]:
        windows = []
        idx = 0
        for _ in range(self.num_windows):
            position = particle_pos[idx:idx+3].copy()
            idx += 3
            size = particle_pos[idx:idx+2].copy()
            idx += 2
            transmittance = particle_pos[idx]
            idx += 1
            windows.append(WindowParameters(
                position=position,
                size=size,
                transmittance=transmittance
            ))
        return windows

    def _compute_multi_objective(
        self,
        fitness: float,
        uniformity: float,
        avg_ill: float,
        windows: List[WindowParameters]
    ) -> MultiObjectiveFitness:
        total_area = sum(float(np.prod(w.size)) for w in windows)
        max_area = self.num_windows * float(np.prod(self.size_bounds[1]))
        window_efficiency = avg_ill / max(total_area, 1.0) * 10.0
        window_efficiency = min(1.0, window_efficiency)

        objectives = np.array([
            uniformity,
            min(1.0, avg_ill / 1000.0),
            window_efficiency
        ], dtype=np.float64)

        return MultiObjectiveFitness(
            objectives=objectives,
            uniformity=uniformity,
            avg_illuminance=avg_ill,
            window_efficiency=window_efficiency
        )

    def _fast_non_dominated_sort(self, particles: List[PSOParticle]) -> List[List[PSOParticle]]:
        fronts: List[List[PSOParticle]] = [[]]
        S: Dict[int, List[int]] = {}
        n: Dict[int, int] = {}

        for i in range(len(particles)):
            S[i] = []
            n[i] = 0
            for j in range(len(particles)):
                if i == j:
                    continue
                if particles[i].mo_fitness.dominates(particles[j].mo_fitness):
                    S[i].append(j)
                elif particles[j].mo_fitness.dominates(particles[i].mo_fitness):
                    n[i] += 1
            if n[i] == 0:
                particles[i].rank = 0
                fronts[0].append(particles[i])

        i = 0
        while len(fronts[i]) > 0:
            next_front = []
            for p in fronts[i]:
                p_idx = particles.index(p)
                for q_idx in S[p_idx]:
                    n[q_idx] -= 1
                    if n[q_idx] == 0:
                        particles[q_idx].rank = i + 1
                        next_front.append(particles[q_idx])
            i += 1
            fronts.append(next_front)

        return fronts[:-1] if len(fronts) > 1 else fronts

    def _calculate_crowding_distance(self, front: List[PSOParticle]):
        if len(front) <= 2:
            for p in front:
                p.crowding_distance = float('inf')
            return

        n_obj = len(front[0].mo_fitness.objectives)
        for p in front:
            p.crowding_distance = 0.0

        for m in range(n_obj):
            front.sort(key=lambda x: x.mo_fitness.objectives[m])

            front[0].crowding_distance = float('inf')
            front[-1].crowding_distance = float('inf')

            min_val = front[0].mo_fitness.objectives[m]
            max_val = front[-1].mo_fitness.objectives[m]
            obj_range = max_val - min_val if max_val > min_val else 1.0

            for i in range(1, len(front) - 1):
                front[i].crowding_distance += (
                    front[i+1].mo_fitness.objectives[m] -
                    front[i-1].mo_fitness.objectives[m]
                ) / obj_range

    def _select_global_best_mo(self, particle: PSOParticle) -> np.ndarray:
        if not self.pareto_archive:
            return particle.best_position

        if len(self.pareto_archive) < 5:
            idx = np.random.randint(0, len(self.pareto_archive))
            return self.pareto_archive[idx].best_position

        tournament = np.random.choice(len(self.pareto_archive), 3, replace=False)
        candidates = [self.pareto_archive[i] for i in tournament]

        candidates.sort(key=lambda p: (p.rank, -p.crowding_distance))
        return candidates[0].best_position

    def _update_pareto_archive(self):
        all_particles = self.pareto_archive + self.particles
        fronts = self._fast_non_dominated_sort(all_particles)

        new_archive = []
        for front in fronts:
            if len(new_archive) + len(front) <= self.population_size:
                self._calculate_crowding_distance(front)
                new_archive.extend(front)
            else:
                self._calculate_crowding_distance(front)
                front.sort(key=lambda p: -p.crowding_distance)
                remaining = self.population_size - len(new_archive)
                new_archive.extend(front[:remaining])
                break

        self.pareto_archive = new_archive

    def _initialize_particles(self):
        self.particles = []
        dims_per_window = 6
        total_dims = self.num_windows * dims_per_window

        bound_range = np.concatenate([
            np.tile(self.position_bounds[1] - self.position_bounds[0], self.num_windows),
            np.tile(self.size_bounds[1] - self.size_bounds[0], self.num_windows),
            np.full(self.num_windows, 0.35)
        ])
        self.v_max = self.v_max_scale * bound_range

        for _ in range(self.population_size):
            position = np.zeros(total_dims, dtype=np.float64)
            velocity = np.zeros_like(position)

            for i in range(self.num_windows):
                pos_idx = i * dims_per_window

                if self.use_dimension_grouping:
                    wall_side = i % 4
                    if wall_side == 0:
                        position[pos_idx] = np.random.uniform(6, self.position_bounds[1][0])
                        position[pos_idx + 2] = np.random.uniform(-6, 6)
                    elif wall_side == 1:
                        position[pos_idx] = np.random.uniform(self.position_bounds[0][0], -6)
                        position[pos_idx + 2] = np.random.uniform(-6, 6)
                    elif wall_side == 2:
                        position[pos_idx] = np.random.uniform(-6, 6)
                        position[pos_idx + 2] = np.random.uniform(6, self.position_bounds[1][2])
                    else:
                        position[pos_idx] = np.random.uniform(-6, 6)
                        position[pos_idx + 2] = np.random.uniform(self.position_bounds[0][2], -6)
                else:
                    for j in range(3):
                        position[pos_idx + j] = np.random.uniform(
                            self.position_bounds[0][j],
                            self.position_bounds[1][j]
                        )

                position[pos_idx + 1] = np.random.uniform(1.5, 3.0)

                for j in range(2):
                    position[pos_idx + 3 + j] = np.random.uniform(
                        self.size_bounds[0][j],
                        self.size_bounds[1][j]
                    )

                position[pos_idx + 5] = np.random.uniform(0.5, 0.85)
                velocity[pos_idx + 5] = np.random.uniform(-0.05, 0.05)

            velocity = np.random.uniform(-1, 1, total_dims) * self.v_max

            windows = self._particle_to_solution(position)
            fitness, uniformity, avg_ill = self.fitness_function(windows)

            particle = PSOParticle(
                position=position,
                velocity=velocity,
                best_position=position.copy(),
                best_fitness=fitness,
                fitness=fitness
            )

            if self.use_multi_objective:
                mo_fit = self._compute_multi_objective(fitness, uniformity, avg_ill, windows)
                particle.mo_fitness = mo_fit
                particle.best_mo_fitness = deepcopy(mo_fit)

            self.particles.append(particle)

            if fitness > self.global_best_fitness:
                self.global_best_fitness = fitness
                self.global_best_position = position.copy()

        if self.use_multi_objective:
            self._update_pareto_archive()

    def _clip_bounds(self, position: np.ndarray) -> np.ndarray:
        clipped = position.copy()
        dims_per_window = 6

        for i in range(self.num_windows):
            pos_idx = i * dims_per_window

            for j in range(3):
                clipped[pos_idx + j] = np.clip(
                    clipped[pos_idx + j],
                    self.position_bounds[0][j],
                    self.position_bounds[1][j]
                )

            for j in range(2):
                clipped[pos_idx + 3 + j] = np.clip(
                    clipped[pos_idx + 3 + j],
                    self.size_bounds[0][j],
                    self.size_bounds[1][j]
                )

            clipped[pos_idx + 5] = np.clip(clipped[pos_idx + 5], 0.5, 0.85)

        return clipped

    def _update_inertia_weight(self, iteration: int) -> float:
        progress = iteration / self.max_iterations
        w = self.w_max - (self.w_max - self.w_min) * progress
        return w

    def _update_velocity(self, particle: PSOParticle, iteration: int) -> np.ndarray:
        w = self._update_inertia_weight(iteration)

        r1 = np.random.random(particle.velocity.shape)
        r2 = np.random.random(particle.velocity.shape)

        if self.use_multi_objective and self.pareto_archive:
            gbest_pos = self._select_global_best_mo(particle)
        else:
            gbest_pos = self.global_best_position

        cognitive = self.c1 * r1 * (particle.best_position - particle.position)
        social = self.c2 * r2 * (gbest_pos - particle.position)

        new_velocity = w * particle.velocity + cognitive + social

        new_velocity = np.clip(new_velocity, -self.v_max, self.v_max)

        if self.use_dimension_grouping and np.random.random() < 0.1:
            dims_per_window = 6
            win_idx = np.random.randint(0, self.num_windows)
            start = win_idx * dims_per_window
            end = start + dims_per_window
            perturbation = np.random.normal(0, 0.1, dims_per_window) * self.v_max[start:end]
            new_velocity[start:end] += perturbation

        return new_velocity

    def _local_search(self, particle: PSOParticle) -> Tuple[float, float, float]:
        best_fit = particle.fitness
        best_uniformity = particle.mo_fitness.uniformity if particle.mo_fitness else 0.0
        best_avg_ill = particle.mo_fitness.avg_illuminance if particle.mo_fitness else 0.0
        improved = False

        dims_per_window = 6
        for _ in range(min(5, self.num_windows)):
            win_idx = np.random.randint(0, self.num_windows)
            start = win_idx * dims_per_window
            end = start + dims_per_window

            test_pos = particle.position.copy()
            perturbation = np.random.normal(0, 0.05, dims_per_window) * (
                self.position_bounds[1][0] - self.position_bounds[0][0]
            )
            test_pos[start:end] += perturbation
            test_pos = self._clip_bounds(test_pos)

            windows = self._particle_to_solution(test_pos)
            fit, uni, avg = self.fitness_function(windows)

            if fit > best_fit:
                best_fit = fit
                best_uniformity = uni
                best_avg_ill = avg
                particle.position = test_pos
                improved = True

        return best_fit, best_uniformity, best_avg_ill

    def optimize(self, callback: Optional[Callable[[int, float], None]] = None) -> OptimizationResult:
        import time
        start_time = time.time()

        logger.info("Starting Particle Swarm Optimization...")
        logger.info(f"Population size: {self.population_size}, Max iterations: {self.max_iterations}")
        logger.info(f"Number of windows to optimize: {self.num_windows}")
        logger.info(f"Multi-objective: {self.use_multi_objective}, Dimension grouping: {self.use_dimension_grouping}")

        self._initialize_particles()
        self.convergence_curve = [self.global_best_fitness]

        best_uniformity = 0.0
        best_avg_ill = 0.0
        best_window_efficiency = 0.0
        stagnation_count = 0

        for iteration in range(self.max_iterations):
            for particle in self.particles:
                windows = self._particle_to_solution(particle.position)
                try:
                    fitness, uniformity, avg_ill = self.fitness_function(windows)
                except Exception as e:
                    logger.warning(f"Error evaluating fitness: {e}")
                    fitness = -np.inf
                    uniformity = 0.0
                    avg_ill = 0.0

                particle.fitness = fitness

                if self.use_multi_objective:
                    mo_fit = self._compute_multi_objective(fitness, uniformity, avg_ill, windows)
                    particle.mo_fitness = mo_fit

                    if particle.best_mo_fitness is None or mo_fit.dominates(particle.best_mo_fitness):
                        particle.best_mo_fitness = deepcopy(mo_fit)
                        particle.best_position = particle.position.copy()
                        particle.best_fitness = fitness

                if fitness > particle.best_fitness:
                    particle.best_fitness = fitness
                    particle.best_position = particle.position.copy()

                if fitness > self.global_best_fitness:
                    self.global_best_fitness = fitness
                    self.global_best_position = particle.position.copy()
                    best_uniformity = uniformity
                    best_avg_ill = avg_ill
                    if particle.mo_fitness:
                        best_window_efficiency = particle.mo_fitness.window_efficiency
                    stagnation_count = 0

            if self.use_multi_objective:
                self._update_pareto_archive()

            for particle in self.particles:
                particle.velocity = self._update_velocity(particle, iteration)
                particle.position += particle.velocity
                particle.position = self._clip_bounds(particle.position)

            if self.local_search_freq > 0 and (iteration + 1) % self.local_search_freq == 0:
                sorted_particles = sorted(self.particles, key=lambda p: p.fitness, reverse=True)
                for elite in sorted_particles[:max(3, self.population_size // 10)]:
                    fit, uni, avg = self._local_search(elite)
                    if fit > elite.fitness:
                        elite.fitness = fit
                        elite.best_fitness = fit
                        elite.best_position = elite.position.copy()
                        if fit > self.global_best_fitness:
                            self.global_best_fitness = fit
                            self.global_best_position = elite.position.copy()
                            best_uniformity = uni
                            best_avg_ill = avg
                            stagnation_count = 0

            self.convergence_curve.append(self.global_best_fitness)

            if callback is not None:
                callback(iteration + 1, self.global_best_fitness)

            if (iteration + 1) % 10 == 0:
                logger.info(
                    f"Iteration {iteration + 1}/{self.max_iterations}, "
                    f"Best fitness: {self.global_best_fitness:.4f}, "
                    f"Uniformity: {best_uniformity:.4f}, "
                    f"Avg Ill: {best_avg_ill:.1f} lux"
                )

            if len(self.convergence_curve) > 10:
                if abs(self.convergence_curve[-1] - self.convergence_curve[-10]) < 1e-5:
                    stagnation_count += 1
                    if stagnation_count > 15 and iteration > self.max_iterations * 0.3:
                        logger.info(f"Convergence stagnated for {stagnation_count} iters, stopping early")
                        break
                else:
                    stagnation_count = 0

        best_windows = self._particle_to_solution(self.global_best_position)

        execution_time = time.time() - start_time

        pareto_front = None
        if self.use_multi_objective and self.pareto_archive:
            pareto_front = []
            for p in self.pareto_archive[:20]:
                if p.mo_fitness:
                    pareto_front.append({
                        'objectives': p.mo_fitness.objectives.tolist(),
                        'uniformity': float(p.mo_fitness.uniformity),
                        'avg_illuminance': float(p.mo_fitness.avg_illuminance),
                        'window_efficiency': float(p.mo_fitness.window_efficiency),
                    })

        logger.info(f"Optimization completed in {execution_time:.2f} seconds")
        logger.info(f"Best fitness: {self.global_best_fitness:.4f}")
        logger.info(f"Uniformity: {best_uniformity:.4f}")
        logger.info(f"Average illuminance: {best_avg_ill:.2f} lux")

        return OptimizationResult(
            best_solution=best_windows,
            best_fitness=self.global_best_fitness,
            uniformity=best_uniformity,
            convergence_curve=self.convergence_curve,
            iterations=len(self.convergence_curve) - 1,
            avg_illuminance=best_avg_ill,
            execution_time=execution_time,
            pareto_front=pareto_front,
            window_efficiency=best_window_efficiency
        )


class LightingFitnessEvaluator:
    def __init__(
        self,
        lighting_calculator,
        target_uniformity_weight: float = 0.6,
        avg_illuminance_weight: float = 0.4,
        min_avg_illuminance: float = 100.0,
        evaluation_times: Optional[List[datetime]] = None
    ):
        self.lighting_calculator = lighting_calculator
        self.w = target_uniformity_weight
        self.ill_weight = avg_illuminance_weight
        self.min_avg_ill = min_avg_illuminance

        if evaluation_times is None:
            now = datetime.now()
            self.evaluation_times = [
                datetime(now.year, now.month, now.day, 10),
                datetime(now.year, now.month, now.day, 12),
                datetime(now.year, now.month, now.day, 14),
            ]
        else:
            self.evaluation_times = evaluation_times

    def __call__(self, windows: List[WindowParameters]) -> Tuple[float, float, float]:
        window_configs = []
        for wp in windows:
            normal = self._get_normal_from_position(wp.position)
            window_configs.append({
                'position': wp.position.tolist(),
                'size': wp.size.tolist(),
                'normal': normal.tolist(),
                'up': [0, 0, 1],
                'transmittance': wp.transmittance
            })

        self.lighting_calculator.update_windows(window_configs)

        uniformities = []
        avg_illuminances = []

        for eval_time in self.evaluation_times:
            result = self.lighting_calculator.calculate_illuminance(eval_time)
            uniformities.append(result.uniformity)
            avg_illuminances.append(result.avg_illuminance)

        avg_uniformity = np.mean(uniformities)
        avg_ill = np.mean(avg_illuminances)

        uniformity_score = avg_uniformity

        if avg_ill >= self.min_avg_ill:
            illuminance_score = 1.0
        else:
            illuminance_score = avg_ill / self.min_avg_ill

        penalty = self._calculate_overlap_penalty(windows)

        fitness = (self.w * uniformity_score +
                   self.ill_weight * illuminance_score) * (1 - penalty)

        return fitness, avg_uniformity, avg_ill

    def _get_normal_from_position(self, position: np.ndarray) -> np.ndarray:
        x, y, z = position
        if abs(x) > abs(y):
            return np.array([1 if x > 0 else -1, 0, 0], dtype=np.float64)
        else:
            return np.array([0, 1 if y > 0 else -1, 0], dtype=np.float64)

    def _calculate_overlap_penalty(self, windows: List[WindowParameters]) -> float:
        penalty = 0.0
        for i in range(len(windows)):
            for j in range(i + 1, len(windows)):
                w1, w2 = windows[i], windows[j]
                dist = np.linalg.norm(w1.position[:2] - w2.position[:2])
                min_dist = np.mean(w1.size) + np.mean(w2.size)
                if dist < min_dist * 0.5:
                    penalty += 0.1 * (1 - dist / (min_dist * 0.5))
        return min(penalty, 0.5)
