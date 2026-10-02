# Relatório de alterações, execução e limpeza

> Preparação para versionamento: o `.gitignore` cobre ambientes locais,
> bytecode, caches, cobertura, empacotamento, configurações com credenciais,
> auxiliares de LaTeX e metadados do sistema. Os 23 bytecodes encontrados no
> índice foram retirados do versionamento, sem apagar as cópias locais.
> Gráficos, PDFs finais e registros experimentais são mantidos. A fonte do
> fluxograma interativo, antes fora do repositório, foi incluída em `relatorio`.
> O caso de três pedidos foi classificado como referência de regressão;
> a campanha de 12 pedidos é a análise principal.

> Atualização Q=1..10: entrada de 12 pedidos concorrentes e campanha com cinco
> sementes, referência empírica, cache isolado por execução e guias detalhados.
> O avaliador foi corrigido para separar distância e tempo; as campanhas com
> rede sintética foram refeitas. O [protocolo](CAMPANHA_Q1_10.md) explica essa
> correção, os arquivos novos e o limite das conclusões. O cenário anterior
> continua disponível para gabarito pequeno; esta atualização substitui seus
> valores incorretos de distância.

> Atualização posterior à auditoria: os onze imports listados foram retirados,
> o exemplo da raiz foi removido e a cópia em dados foi reformulada. O comparador
> usa o exemplo canônico e seus parâmetros de avaliação; o leitor valida o
> contrato urbano. Ver [FORMATO_ENTRADA.md](../dados/FORMATO_ENTRADA.md). As
> seções abaixo preservam o retrato do momento da auditoria anterior.

> Atualização da campanha de capacidade: Q saiu do JSON de demanda e passou
> para a configuração em `experimentos/comparacao_exemplo.json`. O leitor
> aceita Q externo e mantém compatibilidade com entradas antigas. Foram
> adicionados `executar_campanha.py` e `gerar_graficos_campanha.py`, checkpoints
> de fronteira, tempo e esforço em SA/GA/GRASP, e 180 execuções validadas com
> oito gráficos em PNG/SVG. Veja o [guia dos resultados](../resultados/comparacao_exemplo/GUIA_RESULTADOS.md).

**Data:** 01/10/2026. **Base da comparação:** estado atual do projeto contra
`HEAD` (`eee0ab4`, “Abordagem com Grafos”). A revisão incluiu diferenças do Git,
arquivos novos, imports Python, chamadas, entradas e saídas dos experimentos,
referências da documentação e comparação SHA-256 de arquivos duplicados.

## 1. O que mudou e de onde veio

As alterações descritas nas seções 2–5 foram realizadas nesta conversa antes
desta auditoria. Não foram criados commits: parte dos arquivos está modificada
e parte é nova, ainda não versionada. O Git registra oito arquivos rastreados
com diferenças, incluindo dois artefatos regenerados.

Já existiam antes: a modelagem DARP, os leitores, a rede fixa e Dijkstra, a
serialização JSON, as três políticas de agendamento, a enumeração, o modelo
Gurobi, as métricas Pareto e as implementações de SA, GA e GRASP. Essas partes
foram examinadas ou reutilizadas; não são novas funcionalidades desta conversa.
Também não foram implementados MOILS ou epsilon-restrito com ILS.

## 2. Mudanças nos arquivos existentes

### `codigo/darp/avaliador.py`

Antes, a falta de NumPy/SciPy fazia OTIMO executar BORDO silenciosamente.
Agora, lança erro explícito com orientação para instalar as dependências.
Isso impede apresentar um resultado heurístico como agendamento ótimo.
Não houve reescrita da programação linear, das restrições ou dos objetivos.
A agenda BORDO após falha de uma PL permanece como diagnóstico de violações.

### `codigo/darp/exato.py`

Correção da documentação do módulo: enumeração com OTIMO é exata também nos
horários, pois resolve a PL por rota. Com CEDO/BORDO, o resultado vale apenas
dentro da política escolhida. O algoritmo de enumeração não foi alterado.

### `codigo/darp/metaheuristicas/operadores.py`

