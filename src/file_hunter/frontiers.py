"""Estruturas de fronteira que definem o comportamento de cada algoritmo.

O motor de busca é o mesmo para BFS, DFS, UCS e A*. O que muda é apenas a
política de remoção da fronteira:

* BFS usa uma fila FIFO (``collections.deque`` com ``popleft``).
* DFS usa uma pilha LIFO (``collections.deque`` com ``pop``).
* UCS usa um heap (``heapq``) ordenado pelo custo acumulado g(n).
* A* usa um heap (``heapq``) ordenado por f(n) = g(n) + h(n).
"""

from __future__ import annotations

import heapq
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable, Iterable

from .models import Node


class Frontier(ABC):
    """Conjunto de nós gerados e ainda não visitados."""

    #: Verdadeiro quando a política precisa de g(n) (e talvez h(n)) em cada nó.
    informed: bool = False

    @abstractmethod
    def push(self, node: Node) -> None: ...

    @abstractmethod
    def pop(self) -> Node: ...

    @abstractmethod
    def __len__(self) -> int: ...

    def extend(self, nodes: Iterable[Node]) -> None:
        for node in nodes:
            self.push(node)

    def __bool__(self) -> bool:
        return len(self) > 0


class FifoFrontier(Frontier):
    """Fila FIFO da busca em largura."""

    def __init__(self) -> None:
        self._items: deque[Node] = deque()

    def push(self, node: Node) -> None:
        self._items.append(node)

    def pop(self) -> Node:
        return self._items.popleft()

    def __len__(self) -> int:
        return len(self._items)


class LifoFrontier(Frontier):
    """Pilha LIFO da busca em profundidade."""

    def __init__(self) -> None:
        self._items: deque[Node] = deque()

    def push(self, node: Node) -> None:
        self._items.append(node)

    def pop(self) -> Node:
        return self._items.pop()

    def extend(self, nodes: Iterable[Node]) -> None:
        # Empilha ao contrário para que o primeiro filho em ordem alfabética
        # seja o primeiro a sair da pilha. Sem isso a DFS visitaria os filhos
        # da direita para a esquerda.
        for node in reversed(list(nodes)):
            self.push(node)

    def __len__(self) -> int:
        return len(self._items)


PriorityKey = Callable[[Node], tuple[float, ...]]


class PriorityFrontier(Frontier):
    """Heap de prioridade mínima com desempate estável.

    ``key`` devolve a tupla de ordenação do nó. Um contador crescente entra no
    final da tupla, de modo que nós empatados saem na ordem em que foram gerados
    e o ``heapq`` nunca precisa comparar objetos ``Node``.
    """

    informed = True

    def __init__(self, key: PriorityKey) -> None:
        self._key = key
        self._heap: list[tuple[tuple[float, ...], int, Node]] = []
        self._counter = 0

    def push(self, node: Node) -> None:
        heapq.heappush(self._heap, (self._key(node), self._counter, node))
        self._counter += 1

    def pop(self) -> Node:
        return heapq.heappop(self._heap)[2]

    def __len__(self) -> int:
        return len(self._heap)


def _kind_rank(node: Node) -> float:
    """Arquivos saem antes de pastas quando o custo empata."""
    return 1.0 if node.is_directory else 0.0


def ucs_key(node: Node) -> tuple[float, ...]:
    """UCS ordena somente pelo custo acumulado g(n)."""
    return (node.g, _kind_rank(node))


def astar_key(node: Node) -> tuple[float, ...]:
    """A* ordena por f(n) = g(n) + h(n); empates vão para o menor h(n)."""
    return (node.g + node.h, _kind_rank(node), node.h)
