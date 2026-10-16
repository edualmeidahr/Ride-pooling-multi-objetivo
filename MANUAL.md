# Manual da entrega — Ride-pooling multiobjetivo

Versão de apresentação: 16/10/2026. Código organizado em três implementações, com avaliador e entradas compartilhados. A colônia de formigas foi integrada à rede e ao modelo ambiental atuais. Esta branch contém a entrega executável, sem campanhas e relatórios históricos.

## 1. O que esta entrega resolve

O problema é alocar pedidos de transporte em veículos e ordenar suas coletas e entregas, respeitando capacidade, janelas de atendimento, duração máxima das rotas e tempo máximo a bordo. Cada pedido deve ser atendido integralmente, com coleta anterior à entrega e ambas no mesmo veículo.

Os dois objetivos são minimizados juntos:

- `f1`: distância total em km no exemplo sem modelo ambiental; emissão operacional estimada em gramas de CO2 quando o modelo ambiental está habilitado.
- `f2`: tempo perdido total em passageiro-minutos, formado por espera em relação ao horário desejado e desvio do tempo a bordo em relação à viagem direta. Não é o tempo total de viagem. Por isso, `f2 = 0` pode ocorrer mesmo com deslocamentos longos.

`Q` é a capacidade de cada veículo no cenário; `m` é o número máximo de veículos disponíveis. O programa repete o cenário para os valores de Q da configuração. A frota disponível permanece fixa entre esses cenários; o número efetivamente usado pode mudar. A frota é homogênea dentro de cada Q: esta versão não combina tipos de veículos diferentes em uma única solução.

As três categorias exigidas estão presentes: método exato por enumeração, metaheurísticas GA/SA/GRASP/ACO e heurística gulosa independente. A colônia de formigas da branch `colonia-formiga` está integrada como quarta metaheurística, com as adaptações descritas na seção sobre ACO. O modelo MIP opcional com Gurobi também não faz parte do pacote: o método exato disponível no menu é a enumeração descrita adiante.

## 2. Todos utilizam SciPy?

**Sim, com a política `otimo` utilizada em todas as configurações incluídas, as seis implementações compartilham o avaliador que utiliza SciPy.** Isso não significa que SciPy implemente GA, SA, GRASP, ACO ou a heurística gulosa.

O trabalho é dividido em duas partes:

1. O algoritmo decide quais pedidos ficam em cada veículo e em qual ordem serão visitados.
2. Para essa ordem já fixada, o avaliador usa `scipy.optimize.linprog(..., method="highs")` para escolher horários de atendimento que minimizem o tempo perdido, respeitando as restrições temporais.

SciPy é a biblioteca de computação científica; `linprog` é sua interface de programação linear; HiGHS é o solucionador numérico usado por essa chamada. As variáveis desse subproblema são contínuas: horários de início de serviço e variáveis auxiliares de espera. As restrições incluem encadeamento temporal dos eventos, janelas, limites de permanência a bordo e duração da rota. A verificação de cobertura, pareamento, precedência e capacidade também é feita pelo código do projeto.

Como a ordem já foi fixada, os deslocamentos e `f1` dessa rota já estão definidos. O SciPy melhora os horários e, portanto, `f2`; ele não procura todas as rotas nem decide a alocação global dos passageiros. GA, SA, GRASP, ACO, enumeração, operadores e construção gulosa foram programados no projeto, sem uma biblioteca externa que forneça esses algoritmos prontos. NumPy dá suporte aos dados numéricos.

O avaliador também oferece as políticas `cedo` e `bordo`, que não utilizam essa programação linear para agendar. O menu exige `otimo` para o exato. No código atual, se o solucionador linear retorna insucesso, o avaliador produz uma agenda `bordo` para diagnosticar as violações. Esse retorno não deve ser confundido com uma certificação de horário ótimo em caso de falha numérica. A exatidão temporal pressupõe a solução bem-sucedida dos subproblemas lineares, dentro das tolerâncias numéricas.

## 3. Estrutura e responsabilidade de cada arquivo

```text
Ride-pooling-multi-objetivo/
  implementacao1/             # Método Exato
    __init__.py
    exato.py
    executar.py
  implementacao2/             # Heurística
    __init__.py
    gulosa.py
    executar.py
  implementacao3/             # MetaHeurística
    __init__.py
    ga.py
    sa.py
    grasp.py
    colonia_formigas.py
    aco.py                   # Adaptador do ACO para o executor comum
    base.py
    executar.py
  comum/
    __init__.py
    avaliador.py
    instancia.py
    rede.py
    solucao.py
    cenarios.py
    emissoes.py
    pareto.py
    operadores.py
    leitor_res.py
    validacao.py
  dados/
    exemplo_pequeno.json
    cenario_concorrente_q10.json
    cenario_100_corridas.json
  experimentos/
    exemplo_pequeno.json
    validacao_emissoes.json
    comparacao_emissoes_q1_10.json
    comparacao_100_corridas.json
  menu.py
  requirements.txt
  README.md
  MANUAL.md
```

Cada pasta de implementação contém `executar.py`, um ponto de entrada que chama o executor comum com sua categoria fixa. `implementacao1/__init__.py` exporta a função exata. Os demais arquivos de algoritmo estão fisicamente nas pastas correspondentes. A numeração do menu segue a mesma ordem das pastas: 1 exato, 2 heurística, 3 metaheurísticas.

