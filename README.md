# File Hunter Agent

Trabalho de Inteligência Artificial: um agente que recebe o nome (ou uma palavra do conteúdo) de um arquivo e procura o caminho dele na árvore `docencia/fontes/`, usando BFS, DFS, UCS e A*. Para cada busca ele mostra pastas abertas, itens examinados, custo do caminho, tempo e memória.

Só usa a biblioteca padrão, com uma exceção: o `pypdf`, que a etapa 3 precisa para ler o texto dos PDFs.

## Como rodar

Python 3.10 ou mais novo.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Os dados do professor (mais de 400 MB, com um PDF de 192 MB) não estão no repositório, porque o GitHub não aceita arquivos acima de 100 MB. Coloque o zip na raiz do projeto e extraia:

```bash
file-hunter extract [nome do arquivo].zip
```

Isso cria `docencia/fontes/` com 11 pastas e 62 PDFs.

```bash
file-hunter stage1                         # BFS e DFS, varredura completa
file-hunter stage1 --full-list             # lista o caminho de todos os arquivos
file-hunter stage2 -k livro -k plano       # BFS, DFS, UCS e A* por nome
file-hunter stage3 -k algoritmo --trace    # UCS e A* por conteúdo
file-hunter stage3 --algorithms bfs dfs ucs astar
file-hunter demo-pruning --trace           # árvore sintética onde o A* poda
file-hunter all --full-list --output docs/resultados.md
```

Sem instalar, `python main.py stage1` também funciona. Outras opções: `--root`, `--repeats`, `--weight` (etapa 2), `--weight-mib` (etapa 3) e `--metric levenshtein|ngram`.

As saídas que usei no relatório estão em `docs/`.

## Estrutura

```
src/file_hunter/
  frontiers.py    deque.popleft (BFS), deque.pop (DFS), heapq (UCS e A*)
  engine.py       o laço de busca, igual para os quatro
  problems.py     o que é nó, quanto custa abrir uma pasta, o que é objetivo
  heuristics.py   Levenshtein, Jaccard de trigramas e h(n)
  content.py      procura palavra dentro de texto e PDF
  stages.py       etapas 1, 2 e 3
  measure.py      perf_counter e tracemalloc
  report.py       tabelas em Markdown
  scenarios.py    árvore sintética da demonstração de poda
  dataset.py      extração do zip
  cli.py          linha de comando
tests/            pytest
```

O motor de busca é um só. O que muda de um algoritmo para outro é a fronteira:

| Algoritmo | Estrutura | Sai primeiro |
| --- | --- | --- |
| BFS | `deque`, `popleft()` | o mais antigo |
| DFS | `deque`, `pop()` | o mais recente |
| UCS | `heapq` | menor g(n) |
| A* | `heapq` | menor f(n) = g(n) + h(n) |

## Decisões

Arquivos também entram na fronteira. O teste de objetivo é feito quando o nó sai dela, e não quando é gerado. No UCS e no A* isso garante que o primeiro alvo a sair é o de menor valor. Arquivo não tem custo próprio, o custo já foi pago ao abrir a pasta.

Os itens de cada pasta são ordenados por nome, sem diferenciar maiúsculas. Na DFS os filhos são empilhados ao contrário, para o primeiro da ordem alfabética sair primeiro.

Custo de abrir uma pasta:

| Etapa | Custo | g(n) |
| --- | --- | --- |
| 1 | 1 por pasta | profundidade |
| 2 | itens da pasta (arquivos e subpastas) | soma ao longo do caminho |
| 3 | bytes dos arquivos da pasta | soma ao longo do caminho |

Na etapa 3 usei bytes e não o tempo de leitura, porque bytes não variam de uma execução para outra.

UCS e A* precisam saber o custo de uma pasta filha antes de abri-la, então listam todas as filhas ao expandir o pai. Por isso, na etapa 2, o UCS abre 2 pastas mas examina 60 itens, enquanto a DFS abre 3 e examina 25. A tabela mostra as duas métricas.

BFS e DFS não usam g(n) para decidir. O custo do caminho deles é calculado no fim, só para comparar.

Na etapa 3 os nós são só pastas. Abrir uma pasta lê os arquivos dela, em ordem alfabética, até achar um com a palavra. A comparação ignora acentos e maiúsculas.

Medição: cada algoritmo roda com estado novo. A primeira passada mede memória com `tracemalloc` e esquenta o cache do sistema. Depois vêm as passadas cronometradas com `perf_counter`, e a tabela mostra a mediana (5 passadas nas etapas 1 e 2, 1 na etapa 3). O pico é de alocações Python, não o RSS do processo.

