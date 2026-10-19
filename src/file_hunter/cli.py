"""Interface de linha de comando do File Hunter Agent."""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .algorithms import ALGORITHMS, ASTAR, UCS, Algorithm, get_algorithms
from .dataset import DatasetError, extract_dataset
from .heuristics import METRICS, NameHeuristic
from .problems import ITEMS_COST
from .report import stage1_report, stage2_report, stage3_report
from .scenarios import KEYWORD as SCENARIO_KEYWORD
from .scenarios import WEIGHT_BYTES as SCENARIO_WEIGHT
from .scenarios import build_pruning_scenario
from .stages import (
    DEFAULT_CONTENT_WEIGHT,
    DEFAULT_NAME_WEIGHT,
    STAGE2_ALGORITHMS,
    STAGE3_ALGORITHMS,
    explain_cost,
    run_stage1,
    run_stage2,
    run_stage3,
)

DEFAULT_ROOT = Path("docencia/fontes")
MIB = 1024 * 1024
DEFAULT_STAGE2_KEYWORD = "livro"
DEFAULT_STAGE3_KEYWORD = "algoritmo"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="file-hunter",
        description="Agente que localiza arquivos em uma árvore de diretórios com BFS, DFS, UCS e A*.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="pasta raiz da busca (padrão: %(default)s)")
    common.add_argument("--output", type=Path, help="grava o relatório também neste arquivo")
    common.add_argument("--repeats", type=int, help="passadas cronometradas por algoritmo (a mediana é reportada)")

    metric = argparse.ArgumentParser(add_help=False)
    metric.add_argument(
        "--metric",
        choices=sorted(METRICS),
        default="levenshtein",
        help="distância de nomes usada na heurística (padrão: %(default)s)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    extract = sub.add_parser("extract", help="extrai o zip do professor em docencia/fontes")
    extract.add_argument("archive", type=Path, help="caminho do arquivo .zip")
    extract.add_argument("--dest", type=Path, default=DEFAULT_ROOT, help="destino (padrão: %(default)s)")
    extract.add_argument("--force", action="store_true", help="substitui o destino se ele já existir")

    stage1 = sub.add_parser("stage1", parents=[common], help="etapa 1: varredura completa, BFS contra DFS")
    stage1.add_argument("--full-list", action="store_true", help="lista o caminho de todos os arquivos achados")

    stage2 = sub.add_parser(
        "stage2", parents=[common, metric], help="etapa 2: palavra no nome do arquivo, BFS, DFS, UCS e A*"
    )
    stage2.add_argument(
        "-k",
        "--keyword",
        action="append",
        help=f'palavra-chave; repita para várias (padrão: "{DEFAULT_STAGE2_KEYWORD}")',
    )
    stage2.add_argument("--weight", type=float, default=DEFAULT_NAME_WEIGHT, help="peso de h(n) em itens")
    stage2.add_argument("--algorithms", nargs="+", choices=list(ALGORITHMS), help="algoritmos a executar")

    stage3 = sub.add_parser("stage3", parents=[common, metric], help="etapa 3: palavra no conteúdo, UCS contra A*")
    stage3.add_argument(
        "-k", "--keyword", default=DEFAULT_STAGE3_KEYWORD, help="palavra no conteúdo (padrão: %(default)s)"
    )
    stage3.add_argument("--weight-mib", type=float, default=DEFAULT_CONTENT_WEIGHT / MIB, help="peso de h(n) em MiB")
    stage3.add_argument("--algorithms", nargs="+", choices=list(ALGORITHMS), help="algoritmos a executar")
    stage3.add_argument("--trace", action="store_true", help="mostra g, h e f de cada pasta aberta")

    everything = sub.add_parser("all", parents=[common], help="executa as três etapas com os parâmetros do enunciado")
    everything.add_argument("--full-list", action="store_true", help="lista o caminho de todos os arquivos na etapa 1")

    demo = sub.add_parser(
        "demo-pruning",
        parents=[metric],
        help="etapa 3 sobre uma árvore sintética onde a poda do A* aparece",
    )
    demo.add_argument("--output", type=Path, help="grava o relatório também neste arquivo")
    demo.add_argument("--keep", type=Path, help="cria a árvore nesta pasta e não a apaga")
    demo.add_argument("--trace", action="store_true", help="mostra g, h e f de cada pasta aberta")
    return parser


def _algorithms(keys: Sequence[str] | None, default: Sequence[Algorithm]) -> Sequence[Algorithm]:
    return get_algorithms(list(keys)) if keys else default


def render_stage1(root: Path, *, repeats: int, full_list: bool) -> str:
    records = run_stage1(root, repeats=repeats)
    return stage1_report(root, records, full_list=full_list)


def render_stage2(
    root: Path,
    keyword: str,
    algorithms: Sequence[Algorithm],
    *,
    weight: float,
    metric: str,
    repeats: int,
) -> str:
    records = run_stage2(root, keyword, algorithms, weight=weight, metric=metric, repeats=repeats)
    heuristic = NameHeuristic(keyword, weight, metric)
    cost_parts = None
    ucs = next((r for r in records if r.algorithm == UCS.label), None)
    if ucs and ucs.outcome.first:
        cost_parts = explain_cost(root, ucs.outcome.first.path, ITEMS_COST)
    return stage2_report(root, keyword, records, heuristic, cost_parts)


def render_stage3(
    root: Path,
    keyword: str,
    algorithms: Sequence[Algorithm],
    *,
    weight: float,
    metric: str,
    repeats: int,
    trace: bool,
) -> str:
    records = run_stage3(root, keyword, algorithms, weight=weight, metric=metric, repeats=repeats)
    heuristic = NameHeuristic(keyword, weight, metric)
    return stage3_report(root, keyword, records, heuristic, trace=trace)


def _stage1(args: argparse.Namespace) -> str:
    return render_stage1(args.root, repeats=args.repeats or 5, full_list=args.full_list)


def _stage2(args: argparse.Namespace) -> str:
    algorithms = _algorithms(args.algorithms, STAGE2_ALGORITHMS)
    return "\n\n".join(
        render_stage2(args.root, keyword, algorithms, weight=args.weight, metric=args.metric, repeats=args.repeats or 5)
        for keyword in args.keyword or [DEFAULT_STAGE2_KEYWORD]
    )


def _stage3(args: argparse.Namespace) -> str:
    return render_stage3(
        args.root,
        args.keyword,
        _algorithms(args.algorithms, STAGE3_ALGORITHMS),
        weight=args.weight_mib * MIB,
        metric=args.metric,
        repeats=args.repeats or 1,
        trace=args.trace,
    )


def _all(args: argparse.Namespace) -> str:
    sections = [
        render_stage1(args.root, repeats=args.repeats or 5, full_list=args.full_list),
        render_stage2(
            args.root,
            DEFAULT_STAGE2_KEYWORD,
            STAGE2_ALGORITHMS,
            weight=DEFAULT_NAME_WEIGHT,
            metric="levenshtein",
            repeats=args.repeats or 5,
        ),
        render_stage3(
            args.root,
            DEFAULT_STAGE3_KEYWORD,
            STAGE3_ALGORITHMS,
            weight=DEFAULT_CONTENT_WEIGHT,
            metric="levenshtein",
            repeats=args.repeats or 1,
            trace=False,
        ),
    ]
    return "\n\n".join(sections)


def _demo(args: argparse.Namespace) -> str:
    def run(root: Path) -> str:
        build_pruning_scenario(root)
        records = run_stage3(
            root,
            SCENARIO_KEYWORD,
            (UCS, ASTAR),
            weight=SCENARIO_WEIGHT,
            metric=args.metric,
            repeats=5,
        )
        heuristic = NameHeuristic(SCENARIO_KEYWORD, SCENARIO_WEIGHT, args.metric)
        return stage3_report(root, SCENARIO_KEYWORD, records, heuristic, trace=args.trace)

    if args.keep:
        return run(args.keep.resolve())
    with tempfile.TemporaryDirectory(prefix="file-hunter-demo-") as tmp:
        return run(Path(tmp) / "corpus")


def _extract(args: argparse.Namespace) -> str:
    count = extract_dataset(args.archive, args.dest, force=args.force)
    return f"{count} arquivos extraídos em {args.dest}"


_COMMANDS = {
    "extract": _extract,
    "stage1": _stage1,
    "stage2": _stage2,
    "stage3": _stage3,
    "all": _all,
    "demo-pruning": _demo,
}


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        text = _COMMANDS[args.command](args)
    except (FileNotFoundError, DatasetError, ValueError) as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2
    print(text)
    output = getattr(args, "output", None)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
