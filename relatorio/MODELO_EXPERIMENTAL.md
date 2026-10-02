# Modelo experimental consolidado — 1 de outubro de 2026

Este documento define o protocolo atual. O relatório acadêmico e seus PDFs
registram a proposta anterior; quando houver divergência, este protocolo descreve
os experimentos atuais. Não houve conversão do problema para transporte de cargas.

Atualização: o JSON canônico de demanda não contém Q. A campanha em
`experimentos/comparacao_exemplo.json` seleciona Q=1..20 e o leitor recebe o
valor concreto de cada cenário. Para execução isolada, usar `--q` no comparador.
A campanha exploratória já executada usa os três primeiros pedidos do exemplo
sintético, três sementes e os três métodos atuais; resultados e oito figuras
estão em `resultados/comparacao_exemplo/GUIA_RESULTADOS.md`.

A [campanha controlada Q=1..10](CAMPANHA_Q1_10.md) amplia a demanda para
12 pedidos concorrentes, cinco sementes e referência empírica, mantendo m=12.
Ela é definida em `experimentos/comparacao_q1_10.json`. Na revisão, o avaliador
foi corrigido para somar distâncias com `inst.dist`, preservando tempos com
`inst.tempo`. O pequeno exemplo tem mínimos corretos de 24/16/10 km; valores
anteriores de 48/32/20 somavam minutos como quilômetros e foram substituídos.

## Pergunta de pesquisa

Como a capacidade simultânea Q altera o compromisso entre distância da frota
(proporcional às emissões) e tempo perdido pelos passageiros, mantendo as mesmas
solicitações, frota disponível, rede e restrições temporais?

## Escopo e significado de Q

DARP estático de passageiros, com coleta e entrega no mesmo veículo, sem
transferências. Q é capacidade simultânea em passageiros; q_i é a demanda de uma
solicitação. Q não limita o número de pedidos atendidos ao longo do dia.
Q=1 permite várias viagens sequenciais, mas impede compartilhamento se q_i=1.
Um pedido com q_i>Q torna o cenário inviável: pedidos não são fracionados.
Q=1..20 amplia o estudo para transporte sob demanda por carros, vans e micro-ônibus.

Não é necessário mudar de escopo. Em cargas, Q teria unidades de peso, volume ou
paletes e o objetivo de serviço precisaria ser redefinido (atraso de entrega,
tempo de transporte, perecibilidade etc.). Renomear passageiros para produtos
mantendo passageiro-minutos não constitui uma adaptação válida.

