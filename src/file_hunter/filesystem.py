"""Acesso ao sistema de arquivos com contagem de itens examinados."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .models import Counters


@dataclass(frozen=True, slots=True)
class Entry:
    name: str
    path: Path
    is_dir: bool
    size: int


@dataclass(frozen=True, slots=True)
class Listing:
    """Conteúdo direto de uma pasta, em ordem alfabética estável."""

    entries: tuple[Entry, ...]

    @property
    def item_count(self) -> int:
        """Arquivos mais subpastas contidos diretamente na pasta."""
        return len(self.entries)

    @property
    def directories(self) -> tuple[Entry, ...]:
        return tuple(entry for entry in self.entries if entry.is_dir)

    @property
    def files(self) -> tuple[Entry, ...]:
        return tuple(entry for entry in self.entries if not entry.is_dir)

    @property
    def file_bytes(self) -> int:
        """Soma dos tamanhos dos arquivos diretamente na pasta."""
        return sum(entry.size for entry in self.entries if not entry.is_dir)


class DirectoryReader:
    """Lista pastas uma única vez por execução e conta os itens vistos.

    Cada execução de algoritmo cria o seu próprio leitor. Assim os contadores
    de ``items_examined`` não dependem de buscas anteriores e a comparação entre
    algoritmos é justa. Links simbólicos são ignorados para evitar ciclos.
    """

    def __init__(self, counters: Counters) -> None:
        self._counters = counters
        self._cache: dict[Path, Listing] = {}

    def list(self, path: Path) -> Listing:
        cached = self._cache.get(path)
        if cached is not None:
            return cached
        listing = self._scan(path)
        self._cache[path] = listing
        self._counters.directories_listed += 1
        self._counters.items_examined += listing.item_count
        return listing

    @staticmethod
    def _scan(path: Path) -> Listing:
        entries: list[Entry] = []
        try:
            with os.scandir(path) as iterator:
                for raw in iterator:
                    if raw.is_symlink():
                        continue
                    is_dir = raw.is_dir(follow_symlinks=False)
                    size = 0 if is_dir else raw.stat(follow_symlinks=False).st_size
                    entries.append(Entry(raw.name, Path(raw.path), is_dir, size))
        except PermissionError:
            print(f"aviso: sem permissão para ler {path}", file=sys.stderr)
        entries.sort(key=lambda entry: (entry.name.casefold(), entry.name))
        return Listing(tuple(entries))
