# Relatório de Desenvolvimento

> Atualização em 01/10/2026: o protocolo atual está em
> [MODELO_EXPERIMENTAL.md](MODELO_EXPERIMENTAL.md). As fases abaixo são o histórico
> até a Fase 2; já existem SA, GA e GRASP exploratórios e rede fixa. A análise
> atual varia Q=1..20 mantendo o escopo de passageiros. Foram corrigidas a
> inserção na construção, a precedência do fallback e a participação do segundo
> pai no cruzamento; o GA também passou a usar crowding na seleção ambiental.
> A política OTIMO agora exige SciPy explicitamente, sem substituição silenciosa.

**Projeto:** Ride-Pooling vs. Transporte Individual — formulação multiobjetivo entre emissões de CO₂ e tempo perdido pelo usuário  
**Disciplina:** Tópicos Especiais em Sistemas Inteligentes — Otimização Multiobjetivo  
**Escopo deste documento:** registrar o que foi feito em cada fase do desenvolvimento, com ênfase nos problemas encontrados e nas decisões técnicas. Não substitui o relatório acadêmico (`relatorio/main.pdf`); complementa-o com o diário de engenharia.

---

## Visão geral das fases

| Fase | Objetivo | Status |
|------|----------|--------|
| 0 | Modelagem biobjetivo e alinhamento com o professor | Concluída |
| 1 | Leitor de instâncias e avaliador de soluções | Concluída |
| 2 | Gabarito: extremos e fronteira exata em instância pequena | Concluída |
| 3 | Metaheurística NSGA-II | Pendente |
| 4 | Metaheurística MOILS | Pendente |
| 5 | Método ε-restrito + ILS | Pendente |
| 6 | Experimentos, métricas e redação final | Pendente |

---

## Fase 0 — Modelagem

### O que foi feito

- Reformulação do problema a partir do relatório inicial: em vez de emissão + custo (objetivos correlacionados, fronteira degenerada), adotou-se o par **emissão de CO₂ (\(f_1\))** × **tempo perdido pelo usuário (\(f_2\))** (desvio de rota + espera no embarque).
- Prova formal de conflito: \(f_2 = 0\) proíbe agrupamento (nenhum nó entre coleta e entrega); a vantagem do compartilhamento só existe com \(f_2 > 0\).
- Evidência empírica com a solução publicada de `pr01`: distância 190,02 com tempo médio a bordo ~45,6 min para viagem direta ~6,3 min.
- Dois cenários de frota (individual vs. compartilhada) sobre o mesmo conjunto de viagens.
- Plano de solução: NSGA-II, MOILS e ε-restrito + ILS; métricas HV, cobertura e cardinalidade.
- Entregas: `relatorio/main.tex`, `relatorio/resumo_professor.tex` (e PDFs).

### Decisões de modelagem registradas

- Custo operacional **não** entra como objetivo (acompanha a distância quando a frota é homogênea).
- \(L_i = \alpha\,\bar{t}_i\) (limite a bordo proporcional), em vez de constante global do arquivo.
- \(f_2\) em passageiro-minuto, com tempo *excedente* \((R_i - \bar{t}_i)\), não o tempo absoluto a bordo.

---

## Fase 1 — Avaliador

### O que foi feito

Implementação do pacote `codigo/darp/` e da bateria `codigo/experimentos/validar_fase1.py`.

| Arquivo | Papel |
|---------|--------|
| `instancia.py` | Lê coleções `bnc` e `tabu`; normaliza depósito; classifica ida/volta; infere \(\rho_i\) |
| `solucao.py` | Representa rotas; checa cobertura, pareamento e precedência; constrói solução sem agrupamento |
| `avaliador.py` | Agenda horários, calcula \(f_1\)/\(f_2\), verifica viabilidade |
| `leitor_res.py` | Lê `.res` nos dois formatos (rotulado e sem rótulo) |
| `validar_fase1.py` | Testes de regressão contra `pr01.res` e `pr07.res` |

### Validação

- Distância reconstruída de `pr01`: **190,02** (bate com o publicado).
- Esperas e tempos a bordo conferidos nó a nó (tolerância pelo arredondamento de 2 casas dos `.res`).
- Conferir esperas equivale a testar a matriz de tempos trecho a trecho, porque o arquivo não grava distâncias.

