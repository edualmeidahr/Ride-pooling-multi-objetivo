# Colônia de formigas multiobjetivo implementada à mão

## O que foi implementado

A ACO escolhe a alocação das solicitações aos veículos e a ordem das visitas.
É uma variante própria de Ant System com inserção de pares e arquivo de
Pareto, inspirada no mecanismo geral de colônia de formigas; não é apresentada
como reprodução de um algoritmo multiobjetivo publicado específico.

Referência conceitual: Marco Dorigo, *Ant colony optimization*, Scholarpedia,
2007, <https://www.scholarpedia.org/article/Ant_colony_optimization>.

Todo o núcleo é código próprio: construção, roleta, matriz de feromônios,
evaporação, reforço, normalização incremental e manutenção do arquivo. Não
foram usados `pymoo`, `DEAP`, pacotes de ACO ou rotinas prontas de metaheurística.
NSGA-II, MOILS e ε-restrito + ILS continuam pendentes.

| Configuração | Roteamento | Agendamento |
|---|---|---|
| ACO-BORDO | ACO própria | Heurística BORDO própria existente |
| ACO-OTIMO | A mesma ACO própria | PL via SciPy/HiGHS, sem fallback |
| Construtivo-BORDO | Mesmo construtor e roleta; feromônios fixos em 1 | BORDO |
| Construtivo-OTIMO | Mesmo construtor e roleta; feromônios fixos em 1 | PL estrito |

Gurobi só participa da conferência dos gabaritos. ACO-BORDO funciona sem importar
NumPy, SciPy ou Gurobi; um teste bloqueia explicitamente essas importações.
SciPy em ACO-OTIMO resolve somente horários de sequências já escolhidas pela ACO.

## Modelo mantido nesta etapa

São usadas as unidades e os parâmetros dos benchmarks: `phi=1`, limite de tempo
a bordo do cabeçalho, frota original nas instâncias completas e cinco veículos
nos recortes. Idas e voltas são incluídas. A primeira configuração não introduz
carros/vans, fatores físicos de CO₂, novas janelas ou frota ampliada.

Os objetivos são `f1 = phi * distância` e
`f2 = soma(q * (max(0, R-direto) + max(0, B-rho)))`. Para idas, `rho=e_coleta`;
para voltas sem janela de coleta, `rho=e_entrega-serviço_coleta-direto`.
A distância do benchmark é euclidiana e coincide numericamente com o tempo de
percurso. Não é uma medição de CO₂ em gramas sem conversão das unidades.

## Algoritmo

```text
inicializar feromônios em todos os arcos dirigidos
inicializar arquivo de Pareto vazio e gerador Random(seed)
para cada iteração:
    para cada formiga, com lambda igualmente espaçado de 0 a 1:
        embaralhar pedidos; começar com rotas vazias
        para cada pedido:
            enumerar inserções de coleta antes da entrega
            considerar rotas existentes e uma nova, se houver veículo
            eliminar sobrecarga e inviabilidades temporais necessárias
            agendar só a rota modificada, com cache por sequência
            calcular incrementos em f1 e f2 e probabilidades
            escolher por roleta uma inserção viável
            se não houver candidata: registrar fracasso da construção
        se a construção estiver completa:
            auditar de forma independente
            guardar a solução, mesmo se dominada
            atualizar o arquivo de Pareto com cópias independentes
    evaporar e reforçar feromônios com representantes do arquivo
    guardar histórico
parar por iterações, consultas ou tempo
```

Cada posição de coleta é combinada com todas as posições posteriores de entrega.
Mover apenas o pedido completo preserva pareamento e precedência. A frota nunca
é aumentada automaticamente. Falhar em construir uma solução não prova que a
instância seja inviável. Não há reparo, busca local ou injeção do gabarito nesta
versão: o objetivo é medir a própria ACO.

Para cada conjunto de candidatas, os incrementos de cada objetivo são escalados
por `(delta-min(delta))/(max(delta)-min(delta))`; amplitude zero contribui zero.
Isso também trata incrementos negativos que o agendamento heurístico possa causar.
Com `lambda=1`, a formiga prioriza emissão; com `lambda=0`, tempo perdido.

```text
custo = lambda * delta_f1_normalizado + (1-lambda) * delta_f2_normalizado
eta = 1/(1+custo)
probabilidade proporcional a tau^a * eta^b
```

`tau` é a média geométrica dos feromônios dos arcos acrescentados pela inserção,
incluindo depósito. As probabilidades são calculadas no domínio logarítmico para
evitar estouros. O arquivo usa dominância de Pareto estrita, não o custo ponderado.
Objetivos equivalentes a `1e-9` são deduplicados.

Até vinte representantes, espaçados pelo índice da frente ordenada em `f1`,
reforçam os seus arcos; os extremos são preservados. Cada representante deposita
`1/K`. A evaporação ocorre antes do depósito e os limites são aplicados depois.

### Parâmetros iniciais congelados

