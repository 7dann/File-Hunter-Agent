"""Catálogo dos quatro algoritmos e fábrica das suas fronteiras."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .frontiers import FifoFrontier, Frontier, LifoFrontier, PriorityFrontier, astar_key, ucs_key


@dataclass(frozen=True, slots=True)
class Algorithm:
    key: str
    label: str
    make_frontier: Callable[[], Frontier]
    uses_heuristic: bool = False


BFS = Algorithm("bfs", "BFS", FifoFrontier)
DFS = Algorithm("dfs", "DFS", LifoFrontier)
UCS = Algorithm("ucs", "UCS", lambda: PriorityFrontier(ucs_key))
ASTAR = Algorithm("astar", "A*", lambda: PriorityFrontier(astar_key), uses_heuristic=True)

ALGORITHMS: dict[str, Algorithm] = {a.key: a for a in (BFS, DFS, UCS, ASTAR)}


def get_algorithms(keys: list[str]) -> list[Algorithm]:
    unknown = [key for key in keys if key not in ALGORITHMS]
    if unknown:
        valid = ", ".join(ALGORITHMS)
        raise ValueError(f"Algoritmo desconhecido: {', '.join(unknown)}. Use: {valid}.")
    return [ALGORITHMS[key] for key in keys]
