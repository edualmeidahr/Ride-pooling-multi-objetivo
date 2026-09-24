"""Representacao de uma solucao do DARP.

Uma solucao e um conjunto de rotas. Cada rota guarda apenas a sequencia de nos
de atendimento; os depositos de saida e de retorno ficam implicitos e sao
acrescentados pelo agendador. Rotas vazias sao permitidas e representam
veiculos nao utilizados (y_k = 0).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .instancia import Instancia


@dataclass
class Rota:
    sequencia: list[int] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.sequencia)

    @property
    def usada(self) -> bool:
        return len(self.sequencia) > 0

    def copiar(self) -> "Rota":
        return Rota(sequencia=list(self.sequencia))


@dataclass
class Solucao:
    rotas: list[Rota] = field(default_factory=list)
    partidas: dict[int, float] | None = None
    """Instante de saida do deposito por rota.

    Quando None, o agendador escolhe a saida. Usado para reproduzir solucoes
    publicadas, que fixam esse instante.
    """

    @property
    def veiculos_usados(self) -> int:
        return sum(1 for r in self.rotas if r.usada)

    def copiar(self) -> "Solucao":
        return Solucao(
            rotas=[r.copiar() for r in self.rotas],
            partidas=dict(self.partidas) if self.partidas else None,
        )

    def nos_visitados(self) -> list[int]:
        return [no for rota in self.rotas for no in rota.sequencia]

    def conferir_estrutura(self, inst: Instancia) -> list[str]:
        """Verifica o que nao depende de tempo: cobertura, pareamento, precedencia.

        Separado da avaliacao porque um erro aqui indica defeito no operador que
        gerou a solucao, e nao uma solucao apenas inviavel.
        """
        erros: list[str] = []

        visitados = self.nos_visitados()
        if len(visitados) != len(set(visitados)):
            repetidos = sorted({x for x in visitados if visitados.count(x) > 1})
            erros.append(f"nos visitados mais de uma vez: {repetidos}")

        faltando = set(inst.atendimento) - set(visitados)
        if faltando:
            erros.append(f"nos nao atendidos: {sorted(faltando)}")

        sobrando = set(visitados) - set(inst.atendimento)
        if sobrando:
            erros.append(f"nos fora do conjunto de atendimento: {sorted(sobrando)}")

        if len(self.rotas) > inst.m:
            erros.append(f"{len(self.rotas)} rotas para m={inst.m} veiculos")

        for k, rota in enumerate(self.rotas):
            posicao = {no: p for p, no in enumerate(rota.sequencia)}
            for no in rota.sequencia:
                i = inst.solicitacao_de(no)
                par = inst.entrega_de(i) if no <= inst.n else i
                if par not in posicao:
                    erros.append(
                        f"rota {k}: no {no} sem o par {par} no mesmo veiculo")
                elif no <= inst.n and posicao[no] > posicao[par]:
                    erros.append(
                        f"rota {k}: entrega {par} antes da coleta {no}")

        return erros


def solucao_individual(inst: Instancia) -> Solucao:
    """Atendimento sem agrupamento: uma solicitacao por viagem, em blocos.

    Serve de ponto de partida e corresponde ao extremo f_2 minimo descrito na
    Proposicao do relatorio, no qual nenhum no e visitado entre a coleta e a
    entrega da mesma solicitacao.
    """
    rotas = [Rota() for _ in range(inst.m)]
    ordem = sorted(inst.coletas, key=lambda i: inst.rho[i])
    for posicao, i in enumerate(ordem):
        rotas[posicao % inst.m].sequencia.extend([i, inst.entrega_de(i)])
    return Solucao(rotas=rotas)
