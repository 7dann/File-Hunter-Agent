from __future__ import annotations

from pathlib import Path

from file_hunter.frontiers import FifoFrontier, LifoFrontier, PriorityFrontier, astar_key, ucs_key
from file_hunter.models import Node, NodeKind


def node(name: str, g: float = 0.0, h: float = 0.0, kind: NodeKind = NodeKind.DIRECTORY) -> Node:
    return Node(Path(name), kind, 0, g, h)


def drain(frontier) -> list[str]:
    names = []
    while frontier:
        names.append(frontier.pop().name)
    return names


def test_fifo_returns_oldest_first():
    frontier = FifoFrontier()
    frontier.extend([node("a"), node("b"), node("c")])
    assert drain(frontier) == ["a", "b", "c"]


def test_lifo_returns_newest_first_but_keeps_sibling_order_on_extend():
    frontier = LifoFrontier()
    frontier.push(node("x"))
    assert frontier.pop().name == "x"
    frontier.extend([node("a"), node("b"), node("c")])
    assert drain(frontier) == ["a", "b", "c"]


def test_lifo_push_is_plain_stack():
    frontier = LifoFrontier()
    for name in "abc":
        frontier.push(node(name))
    assert drain(frontier) == ["c", "b", "a"]


def test_ucs_orders_by_g_and_breaks_ties_by_insertion():
    frontier = PriorityFrontier(ucs_key)
    frontier.extend([node("far", g=9), node("near1", g=1), node("near2", g=1), node("mid", g=5)])
    assert drain(frontier) == ["near1", "near2", "mid", "far"]


def test_ucs_prefers_files_over_directories_on_ties():
    frontier = PriorityFrontier(ucs_key)
    frontier.push(node("dir", g=3))
    frontier.push(node("file", g=3, kind=NodeKind.FILE))
    assert drain(frontier) == ["file", "dir"]


def test_astar_orders_by_f_and_uses_h_to_break_ties():
    frontier = PriorityFrontier(astar_key)
    frontier.extend(
        [
            node("a", g=2, h=8),  # f = 10
            node("b", g=6, h=1),  # f = 7
            node("c", g=5, h=2),  # f = 7, h maior que b
        ]
    )
    assert drain(frontier) == ["b", "c", "a"]


def test_informed_flags():
    assert not FifoFrontier().informed
    assert not LifoFrontier().informed
    assert PriorityFrontier(ucs_key).informed


def test_empty_frontier_is_falsy():
    frontier = PriorityFrontier(ucs_key)
    assert not frontier
    frontier.push(node("a"))
    assert frontier and len(frontier) == 1
