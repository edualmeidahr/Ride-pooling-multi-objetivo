# Heurística independente de inserção gulosa

Implementação 3 da entrega: [HeuristicaGulosa](../codigo/darp/heuristicas/gulosa.py).
Ela constrói uma única solução, sem população, temperatura, reinícios, sorteios
ou busca local. Não executa GA, SA ou GRASP. Reutiliza apenas o operador estrutural
de inserir coleta/entrega e o avaliador comum aos métodos.

## Regra de construção

1. Começa com m rotas vazias e todos os pedidos pendentes.
2. Para cada pedido, veículo e par de posições de coleta/entrega, testa a inserção.
3. Descarta violações de capacidade/janela detectadas por podas necessárias e
   agenda as demais rotas para conferir todas as restrições.
4. Calcula os acréscimos de f1 e f2 em relação à rota antes da inserção.
5. Normaliza separadamente os acréscimos entre os candidatos viáveis daquela etapa:
   zi = (delta_i − menor_delta_i)/(maior_delta_i − menor_delta_i).
   Se a amplitude for zero, zi=0.
6. Escolhe a menor nota: peso_emissao × z1 + (1 − peso_emissao) × z2.
7. Em empate exato, prioriza menor acréscimo de f1, menor acréscimo de f2,
   menor índice interno do pedido, veículo e posições. Insere o escolhido e repete.
8. Confere a solução completa antes de retorná-la.

O padrão é peso_emissao=0,5; 1 prioriza emissão e 0 prioriza tempo perdido.
Essa ponderação orienta decisões locais. Não garante a melhor solução ponderada
global nem a fronteira de Pareto. Uma única chamada produz uma solução completa
ou informa bloqueio. Não confundir a normalização local com hipervolume ou com
o critério posterior de escolha de solução equilibrada dos relatórios.

No modo ambiental, f1 considera phi(Q), fatores de rua e os percursos incluindo
garagens; f2 soma espera e desvio em passageiro-minutos. Com phi=1 e sem fatores
de rua, f1 coincide com km. O agendamento OTIMO usa programação linear para
horários de uma sequência; a escolha das rotas permanece heurística.

Se nenhuma inserção for viável, retorna status bloqueada, solução/avaliação
ausentes e os pedidos pendentes. O histórico mostra as inserções já feitas.
Bloqueio não comprova inviabilidade da entrada: uma decisão gulosa anterior pode
ter impedido uma construção que outro método encontraria. Não há fallback
silencioso para atendimento individual nem aceitação de soluções inviáveis.

Custos de uma mesma sequência são reutilizados em cache local a cada chamada.
Os candidatos são mantidos como inserções leves; não se copia toda a solução
para avaliar cada possibilidade. Isso não muda a regra de escolha.

## Execução independente

Exemplo de dois pedidos, Q=1/2:

```powershell
.\.venv\Scripts\python.exe codigo/experimentos/executar_heuristica.py
```

Entrada ambiental de 12 pedidos, Q=1..10:

```powershell
.\.venv\Scripts\python.exe codigo/experimentos/executar_heuristica.py --config experimentos/comparacao_emissoes_q1_10.json --peso-emissao 0.5 --saida resultados/heuristica_gulosa_emissoes_q1_10
```

O executor reutiliza os blocos instancia/pedidos/m/capacidades/parametros_avaliacao
e modelo_emissoes da configuração. Sementes e parâmetros dos outros algoritmos
são ignorados; a heurística não tem semente. A semente do ambiente mantém os
mesmos fatores de rua. As saídas ficam na pasta escolhida, sem sobrescrever as
campanhas anteriores. Use pastas diferentes para pesos diferentes.

Uso como biblioteca:

```python
from darp import Avaliador, Parametros, HeuristicaGulosa, ler_instancia_json
inst = ler_instancia_json("dados/exemplo_pequeno.json", Q=2)
resultado = HeuristicaGulosa(peso_emissao=0.5).resolver(
    inst, Avaliador(inst, Parametros(alpha=2)))
if resultado.solucao is not None:
    print(resultado.avaliacao.objetivos)
```

## Saídas

- metricas.csv: Q, status, f1 e f2 da mesma solução, veículos e tempo de execução.
- execucoes.json: configuração, hashes, peso, unidade, ambiente e uma execução
  por Q. ponto contém rotas, agendas, distância física, emissão, espera, desvio
  e ocupação. Quando bloqueada, ponto=null e f1/f2 ficam vazios no CSV.
- historico: pedido e posição escolhidos, acréscimos, nota e faixas de normalização
  em cada etapa. IDs de pedido são internos, como nos demais algoritmos.
- candidatos_testados: tentativas de inserção, incluindo as inviáveis/repetidas.
- avaliacoes_rotas: chamadas efetivas a avaliar_rota durante a construção,
  após podas/cache. Não inclui a conferência final da solução completa. Não é
  diretamente equivalente ao contador agendamentos das campanhas anteriores.

## Validação em 13/10/2026

Sete testes verificam repetibilidade, preservação da entrada, cobertura,
capacidade, bloqueio, pesos inválidos, invariância ao trocar g por kg e saídas
recalculadas por arcos, horários e cargas.
No exemplo pequeno, peso 1 encontrou (46 km, 4,5 passageiro-minutos), e peso 0
encontrou (92 km, 0). Ambos coincidem com pontos da fronteira exata desse caso.
Isso valida o exemplo, não demonstra otimalidade geral da heurística.
Os oito testes dos operadores compartilhados também passaram.

```powershell
.\.venv\Scripts\python.exe codigo/experimentos/validar_heuristica.py
```

O teste operacional ambiental usa 12 pedidos, Q=1..10 e peso 0,5, com os mesmos
fatores da campanha ambiental existente. As dez construções terminaram com
soluções completas. A comparação com os outros métodos deve usar os mesmos
objetivos e conferir cada solução; o resultado de uma heurística pode melhorar
a referência empírica anterior, que nunca foi uma prova de ótimo.

Próxima etapa: integrar este executor ao menu junto do método exato e das
metaheurísticas, padronizando o formato de resultados antes de comparar métodos.
