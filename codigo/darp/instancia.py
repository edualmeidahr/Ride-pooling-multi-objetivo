"""Leitura das instancias DARP de Cordeau & Laporte.

As duas colecoes usadas no projeto gravam o mesmo problema em convencoes
diferentes, e o leitor normaliza ambas para uma unica representacao interna:

    colecao "bnc"   cabecalho "m n T Q L",   nos 0..2n+1 (deposito duplicado)
    colecao "tabu"  cabecalho "m 2n T Q L",  nos 0..2n   (deposito unico)

Internamente o deposito final e sempre o no 2n+1, criado por copia do no 0
quando o arquivo nao o traz.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

# Janela [0, 1440] e o valor que os arquivos usam para "sem restricao".
JANELA_LIVRE = 1440.0

# Classificacao de cada solicitacao conforme onde esta a janela apertada.
IDA = "ida"        # janela na coleta: o usuario marca a hora de embarque
VOLTA = "volta"    # janela na entrega: o usuario marca a hora de chegada
LIVRE = "livre"    # nenhuma das duas pontas tem janela apertada


@dataclass(frozen=True)
class No:
    """Um no do grafo: deposito, ponto de coleta ou ponto de entrega."""

    id: int
    x: float
    y: float
    s: float    # tempo de servico (embarque/desembarque)
    q: int      # passageiros; positivo na coleta, negativo na entrega
    e: float    # inicio da janela de tempo
    l: float    # fim da janela de tempo

    @property
    def janela_apertada(self) -> bool:
        return not (self.e <= 0.0 and self.l >= JANELA_LIVRE)


@dataclass
class Instancia:
    nome: str
    m: int                  # veiculos disponiveis
    n: int                  # solicitacoes
    T_max: float            # duracao maxima de rota
    Q: int                  # capacidade do veiculo
    L_arquivo: float        # tempo maximo a bordo declarado no cabecalho
    nos: list[No]           # indexado pelo id; comprimento 2n+2
    formato: str

    # Derivados no __post_init__.
    tipo: dict[int, str] = field(default_factory=dict, repr=False)
    rho: dict[int, float] = field(default_factory=dict, repr=False)

    # ----- indices -----

    @property
    def coletas(self) -> range:
        return range(1, self.n + 1)

    @property
    def entregas(self) -> range:
        return range(self.n + 1, 2 * self.n + 1)

    @property
    def atendimento(self) -> range:
        return range(1, 2 * self.n + 1)

    @property
    def deposito_ini(self) -> int:
        return 0

    @property
    def deposito_fim(self) -> int:
        return 2 * self.n + 1

    def entrega_de(self, i: int) -> int:
        return i + self.n

    def coleta_de(self, j: int) -> int:
        return j - self.n

    def solicitacao_de(self, no: int) -> int:
        """Solicitacao a que um no de atendimento pertence."""
        return no if no <= self.n else no - self.n

    # ----- geometria e tempo -----

    def dist(self, i: int, j: int) -> float:
        a, b = self.nos[i], self.nos[j]
        return math.hypot(a.x - b.x, a.y - b.y)

    def tempo(self, i: int, j: int) -> float:
        """Velocidade unitaria: tempo de percurso igual a distancia.

        Convencao das instancias de Cordeau & Laporte.
        """
        return self.dist(i, j)

    def t_direto(self, i: int) -> float:
        """Tempo do percurso direto da solicitacao i (t_barra_i)."""
        return self.tempo(i, self.entrega_de(i))

    def limite_bordo(self, i: int, alpha: float | None = None) -> float:
        """Tempo maximo tolerado a bordo (L_i).

        Com alpha=None usa o limite global do arquivo. Com alpha informado usa
        L_i = alpha * t_direto_i, a definicao proporcional adotada no relatorio.
        """
        if alpha is None:
            return self.L_arquivo
        return alpha * self.t_direto(i)

    # ----- derivados -----

    def __post_init__(self) -> None:
        esperado = 2 * self.n + 2
        if len(self.nos) != esperado:
            raise ValueError(f"esperados {esperado} nos, recebidos {len(self.nos)}")
        self._classificar_solicitacoes()

    def _classificar_solicitacoes(self) -> None:
        """Define o tipo de cada solicitacao e o horario desejado de embarque.

        O arquivo nao traz rho_i explicitamente, entao ele e inferido da ponta
        que tem janela apertada:

            ida    rho_i = e_i, a hora de embarque pedida esta no proprio no
            volta  rho_i = e_{n+i} - s_i - t_direto_i, isto e, a hora de sair
                   para chegar no inicio da janela de entrega pelo caminho direto
            livre  rho_i = e_i, caso degenerado sem hora pedida
        """
        for i in self.coletas:
            coleta, entrega = self.nos[i], self.nos[self.entrega_de(i)]
            if coleta.janela_apertada:
                self.tipo[i] = IDA
                self.rho[i] = coleta.e
            elif entrega.janela_apertada:
                self.tipo[i] = VOLTA
                self.rho[i] = entrega.e - coleta.s - self.t_direto(i)
            else:
                self.tipo[i] = LIVRE
                self.rho[i] = coleta.e

    def resumo(self) -> str:
        contagem = {t: sum(1 for i in self.coletas if self.tipo[i] == t)
                    for t in (IDA, VOLTA, LIVRE)}
        return (f"{self.nome}: m={self.m} n={self.n} Q={self.Q} "
                f"T_max={self.T_max:.0f} L={self.L_arquivo:.0f} "
                f"formato={self.formato} "
                f"ida={contagem[IDA]} volta={contagem[VOLTA]} livre={contagem[LIVRE]}")


def ler_instancia(caminho: str | Path) -> Instancia:
    caminho = Path(caminho)
    linhas = [l for l in caminho.read_text().splitlines() if l.strip()]

    cabecalho = [float(v) for v in linhas[0].split()]
    if len(cabecalho) < 5:
        raise ValueError(f"cabecalho com {len(cabecalho)} campos, esperados 5")
    m, campo2, T_max, Q, L = cabecalho[:5]

    brutos = [[float(v) for v in l.split()] for l in linhas[1:]]

    # A quantidade de linhas de no desambigua o significado do segundo campo.
    if len(brutos) == 2 * campo2 + 2:
        n, formato = int(campo2), "2n+2"
    elif len(brutos) == campo2 + 1:
        n, formato = int(campo2) // 2, "2n+1"
    else:
        raise ValueError(
            f"{caminho.name}: {len(brutos)} linhas de no nao correspondem a "
            f"2n+2 nem a 2n+1 com o campo 2 igual a {campo2:.0f}"
        )

    nos = [No(id=int(b[0]), x=b[1], y=b[2], s=b[3], q=int(b[4]), e=b[5], l=b[6])
           for b in brutos]

    # Normaliza para que o deposito final seja sempre o no 2n+1.
    if formato == "2n+1":
        origem = nos[0]
        nos.append(No(id=2 * n + 1, x=origem.x, y=origem.y, s=0.0, q=0,
                      e=origem.e, l=origem.l))

    for esperado, no in enumerate(nos):
        if no.id != esperado:
            raise ValueError(f"{caminho.name}: no {esperado} tem id {no.id}")

    return Instancia(nome=caminho.name, m=int(m), n=n, T_max=T_max, Q=int(Q),
                     L_arquivo=L, nos=nos, formato=formato)


def reduzir(inst: Instancia, pedidos: list[int], m: int | None = None) -> Instancia:
    """Recorta uma instancia menor mantendo apenas as solicitacoes escolhidas.

    Os nos sao renumerados para continuar obedecendo a convencao de que a
    entrega da solicitacao i e o no i + n. Serve para produzir instancias de 5 a
    8 solicitacoes, nas quais a fronteira exata pode ser obtida por enumeracao
    ou por solver e usada como gabarito das metaheuristicas.
    """
    pedidos = sorted(pedidos)
    k = len(pedidos)
    if not pedidos or pedidos[0] < 1 or pedidos[-1] > inst.n:
        raise ValueError(f"solicitacoes fora de 1..{inst.n}: {pedidos}")

    nos = [No(id=0, x=inst.nos[0].x, y=inst.nos[0].y, s=inst.nos[0].s,
              q=0, e=inst.nos[0].e, l=inst.nos[0].l)]
    for novo, antigo in enumerate(pedidos, start=1):
        fonte = inst.nos[antigo]
        nos.append(No(id=novo, x=fonte.x, y=fonte.y, s=fonte.s, q=fonte.q,
                      e=fonte.e, l=fonte.l))
    for novo, antigo in enumerate(pedidos, start=1):
        fonte = inst.nos[inst.entrega_de(antigo)]
        nos.append(No(id=k + novo, x=fonte.x, y=fonte.y, s=fonte.s, q=fonte.q,
                      e=fonte.e, l=fonte.l))
    fim = inst.nos[inst.deposito_fim]
    nos.append(No(id=2 * k + 1, x=fim.x, y=fim.y, s=0.0, q=0, e=fim.e, l=fim.l))

    return Instancia(nome=f"{inst.nome}-r{k}", m=m if m is not None else inst.m,
                     n=k, T_max=inst.T_max, Q=inst.Q, L_arquivo=inst.L_arquivo,
                     nos=nos, formato=inst.formato)