### Arquivos da raiz

| Arquivo | Função específica |
|---|---|
| `README.md` | Início rápido: instalação e primeira execução. |
| `MANUAL.md` | Este documento: arquitetura, algoritmos, exemplos, formatos e limitações. |
| `requirements.txt` | Lista as dependências externas necessárias: NumPy e SciPy. |

### Código comum e método exato

| Arquivo | Função específica |
|---|---|
| `menu.py` | Ponto de entrada interativo e por argumentos. Lê a configuração, prepara cada Q, escolhe os métodos, mede a busca, reavalia as soluções antes da exportação e grava os quatro arquivos de saída. Inclui cache de agendas e retomada de campanhas. |
| `comum/__init__.py` | Identifica a pasta comum como pacote Python, sem carregar os algoritmos. |
| `comum/instancia.py` | Representa os nós e a instância interna: pedidos, depósitos, capacidade, frota, distâncias, tempos e limites. Oferece a redução para um subconjunto de pedidos. |
| `comum/rede.py` | Representa locais físicos, ruas e requisições; valida o JSON; calcula caminhos na rede e transforma locais físicos em eventos internos de coleta e entrega. |
| `comum/leitor_res.py` | Leitor e rotinas de compatibilidade do formato textual clássico de instâncias. É mantido como suporte ao formato textual clássico no pacote. Os exemplos desta entrega usam JSON. |
| `comum/solucao.py` | Representa rotas e soluções, com depósitos implícitos. Confere cobertura, duplicações, pareamento e precedência; contém construção individual e ferramentas de representação. |
| `comum/avaliador.py` | Agenda as rotas, verifica restrições e calcula `f1`, espera, desvio e `f2`. Contém a chamada ao SciPy/HiGHS e as políticas alternativas de agendamento. É compartilhado por todas as categorias. |
| `comum/cenarios.py` | Cria uma cópia de cenário com outro Q, preservando os demais dados e a frota, salvo alteração explícita de `m`. |
| `comum/emissoes.py` | Prepara os fatores de ruas reproduzíveis, calcula custos ambientais dos caminhos e escolhe o fator de veículo correspondente ao Q. |
| `comum/pareto.py` | Define dominância e filtragem de pontos não dominados; reúne também ferramentas de comparação, incluindo hipervolume. O executor do menu não exporta hipervolume nesta entrega. |
| `implementacao3/colonia_formigas.py` | Núcleo importado e adaptado da branch `colonia-formiga`: construções por inserção de pares, roleta, arquivo Pareto, evaporação e reforço dos feromônios. |
| `comum/validacao.py` | Auditoria das rotas e horários sem chamar o avaliador ou o agendador. Recalcula os objetivos e as restrições com a rede e a matriz ambiental da instância. |
| `implementacao1/exato.py` | Enumera sequências viáveis por subconjunto de pedidos e combina as fronteiras usando programação dinâmica, respeitando a quantidade disponível de veículos. |

### Heurística e metaheurísticas

| Arquivo | Função específica |
|---|---|
| `implementacao2/__init__.py` | Exporta a heurística e seu tipo de resultado. |
| `implementacao2/gulosa.py` | Construção determinística por inserções de menor acréscimo ponderado e normalizado nos objetivos. Registra decisões e pedidos pendentes em caso de bloqueio. |
| `implementacao3/__init__.py` | Exporta as metaheurísticas e fornece a seleção por nome usada pelo menu. |
| `implementacao3/base.py` | Define a interface comum, o resultado de otimização e o arquivo externo de soluções não dominadas, preservando as rotas correspondentes. |
| `comum/operadores.py` | Implementa construções e movimentos sobre soluções: inserções e modificações de pedidos/rotas, com verificação de viabilidade. A gulosa também reutiliza ferramentas estruturais deste arquivo; por isso ele não pode ser retirado do pacote. |
| `implementacao3/aco.py` | Adaptador da colônia para a interface comum: recebe os parâmetros do menu, força a mesma política de avaliação e transforma a saída ACO no resultado padrão. |
| `implementacao3/ga.py` | Implementa população, cruzamento, mutação, classificação por dominância e diversidade para o algoritmo genético. |
| `implementacao3/sa.py` | Implementa o resfriamento simulado: vizinhanças, temperatura, aceitação probabilística e trajetórias com diferentes pesos dos objetivos. |
| `implementacao3/grasp.py` | Implementa construções gulosas aleatórias repetidas, lista restrita de candidatos e busca local com diferentes preferências entre objetivos. |

### Entradas de exemplo

| Arquivo | Conteúdo e uso |
|---|---|
| `dados/exemplo_pequeno.json` | Rede de quatro locais físicos e dois pedidos sintéticos. Adequado para entender as rotas e conferir o exato. |
| `dados/cenario_concorrente_q10.json` | Rede e 12 pedidos concorrentes, adequados para estudar agrupamento e capacidade. |
| `dados/cenario_100_corridas.json` | Rede e 100 pedidos com identificadores distintos. Amplia padrões de origens, destinos e horários de um corredor com dez locais físicos; não representa cem localidades distintas nem uma amostra real de cidade. |
| `experimentos/exemplo_pequeno.json` | Seleciona os dois pedidos, `m=2`, Q=1 e 2, sem modelo ambiental, e orçamentos pequenos para demonstração. |
| `experimentos/validacao_emissoes.json` | Usa os dois pedidos com modelo ambiental e Q=1, 2, 5, 7 e 10; permite conferir a mudança de unidade de distância para emissão e as faixas de veículo. |
| `experimentos/comparacao_emissoes_q1_10.json` | Configura os 12 pedidos, Q=1 a 10 e modelo ambiental. Deve usar os métodos aproximados por superar o limite do exato. |
| `experimentos/comparacao_100_corridas.json` | Configura os 100 pedidos completos, `m=100` fixo, Q=1 a 10, modelo ambiental e construção limitada para reduzir custo computacional. |

