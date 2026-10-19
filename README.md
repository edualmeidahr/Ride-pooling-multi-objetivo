# Ride-pooling multiobjetivo — guia para executar o trabalho

A ideia do projeto é organizar as corridas e decidir quais passageiros podem
compartilhar um veículo. A gente tenta reduzir a emissão de CO2 e o tempo
perdido pelas pessoas, respeitando capacidade, horários, duração das rotas e
tempo máximo a bordo. Cada pedido precisa ser atendido por completo.

Há um método exato, uma heurística gulosa e **sete metaheurísticas**: quatro
programadas no projeto e três que usam motores prontos de bibliotecas.
Este guia mostra como instalar, escolher os métodos e encontrar os resultados.
As fórmulas e os detalhes do modelo estão no [MANUAL.md](MANUAL.md).

## 1. Instalar uma vez

Abra um terminal **na pasta do projeto**, a mesma em que estão `menu.py` e
`requirements.txt`. Você precisa de Python 3.10 ou superior e internet para
baixar as dependências. Esta versão foi instalada e testada em **Windows
com Python 3.14.6**, NumPy 2.5.4, SciPy 1.18.1, pymoo 0.6.2 e simanneal 0.5.0.
Outras versões compatíveis de Python não foram certificadas nesta validação.

No PowerShell, crie um ambiente separado e instale tudo nele:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Não precisa ativar o ambiente para usar esse caminho completo. Se o Windows
não reconhecer `python`, tente `py -3` no primeiro comando.

No Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

**Nos exemplos com `python` abaixo, use o Python desse ambiente.** Você pode
ativá-lo com `.\.venv\Scripts\Activate.ps1` no PowerShell ou
`source .venv/bin/activate` no Linux/macOS. Se a ativação do PowerShell estiver
bloqueada, basta trocar `python` por `.\.venv\Scripts\python.exe` nos comandos;
não é necessário alterar a política do sistema.

As bibliotecas exigidas já estão no `requirements.txt`. Você não precisa de
Gurobi, conta em serviço externo ou código de outra branch para executar.

## 2. Comece por esta demonstração

Este comando pequeno já compara o exato, a gulosa e as quatro metaheurísticas
próprias, deixando os métodos escolherem Q. O orçamento exploratório é **10
rodadas** (pedido para reduzir as 100 iterações da colônia de formigas):

```powershell
python menu.py --modo comparar --config experimentos/q_variavel_exemplo.json --saida resultados/demo_10
```

No Linux, o mesmo atalho:

```bash
./rodar_demo.sh
```

Sem ativar o ambiente, o mesmo comando no Windows é:

```powershell
.\.venv\Scripts\python.exe menu.py --modo comparar --config experimentos/q_variavel_exemplo.json
```

Ao terminar, o programa informa a pasta dos resultados. Abra primeiro o
**`RESUMO.md` dessa pasta**. Sem `--saida`, ele cria uma pasta nova dentro de
`resultados/menu/`, evitando misturar a demonstração com outra execução.

O exemplo tem dois pedidos, cada um com um grupo indivisível de três pessoas,
e permite Q=4, 6 ou 10. A fronteira exata é:

| Capacidade Q | Emissão estimada, g CO2 | Tempo perdido, passageiro-minutos |
|---:|---:|---:|
| 6 | 12.215,56 | 13,5 |
| 4 | 17.590,40 | 0 |

São duas escolhas possíveis: compartilhar um veículo maior reduz emissão;
usar dois menores evita a perda de tempo desse agrupamento. Não existe uma
única resposta melhor nos dois objetivos. Q=10 não melhora esse exemplo.
Os fatores de emissão são **hipóteses sintéticas**, sem calibração de frota real.

## 3. Quais métodos existem e onde estão os códigos?

| Categoria / identificador | O que executa | Código |
|---|---|---|
| `exato` | Enumeração e programação dinâmica próprias | `implementacao1/exato.py` |
| `gulosa` | Uma construção determinística por inserções | `implementacao2/gulosa.py` |
| `sa` | Simulated Annealing próprio | `implementacao3/sa.py` |
| `ga` | Genético próprio, inspirado no NSGA-II | `implementacao3/ga.py` |
| `grasp` | GRASP próprio | `implementacao3/grasp.py` |
| `aco` | Colônia de formigas própria | `implementacao3/colonia_formigas.py`, com adaptador em `aco.py` |
| `ga_lib` | NSGA-II pronto do **pymoo** | `implementacao3/ga_biblioteca.py` |
| `sa_lib` | SA pronto do **simanneal** | `implementacao3/sa_biblioteca.py` |
| `pso_lib` | PSO pronto do **pymoo** | `implementacao3/pso_biblioteca.py` |

