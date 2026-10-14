# Resultados das implementações

Entrada: 100 pedidos completos; 100 veículos disponíveis; capacidades [1, 2, 3, 4, 5, 6, 7, 8, 9, 10].

Unidades: f1 = g_CO2; f2 = passageiro-minutos. Distância física é registrada separadamente em km.

Cada linha representa uma solução real. Para métodos com vários pontos, o resumo escolhe a menor distância euclidiana ao ideal dos objetivos normalizados, com pesos iguais e extremos da referência do mesmo Q. A referência é exata se a enumeração foi executada; caso contrário, é a união não dominada dos métodos selecionados. Esta escolha de apresentação não muda a busca e não garante um ótimo único. Não combinar mínimos de soluções diferentes.

| Q | Categoria | Método | Status | f1 | f2 | Veículos | Pontos |
|---|---|---|---|---:|---:|---:|---:|
| 1 | metaheuristica | sa | concluida | 999639.82 | 0.00 | 100 | 1 |
| 1 | metaheuristica | ga | concluida | 999639.82 | 0.00 | 100 | 1 |
| 1 | metaheuristica | grasp | concluida | 999639.82 | 0.00 | 100 | 1 |
| 1 | heuristica | gulosa | concluida | 999639.82 | 0.00 | 100 | 1 |
| 2 | metaheuristica | sa | concluida | 999639.82 | 0.00 | 100 | 7 |
| 2 | metaheuristica | ga | concluida | 977389.76 | 1.20 | 98 | 12 |
| 2 | metaheuristica | grasp | concluida | 514390.44 | 86.40 | 51 | 2 |
| 2 | heuristica | gulosa | concluida | 546378.27 | 573.00 | 50 | 1 |
| 3 | metaheuristica | sa | concluida | 999639.82 | 0.00 | 100 | 17 |
| 3 | metaheuristica | ga | concluida | 962304.55 | 43.00 | 96 | 10 |
| 3 | metaheuristica | grasp | concluida | 582834.78 | 446.20 | 55 | 4 |
| 3 | heuristica | gulosa | concluida | 396833.50 | 1205.80 | 34 | 1 |
| 4 | metaheuristica | sa | concluida | 999639.82 | 0.00 | 100 | 7 |
| 4 | metaheuristica | ga | concluida | 977382.72 | 1.20 | 98 | 8 |
| 4 | metaheuristica | grasp | concluida | 581194.14 | 497.80 | 55 | 5 |
| 4 | heuristica | gulosa | concluida | 306224.28 | 1799.00 | 25 | 1 |
| 5 | metaheuristica | sa | concluida | 1388388.63 | 0.00 | 100 | 11 |
| 5 | metaheuristica | ga | concluida | 1363163.83 | 23.80 | 98 | 9 |
| 5 | metaheuristica | grasp | concluida | 792427.31 | 509.80 | 54 | 5 |
| 5 | heuristica | gulosa | concluida | 340935.55 | 1885.00 | 20 | 1 |
| 6 | metaheuristica | sa | concluida | 793197.69 | 889.00 | 52 | 15 |
| 6 | metaheuristica | ga | concluida | 812637.56 | 723.00 | 54 | 15 |
| 6 | metaheuristica | grasp | concluida | 769943.68 | 546.00 | 52 | 6 |
| 6 | heuristica | gulosa | concluida | 295108.80 | 1989.40 | 17 | 1 |
| 7 | metaheuristica | sa | concluida | 1065467.25 | 779.60 | 51 | 11 |
| 7 | metaheuristica | ga | concluida | 1777706.07 | 203.40 | 91 | 9 |
| 7 | metaheuristica | grasp | concluida | 1077921.15 | 546.00 | 52 | 5 |
| 7 | heuristica | gulosa | concluida | 378685.41 | 2408.00 | 15 | 1 |
| 8 | metaheuristica | sa | concluida | 1078790.30 | 744.80 | 51 | 9 |
| 8 | metaheuristica | ga | concluida | 368089.97 | 1641.80 | 16 | 5 |
| 8 | metaheuristica | grasp | concluida | 1077921.15 | 546.00 | 52 | 6 |
| 8 | heuristica | gulosa | concluida | 331626.85 | 2512.60 | 13 | 1 |
| 9 | metaheuristica | sa | concluida | 1217625.26 | 717.20 | 58 | 14 |
| 9 | metaheuristica | ga | concluida | 1013893.55 | 993.60 | 47 | 12 |
| 9 | metaheuristica | grasp | concluida | 1077921.15 | 546.00 | 52 | 5 |
| 9 | heuristica | gulosa | concluida | 300146.75 | 2366.80 | 12 | 1 |
| 10 | metaheuristica | sa | concluida | 1070212.89 | 932.60 | 50 | 13 |
| 10 | metaheuristica | ga | concluida | 1768052.92 | 232.00 | 91 | 7 |
| 10 | metaheuristica | grasp | concluida | 1077921.15 | 546.00 | 52 | 5 |
| 10 | heuristica | gulosa | concluida | 276279.31 | 2467.40 | 11 | 1 |

[Resumo CSV](metricas.csv) · [Todas as soluções](solucoes.csv) · [Rotas, agendas e histórico](execucoes.json)

O tempo de busca inclui a execução do método, sem a reavaliação posterior para exportação. Bloqueio de construção ou ausência de soluções em uma metaheurística não comprovam inviabilidade. Enumeração concluída sem soluções informa inviabilidade do modelo. Comparações com uma semente e orçamentos diferentes não constituem ranking científico dos métodos.