Não foram incluídos os gráficos antigos, relatórios de campanhas, resultados já calculados, histórico Git, ambiente virtual, caches, scripts antigos de análise ou bibliotecas binárias. Os resultados serão criados pela própria execução.

## 4. Como os algoritmos resolvem o problema

### Método exato

Para cada subconjunto de pedidos que pode ser atendido por um veículo, o código enumera ordens de visita respeitando coleta antes da entrega e faz podas de inviabilidade. O avaliador calcula os horários e os objetivos. As rotas não dominadas de cada subconjunto são combinadas por programação dinâmica para cobrir todos os pedidos sem ultrapassar `m` veículos. A fronteira final contém pares reais de objetivos com suas soluções completas.

Não é simplesmente chamar o SciPy para resolver o problema inteiro: a enumeração e a combinação são código próprio; o SciPy resolve os horários de cada ordem examinada. O menu limita a entrada exata a **seis pedidos** para evitar crescimento combinatório. Esse limite não significa que seis pedidos sejam sempre rápidos. Cem pedidos não devem ser submetidos ao exato.

### GA

O algoritmo genético mantém uma população de soluções completas, gera descendentes por cruzamento e mutação e usa dominância de Pareto e diversidade para selecionar sobreviventes. A adaptação multiobjetivo é inspirada no NSGA-II. Um ponto domina outro quando não é pior em nenhum objetivo e é estritamente melhor em pelo menos um. Um arquivo externo preserva soluções não dominadas encontradas durante a busca. O avaliador fornece os pares `f1,f2` de cada solução viável.

### SA

O simulated annealing começa com uma solução, faz movimentos de vizinhança e pode aceitar pioras com uma probabilidade que diminui com a temperatura. A adaptação executa trajetórias com preferências diferentes — pesos `(0,8; 0,2)`, `(0,5; 0,5)` e `(0,2; 0,8)` — usando uma combinação escalar dos objetivos para conduzir cada trajetória. As soluções descobertas alimentam um arquivo Pareto comum. A combinação guia a busca; o arquivo mantém os dois objetivos separados e as rotas reais.

### GRASP

O GRASP repete uma construção por inserções, sorteando entre candidatos considerados bons, e aplica busca local para melhorar o resultado. Também alterna preferências entre os objetivos e reúne soluções em um arquivo Pareto. Seu resultado depende das construções, dos movimentos, dos pesos, do orçamento e da semente.

### ACO — colônia de formigas

Cada formiga constrói uma solução completa inserindo pares de coleta/entrega em rotas viáveis. A ordem dos pedidos é sorteada. Os candidatos são escolhidos por roleta usando feromônio e uma preferência ponderada pelos acréscimos normalizados dos objetivos. Formigas diferentes usam pesos distribuídos entre os extremos de emissão e tempo perdido. Ao fim de cada iteração, o feromônio evapora e as soluções representantes do arquivo Pareto reforçam seus arcos. O processo repete a construção com essa informação acumulada. Não reproduz uma variante publicada específica.

A integração preserva essa lógica e adapta a emissão, a auditoria e a interface. A auditoria passou a usar distâncias e tempos da rede separadamente e a considerar os fatores ambientais; os feromônios, a roleta e as inserções de pares foram preservados. No menu, o ACO utiliza a política de `parametros_avaliacao`, portanto `otimo` nos exemplos, com as mesmas regras numéricas do avaliador comum. A função direta `resolver_aco` conserva `bordo` como padrão original; não a confunda com a configuração usada pelo menu.

A configuração de cem pedidos tem duas formigas, duas iterações e até 200.000 consultas; o limite de oito posições de inserção é herdado do bloco `construcao`. A ordem dos pedidos do ACO continua sorteada, enquanto a construção limitada dos demais métodos pode priorizar horários. Ao atingir o orçamento, somente construções completas entram na saída. Isso pode resultar em uma fronteira vazia, sem provar inviabilidade.

### Heurística gulosa

Parte de rotas vazias. Em cada etapa examina inserções viáveis de uma coleta e sua entrega, compara os acréscimos dos objetivos, normaliza-os entre os candidatos da etapa e escolhe a menor soma ponderada. O peso de emissão padrão é 0,5. Empates são tratados deterministicamente. Não há repetição aleatória nem busca local após a construção. Produz uma solução ou informa bloqueio e os pedidos ainda pendentes; bloqueio não prova que a instância seja inviável.

Na configuração de 100 pedidos, a construção dos métodos anteriores ao ACO escolhe o próximo pedido por horário desejado e examina até oito pares de posições por rota, em vez de enumerar todas as alternativas. Isso limita a exploração, não a quantidade de pedidos: os cem continuam sendo exigidos. A frota de cem veículos ajuda a viabilidade em Q=1 no cenário concorrente. Não é uma imposição de usar cem veículos em todos os Q.