Referência sobre capacidade em DARP de passageiros:
[Wong et al., Solution of the Dial-a-Ride Problem with multi-dimensional capacity constraints](https://doi.org/10.1111/j.1475-3995.2006.00544.x).

## Objetivos e hipóteses

- f1 = phi * distância total, incluindo depósito e trajetos vazios.
- f2 = soma q_i * [max(0, R_i - t_direto_i) + max(0, B_i - rho_i)].
- Todas as solicitações devem ser atendidas exatamente uma vez.
- Capacidade, precedência, janelas, duração máxima e limite a bordo são restrições.
- Rede, demanda, tempos de serviço, m e phi ficam fixos ao variar Q.
- phi=1 no estudo principal: f1 é distância, usada como proxy de emissão.

Com objetivos invariantes em Q, o conjunto viável para Q menor está contido no
conjunto viável para Q maior. Portanto, aumentar Q não piora o conjunto de
alternativas ótimas: todo ponto antes viável é igualado ou dominado. Isso não
significa que os pontos individuais das fronteiras sejam os mesmos ou que a
cardinalidade aumente. Resultados heurísticos podem piorar por erro de busca.

Capacidade maior não garante fronteira distinta. As restrições temporais podem
saturar o benefício muito antes de Q=20. Para Q >= soma q_i, a restrição de
capacidade é redundante; fronteiras exatas devem coincidir.

O estudo com phi constante isola o efeito da capacidade. Para comparar tipos
reais de veículo, será preciso fornecer phi(Q), com fonte e unidades, e custos
correspondentes. Nesse segundo estudo, a propriedade de melhoria com Q deixa
de ser garantida, porque o próprio objetivo muda. Não inferir redução real de
CO2 de veículos maiores apenas da redução de distância.

## Famílias de experimentos

1. **Regressão legada:** pr01, pedidos [1,2,3,4,5], m=5, Q original=6,
   limite global do arquivo, phi=1, agendamento OTIMO. Esses cinco pedidos são
   de volta. Mantém o gabarito histórico; não é o cenário principal de aplicativo.
2. **Sensibilidade principal pequena:** pr01, pedidos de ida [13,14,15,16,17],
   m=5, Q=1..20, alpha=2, phi=1, OTIMO. rho é o início da janela de coleta.
   m=n evita confundir inviabilidade por falta de frota com o efeito de Q.
   A viabilidade do cenário Q=1 deve ser verificada, não presumida.
3. **Frota escassa:** repetir os mesmos pedidos com m=3, sem alterar outros
   parâmetros. Registrar cenários inviáveis separadamente; não atribuir HV=0
   como se houvesse uma fronteira viável.
4. **Sensibilidade temporal:** repetir os cenários para alpha=1.5 e 2.0.
5. **Escala maior (próxima etapa):** todas as solicitações de ida nas instâncias
   escolhidas; registrar IDs, m e sementes. SA, GA e GRASP são métodos atuais
   exploratórios. MOILS e epsilon+ILS ainda não estão implementados; o GA tem
   ranking e crowding, mas não deve ser apresentado como NSGA-II canônico.

Pedidos de volta permanecem suportados para regressão. Seu rho é inferido da
janela de entrega e não representa um horário solicitado explicitamente pelo
usuário. Não misturar esse cenário com pedidos de ida sem informar a convenção.

## Agendamento e interpretação do serviço perfeito

OTIMO exige SciPy e resolve o subproblema linear para uma sequência fixa.
Ausência da dependência gera erro explícito. BORDO é heurístico e deve ser
identificado como tal. Para grandes instâncias, pode ser usado na busca, mas
as soluções finais devem ser reavaliadas com OTIMO antes das métricas finais.
Se a PL detecta inviabilidade, a agenda BORDO é usada somente para diagnóstico
das violações, sem certificar uma solução exata viável.

A proposição de que f2=0 impede agrupamento exige hipóteses adicionais:
tempos satisfazem desigualdade triangular e todo atendimento intermediário
introduz tempo estritamente positivo ou desvio estrito. Com paradas coincidentes
e serviços nulos, passageiros podem compartilhar sem tempo excedente. A redação
original do relatório não deve ser generalizada a toda rede fixa sem essas
hipóteses. Distância e tempo calculados em caminhos mínimos diferentes também
devem ser entendidos como matrizes abstratas; para uma rede viária real, validar
se os custos dos arcos representam trajetos fisicamente consistentes.

## Validação e resultados reprodutíveis

- Validar cobertura e precedência após os movimentos. Operadores preservam a
  estrutura, mas não prometem viabilidade de capacidade ou tempo de cada vizinho.
- Testar inserção de pedidos ausentes, construção efetiva, cruzamento com ambos
  os pais e preservação da solução original.
- Enumerar rotas pequenas com OTIMO e conferir todas as soluções pelo avaliador.
- Conferir inclusão entre os conjuntos viáveis dos cenários Q consecutivos.
- Guardar objetivos sem arredondamento, rotas, horários, Q, m, alpha e phi.
- Usar a mesma referência de normalização e HV ao comparar Q; não normalizar
  cada Q separadamente. Na mesma célula (instância, Q, m, alpha), comparar métodos
  com orçamento equivalente e várias sementes.
- Os contadores internos antigos não incluem todas as avaliações. A campanha
  nova conta chamadas de agendamento de rotas não vazias, inclusive na construção
  e no cruzamento, e registra fronteiras intermediárias. Ela mede esforço,
  mas ainda não impõe orçamentos iguais; a comparação definitiva exige essa
  padronização e normalização das buscas ponderadas de SA/GRASP.

Os valores da pr01 completa são referências de rotas publicadas e de atendimento
individual, não prova de extremos globais em uma nova frota ou capacidade. O
atendimento individual round-robin é um construtor, não um otimizador exato.

## Execução no Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install numpy scipy matplotlib
.\.venv\Scripts\python.exe codigo/experimentos/validar_operadores.py
.\.venv\Scripts\python.exe codigo/experimentos/validar_fase1.py
.\.venv\Scripts\python.exe codigo/experimentos/validar_novo_modelo.py
.\.venv\Scripts\python.exe codigo/experimentos/fase2_fronteira.py
.\.venv\Scripts\python.exe codigo/experimentos/capacidade_q.py
.\.venv\Scripts\python.exe codigo/experimentos/capacidade_q.py --m 3 --saida resultados/capacidade_q_m3
.\.venv\Scripts\python.exe codigo/experimentos/capacidade_q.py --alpha 1.5 --saida resultados/capacidade_q_alpha15
.\.venv\Scripts\python.exe codigo/experimentos/resumir_capacidade.py resultados/capacidade_q resultados/capacidade_q_m3
```

O Gurobi é opcional e requer instalação/licença. Quando indisponível, o gabarito
é reproduzido por enumeração com PL; a conferência independente com MIP fica
explicitamente indisponível. O script de Q limita a enumeração a seis pedidos.

As versões efetivamente utilizadas estão em `requirements-validacao.txt`.
Para repetir esse ambiente, usar `pip install -r requirements-validacao.txt`.