Os métodos `*_lib` realmente usam os ciclos de busca das bibliotecas. A parte
específica deste trabalho — transformar candidatos em rotas, calcular os
objetivos e verificar as restrições — continua no projeto. O suporte comum
desses adaptadores está em `implementacao3/suporte_bibliotecas.py`.

O NSGA-II da biblioteca recebe os dois objetivos diretamente. SA e PSO
exploram combinações com pesos `(0,8;0,2)`, `(0,5;0,5)` e `(0,2;0,8)` e guardam
as soluções viáveis em um arquivo Pareto comum. Por isso, essas duas versões
são adaptações para explorar o problema multiobjetivo, não motores
multiobjetivo nativos. Uma busca curta pode deixar de encontrar alternativas.

SciPy/HiGHS escolhe os horários de atendimento para uma ordem de visitas já
definida, quando a política é `otimo`. Ele é usado também pelos métodos
próprios; isso não transforma seus algoritmos de busca em algoritmos de biblioteca.

```text
menu.py                   menu e execução por argumentos
requirements.txt          dependências
implementacao1/           método exato e executar.py
implementacao2/           gulosa e executar.py
implementacao3/           sete metaheurísticas, fábrica, suporte e executar.py
comum/                    dados, rede, solução, avaliador, Q, operadores e auditoria
dados/                    redes e pedidos de transporte em JSON
experimentos/             configurações e scripts de comparação/auditoria
tests/                    testes automatizados
resultados/               arquivos gerados ao executar; pasta ignorada pelo Git
MANUAL.md                 detalhes técnicos
```

## 4. Q fixo, Q variável e os exemplos disponíveis

**Q** é a capacidade de cada veículo, e **m** é o máximo de veículos disponíveis.
O `q` minúsculo dentro de um pedido é o número de passageiros daquele grupo.
A capacidade é um limite: ninguém é obrigado a lotar um veículo.

- **Fixo:** uma busca separada para cada Q da configuração.
- **Variável:** uma única busca por metaheurística, escolhendo Q e rotas juntos.
  Cada solução usa veículos da mesma capacidade; soluções diferentes podem
  escolher Q diferentes. Não há mistura de tipos dentro da mesma solução.

Mais capacidade permite compartilhar mais, mas pode mudar a categoria do
veículo e sua emissão por quilômetro. Sem essa diferença de custo/emissão,
uma capacidade maior consegue reproduzir as opções das menores.

| Configuração em `experimentos/` | Pedidos | Capacidades | Uso |
|---|---:|---|---|
| `exemplo_pequeno.json` | 2 | 1 e 2 | Demonstração por distância; padrão fixo |
| `validacao_emissoes.json` | 2 | 1, 2, 5, 7 e 10 | Demonstração com emissão; padrão fixo |
| `q_variavel_exemplo.json` | 2 grupos de 3 | 4, 6 e 10 | Escolha entre categorias; padrão variável |
| `comparacao_emissoes_q1_10.json` | 12 | 1 a 10 | Comparação aproximada com emissão |
| `comparacao_100_corridas.json` | 100 | 1 a 10 | Entrada maior com construção limitada |

Os dados físicos ficam em `dados/`; os JSONs acima escolhem os pedidos,
capacidades, frota e parâmetros dos métodos. Passe uma **configuração de
`experimentos/`** para `--config`, não diretamente a demanda de `dados/`.

O exato é limitado a **seis pedidos**. Para 12 ou 100, use `heuristica`,
`metaheuristica` ou `comparar_aproximados`. Os cem pedidos são todos exigidos;
o programa não reduz a entrada para facilitar a execução.

## 5. Usar o menu interativo

```powershell
python menu.py
```

### Menu principal

