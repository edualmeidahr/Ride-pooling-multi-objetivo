# Registro de validação — 01/10/2026

## Atualização: unidades e cenário concorrente Q=1..10

O avaliador passou a acumular `inst.dist` nos campos de distância, mantendo
`inst.tempo` na propagação dos horários. Havia confusão de unidades em redes
com tempos diferentes das distâncias. O pequeno exemplo foi reproduzido com
mínimos de 24/16/10 km. Os valores 48/32/20 mencionados no retrato anterior
estavam rotulados incorretamente e ficam substituídos por essa atualização.

A nova entrada usa 12 pedidos concorrentes, quatro origens, quatro destinos,
m=12 e Q=1..10 definido na configuração experimental. Cinco testes verificam
concorrência, viabilidade individual, agrupamentos para todos os Q, cache
isolado e separação de distância/tempo. No último, uma rota tem 46 km e duração
92,4 minutos nas políticas CEDO, BORDO e OTIMO. Veja [CAMPANHA_Q1_10.md](CAMPANHA_Q1_10.md).

A referência da nova campanha é empírica, construída separadamente por Q,
usando todos os métodos e sementes. Não há enumeração exata dos 12 pedidos.
O agendamento de cada sequência continua usando PL e cada solução final é
reavaliada sem cache para conferir viabilidade e os dois objetivos.

Campanhas concluídas após a correção: 150 execuções/1.146 pontos no cenário
Q=1..10 e 180 execuções/538 pontos no exemplo pequeno Q=1..20. O conferidor
recalculou objetivos por arcos e horários e verificou cobertura, precedência,
carga, janelas, duração e hipervolume nos registros. Os cinco testes do novo
cenário, nove de entrada e oito de operadores passaram (22 testes).
Os dez novos gráficos e os oito anteriores foram gerados novamente em PNG/SVG.

## Atualização: Q externo e campanha de gráficos

O exemplo canônico deixou de definir Q. O leitor recebe Q do cenário e mantém
compatibilidade com arquivos antigos que o declaram. Nove testes de entrada
(incluindo capacidade externa, ausência de Q e substituição de Q legado) e os
oito testes de operadores passaram.

Foram executadas 180 buscas: Q=1..20 × SA/GA/GRASP × sementes 7/42/2026, com
os três primeiros pedidos do exemplo, m=3, alpha=2, phi=1 e OTIMO em todos os
métodos. Cada solução final foi reavaliada; hipervolume não ultrapassou o exato.
Configuração, versões, hashes de entrada/fontes, rotas, horários, checkpoints e
métricas são preservados em `resultados/comparacao_exemplo`.

O esforço registrado conta todos os agendamentos de rotas não vazias. Os
orçamentos dos métodos ainda são diferentes: os oito gráficos são exploratórios,
não uma prova de superioridade. As fronteiras exatas saturam em Q=3 porque esse
recorte só possui três passageiros.

## Atualização: entrada canônica e limpeza

Os onze imports sem uso foram retirados. A cópia do exemplo na raiz foi
removida; `dados/exemplo_instancia.json` agora tem unidades, pedidos concorrentes
e parâmetros lidos pelo comparador. O leitor valida demandas, IDs, janelas,
custos e caminhos da rede. Os oito testes novos de entrada e os oito testes de
operadores passaram; a regressão da rede/JSON também passou. A análise estática
dos imports locais não encontrou novos nomes sem uso.

O comparador também foi executado com GRASP sobre o arquivo canônico: carregou
OTIMO, alpha=2 e phi=180 do JSON e retornou três soluções viáveis. Isso é teste
de execução e integração, não uma comparação de qualidade entre métodos.

O recorte de três pedidos do novo exemplo produziu três pontos por capacidade,
com menores distâncias 48,32,20,20,20 para Q=1,2,4,8,20. Os resultados foram
guardados em `resultados/exemplo_q`, separados dos estudos anteriores.

O fluxograma interativo teve todas as 19 etapas clicadas em teste de navegador:
títulos e descrições acompanharam a seleção, sem erros JavaScript. O layout
também foi conferido com largura de 320 px, sem transbordamento horizontal.
Os fluxogramas Markdown permanecem como documentação estática detalhada.

## Correção da interpretação da execução anterior

