### Etapa 2: arquivo com "plano" no nome em ./docencia/fontes

| Algoritmo | Alvo    | Caminho        | Pastas abertas | Itens examinados | Custo acumulado g(n) | Tempo (ms) | Memória (KB) |
| --------- | ------- | -------------- | -------------- | ---------------- | -------------------- | ---------- | ------------ |
| BFS       | "plano" | não encontrado | 11             | 72               | -                    | 1,203      | 61,8         |
| DFS       | "plano" | não encontrado | 11             | 72               | -                    | 1,141      | 56,5         |
| UCS       | "plano" | não encontrado | 11             | 72               | -                    | 1,204      | 55,9         |
| A*        | "plano" | não encontrado | 11             | 72               | -                    | 7,287      | 59,9         |

Custo de aresta: itens (arquivos + subpastas) da pasta aberta. g(n) é a soma desse custo nas pastas do caminho da raiz até o arquivo.
Heurística do A*: h(n) = 10 itens x d("plano", nome(n)), com d = Levenshtein normalizada (número de edições / tamanho da maior palavra); d = 0 quando o termo aparece no nome.

Leitura dos números:

- Nenhum arquivo tem "plano" no nome. Os algoritmos esgotaram a árvore, então o número de pastas abertas é o total.
