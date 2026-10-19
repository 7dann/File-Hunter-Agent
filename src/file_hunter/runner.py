"""Execução e medição de um algoritmo sobre um problema."""

from __future__ import annotations

from collections.abc import Callable

from .algorithms import Algorithm
from .engine import run_search
from .measure import profile
from .models import Counters, RunRecord, SearchOutcome
from .problems import TreeProblem

ProblemFactory = Callable[[Algorithm, Counters], TreeProblem]


def execute(
    algorithm: Algorithm,
    make_problem: ProblemFactory,
    *,
    stop_at_first_goal: bool,
    repeats: int = 1,
) -> RunRecord:
    """Roda o algoritmo com estado novo a cada passada e devolve o registro medido."""

    def once() -> tuple[SearchOutcome, Counters]:
        counters = Counters()
        problem = make_problem(algorithm, counters)
        outcome = run_search(problem, algorithm.make_frontier(), stop_at_first_goal=stop_at_first_goal)
        return outcome, counters

    (outcome, counters), measurement = profile(once, repeats=repeats)
    informed = algorithm.make_frontier().informed
    return RunRecord(algorithm.label, outcome, counters, measurement, informed)
