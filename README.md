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

**Para rodar 100 corridas: digite 6 e pressione Enter.**

Essa opção executa SA, GA, GRASP, ACO e gulosa, com Q de 1 a 10 e semente 42:
50 execuções ao todo. São usados os 100 pedidos completos e o modelo de CO2.
Não é necessário informar caminhos, capacidade ou outros parâmetros.

O programa mostra a pasta de saída e avisa quando inicia e termina cada método/Q.
Abra o `RESUMO.md` dessa pasta para consultar os resultados. A campanha pode
demorar; os resultados são salvos ao término de cada método/Q.

Outras opções: 1 = exato; 2 = heurística; 3 = metaheurísticas; 4 = comparar as três
categorias no pequeno; 5 = comparar aproximados; 0 = sair.
Depois de escolher uma dessas opções, selecione o exemplo pelo número:

| Número do exemplo | Entrada |
|---|---|
| 1 | 2 corridas — distância |
| 2 | 2 corridas — emissão de CO2 |
| 3 | 12 corridas — emissão de CO2 |
| 4 | 100 corridas — emissão de CO2 |
| 5 | Caminho de uma configuração própria |
| 0 | Voltar |

As opções com exato oferecem apenas os exemplos pequenos e a configuração
própria, sujeita ao limite de seis pedidos. Para rodar somente uma metaheurística
com 100 corridas, selecione 3 no menu principal, 4 no exemplo, Enter para todos
os Q e escolha a metaheurística. Para somente a gulosa, use 2, 4 e Enter.

Para a demonstração pequena, escolha 4 no menu principal e aceite os três padrões
com Enter (exemplo, Q e metaheurísticas). A semente fica em 42 e o peso da gulosa
em 0,5. Para alterar esses parâmetros, utilize os argumentos de execução.

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
