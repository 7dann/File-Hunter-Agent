from __future__ import annotations

import pytest

from file_hunter.heuristics import (
    NameHeuristic,
    jaccard_similarity,
    levenshtein,
    levenshtein_distance,
    name_distance,
    ngram_distance,
    ngrams,
)
from file_hunter.text import normalize, tokenize


def test_normalize_removes_accents_case_and_separators():
    assert normalize("Guia Rápido_ Minimização-2024.PDF") == "guia rapido minimizacao 2024 pdf"


def test_tokenize_empty_and_symbols():
    assert tokenize("___") == []
    assert tokenize("Fontes GD") == ["fontes", "gd"]


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("", "", 0),
        ("abc", "", 3),
        ("", "abc", 3),
        ("kitten", "sitting", 3),
        ("livro", "livros", 1),
        ("pedagogia", "pedagogicos", 3),
        ("abc", "abc", 0),
    ],
)
def test_levenshtein_known_values(a, b, expected):
    assert levenshtein(a, b) == expected
    assert levenshtein(b, a) == expected


def test_levenshtein_distance_is_normalized():
    assert levenshtein_distance("", "") == 0.0
    assert levenshtein_distance("abc", "xyz") == 1.0
    assert levenshtein_distance("livro", "livros") == pytest.approx(1 / 6)


def test_ngrams_and_jaccard():
    assert ngrams("ab") == {" ab", "ab "}
    assert jaccard_similarity(set(), set()) == 1.0
    assert jaccard_similarity({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)
    assert ngram_distance("livro", "livro") == 0.0
    assert 0.0 < ngram_distance("livro", "livros") < 1.0


def test_promising_folder_is_closer_than_useless_folder():
    near = name_distance("pedagogia", "_planos_pedagogicos_2024")
    far = name_distance("pedagogia", "_imagens_auxiliares")
    assert near < 0.35
    assert far > 0.6
    assert near < far


def test_name_distance_is_zero_when_term_is_inside_name():
    assert name_distance("livro", "LIVRO SISTEMAS-DIGITAIS.pdf") == 0.0
    assert name_distance("livro", "Meu_Livro_Novo.txt") == 0.0


def test_name_distance_handles_empty_inputs():
    assert name_distance("", "abc") == 1.0
    assert name_distance("abc", "___") == 1.0


def test_name_heuristic_scales_distance_by_weight():
    heuristic = NameHeuristic("livro", weight=10.0)
    assert heuristic.estimate("livre") == pytest.approx(10.0 / 5)
    assert heuristic.estimate("Livro GTI.pdf") == 0.0


def test_name_heuristic_validates_arguments():
    with pytest.raises(ValueError, match="Métrica"):
        NameHeuristic("x", 1.0, "cosseno")
    with pytest.raises(ValueError, match="negativo"):
        NameHeuristic("x", -1.0)


def test_heuristic_description_mentions_formula_parts():
    text = NameHeuristic("livro", 10.0).describe("itens")
    assert "h(n)" in text
    assert "Levenshtein" in text
    assert "10 itens" in text