| Operação | Antes | Agora | Motivo |
|---|---|---|---|
| Inserção | Aceitava posições inconsistentes e pares repetidos | Exige `0 <= coleta <= entrega <= tamanho` e rejeita pedido já presente na rota | Evitar entrega antes da coleta e duplicação local |
| Movimento entre rotas | Pressupunha lista com todas as rotas | Completa a cópia com rotas vazias até m | Aceitar soluções compactas vindas da enumeração |
| Perturbação | Pressupunha todas as rotas presentes | Copia a solução e completa rotas vazias | Preservar original e evitar índices inexistentes |
| Fallback da perturbação | Sorteava posições independentemente | Sorteia entrega após coleta e desconta o par removido em movimento interno | Preservar precedência e posições válidas |
| Construção gulosa | Tentava mover pedidos ausentes; a solução não mudava | Insere explicitamente coleta e entrega do pedido pendente | Construção passa a incluir os pedidos de fato |
| Custo de construção | Custo absoluto da rota com escalas distintas | Variação marginal de f1/f2, normalizada entre candidatos da etapa | Comparar impacto da inserção e reduzir viés das unidades |
| Parâmetros da construção | Sem validação de intervalo | Exige alpha e peso entre 0 e 1 | Evitar RCL e ponderação inconsistentes |
| Seleção RCL | Tuplas com seis campos | Tuplas reformuladas; seleção acessa a solução no índice correto | Adaptar ao novo cálculo de custo |

O construtor ainda retorna a solução individual caso fique sem candidatos
viáveis. Essa alternativa tem estrutura válida, mas pode ser temporalmente
inviável; quem chama deve avaliar. A normalização acrescentada vale para a
construção; não padroniza automaticamente toda a busca de SA e GRASP.

### `codigo/darp/metaheuristicas/ga.py`

- Copia e completa ambos os pais com rotas vazias quando necessário.
- Herda uma rota do primeiro pai.
- Preserva nas outras rotas a ordem e a atribuição do segundo pai, removendo
  pedidos já herdados; insere os pedidos que ainda faltam.
- Acrescenta `_crowding`: distâncias entre vizinhos normalizadas por objetivo,
  preservando extremos quando há amplitude.
- Na frente que excede o tamanho da população, prioriza maior crowding,
  com desempate aleatório, em vez de escolher todos aleatoriamente.

O ranking por Pareto, arquivo externo e restante do algoritmo já existiam.
O método continua descrito como GA inspirado em NSGA-II: a seleção de pais
continua aleatória, portanto não foi convertido em uma implementação canônica.

### `codigo/experimentos/fase2_fronteira.py`

- Corrige o comentário: os pedidos originais 1–5 da pr01 são todos de volta.
- Confere explicitamente os quatro pares históricos de objetivos, com
  tolerância 0.001, além das verificações já existentes.
- Usa `.cache/matplotlib` no projeto para o cache de fontes, salvo quando o
  usuário já definiu `MPLCONFIGDIR`.
- Mantém Gurobi opcional; sua indisponibilidade é informada na execução.

### Documentação e resultados existentes

| Arquivo | Alteração |
|---|---|
| `relatorio/RELATORIO_DESENVOLVIMENTO.md` | Nota inicial direciona ao protocolo atual e explica que as fases seguintes são histórico |
| `resultados/fase2_fronteira_pr01r5.csv` | Regenerado; mantém quatro pontos OTIMO e dez BORDO; retira quatro linhas do solver, pois Gurobi não foi executado nesta reprodução |
| `resultados/fase2_fronteira_pr01r5.png` | Regenerado com as duas séries efetivamente executadas |
| `resultados/fase2_extremos_pr01.csv` | Regravado, mas sem diferença de conteúdo em relação ao Git |

Os valores históricos do solver podem ser recuperados na revisão Git de base.
A ausência da série no CSV atual não significa que o modelo Gurobi foi removido.

## 3. Arquivos novos de código

