# Manual da entrega — Ride-pooling multiobjetivo

Versão atualizada: 18/10/2026, branch `codex/q-variavel`. Código organizado em três implementações, com avaliador e entradas compartilhados. Inclui quatro metaheurísticas próprias e três adaptadores de bibliotecas. O [README.md](README.md) é o guia de execução; este manual detalha o modelo e a arquitetura.

## 1. O que esta entrega resolve

O problema é alocar pedidos de transporte em veículos e ordenar suas coletas e entregas, respeitando capacidade, janelas de atendimento, duração máxima das rotas e tempo máximo a bordo. Cada pedido deve ser atendido integralmente, com coleta anterior à entrega e ambas no mesmo veículo.

Os dois objetivos são minimizados juntos:

- `f1`: distância total em km no exemplo sem modelo ambiental; emissão operacional estimada em gramas de CO2 quando o modelo ambiental está habilitado.
- `f2`: tempo perdido total em passageiro-minutos, formado por espera em relação ao horário desejado e desvio do tempo a bordo em relação à viagem direta. Não é o tempo total de viagem. Por isso, `f2 = 0` pode ocorrer mesmo com deslocamentos longos.

`Q` é a capacidade de cada veículo; `m` é o número máximo de veículos disponíveis. No modo `fixo`, o programa repete o cenário para os Q da configuração. No modo `variavel`, cada candidato escolhe Q junto com as rotas, dentro da lista autorizada. Cada solução tem frota homogênea, embora soluções de uma mesma execução possam ter capacidades diferentes. O número máximo de veículos permanece fixo; o número usado pode mudar. Não há mistura de capacidades dentro de uma mesma solução.

As três categorias exigidas estão presentes: método exato por enumeração, sete metaheurísticas e heurística gulosa independente. SA, GA, GRASP e ACO são próprias; `ga_lib`, `sa_lib` e `pso_lib` usam motores prontos, descritos na seção 12. A colônia de formigas da branch `colonia-formiga` está integrada como quarta metaheurística própria. O método exato disponível no menu é a enumeração descrita adiante; não exige Gurobi.

## 2. Todos utilizam SciPy?

**Sim, com a política `otimo` utilizada nas configurações incluídas, todos os nove métodos compartilham o avaliador que utiliza SciPy.** Por padrão são selecionados seis: exato, gulosa e quatro metaheurísticas próprias. Isso não significa que SciPy implemente seus ciclos de busca.

O trabalho é dividido em duas partes:

1. O algoritmo decide quais pedidos ficam em cada veículo e em qual ordem serão visitados.
2. Para essa ordem já fixada, o avaliador usa `scipy.optimize.linprog(..., method="highs")` para escolher horários de atendimento que minimizem o tempo perdido, respeitando as restrições temporais.

SciPy é a biblioteca de computação científica; `linprog` é sua interface de programação linear; HiGHS é o solucionador numérico usado por essa chamada. As variáveis desse subproblema são contínuas: horários de início de serviço e variáveis auxiliares de espera. As restrições incluem encadeamento temporal dos eventos, janelas, limites de permanência a bordo e duração da rota. A verificação de cobertura, pareamento, precedência e capacidade também é feita pelo código do projeto.

Como a ordem já foi fixada, os deslocamentos e `f1` dessa rota já estão definidos. O SciPy melhora os horários e, portanto, `f2`; ele não procura todas as rotas nem decide a alocação global dos passageiros. Os quatro métodos próprios, enumeração, operadores e construção gulosa foram programados no projeto. Os métodos com sufixo `_lib` delegam a busca ao pymoo ou simanneal. NumPy dá suporte aos dados numéricos.

O avaliador também oferece as políticas `cedo` e `bordo`, que não utilizam essa programação linear para agendar. O menu exige `otimo` para o exato. Se o solver comprova inviabilidade (status 2), o avaliador usa BORDO somente para diagnóstico e mantém a rota marcada como inviável. Falhas técnicas ou numéricas interrompem a execução com erro explícito; não são tratadas como horários ótimos nem como prova de inviabilidade. A programação linear inclui horários próprios dos dois depósitos e permite espera após uma saída limitada pela janela. O retorno considera a abertura do depósito final; essa espera conta na duração da rota.

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
    ga_biblioteca.py          # NSGA-II do pymoo
    sa_biblioteca.py          # SA do simanneal
    pso_biblioteca.py         # PSO do pymoo
    suporte_bibliotecas.py    # Representação, avaliação e quotas dos adaptadores
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
| `requirements.txt` | NumPy, SciPy, pymoo 0.6.2 e simanneal 0.5.0. |

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
| `comum/capacidade.py` | Mantém contextos e caches isolados por Q, escalas globais, escolha/mutação de capacidade, reparo de carga e orçamento comum de consultas. |
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