| Parâmetro | Valor |
|---|---:|
| Formigas por iteração | 20 |
| Iterações no experimento por avaliações | 100 |
| Consultas máximas de rota | 200.000 |
| Expoente do feromônio `a` | 1 |
| Expoente da atratividade `b` | 2 |
| Evaporação | 0,1 |
| Feromônio inicial | 1 |
| Limites do feromônio | 0,01 a 10 |
| Representantes no reforço | até 20 |

O parâmetro `alpha` do modelo continua sendo a tolerância proporcional a bordo;
não é o expoente do feromônio. Os parâmetros do algoritmo estão em `ConfigACO`.

As podas usam apenas condições necessárias: chegada mais cedo já após o fim da
janela, percurso mínimo a bordo excessivo, distância+serviços maior que a duração
permitida e retorno fisicamente tardio. Não usam o tempo a bordo de CEDO para
rejeitar rotas, porque atrasar o embarque pode corrigir esse tempo. Um teste
compara essas podas com rotas agendadas otimamente.

O cache de horários e de geometria é privado de cada execução. Consultas com
acerto de cache e rejeições por condições necessárias também contam no orçamento.
Chamadas efetivas ao PL são contadas separadamente. Isso impede que um método
ganhe avaliações gratuitas por cache; os tempos reais continuam sendo medidos.
Cada PL HiGHS usa uma thread, evitando multiplicação de threads em campanhas
com vários processos.

## Interface e execução

Na raiz do repositório, com Python 3.10 ou superior e as dependências do projeto:

```powershell
python -m unittest discover -s tests -v
python codigo/experimentos/validar_fase1.py
python codigo/experimentos/fase2_fronteira.py
```

O último comando sobrescreve os artefatos históricos da fase 2 em `resultados/`.

Uma execução pequena, comparando os quatro tratamentos:

```powershell
python codigo/experimentos/fase3_aco.py --pedidos 1 2 3 4 5 --veiculos 5 --sementes 0 1 2 --saida resultados/aco/exemplo
```

Piloto com cinco sementes nos três recortes e em a2-16, b2-16 e pr01:

```powershell
python codigo/experimentos/fase3_aco.py --suite piloto --jobs 4 --mip --saida resultados/aco/piloto
```

Campanha com trinta sementes, de 0 a 29:

```powershell
python codigo/experimentos/fase3_aco.py --suite campanha --jobs 4 --mip --saida resultados/aco/campanha
```

Comparação por tempo, com sessenta segundos por execução:

```powershell
python codigo/experimentos/fase3_aco.py --suite campanha --modalidade tempo --segundos 60 --jobs 4 --saida resultados/aco/campanha_tempo
```

O modo por tempo substitui os limites de consultas/iterações por limites muito
altos e verifica o prazo antes de cada consulta. É um prazo cooperativo: uma
consulta já iniciada pode terminar após o limite. Inicialização do processo,
exportação, métricas, gabaritos e reagendamento final não contam como busca.
Comparações de tempo devem usar a mesma quantidade de processos concorrentes;
a concorrência e o ambiente ficam no manifesto.

Há opções `--politica bordo|otimo|ambas`, `--metodo aco|construtivo|ambos`,
`--instancia`, `--pedidos`, `--veiculos`, `--seed`, `--sementes`, `--orcamento`,
`--formigas`, `--iteracoes`, `--modalidade avaliacoes|tempo|ambas` e `--saida`.
Use `--help` para a lista. `--sem-reavaliacao` apenas adia a auditoria cruzada;
não deve ser usado na entrega final dos resultados.

Uso como biblioteca, após instalar o pacote (`python -m pip install -e .`):

```python
from darp import ConfigACO, Parametros, ler_instancia, resolver_aco

inst = ler_instancia('dados/tabu/pr01')
resultado = resolver_aco(inst, Parametros(), ConfigACO(politica='bordo', seed=0))
for ponto in resultado.fronteira:
    print(ponto.f1, ponto.f2, ponto.solucao.rotas)
print(resultado.consultas, resultado.chamadas_pl, resultado.motivo_parada)
```

## Validação e correções de referência

O avaliador agora rejeita estruturas inválidas antes do agendamento e verifica
janelas inferiores/superiores, encadeamento, depósito, carga negativa/final,
duração e ambos os limites de tempo a bordo. Agendas internas usam `1e-6`; as
agendas publicadas arredondadas usam `0,02` na regressão. O auditor independente
recalcula distâncias e restrições sem usar os campos derivados do avaliador.

`Parametros.exigir_otimo=True` proíbe fallback. Dependência ausente ou falha
numérica gera `ErroAgendamento`; inviabilidade provada gera
`RotaTemporalmenteInviavel`. A ACO descarta somente a segunda. O modo legado
continua disponível por padrão e registra o motivo de eventual fallback.
Cada agenda registra política efetiva e status.

