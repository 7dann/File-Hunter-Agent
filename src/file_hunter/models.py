"""Tipos de dados compartilhados entre o motor de busca, as etapas e os relatórios."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class NodeKind(Enum):
    DIRECTORY = "directory"
    FILE = "file"


@dataclass(frozen=True, slots=True)
class Node:
    """Um nó da fronteira de busca.

    ``g`` é o custo acumulado desde a raiz e ``h`` a estimativa até o objetivo.
    Quando o algoritmo não é informado (BFS e DFS), ``g`` e ``h`` ficam em 0 e o
    custo do caminho é recalculado ao final, só para relatório.
    """

    path: Path
    kind: NodeKind
    depth: int
    g: float = 0.0
    h: float = 0.0

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def is_directory(self) -> bool:
        return self.kind is NodeKind.DIRECTORY

    @property
    def f(self) -> float:
        return self.g + self.h


@dataclass(frozen=True, slots=True)
class Discovery:
    """Um alvo encontrado, com o custo do nó em que isso ocorreu."""

    order: int
    path: Path
    g: float
    h: float

    @property
    def f(self) -> float:
        return self.g + self.h


@dataclass(slots=True)
class Counters:
    """Contadores de trabalho feitos pelo problema durante uma busca."""

    items_examined: int = 0
    directories_listed: int = 0
    files_visited: int = 0
    files_read: int = 0
    bytes_read: int = 0


@dataclass(slots=True)
class SearchOutcome:
    """Resultado bruto de uma execução do motor de busca."""

    opened: list[Node] = field(default_factory=list)
    discoveries: list[Discovery] = field(default_factory=list)
    generated: int = 0
    peak_frontier: int = 0

    @property
    def expanded(self) -> int:
        return len(self.opened)

    @property
    def opened_paths(self) -> list[Path]:
        return [node.path for node in self.opened]

    @property
    def found(self) -> bool:
        return bool(self.discoveries)

    @property
    def first(self) -> Discovery | None:
        return self.discoveries[0] if self.discoveries else None


@dataclass(frozen=True, slots=True)
class Measurement:
    """Tempo e memória de uma execução."""

    elapsed_ms: float
    peak_memory_kb: float


@dataclass(slots=True)
class RunRecord:
    """Tudo o que uma execução de algoritmo produziu, pronto para virar tabela."""

    algorithm: str
    outcome: SearchOutcome
    counters: Counters
    measurement: Measurement
    informed: bool = False