Os resultados são gerados localmente em `resultados/`, pasta ignorada pelo Git.
O ambiente virtual e as bibliotecas binárias também não pertencem ao código
versionado. Os scripts atuais de comparação e auditoria ficam em `experimentos/`.

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

A integração adapta emissão, auditoria e interface. A auditoria usa distâncias e tempos da rede separadamente e considera os fatores ambientais. No menu, o ACO utiliza a política de `parametros_avaliacao`, portanto `otimo` nos exemplos, com as mesmas regras numéricas do avaliador comum. A função direta `resolver_aco` conserva `bordo` como padrão original; não a confunda com a configuração usada pelo menu. No modo variável, cada formiga escolhe Q antes das inserções, com feromônio de capacidade, exploração uniforme mínima de 10% e trilhas de arcos separadas por Q. Os pontos globais não dominados reforçam as capacidades e trilhas correspondentes. `aprender=False` desativa também o aprendizado de Q.

A configuração de cem pedidos tem duas formigas, duas iterações e até 200.000 consultas; o limite de oito posições de inserção é herdado do bloco `construcao`. A ordem dos pedidos do ACO continua sorteada, enquanto a construção limitada dos demais métodos pode priorizar horários. Ao atingir o orçamento, somente construções completas entram na saída. Isso pode resultar em uma fronteira vazia, sem provar inviabilidade.

### Heurística gulosa

Parte de rotas vazias. Em cada etapa examina inserções viáveis de uma coleta e sua entrega, compara os acréscimos dos objetivos, normaliza-os entre os candidatos da etapa e escolhe a menor soma ponderada. O peso de emissão padrão é 0,5. Empates são tratados deterministicamente. Não há repetição aleatória nem busca local após a construção. Produz uma solução ou informa bloqueio e os pedidos ainda pendentes; bloqueio não prova que a instância seja inviável.

Na configuração de 100 pedidos, a construção dos métodos anteriores ao ACO escolhe o próximo pedido por horário desejado e examina até oito pares de posições por rota, em vez de enumerar todas as alternativas. Isso limita a exploração, não a quantidade de pedidos: os cem continuam sendo exigidos. A frota de cem veículos ajuda a viabilidade em Q=1 no cenário concorrente. Não é uma imposição de usar cem veículos em todos os Q.

As metaheurísticas não garantem a fronteira ótima. Uma execução por semente e orçamentos diferentes não permitem concluir um ranking científico entre métodos.

## 5. Instalação e execução

### Windows