A análise inicial usou o Python disponibilizado pelo aplicativo, sem SciPy.
O avaliador substituía OTIMO por BORDO silenciosamente quando a dependência
faltava. Assim, o f2=1225.55 observado naquela execução era heurístico; não
era divergência dos dados nem reprodução do agendamento ótimo. A dependência
foi instalada no ambiente local `.venv` e o fallback silencioso foi removido.

## Gabarito reproduzido com programação linear

pr01, pedidos originais [1,2,3,4,5], m=5, Q=6, limite a bordo do arquivo:

| Ponto | f1 | f2 |
|---|---:|---:|
| 1 | 47.0253 | 89.4142 |
| 2 | 47.6721 | 70.2116 |
| 3 | 49.1145 | 39.1136 |
| 4 | 49.9657 | 0.0000 |

Todos coincidem com o gabarito salvo (tolerância 0.001).
A fronteira com BORDO tem dez pontos; todos são dominados pela fronteira OTIMO.
Hipervolumes na referência comum do experimento: 0.9222 e 0.5738.
As rotas publicadas da pr01 completa, reagendadas, reproduzem f1=190.02 e
f2=1183.64. Esses valores não certificam extremos globais para todos os cenários.

Gurobi indisponível nesta execução. O CSV e o gráfico regenerados contêm apenas
enumeração OTIMO e BORDO; os pontos históricos do solver não foram apresentados
como se tivessem sido reexecutados. Os quatro pontos históricos agora são
conferidos explicitamente pelo script da Fase 2.

## Capacidade e saturação

pr01, pedidos de ida [13,14,15,16,17], m=5, alpha=2, phi=1, OTIMO:
Q=1..20 produz a mesma fronteira de quatro pontos:

| Ponto | f1 | f2 |
|---|---:|---:|
| 1 | 75.483080 | 28.015776 |
| 2 | 76.110035 | 21.712101 |
| 3 | 80.303380 | 6.303676 |
| 4 | 80.633929 | 0.000000 |

Isso é evidência de saturação nessa amostra; não demonstra que Q seja irrelevante
nas instâncias maiores. Há múltiplos pedidos atendidos sequencialmente pelo
mesmo veículo sem compartilhar simultaneamente. O ponto com menor f1 ainda
tem espera de embarque mesmo com Q=1.

A repetição com m=3 também encontrou uma única fronteira distinta entre Q=1 e
Q=20. Os dois cenários têm resumos em CSV e figura conjunta em
`resultados/capacidade_q_comparativo.png`. Nesse recorte, ampliar capacidade não
gera diversidade adicional; incluir mais pedidos concorrentes é necessário
para investigar benefícios de compartilhamento em instâncias maiores.

O experimento guarda rotas, partidas, horários e carga máxima em JSON e objetivos
sem arredondamento em CSV. Confere viabilidade de cada ponto e inclusão das
alternativas entre capacidades sucessivas. Para Q >= demanda total, reaproveita
a fronteira, pois a restrição de capacidade é comprovadamente redundante.

## Verificações executadas

As oito provas da bateria de operadores e integração passaram na execução final.

- `validar_fase1.py`: leitura das onze instâncias locais, reprodução de pr01/pr07,
  agendas e extremo sem agrupamento — todas as conferências passaram com SciPy.
- `validar_novo_modelo.py`: grafo, paradas coincidentes, JSON e enumeração — todas
  as conferências passaram. O primeiro ponto exato é (67,92); (67,101) era o
  resultado do antigo fallback BORDO.
- `validar_operadores.py`: inserção real, posições inválidas, construção que
  melhora distância, 1000 perturbações preservando estrutura e original,
  cruzamentos com ambos os pais e independência dos cenários.
  A bateria ampliada inclui rotas compactas, integração curta de SA/GA/GRASP e
  um caso controlado com quatro pedidos coincidentes: a menor distância é
  10, 6, 4 e 4 para Q=1,2,4,20. Isso verifica efeito real e saturação da capacidade.

Os testes estruturais não afirmam que todo vizinho seja temporalmente viável:
a avaliação continua responsável por capacidade, janelas e limites a bordo.
As metaheurísticas de grande escala continuam exploratórias; seus orçamentos
de avaliação e buscas ponderadas ainda exigem padronização antes da comparação.