### Descoberta de número no relatório

A linha “espera total = 211,15” do `.res` é a **espera do veículo**, não a parcela de espera de \(f_2\). Com a definição do modelo:

- desvio ≈ 943,49  
- espera do usuário ≈ 289,76  
- \(f_2\) total ≈ **1233** (valores refinados depois com agendamento ótimo: \(f_2 \approx 1183{,}64\) no extremo de emissão da `pr01` completa)

Tabelas do relatório acadêmico foram corrigidas.

### Política inicial de agendamento

A primeira versão do avaliador usava só **início mais cedo** (CEDO): cada nó no primeiro instante admissível. Isso bastou para validar fórmulas com agenda *externa* (`avaliar_com_B`), lendo os instantes do `.res`, mas falhou como política geral — o problema é o tema de abertura da Fase 2.

---

## Fase 2 — Gabarito (e o subproblema de agendamento)

### 2.1 Problema encontrado: início mais cedo vs. DARP

Antes de gerar extremos e fronteira exata, a política CEDO foi confrontada com a solução publicada de `pr01` **sobre a mesma sequência de nós** (só mudam os horários).

**Resultado:** a política de início mais cedo **declara inviável a solução ótima da literatura**.

**Motivo (específico do DARP):** metade das solicitações de `pr01` tem janela apertada na **entrega**, não na coleta. Se o veículo embarca a pessoa o mais cedo possível, chega adiantado no destino e **fica parado com o passageiro dentro do carro** até a janela abrir. Esse tempo conta como tempo a bordo (\(R_i\)) e estoura o limite de 90 minutos. A solução publicada **atrasa de propósito** alguns embarques justamente para evitar isso.

Comparação qualitativa na mesma rota publicada:

| | Agenda publicada | Início mais cedo (CEDO) |
|--|------------------|-------------------------|
| \(f_1\) (distância) | 190,02 | 190,02 (igual: ordem fixa) |
| \(f_2\) | ~1233 | bem pior (~1700) |
| Violações | 0 | várias (tempo a bordo e duração) |

### 2.2 Confirmação no extremo sem agrupamento

O construtor `solucao_individual` atende uma solicitação por vez, em blocos coleta–entrega. Pela proposição do relatório, o **desvio** (\(R_i - \bar{t}_i\)) deveria ser **zero**.

Com agendamento CEDO:

- desvio **309,31** com 3 veículos;
- piorava para **3067** com 24 veículos.

Quanto mais veículos, mais cedo cada um sai e mais tempo o passageiro espera **sentado no destino**. A proposição parecia falsa no código — mas o erro era do agendador, não da proposição.

**Consequência prática:** não existe extremo \(f_2 = 0\) sem **agendamento inteligente**, mesmo com a rota perfeita (sem desvio de caminho).

### 2.3 O subproblema: escolher os instantes de atendimento

A rota fixa a **ordem** das visitas; os **instantes** \(B_i\) (e a partida do depósito) ainda são livres dentro das janelas.

Atrasar um embarque:

- **encurta** o tempo a bordo de quem embarca naquele ponto (a entrega não precisa “esperar” tanto no destino);
- **prolonga** o tempo a bordo de quem já está no veículo (a entrega deles é empurrada).

Resolver esse compromisso é um **subproblema de otimização** acoplado ao DARP. Não é um ajuste de uma linha.

Duas respostas foram implementadas no avaliador:

1. **BORDO** — heurística dos oito passos de Cordeau & Laporte (2003): calcula a *folga de tempo para frente* (quanto se pode atrasar sem quebrar janelas, limites a bordo de quem já embarcou, nem \(T_{max}\)) e atrasa saída/embarques na medida em que a espera já existente adiante absorva o atraso. Critério de aceitação: não piorar o par (violação total, soma dos tempos a bordo).
2. **OTIMO** — programação linear que, para a sequência dada, escolhe os \(B_i\) minimizando a contribuição de \(f_2\) (respeitando restrições). Mais lento; usado como referência e no gabarito.

A política CEDO permanece no código (documentada e testável). O avaliador também aceita **agenda externa** (`avaliar_com_B`), o que permitiu validar distância, bordo e carga contra os `.res` **sem depender** de política alguma.

