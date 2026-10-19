"""Atalho para rodar o agente sem instalar o pacote: ``python main.py stage1``."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from file_hunter.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
