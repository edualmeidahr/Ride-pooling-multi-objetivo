# Emissão por categoria de veículo e por rua

## O que as referências sustentam

Consulta em 04/10/2026. A capacidade pode servir como aproximação do porte,
mas não determina sozinha a emissão por km. Combustível, tecnologia, massa e
condições de uso também importam. Não há nas referências consultadas uma tabela
universal de phi para cada Q de 1 a 20.

- [INMETRO — PBE Veicular](https://www.gov.br/inmetro/pt-br/assuntos/avaliacao-da-conformidade/programa-brasileiro-de-etiquetagem/tabelas-de-eficiencia-energetica/veiculos-automotivos-pbe-veicular): informações de consumo e emissão por modelo/versão. É a referência brasileira para uma futura calibração de veículos leves.
- [DESNZ — fatores de conversão 2026](https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2026): metodologia e fatores por categorias/combustíveis, com unidades que precisam ser distinguidas entre veículo-km e passageiro-km e entre CO2 e CO2 equivalente.
- [DESNZ — metodologia 2025, tabela 15](https://assets.publishing.service.gov.uk/media/6846b0870392ed9b784c0187/2025-GHG-CF-methodology-paper.pdf): médias de homologação WLTP de carros a gasolina por tamanho do motor: 129,3, 153,9 e 246,4 g CO2/km nas classes pequena, média e grande. São classes de motor, não de assentos; não são valores diretamente atribuíveis a vans nem fatores brasileiros. Usadas como evidência da tendência por categoria, não como calibração do projeto.
- [HBEFA — metodologia](https://www.hbefa.net/en/methodology): fatores diferenciados por categoria de veículo, situações de tráfego e classes de inclinação. Sustenta considerar condições viárias; não fundamenta nossa distribuição aleatória ou faixa de 15%.

Conclusão: implementar phi por tipos de veículos é defensável. Fazer phi
crescer obrigatoriamente a cada assento, ou tratar todo veículo maior como
mais emissor independentemente da propulsão, não é uma lei física. Um carro
utilizado com limite Q=1 e o mesmo carro com Q=4 pode ter o mesmo phi.

## Hipótese sintética implementada

O [perfil ambiental](../experimentos/modelo_emissoes.json) adota:

| Capacidade permitida Q, excluindo motorista | Categoria ilustrativa | phi (g CO2/km) |
|---|---|---:|
| 1–4 | Automóvel | 180 |
| 5–6 | Veículo familiar | 250 |
| 7–10 | Van | 350 |
| 11–20 | Micro-ônibus | 500 |

**Esses quatro números e as faixas são hipóteses de simulação, não dados
retirados das tabelas citadas.** Representam uma frota convencional hipotética.
Podem ser substituídos por fatores medidos. Todos os veículos disponíveis de
uma execução têm o mesmo tipo/capacidade; ainda não há frota heterogênea.

Para cada aresta, sorteia-se uniformemente um multiplicador entre 1,00 e 1,15,
com semente 20261004, independente da semente das buscas. Os limites são uma
escolha controlada do experimento, sem pretensão de reproduzir a variabilidade
real. O fator é sorteado uma vez, em ordem determinística de arestas. Em rede
não dirigida, vale nos dois sentidos (simplificação que não descreve subida e
descida reais); redes dirigidas permitem fatores por sentido.

Para um percurso: CO2 = phi(Q) × soma(d_rua × fator_rua). Ida à primeira coleta
e retorno à garagem entram no cálculo; veículos vazios não emitem no modelo.
Tempos de serviço e espera afetam o segundo objetivo, mas marcha lenta e partida
a frio não possuem parcelas ambientais próprias nesta versão. Não inclui
fabricação, combustível a montante, eletricidade ou outros gases.

## Caminhos e matrizes

A matriz ambiental soma os custos das arestas do **mesmo caminho mínimo de
distância** da rede física; não calcula um caminho ambiental mais curto e
incompatível com o caminho percorrido. Em empates, a escolha é determinística.
O modo ambiental exige arestas explícitas e verifica que o tempo desse caminho
coincide com a matriz temporal. Caso contrário, rejeita a rede, pois distância
e tempo independentes poderiam descrever caminhos diferentes. Não altera os
quilômetros físicos nem os tempos para ajustar a emissão.

O arquivo ambiente_emissoes.json guarda configurações, fatores sorteados,
caminhos, matriz ambiental e phi por Q. execucoes.json guarda tudo isso também,
além da distância física de cada solução, phi da execução e objetivos f1/f2.
O modo é ativado pelo bloco modelo_emissoes do JSON experimental. O gerador
copia o perfil para a configuração; editar o perfil exige gerar de novo as
configurações antes de executar. Entradas de demanda continuam sem Q.

## Adaptação das buscas e interpretação

O avaliador, a construção gulosa, o cruzamento GA, a enumeração exata e a
expressão do MIP usam o custo ambiental. No modo ambiental, SA e GRASP usam
escalas fixas por execução: f1 da solução individual e um limite de f2 calculado
pelas janelas/limites a bordo. Isso evita que trocar gramas por kg mude a
prioridade ponderada. A inserção do cruzamento GA prioriza menos violações antes
de comparar emissão. O modo antigo mantém suas ponderações para preservar o
protocolo histórico. A programação linear continua otimizando horários para
cada sequência; o CO2 deste modelo não depende do horário.

Com phi diferente entre categorias, aumentar Q **não garante reduzir o ótimo
ambiental**. Capacidade e tipo de veículo mudam juntos; não é um experimento
que isola apenas Q. Dentro da mesma categoria, aumentar Q mantém phi e amplia
as rotas permitidas. Fatores viários continuam idênticos entre algoritmos e Q.
O hipervolume tem normalização global comum na campanha ambiental, e sua
referência empírica é a união não dominada dos métodos. Não comparar seu valor
diretamente com hipervolumes de campanhas históricas com outra escala.

## Reprodução e validação

As campanhas anteriores de distância não são sobrescritas.

```powershell
.\.venv\Scripts\python.exe codigo/experimentos/preparar_experimentos_emissoes.py
.\.venv\Scripts\python.exe codigo/experimentos/validar_emissoes.py
.\.venv\Scripts\python.exe codigo/experimentos/executar_campanha.py --config experimentos/validacao_emissoes.json
.\.venv\Scripts\python.exe codigo/experimentos/conferir_registros_campanha.py resultados/validacao_emissoes
.\.venv\Scripts\python.exe codigo/experimentos/executar_campanha.py --config experimentos/comparacao_emissoes_q1_10.json
.\.venv\Scripts\python.exe codigo/experimentos/conferir_registros_campanha.py resultados/comparacao_emissoes_q1_10
.\.venv\Scripts\python.exe codigo/experimentos/gerar_graficos_campanha.py --resultados resultados/comparacao_emissoes_q1_10
```

A validação pequena usa dois pedidos, três métodos, uma semente e Q=1/2/5/7/10,
com referência exata. Q acima da demanda é redundante em capacidade, mas permite
conferir mudanças de phi. A campanha piloto ambiental usa os 12 pedidos anteriores,
Q=1..10, três métodos e semente 42. Uma semente não estima variabilidade.
O experimento de 100 pedidos permanece para a próxima etapa, após esta alteração.

O MIP teve sua expressão ambiental atualizada, mas não foi executado nesta
validação (Gurobi opcional). Os modos do leitor/serializador de instância
representam demanda/rede; a reprodução ambiental deve usar a configuração
experimental e o registro de ambiente, não apenas exportar a instância em memória.

## Resultado da validação em 04/10/2026

Passaram cinco testes ambientais (incluindo troca de g por kg sem alterar
rotas dos três métodos), oito de operadores, nove de entrada, cinco do cenário
concorrente e cinco de exportação/pareamento. As conferências do modelo de rede
e do gabarito clássico também passaram; os 1.146 pontos da campanha histórica
continuam consistentes com sua própria configuração.

A campanha ambiental pequena concluiu 15 execuções e 27 pontos, com referência
exata. O piloto de 12 pedidos concluiu 30 execuções e 219 pontos; a soma dos
tempos de busca foi aproximadamente 332 segundos nesta máquina. Todos os
pontos foram conferidos por arcos, horários, capacidade e métricas.
Foram produzidos dez gráficos PNG/SVG e os CSVs de soluções reais.

Exemplo observado: menor emissão empírica de aproximadamente 34.971 g em Q=4
e 49.051 g em Q=5, onde phi muda de 180 para 250. Essa comparação não isola
capacidade, nem prova que esses são ótimos globais. O novo piloto possui buscas
ponderadas ajustadas no modo ambiental; diferenças em relação à campanha antiga
não devem ser atribuídas exclusivamente ao objetivo de emissão.

[Guia do piloto](../resultados/comparacao_emissoes_q1_10/GUIA_RESULTADOS.md) ·
[Soluções reais](../resultados/comparacao_emissoes_q1_10/RESUMO_SOLUCOES.md).