| Arquivo | Responsabilidade e comportamento |
|---|---|
| `codigo/darp/cenarios.py` | `cenario_capacidade`: valida Q/m inteiros positivos e cria cenário com `dataclasses.replace`, sem modificar Q/m da base. A cópia é superficial; rede e lista de nós são compartilhadas para leitura |
| `codigo/experimentos/capacidade_q.py` | CLI para ler texto/JSON, selecionar pedidos, fixar m/alpha/phi, percorrer Q, enumerar fronteiras com OTIMO, conferir viabilidade e inclusão entre capacidades e exportar objetivos/rotas/horários |
| `codigo/experimentos/resumir_capacidade.py` | Lê os JSONs anteriores; conta fronteiras distintas a seis casas decimais; escreve resumo por Q e gráfico conjunto dos extremos |
| `codigo/experimentos/validar_operadores.py` | Oito testes de regressão de operadores, cenários, capacidade e integração curta dos três algoritmos |

O estudo de capacidade usa, por padrão, pr01 com pedidos de ida 13–17, m=5,
alpha=2, phi=1 e Q=1–20. Rejeita enumeração com mais de seis pedidos.
O cache usa `min(Q, demanda total)`: Q acima da soma das demandas não restringe
mais a carga. Não deduz saturação antecipada apenas porque duas fronteiras
anteriores coincidiram. JSON inclui cenário inviável; CSV lista apenas pontos.
As conferências internas usam `assert`: executar com Python normal, sem `-O`.

O resumo mantém valores numéricos originais em CSV; apenas o gráfico apresenta
resíduos de f2 inferiores a 1e-6 como zero. A figura resume extremos e não
substitui o conjunto completo de pontos guardado no JSON/CSV.

## 4. Arquivos novos de apoio e resultados

| Arquivo ou conjunto | Finalidade |
|---|---|
| `.gitignore` | Ignora `.venv/`, `.cache/`, `__pycache__/` e `*.pyc`; não retira arquivos já rastreados pelo Git |
| `README.md` | Entrada para o projeto, estrutura e documentos atuais |
| `requirements-validacao.txt` | Versões exatas obtidas do ambiente de validação; `pyproject.toml` continua definindo as dependências do pacote |
| `relatorio/MODELO_EXPERIMENTAL.md` | Pergunta de pesquisa, passageiros, Q=1–20, objetivos, cenários, hipóteses, limites e comandos |
| `relatorio/VALIDACAO_2026_10_01.md` | Resultados reproduzidos e evidências das verificações |
| `resultados/capacidade_q/fronteiras.json` | Fronteiras para m=5, com parâmetros, rotas, agendas e cargas |
| `resultados/capacidade_q/fronteiras.csv` | Pontos numéricos para m=5 |
| `resultados/capacidade_q/resumo.csv` | Situação, cardinalidade, extremos e carga por Q para m=5 |
| `resultados/capacidade_q_m3/fronteiras.json` | Mesmo estudo com m=3 |
| `resultados/capacidade_q_m3/fronteiras.csv` | Pontos numéricos para m=3 |
| `resultados/capacidade_q_m3/resumo.csv` | Resumo por Q para m=3 |
| `resultados/capacidade_q_comparativo.png` | Comparação conjunta dos extremos por capacidade |
| `.venv/` | Ambiente Python criado para executar a PL de verdade; não é código-fonte |
| `.cache/matplotlib/` | Cache de renderização regenerável |

Nesta auditoria foram acrescentados este relatório e
`FLUXOGRAMA_ATUAL.md`, além de links no README. Nenhum arquivo de implementação
foi refatorado nesta etapa e nenhum arquivo foi removido.

## 5. Validação das mudanças anteriores

| Verificação | Evidência registrada |
|---|---|
| Leitores e agendas clássicas | `validar_fase1.py`: todas as conferências passaram |
| Rede fixa, grafo e persistência | `validar_novo_modelo.py`: todas as conferências passaram |
| Operadores e integração | Oito testes passaram; inclui 1000 perturbações e cruzamentos com ambos os pais |
| Gabarito pequeno | Quatro pontos: (47.0253,89.4142), (47.6721,70.2116), (49.1145,39.1136), (49.9657,0) |
| Rotas publicadas da pr01 reagendadas | f1=190.02, f2=1183.64; a divergência anterior vinha do fallback sem SciPy |
| Estudo Q, m=5 e m=3 | Cada cenário gerou a mesma fronteira de quatro pontos para Q=1–20, com carga máxima 1 nas soluções guardadas |
| Caso controlado de capacidade | Menor distância 10,6,4,4 para Q=1,2,4,20, respectivamente |
| Gurobi | Indisponível no ambiente; não há nova conferência independente por solver |