As metaheurísticas não garantem a fronteira ótima. Uma execução por semente e orçamentos diferentes não permitem concluir um ranking científico entre métodos.

## 5. Instalação e execução

### Windows

Extraia o ZIP. Abra um terminal **na pasta raiz da branch `apresentacao`**, onde estão `README.md` e `requirements.txt`. Instale Python 3.10 ou superior; a validação desta entrega utiliza Python 3.12. Não é necessário ativar o ambiente virtual no PowerShell.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe menu.py
```

A instalação de NumPy e SciPy exige internet ou os pacotes disponíveis localmente. O ZIP não contém o interpretador nem um ambiente virtual portátil. As dependências não foram fixadas em versões para permitir que o instalador escolha versões compatíveis com o Python. O ambiente de validação utilizou Python 3.12.14, NumPy 2.5.3 e SciPy 1.18.1.

No Linux/macOS, os equivalentes são `python3 -m venv .venv`, `.venv/bin/python -m pip install -r requirements.txt` e `.venv/bin/python menu.py`.

### Menu interativo

As opções são: 1 — exato; 2 — gulosa; 3 — metaheurísticas; 4 — comparar todas as categorias em entrada pequena; 5 — comparar aproximados em entradas maiores; 0 — sair. Informe uma **configuração de experimento**, não diretamente um arquivo de `dados/`. Enter aceita o exemplo pequeno como padrão. É possível escolher um Q ou usar todos os Q da configuração. Nas metaheurísticas, escolha SA, GA, GRASP e/ou ACO e uma semente. No submenu de metaheurísticas, 1 seleciona SA, 2 GA, 3 GRASP, 4 todas e 5 ACO. Na gulosa, o peso de emissão varia de 0 a 1; o menu aceita vírgula decimal.

### Execução por argumentos

Nos comandos abaixo, use o Python do ambiente virtual. Todos os caminhos relativos de entrada e saída são resolvidos a partir da raiz da entrega.

```powershell
# As seis implementações, Q=1 e 2, caso pequeno
.\.venv\Scripts\python.exe menu.py --modo comparar --config experimentos/exemplo_pequeno.json --saida resultados/demonstracao

# Somente o exato, Q=2
.\.venv\Scripts\python.exe menu.py --modo exato --config experimentos/exemplo_pequeno.json --q 2 --saida resultados/exato

# Somente as quatro metaheurísticas, uma semente
.\.venv\Scripts\python.exe menu.py --modo metaheuristica --config experimentos/exemplo_pequeno.json --algoritmos sa ga grasp aco --seed 42 --saida resultados/metas

# Somente a heurística determinística
.\.venv\Scripts\python.exe menu.py --modo heuristica --config experimentos/exemplo_pequeno.json --peso-emissao 0.5 --saida resultados/gulosa

# Verificação ambiental pequena
.\.venv\Scripts\python.exe menu.py --modo comparar --config experimentos/validacao_emissoes.json --q 2 --saida resultados/ambiental

# 12 pedidos e Q=1 a 10: cinco métodos aproximados
.\.venv\Scripts\python.exe menu.py --modo comparar_aproximados --config experimentos/comparacao_emissoes_q1_10.json --seed 42 --saida resultados/12_corridas

