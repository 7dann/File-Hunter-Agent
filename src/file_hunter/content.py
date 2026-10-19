"""Busca de palavras no conteúdo de arquivos (texto puro e PDF)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Protocol

from .text import normalize

_CHUNK_CHARS = 1 << 18  # 256 Ki caracteres por leitura em arquivos de texto

TEXT_SUFFIXES = frozenset(
    {".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm", ".log", ".py", ".java", ".c", ".sql", ".tex"}
)


class ContentSearcher(Protocol):
    def contains(self, path: Path, term: str) -> bool:
        """Verdadeiro se o termo aparece no conteúdo do arquivo, ignorando caixa e acentos."""
        ...


class PlainTextSearcher:
    """Lê o arquivo em blocos e procura o termo sem carregar tudo na memória."""

    def contains(self, path: Path, term: str) -> bool:
        needle = normalize(term)
        if not needle:
            return False
        carry = ""
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            while chunk := handle.read(_CHUNK_CHARS):
                folded = normalize(chunk, strip=False)
                if carry.endswith(" ") and folded.startswith(" "):
                    folded = folded[1:]
                haystack = carry + folded
                if needle in haystack:
                    return True
                # Guarda o final do bloco para achar termos cortados na fronteira.
                carry = haystack[-len(needle) :]
        return False


class PdfSearcher:
    """Extrai o texto página a página e para na primeira ocorrência.

    PDFs guardam o texto comprimido, então uma busca de bytes simples não
    funciona. A extração usa ``pypdf``. Arquivos ilegíveis (corrompidos ou
    protegidos por senha) contam como "termo ausente" e geram um aviso.
    """

    def __init__(self) -> None:
        # Importar no construtor tira o custo único de carregar o módulo (cerca de
        # 10 MB de alocações) de dentro da primeira execução medida.
        from pypdf import PdfReader

        logging.getLogger("pypdf").setLevel(logging.ERROR)
        self._reader_class = PdfReader

    def contains(self, path: Path, term: str) -> bool:
        needle = normalize(term)
        if not needle:
            return False
        try:
            reader = self._reader_class(path)
            carry = ""
            for page in reader.pages:
                text = normalize(page.extract_text() or "")
                haystack = carry + " " + text
                if needle in haystack:
                    return True
                carry = haystack[-len(needle) :]
        except Exception as error:  # noqa: BLE001 - pypdf levanta tipos variados
            print(f"aviso: não foi possível ler {path.name}: {error}", file=sys.stderr)
        return False


class DispatchingSearcher:
    """Escolhe o leitor pela extensão do arquivo."""

    def __init__(self) -> None:
        self._text = PlainTextSearcher()
        self._pdf = PdfSearcher()

    def contains(self, path: Path, term: str) -> bool:
        suffix = path.suffix.casefold()
        if suffix == ".pdf":
            return self._pdf.contains(path, term)
        if suffix in TEXT_SUFFIXES:
            return self._text.contains(path, term)
        return False
