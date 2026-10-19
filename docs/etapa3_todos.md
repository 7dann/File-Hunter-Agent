### Etapa 3: palavra "algoritmo" no conteúdo dos arquivos em ./docencia/fontes

| Algoritmo | Palavra no conteúdo | Caminho                                                              | Pastas abertas | Arquivos lidos do disco | Bytes lidos            | g(n)       | h(n)       | Custo total f(n) | Tempo (ms) | Memória (KB) |
| --------- | ------------------- | -------------------------------------------------------------------- | -------------- | ----------------------- | ---------------------- | ---------- | ---------- | ---------------- | ---------- | ------------ |
| BFS       | "algoritmo"         | ./docencia/fontes/Fontes BD/Sistemas de Banco de Dados - Elmasri.pdf | 2              | 5                       | 31.583.154 (30,12 MiB) | 36.952.610 | 0          | 36.952.610       | 11.797,5   | 80.558,0     |
| DFS       | "algoritmo"         | ./docencia/fontes/Fontes BD/Sistemas de Banco de Dados - Elmasri.pdf | 2              | 5                       | 31.583.154 (30,12 MiB) | 36.952.610 | 0          | 36.952.610       | 11.123,3   | 80.379,0     |
| UCS       | "algoritmo"         | ./docencia/fontes/Fontes PCD/LIVRO SISTEMAS-DIGITAIS.pdf             | 2              | 4                       | 5.741.957 (5,48 MiB)   | 5.741.957  | 0          | 5.741.957        | 2.303,7    | 21.136,9     |
| A*        | "algoritmo"         | ./docencia/fontes/Fontes PCD/LIVRO SISTEMAS-DIGITAIS.pdf             | 2              | 4                       | 5.741.957 (5,48 MiB)   | 5.741.957  | 13.048.946 | 18.790.903       | 2.263,0    | 20.238,2     |

Custo de aresta: total de bytes dos arquivos da pasta aberta. g(n) soma esse custo nas pastas do caminho; f(n) = g(n) + h(n) no nó onde a palavra foi achada.
Heurística do A*: h(n) = 16,00 MiB x d("algoritmo", nome(n)), com d = Levenshtein normalizada (número de edições / tamanho da maior palavra); d = 0 quando o termo aparece no nome.

#### Pastas abertas por algoritmo

| # | BFS: pasta | DFS: pasta | UCS: pasta (g, h)          | A*: pasta (g, h)                 |
| - | ---------- | ---------- | -------------------------- | -------------------------------- |
| 1 | fontes     | fontes     | fontes (0 B, 0 B)          | fontes (0 B, 0 B)                |
| 2 | Fontes BD  | Fontes BD  | Fontes PCD (5,48 MiB, 0 B) | Fontes PCD (5,48 MiB, 12,44 MiB) |

Leitura dos números:

- O A* abriu o mesmo número de pastas que o UCS (2), sem poda neste cenário.
- Os dois leram 4 arquivos (5,48 MiB).
