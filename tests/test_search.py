from __future__ import annotations

import random
from pathlib import Path

import pytest

from file_hunter.algorithms import ASTAR, BFS, DFS, UCS, get_algorithms
from file_hunter.engine import run_search
from file_hunter.heuristics import NameHeuristic
from file_hunter.models import Counters
from file_hunter.problems import ITEMS_COST, NameKeywordProblem
from file_hunter.stages import explain_cost, run_stage1, run_stage2
from helpers import make_tree


def names(paths):
    return [p.name for p in paths]


def test_stage1_bfs_and_dfs_find_every_file_in_different_orders(sample_root):
    bfs, dfs = run_stage1(sample_root, repeats=1)

    assert bfs.outcome.expanded == dfs.outcome.expanded == 5
    assert len(bfs.outcome.discoveries) == len(dfs.outcome.discoveries) == 12
    assert {d.path for d in bfs.outcome.discoveries} == {d.path for d in dfs.outcome.discoveries}

    bfs_order = names(d.path for d in bfs.outcome.discoveries)
    dfs_order = names(d.path for d in dfs.outcome.discoveries)
    assert bfs_order[0] == "top.txt"  # BFS atende o nível 1 antes de descer
    assert dfs_order[:2] == ["a1.txt", "livro_b.txt"]  # DFS desce em a_docs primeiro
    assert dfs_order[-1] == "top.txt"
    assert bfs_order != dfs_order


def test_stage1_opened_order_and_items_examined(sample_root):
    bfs, dfs = run_stage1(sample_root, repeats=1)
    assert names(bfs.outcome.opened_paths) == ["root", "a_docs", "b_deep", "c_big", "c_inner"]
    assert names(dfs.outcome.opened_paths) == ["root", "a_docs", "b_deep", "c_inner", "c_big"]
    # 4 itens na raiz + 2 + 2 + 3 + 5
    assert bfs.counters.items_examined == dfs.counters.items_examined == 16
    assert bfs.counters.files_visited == 12


def test_stage1_peak_frontier_is_larger_for_bfs(sample_root):
    bfs, dfs = run_stage1(sample_root, repeats=1)
    assert bfs.outcome.peak_frontier >= dfs.outcome.peak_frontier


def test_stage2_keyword_results_per_algorithm(sample_root):
    records = {r.algorithm: r for r in run_stage2(sample_root, "LIVRO", repeats=1)}

    for label in ("BFS", "DFS", "UCS", "A*"):
        assert "livro" in records[label].outcome.first.path.name

    # Raiz com 4 itens + a_docs com 2 itens.
    assert records["UCS"].outcome.first.path.name == "livro_b.txt"
    assert records["UCS"].outcome.first.g == 6
    assert records["UCS"].outcome.expanded == 2
    assert records["DFS"].outcome.expanded == 2
    assert records["BFS"].outcome.expanded == 4


def test_stage2_reports_the_same_g_for_blind_and_informed_algorithms(sample_root):
    for record in run_stage2(sample_root, "livro", repeats=1):
        first = record.outcome.first
        parts = explain_cost(sample_root, first.path, ITEMS_COST)
        assert first.g == sum(cost for _, cost in parts)


def test_stage2_keyword_missing_explores_everything(sample_root):
    for record in run_stage2(sample_root, "inexistente", repeats=1):
        assert not record.outcome.found
        assert record.outcome.expanded == 5


def test_accent_and_case_insensitive_name_match(tmp_path):
    root = make_tree(tmp_path / "r", {"d/Relatório Parcial.txt": 1})
    (record,) = run_stage2(root, "relatorio", get_algorithms(["bfs"]), repeats=1)
    assert record.outcome.found


