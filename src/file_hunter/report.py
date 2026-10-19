"""Formatação dos resultados como tabelas Markdown alinhadas.

As tabelas ficam legíveis no terminal e renderizam direto no GitHub.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from .heuristics import NameHeuristic
from .models import Node, RunRecord

NOT_FOUND = "não encontrado"
FIRST_N = 10


def number(value: float, decimals: int = 0) -> str:
    """Formata com ponto de milhar e vírgula decimal, como no Brasil."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "\0").replace(".", ",").replace("\0", ".")


def human_bytes(size_bytes: float) -> str:
    """Tamanho em B, KiB ou MiB, conforme a ordem de grandeza."""
    if size_bytes < 1024:
        return f"{number(size_bytes)} B"
    if size_bytes < 1024 * 1024:
        return f"{number(size_bytes / 1024, 1)} KiB"
    return f"{number(size_bytes / (1024 * 1024), 2)} MiB"


def display_path(path: Path) -> str:
    """Caminho no formato ./pasta/arquivo quando está dentro do diretório atual."""
    relative = Path(os.path.relpath(path))
    if relative.parts and relative.parts[0] == "..":
        return path.resolve().as_posix()
    return f"./{relative.as_posix()}"


def table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Tabela Markdown com colunas alinhadas à esquerda."""
    cells = [[str(cell).replace("|", "\\|") for cell in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in cells:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def line(values: Sequence[str]) -> str:
        padded = (value.ljust(width) for value, width in zip(values, widths, strict=True))
        return "| " + " | ".join(padded) + " |"

    separator = "| " + " | ".join("-" * width for width in widths) + " |"
    return "\n".join([line(headers), separator, *(line(row) for row in cells)])


def _first_path(record: RunRecord) -> str:
    first = record.outcome.first
    return display_path(first.path) if first else NOT_FOUND


# ---------------------------------------------------------------- etapa 1


def stage1_report(root: Path, records: Sequence[RunRecord], *, full_list: bool = False) -> str:
    parts = [
        f"### Etapa 1: varredura completa de {display_path(root)}",
        "",
        table(
            [
                "Algoritmo",
                "Pastas abertas",
                "Arquivos encontrados",
                "Itens examinados",
                "Tempo (ms)",
                "Pico de memória (KB)",
                "Pico da fronteira",
            ],
            [
                [
                    r.algorithm,
                    number(r.outcome.expanded),
                    number(len(r.outcome.discoveries)),
                    number(r.counters.items_examined),
                    number(r.measurement.elapsed_ms, 3),
                    number(r.measurement.peak_memory_kb, 1),
                    number(r.outcome.peak_frontier),
                ]
                for r in records
            ],
        ),
        "",
        f"#### Ordem de descoberta: {FIRST_N} primeiros arquivos",
        "",
        _side_by_side(records, [_discovered(r)[:FIRST_N] for r in records]),
        "",
        "#### Ordem de abertura das pastas",
        "",
        _side_by_side(records, [r.outcome.opened_paths for r in records]),
    ]
    if full_list:
        parts += [
            "",
            "#### Caminho completo de cada arquivo encontrado",
            "",
            _side_by_side(records, [_discovered(r) for r in records]),
        ]
    parts += ["", *_stage1_analysis(records)]
    return "\n".join(parts)


def _discovered(record: RunRecord) -> list[Path]:
    return [d.path for d in record.outcome.discoveries]


def _side_by_side(records: Sequence[RunRecord], columns: Sequence[Sequence[Path]]) -> str:
    height = max((len(column) for column in columns), default=0)
    rows = []
    for index in range(height):
        row = [str(index + 1)]
        for column in columns:
            row.append(display_path(column[index]) if index < len(column) else "")
        rows.append(row)
    return table(["#", *(r.algorithm for r in records)], rows)


def _stage1_analysis(records: Sequence[RunRecord]) -> list[str]:
    lines = ["Leitura dos números:", ""]
    opened = {r.outcome.expanded for r in records}
    found = {len(r.outcome.discoveries) for r in records}
    if len(opened) == 1 and len(found) == 1:
        lines.append(
            f"- Todos os algoritmos abriram {number(opened.pop())} pastas e encontraram "
            f"{number(found.pop())} arquivos. Em uma varredura completa a ordem de visita "
            "não muda o total de trabalho."
        )
    firsts = {r.outcome.first.path.name for r in records if r.outcome.first}
    if len(firsts) == 1:
        lines.append(f"- Todos acharam primeiro {firsts.pop()}.")
    else:
        for r in records:
            if r.outcome.first:
                lines.append(f"- {r.algorithm} achou primeiro {r.outcome.first.path.name}.")
    lines += _divergence_lines(records)
    peaks = ", ".join(f"{r.algorithm} {number(r.outcome.peak_frontier)}" for r in records)
    lines.append(
        f"- Pico de nós na fronteira: {peaks}. A fila do BFS guarda a camada inteira, "
        "enquanto a pilha do DFS guarda só os irmãos pendentes do caminho atual."
    )
    return lines


def _divergence_lines(records: Sequence[RunRecord]) -> list[str]:
    """Aponta a primeira posição em que a ordem de descoberta de dois algoritmos difere."""
    if len(records) < 2:
        return []
    first, second = records[0], records[1]
    for index, (a, b) in enumerate(zip(first.outcome.discoveries, second.outcome.discoveries, strict=False)):
        if a.path != b.path:
            position = index + 1
            note = ""
            if position > FIRST_N:
                note = f" As {FIRST_N} primeiras posições são idênticas."
            return [
                f"- As ordens divergem na posição {position}: {first.algorithm} achou "
                f"{a.path.name} e {second.algorithm} achou {b.path.name}.{note}"
            ]
    return [f"- {first.algorithm} e {second.algorithm} descobriram os arquivos na mesma ordem."]


# ---------------------------------------------------------------- etapa 2


def stage2_report(
    root: Path,
    keyword: str,
    records: Sequence[RunRecord],
    heuristic: NameHeuristic,
    cost_parts: Sequence[tuple[Path, float]] | None = None,
) -> str:
    parts = [
        f'### Etapa 2: arquivo com "{keyword}" no nome em {display_path(root)}',
        "",
        table(
            [
                "Algoritmo",
                "Alvo",
                "Caminho",
                "Pastas abertas",
                "Itens examinados",
                "Custo acumulado g(n)",
                "Tempo (ms)",
                "Memória (KB)",
            ],
            [
                [
                    r.algorithm,
                    f'"{keyword}"',
                    _first_path(r),
                    number(r.outcome.expanded),
                    number(r.counters.items_examined),
                    number(r.outcome.first.g) if r.outcome.first else "-",
                    number(r.measurement.elapsed_ms, 3),
                    number(r.measurement.peak_memory_kb, 1),
                ]
                for r in records
            ],
        ),
        "",
        "Custo de aresta: itens (arquivos + subpastas) da pasta aberta. "
        "g(n) é a soma desse custo nas pastas do caminho da raiz até o arquivo.",
        f"Heurística do A*: {heuristic.describe('itens')}",
    ]
    parts += ["", *_stage2_analysis(keyword, records, cost_parts)]
    return "\n".join(parts)


def _stage2_analysis(
    keyword: str,
    records: Sequence[RunRecord],
    cost_parts: Sequence[tuple[Path, float]] | None,
) -> list[str]:
    lines = ["Leitura dos números:", ""]
    by_name = {r.algorithm: r for r in records}
    if not any(r.outcome.found for r in records):
        lines.append(
            f'- Nenhum arquivo tem "{keyword}" no nome. Os algoritmos esgotaram a árvore, '
            "então o número de pastas abertas é o total."
        )
        return lines
    ucs = by_name.get("UCS")
    if ucs and ucs.outcome.first and cost_parts:
        breakdown = " + ".join(f"{number(c)} ({path.name})" for path, c in cost_parts)
        lines.append(f"- g(n) do UCS no nó do achado: {number(ucs.outcome.first.g)} = {breakdown}.")
    informed = [r for r in records if r.algorithm in ("UCS", "A*") and r.outcome.first]
    blind = [r for r in records if r.algorithm in ("BFS", "DFS") and r.outcome.first]
    if informed and blind:
        best = min(r.outcome.first.g for r in informed)
        worst = max(r.outcome.first.g for r in blind)
        lines.append(f"- Menor g(n) entre UCS e A*: {number(best)}. Maior entre BFS e DFS: {number(worst)}.")
    astar = by_name.get("A*")
    if ucs and astar:
        lines.append(_pruning_sentence(ucs, astar, "pastas"))
    return lines


def _pruning_sentence(ucs: RunRecord, astar: RunRecord, unit: str) -> str:
    saved = ucs.outcome.expanded - astar.outcome.expanded
    if saved > 0:
        return (
            f"- O A* abriu {number(astar.outcome.expanded)} {unit} contra "
            f"{number(ucs.outcome.expanded)} do UCS, uma poda de {number(saved)}."
        )
    if saved < 0:
        return (
            f"- O A* abriu {number(-saved)} {unit} a mais que o UCS "
            f"({number(astar.outcome.expanded)} contra {number(ucs.outcome.expanded)}). "
            "Neste cenário a heurística não ajudou."
        )
    return f"- O A* abriu o mesmo número de {unit} que o UCS ({number(ucs.outcome.expanded)}), sem poda neste cenário."


# ---------------------------------------------------------------- etapa 3


def stage3_report(
    root: Path,
    keyword: str,
    records: Sequence[RunRecord],
    heuristic: NameHeuristic,
    *,
    trace: bool = False,
) -> str:
    parts = [
        f'### Etapa 3: palavra "{keyword}" no conteúdo dos arquivos em {display_path(root)}',
        "",
        table(
            [
                "Algoritmo",
                "Palavra no conteúdo",
                "Caminho",
                "Pastas abertas",
                "Arquivos lidos do disco",
                "Bytes lidos",
                "g(n)",
                "h(n)",
                "Custo total f(n)",
                "Tempo (ms)",
                "Memória (KB)",
            ],
            [_stage3_row(keyword, r) for r in records],
        ),
        "",
        "Custo de aresta: total de bytes dos arquivos da pasta aberta. g(n) soma esse custo "
        "nas pastas do caminho; f(n) = g(n) + h(n) no nó onde a palavra foi achada.",
        f"Heurística do A*: {heuristic.describe('bytes', human_bytes(heuristic.weight))}",
        "",
        "#### Pastas abertas por algoritmo",
        "",
        table(
            ["#", *(f"{r.algorithm}: pasta (g, h)" if r.informed else f"{r.algorithm}: pasta" for r in records)],
            _trace_rows(records),
        ),
    ]
    if trace:
        for r in (r for r in records if r.informed):
            title = f"#### Traço do {r.algorithm}: nós abertos com g, h e f"
            parts += ["", title, "", _trace_table(r.outcome.opened)]
    parts += ["", *_stage3_analysis(records)]
    return "\n".join(parts)


def _stage3_row(keyword: str, record: RunRecord) -> list[str]:
    first = record.outcome.first
    return [
        record.algorithm,
        f'"{keyword}"',
        _first_path(record),
        number(record.outcome.expanded),
        number(record.counters.files_read),
        f"{number(record.counters.bytes_read)} ({human_bytes(record.counters.bytes_read)})",
        number(first.g) if first else "-",
        number(first.h) if first else "-",
        number(first.f) if first else "-",
        number(record.measurement.elapsed_ms, 1),
        number(record.measurement.peak_memory_kb, 1),
    ]


def _node_cell(node: Node, informed: bool) -> str:
    if not informed:
        return node.path.name
    return f"{node.path.name} ({human_bytes(node.g)}, {human_bytes(node.h)})"


def _trace_rows(records: Sequence[RunRecord]) -> list[list[str]]:
    height = max((r.outcome.expanded for r in records), default=0)
    rows = []
    for index in range(height):
        row = [str(index + 1)]
        for r in records:
            row.append(_node_cell(r.outcome.opened[index], r.informed) if index < r.outcome.expanded else "")
        rows.append(row)
    return rows


def _trace_table(nodes: Sequence[Node]) -> str:
    return table(
        ["#", "Pasta", "g(n) bytes", "h(n) bytes", "f(n) bytes"],
        [[str(i), display_path(n.path), number(n.g), number(n.h), number(n.f)] for i, n in enumerate(nodes, start=1)],
    )


def _stage3_analysis(records: Sequence[RunRecord]) -> list[str]:
    lines = ["Leitura dos números:", ""]
    by_name = {r.algorithm: r for r in records}
    ucs, astar = by_name.get("UCS"), by_name.get("A*")
    if ucs and astar:
        lines.append(_pruning_sentence(ucs, astar, "pastas"))
        read_diff = ucs.counters.files_read - astar.counters.files_read
        bytes_diff = ucs.counters.bytes_read - astar.counters.bytes_read
        if read_diff:
            who = "A*" if read_diff > 0 else "UCS"
            lines.append(
                f"- Arquivos lidos do disco: UCS {number(ucs.counters.files_read)}, "
                f"A* {number(astar.counters.files_read)}. O {who} leu "
                f"{number(abs(read_diff))} arquivos e {human_bytes(abs(bytes_diff))} a menos."
            )
        else:
            lines.append(
                f"- Os dois leram {number(ucs.counters.files_read)} arquivos ({human_bytes(ucs.counters.bytes_read)})."
            )
        if ucs.outcome.first and astar.outcome.first and ucs.outcome.first.path != astar.outcome.first.path:
            lines.append(
                "- Os caminhos achados são diferentes. A heurística não é admissível, então o A* "
                "não garante o menor custo. Compare o g(n) das duas linhas."
            )
    return lines
