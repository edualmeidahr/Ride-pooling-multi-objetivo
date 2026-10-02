# Fluxogramas do código atual

Auditoria de 01/10/2026. O projeto é uma biblioteca com scripts independentes:
não há um programa principal que execute todas as etapas automaticamente.
Execute um dos arquivos em `codigo/experimentos/`. As setas abaixo representam
chamadas e passagem de dados, não processos simultâneos.

## 1. Visão geral dos pontos de entrada

```mermaid
flowchart TD
    START[Escolher experimento] --> Q[capacidade_q.py]
    START --> F[fase2_fronteira.py]
    START --> M[comparar_metaheuristicas.py]
    START --> T[Scripts de validação]
    Q --> L[instancia.py: ler texto ou JSON e reduzir pedidos]
    F --> L
    M --> L
    T --> L
    L --> R[rede.py: paradas e matrizes, quando a entrada é uma rede]
    Q --> C[cenarios.py: copiar cenário para cada Q]
    C --> E[exato.py: enumerar e combinar rotas]
    F --> E
    F --> G[mip.py: Gurobi opcional]
    M --> H[SA, GA ou GRASP]
    H --> O[operadores.py: construir, mover e cruzar pedidos]
    O --> A[avaliador.py: horários, restrições e objetivos]
    E --> A
    T --> A
    A --> S[solucao.py: rotas, cobertura e precedência]
    A --> P[pareto.py e ArquivoPareto: filtrar alternativas]
    P --> OUT[Resultados do experimento]
    G --> OUT
    OUT --> FILE[CSV, JSON, gráfico ou saída no terminal]
    FILE --> SUM[resumir_capacidade.py: ler JSON de capacidade]
    SUM --> FIN[resumo.csv e capacidade_q_comparativo.png]
```

O comparador usa BORDO por padrão; o avaliador isolado e o estudo exato de Q
usam OTIMO. O Gurobi constrói seu próprio modelo, sem chamar o avaliador durante
a otimização; a Fase 2 usa o avaliador depois para conferir os pontos do solver.

## 2. Estudo de capacidade Q=1 até 20

```mermaid
flowchart TD
    A[Argumentos: instância, pedidos, m, alpha e Q] --> B[Ler dados e reduzir aos pedidos escolhidos]
    B --> C[Fixar phi=1 e política OTIMO]
    C --> D[Ordenar capacidades e selecionar próximo Q]
    D --> E[Criar cenário sem alterar Q e m da instância base]
    E --> F{Fronteira em cache para min de Q e demanda total?}
    F -->|Sim| G[Reutilizar fronteira equivalente]
    F -->|Não| H[Enumerar subconjuntos de solicitações]
    H --> I[Gerar sequências com pareamento e precedência]
    I --> J[Podar excesso de capacidade e janelas impossíveis]
    J --> K[Agendar e avaliar cada rota com OTIMO]
    K --> L[Guardar rotas viáveis não dominadas por subconjunto]
    L --> M[Combinar subconjuntos usando até m veículos]
    M --> N[Filtrar Pareto e guardar fronteira no cache]
    N --> G
    G --> O[Reavaliar cada solução completa: estrutura, horários e objetivos]
    O --> P[Conferir inclusão: pontos de Q menor são igualados ou dominados]
    P --> V[Registrar cenário viável ou inviável e seus pontos]
    V --> R{Há outro Q?}
    R -->|Sim| D
    R -->|Não| S[Salvar fronteiras.json e fronteiras.csv]
    S --> T[Executar resumir_capacidade.py separadamente]
    T --> U[Salvar resumo.csv e gráfico comparativo]
```

Se a fronteira estiver vazia, o JSON registra `inviavel`; o CSV de pontos não
possui linhas para aquele Q. O limite de seis pedidos protege contra o custo
combinatório da enumeração. O cache reaproveita Q acima da demanda total;
capacidades inferiores continuam sendo calculadas separadamente.

## 3. Avaliação compartilhada e políticas de horário

```mermaid
flowchart TD
    A[Solucao: sequências e partidas opcionais] --> B[conferir_estrutura: cobertura, pares e precedência]
    B --> C[Percorrer rotas não vazias]
    C --> D{Política de horário}
    D -->|CEDO| E[Propagar atendimento mais cedo]
    D -->|BORDO| F[Atrasar saída e embarques usando folgas]
    D -->|OTIMO| G{NumPy e SciPy disponíveis?}
    G -->|Não| ERR[Erro explícito: instalar dependências]
    G -->|Sim| H[PL: minimizar contribuição de f2 com a sequência fixa]
    H --> I{PL encontrou solução?}
    I -->|Sim| J[Montar agenda com horários da PL]
    I -->|Não| K[Agenda BORDO para diagnosticar violações]
    E --> V[Verificar capacidade, janelas, duração e tempo a bordo]
    F --> V
    J --> V
    K --> V
    V --> O[Calcular distância, desvio, espera e custo auxiliar]
    O --> R{Há outra rota?}
    R -->|Sim| C
    R -->|Não| S[Somar f1 e f2 e devolver lista de violações]
    S --> W[Busca, enumeração ou validação decide como usar o resultado]
```

`avaliar_rota` trabalha com uma rota e não exige cobertura global: isso permite
avaliar construções parciais. `avaliar` verifica a solução completa.
`avaliar_com_B` recebe uma agenda externa e é usado para reproduzir `.res` e
conferir o Gurobi. Um movimento preservando estrutura ainda pode violar tempo
ou capacidade; viabilidade completa depende do avaliador.

## 4. Loop das metaheurísticas

```mermaid
flowchart TD
    A[Carregar instância e escolher SA, GA ou GRASP] --> B[Criar avaliador e gerador com semente]
    B --> C[Construir solução individual e soluções iniciais]
    C --> D{Algoritmo}
    D -->|SA| S[Vizinhos e aceitação por energia e temperatura]
    D -->|GA| G[Cruzamento, mutação, ranking e crowding]
    D -->|GRASP| R[Construção randomizada e busca local ponderada]
    S --> E[Avaliar candidatos]
    G --> E
    R --> E
    E --> P[Atualizar arquivo externo com soluções viáveis não dominadas]
    P --> F{Critério de parada do método atingido?}
    F -->|Não| D
    F -->|Sim| O[ResultadoOtimizacao: fronteira, tempo, histórico e contadores]
    O --> H[Comparador: extremos e HV com referência comum]
    H --> END[Mostrar rotas no terminal e gráfico opcional]
```

Esse diagrama resume os métodos; o arquivo não recebe obrigatoriamente todo
vizinho intermediário. SA registra vizinhos viáveis; GA registra população e
descendentes; GRASP registra a construção e o resultado da busca local.
Os contadores atuais não contabilizam todas as avaliações internas.
