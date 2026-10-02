# Campanha controlada de capacidade Q=1..10

## O que mudou na entrada

A entrada do experimento é [comparacao_q1_10.json](../experimentos/comparacao_q1_10.json).
Ela contém explicitamente `capacidades: [1,2,3,4,5,6,7,8,9,10]` e aponta para
[cenario_concorrente_q10.json](../dados/cenario_concorrente_q10.json), que descreve
a demanda e a rede. A capacidade não é uma constante dentro da demanda: o
executor lê a mesma entrada e fornece um Q diferente em cada cenário.

Esta campanha usa arquivos separados do exemplo anterior, que continua
disponível com resultados regenerados após a correção de unidade. Não
confundir o novo cenário de 12 pedidos com o recorte anterior de três pedidos.

Na revisão foi corrigido um erro de unidade no avaliador: a distância das
agendas somava `inst.tempo` em vez de `inst.dist`. A rede possui tempos em minutos
iguais ao dobro das distâncias em quilômetros; os antigos rótulos de distância
estavam incorretos. As duas campanhas são reproduzidas com o avaliador corrigido.
No pequeno gabarito, os mínimos corretos são 24/16/10 km para Q=1/2/3 ou mais.
O teste de regressão verifica separadamente 46 km e 92,4 minutos em uma rota
da nova entrada, nas três políticas de agendamento. As instâncias clássicas,
em que tempo e distância coincidem numericamente, não são afetadas.

## Por que a capacidade agora tem oportunidade de fazer diferença

Antes existiam apenas três passageiros no recorte. Depois de Q=3, não havia
mais ninguém para ocupar lugares adicionais. A nova demanda contém 12 pedidos
unitários, com quatro origens, quatro destinos e horários desejados entre 30 e
32 minutos. Todas as coletas terminam até o minuto 50. A primeira entrega
possível, mesmo em uma viagem direta, ocorre depois desse instante.

Assim, qualquer rota viável precisa coletar todos os seus passageiros antes de
entregar o primeiro. Ela não pode reutilizar um lugar durante a janela das
coletas. O executor verifica essa propriedade antes de executar a campanha.
Consequentemente, são necessários pelo menos `ceil(12/Q)` veículos:

| Q | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Limite inferior de veículos | 12 | 6 | 4 | 3 | 3 | 2 | 2 | 2 | 2 | 2 |

Há 12 veículos disponíveis em todos os cenários, para que Q=1 também seja
viável. A frota disponível é mantida fixa; o número de veículos usados é uma
decisão das rotas. Reduzir m juntamente com aumentar Q confundiria os efeitos.

O corredor principal tem 20 km e é compartilhado pelas viagens. Agrupar pode
evitar percorrê-lo com vários veículos, mas juntar origens/destinos exige
desvios e espera. Portanto, há oportunidade de compromissos distintos entre
distância e serviço. Tempos são duas vezes as distâncias, em minutos, e os
atendimentos duram 0,2 minuto. A tolerância a bordo permanece alpha=2 e o fator
phi=1 para comparar distância em quilômetros. Não são emissões calibradas.

Os testes também construíram exemplos viáveis para cada Q, ocupando Q lugares
e atingindo o limite de quantidade de veículos. Esses exemplos estão em
[diagnostico_entrada.json](../resultados/comparacao_q1_10/diagnostico_entrada.json).
Eles verificam a entrada; não são ótimos, não foram inseridos nos arquivos das
heurísticas e não compõem a referência empírica.

## O que se pode garantir

Podemos garantir que há demanda suficiente, concorrência real, viabilidade em
todos os Q e oportunidade de agrupamento até Q=10. Não podemos garantir uma
fronteira diferente em cada Q ou que uma heurística será pior em determinado Q.
Resultados coincidentes são admissíveis. A quantidade inteira de veículos,
as janelas e a geometria podem gerar patamares mesmo com muita demanda.

Aumentar Q expande o conjunto de soluções viáveis, mantendo todo o restante.
O ótimo não piora; uma busca limitada pode deixar de encontrar soluções já
encontradas em outro Q. Por isso, oscilações nos resultados heurísticos devem
ser investigadas e não interpretadas automaticamente como efeito físico de Q.

## Protocolo e reprodução

São 10 capacidades × SA/GA/GRASP × cinco sementes = 150 execuções. Sementes:
7, 42, 2026, 314 e 2718. Não são 150 instâncias independentes: todas usam a mesma
demanda sintética. A repetição mede variabilidade da busca nessa entrada.

Os parâmetros são fixos em todos os Q. SA usa três trajetórias e 120 movimentos
de resfriamento no total; GA usa população 6 e seis gerações; GRASP usa quatro
construções e até três passos de busca local por construção. São orçamentos
exploratórios distintos. Os contadores registram o trabalho observado, sem
impor igualdade de esforço. A campanha não é um ranking definitivo.

