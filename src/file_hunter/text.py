"""Normalização de texto usada pelas buscas por nome e por conteúdo."""

from __future__ import annotations

import re
import unicodedata

_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def normalize(text: str, *, strip: bool = True) -> str:
    """Devolve o texto em minúsculas, sem acentos e com separadores colapsados.

    Qualquer sequência de caracteres que não seja letra ou dígito vira um único
    espaço. Assim "Guia Rápido_ Minimização" e "guia rapido minimizacao"
    comparam como iguais. Com ``strip=False`` o espaço das bordas é mantido,
    o que permite normalizar um arquivo em blocos sem juntar palavras vizinhas.
    """
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    folded = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    collapsed = _NON_ALNUM.sub(" ", folded)
    return collapsed.strip() if strip else collapsed


def tokenize(text: str) -> list[str]:
    """Quebra o texto normalizado em palavras."""
    normalized = normalize(text)
    return normalized.split() if normalized else []