| Opção | O que faz |
|---|---|
| 0 | Sair |
| 1 | Executar somente o método exato |
| 2 | Executar somente a gulosa |
| 3 | Escolher metaheurísticas com Q fixo por busca |
| 4 | Comparar exato, gulosa e metaheurísticas em entrada pequena |
| 5 | Comparar gulosa e metaheurísticas em entrada maior |
| 6 | Atalho de cem pedidos: quatro métodos próprios e gulosa, Q=1 a 10, semente 42 — 50 execuções |
| 7 | Escolher metaheurísticas para otimizar Q junto com as rotas |

Nas opções 1 a 5, o menu usa capacidade fixa. A opção 7 usa capacidade variável.
A opção 6 mantém o atalho original e não inclui bibliotecas automaticamente.

### Escolha do exemplo

| Opção | Entrada |
|---|---|
| 0 | Voltar ao menu principal |
| 1 | Dois pedidos, distância — padrão ao apertar Enter |
| 2 | Dois pedidos, emissão de CO2 |
| 3 | Doze pedidos, emissão de CO2 |
| 4 | Cem pedidos, emissão de CO2 |
| 5 | Digitar o caminho de uma configuração própria |

Os menus que incluem o exato oferecem apenas os exemplos pequenos e a opção
de caminho próprio. Para abrir `q_variavel_exemplo.json` pelo menu, escolha
5 e informe `experimentos/q_variavel_exemplo.json`.

Na pergunta sobre Q, Enter usa todos os valores da configuração. Você também
pode digitar um valor, como `6`, ou uma lista, como `4, 6, 10`.

### Submenu das metaheurísticas

| Opção | Métodos |
|---|---|
| 1 | SA próprio |
| 2 | GA próprio |
| 3 | GRASP próprio |
| 4 | Os quatro próprios — padrão ao apertar Enter |
| 5 | ACO própria |
| 6 | GA de biblioteca |
| 7 | SA de biblioteca |
| 8 | PSO de biblioteca |
| 9 | As três versões de biblioteca |
| 10 | Todas as sete metaheurísticas |

**Atenção aos dois menus:** 7 no menu principal escolhe Q variável; 7 no
submenu escolhe o SA de biblioteca. A semente do menu é 42 e o peso da
gulosa é 0,5. Para mudar esses valores, use os argumentos abaixo.

## 6. Comandos prontos para copiar

Cada bloco é uma execução independente. Os quatro métodos próprios continuam
sendo o padrão quando `--algoritmos` não aparece.

Comparação atual, com referência exata e Q variável:

```powershell
python menu.py --modo comparar --config experimentos/q_variavel_exemplo.json
```

Somente as três versões de biblioteca:

```powershell
python menu.py --modo metaheuristica --config experimentos/q_variavel_exemplo.json --algoritmos bibliotecas
```

Exato, gulosa e todas as sete metaheurísticas — nove métodos ao todo:

```powershell
python menu.py --modo comparar --config experimentos/q_variavel_exemplo.json --algoritmos todos
```

Uma versão de biblioteca por vez; troque `ga_lib` por `sa_lib` ou `pso_lib`:

```powershell
python menu.py --modo metaheuristica --config experimentos/q_variavel_exemplo.json --algoritmos ga_lib
```

Somente o exato ou somente a gulosa:

```powershell
python menu.py --modo exato --config experimentos/q_variavel_exemplo.json
```

```powershell
python menu.py --modo heuristica --config experimentos/q_variavel_exemplo.json --peso-emissao 0.5
```

Fixar Q=6 e comparar GA próprio com GA de biblioteca:

```powershell
python menu.py --modo metaheuristica --config experimentos/q_variavel_exemplo.json --capacidade fixo --q 6 --algoritmos ga ga_lib --seed 42
```

Comparação aproximada em doze pedidos:

```powershell
python menu.py --modo comparar_aproximados --config experimentos/comparacao_emissoes_q1_10.json --capacidade variavel --algoritmos todos --max-consultas-rotas 20000 --saida resultados/comparacao_12
```

Cem pedidos, somente bibliotecas:

```powershell
python menu.py --modo metaheuristica --config experimentos/comparacao_100_corridas.json --capacidade variavel --algoritmos bibliotecas --max-consultas-rotas 30000 --saida resultados/bibliotecas_100
```

As entradas maiores podem demorar. Falta de solução dentro de um orçamento
curto significa que a busca não encontrou uma solução completa nesse esforço;
não prova que atender os pedidos seja impossível.