Abra um terminal **na pasta raiz do projeto**, onde estão `README.md` e `requirements.txt`. Use Python 3.10 ou superior; a instalação limpa desta versão foi validada em Python 3.14.6 no Windows. Não é necessário ativar o ambiente virtual no PowerShell.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe menu.py
```

A instalação exige internet ou os pacotes disponíveis localmente. O projeto não contém um ambiente virtual portátil. As versões dos motores estão fixadas em `pymoo==0.6.2` e `simanneal==0.5.0`; NumPy e SciPy são resolvidos pelo instalador. A validação atual utilizou Python 3.14.6, NumPy 2.5.4 e SciPy 1.18.1. Outras versões de Python não foram certificadas nesta validação.

No Linux/macOS, os equivalentes são `python3 -m venv .venv`, `.venv/bin/python -m pip install -r requirements.txt` e `.venv/bin/python menu.py`.

### Menu interativo

**Para rodar 100 corridas: digite 6 e pressione Enter.**

Essa opção executa SA, GA, GRASP, ACO e gulosa, com Q de 1 a 10 e semente 42:
50 execuções ao todo. São usados os 100 pedidos completos e o modelo de CO2.
Não é necessário informar caminhos, capacidade ou outros parâmetros.

O programa mostra a pasta de saída e avisa quando inicia e termina cada método/Q.
Abra o `RESUMO.md` dessa pasta para consultar os resultados. A campanha pode
demorar; os resultados são salvos ao término de cada método/Q.

Outras opções: 1 = exato; 2 = heurística; 3 = metaheurísticas; 4 = comparar as três
categorias no pequeno; 5 = comparar aproximados; 0 = sair.
Depois de escolher uma dessas opções, selecione o exemplo pelo número:

| Número do exemplo | Entrada |
|---|---|
| 1 | 2 corridas — distância |
| 2 | 2 corridas — emissão de CO2 |
| 3 | 12 corridas — emissão de CO2 |
| 4 | 100 corridas — emissão de CO2 |
| 5 | Caminho de uma configuração própria |
| 0 | Voltar |

As opções com exato oferecem apenas os exemplos pequenos e a configuração
própria, sujeita ao limite de seis pedidos. Para rodar somente uma metaheurística
com 100 corridas, selecione 3 no menu principal, 4 no exemplo, Enter para todos
os Q e escolha a metaheurística. Para somente a gulosa, use 2, 4 e Enter.

Para a demonstração pequena, escolha 4 no menu principal e aceite os três padrões
com Enter (exemplo, Q e metaheurísticas). A semente fica em 42 e o peso da gulosa
em 0,5. Para alterar esses parâmetros, utilize os argumentos de execução.

No campo Q, Enter seleciona todas as capacidades do exemplo. Também é possível
digitar um inteiro ou uma lista separada por vírgulas/espaços, por exemplo
`2` ou `1, 5, 10`. Valores inválidos são solicitados novamente. Caminhos de
arquivos só precisam ser digitados ao escolher o exemplo 5. A opção 6 do menu
principal é o atalho completo de cem corridas e dispensa essas perguntas.

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
Q,categoria,metodo,status,f1,f2,veiculos_usados,tempo_busca_s,pontos,solucao_id,origem,biblioteca,versao_biblioteca
```

| Coluna | Interpretação |
|---|---|
| `Q` | Capacidade do cenário. |
| `categoria` | `exato`, `metaheuristica` ou `heuristica`. |
| `metodo` | `exato`, `sa`, `ga`, `grasp`, `aco`, `ga_lib`, `sa_lib`, `pso_lib` ou `gulosa`. |
| `status` | Estado de conclusão/construção, descrito abaixo. |
| `f1`, `f2` | Objetivos do representante real escolhido para a linha. A unidade de f1 consta do resumo/JSON. |
| `veiculos_usados` | Quantidade de rotas não vazias dessa solução, e não a frota máxima `m`. |
| `tempo_busca_s` | Segundos da execução do método; não inclui a reavaliação posterior para exportação. |
| `pontos` | Quantidade de soluções não dominadas retornadas pelo método; não é número de pedidos nem de veículos. |
| `solucao_id` | Identificador para localizar exatamente a mesma solução em `solucoes.csv` e `execucoes.json`. |
| `origem`, `biblioteca`, `versao_biblioteca` | Implementação própria ou de biblioteca, pacote e versão do motor efetivamente executado. |

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

A validação da entrega executou doze combinações no caso de distância e seis no caso ambiental, além de testes do ACO, dos três executores e do menu. Na simplificação do menu, passaram nove testes de navegação e execução; um deles executou a gulosa com os cem pedidos completos em Q=1 e conferiu cobertura e objetivos exportados. A referência exata pequena esperada é `[[46.0,4.5],[92.0,0.0]]` para Q=2. Para conferir localmente, execute a comparação pequena da seção 5.

Use entrada, configuração, semente de busca, semente de ruas e versões das bibliotecas iguais ao comparar reproduções. O tempo de execução depende da máquina; pequenas diferenças numéricas podem depender das versões do solucionador. Na atualização de 18/10/2026 foram validados a instalação em ambiente virtual limpo, os 26 testes anteriores mais as integrações de bibliotecas, o pequeno com referência exata e os pilotos com 12 e 100 pedidos completos. Os pilotos usam limites curtos, sem estabelecer um ranking científico. Para conferir rapidamente, comece pelo exemplo pequeno do README.

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


## 10. Q variável: decisão conjunta de capacidade e rotas

O modo `fixo` continua sendo o padrão dos experimentos anteriores. Use a opção
**7** no menu para escolher um exemplo, as capacidades permitidas e as
metaheurísticas que vão otimizar Q junto com as rotas. A opção 6 mantém as
50 execuções fixas de cem pedidos. Pela linha de comando:

