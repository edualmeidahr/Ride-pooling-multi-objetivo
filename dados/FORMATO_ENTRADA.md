# Entrada urbana de passageiros

O exemplo canônico é [exemplo_instancia.json](exemplo_instancia.json). A cópia
da raiz foi removida. O formato descreve um DARP estático: os pedidos são
conhecidos antes da execução. Não define uma agenda de atendimento nem rotas
prontas; isso é produzido pela otimização.

## Organização do arquivo

| Bloco | Campos | Significado |
|---|---|---|
| Identificação | `versao_formato`, `nome`, `descricao` | Versão 1, nome do cenário e origem dos dados |
| Unidades | `unidades` | No contrato urbano: distância em km, tempo em minutos, demanda em passageiros |
| Frota | `m` | Veículos disponíveis; Q é definido no experimento |
| Limites | `T_max`, `L_arquivo` | Duração máxima da rota e limite global de tempo a bordo, em minutos |
| Depósitos | `deposito_origem_id`, `deposito_destino_id`, `janela_deposito_ini`, `janela_deposito_fim` | Paradas de saída/retorno e disponibilidade dos depósitos |
| Avaliação | `parametros_avaliacao` | Emissão, limite proporcional a bordo, política de horário, custos auxiliares e tolerância |
| Rede | `rede.nos_fixos`, `rede.arestas` | Paradas físicas e conexões viárias |
| Pedidos | `requisicoes` | Origem, destino, passageiros e janelas de cada solicitação |

Não é necessário fornecer `n`: ele é calculado pela quantidade de pedidos.
O JSON canônico não define Q: a mesma demanda serve para capacidades diferentes.
`experimentos/comparacao_exemplo.json` define Q=1..20 para a campanha;
`--q 4` seleciona Q=4 numa execução isolada. A instância em memória sempre tem
um Q concreto, pois precisa dele para verificar capacidade. O leitor aceita
`ler_instancia_json(caminho, Q=valor)`; se não houver Q no arquivo nem argumento,
informa erro explícito. Arquivos antigos com Q continuam aceitos e o argumento
externo tem prioridade.

`m` e o Q de cada execução devem ser inteiros positivos. Um pedido pode ter `q>1`, mas seu grupo
é indivisível; com `Q<q` o cenário é inviável. O exemplo usa q=1 para permitir
estudar Q=1 sem essa inviabilidade trivial.

## Rede física

Cada parada contém `id`, `x`, `y`, `nome`, `s_embarque` e `s_desembarque`.
As coordenadas servem à identificação geométrica; com arestas explícitas,
os custos usados são os caminhos mínimos na rede, não a distância entre x/y.
Os serviços são tempos por evento de pedido, não por passagem física unificada
de todos os passageiros. Pedidos compartilhando uma parada continuam tendo
eventos distintos; o serviço de cada um é contado.

Cada aresta contém `origem`, `destino`, `distancia` e `tempo`. No exemplo,
`direcionado=false` faz cada conexão valer nos dois sentidos. Em rede dirigida,
é necessário fornecer ambos os sentidos se ambos existirem. A leitura exige
caminhos entre todas as paradas em ambas as direções; não completa uma rede
viária desconectada com atalhos euclidianos.

O exemplo tem seis paradas, cinco conexões e custo de tempo igual a duas vezes
a distância em cada conexão (30 km/h constantes). Assim, o menor caminho em
tempo é consistente com o menor caminho em distância. São dados sintéticos,
não uma rede urbana real. No modelo geral, as duas matrizes são calculadas
independentemente; calibrar custos para dados reais requer atenção a isso.

Alternativa suportada: fornecer `matriz_dist` e `matriz_tempo`, listas de objetos
`{"origem": 1, "destino": 2, "valor": 4.0}`. Todos os pares ordenados distintos
precisam de distância e tempo; fornecer ambas as matrizes e não misturar
matrizes e arestas. Nas arestas, se `tempo` for omitido, ele é derivado da
distância e de `velocidade` (km/min). Se nenhuma
rede de custos for fornecida, o leitor mantém a alternativa euclidiana legada.
Para um experimento viário, preferir custos explícitos e unidades consistentes.

## Pedidos

Cada pedido contém:

| Campo | Regra |
|---|---|
| `id` | Inteiro positivo e único; identifica o pedido externo |
| `origem_id`, `destino_id` | Referências a paradas existentes, distintas |
| `q` | Inteiro positivo: passageiros que viajam juntos |
| `e_coleta`, `l_coleta` | Início/fim da janela de embarque, em minutos |
| `e_entrega`, `l_entrega` | Início/fim da janela de desembarque |
| `s_coleta`, `s_entrega` | Opcionais: substituem o serviço definido na parada |

IDs externos 101–105 são mantidos em `inst.requisicoes`; os algoritmos usam
posições internas 1–5 e entregas 6–10. Portanto, `--pedidos` do estudo Q recebe
os índices internos, não os IDs externos.