### Executar por pasta

Os três `executar.py` usam o mesmo executor e fixam a categoria. Por padrão,
utilizam o exemplo pequeno de distância. Você também pode passar `--config`:

```powershell
python implementacao1/executar.py --q 2 --saida resultados/exato_pasta
```

```powershell
python implementacao2/executar.py --q 2 --saida resultados/gulosa_pasta
```

```powershell
python implementacao3/executar.py --config experimentos/q_variavel_exemplo.json --algoritmos bibliotecas --saida resultados/bibliotecas_pasta
```

### Todos os argumentos do executor

```powershell
python menu.py --help
```

| Argumento | Valores / efeito | Padrão |
|---|---|---|
| `--modo` | `exato`, `heuristica`, `metaheuristica`, `comparar`, `comparar_aproximados` | Sem modo, abre o menu |
| `--config` | Caminho da configuração de experimento | `experimentos/exemplo_pequeno.json` |
| `--algoritmos` | Um ou mais entre `sa ga grasp aco ga_lib sa_lib pso_lib`; grupos `bibliotecas` ou `todos` | `sa ga grasp aco` |
| `--seed` | Semente inteira da busca | `42` |
| `--peso-emissao` | Peso de 0 a 1 na construção gulosa | `0.5` |
| `--q` | Uma capacidade ou lista, como `--q 4 6 10` | Lista da configuração |
| `--capacidade` | `fixo` ou `variavel`; prevalece sobre o JSON | Campo do JSON ou `fixo` |
| `--max-consultas-rotas` | Limite positivo de consultas por metaheurística | Limite do JSON, se houver; senão, só limites nativos |
| `--saida` | Pasta de resultados | Nova pasta em `resultados/menu/` |
| `--retomar` | Continua uma campanha preservando métodos concluídos; exige `--saida` | Desativado |
| `-h`, `--help` | Mostra a ajuda | — |

`comparar` inclui exato, gulosa e as metaheurísticas selecionadas.
`comparar_aproximados` inclui gulosa e as metaheurísticas selecionadas.
`--algoritmos` não seleciona exato ou gulosa: isso é definido por `--modo`.
Não repita métodos nem combine um grupo com um método já presente nele.

O limite de consultas é **total por metaheurística/semente**, incluindo acertos
de cache e inicialização. No modo fixo, cada Q recebe a divisão inteira desse
total pelo número de capacidades. No variável, o domínio compartilha o total.
SA e PSO de biblioteca dividem seu limite entre as trajetórias de pesos,
deixando o resto para a última. Exato e gulosa de referência não são limitados
por essa opção. Os limites nativos ainda podem encerrar uma busca antes.

O peso da gulosa não altera os pesos internos de SA/PSO. Nos JSONs, cada
método tem seus parâmetros em `algoritmos`: população/gerações no GA,
temperaturas/iterações no SA de biblioteca e população/iterações no PSO.
Os pesos de SA/PSO podem ser informados como uma lista de pares em `pesos`.
Campos herdados `sementes`, `saida` e `referencia` do JSON são metadados:
não substituem `--seed`, `--saida` nem a referência calculada pelo executor.

## 7. Onde encontrar e como ler os resultados

Cada campanha gera:

| Arquivo | Para que serve |
|---|---|
| `RESUMO.md` | Leitura inicial: uma solução real por método, com Q, objetivos e uso de veículos |
| `metricas.csv` | O resumo em tabela, com identificação de implementação própria/biblioteca e versão |
| `solucoes.csv` | Todos os pontos retornados e as rotas correspondentes |
| `execucoes.json` | Configuração, ambiente, sementes, versões, rotas, horários, contadores e histórico |

**f1** é distância em km no exemplo sem ambiente ou emissão estimada em g CO2
no modo ambiental. **f2** é tempo perdido em passageiro-minutos: espera em
relação ao horário desejado mais desvio em relação à viagem direta. f2=0
não quer dizer que a viagem levou zero minutos.

O resumo escolhe um representante pela proximidade do ideal normalizado,
com pesos iguais. A referência é exata nos casos em que o exato foi executado;
nos demais, é a união empírica dos métodos. No modo variável a referência é
global; no fixo, é separada por Q. Os mínimos de linhas diferentes não devem
ser combinados como se fossem uma única solução.

