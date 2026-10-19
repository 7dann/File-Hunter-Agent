from __future__ import annotations

from pathlib import Path

import pytest

from file_hunter.algorithms import ASTAR, BFS, UCS
from file_hunter.content import DispatchingSearcher, PdfSearcher, PlainTextSearcher
from file_hunter.engine import run_search
from file_hunter.models import Counters
from file_hunter.problems import ContentKeywordProblem
from file_hunter.scenarios import KEYWORD, WEIGHT_BYTES, build_pruning_scenario
from file_hunter.stages import run_stage3
from helpers import make_pdf, make_tree


class FakeSearcher:
    """Marca como achado qualquer arquivo cujo nome esteja em ``hits`` e registra as leituras."""

    def __init__(self, hits: set[str]) -> None:
        self.hits = hits
        self.calls: list[str] = []

    def contains(self, path: Path, term: str) -> bool:
        self.calls.append(path.name)
        return path.name in self.hits


def test_plain_text_searcher_ignores_case_and_accents(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("Introdução ao ALGORÍTMO de busca", encoding="utf-8")
    assert PlainTextSearcher().contains(path, "algoritmo")
    assert not PlainTextSearcher().contains(path, "grafo")
    assert not PlainTextSearcher().contains(path, "   ")


def test_plain_text_searcher_finds_term_split_across_chunks(tmp_path, monkeypatch):
    monkeypatch.setattr("file_hunter.content._CHUNK_CHARS", 8)
    path = tmp_path / "a.txt"
    path.write_text("xxxxxxxalgoritmoyyyyyyy", encoding="utf-8")
    assert PlainTextSearcher().contains(path, "algoritmo")


def test_pdf_searcher_reads_text_from_any_page(tmp_path):
    path = tmp_path / "doc.pdf"
    make_pdf(path, ["primeira pagina", "estudo de algoritmo guloso", "fim"])
    assert PdfSearcher().contains(path, "Algoritmo")
    assert not PdfSearcher().contains(path, "heuristica")


def test_pdf_searcher_survives_corrupt_file(tmp_path, capsys):
    path = tmp_path / "ruim.pdf"
    path.write_bytes(b"isto nao e um pdf")
    assert not PdfSearcher().contains(path, "algoritmo")
    assert "ruim.pdf" in capsys.readouterr().err


def test_dispatching_searcher_by_extension(tmp_path):
    txt = tmp_path / "a.txt"
    txt.write_text("algoritmo", encoding="utf-8")
    pdf = tmp_path / "b.pdf"
    make_pdf(pdf, ["algoritmo"])
    other = tmp_path / "c.bin"
    other.write_bytes(b"algoritmo")
    searcher = DispatchingSearcher()
    assert searcher.contains(txt, "algoritmo")
    assert searcher.contains(pdf, "algoritmo")
    assert not searcher.contains(other, "algoritmo")


def run_once(root: Path, algorithm, searcher: FakeSearcher):
    counters = Counters()
    problem = ContentKeywordProblem(root, counters, "x", searcher)
    outcome = run_search(problem, algorithm.make_frontier(), stop_at_first_goal=True)
    return outcome, counters


def test_stage3_ucs_opens_cheapest_folder_first_and_counts_reads(tmp_path):
    root = make_tree(
        tmp_path / "r",
        {"barata/a.txt": 10, "barata/b.txt": 10, "cara/c.txt": 1000, "cara/alvo.txt": 1000},
    )
    searcher = FakeSearcher({"alvo.txt"})
    outcome, counters = run_once(root, UCS, searcher)

    assert outcome.first.path.name == "alvo.txt"
    assert [p.name for p in outcome.opened_paths] == ["r", "barata", "cara"]
    # Arquivos de cada pasta são lidos em ordem alfabética: alvo.txt vem antes de c.txt.
    assert searcher.calls == ["a.txt", "b.txt", "alvo.txt"]
    assert counters.files_read == 3
    assert counters.bytes_read == 20 + 1000
    # g soma o custo de abrir a pasta inteira (2000 bytes), a raiz não tem arquivos.
    assert outcome.first.g == 2000


def test_stage3_stops_reading_at_first_match(tmp_path):
    root = make_tree(tmp_path / "r", {"p/a.txt": 1, "p/b.txt": 1, "p/c.txt": 1})
    searcher = FakeSearcher({"a.txt"})
    _, counters = run_once(root, BFS, searcher)
    assert searcher.calls == ["a.txt"]
    assert counters.files_read == 1


def test_stage3_not_found_reads_everything(tmp_path):
    root = make_tree(tmp_path / "r", {"p/a.txt": 1, "q/b.txt": 1})
    outcome, counters = run_once(root, UCS, FakeSearcher(set()))
    assert not outcome.found
    assert counters.files_read == 2


def test_run_stage3_public_api_with_injected_searcher(tmp_path):
    root = make_tree(tmp_path / "r", {"p/a.txt": 1, "q/b.txt": 1})
    (record,) = run_stage3(root, "x", (UCS,), repeats=1, searcher=FakeSearcher({"b.txt"}))
    assert record.outcome.first.path.name == "b.txt"
    assert record.counters.files_read == 2


def test_astar_prunes_useless_folders_in_synthetic_scenario(tmp_path):
    root = tmp_path / "corpus"
    target = build_pruning_scenario(root)

    ucs, astar = run_stage3(root, KEYWORD, (UCS, ASTAR), weight=WEIGHT_BYTES, repeats=1)

    assert ucs.outcome.first.path == astar.outcome.first.path == target
    assert astar.outcome.expanded < ucs.outcome.expanded
    assert astar.counters.files_read < ucs.counters.files_read
    assert astar.counters.bytes_read < ucs.counters.bytes_read
    assert "_imagens_auxiliares" not in [p.name for p in astar.outcome.opened_paths]
    assert "_imagens_auxiliares" in [p.name for p in ucs.outcome.opened_paths]


def test_astar_total_cost_includes_heuristic(tmp_path):
    root = tmp_path / "corpus"
    build_pruning_scenario(root)
    ucs, astar = run_stage3(root, KEYWORD, (UCS, ASTAR), weight=WEIGHT_BYTES, repeats=1)
    assert ucs.outcome.first.f == ucs.outcome.first.g
    assert astar.outcome.first.f == pytest.approx(astar.outcome.first.g + astar.outcome.first.h)
    assert astar.outcome.first.h > 0
