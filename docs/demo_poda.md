### Etapa 3: palavra "pedagogia" no conteúdo dos arquivos em ./docencia/demo

| Algoritmo | Palavra no conteúdo | Caminho                                                | Pastas abertas | Arquivos lidos do disco | Bytes lidos         | g(n)   | h(n)   | Custo total f(n) | Tempo (ms) | Memória (KB) |
| --------- | ------------------- | ------------------------------------------------------ | -------------- | ----------------------- | ------------------- | ------ | ------ | ---------------- | ---------- | ------------ |
| UCS       | "pedagogia"         | ./docencia/demo/_planos_pedagogicos_2024/02_ementa.txt | 5              | 20                      | 135.214 (132,0 KiB) | 61.493 | 0      | 61.493           | 14,2       | 460,0        |
| A*        | "pedagogia"         | ./docencia/demo/_planos_pedagogicos_2024/02_ementa.txt | 2              | 2                       | 41.013 (40,1 KiB)   | 61.493 | 71.494 | 132.987          | 4,9        | 448,5        |

Custo de aresta: total de bytes dos arquivos da pasta aberta. g(n) soma esse custo nas pastas do caminho; f(n) = g(n) + h(n) no nó onde a palavra foi achada.
Heurística do A*: h(n) = 256,0 KiB x d("pedagogia", nome(n)), com d = Levenshtein normalizada (número de edições / tamanho da maior palavra); d = 0 quando o termo aparece no nome.

#### Pastas abertas por algoritmo

| # | UCS: pasta (g, h)                        | A*: pasta (g, h)                              |
| - | ---------------------------------------- | --------------------------------------------- |
| 1 | demo (0 B, 0 B)                          | demo (0 B, 0 B)                               |
| 2 | _imagens_auxiliares (16,0 KiB, 0 B)      | _planos_pedagogicos_2024 (60,1 KiB, 69,8 KiB) |
| 3 | _backups_antigos (36,0 KiB, 0 B)         |                                               |
| 4 | relatorios_financeiros (40,0 KiB, 0 B)   |                                               |
| 5 | _planos_pedagogicos_2024 (60,1 KiB, 0 B) |                                               |

#### Traço do UCS: nós abertos com g, h e f

| # | Pasta                                    | g(n) bytes | h(n) bytes | f(n) bytes |
| - | ---------------------------------------- | ---------- | ---------- | ---------- |
| 1 | ./docencia/demo                          | 0          | 0          | 0          |
| 2 | ./docencia/demo/_imagens_auxiliares      | 16.381     | 0          | 16.381     |
| 3 | ./docencia/demo/_backups_antigos         | 36.861     | 0          | 36.861     |
| 4 | ./docencia/demo/relatorios_financeiros   | 40.959     | 0          | 40.959     |
| 5 | ./docencia/demo/_planos_pedagogicos_2024 | 61.493     | 0          | 61.493     |

#### Traço do A*: nós abertos com g, h e f

| # | Pasta                                    | g(n) bytes | h(n) bytes | f(n) bytes |
| - | ---------------------------------------- | ---------- | ---------- | ---------- |
| 1 | ./docencia/demo                          | 0          | 0          | 0          |
| 2 | ./docencia/demo/_planos_pedagogicos_2024 | 61.493     | 71.494     | 132.987    |

Leitura dos números:

- O A* abriu 2 pastas contra 5 do UCS, uma poda de 3.
- Arquivos lidos do disco: UCS 20, A* 2. O A* leu 18 arquivos e 92,0 KiB a menos.
