# Resumo de soluções reais

Cada linha abaixo representa uma única solução encontrada, com distância e tempo perdido do mesmo conjunto completo de rotas. A seleção é feita entre as soluções da referência empírica (ou exata, no caso reduzido), reunindo métodos e sementes por Q. O método e a semente identificam a origem; não são um ranking dos algoritmos.

## Critério de equilíbrio

Não existe uma melhor solução única sem definir preferências. Adotamos pesos iguais para os dois objetivos normalizados: escore = sqrt(0,5 × z1² + 0,5 × z2²). Menor é melhor segundo esse critério. zi = (fi − mínimo_i)/(máximo_i − mínimo_i), usando os extremos da referência do mesmo Q, comuns aos métodos e sementes. Se a amplitude for zero, usa-se divisor 1. O ponto ideal formado pelos mínimos é apenas um alvo matemático; não é apresentado como solução realizável. A escolha sempre copia uma solução efetivamente registrada. Empates são resolvidos por f1, f2 e identificador. O escore não é hipervolume, não prova otimalidade e não deve ser comparado entre Q com escalas distintas.

Nesta campanha, f1 representa gramas de CO2 estimado pelo modelo sintético e f2 passageiro-minutos. Os fatores não são calibrados.

| Q | Origem | Semente | f1 | f2 | Espera | Desvio | Veículos | Carga máxima | ID |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | GA | 42 | 17590.40 | 0.00 | 0.00 | 0.00 | 2 | 1 | Q1_ga_seed42_p0 |
| 2 | GA | 42 | 8795.20 | 4.50 | 3.50 | 1.00 | 1 | 2 | Q2_ga_seed42_p0 |
| 5 | GA | 42 | 12215.56 | 4.50 | 3.50 | 1.00 | 1 | 2 | Q5_ga_seed42_p0 |
| 7 | GA | 42 | 17101.78 | 4.50 | 3.50 | 1.00 | 1 | 2 | Q7_ga_seed42_p0 |
| 10 | GA | 42 | 17101.78 | 4.50 | 3.50 | 1.00 | 1 | 2 | Q10_ga_seed42_p0 |

## Arquivos e rastreabilidade

- [solucoes_equilibradas_por_q.csv](solucoes_equilibradas_por_q.csv): uma escolha equilibrada por Q, com os dois objetivos e as rotas.
- [solucoes_representativas.csv](solucoes_representativas.csv): três escolhas por execução: equilibrada, menor distância e menor tempo perdido. Os perfis podem selecionar a mesma solução.
- [solucoes.csv](solucoes.csv): todas as soluções finais, uma por linha, com objetivos pareados e rotas.
- [metricas.csv](metricas.csv): resumo simples, uma linha por execução. f1/f2/veiculos_usados descrevem a mesma solução equilibrada; tempo_busca (segundos), hv_relativo (fração) e cardinalidade descrevem a execução/fronteira.
- [metricas_tecnicas.csv](metricas_tecnicas.csv): detalhamento dos três perfis, escore, agendamentos e cache.
- [execucoes.json](execucoes.json): registro original completo, preservado. Localize Q/metodo/seed e use indice_ponto_json (começa em zero) em pontos para acessar horários e cargas.

rotas_json lista as sequências de atendimento de todos os veículos; listas vazias representam veículos não utilizados. As garagens são implícitas. agendas no JSON acompanha somente as rotas não vazias, na mesma ordem. Os identificadores são nós de coleta/entrega, não os IDs das paradas físicas.

Os antigos min_f1/min_f2 permanecem no JSON como estatísticas históricas da fronteira. No resumo simples, f1 e f2 são os objetivos da solução equilibrada identificada. No detalhamento técnico, os três perfis têm pares de objetivos identificados. Nenhuma média ou mediana dos objetivos é apresentada como uma rota real.