Cada execução mantém um cache próprio de agendas já calculadas para a mesma
sequência, partida e política. Instância e parâmetros ficam fixos durante essa
execução. O cache evita resolver novamente problemas idênticos; não compartilha
soluções entre métodos ou sementes e não muda as escolhas da busca. Foram
conferidos agendas, isolamento das cópias e equivalência de pontos/rotas no
piloto com e sem cache. Tempo com cache não deve ser comparado diretamente ao
tempo sem cache da campanha anterior.

O contador de chamadas inclui acertos no cache; o CSV também registra
`resolucoes_agendamento` e `cache_hits`. As resoluções de agendamento incluem
tentativas temporalmente inviáveis, não apenas PLs com solução ótima.

```powershell
.\.venv\Scripts\python.exe codigo/experimentos/validar_cenario_q10.py
.\.venv\Scripts\python.exe codigo/experimentos/executar_campanha.py --config experimentos/comparacao_q1_10.json
.\.venv\Scripts\python.exe codigo/experimentos/gerar_graficos_campanha.py --resultados resultados/comparacao_q1_10
.\.venv\Scripts\python.exe codigo/experimentos/conferir_registros_campanha.py resultados/comparacao_q1_10
```

O gerador `preparar_cenario_q10.py` reproduz deterministicamente os dois JSONs.
Ele sobrescreve esses arquivos; não é necessário executá-lo para rodar a campanha.

## Referência e métricas

Enumerar a fronteira exata de 12 pedidos não é uma extensão prática do pequeno
gabarito. Nesta campanha, a referência de cada Q é a união não dominada das
soluções encontradas pelos três métodos e pelas cinco sementes naquele Q.
Ela é empírica e depende da campanha; não comprova otimalidade. Um hipervolume
relativo de 100% significa alcançar essa referência observada.

A programação linear continua calculando o melhor horário para cada sequência
de rota avaliada. Isso não torna a escolha das sequências ou o agrupamento
global ótimos. Todos os pontos finais são reavaliados com um avaliador normal,
sem cache, e seus objetivos e sua viabilidade são conferidos.

Para comparar gráficos, o hipervolume usa uma única normalização global para
todos os Q, métodos e sementes e o mesmo canto de referência. O denominador
da razão é a referência de cada Q. As faixas mostram mínimo–máximo entre as
cinco sementes; não são intervalos de confiança.

O [guia da campanha](../resultados/comparacao_q1_10/GUIA_RESULTADOS.md) detalha
os eixos, cálculos, exemplos e limitações de cada gráfico. Os dois gráficos
adicionais mostram veículos/carga máxima e todas as fronteiras por capacidade.

## Resultados observados nesta execução

Foram concluídas as 150 execuções e conferidos independentemente 1.146 pontos
pelos arcos, horários, cargas e métricas salvos. As menores distâncias observadas
por Q foram:

| Q | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Menor distância encontrada (km) | 600 | 318 | 228 | 180 | 178 | 124 | 126 | 122 | 124 | 122 |

Há diferenças em todas as referências empíricas completas, embora alguns
extremos coincidam. A subida em Q=7 ou Q=9 é falha de recuperação pela busca,
não prova de piora do ótimo. A solução de 124 km em Q=6 continua viável em Q=7,
assim como a de 122 km em Q=8 continua viável em Q=9.

Na solução de menor distância de cada execução, a maior carga mediana do GA
fica em seis passageiros a partir de Q=6; ele utiliza mediana de três veículos,
enquanto SA/GRASP utilizam dois nessa faixa. Em Q=10, as cargas máximas medianas
são 10 para SA, 6 para GA e 9 para GRASP. Isso descreve uso da capacidade, não
ocupação média de toda a frota.

O hipervolume relativo mediano em Q=10 foi 88,4% para SA, 83,7% para GA e 90,8%
para GRASP. O GA executou menos chamadas de agendamento; diferenças de orçamento
e parâmetros impedem atribuir esses resultados exclusivamente ao algoritmo.

## Próxima etapa científica

Após este teste controlado, usar várias demandas e intensidades de concorrência,
ampliar os pedidos e comparar métodos com orçamento equivalente. Separar
instâncias para ajuste de parâmetros e avaliação, aumentar sementes e incluir
comparações de cobertura entre métodos. Quando viável, usar limites de solver
para medir distância ao ótimo em instâncias intermediárias. Uma única entrada
sintética com cinco sementes não suporta generalizações sobre cidades ou
superioridade dos algoritmos. Reaproveitar as soluções viáveis de Q menores
como pontos iniciais de Q maiores pode evitar perder alternativas conhecidas;
isso deve ser explicitado como um protocolo novo, aplicado a todos os métodos.
