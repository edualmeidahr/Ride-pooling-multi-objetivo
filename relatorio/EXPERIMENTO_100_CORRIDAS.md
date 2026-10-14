# Teste de escala com 100 corridas

## Protocolo

Demanda: [cenario_100_corridas.json](../dados/cenario_100_corridas.json).
Configuração: [comparacao_100_corridas.json](../experimentos/comparacao_100_corridas.json).

- 100 pedidos distintos, cada um com uma pessoa; índices internos 1–100 e entregas 101–200.
- 100 veículos disponíveis, fixos em todos os Q. Isso torna Q=1 viável na demanda concorrente.
- Q=1..10; phi por categoria e fatores de rua iguais aos do piloto ambiental.
- SA, GA e GRASP com semente 42; gulosa determinística com peso 0,5.
- Total realizado: 40 execuções, uma por método/Q. Não são 40 instâncias independentes.
- Método exato não executado: a enumeração continua limitada a seis pedidos.

Os pedidos têm IDs externos distintos, mas repetem o padrão de origens/destinos
e janelas do corredor anterior, como passageiros distintos indo aos mesmos
destinos. A rede continua com dez paradas e nove conexões. Esse teste amplia
demanda/ocupação, não diversidade urbana. Não é uma amostra de corridas reais.

## Construção para escala

O perfil grande usa limite_pedidos_candidatos=1: insere o próximo pedido por
horário desejado. Considera todos os veículos com capacidade disponível e até
oito pares de posições de inserção por rota, espalhados deterministicamente
entre as posições possíveis. A ordem coleta/entrega continua preservada.
Os 100 pedidos permanecem na entrada e precisam ser atendidos: esses limites
não recortam a demanda, apenas restringem candidatos na construção.

SA/GA/GRASP ainda executam suas buscas, cruzamentos ou melhorias locais. A
gulosa executa somente a construção. Os orçamentos são os exploratórios do
piloto anterior, não foram igualados. As construções limitadas diferem do
protocolo de 12 pedidos; não atribuir todas as mudanças apenas ao tamanho.
Sem o bloco construcao, a exploração original de pedidos/posições permanece.

Também foi retirada a cópia do conjunto inteiro de rotas para cada inserção
candidata na construção compartilhada. Agora avalia-se apenas a rota alterada
e aplica-se a inserção escolhida. Isso reduz cópias sem mudar as escolhas do
perfil original. Podas de capacidade e janela descartam inserções que não
podem ser viáveis. A poda de quantidade de passageiros só é usada quando a
entrada declara, e o leitor do menu verifica, coletas anteriores a toda entrega.

## Reprodução

No menu, escolha opção 5 e informe experimentos/comparacao_100_corridas.json.
Enter para Q executa todas as capacidades. Por argumentos:

```powershell
.\.venv\Scripts\python.exe codigo/menu.py --modo comparar_aproximados --config experimentos/comparacao_100_corridas.json --saida resultados/comparacao_100_corridas
.\.venv\Scripts\python.exe codigo/experimentos/conferir_menu.py resultados/comparacao_100_corridas
.\.venv\Scripts\python.exe codigo/experimentos/gerar_graficos_menu.py resultados/comparacao_100_corridas
```

Para regenerar deterministicamente a demanda e a configuração:
`codigo/experimentos/preparar_cenario_100.py`. O gerador sobrescreve apenas
os dois arquivos deste cenário.

## Saídas e conferência

Cada solução exportada deve cobrir exatamente os 200 eventos dos 100 pedidos,
sem duplicidade e com coleta antes da entrega no mesmo veículo. A conferência
independente recalcula distância física, custo ambiental, espera/desvio,
janelas, duração e cargas pelos registros. O CSV de resumo mantém os dois
objetivos da mesma solução e seu identificador.

O piloto Q=10 foi executado separadamente para verificar desempenho e depois
reaproveitado na consolidação, sem repetir suas quatro execuções. Os lotes
mantêm hashes dos respectivos fontes e opções no JSON consolidado. O piloto
de desempenho inicial foi interrompido antes de produzir resultados de método
e não compõe a campanha; motivou o limite de posições da construção.
O piloto e o início do lote Q=1..9 se sobrepuseram no tempo. Portanto, os tempos
registrados incluem condições de carga da máquina diferentes e não devem ser
usados como comparação de desempenho em isolamento.

Durante a campanha, as saídas são preservadas após cada método/Q. Somente um
JSON com concluida=true representa um lote finalizado. A consolidação exige
lotes completos, configurações/ruas iguais e ausência de método/Q duplicados.

Uma semente não mede variabilidade estatística. A referência empírica reúne
somente os pontos encontrados pelos quatro métodos neste teste. Mais corridas
não transforma essa referência em ótimo comprovado.

[Resumo de soluções](../resultados/comparacao_100_corridas/RESUMO.md) ·
[Guia dos gráficos](../resultados/comparacao_100_corridas/GUIA_RESULTADOS.md).

## Conclusão da campanha em 14/10/2026

As 40 execuções foram concluídas e consolidadas. Foram conferidas 247 soluções
completas por arcos, horários, cargas e objetivos; cada uma atende exatamente os
100 pedidos (200 eventos de coleta/entrega), sem duplicidades.
O lote Q=1..9 foi retomado a partir do checkpoint de 33 execuções, executando
somente GA, GRASP e gulosa em Q=9. Não foram repetidas as execuções salvas.
O registro inclui hashes e opções da retomada e dos dois lotes consolidados.
Foram gerados três gráficos PNG/SVG com um guia de leitura.