```powershell
python menu.py --modo comparar --config experimentos/q_variavel_exemplo.json --saida resultados/q_variavel
python menu.py --modo metaheuristica --config experimentos/comparacao_emissoes_q1_10.json --capacidade variavel --q 1 2 3 4 5 6 7 8 9 10 --max-consultas-rotas 20000 --saida resultados/q_variavel_12
```

O novo JSON de exemplo já declara `capacidade: "variavel"`; os demais preservam
o modo fixo. A opção de linha de comando prevalece sobre o JSON. No modo
variável, `capacidades`/`--q` definem o domínio da decisão, e não execuções
separadas. Um domínio de um elemento é válido. Q deve ser inteiro positivo e
estar coberto por exatamente um perfil ambiental. Capacidades menores que
uma demanda indivisível são excluídas da inicialização e registradas.

Cada solução transporta Q e continua usando no máximo `m` veículos da mesma
capacidade. Os dois objetivos permanecem emissão/distância e tempo perdido.
O GA herda/muta Q; o SA altera Q entre estados; o GRASP escolhe Q nos reinícios
e também o modifica na busca local; a ACO escolhe Q por formiga e aprende sua
distribuição com feromônios. Não há garantia de visitar todos os Q sob um
orçamento curto.

Reduções de capacidade removem pares das rotas sobrecarregadas e tentam
reinseri-los no Q pretendido. Se o reparo falha, há uma reconstrução limitada
ou rejeição; o programa não aumenta Q silenciosamente. Modificações de rotas
invalidam partidas externas para que a agenda seja recalculada. O histórico
registra movimentos tentados e aceitos no contexto, sem confundir essa
aceitação estrutural/temporal com a aceitação posterior do estado pelo SA.

Cada Q possui instância, parâmetros e cache próprios; a rede e os fatores de
ruas são preparados uma vez. SA/GRASP comparam candidatos usando escalas
globais fixas da execução: emissão de viagens individuais com o maior phi
do domínio e um limite de tempo perdido calculado da demanda. As escalas
estão em `estatisticas.escalas`; não são recalculadas com phi do candidato.
Dominância continua dependendo só de f1/f2. Em objetivos iguais, o arquivo
prefere menor Q e depois uma ordem canônica de rotas.

No modelo atual, Q maior com o mesmo phi pode reproduzir soluções de Q menor.
Para o domínio 1–10, [4,6,10] preserva a fronteira objetiva, embora omita
capacidades equivalentes. A busca conserva a lista solicitada, sem reduzir
automaticamente o domínio ou penalizar Q. Sem emissão/custo dependente de Q,
a capacidade máxima amplia as opções e não piora a fronteira ótima.

O exemplo novo contém dois pedidos indivisíveis de três passageiros. Sua
fronteira exata global usa Q=4 e Q=6: dois automóveis evitam perda de tempo;
um veículo familiar permite agrupamento com menor emissão total e algum
tempo perdido. Q=10 não melhora essa fronteira. Os fatores ambientais
continuam sendo hipóteses sintéticas, sem calibração física adicional.

No modo variável, exato e gulosa fazem uma varredura do domínio e filtram a
união. O exato segue limitado a seis pedidos e fornece a referência global;
a gulosa é identificada como heurística. Cada metaheurística faz uma única
busca por semente. Nos modos aproximados a referência global é empírica.

O formato de saída é versão 2 (`versao_formato`). Cada ponto possui `Q`,
`phi_g_km`, carga de pico, rotas e agendas completas, incluindo retorno e
`status_agendamento`. No modo ambiental variável, inclui `tipo_veiculo`.
O registro da execução variável possui `Q: null`, `capacidade: "variavel"`,
domínio em `opcoes.capacidades`, `motivo_parada` e `estatisticas`.
`referencias.global` serve à comparação e escolha do representante de todos
os métodos. O resumo/CSV apresenta o Q do ponto selecionado, não um Q comum
a todos os pontos da execução. No modo fixo as referências por Q continuam.

`--max-consultas-rotas N` limita o total de consultas de rotas não vazias por
metaheurística/semente. Acertos de cache contam. No modo variável o orçamento
é compartilhado por todos os Q; no fixo cada Q recebe `N // quantidade_Q`,
sem redistribuir o resto. Construção, avaliação e reparo usam o mesmo limite;
as podas temporais consultadas e caches da ACO também contam. Rejeições
imediatas de capacidade são verificações estruturais e não consultas de
agendamento. Exato e gulosa de referência não são interrompidos por esse
limite. Os limites nativos continuam valendo e podem encerrar antes.

