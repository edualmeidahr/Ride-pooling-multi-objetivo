# Menu das três implementações

Ponto de entrada: [codigo/menu.py](../codigo/menu.py).

Na raiz do projeto, execute:

```powershell
.\.venv\Scripts\python.exe codigo/menu.py
```

O ambiente precisa de NumPy e SciPy (agendamento por programação linear);
Matplotlib é usado pelos geradores de gráficos existentes. A opção exata do
menu usa enumeração, sem depender de licença Gurobi.

## Opções

| Opção | Execução |
|---|---|
| 1 | Método exato: enumeração de sequências e combinação por subconjuntos |
| 2 | Metaheurística: SA, GA, GRASP ou os três |
| 3 | Heurística gulosa determinística, com peso configurável |
| 4 | Comparar as três categorias na mesma entrada pequena |
| 5 | Comparar gulosa e metaheurísticas, sem enumeração |
| 0 | Sair |

Depois de escolher a opção, informe o caminho de uma configuração experimental.
Enter seleciona `experimentos/exemplo_pequeno.json`, que tem dois pedidos.
Q pode ser um valor único ou, com Enter, todas as capacidades da configuração.
Para metaheurísticas, escolha métodos e uma semente (padrão 42).
Para gulosa, escolha peso da emissão (padrão 0,5; restante é peso do tempo).
A semente de busca não altera os fatores de rua, que têm sua própria semente
fixa na configuração ambiental.

Entradas disponíveis:

- `experimentos/exemplo_pequeno.json`: dois pedidos, Q=1/2, objetivo de distância.
- `experimentos/validacao_emissoes.json`: dois pedidos, Q=1/2/5/7/10, objetivo de CO2 sintético.
- `experimentos/comparacao_emissoes_q1_10.json`: 12 pedidos, Q=1..10, objetivo de CO2 sintético. Use opções 2, 3 ou 5.
- `experimentos/comparacao_100_corridas.json`: 100 pedidos, Q=1..10 e construção limitada para escala. Use opções 2, 3 ou 5; consulte o [protocolo de 100 corridas](EXPERIMENTO_100_CORRIDAS.md).

O método exato é limitado a seis pedidos e exige política `otimo`. Opções 1 e 4
rejeitam uma entrada maior antes de iniciar os algoritmos. Não recortam pedidos
automaticamente nem mudam a política de horário. O limite de seis é um controle
operacional; instâncias difíceis mesmo dentro dele podem levar mais tempo.

Os métodos compartilham demanda, frota, capacidade, matriz ambiental, phi e
política de horário. Cada método tem avaliador/cache próprio. O cache habilitado
pela configuração não compartilha soluções entre algoritmos. O exato devolve uma
fronteira, as metaheurísticas uma aproximação e a gulosa uma solução. Nenhuma
referência empírica é apresentada como prova de ótimo.

## Execução reproduzível sem preencher o menu

Comparação pequena:

```powershell
.\.venv\Scripts\python.exe codigo/menu.py --modo comparar --config experimentos/exemplo_pequeno.json
```

Comparação ambiental pequena, somente Q=1/2:

```powershell
.\.venv\Scripts\python.exe codigo/menu.py --modo comparar --config experimentos/validacao_emissoes.json --q 1 2
```

Comparação aproximada de 12 pedidos, selecionando SA e GA:

```powershell
.\.venv\Scripts\python.exe codigo/menu.py --modo comparar_aproximados --config experimentos/comparacao_emissoes_q1_10.json --algoritmos sa ga --seed 42 --peso-emissao 0.5
```

Modo individual: `--modo exato`, `--modo metaheuristica` ou `--modo heuristica`.
`--q` aceita vários valores na execução por argumentos. `--saida` informa a pasta
de exportação; se omitida, cada execução recebe uma pasta única em `resultados/menu`.
Caminhos relativos são resolvidos na raiz do projeto. Ao reutilizar explicitamente
uma pasta com `--saida`, seus arquivos de resultado são substituídos.

## Saída comum

- `RESUMO.md`: tabela legível, unidades, critério de seleção e limites.
- `metricas.csv`: uma linha por método/Q, com f1/f2 da mesma solução escolhida,
  veículos usados, status, tempo de busca, quantidade de pontos e ID da solução.
- `solucoes.csv`: todas as soluções finais, uma por linha, com os dois objetivos,
  distância física e rotas.
- `execucoes.json`: configuração, opções efetivas, hashes, ambiente ambiental,
  referências, rotas/horários/cargas, históricos e flag de conclusão.

O resumo seleciona uma solução por método/Q usando distância euclidiana ao
ideal dos objetivos normalizados, com pesos iguais. Escalas comuns vêm da
referência do Q: exata se enumerada ou empírica entre os métodos executados.
É um critério de apresentação, separado dos pesos de busca da gulosa. Não
apresenta mínimos independentes como uma solução.

Status `otimo` significa enumeração concluída, dentro das tolerâncias numéricas;
`inviavel` significa que a enumeração concluiu sem solução. `bloqueada` na gulosa
e `sem_solucao_encontrada` nas metaheurísticas não provam inviabilidade. Nesses
casos, f1/f2 ficam vazios. As soluções retornadas são reavaliadas sem cache.

Arquivos são atualizados após cada método/Q. Se interromper com Ctrl+C, o JSON
mantém `concluida=false`; as soluções já exportadas permanecem. O menu não possui
retomada automática, mas a execução por argumentos aceita `--retomar` junto da
mesma configuração/opções e `--saida` original. Executa só os métodos/Q pendentes;
recusa mudanças na demanda, opções, ambiente ou fontes dos algoritmos/modelo.
Os formatos desses arquivos são próprios do menu; não
devem ser enviados diretamente aos geradores antigos de gráficos das campanhas,
que esperam outro esquema. As campanhas/relatórios anteriores permanecem separados.

## Validação

O teste `codigo/experimentos/validar_menu.py` verifica as três categorias na mesma
entrada, modos individuais, emissão ambiental, objetivos pareados, configuração
das escolhas interativas, bloqueio/inviabilidade e rejeição de enumeração grande.

Foi exportada uma comparação ambiental pequena em
[resultados/menu_validacao/RESUMO.md](../resultados/menu_validacao/RESUMO.md), com
Q=1/2 e cinco métodos: exato, SA, GA, GRASP e gulosa.
Uma semente e orçamentos distintos não permitem concluir superioridade científica.