Esta auditoria de uso e documentação é estática: não reexecutou uma campanha
comparativa de grande escala. As evidências acima são da etapa anterior.

## 6. Como o código roda hoje

Ver [FLUXOGRAMA_ATUAL.md](FLUXOGRAMA_ATUAL.md) para os diagramas completos.
Os sete scripts são pontos de entrada independentes:

| Entrada | Principais dependências | Saída |
|---|---|---|
| `validar_fase1.py` | Todos os arquivos bnc/tabu, leitor `.res`, solução, avaliador | Conferências no terminal e código de saída |
| `validar_novo_modelo.py` | Rede sintética, JSON temporário, avaliador, enumeração | Conferências no terminal; JSON temporário removido pelo próprio teste |
| `validar_operadores.py` | Operadores, GA/SA/GRASP, cenários, enumeração | Resultado unittest e código de saída |
| `fase2_fronteira.py` | pr01/pr01.res, enumeração, Pareto, Gurobi opcional | Dois CSVs e um PNG em resultados |
| `capacidade_q.py` | Leitor, redução, cenários, enumeração, avaliador | JSON e CSV de fronteiras na pasta escolhida |
| `resumir_capacidade.py` | JSONs de capacidade, Matplotlib | CSVs de resumo e PNG comparativo |
| `comparar_metaheuristicas.py` | Entrada texto/JSON, fábrica de métodos, operadores, avaliador e Pareto | Fronteiras no terminal; PNG opcional na pasta de execução |

As validações de Fase 1 e rede têm execução no nível superior do arquivo;
não devem ser importadas como módulos auxiliares. O comparador usa BORDO por
padrão, enquanto os estudos exatos usam OTIMO. `mip.py` tem uso condicional,
portanto ausência de Gurobi não torna esse módulo código morto.

## 7. Auditoria dos módulos Python

**Não foi identificado nenhum módulo inteiro comprovadamente sem uso.**

| Módulo em `codigo/darp/` | Consumidores e motivo para manter |
|---|---|
| `__init__.py` | API pública importada pelos experimentos |
| `instancia.py` | Todos os caminhos que carregam dados ou manipulam pedidos |
| `rede.py` | Leitura JSON, instância e validação da rede |
| `solucao.py` | Avaliador, leitores, enumeração, Gurobi e metaheurísticas |
| `avaliador.py` | Avaliação central dos experimentos e buscas |
| `leitor_res.py` | Regressão clássica e referência da Fase 2 |
| `pareto.py` | Enumeração, métricas, arquivo externo e ranking |
| `exato.py` | Fase 2, capacidade e validações pequenas |
| `mip.py` | Conferência opcional da Fase 2 |
| `cenarios.py` | Capacidade e testes |
| `metaheuristicas/__init__.py` | Exportações e fábrica usada pelo comparador |
| `metaheuristicas/base.py` | Resultado comum, interface e arquivo Pareto dos métodos |
| `metaheuristicas/operadores.py` | Construção/vizinhanças dos três métodos e testes |
| `metaheuristicas/sa.py` | Comparador, API e teste de integração |
| `metaheuristicas/ga.py` | Comparador, API, cruzamentos e integração |
| `metaheuristicas/grasp.py` | Comparador, API e integração |

`Instancia.no_fixo_de`, `Rede.from_matrizes` e `ResultadoOtimizacao.resumo` não
têm chamadas diretas encontradas nos scripts atuais. São facilidades da API,
não prova de código abandonado; sua remoção reduziria funcionalidades públicas.
As políticas CEDO/BORDO e o limite global do arquivo continuam necessários
para diagnóstico e regressão, mesmo com OTIMO/alpha no protocolo principal.

## 8. Candidatos à limpeza e evidências

### Remoção recomendada: duplicação e caches

