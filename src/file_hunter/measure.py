"""Medição de tempo e memória com a biblioteca padrão."""

from __future__ import annotations

import statistics
import time
import tracemalloc
from collections.abc import Callable
from typing import TypeVar

from .models import Measurement

T = TypeVar("T")


def profile(run: Callable[[], T], *, repeats: int = 1) -> tuple[T, Measurement]:
    """Executa ``run`` e mede tempo (``perf_counter``) e pico de memória (``tracemalloc``).

    ``run`` precisa criar todo o seu estado a cada chamada, porque é executada
    ``repeats + 1`` vezes:

    1. Uma passada com ``tracemalloc`` ligado, só para o pico de memória. O
       rastreamento deixa o código mais lento, então esse tempo é descartado.
       Essa passada também aquece o cache de páginas do sistema operacional, o
       que evita que o primeiro algoritmo medido pague sozinho pela leitura fria.
    2. ``repeats`` passadas sem rastreamento, só para tempo. O resultado é a
       mediana, que reduz o efeito de picos isolados do sistema.

    O pico reportado é de alocações Python (heap), que é o que a fronteira, o
    cache de listagens e o extrator de PDF usam. Não é o RSS do processo.
    """
    if repeats < 1:
        raise ValueError("repeats deve ser pelo menos 1")

    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        run()
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    timings: list[float] = []
    result: T
    for _ in range(repeats):
        started = time.perf_counter()
        result = run()
        timings.append((time.perf_counter() - started) * 1000.0)

    measurement = Measurement(
        elapsed_ms=statistics.median(timings),
        peak_memory_kb=peak_bytes / 1024.0,
    )
    return result, measurement