## Heurística

```
h(n) = peso * d(termo, nome(n))
```

`d` vai de 0 a 1. O termo e o nome são normalizados (minúsculas, sem acento, símbolos viram espaço). Se o termo aparece dentro do nome, `d = 0`. Se não, `d` é a menor distância de Levenshtein, dividida pelo tamanho da maior das duas strings, entre o nome inteiro e cada palavra dele. Com `--metric ngram` vira `1 - Jaccard` dos trigramas.

O peso converte `d` para a unidade de g(n): 10 itens na etapa 2 e 16 MiB na etapa 3. Para "pedagogia", `_planos_pedagogicos_2024` dá `d` de 0,27 e `_imagens_auxiliares` dá mais de 0,6.

Essa h(n) não é admissível. Um nome parecido não garante que o conteúdo esteja na pasta, e um nome diferente não garante o contrário. Por isso o A* pode achar um caminho mais caro que o do UCS. Com peso 0 ele se comporta como UCS, e há um teste para isso.

## Resultados

Medidos na minha máquina, os tempos variam. As tabelas completas estão em `docs/`.

Etapa 1: BFS e DFS abrem 11 pastas, acham 62 arquivos e examinam 72 itens. O que muda é a ordem. Os 10 primeiros são iguais, porque as pastas anteriores a `Fontes GD` não têm subpastas. A diferença aparece na posição 18, quando a DFS entra em `Fontes GD/Ferramentas gestao de dados` antes de terminar de listar `Fontes GD`. O pico da fronteira é 51 nós no BFS e 23 na DFS.

Etapa 2, "livro":

| Algoritmo | Caminho | Pastas abertas | g(n) |
| --- | --- | --- | --- |
| BFS | `Fontes DMN/Livro Desenvolvimento Mobile.pdf` | 10 | 17 |
| DFS | `Fontes DMN/Livro Desenvolvimento Mobile.pdf` | 3 | 17 |
| UCS | `Fontes GTI/Livro GTI.pdf` | 2 | 13 |
| A* | `Fontes GTI/Livro GTI.pdf` | 2 | 13 |

O 13 é 9 itens da raiz mais 4 de `Fontes GTI`. A DFS abriu menos pastas, mas o arquivo dela custa 17. Com "plano" nenhum arquivo casa e todos esgotam as 11 pastas.

Etapa 3, "algoritmo": UCS e A* abrem 2 pastas, leem 4 arquivos (5,48 MiB) e chegam em `Fontes PCD/LIVRO SISTEMAS-DIGITAIS.pdf`. BFS e DFS vão para `Fontes BD`, leem 5 arquivos (30,12 MiB) e chegam em um arquivo com g(n) de 36.952.610 bytes.

O A* não podou nada no conjunto real. As pastas se chamam `Fontes BD`, `Fontes PAA` e assim por diante, nenhuma lembra "algoritmo", então h(n) fica alta e parecida em todas e a ordem não muda. O resultado é igual ao do UCS, com o trabalho extra de calcular h(n).

Para ver a poda acontecer, o `demo-pruning` monta a árvore do enunciado, com as pastas inúteis mais baratas que a certa:

| Algoritmo | Pastas abertas | Arquivos lidos | Bytes lidos | g(n) no achado |
| --- | --- | --- | --- | --- |
| UCS | 5 | 20 | 135.214 | 61.493 |
| A* | 2 | 2 | 41.013 | 61.493 |

Os dois chegam ao mesmo arquivo. O A* não abre `_imagens_auxiliares`, `_backups_antigos` nem `relatorios_financeiros`. O peso dessa demonstração (256 KiB) foi escolhido para ficar perto do tamanho das pastas. Com um peso muito maior que os custos, o A* passa a seguir só o nome da pasta.

## Limitações

- A heurística só olha nomes, então não ajuda quando as pastas não têm nomes descritivos, como neste conjunto.
- PDF escaneado, sem camada de texto, nunca casa. Se o `pypdf` não conseguir ler um arquivo, sai um aviso e ele conta como sem a palavra.
- Só `.pdf` e extensões de texto comuns são lidos na etapa 3.
- Links simbólicos são ignorados.
- A busca usa a palavra como trecho, então "algoritmo" também casa com "algoritmos". Palavra quebrada com hífen no fim da linha não é juntada.

## Testes

```bash
pytest
ruff check .
```

`tests/test_real_dataset.py` usa `docencia/fontes` e é pulado se a pasta não existir. Leva cerca de 20 segundos porque lê PDFs de verdade.
