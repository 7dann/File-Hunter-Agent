from __future__ import annotations

from pathlib import Path

import pytest

from helpers import make_tree

SAMPLE_TREE: dict[str, int | str] = {
    "a_docs/a1.txt": 10,
    "a_docs/livro_b.txt": 10,
    "b_deep/z.txt": 10,
    "b_deep/c_inner/livro_inner.txt": 10,
    "b_deep/c_inner/x.txt": 10,
    "b_deep/c_inner/y.txt": 10,
    "c_big/f1.txt": 10,
    "c_big/f2.txt": 10,
    "c_big/f3.txt": 10,
    "c_big/f4.txt": 10,
    "c_big/f5.txt": 10,
    "top.txt": 10,
}


@pytest.fixture()
def sample_root(tmp_path: Path) -> Path:
    """Raiz com 4 itens; a_docs tem 2, b_deep tem 2, c_inner tem 3 e c_big tem 5."""
    return make_tree(tmp_path / "root", SAMPLE_TREE)