O PL possui variáveis explícitas de saída e retorno, permitindo esperar nos
depósitos e respeitando suas janelas sem omitir duração. Agendas diferentes
podem ter o mesmo f2 ótimo; a decomposição em desvio e espera não é única.

A conferência dos recortes revelou um erro no MIP antigo: ao atualizar a RHS de
`f2 <= epsilon`, a constante negativa de f2 havia sido transferida de lado por
Gurobi. Atualizar a RHS apenas com epsilon apertava indevidamente o limite e
pulava pontos. Agora a atualização subtrai `f2.getConstant()`. Também se usa
desempate lexicográfico, gaps zerados e status ótimo obrigatório. Atingir o
limite de pontos não é apresentado como uma frente completa. O passo numérico
de epsilon ainda exige confronto com enumeração antes de alegar completude.

| Recorte em pr01 | Pedidos originais | Pontos exatos com OTIMO |
|---|---|---:|
| Volta | 1, 2, 3, 4, 5 | 4 |
| Ida | 13, 14, 15, 16, 17 | 15 |
| Misto | 1, 2, 13, 14, 15 | 8 |

Nos três casos, a enumeração e o MIP corrigido coincidem com tolerância `1e-3`;
as agendas do solver também são verificadas pelo auditor independente.

## Artefatos e interpretação

Cada pasta de experimento contém:

- `manifesto.json`: argumentos, sementes, ambiente, versões, commit e hashes das
  fontes. Alterar as fontes durante uma campanha invalida sua consolidação.
- `fontes/`: cópia das fontes Python efetivamente usadas nas campanhas novas.
  A ordem das tarefas é embaralhada com semente 0, sem alterar o RNG de cada
  execução; a quantidade de processos também integra a assinatura de retomada.
- `execucoes/*.json`: configurações, parâmetros, todas as soluções completas,
  agendas, fronteira, histórico, matriz final e contadores. Soluções repetidas
  são armazenadas uma vez, com índice de ocorrências e peso de cada construção;
  soluções dominadas não são eliminadas desses dados brutos.
- `metricas.csv`, `resumo.csv`: medidas por execução, medianas e quartis.
- `cobertura.csv`: cobertura estrita nos dois sentidos, para a mesma semente.
- `normalizacao.json`: mínimos/máximos comuns e referência HV `(1.1,1.1)`.
- `referencias/*.json`: frentes por enumeração e, com `--mip`, confirmação MIP.
- `*_avaliacoes.png`, `*_tempo.png`, `*_convergencia.png`: frentes empíricas,
  distribuições do HV e evolução por consultas.
- `reavaliacao.csv`, `*_reavaliacao.json`: mesma união de soluções completas
  reagendada com BORDO e OTIMO; frentes refiltradas, custo e chamadas ao PL fora
  da busca registrados separadamente.

A normalização usa todas as soluções completas e referências de cada caso,
compartilhada entre políticas e métodos, não uma escala por execução. Nas pequenas,
HV relativo e recuperação são medidos contra o gabarito da política correspondente.
Nas grandes não há alegação de ótimo; as frentes de união são referências empíricas.
Uma frente vazia tem HV zero e taxa de viabilidade de saídas indefinida, não 100%.
Construções fracassadas/interrompidas são contadas separadamente.

Com referência `(1.1,1.1)`, o HV absoluto pode superar 1 (o quadrado completo
tem área 1,21). Isso não indica erro; HV relativo ao gabarito deve ser no máximo
1, salvo tolerância numérica. Não comparar valores absolutos entre pastas com
normalizações distintas, nem tempos obtidos com concorrências diferentes.

Maior cardinalidade não implica melhor qualidade. A comparação ACO x construtivo
isola o reforço por feromônios; BORDO x OTIMO também altera decisões e viabilidade
durante a busca. Para isolar horários, usar o reagendamento posterior do mesmo
conjunto bruto. Não concluir superioridade geral a partir de um recorte ou da
melhor semente. A presença de platôs e a recuperação incompleta do gabarito são
limitações esperadas de uma primeira metaheurística sem busca local.

Os resultados efetivamente executados e suas limitações estão registrados em
`RESULTADOS_ACO.md`, distinguindo o piloto da campanha.

Para repetir a auditoria dos artefatos reabertos e a consolidação conjunta dos
experimentos desta entrega (720 execuções por avaliações e 20 por tempo):

```powershell
python ferramentas/auditar_artefatos_aco.py resultados/aco/piloto resultados/aco/campanha resultados/aco/tempo_pr01
python ferramentas/consolidar_resultados_aco.py
```

Os JSONs brutos e as cópias de fontes são mantidos localmente e ignorados pelo
Git por padrão para não incluir centenas de megabytes numa alteração de código.
Os CSVs, manifestos, referências, auditorias e gráficos continuam versionáveis.
Para compartilhar o experimento completo, incluir também as pastas `execucoes/`
e `fontes/` em um arquivo de dados separado, ou adicioná-las explicitamente com
`git add -f` se esse for o fluxo escolhido pela equipe.