`estatisticas` registra soluções avaliadas, consultas de rotas, agendamentos,
chamadas PL, acertos de cache, visitas por Q, movimentos e reparos. Ao atingir
o limite, somente soluções completas já arquivadas são retornadas. Uma
fronteira vazia não comprova inviabilidade. `motivo_parada` distingue
`consultas_rotas`, limites ACO e término nativo. O limite não iguala tempo
de máquina nem quantidade de resoluções PL entre métodos.

A retomada continua entre métodos concluídos, sem restaurar o estado interno
de uma busca interrompida. Modo, domínio, semente, orçamento, configuração,
ambiente, entrada e hashes dos algoritmos/menu precisam coincidir. Registros
antigos permanecem legíveis como fixos; executar código novo sobre checkpoints
de algoritmos antigos é recusado por incompatibilidade de hashes.

Testes e piloto reproduzível:

```powershell
python -m unittest discover -s tests -v
python experimentos/comparar_q.py --orcamento 2000 --sementes 42 43 44
python experimentos/auditar_q.py resultados/q_variavel resultados/q_variavel_piloto
```

O piloto compara 12 e 100 pedidos com a demanda inteira. Ele eleva os limites
nativos para priorizar o orçamento comum e utiliza a mesma construção limitada
em ambas as modalidades. Produz campanhas detalhadas, `comparacao.json` e
`RESUMO.md` em `resultados/q_variavel_piloto`. O hipervolume usa uma referência
empírica e extremos comuns a todas as modalidades/sementes do mesmo tamanho.
Limites curtos, três sementes e dados sintéticos não estabelecem um ranking
conclusivo. Para uma campanha maior, aumente orçamento e sementes.

## 11. Demonstração por pasta



```powershell
.\.venv\Scripts\python.exe menu.py
```

**Para rodar 100 corridas: digite 6 e pressione Enter.**

Essa opção executa SA, GA, GRASP, ACO e gulosa, com Q de 1 a 10 e semente 42:
50 execuções ao todo. São usados os 100 pedidos completos e o modelo de CO2.
Não é necessário informar caminhos, capacidade ou outros parâmetros.

O programa mostra a pasta de saída e avisa quando inicia e termina cada método/Q.
Abra o `RESUMO.md` dessa pasta para consultar os resultados. A campanha pode
demorar; os resultados são salvos ao término de cada método/Q.

Outras opções: 1 = exato; 2 = heurística; 3 = metaheurísticas; 4 = comparar as três
categorias no pequeno; 5 = comparar aproximados; 0 = sair.
Depois de escolher uma dessas opções, selecione o exemplo pelo número:

| Número do exemplo | Entrada |
|---|---|
| 1 | 2 corridas — distância |
| 2 | 2 corridas — emissão de CO2 |
| 3 | 12 corridas — emissão de CO2 |
| 4 | 100 corridas — emissão de CO2 |
| 5 | Caminho de uma configuração própria |
| 0 | Voltar |

As opções com exato oferecem apenas os exemplos pequenos e a configuração
própria, sujeita ao limite de seis pedidos. Para rodar somente uma metaheurística
com 100 corridas, selecione 3 no menu principal, 4 no exemplo, Enter para todos
os Q e escolha a metaheurística. Para somente a gulosa, use 2, 4 e Enter.

Para a demonstração pequena, escolha 4 no menu principal e aceite os três padrões
com Enter (exemplo, Q e metaheurísticas). A semente fica em 42 e o peso da gulosa
em 0,5. Para alterar esses parâmetros, utilize os argumentos de execução.

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
Não inclui Python nem bibliotecas binárias.

## 12. Metaheurísticas prontas de bibliotecas

O catálogo em `implementacao3/__init__.py` centraliza fábrica, validação,
menu e scripts. Sem `--algoritmos`, a seleção continua sendo `sa ga grasp aco`.
O grupo `bibliotecas` seleciona `ga_lib sa_lib pso_lib`; `todos` seleciona
as sete metaheurísticas. O modo `comparar` acrescenta exato e gulosa.
O menu principal 7 escolhe Q variável; o submenu 7 escolhe SA de biblioteca.
Consulte a tabela completa dos dois menus no README.

### Representação e restrições

