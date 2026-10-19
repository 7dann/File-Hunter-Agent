"""Heurísticas h(n) baseadas apenas em nomes, sem aprendizado de máquina.

A ideia é medir o quanto o nome de uma pasta (ou arquivo) se parece com o termo
procurado. Uma distância perto de 0 indica um nome promissor; perto de 1, um
nome sem relação com o termo.

    d(termo, nome) = min sobre os candidatos c de  metrica(termo, c)

Os candidatos são cada palavra do nome normalizado e o nome inteiro. Se o termo
aparece como trecho de algum candidato, a distância é 0. A estimativa final em
unidades de custo é

    h(n) = peso * d(termo, nome(n))

``peso`` converte a distância (adimensional) para a mesma unidade do custo g(n):
itens na etapa 2 e bytes na etapa 3.

Essa heurística não é admissível no sentido estrito, porque um nome parecido não
garante que o conteúdo esteja ali e um nome diferente não garante que não esteja.
Ela funciona como uma pista barata para ordenar a fronteira. Por isso o A* aqui
pode devolver um caminho de custo maior que o do UCS, e os relatórios mostram
essa comparação.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .text import normalize, tokenize

DistanceMetric = Callable[[str, str], float]

NGRAM_SIZE = 3


def levenshtein(a: str, b: str) -> int:
    """Distância de edição: inserções, remoções e trocas de um caractere."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            cost = 0 if char_a == char_b else 1
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + cost,
                )
            )
        previous = current
    return previous[-1]


def levenshtein_distance(a: str, b: str) -> float:
    """Levenshtein normalizada para [0, 1] pelo tamanho da maior palavra."""
    longest = max(len(a), len(b))
    if longest == 0:
        return 0.0
    return levenshtein(a, b) / longest


def ngrams(text: str, size: int = NGRAM_SIZE) -> set[str]:
    """Conjunto de n-gramas de caracteres, com espaços nas bordas como marcadores."""
    padded = f" {text} "
    if len(padded) < size:
        return {padded}
    return {padded[i : i + size] for i in range(len(padded) - size + 1)}


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Interseção sobre união de dois conjuntos. Dois conjuntos vazios valem 1."""
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def ngram_distance(a: str, b: str) -> float:
    """1 menos a similaridade de Jaccard entre os trigramas das duas palavras."""
    return 1.0 - jaccard_similarity(ngrams(a), ngrams(b))


METRICS: dict[str, DistanceMetric] = {
    "levenshtein": levenshtein_distance,
    "ngram": ngram_distance,
}


def name_distance(term: str, name: str, metric: DistanceMetric = levenshtein_distance) -> float:
    """Distância em [0, 1] entre um termo e um nome de pasta ou arquivo."""
    normalized_term = normalize(term)
    normalized_name = normalize(name)
    if not normalized_term:
        return 1.0
    if not normalized_name:
        return 1.0
    if normalized_term in normalized_name:
        return 0.0
    candidates = [*tokenize(name), normalized_name]
    return min(metric(normalized_term, candidate) for candidate in candidates)


@dataclass(frozen=True, slots=True)
class NameHeuristic:
    """h(n) = peso * distância entre o termo procurado e o nome do nó."""

    term: str
    weight: float
    metric_name: str = "levenshtein"

    def __post_init__(self) -> None:
        if self.metric_name not in METRICS:
            valid = ", ".join(sorted(METRICS))
            raise ValueError(f"Métrica desconhecida: {self.metric_name!r}. Use uma de: {valid}.")
        if self.weight < 0:
            raise ValueError("O peso da heurística não pode ser negativo.")

    def distance(self, name: str) -> float:
        return name_distance(self.term, name, METRICS[self.metric_name])

    def estimate(self, name: str) -> float:
        return self.weight * self.distance(name)

    def describe(self, unit: str, weight_text: str | None = None) -> str:
        """Fórmula legível para os relatórios."""
        metric = {
            "levenshtein": "Levenshtein normalizada (número de edições / tamanho da maior palavra)",
            "ngram": "1 - Jaccard dos trigramas de caracteres",
        }[self.metric_name]
        weight = weight_text or f"{self.weight:g} {unit}"
        return f'h(n) = {weight} x d("{self.term}", nome(n)), com d = {metric}; d = 0 quando o termo aparece no nome.'