Todas as soluções exportadas passam pela auditoria independente. Os JSONs
registram origem, biblioteca, versão, motivo de parada, consultas, chamadas
PL e Q visitados. O tempo de busca não inclui a reavaliação de exportação.
Tempos, consultas e chamadas PL medem esforços diferentes.

### Retomar uma execução

Primeiro execute com uma pasta explícita:

```powershell
python menu.py --modo metaheuristica --config experimentos/q_variavel_exemplo.json --algoritmos bibliotecas --saida resultados/retomada_bibliotecas
```

Para continuar, repita o comando e acrescente `--retomar`:

```powershell
python menu.py --modo metaheuristica --config experimentos/q_variavel_exemplo.json --algoritmos bibliotecas --saida resultados/retomada_bibliotecas --retomar
```

Se já terminou, o executor reconhece a conclusão. Se foi interrompida,
preserva os métodos concluídos e refaz o método que estava em andamento.
Configuração, código, domínio, orçamento, semente e versões das bibliotecas
precisam coincidir. Não restaura a população ou temperatura no meio da busca.
Repetir uma pasta sem `--retomar` substitui os arquivos dessa campanha.

## 8. Testes, comparação e auditoria

Rodar todos os testes:

```powershell
python -m unittest discover -s tests -v
```

Comparar Q fixo e variável em 12 e 100 pedidos, com três sementes e orçamento
equivalente. Sem `--algoritmos`, o script mantém os quatro métodos próprios:

```powershell
python experimentos/comparar_q.py --orcamento 2000 --sementes 42 43 44
```

Para comparar as três bibliotecas em uma pasta diferente:

```powershell
python experimentos/comparar_q.py --orcamento 2000 --sementes 42 43 44 --algoritmos bibliotecas --saida resultados/bibliotecas_piloto
```

O script aceita `--tamanhos 12`, `--tamanhos 100` ou ambos, `--orcamento`,
`--sementes`, `--saida` e a mesma seleção `--algoritmos` do executor.
Ele eleva os limites nativos para priorizar o orçamento de consultas, usa
construção limitada e grava `comparacao.json` e `RESUMO.md` na pasta escolhida.
Sua referência e seu hipervolume são empíricos, não certificados como ótimos.

Reauditar os horários já exportados de uma ou mais pastas:

```powershell
python experimentos/auditar_q.py resultados/comparacao_12 resultados/bibliotecas_piloto --saida output/auditoria_bibliotecas.json
```

Use pastas criadas pelos comandos anteriores. O auditor aceita uma lista de
pastas e `--saida`. Ele recalcula as restrições
e os objetivos pelos horários gravados, sem reagendar rotas. Confira também
`--help` dos dois scripts para consultar os argumentos.

## 9. Se algo der errado

| Situação | O que conferir |
|---|---|
| `python` não encontrado | Instalação do Python; no Windows, tente `py -3` |
| `No module named ...` | Use o Python da `.venv` e rode `python -m pip install -r requirements.txt` nele |
| Erro citando pymoo/simanneal | A biblioteca precisa estar instalada; não há troca silenciosa para método próprio |
| `menu.py` não encontrado | Abra o terminal na raiz do projeto |
| Campo de configuração ausente | Use um JSON de `experimentos/`, não a demanda de `dados/` |
| Exato rejeita a entrada | Ele aceita até seis pedidos; use os aproximados para 12/100 |
| Execução demorada | Comece pelo caso pequeno ou use um orçamento de consultas |
| Nenhuma solução encontrada | Examine orçamento, construção e restrições; não significa inviabilidade comprovada |
| Retomada recusada | Não misture versões de código, bibliotecas, configurações ou sementes na mesma campanha |
| CSV abriu em uma coluna | Importe no Excel usando vírgula como separador e ponto decimal |

Os casos são sintéticos e as metaheurísticas não garantem encontrar a fronteira
ótima. Para a apresentação, o exemplo pequeno permite conferir as respostas
com o exato; os maiores servem para observar a busca e seus limites.

Referências dos motores: [pymoo NSGA-II](https://pymoo.org/algorithms/moo/nsga2.html),
[pymoo PSO](https://pymoo.org/algorithms/soo/pso.html) e
[simanneal](https://github.com/perrygeo/simanneal).
