# Resultados das implementações

Unidades: f1 = g_CO2; f2 = passageiro-minutos. Distância física é registrada separadamente em km.

Cada linha representa uma solução real. Para métodos com vários pontos, o resumo escolhe a menor distância euclidiana ao ideal dos objetivos normalizados, com pesos iguais e extremos da referência do mesmo Q. A referência é exata se a enumeração foi executada; caso contrário, é a união não dominada dos métodos selecionados. Esta escolha de apresentação não muda a busca e não garante um ótimo único. Não combinar mínimos de soluções diferentes.

| Q | Categoria | Método | Status | f1 | f2 | Veículos | Pontos |
|---|---|---|---|---:|---:|---:|---:|
| 1 | exato | exato | otimo | 17590.40 | 0.00 | 2 | 1 |
| 1 | metaheuristica | sa | concluida | 17590.40 | 0.00 | 2 | 1 |
| 1 | metaheuristica | ga | concluida | 17590.40 | 0.00 | 2 | 1 |
| 1 | metaheuristica | grasp | concluida | 17590.40 | 0.00 | 2 | 1 |
| 1 | heuristica | gulosa | concluida | 17590.40 | 0.00 | 2 | 1 |
| 2 | exato | exato | otimo | 8795.20 | 4.50 | 1 | 2 |
| 2 | metaheuristica | sa | concluida | 8795.20 | 4.50 | 1 | 2 |
| 2 | metaheuristica | ga | concluida | 8795.20 | 4.50 | 1 | 2 |
| 2 | metaheuristica | grasp | concluida | 8795.20 | 4.50 | 1 | 2 |
| 2 | heuristica | gulosa | concluida | 8795.20 | 4.50 | 1 | 1 |

[Resumo CSV](metricas.csv) · [Todas as soluções](solucoes.csv) · [Rotas, agendas e histórico](execucoes.json)

O tempo de busca inclui a execução do método, sem a reavaliação posterior para exportação. Bloqueio de construção ou ausência de soluções em uma metaheurística não comprovam inviabilidade. Enumeração concluída sem soluções informa inviabilidade do modelo. Comparações com uma semente e orçamentos diferentes não constituem ranking científico dos métodos.
