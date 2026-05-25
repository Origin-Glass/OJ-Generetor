from __future__ import annotations

import random
from itertools import combinations

from .models import TaskSlot


SUPPORTED_TAGS = [
    "implementation",
    "arithmetic",
    "math",
    "geometry",
    "combinatorics",
    "number theory",
    "string",
    "parsing",
    "sorting",
    "binary search",
    "ternary search",
    "two pointers",
    "prefix sum",
    "difference array",
    "stack",
    "queue",
    "deque",
    "priority queue",
    "hash",
    "set",
    "map",
    "brute force",
    "backtracking",
    "greedy",
    "dynamic programming",
    "graph",
    "BFS",
    "DFS",
    "shortest path",
    "dijkstra",
    "floyd warshall",
    "topological sort",
    "union find",
    "minimum spanning tree",
    "tree",
    "tree DP",
    "LCA",
    "segment tree",
    "fenwick tree",
    "lazy propagation",
    "sparse table",
    "bitmask",
    "divide and conquer",
    "sweeping",
    "offline query",
    "game theory",
    "probability",
    "flow",
    "bipartite matching",
    "strongly connected components",
    "centroid decomposition",
    "suffix array",
    "trie",
    "KMP",
    "FFT",
    "convex hull",
    "coordinate compression",
]


LEVEL_POOLS = {
    (1, 5): [
        "implementation",
        "arithmetic",
        "math",
        "sorting",
        "greedy",
        "string",
        "parsing",
        "brute force",
    ],
    (6, 10): [
        "binary search",
        "two pointers",
        "stack",
        "queue",
        "deque",
        "BFS",
        "DFS",
        "dynamic programming",
        "prefix sum",
        "hash",
        "set",
        "map",
        "greedy",
    ],
    (11, 15): [
        "dynamic programming",
        "greedy",
        "graph",
        "shortest path",
        "tree",
        "union find",
        "combinatorics",
        "dijkstra",
        "topological sort",
        "minimum spanning tree",
        "bitmask",
    ],
    (16, 20): [
        "segment tree",
        "lazy propagation",
        "tree DP",
        "dijkstra",
        "offline query",
        "geometry",
        "fenwick tree",
        "sparse table",
        "divide and conquer",
        "sweeping",
        "LCA",
        "coordinate compression",
    ],
    (21, 25): [
        "flow",
        "graph",
        "strongly connected components",
        "centroid decomposition",
        "dynamic programming",
        "convex hull",
        "suffix array",
        "trie",
        "KMP",
        "game theory",
        "probability",
        "bipartite matching",
    ],
    (26, 30): [
        "segment tree",
        "lazy propagation",
        "sparse table",
        "geometry",
        "flow",
        "FFT",
        "combinatorics",
        "offline query",
        "dynamic programming",
        "convex hull",
        "centroid decomposition",
        "suffix array",
        "bitmask",
        "divide and conquer",
    ],
}


class TagPlanner:
    def __init__(self, seed: int = 20260525) -> None:
        self.seed = seed

    def pool_for_level(self, level: int) -> list[str]:
        for (lo, hi), pool in LEVEL_POOLS.items():
            if lo <= level <= hi:
                return list(pool)
        raise ValueError(f"Invalid level: {level}")

    def build_assignments(self, slots: list[TaskSlot]) -> dict[str, list[str]]:
        assignments: dict[str, list[str]] = {}
        by_level: dict[int, list[TaskSlot]] = {}
        for slot in slots:
            by_level.setdefault(slot.level, []).append(slot)
        for level, level_slots in by_level.items():
            pool = self.pool_for_level(level)
            combos = self._unique_combos(pool, len(level_slots), level)
            for slot, combo in zip(sorted(level_slots, key=lambda s: s.index), combos):
                assignments[slot.slot_id] = combo
        return assignments

    def apply(self, slots: list[TaskSlot]) -> list[TaskSlot]:
        assignments = self.build_assignments(slots)
        updated: list[TaskSlot] = []
        for slot in slots:
            if hasattr(slot, "model_copy"):
                updated.append(slot.model_copy(update={"tags": assignments[slot.slot_id]}))
            else:
                updated.append(slot.copy(update={"tags": assignments[slot.slot_id]}))
        return updated

    def _unique_combos(self, pool: list[str], needed: int, level: int) -> list[list[str]]:
        rng = random.Random(self.seed + level)
        candidates: list[tuple[str, ...]] = []
        for size in (1, 2, 3):
            candidates.extend(combinations(pool, size))
        rng.shuffle(candidates)
        if len(candidates) < needed:
            raise ValueError(f"Not enough unique tag combinations for level {level}")
        chosen = candidates[:needed]
        return [list(combo) for combo in chosen]
