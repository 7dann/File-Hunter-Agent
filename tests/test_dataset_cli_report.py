from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from file_hunter.cli import main
from file_hunter.dataset import DatasetError, extract_dataset
from file_hunter.measure import profile
from file_hunter.report import human_bytes, number, table
from helpers import make_tree


def make_zip(path: Path, entries: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as bundle:
        for name, data in entries.items():
            bundle.writestr(name, data)
    return path


def test_extract_strips_single_top_level_folder(tmp_path):
    archive = make_zip(tmp_path / "f.zip", {"Fontes/A/x.pdf": b"1", "Fontes/B/y.pdf": b"2"})
    count = extract_dataset(archive, tmp_path / "docencia" / "fontes")
    assert count == 2
    assert (tmp_path / "docencia" / "fontes" / "A" / "x.pdf").read_bytes() == b"1"


def test_extract_keeps_structure_without_common_prefix(tmp_path):
    archive = make_zip(tmp_path / "f.zip", {"A/x.pdf": b"1", "B/y.pdf": b"2"})
    extract_dataset(archive, tmp_path / "out")
    assert (tmp_path / "out" / "B" / "y.pdf").exists()


def test_extract_rejects_path_traversal(tmp_path):
    archive = make_zip(tmp_path / "f.zip", {"../fora.txt": b"x", "Fontes/ok.txt": b"y"})
    with pytest.raises(DatasetError, match="insegura"):
        extract_dataset(archive, tmp_path / "out")
    assert not (tmp_path / "fora.txt").exists()


def test_extract_refuses_non_empty_destination_without_force(tmp_path):
    archive = make_zip(tmp_path / "f.zip", {"Fontes/a.txt": b"1"})
    destination = tmp_path / "out"
    extract_dataset(archive, destination)
    with pytest.raises(DatasetError, match="--force"):
        extract_dataset(archive, destination)
    assert extract_dataset(archive, destination, force=True) == 1


def test_extract_missing_archive(tmp_path):
    with pytest.raises(DatasetError, match="não encontrado"):
        extract_dataset(tmp_path / "nada.zip", tmp_path / "out")


def test_number_uses_brazilian_format():
    assert number(1234567) == "1.234.567"
    assert number(1234.5, 2) == "1.234,50"
    assert number(0) == "0"


def test_human_bytes_scales():
    assert human_bytes(512) == "512 B"
    assert human_bytes(2048) == "2,0 KiB"
    assert human_bytes(5 * 1024 * 1024) == "5,00 MiB"


def test_table_is_aligned_and_escapes_pipes():
    text = table(["a", "bb"], [["1", "x|y"], ["222", "z"]])
    lines = text.splitlines()
    assert len({len(line) for line in lines}) == 1
    assert "x\\|y" in text


def test_profile_returns_result_and_positive_measurements():
    result, measurement = profile(lambda: [0] * 10_000, repeats=3)
    assert len(result) == 10_000
    assert measurement.elapsed_ms >= 0
    assert measurement.peak_memory_kb > 0


def test_profile_rejects_zero_repeats():
    with pytest.raises(ValueError):
        profile(lambda: None, repeats=0)


def test_cli_stage1_prints_table_and_writes_output(sample_root, tmp_path, capsys):
    out = tmp_path / "saida" / "etapa1.md"
    code = main(["stage1", "--root", str(sample_root), "--repeats", "1", "--output", str(out), "--full-list"])
    printed = capsys.readouterr().out
    assert code == 0
    assert "| BFS" in printed and "| DFS" in printed
    assert "Caminho completo" in printed
    assert out.read_text(encoding="utf-8").strip() == printed.strip()


def test_cli_stage2_multiple_keywords(sample_root, capsys):
    code = main(["stage2", "--root", str(sample_root), "--repeats", "1", "-k", "livro", "-k", "zzz"])
    printed = capsys.readouterr().out
    assert code == 0
    assert printed.count("### Etapa 2") == 2
    assert "não encontrado" in printed
    assert "livro_b.txt" in printed


def test_cli_stage3_on_text_tree(tmp_path, capsys):
    root = make_tree(tmp_path / "r", {"x/a.txt": "nada", "y/b.txt": "tem algoritmo aqui"})
    code = main(["stage3", "--root", str(root), "-k", "algoritmo", "--trace"])
    printed = capsys.readouterr().out
    assert code == 0
    assert "b.txt" in printed
    assert "Traço do A*" in printed


def test_cli_demo_pruning_shows_reduction(capsys):
    code = main(["demo-pruning"])
    printed = capsys.readouterr().out
    assert code == 0
    assert "poda de" in printed


def test_cli_missing_root_returns_error_code(tmp_path, capsys):
    code = main(["stage1", "--root", str(tmp_path / "nada")])
    assert code == 2
    assert "erro:" in capsys.readouterr().err


def test_cli_extract(tmp_path, capsys):
    archive = make_zip(tmp_path / "f.zip", {"Fontes/a.txt": b"1"})
    code = main(["extract", str(archive), "--dest", str(tmp_path / "d")])
    assert code == 0
    assert "1 arquivos extraídos" in capsys.readouterr().out


def test_cli_rejects_unknown_algorithm(sample_root):
    with pytest.raises(SystemExit):
        main(["stage2", "--root", str(sample_root), "--algorithms", "dijkstra"])


def test_cli_trace_only_for_informed_algorithms(tmp_path, capsys):
    root = make_tree(tmp_path / "r", {"x/a.txt": "nada", "y/b.txt": "tem algoritmo aqui"})
    main(["stage3", "--root", str(root), "--algorithms", "bfs", "ucs", "astar", "--trace"])
    printed = capsys.readouterr().out
    assert "Traço do UCS" in printed and "Traço do A*" in printed
    assert "Traço do BFS" not in printed
