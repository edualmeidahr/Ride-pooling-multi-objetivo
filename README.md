# Ride-pooling multiobjetivo

Projeto de DARP estático: distância/emissão versus tempo perdido pelos passageiros.

O [menu das três implementações](relatorio/MENU_IMPLEMENTACOES.md) permite
selecionar método exato, metaheurísticas ou heurística gulosa e comparar métodos.

O [experimento de 100 corridas](relatorio/EXPERIMENTO_100_CORRIDAS.md) amplia o
teste de escala, com Q=1..10 e uma execução por SA/GA/GRASP/gulosa. A configuração
é `experimentos/comparacao_100_corridas.json`.

```powershell
.\.venv\Scripts\python.exe codigo/menu.py
```

A [heurística gulosa independente](relatorio/HEURISTICA_GULOSA.md) constrói uma
solução determinística com pesos configuráveis, sem executar as metaheurísticas.
Para o exemplo pequeno: `.\.venv\Scripts\python.exe codigo/experimentos/executar_heuristica.py`.

O [modelo ambiental por veículo e rua](relatorio/MODELO_EMISSOES.md) apresenta
as referências, hipóteses sintéticas, configuração e validação de CO2 estimado.
As campanhas ambientais são separadas das campanhas históricas de distância.

O [modelo experimental consolidado](relatorio/MODELO_EXPERIMENTAL.md) define a
análise de capacidade Q=1..20, os cenários, hipóteses e comandos de reprodução.
O [diário de desenvolvimento](relatorio/RELATORIO_DESENVOLVIMENTO.md) contém o
histórico. O relatório acadêmico em LaTeX/PDF registra uma proposta anterior.

A [auditoria de alterações e limpeza](relatorio/AUDITORIA_ALTERACOES_E_LIMPEZA.md)
explica cada mudança e os candidatos à remoção. Os
[fluxogramas atuais](relatorio/FLUXOGRAMA_ATUAL.md) mostram entradas, avaliação,
estudo de capacidade e metaheurísticas.

O [exemplo de entrada](dados/exemplo_instancia.json) fica apenas em `dados`.
O [guia do formato JSON](dados/FORMATO_ENTRADA.md) explica unidades, rede,
pedidos, parâmetros utilizados e validações.
O [exemplo didático de dois pedidos](dados/EXEMPLO_PEQUENO.md) apresenta uma
entrada menor e uma campanha com Q=1 e Q=2.

A **campanha principal atual** é a [comparação Q=1..10](relatorio/CAMPANHA_Q1_10.md), com 12 pedidos concorrentes,
cinco sementes e referência empírica. A [entrada experimental](experimentos/comparacao_q1_10.json)
define todas as capacidades e aponta para a demanda. O
[guia detalhado dos novos gráficos](resultados/comparacao_q1_10/GUIA_RESULTADOS.md)
explica os resultados e seus limites.

O [resumo de soluções reais](resultados/comparacao_q1_10/RESUMO_SOLUCOES.md)
mantém distância e tempo perdido da mesma solução em cada linha. Destaca um
compromisso por Q com pesos iguais e normalização explícita, sem afirmar ótimo
global. Os CSVs exportam todas as soluções e os três perfis por execução.
`metricas.csv` contém apenas o resumo da solução equilibrada de cada execução;
`metricas_tecnicas.csv` preserva os extremos pareados e contadores detalhados.
Para atualizar esses resumos sem repetir a busca:

```powershell
.\.venv\Scripts\python.exe codigo/experimentos/resumir_campanha.py --resultados resultados/comparacao_q1_10
```

O [caso reduzido de três pedidos](experimentos/comparacao_exemplo.json) permanece
como referência de validação com fronteira exata, não como base das conclusões
sobre capacidade ou superioridade das heurísticas. Seu
[guia de gráficos](resultados/comparacao_exemplo/GUIA_RESULTADOS.md) preserva a
campanha anterior. Resultados iguais após Q=3 são a saturação esperada desse
recorte, uma propriedade útil para detectar regressões.

A [fonte do fluxograma interativo](relatorio/fluxograma_interativo.html) preserva
a visualização da auditoria inicial. É um fragmento para o visualizador da
conversa; a campanha atual e seus parâmetros são descritos no protocolo acima.

Ambientes, caches e auxiliares de compilação são ignorados. Entradas,
configurações, registros de execução, tabelas, figuras PNG/SVG e relatórios
finais são versionados como evidências das campanhas.

```powershell
.\.venv\Scripts\python.exe codigo/experimentos/executar_campanha.py --config experimentos/comparacao_q1_10.json
.\.venv\Scripts\python.exe codigo/experimentos/gerar_graficos_campanha.py --resultados resultados/comparacao_q1_10
```

Sem argumentos, os dois comandos também selecionam a campanha atual Q=1..10.
Para reproduzir o gabarito anterior, usar `--config experimentos/comparacao_exemplo.json`
e `--resultados resultados/comparacao_exemplo`.

- `codigo/darp`: dados, rede, soluções, agendamento, métodos exatos e metaheurísticas.
- `codigo/experimentos`: validação, reprodução do gabarito e estudo de capacidade.
- `dados`: instâncias clássicas e exemplo de rede fixa.
- `resultados`: fronteiras e registros experimentais.

Requer Python >=3.10, NumPy, SciPy e Matplotlib. O ambiente `.venv` é local e não
deve ser versionado. O Gurobi é opcional. SA, GA e GRASP são implementações
exploratórias; a campanha comparativa de grande escala ainda está pendente.
