# Entrada didática: dois passageiros

[exemplo_pequeno.json](exemplo_pequeno.json) é um arquivo completo aceito pelo leitor.
Descreve a demanda e a rede; não contém rotas prontas nem define Q.

Garagem → Bairro A → Bairro B → Campus. As conexões são bidirecionais:

| Conexão | Distância | Tempo |
|---|---:|---:|
| Garagem — A | 1 km | 2 min |
| A — B | 2 km | 4 min |
| B — Campus | 20 km | 40 min |

O pedido 101 leva uma pessoa de A ao Campus, com coleta entre os minutos 30 e 35.
O pedido 102 leva uma pessoa de B ao Campus, com coleta entre 31 e 36.
Esses tempos são relativos ao início do cenário, não horários do relógio.
As entregas têm janela livre [0,1440], mas a garagem fecha no minuto 240.

- `m=2`: dois veículos disponíveis em todas as capacidades.
- `q=1` em cada pedido: uma pessoa naquele pedido; não é a capacidade do veículo.
- `capacidades=[1,2]` no [experimento](../experimentos/exemplo_pequeno.json): Q muda entre execuções.
- `T_max=180`: duração máxima de cada rota, em minutos.
- `alpha=2`: tempo a bordo limitado a duas vezes o tempo de viagem direta.
- `phi=1`: o primeiro objetivo é numericamente a distância em km, sem CO2 calibrado.
- `s_embarque/s_desembarque=0.5`: cada atendimento leva meio minuto.
- `direcionado=false`: cada conexão pode ser percorrida nos dois sentidos.

O leitor calcula os caminhos na rede. Não precisamos fornecer uma aresta
Garagem–Campus: ela é alcançada passando por A e B. Os algoritmos recebem
coletas internas 1 e 2 e entregas internas 3 e 4; os IDs externos 101/102
identificam os pedidos na entrada, e os IDs 0–3 identificam as paradas físicas.

Em Q=1, os dois veículos atendem separadamente. Em Q=2, um veículo pode coletar
as duas pessoas antes de chegar ao Campus, reduzindo a distância com tempo perdido
adicional. Retorno à garagem entra na distância. Veículos disponíveis podem ficar vazios.

Para reproduzir as seis execuções (três métodos × duas capacidades × uma semente):

```powershell
.\.venv\Scripts\python.exe codigo/experimentos/executar_campanha.py --config experimentos/exemplo_pequeno.json
```

Este caso usa referência exata por ser pequeno. As saídas estão em
[resultados/exemplo_pequeno](../resultados/exemplo_pequeno/RESUMO_SOLUCOES.md).
