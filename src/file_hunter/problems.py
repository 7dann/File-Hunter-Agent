"""Definições de problema: o que é um nó, quanto custa abri-lo e quando é o objetivo."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .content import ContentSearcher
from .filesystem import DirectoryReader, Entry, Listing
from .heuristics import NameHeuristic
from .models import Counters, Node, NodeKind
from .text import normalize


@dataclass(frozen=True, slots=True)
class CostModel:
    """Quanto custa abrir uma pasta, em função do que ela contém."""

    name: str
    unit: str
    open_cost: Callable[[Listing], float]


UNIT_COST = CostModel("1 por pasta aberta", "pastas", lambda listing: 1.0)
ITEMS_COST = CostModel("itens da pasta (arquivos + subpastas)", "itens", lambda listing: float(listing.item_count))
BYTES_COST = CostModel("bytes dos arquivos da pasta", "bytes", lambda listing: float(listing.file_bytes))


class TreeProblem(ABC):
    """Base comum: raiz, custo acumulado e geração de filhos de uma pasta."""

    def __init__(
        self,
        root: Path,
        counters: Counters,
        cost_model: CostModel,
        heuristic: NameHeuristic | None = None,
    ) -> None:
        self.root_path = root
        self.counters = counters
        self.cost_model = cost_model
        self.heuristic = heuristic
        self.reader = DirectoryReader(counters)

    def root(self, informed: bool) -> Node:
        g = self._open_cost(self.root_path) if informed else 0.0
        return Node(self.root_path, NodeKind.DIRECTORY, 0, g, 0.0)

    def accumulated_cost(self, node: Node) -> float:
        """Soma o custo de abertura das pastas da raiz até o nó.

        Para um arquivo, conta as pastas ancestrais. Para uma pasta, inclui a
        própria pasta. Todas já foram listadas pelo algoritmo, então a consulta
        vem do cache do leitor e não altera os contadores.
        """
        return sum(cost for _, cost in self.cost_breakdown(node.path, is_directory=node.is_directory))

    def cost_breakdown(self, path: Path, *, is_directory: bool) -> list[tuple[Path, float]]:
        """Custo de abertura de cada pasta no caminho da raiz até ``path``."""
        relative = path.relative_to(self.root_path)
        parts = relative.parts if is_directory else relative.parts[:-1]
        chain = [self.root_path]
        for part in parts:
            chain.append(chain[-1] / part)
        return [(directory, self._open_cost(directory)) for directory in chain]

    def _open_cost(self, directory: Path) -> float:
        return self.cost_model.open_cost(self.reader.list(directory))

    def _estimate(self, name: str, informed: bool) -> float:
        if not informed or self.heuristic is None:
            return 0.0
        return self.heuristic.estimate(name)

    def _child(self, parent: Node, entry: Entry, informed: bool) -> Node:
        if entry.is_dir:
            g = (parent.g + self._open_cost(entry.path)) if informed else 0.0
            kind = NodeKind.DIRECTORY
        else:
            # Um arquivo não tem custo de abertura próprio: o custo já foi pago
            # ao abrir a pasta que o contém.
            g = parent.g if informed else 0.0
            kind = NodeKind.FILE
        return Node(entry.path, kind, parent.depth + 1, g, self._estimate(entry.name, informed))

    @abstractmethod
    def inspect(self, node: Node) -> Sequence[Path]: ...

    @abstractmethod
    def expand(self, node: Node, informed: bool) -> Sequence[Node]: ...


class FileNodeProblem(TreeProblem):
    """Pastas e arquivos são nós. Um arquivo é objetivo se ``is_target`` aceitar o nome."""

    @abstractmethod
    def is_target(self, name: str) -> bool: ...

    def inspect(self, node: Node) -> Sequence[Path]:
        if node.is_directory:
            return ()
        self.counters.files_visited += 1
        return (node.path,) if self.is_target(node.name) else ()

    def expand(self, node: Node, informed: bool) -> Sequence[Node]:
        if not node.is_directory:
            return ()
        listing = self.reader.list(node.path)
        return [self._child(node, entry, informed) for entry in listing.entries]


class CollectAllFilesProblem(FileNodeProblem):
    """Etapa 1: todo arquivo é objetivo, então a busca percorre a árvore inteira."""

    def is_target(self, name: str) -> bool:
        return True


class NameKeywordProblem(FileNodeProblem):
    """Etapa 2: o objetivo é um arquivo cujo nome contém a palavra-chave."""

    def __init__(
        self,
        root: Path,
        counters: Counters,
        keyword: str,
        cost_model: CostModel = ITEMS_COST,
        heuristic: NameHeuristic | None = None,
    ) -> None:
        super().__init__(root, counters, cost_model, heuristic)
        self.keyword = normalize(keyword)

    def is_target(self, name: str) -> bool:
        return self.keyword in normalize(name)


class ContentKeywordProblem(TreeProblem):
    """Etapa 3: só pastas são nós. Abrir uma pasta lê os arquivos dela, um a um.

    A leitura para no primeiro arquivo que contém a palavra. O custo de abrir a
    pasta é o total de bytes dos arquivos dela (``BYTES_COST``), conhecido por
    ``stat`` sem ler o conteúdo.
    """

    def __init__(
        self,
        root: Path,
        counters: Counters,
        keyword: str,
        searcher: ContentSearcher,
        cost_model: CostModel = BYTES_COST,
        heuristic: NameHeuristic | None = None,
    ) -> None:
        super().__init__(root, counters, cost_model, heuristic)
        self.keyword = keyword
        self._searcher = searcher

    def inspect(self, node: Node) -> Sequence[Path]:
        for entry in self.reader.list(node.path).files:
            self.counters.files_read += 1
            self.counters.bytes_read += entry.size
            if self._searcher.contains(entry.path, self.keyword):
                return (entry.path,)
        return ()

    def expand(self, node: Node, informed: bool) -> Sequence[Node]:
        listing = self.reader.list(node.path)
        return [self._child(node, entry, informed) for entry in listing.directories]
