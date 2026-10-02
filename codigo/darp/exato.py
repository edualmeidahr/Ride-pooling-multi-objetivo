"""Fronteira de Pareto exata por enumeracao, para instancias pequenas.

O gabarito contra o qual as metaheuristicas serao medidas. A enumeracao explora
uma propriedade da formulacao: os dois objetivos sao somas de contribuicoes por
rota e todas as restricoes (janela, capacidade, tempo a bordo, duracao) sao
internas a uma rota. Logo o problema se decompoe em duas etapas.

1. Para cada subconjunto de solicitacoes, enumerar todas as sequencias que um
   unico veiculo pode cumprir e guardar apenas as nao dominadas. E o passo caro,
   e onde as podas atuam.

2. Combinar os subconjuntos por particao, somando objetivos e filtrando os
   dominados a cada juncao. Feito por programacao dinamica sobre subconjuntos,
   fixando sempre a menor solicitacao pendente para nao gerar a mesma particao
   em ordens diferentes.

Com OTIMO, a enumeracao e exata tambem nos horarios (PL por rota). Com BORDO
ou CEDO, a exatidao vale apenas dentro da politica heuristica escolhida.
"""

from __future__ import annotations

from itertools import combinations

from . import pareto
from .avaliador import Avaliador
from .instancia import Instancia
from .solucao import Rota, Solucao


def sequencias_viaveis(inst: Instancia, pedidos: tuple[int, ...],
                       tol: float = 1e-6) -> list[list[int]]:
    """Todas as ordens de visita que um veiculo pode usar para atender pedidos.

    A construcao e recursiva: em cada passo o veiculo pode embarcar alguem ainda
    nao coletado ou desembarcar alguem a bordo, o que garante por construcao o
    pareamento e a precedencia.

    Duas podas. A de capacidade e exata. A de janela usa a chegada mais cedo
    possivel, saindo do deposito no instante mais cedo: se nem assim o no e
    alcancado dentro da janela, nenhuma agenda resolve, porque atrasar so
    aumenta o instante de atendimento. O tempo a bordo nao permite poda parcial
    (atrasar o embarque pode reduzi-lo) e e conferido no fim.
    """
    resultado: list[list[int]] = []
    partida = inst.nos[inst.deposito_ini].e

    def passo(seq: list[int], nao_coletados: frozenset[int],
              a_bordo: frozenset[int], carga: int, instante: float, ultimo: int) -> None:
        if not nao_coletados and not a_bordo:
            resultado.append(list(seq))
            return

        candidatos = [i for i in nao_coletados if carga + inst.nos[i].q <= inst.Q]
        candidatos += [inst.entrega_de(i) for i in a_bordo]

        for no in candidatos:
            chegada = instante + inst.tempo(ultimo, no)
            inicio = max(chegada, inst.nos[no].e)
            if inicio > inst.nos[no].l + tol:
                continue

            dados = inst.nos[no]
            if no <= inst.n:
                passo(seq + [no], nao_coletados - {no}, a_bordo | {no},
                      carga + dados.q, inicio + dados.s, no)
            else:
                i = inst.coleta_de(no)
                passo(seq + [no], nao_coletados, a_bordo - {i},
                      carga + dados.q, inicio + dados.s, no)

    passo([], frozenset(pedidos), frozenset(), 0, partida, inst.deposito_ini)
    return resultado


def frentes_por_subconjunto(inst: Instancia, av: Avaliador,
                            politica: str | None = None) -> dict[int, list[tuple]]:
    """Fronteira de uma rota para cada subconjunto de solicitacoes.

    As chaves sao mascaras de bits: o bit i-1 ligado significa que a solicitacao
    i pertence ao subconjunto. Subconjuntos sem nenhuma rota viavel ficam de
    fora do dicionario.
    """
    frentes: dict[int, list[tuple]] = {}

    for tamanho in range(1, inst.n + 1):
        for pedidos in combinations(inst.coletas, tamanho):
            pontos = []
            for seq in sequencias_viaveis(inst, pedidos):
                ag, violacoes = av.avaliar_rota(Rota(list(seq)), politica=politica)
                if violacoes:
                    continue
                desvio, espera, _ = av.contribuicao(ag)
                pontos.append((av.par.phi * ag.distancia, desvio + espera, tuple(seq)))
            if pontos:
                frentes[_mascara(pedidos)] = pareto.filtrar(pontos)

    return frentes


def fronteira_exata(inst: Instancia, av: Avaliador, politica: str | None = None
                    ) -> list[tuple[float, float, Solucao]]:
    """Fronteira exata da instancia, dentro da politica de agendamento dada."""
    frentes = frentes_por_subconjunto(inst, av, politica)
    completo = _mascara(inst.coletas)
    memo: dict[tuple[int, int], list[tuple]] = {}

    def resolver(pendentes: int, veiculos: int) -> list[tuple]:
        if pendentes == 0:
            return [(0.0, 0.0, ())]
        if veiculos == 0:
            return []
        chave = (pendentes, veiculos)
        if chave in memo:
            return memo[chave]

        # Fixar a menor solicitacao pendente evita gerar a mesma particao em
        # ordens diferentes: ela pertence obrigatoriamente a primeira rota.
        menor = pendentes & -pendentes
        resto = pendentes ^ menor

        candidatos: list[tuple] = []
        for extra in _subconjuntos(resto):
            grupo = menor | extra
            frente_grupo = frentes.get(grupo)
            if not frente_grupo:
                continue
            frente_resto = resolver(pendentes ^ grupo, veiculos - 1)
            if not frente_resto:
                continue
            # A carga util de cada ponto e a tupla das rotas que o compoem; o
            # parenteses externo a mantem como um unico elemento da tupla.
            candidatos.extend(
                pareto.soma_frentes(frente_grupo, frente_resto,
                                    juntar=lambda a, b: ((a[2],) + b[2],))
            )

        memo[chave] = pareto.filtrar(candidatos)
        return memo[chave]

    frente = resolver(completo, inst.m)
    return [(f1, f2, Solucao(rotas=[Rota(list(s)) for s in rotas]))
            for f1, f2, rotas in frente]


def _mascara(pedidos) -> int:
    valor = 0
    for i in pedidos:
        valor |= 1 << (i - 1)
    return valor


def _subconjuntos(mascara: int):
    """Todos os subconjuntos de uma mascara, incluindo o vazio."""
    atual = mascara
    while True:
        yield atual
        if atual == 0:
            break
        atual = (atual - 1) & mascara