# 100 pedidos e Q=1 a 10: cinco métodos aproximados
.\.venv\Scripts\python.exe menu.py --modo comparar_aproximados --config experimentos/comparacao_100_corridas.json --seed 42 --saida resultados/100_corridas
```

`--q 1 5 10` substitui a lista de capacidades da configuração. `--algoritmos ga` seleciona apenas GA entre as metaheurísticas; em `comparar_aproximados`, a gulosa continua incluída. `--seed` tem padrão 42 e representa uma execução por método/Q; a gulosa e o exato não usam essa semente. `--peso-emissao` afeta a construção gulosa, não os pesos internos de SA/GRASP nem o critério do resumo.

Os cenários grandes podem demorar bastante. Sem `--saida`, cada execução recebe uma pasta própria em `resultados/menu/execucao-...`. Ao repetir explicitamente uma pasta sem `--retomar`, os arquivos dessa pasta são substituídos. Para continuar uma campanha interrompida, repita os mesmos argumentos e a mesma pasta, acrescentando `--retomar`. Configuração, opções, entrada e modelo ambiental devem permanecer iguais; a retomada também confere hashes do núcleo comum e das três implementações. Uma campanha já concluída é apenas reconhecida. O salvamento ocorre após cada método/Q; o método em andamento no momento da interrupção precisa ser refeito. Se a interrupção acontecer antes do primeiro salvamento, ainda não haverá checkpoint a retomar.

## 6. Formato de entrada: dois níveis

### 6.1 Dados do problema — `dados/*.json`

O arquivo descreve a cidade e os pedidos, sem precisar fixar Q. Consulte `dados/exemplo_pequeno.json` como exemplo completo válido. JSON exige aspas duplas, ponto decimal, ausência de comentários e ausência de vírgula após o último item. Salve em UTF-8.

| Campo | Significado |
|---|---|
| `versao_formato` | Versão do esquema; os exemplos utilizam 1. |
| `nome`, `descricao` | Identificação e contexto dos dados. |
| `unidades` | Nos exemplos: distância `km`, tempo `min`, demanda `passageiros`. Não misture metros e quilômetros. |
| `m` | Frota máxima disponível na instância; a configuração de experimento pode substituí-la. |
| `T_max` | Duração máxima de uma rota, em minutos. |
| `L_arquivo` | Limite de tempo a bordo usado quando `alpha` é nulo. |
| `deposito_origem_id`, `deposito_destino_id` | Identificadores dos locais físicos de saída e retorno. Podem apontar para a mesma garagem. |
| `janela_deposito_ini`, `janela_deposito_fim` | Limites de operação dos depósitos, em minutos. |
| `parametros_avaliacao` | Parâmetros de avaliação da instância; o executor utiliza os parâmetros presentes na configuração do experimento. |
| `rede` | Locais e ruas descritos adiante. |
| `requisicoes` | Lista de pedidos de transporte. |

`rede.direcionado = false` torna cada aresta utilizável nos dois sentidos. Com `true`, uma ligação no sentido contrário precisa existir explicitamente. Em `rede.nos_fixos`, cada local possui `id` único, nome opcional, coordenadas `x,y` e tempos de serviço `s_embarque,s_desembarque`. As coordenadas representam os locais; no exemplo com arestas explícitas, são as distâncias e os tempos das ruas que orientam os deslocamentos.

Cada item de `rede.arestas` possui `origem`, `destino`, `distancia` em km e `tempo` em minutos. Não é necessário ligar diretamente todos os pares: o código calcula caminhos pela rede. É necessário haver caminhos entre os locais utilizados. Use valores finitos e não negativos e uma rede consistente. No modelo ambiental, use ruas explícitas; a preparação também confere a compatibilidade entre os caminhos de distância e os tempos usados na avaliação.

Exemplo de pedido:

```json
{
  "id": 101,
  "origem_id": 1,
  "destino_id": 3,
  "q": 1,
  "e_coleta": 30,
  "l_coleta": 35,
  "e_entrega": 0,
  "l_entrega": 1440
}
```

`id` identifica o pedido nos dados de origem. `origem_id` e `destino_id` apontam para locais físicos diferentes. `q` minúsculo é a demanda desse pedido: um grupo indivisível de `q` passageiros. Não é a capacidade Q do veículo. As janelas são intervalos de início de serviço: `e` indica o mais cedo e `l`, o mais tarde. Tempos são minutos relativos à origem temporal adotada no arquivo; 30 significa minuto 30, não necessariamente 00h30 de um dia real. Os campos opcionais `s_coleta,s_entrega` permitem informar serviço específico do pedido; caso contrário, são usados os tempos dos locais.

A janela `[0,1440]` representa a convenção de janela livre utilizada pelo leitor; as demais restrições, como encerramento do depósito, continuam valendo. O horário desejado interno `rho` é derivado da interpretação das janelas, e não um campo independente dos exemplos. Com janela restrita na coleta, utiliza-se seu início como referência. `alpha=2` limita o tempo a bordo em função do tempo direto; com `alpha=null`, utiliza-se `L_arquivo`. `phi=1` sem modelo ambiental permite interpretar `f1` como distância.

**Há três identificações diferentes:** local físico, pedido externo e evento interno. No exemplo, os locais físicos são 0, 1, 2 e 3; os pedidos externos são 101 e 102; as coletas internas são 1 e 2 e as entregas internas são 3 e 4. Para `n` pedidos, o pedido interno `i` tem entrega `i+n`. Pedidos distintos podem compartilhar um local físico e ainda assim possuem eventos internos diferentes. Após seleção/redução, a numeração dos eventos corresponde à instância reduzida.

### 6.2 Configuração — `experimentos/*.json`

Exemplo completo reduzido:

```json
{
  "instancia": "dados/exemplo_pequeno.json",
  "pedidos": [1, 2],
  "m": 2,
  "capacidades": [1, 2],
  "cache_agendas": true,
  "coletas_antes_de_qualquer_entrega": true,
  "parametros_avaliacao": {"phi": 1, "alpha": 2, "politica": "otimo"},
  "algoritmos": {
    "sa": {"temp_inicial": 1, "temp_final": 0.5, "fator_resfriamento": 0.6, "iter_por_temp": 3},
    "ga": {"tamanho_populacao": 6, "geracoes": 2},
    "grasp": {"max_iteracoes": 2, "max_passos_busca_local": 2},
    "aco": {"formigas": 4, "iteracoes": 3, "max_avaliacoes": 2000}
  }
}
```

`instancia` aponta para o arquivo físico, com caminho relativo à raiz da entrega. `pedidos` contém **índices internos**, de 1 ao número de pedidos do arquivo, não os IDs externos 101/102. Para usar todos os pedidos, liste todos esses índices. `m` define a frota máxima de todos os Q. `capacidades` define os Q positivos a testar; o menu ordena e elimina repetições. O cache reaproveita agendas de rotas idênticas dentro de uma execução de método, sem substituir a reavaliação final.

`coletas_antes_de_qualquer_entrega` declara que a entrada é concorrente: a preparação verifica se nenhuma entrega pode acontecer antes do encerramento das janelas de coleta. Essa declaração só deve ser usada quando verdadeira. A avaliação continua verificando os horários reais.

`algoritmos` define os orçamentos. No SA, temperaturas, resfriamento e iterações por temperatura controlam a duração da busca. No GA, população e gerações controlam a quantidade de soluções exploradas. No GRASP, iterações e passos de busca local controlam repetições e melhoria. No ACO, `formigas` e `iteracoes` controlam construções; `max_avaliacoes` limita consultas de candidatos (incluindo acertos de cache), e `limite_segundos` pode impor um limite de tempo. `a` e `b` controlam a influência do feromônio e do custo; `evaporacao`, `tau_inicial`, `tau_min`, `tau_max` e `representantes` regulam o aprendizado. Não coloque `politica` dentro de `algoritmos.aco`: no menu ela vem do avaliador comum. Aumentá-los tende a aumentar o custo computacional, sem garantir melhora em cada execução.

O bloco opcional `construcao`, presente no cenário de cem pedidos, limita candidatos de inserção: `limite_pedidos_candidatos` e `limite_posicoes_insercao`. Não reduz a obrigação de atender o conjunto completo de pedidos.

**Atenção aos campos herdados nas configurações:** `sementes`, `referencia` e `saida` são metadados dos experimentos originais. Neste executor, a semente efetiva vem de `--seed` ou do menu; não há laço automático sobre `sementes`. A referência é determinada pelos métodos realmente executados, e a pasta vem de `--saida` ou de uma nova pasta automática. Não altere apenas esses três metadados esperando modificar o comportamento do menu.

### 6.3 Modelo ambiental

As configurações ambientais incluem `modelo_emissoes`, contendo categorias de veículos e fatores de ruas. Não é necessário um terceiro arquivo. As categorias incluídas são hipóteses sintéticas:

| Q | Categoria | Fator do veículo, g CO2/km |
|---|---|---:|
| 1–4 | Automóvel | 180 |
| 5–6 | Veículo familiar | 250 |
| 7–10 | Van | 350 |
| 11–20 | Micro-ônibus | 500 |

Esses números não foram medidos nem copiados como tabela validada das referências bibliográficas; representam uma hipótese experimental. Q dentro de uma mesma faixa utiliza o mesmo fator. A documentação bibliográfica da configuração dá contexto, não calibração desses valores específicos.

`modelo_emissoes.ruas` contém `seed=20261004`, `fator_min=1.0` e `fator_max=1.15`. A preparação sorteia fatores limitados para os trechos e produz uma matriz ambiental associada aos caminhos. A mesma realização das ruas é usada por todos os métodos e Q da campanha. A semente de ruas é distinta da semente de busca, cujo padrão é 42.

Para cada veículo utilizado:

```text
emissão = phi(Q) × soma(distância de cada trecho × fator daquele trecho)
```

O total inclui os deslocamentos da garagem até os atendimentos e o retorno. Não modela explicitamente marcha lenta, partida a frio, fabricação do veículo ou ciclo de vida. O fator de rua muda o custo ambiental; ele não altera automaticamente o tempo de deslocamento. Os caminhos são preparados a partir da rede; esta versão não busca itinerários físicos alternativos de menor emissão em cada trecho.

O aumento de Q pode permitir maior compartilhamento, mas também pode mudar `phi`. Portanto, a emissão não precisa cair monotonamente com Q. Para utilizar capacidades fora das faixas disponíveis, é necessário definir categorias que as cubram.

## 7. Saída: quatro arquivos por campanha

```text
resultados/demonstracao/
  RESUMO.md
  metricas.csv
  solucoes.csv
  execucoes.json
```

### `RESUMO.md`: leitura humana

Apresenta uma solução real por método/Q, junto com status, objetivos, veículos usados e quantidade de pontos encontrados. Se um método encontrou vários pontos, o resumo escolhe o mais próximo do ideal pela distância euclidiana dos objetivos normalizados, com pesos iguais. Os limites da normalização vêm da referência do mesmo Q.

Essa escolha é uma convenção de apresentação, não uma prova de uma única melhor solução multiobjetivo. Os dois objetivos da linha pertencem à **mesma solução**. A escolha do resumo não muda a busca. Durante uma campanha parcial, a referência empírica ainda pode crescer e alterar o representante selecionado.

No exemplo pequeno, a fronteira exata para Q=2 tem os pares `(46 km; 4,5 passageiro-minutos)` e `(92 km; 0 passageiro-minutos)`. O primeiro agrupa e percorre menos distância com alguma perda de tempo; o segundo evita essa perda com maior distância. Não existe nesse gabarito a combinação fictícia `(46; 0)`.

### `metricas.csv`: uma linha resumida por método/Q

Cabeçalho quando há execuções:

```csv
Q,categoria,metodo,status,f1,f2,veiculos_usados,tempo_busca_s,pontos,solucao_id
```

| Coluna | Interpretação |
|---|---|
| `Q` | Capacidade do cenário. |
| `categoria` | `exato`, `metaheuristica` ou `heuristica`. |
| `metodo` | `exato`, `sa`, `ga`, `grasp`, `aco` ou `gulosa`. |
| `status` | Estado de conclusão/construção, descrito abaixo. |
| `f1`, `f2` | Objetivos do representante real escolhido para a linha. A unidade de f1 consta do resumo/JSON. |
| `veiculos_usados` | Quantidade de rotas não vazias dessa solução, e não a frota máxima `m`. |
| `tempo_busca_s` | Segundos da execução do método; não inclui a reavaliação posterior para exportação. |
| `pontos` | Quantidade de soluções não dominadas retornadas pelo método; não é número de pedidos nem de veículos. |
| `solucao_id` | Identificador para localizar exatamente a mesma solução em `solucoes.csv` e `execucoes.json`. |

Os CSVs usam vírgula como separador, ponto decimal e UTF-8 com BOM. No Excel configurado em português, utilize importar texto/CSV e selecione vírgula como delimitador se a abertura direta agrupar tudo em uma coluna. Células vazias de objetivos em uma execução sem solução não representam zero.

### `solucoes.csv`: todas as soluções retornadas

```csv
solucao_id,Q,categoria,metodo,f1,f2,distancia_km,veiculos_usados,rotas_json
```

Uma linha corresponde a um par de objetivos e às rotas que o realizam. `distancia_km` permanece disponível mesmo quando `f1` é emissão. `rotas_json` é uma lista de sequências internas, codificada como JSON dentro da célula CSV; um leitor CSV reconhece o escape das aspas. `[]` representa um veículo não utilizado. Depósitos são implícitos.

Por exemplo, com dois pedidos, `[[1,2,4,3]]` significa: sair do depósito, coletar o pedido 1, coletar o pedido 2, entregar o pedido 2, entregar o pedido 1 e retornar. Os números são eventos internos, não os identificadores dos locais físicos. Para interpretar programas, leia o CSV com uma biblioteca CSV e depois aplique um leitor JSON a `rotas_json`.

### `execucoes.json`: registro detalhado e retomada

| Campo de raiz | Conteúdo |
|---|---|
| `config` | Configuração lida para a execução. |
| `opcoes` | Modo, métodos, semente, peso da gulosa e capacidades efetivamente usados. |
| `unidade_f1` | `km` ou `g_CO2`. |
| `input_sha256` | Hash do arquivo de dados utilizado. |
| `ambiente_emissoes` | Realização ambiental e informações necessárias à reprodução; nulo sem ambiente. |
| `fontes_sha256` | Identifica as versões dos códigos utilizados. |
| `referencias` | Fronteira de referência separada por Q, com tipo e pares de objetivos. |
| `execucoes` | Lista com um registro por método/Q. |
| `concluida` | Indica se toda a campanha terminou. Não significa que todos os métodos encontraram solução. |
| `retomadas` | Quando existente, registra retomadas e quantidade de execuções preservadas. |

Cada item de `execucoes` contém `Q`, `categoria`, `metodo`, `status`, `phi_g_km`, `seed`, `tempo_busca_s`, `pontos`, `historico` e `pedidos_pendentes`. A semente é nula para exato e gulosa. No exemplo de distância, o valor de `phi_g_km` é 1 por compatibilidade de campo; consulte `unidade_f1` antes de interpretá-lo como fator físico de emissão.

Cada item de `pontos` contém:

- `solucao_id`, `f1`, `f2`: identidade e par de objetivos.
- `distancia_km`, `espera`, `desvio`: distância física e decomposição de `f2`.
- `veiculos_usados`, `carga_maxima`: uso de frota e maior ocupação observada.
- `rotas`: sequências de eventos, incluindo posições vazias de veículos não usados quando presentes na solução.
- `agendas`: dados das rotas não vazias, na mesma ordem relativa: `B` registra início do serviço por evento, `partida` o instante de saída do depósito e `carga` a ocupação após os eventos. As chaves numéricas de dicionários aparecem como texto no JSON. Os instantes estão em minutos; não são durações entre eventos. O retorno ao depósito não aparece como evento adicional na sequência exportada.

`historico` do ACO inclui uma entrada final `tipo="resumo_aco"` com `motivo_parada` (`iteracoes`, `avaliacoes` ou `tempo`), consultas, acertos de cache, chamadas ao agendamento linear, construções, fracassos e interrupções. `status=concluida` no menu significa que há soluções completas, mesmo se um orçamento encerrou a busca antes de todas as iterações.

`historico` varia por método: pode registrar passos de construção, evolução por geração ou iteração. `pedidos_pendentes` é particularmente útil quando a gulosa fica bloqueada. O arquivo é detalhado para auditoria e retomada; para leitura inicial, comece pelo resumo e pelos CSVs.

### Referência e estados

Quando o modo inclui o exato, a referência vem da enumeração para o mesmo Q. Nos modos aproximados, é a união não dominada das soluções dos métodos efetivamente executados. **A referência empírica não é um resultado do artigo, uma solução conhecida da base nem um ótimo certificado.**

O exato retorna `otimo` ao concluir com soluções ou `inviavel` ao concluir a enumeração sem soluções do modelo. As metaheurísticas retornam `concluida` quando encontram pontos ou `sem_solucao_encontrada` quando não encontram. A gulosa pode retornar `concluida` ou `bloqueada`. Falha de construção ou ausência de solução em busca aproximada não provam inviabilidade. A conclusão exata depende das hipóteses do modelo e do funcionamento numérico do avaliador.

O resumo arredonda objetivos para duas casas; JSON e CSV preservam mais precisão. Não use apenas a impressão arredondada para comparar igualdade ou dominância.

## 8. Conferência, reprodução e problemas comuns

A validação da entrega executou doze combinações no caso de distância e seis no caso ambiental, além de testes do ACO, dos três executores e do menu. A referência exata pequena esperada é `[[46.0,4.5],[92.0,0.0]]` para Q=2. Para conferir localmente, execute a comparação pequena da seção 5.

Use entrada, configuração, semente de busca, semente de ruas e versões das bibliotecas iguais ao comparar reproduções. O tempo de execução depende da máquina; pequenas diferenças numéricas podem depender das versões do solucionador. Não foram repetidas as campanhas completas de 12 e 100 pedidos nem a instalação das dependências do zero. O cenário de cem pedidos foi incluído como entrada, não como obrigação de executar toda a campanha na conferência rápida do pacote.

| Situação | Como proceder |
|---|---|
| `py` ou Python não encontrado | Instale Python e abra outro terminal; se necessário utilize o caminho completo do interpretador. |
| NumPy/SciPy ausente | Instale `requirements.txt` com o mesmo Python usado para executar o menu. |
| Erro de campo `capacidades`/`instancia` | Provavelmente foi fornecido um arquivo de dados em vez de uma configuração de `experimentos/`. |
| Arquivo de entrada não encontrado | Preserve a estrutura extraída e confira os caminhos relativos à raiz da apresentação. |
| Exato rejeita 12 ou 100 pedidos | Use `comparar_aproximados`, `metaheuristica` ou `heuristica`; não reduza silenciosamente a entrada. |
| Configuração concorrente rejeitada | Confira as janelas e os tempos; a declaração de concorrência precisa corresponder à rede. |
| Gulosa bloqueada | Consulte pendentes e restrições; também pode ser consequência das escolhas anteriores ou limites da construção. |
| Alteração recusada na retomada | Use os arquivos/opções originais ou inicie uma nova pasta para a nova configuração. |
| JSON difícil de ler | Abra `RESUMO.md` e `metricas.csv`; use o JSON para rastrear uma `solucao_id` específica. |
| CSV inteiro em uma coluna | Importe com separador vírgula e decimal ponto. |

Esta entrega concentra execução e auditoria básica. Não gera automaticamente os painéis e gráficos históricos, nem constitui validação estatística das metaheurísticas. Para comparação acadêmica posterior, amplie sementes e instâncias e defina orçamentos comparáveis; para fatores ambientais físicos, calibre o modelo com dados de frota e tráfego adequados ao estudo.


## 9. Executar especificamente a colônia de formigas

Após extrair e instalar conforme a seção 5:

```powershell
.\.venv\Scripts\python.exe menu.py --modo metaheuristica --algoritmos aco --config experimentos/exemplo_pequeno.json --q 2 --seed 42 --saida resultados/aco_pequeno
```

Para comparar todos os métodos no pequeno, `--modo comparar` inclui exato, SA, GA, GRASP, ACO e gulosa. Para uma comparação maior, `--modo comparar_aproximados` inclui SA, GA, GRASP, ACO e gulosa. O formato dos quatro arquivos de saída é o mesmo; as linhas do ACO usam `metodo=aco` e `categoria=metaheuristica`.

As pastas implementacao1, implementacao2 e implementacao3 contêm os algoritmos reais, não apenas atalhos. A pasta comum contém os componentes compartilhados. Não é necessário trocar de branch ou anexar manualmente arquivos ao ZIP. Esta edição já contém a integração. Não foram incorporados os gráficos/resultados históricos da outra branch nem substituído o núcleo comum pelo código antigo. Campanhas anteriores não ganham resultados ACO automaticamente; para comparações com ele, gere uma nova campanha/pasta com o código atualizado.


## 10. Demonstração por pasta



```powershell
.\.venv\Scripts\python.exe menu.py
```

No menu: 1 = exato; 2 = heurística; 3 = metaheurísticas; 4 = comparar as três
categorias; 5 = comparar aproximados; 0 = sair. Para a demonstração pequena,
selecione 4 e aceite os padrões com Enter. São executados os seis métodos
com Q=1 e Q=2. A pasta dos resultados é informada ao final.

Também é possível rodar cada pasta diretamente:

```powershell
.\.venv\Scripts\python.exe implementacao1/executar.py --q 2 --saida resultados/exato
.\.venv\Scripts\python.exe implementacao2/executar.py --q 2 --saida resultados/heuristica
.\.venv\Scripts\python.exe implementacao3/executar.py --q 2 --seed 42 --saida resultados/metaheuristicas
```

As três chamadas usam o exemplo de dois pedidos por padrão. Na terceira,
`--algoritmos aco` permite selecionar apenas a colônia de formigas.

Para comparar tudo com uma única chamada:

```powershell
.\.venv\Scripts\python.exe menu.py --modo comparar --config experimentos/exemplo_pequeno.json --q 2 --saida resultados/demonstracao
```

Abra resultados/demonstracao/RESUMO.md. Os outros arquivos são metricas.csv,
solucoes.csv e execucoes.json. O manual detalha suas colunas e os formatos de entrada.
O exato é limitado a seis pedidos; para entradas maiores use os aproximados.

O pacote funciona após a extração sem o repositório original, GitHub ou Gurobi.
Não inclui Python nem bibliotecas binárias. Leia MANUAL.md para detalhes.