`suporte_bibliotecas.py` fornece um vetor de `3n+1` números em `[0,1]` para
GA e PSO: uma chave de Q, `n` chaves de veículos e `2n` prioridades de eventos.
As chaves discretas são convertidas por `min(int(chave*tamanho), tamanho-1)`;
o extremo 1 pertence ao último índice. As capacidades vêm do domínio autorizado,
excluindo as menores que um grupo indivisível de passageiros. Q fixo equivale
a um domínio unitário. O número máximo de veículos não muda com Q.

Dentro de cada veículo, a conversão escolhe o evento disponível de menor
prioridade, desempatando pelo identificador. Uma entrega fica disponível após
sua coleta. Isso garante cobertura, pareamento e precedência, mas não presume
capacidade acumulada ou viabilidade temporal: o avaliador verifica ambas.
A conversão inversa permite fornecer sementes individuais e construídas pelo
projeto aos motores. Vetores aleatórios completam a população.

### Responsabilidade de cada motor

- `ga_biblioteca.py`: usa `pymoo.algorithms.moo.nsga2.NSGA2` e `minimize`.
  Seleção, cruzamento, mutação e sobrevivência são da biblioteca. Os objetivos
  são `f1/escala1` e `f2/escala2`; uma restrição separada recebe a quantidade
  de violações do avaliador, zero para candidato viável.
- `pso_biblioteca.py`: usa `pymoo.algorithms.soo.nonconvex.pso.PSO` e `minimize`.
  Velocidades, posições e melhores partículas são atualizadas pelo pymoo.
  Cada trajetória minimiza a soma ponderada dos objetivos normalizados,
  mantendo a mesma restrição separada usada no GA.
- `sa_biblioteca.py`: especializa `simanneal.Annealer`, com cópia de `Solucao`,
  movimentos de rotas/Q dos operadores comuns e energia ponderada normalizada
  mais `1000 * quantidade_de_violacoes`. Resfriamento e aceitação são do
  `Annealer.anneal`. A semente e o handler SIGINT globais são restaurados.

SA e PSO usam três trajetórias com os pesos `(0,8;0,2)`, `(0,5;0,5)` e
`(0,2;0,8)`, configuráveis por `pesos`. Todos os candidatos viáveis avaliados,
inclusive movimentos rejeitados pelo SA ou partículas que não melhoram o
incumbente, alimentam um arquivo Pareto comum. As escalas são globais entre
capacidades; Q não vira um terceiro objetivo. Os pesos não garantem recuperar
toda a fronteira, principalmente em buscas curtas ou fronteiras não convexas.

### Esforço, parâmetros e rastreabilidade

Quando existe orçamento de consultas, SA e PSO o dividem igualmente entre as
trajetórias; o resto vai para a última. A inicialização também conta. A
construção de sementes recebe até um quarto da quota para reservar esforço
ao motor. Limites nativos podem encerrar antes; sobras de trajetórias que
terminam cedo não são redistribuídas. Mesmo sem uma solução, o método não
ultrapassa o orçamento. Ao atingir o limite, retorna apenas soluções completas
já arquivadas, com histórico e motivo de parada.

Os JSONs usam `tamanho_populacao` e `geracoes` para GA, `iteracoes`,
`temp_inicial`, `temp_final` e `pesos` para SA e `tamanho_populacao`,
`iteracoes` e `pesos` para PSO. `geracoes`/`iteracoes` no pymoo são traduzidos
para `n_gen`, incluindo a população inicial como primeira geração.

As dependências são carregadas somente ao selecionar os novos métodos.
Se faltarem, o erro orienta `python -m pip install -r requirements.txt`;
não há substituição por algoritmo próprio. `ResultadoOtimizacao.estatisticas`
preserva `origem`, `biblioteca`, `versao_biblioteca` e `motor`, além dos
contadores comuns. Esses dados seguem para `execucoes.json`; os três primeiros
também aparecem em `metricas.csv`. Se a demanda elimina todas as capacidades
antes da busca, não há motor executado nem versão a registrar.

Os adaptadores e seu suporte entram nos hashes de retomada. Além de código e
configuração, a retomada verifica as versões dos motores já executados.
Toda solução exportada passa pela auditoria independente. Os testes de
`tests/test_bibliotecas.py` verificam chamadas reais aos motores, codificação,
Q, sementes, orçamentos, metadados, menus, exportação e retomada.

Referências dos motores: [NSGA-II](https://pymoo.org/algorithms/moo/nsga2.html),
[PSO](https://pymoo.org/algorithms/soo/pso.html) e
[simanneal](https://github.com/perrygeo/simanneal).
