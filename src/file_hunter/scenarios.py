"""Árvore sintética para demonstrar a poda do A* sobre o UCS.

No conjunto real do professor os nomes de pasta são siglas de disciplinas
(``Fontes BD``, ``Fontes PAA``), que não se parecem com os termos buscados. A
heurística por nome não tem o que explorar ali. Este cenário reproduz o exemplo
do enunciado: buscando "pedagogia", a pasta ``_planos_pedagogicos_2024`` tem
nome parecido com o termo, enquanto ``_imagens_auxiliares`` não tem.

As pastas inúteis são deliberadamente mais baratas em bytes. Por isso o UCS, que
só olha o custo, abre todas elas antes de chegar à pasta certa.
"""

from __future__ import annotations

from pathlib import Path

KEYWORD = "pedagogia"

#: Peso de h(n) em bytes. Fica na mesma ordem de grandeza das pastas do cenário (dezenas de KB).
WEIGHT_BYTES = 256 * 1024

_FILLER = [
    "dados",
    "arquivo",
    "relatorio",
    "planilha",
    "tabela",
    "registro",
    "indice",
    "versao",
    "copia",
    "resumo",
    "anexo",
    "modelo",
    "rascunho",
    "lista",
    "tarefa",
    "agenda",
    "inventario",
    "balanco",
]

#: pasta -> (quantidade de arquivos, bytes por arquivo)
_USELESS_FOLDERS = {
    "_imagens_auxiliares": (8, 2 * 1024),
    "_backups_antigos": (6, 6 * 1024),
    "relatorios_financeiros": (4, 10 * 1024),
}


def _filler_text(size: int, seed: int) -> str:
    words: list[str] = []
    length = 0
    index = seed
    while length < size:
        word = _FILLER[index % len(_FILLER)]
        words.append(word)
        length += len(word) + 1
        index += 7
    return " ".join(words)[:size]


def build_pruning_scenario(root: Path) -> Path:
    """Cria a árvore de demonstração em ``root`` e devolve o caminho do arquivo alvo."""
    root.mkdir(parents=True, exist_ok=True)
    for folder, (count, size) in _USELESS_FOLDERS.items():
        directory = root / folder
        directory.mkdir(exist_ok=True)
        for number in range(count):
            (directory / f"arquivo_{number:02d}.txt").write_text(_filler_text(size, number), encoding="utf-8")

    useful = root / "_planos_pedagogicos_2024"
    useful.mkdir(exist_ok=True)
    (useful / "01_visao_geral.txt").write_text(_filler_text(24 * 1024, 3), encoding="utf-8")
    target = useful / "02_ementa.txt"
    sentence = f"\nObjetivo: discutir {KEYWORD} e avaliação formativa.\n"
    target.write_text(_filler_text(8 * 1024, 5) + sentence + _filler_text(8 * 1024, 9), encoding="utf-8")
    (useful / "03_bibliografia.txt").write_text(_filler_text(20 * 1024, 11), encoding="utf-8")
    return target
