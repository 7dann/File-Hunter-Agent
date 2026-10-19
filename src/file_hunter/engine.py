"""Motor de busca genérico, compartilhado por BFS, DFS, UCS e A*."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from .frontiers import Frontier
from .models import Discovery, Node, SearchOutcome


class SearchProblem(Protocol):
    """O que o motor precisa saber do domínio (árvore de diretórios)."""

    def root(self, informed: bool) -> Node: ...

    def inspect(self, node: Node) -> Sequence[Path]:
        """Testa o objetivo no nó retirado da fronteira e devolve os alvos achados."""
        ...

    def expand(self, node: Node, informed: bool) -> Sequence[Node]:
        """Gera os filhos do nó."""
        ...

    def accumulated_cost(self, node: Node) -> float:
        """Custo g(n) do caminho da raiz até o nó, calculado sem custo extra de leitura."""
        ...


def run_search(
    problem: SearchProblem,
    frontier: Frontier,
    *,
    stop_at_first_goal: bool,
) -> SearchOutcome:
    """Executa a busca até esvaziar a fronteira ou achar o primeiro alvo.

    O teste de objetivo acontece na retirada do nó da fronteira, não na geração.
    Para UCS e A* isso é o que garante que o primeiro alvo retirado tem o menor
    valor da função de ordenação entre os candidatos da fronteira.
    """
    informed = frontier.informed
    outcome = SearchOutcome()

    frontier.push(problem.root(informed))
    outcome.generated = 1
    outcome.peak_frontier = 1

    while frontier:
        node = frontier.pop()
        goals = problem.inspect(node)

        if node.is_directory:
            outcome.opened.append(node)

        if goals:
            g = node.g if informed else problem.accumulated_cost(node)
            for path in goals:
                outcome.discoveries.append(Discovery(order=len(outcome.discoveries) + 1, path=path, g=g, h=node.h))
            if stop_at_first_goal:
                break

        children = problem.expand(node, informed)
        frontier.extend(children)
        outcome.generated += len(children)
        outcome.peak_frontier = max(outcome.peak_frontier, len(frontier))

    return outcome
