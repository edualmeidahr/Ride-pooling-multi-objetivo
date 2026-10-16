# Ride-pooling — três implementações

Esta é a versão enxuta da branch `apresentacao`, pronta para demonstrar ao professor. Ela contém todo o código
necessário, entradas de exemplo e documentação; não contém campanhas antigas.

| Pasta | Implementação |
|---|---|
| implementacao1 | Método exato: enumeração e programação dinâmica. |
| implementacao2 | Heurística: construção gulosa determinística. |
| implementacao3 | Metaheurísticas: GA, SA, GRASP e ACO. |
| comum | Avaliador, dados, rede, emissão e operadores compartilhados. |
| dados | Redes e pedidos dos exemplos de 2, 12 e 100 corridas. |
| experimentos | Configurações que selecionam entrada, Q e parâmetros. |

## Instalar uma vez

Abra o terminal na raiz desta branch. Para baixar somente esta versão, use
Code → Download ZIP com a branch apresentacao selecionada no GitHub.
É necessário Python 3.10 ou superior e acesso aos pacotes NumPy/SciPy.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Demonstrar

```powershell
.\.venv\Scripts\python.exe menu.py
```

No menu: 1 = exato; 2 = heurística; 3 = metaheurísticas; 4 = comparar as três
categorias; 5 = comparar aproximados; 0 = sair. Para a demonstração pequena,
selecione 4 e aceite os padrões com Enter. São executados os seis métodos
com Q=1 e Q=2. A pasta dos resultados é informada ao final.

Também é possível rodar cada pasta diretamente:

```powershell
.\.venv\Scripts\python.exe implementacao1/executar.py --q 2 --saida resultados/exato
.\.venv\Scripts\python.exe implementacao2/executar.py --q 2 --saida resultados/heuristica
.\.venv\Scripts\python.exe implementacao3/executar.py --q 2 --seed 42 --saida resultados/metaheuristicas
```

As três chamadas usam o exemplo de dois pedidos por padrão. Na terceira,
`--algoritmos aco` permite selecionar apenas a colônia de formigas.

Para comparar tudo com uma única chamada:

```powershell
.\.venv\Scripts\python.exe menu.py --modo comparar --config experimentos/exemplo_pequeno.json --q 2 --saida resultados/demonstracao
```

Abra resultados/demonstracao/RESUMO.md. Os outros arquivos são metricas.csv,
solucoes.csv e execucoes.json. O manual detalha suas colunas e os formatos de entrada.
O exato é limitado a seis pedidos; para entradas maiores use os aproximados.

O pacote funciona após a extração sem o repositório original, GitHub ou Gurobi.
Não inclui Python nem bibliotecas binárias. Leia MANUAL.md para detalhes.