| Alvo | Evidência | Tratamento recomendado |
|---|---|---|
| `exemplo_instancia.json` na raiz | Conteúdo idêntico ao de `dados/exemplo_instancia.json`: SHA-256 `07A5E697544ACA4E36D7ADDB0D462E3B83056F1F4A058991EB2340718421866B`; cada cópia tem 2986 bytes | Manter a cópia em dados; atualizar o padrão e o exemplo de comando do comparador antes de retirar a raiz |
| `codigo/**/__pycache__/*.pyc` | 39 arquivos presentes, total 396000 bytes; 22 deles já rastreados pelo Git, incluindo Python 3.10/3.11 | Retirar caches do controle de versão e remover os locais quando conveniente; serão regenerados |
| `.cache/matplotlib/` | Um arquivo de 83553 bytes na auditoria; criado pela renderização | Remover quando quiser liberar cache; será regenerado |

Os totais de cache mudam a cada execução. `.gitignore` impede novas inclusões,
mas **não elimina os 22 arquivos compilados que já estão versionados**.
A instância da raiz ainda é a primeira escolha do comparador padrão; o carregador
também procura em dados, mas ajustar explicitamente o padrão torna a limpeza clara.

### Código sem uso local: imports removíveis

Os nomes abaixo não têm leitura no corpo do módulo, segundo análise da árvore
sintática e revisão do código. Exportações dos `__init__.py` foram excluídas
desse critério porque fazem parte da API.

| Arquivo | Imports sem uso local |
|---|---|
| `metaheuristicas/base.py` | `time`, `Sequence` |
| `metaheuristicas/ga.py` | `Sequence`, `encontrar_rota_de_requisicao`, `remover_requisicao` |
| `metaheuristicas/operadores.py` | `Sequence` |
| `metaheuristicas/sa.py` | `Solucao` |
| `mip.py` | `Avaliador` |
| `experimentos/comparar_metaheuristicas.py` | `AlgoritmoGenetico`, `GRASP`, `SimulatedAnnealing`; o arquivo usa a fábrica |

São onze imports removíveis em seis arquivos, não seis arquivos descartáveis.

### Materiais fora do caminho principal que devem ser preservados

| Material | Por que não é descarte automático |
|---|---|
| `dados/bnc/*` e `dados/tabu/pr02`, `pr07`, `pr11` | Não entram no estudo padrão de Q, mas são lidos pela validação de Fase 1 |
| `dados/tabu/*.res` | Referências numéricas ativas para validar horários, carga e distância |
| `dados/exemplo_instancia.json` | Exemplo de rede urbana carregável pelo comparador |
| `relatorio/main.tex`, `main.pdf`, `resumo_professor.tex`, `resumo_professor.pdf` | Artefatos acadêmicos da proposta anterior; são documentação histórica, não dependências Python |
| `relatorio/Logo_CEFET-MG.png` | Referenciada diretamente por `main.tex` |
| `referencias/*.pdf` | Bibliografia de pesquisa; não precisa ser importada por código para ter uso |
| Resultados CSV/JSON/PNG | Evidência e reprodução; resumo e PNG são derivados, mas têm papel distinto das fronteiras completas |
| `requirements-validacao.txt` e `pyproject.toml` | Ambiente reproduzível versus dependências do pacote; não são duplicação equivalente |
| `.venv/` | Ambiente ativo com SciPy; remover exige reinstalar dependências para executar OTIMO |
| `.git/` | Histórico necessário para rastrear alterações e recuperar referências |

Os documentos acadêmicos precisam de atualização antes de uma entrega atual,
mas apagá-los não resolve o desalinhamento. Uma opção futura é movê-los para
uma pasta histórica, preservando links e a referência ao logo.

## 9. Ordem recomendada da limpeza

1. Definir `dados/exemplo_instancia.json` como exemplo único e atualizar o CLI.
2. Retirar os onze imports locais sem uso.
3. Remover os `.pyc` rastreados e manter regras de ignore; apagar caches locais
   após verificar que o caminho está dentro do repositório.
4. Manter biblioteca, validações, benchmarks, resultados e referências.
5. Após a limpeza, repetir os oito testes e uma execução do comparador sobre
   o exemplo, além de verificar importação do pacote.

**Nenhuma exclusão foi executada nesta auditoria.** Os alvos e dependências
necessárias foram registrados para tornar uma limpeza posterior revisável.