Com BORDO/OTIMO, o extremo sem agrupamento passa a ter desvio **nulo**, como a proposição prevê; com frota suficiente (\(m = n\)), \(f_2 = 0\).

### 2.4 O que a Fase 2 entregou depois do conserto

Arquivos novos / usados:

| Arquivo | Papel |
|---------|--------|
| `pareto.py` | Dominância, filtragem, hipervolume, cobertura, normalização |
| `exato.py` | Enumeração exata por subconjuntos (instâncias pequenas) |
| `mip.py` | Formulação do relatório no Gurobi + método ε-restrito |
| `fase2_fronteira.py` | Experimento: enumeração × heurística × solver; grava CSV/PNG |
| `resultados/fase2_*.csv`, `fase2_fronteira_pr01r5.png` | Artefatos |

**Instância reduzida** `pr01` → 5 solicitações (`pr01-r5`):

| Método | Pontos | Observação |
|--------|--------|------------|
| Enumeração + OTIMO | 4 | Gabarito “exato nos horários” |
| Enumeração + BORDO | 10 | Heurística: fronteira pior |
| Gurobi ε-restrito | 4 | Coincide com OTIMO (desvio ~\(10^{-14}\)) |

Efeito da heurística de horário (Fase 2):

- 100% da fronteira BORDO dominada pela exata (OTIMO);
- hipervolume normalizado ≈ **0,92** (exata) vs **0,57** (heurística);
- a BORDO **não** é dominada no sentido inverso (0%): ela não “inventa” pontos melhores que o ótimo.

**Extremos da `pr01` completa** (`fase2_extremos_pr01.csv`):

| Extremo | \(f_1\) | \(f_2\) | Veículos |
|---------|---------|---------|----------|
| Emissão mínima (rotas publicadas + OTIMO) | 190,02 | 1183,64 | 3 |
| Serviço perfeito (sem agrupamento, \(m = n\)) | 376,92 | 0,00 | 24 |

Serviço perfeito custa cerca de **+98%** de distância/emissão em relação ao extremo ambiental.

### 2.5 Decisão de engenharia para as fases seguintes

| Política | Uso previsto |
|----------|----------------|
| **OTIMO** | Gabarito, validação, instâncias pequenas |
| **BORDO** | Padrão nas metaheurísticas (avalia milhares de vizinhos) |
| **CEDO** | Apenas diagnóstico / comparação |

Ou seja: a heurística já em uso é de **agendamento** (horários), não de **roteamento** (quem atende quem). As Fases 3–5 atacam o segundo problema.

---

## Estrutura do repositório (ao fim da Fase 2)

```
Trabalho/
├── codigo/darp/           # biblioteca (avaliador, exato, mip, pareto, …)
├── codigo/experimentos/   # validar_fase1.py, fase2_fronteira.py
├── dados/bnc/, dados/tabu/
├── resultados/            # CSVs e gráfico da Fase 2
├── relatorio/             # main, resumo_professor
├── referencias/           # Assis et al. (2013)
└── pyproject.toml
```

---

## Próximos passos (Fases 3–6)

1. Representação cromossômica / vizinhanças que movem o **par** coleta–entrega.
2. NSGA-II (linha de base, p.ex. via `pymoo`).
3. MOILS com movimentos que atuem em \(f_1\) e em \(f_2\) (incl. “desagrupar” uma viagem).
4. ε-restrito + ILS mono-objetivo.
5. Comparar as três fronteiras ao gabarito `pr01-r5` e, nas instâncias maiores, entre si (HV, cobertura, cardinalidade; objetivos normalizados).

---

## Referências técnicas usadas no desenvolvimento

- Cordeau, J.-F.; Laporte, G. (2003). *A tabu search heuristic for the static multi-vehicle dial-a-ride problem*. (procedimento de redução do tempo a bordo / oito passos.)
- Assis et al. (2013). Capítulo sobre VRP multiobjetivo com coleta seletiva — protocolo experimental (NSGA-II, MOILS, ε-restrito; HV, cobertura).
- Instâncias DARP de Cordeau & Laporte (coleções branch-and-cut e tabu).
