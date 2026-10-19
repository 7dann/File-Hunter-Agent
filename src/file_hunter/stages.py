"""As três etapas do desafio, expressas como combinações de problema e algoritmo."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .algorithms import ASTAR, BFS, DFS, UCS, Algorithm
from .content import ContentSearcher, DispatchingSearcher
from .heuristics import NameHeuristic
from .models import Counters, RunRecord
from .problems import (
    BYTES_COST,
    ITEMS_COST,
    UNIT_COST,
    CollectAllFilesProblem,
    ContentKeywordProblem,
    CostModel,
    NameKeywordProblem,
    TreeProblem,
)
from .runner import execute

#: Peso padrão de h(n) na etapa 2, em itens. As pastas do conjunto têm de 4 a 12 itens.
DEFAULT_NAME_WEIGHT = 10.0

#: Peso padrão de h(n) na etapa 3, em bytes (16 MiB), da ordem de uma pasta pequena do conjunto.
DEFAULT_CONTENT_WEIGHT = 16.0 * 1024 * 1024

STAGE1_ALGORITHMS = (BFS, DFS)
STAGE2_ALGORITHMS = (BFS, DFS, UCS, ASTAR)
STAGE3_ALGORITHMS = (UCS, ASTAR)


def _require_directory(root: Path) -> None:
    if not root.is_dir():
        raise FileNotFoundError(
            f"Pasta raiz não encontrada: {root}. Extraia o conjunto de dados com 'file-hunter extract <arquivo.zip>'."
        )


def run_stage1(
    root: Path,
    algorithms: Sequence[Algorithm] = STAGE1_ALGORITHMS,
    *,
    repeats: int = 5,
) -> list[RunRecord]:
    """Etapa 1: varredura completa da árvore por BFS e DFS."""
    _require_directory(root)

    def make_problem(algorithm: Algorithm, counters: Counters) -> TreeProblem:
        return CollectAllFilesProblem(root, counters, UNIT_COST)

    return [execute(a, make_problem, stop_at_first_goal=False, repeats=repeats) for a in algorithms]


def run_stage2(
    root: Path,
    keyword: str,
    algorithms: Sequence[Algorithm] = STAGE2_ALGORITHMS,
    *,
    weight: float = DEFAULT_NAME_WEIGHT,
    metric: str = "levenshtein",
    repeats: int = 5,
) -> list[RunRecord]:
    """Etapa 2: primeiro arquivo cujo nome contém a palavra, com custo em itens por pasta."""
    _require_directory(root)
    heuristic = NameHeuristic(keyword, weight, metric)

    def make_problem(algorithm: Algorithm, counters: Counters) -> TreeProblem:
        return NameKeywordProblem(
            root,
            counters,
            keyword,
            ITEMS_COST,
            heuristic if algorithm.uses_heuristic else None,
        )

    return [execute(a, make_problem, stop_at_first_goal=True, repeats=repeats) for a in algorithms]


def run_stage3(
    root: Path,
    keyword: str,
    algorithms: Sequence[Algorithm] = STAGE3_ALGORITHMS,
    *,
    weight: float = DEFAULT_CONTENT_WEIGHT,
    metric: str = "levenshtein",
    repeats: int = 1,
    searcher: ContentSearcher | None = None,
) -> list[RunRecord]:
    """Etapa 3: primeiro arquivo cujo conteúdo contém a palavra, com custo em bytes por pasta."""
    _require_directory(root)
    heuristic = NameHeuristic(keyword, weight, metric)
    content_searcher = searcher or DispatchingSearcher()

    def make_problem(algorithm: Algorithm, counters: Counters) -> TreeProblem:
        return ContentKeywordProblem(
            root,
            counters,
            keyword,
            content_searcher,
            BYTES_COST,
            heuristic if algorithm.uses_heuristic else None,
        )

    return [execute(a, make_problem, stop_at_first_goal=True, repeats=repeats) for a in algorithms]


def explain_cost(root: Path, target: Path, cost_model: CostModel) -> list[tuple[Path, float]]:
    """Parcelas de g(n) para um arquivo alvo: custo de abertura de cada pasta do caminho."""
    problem = CollectAllFilesProblem(root, Counters(), cost_model)
    return problem.cost_breakdown(target, is_directory=False)