def _random_tree(seed: int, root: Path) -> None:
    rng = random.Random(seed)
    spec: dict[str, int | str] = {}
    folders = ["."]
    for index in range(rng.randint(3, 9)):
        parent = rng.choice(folders)
        folder = f"d{index}" if parent == "." else f"{parent}/d{index}"
        folders.append(folder)
    for folder in folders:
        for index in range(rng.randint(0, 5)):
            name = f"{'livro_' if rng.random() < 0.2 else 'f'}{index}.txt"
            spec[f"{folder}/{name}" if folder != "." else name] = 1
    spec.setdefault("zz.txt", 1)
    make_tree(root, spec)


def _min_matching_cost(root: Path, keyword: str) -> float | None:
    counters = Counters()
    problem = NameKeywordProblem(root, counters, keyword, ITEMS_COST)
    costs = []
    for path in root.rglob("*"):
        if path.is_file() and keyword in path.name:
            costs.append(sum(c for _, c in problem.cost_breakdown(path, is_directory=False)))
    return min(costs) if costs else None


@pytest.mark.parametrize("seed", range(25))
def test_ucs_finds_the_cheapest_target_on_random_trees(tmp_path, seed):
    root = tmp_path / "tree"
    _random_tree(seed, root)
    expected = _min_matching_cost(root, "livro")

    ucs = run_stage2(root, "livro", get_algorithms(["ucs"]), repeats=1)[0]
    if expected is None:
        assert not ucs.outcome.found
    else:
        assert ucs.outcome.first.g == expected
        # Nenhum algoritmo acha um alvo mais barato que o UCS.
        for other in run_stage2(root, "livro", repeats=1):
            assert other.outcome.first.g >= expected


@pytest.mark.parametrize("seed", range(10))
def test_astar_with_zero_weight_behaves_like_ucs(tmp_path, seed):
    root = tmp_path / "tree"
    _random_tree(seed, root)
    ucs, astar = run_stage2(root, "livro", get_algorithms(["ucs", "astar"]), weight=0.0, repeats=1)
    assert names(ucs.outcome.opened_paths) == names(astar.outcome.opened_paths)
    assert ucs.outcome.found == astar.outcome.found


def test_informed_problem_node_cost_matches_recomputed_cost(sample_root):
    counters = Counters()
    problem = NameKeywordProblem(sample_root, counters, "livro", ITEMS_COST, NameHeuristic("livro", 1.0))
    outcome = run_search(problem, ASTAR.make_frontier(), stop_at_first_goal=True)
    goal = outcome.first
    assert goal is not None
    assert goal.g == sum(c for _, c in problem.cost_breakdown(goal.path, is_directory=False))


def test_each_run_starts_with_fresh_counters(sample_root):
    first = run_stage1(sample_root, (BFS,), repeats=1)[0]
    second = run_stage1(sample_root, (BFS,), repeats=1)[0]
    assert first.counters == second.counters


def test_unknown_algorithm_is_rejected():
    with pytest.raises(ValueError, match="desconhecido"):
        get_algorithms(["dijkstra"])


def test_missing_root_gives_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="extract"):
        run_stage1(tmp_path / "nao_existe")


def test_symlinks_are_ignored_and_do_not_loop(tmp_path):
    root = make_tree(tmp_path / "r", {"a/f.txt": 1})
    (root / "a" / "loop").symlink_to(root, target_is_directory=True)
    bfs, dfs = run_stage1(root, (BFS, DFS), repeats=1)
    assert len(bfs.outcome.discoveries) == len(dfs.outcome.discoveries) == 1


def test_empty_tree_is_handled(tmp_path):
    root = tmp_path / "vazio"
    root.mkdir()
    bfs = run_stage1(root, (BFS,), repeats=1)[0]
    assert bfs.outcome.expanded == 1
    assert not bfs.outcome.found


def test_ucs_label_in_registry():
    assert [a.label for a in get_algorithms(["bfs", "dfs", "ucs", "astar"])] == ["BFS", "DFS", "UCS", "A*"]
    assert UCS.uses_heuristic is False and ASTAR.uses_heuristic is True