O exemplo concentra quatro pedidos entre minutos 30 e 32, com destinos próximos,
e inclui um pedido posterior no minuto 90. Isso oferece oportunidades de
agrupamento. Uma janela de entrega `[0,1440]` é a convenção atual para entrega
livre; ela não amplia a janela do depósito, que termina em 240.

O horário desejado `rho` não é um campo independente no modelo atual. Quando
a coleta tem janela apertada, `rho=e_coleta`. Se somente a entrega é apertada,
ele é inferido da chegada desejada e do percurso direto. Para passageiros de
aplicativo, preferir pedidos com janela na coleta, como neste exemplo.

## Parâmetros efetivamente utilizados

| Campo | Exemplo | Efeito |
|---|---:|---|
| `phi` | 180 | Gramas de CO2 por km; valor ilustrativo, sem calibração |
| `alpha` | 2 | Limite a bordo = 2 × tempo direto; substitui `L_arquivo` |
| `politica` | `otimo` | Programação linear dos horários; exige SciPy |
| `custo_fixo` | 0 | Custo auxiliar por veículo usado |
| `custo_distancia` | 0 | Custo auxiliar por km |
| `custo_hora` | 0 | Nome histórico: o código multiplica pela duração em **minutos**; fornecer custo por minuto |
| `tolerancia` | 0.000001 | Tolerância numérica nas restrições |

Com `alpha=null`, vale o limite global `L_arquivo`. Os custos não são objetivos:
são indicadores auxiliares. Com phi=180, f1 é medido em gramas ilustrativas;
com phi=1, é numericamente distância. f2 fica em passageiro-minutos.

O comparador carrega esses parâmetros automaticamente. `--politica` tem
prioridade sobre a política do JSON. JSONs antigos sem esse bloco usam os
padrões de `Parametros` (OTIMO, phi=1, alpha=null). Texto clássico mantém BORDO
como padrão do comparador.

`capacidade_q.py` tem um protocolo separado: define phi=1 e OTIMO e usa seus
argumentos m/alpha/Q. Ele não herda os parâmetros de avaliação do JSON. Isso
mantém distância como referência comum na análise de capacidade.

## Validação da entrada

O leitor rejeita demandas fracionárias, IDs duplicados/inexistentes, janelas
invertidas, custos negativos/não finitos, capacidades inválidas e redes explícitas
sem caminhos completos. O bloco de avaliação rejeita campos desconhecidos,
políticas inválidas e alpha<1. Metadados não executam código.

Uma entrada estruturalmente válida ainda pode ter nenhuma solução viável, por
falta de veículos, capacidade ou tempo; essa decisão pertence à avaliação e
otimização. Não converter essa situação em dados corrigidos silenciosamente.

`salvar_instancia_json` exporta a estrutura da instância, mas não é um editor do
arquivo de configuração: não preserva descrição, unidades nem o bloco externo
de avaliação. Guardar o JSON de entrada original para reproduzir o experimento.

## Execução

```powershell
.\.venv\Scripts\python.exe codigo/experimentos/validar_entrada_json.py
.\.venv\Scripts\python.exe codigo/experimentos/comparar_metaheuristicas.py --instancia dados/exemplo_instancia.json --q 4 --algoritmos grasp
.\.venv\Scripts\python.exe codigo/experimentos/capacidade_q.py --instancia dados/exemplo_instancia.json --pedidos 1 2 3 --m 3 --alpha 2 --q 1 2 4 8 20 --saida resultados/exemplo_q
.\.venv\Scripts\python.exe codigo/experimentos/executar_campanha.py
.\.venv\Scripts\python.exe codigo/experimentos/gerar_graficos_campanha.py
```

A enumeração cresce rapidamente; começar com três pedidos e ampliar depois.
As versões das dependências estão em `requirements-validacao.txt`.

Os comandos de campanha sem argumentos agora selecionam o cenário concorrente
Q=1..10 e seus gráficos. Para a campanha pequena anterior, indicar
`--config experimentos/comparacao_exemplo.json` e, na geração das figuras,
`--resultados resultados/comparacao_exemplo`.

A entrada experimental `experimentos/comparacao_q1_10.json` contém explicitamente
as capacidades de 1 a 10. Ela referencia `dados/cenario_concorrente_q10.json`,
com 12 pedidos concorrentes. A frota permanece m=12 e a demanda permanece
igual em todos os Q. Veja o [protocolo](../relatorio/CAMPANHA_Q1_10.md) para
entender viabilidade, concorrência e referência empírica.

O recorte dos três primeiros pedidos foi executado com OTIMO: a menor distância
foi 24 km para Q=1, 16 km para Q=2 e 10 km para Q=4,8,20 após a correção que separa
distância e tempo no avaliador. Os antigos 48/32/20 estavam em minutos, embora
rotulados como quilômetros. Os objetivos completos,
rotas e horários estão em `resultados/exemplo_q`. Esse é um exemplo sintético
de benefício e saturação; não uma estimativa de ganho para uma cidade real.
