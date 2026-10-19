"""Testes de integração com o conjunto do professor.

São ignorados quando ``docencia/fontes`` não existe, por exemplo em um clone novo
do repositório antes de rodar ``file-hunter extract``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from file_hunter.algorithms import UCS
from file_hunter.stages import run_stage1, run_stage2, run_stage3

ROOT = Path(__file__).resolve().parent.parent / "docencia" / "fontes"

pytestmark = pytest.mark.skipif(not ROOT.is_dir(), reason="conjunto de dados não extraído")


def test_full_scan_matches_the_known_structure():
    bfs, dfs = run_stage1(ROOT, repeats=1)
    for record in (bfs, dfs):
        assert record.outcome.expanded == 11
        assert len(record.outcome.discoveries) == 62
    assert [d.path for d in bfs.outcome.discoveries] != [d.path for d in dfs.outcome.discoveries]


def test_livro_search_uses_cheapest_folder_with_ucs():
    records = {r.algorithm: r for r in run_stage2(ROOT, "livro", repeats=1)}
    assert records["UCS"].outcome.first.path.name == "Livro GTI.pdf"
    assert records["UCS"].outcome.first.g == 13
    assert records["BFS"].outcome.first.g > records["UCS"].outcome.first.g


def test_content_search_finds_keyword_in_cheapest_folder_that_has_it():
    (record,) = run_stage3(ROOT, "algoritmo", (UCS,), repeats=1)
    assert record.outcome.first.path.parent.name == "Fontes PCD"
