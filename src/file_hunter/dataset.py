"""Extração do conjunto de dados entregue pelo professor."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path, PurePosixPath


class DatasetError(Exception):
    """Falha ao preparar o conjunto de dados."""


def _common_top_level(names: list[str]) -> str | None:
    tops = {PurePosixPath(name).parts[0] for name in names if PurePosixPath(name).parts}
    return tops.pop() if len(tops) == 1 else None


def extract_dataset(archive: Path, destination: Path, *, force: bool = False) -> int:
    """Extrai o zip em ``destination``, removendo a pasta de topo única, se houver.

    O zip do professor contém ``Fontes/...``. O desafio espera os arquivos em
    ``docencia/fontes/``, então o prefixo ``Fontes/`` é descartado. Entradas que
    tentariam sair do destino (``..``) são rejeitadas. Devolve o número de
    arquivos extraídos.
    """
    if not archive.is_file():
        raise DatasetError(f"Arquivo zip não encontrado: {archive}")
    if destination.exists() and any(destination.iterdir()):
        if not force:
            raise DatasetError(f"{destination} já existe e não está vazia. Use --force para substituir.")
        shutil.rmtree(destination)

    destination = destination.resolve()
    extracted = 0
    with zipfile.ZipFile(archive) as bundle:
        names = [info.filename for info in bundle.infolist()]
        prefix = _common_top_level(names)
        for info in bundle.infolist():
            parts = list(PurePosixPath(info.filename).parts)
            if prefix and parts and parts[0] == prefix:
                parts = parts[1:]
            if not parts:
                continue
            target = destination.joinpath(*parts).resolve()
            if not target.is_relative_to(destination):
                raise DatasetError(f"Entrada insegura no zip: {info.filename}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink)
            extracted += 1
    return extracted
