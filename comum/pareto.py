"""Dominancia e fronteira de Pareto para dois objetivos de minimizacao.

Modulo compartilhado pela enumeracao exata, pelas metaheuristicas e pelo
calculo das metricas de qualidade. Um ponto e sempre uma tupla cujos dois
primeiros elementos sao (f_1, f_2); o que vier depois e carga util, tipicamente
a solucao que gerou o ponto, e nao participa da comparacao.
"""

from __future__ import annotations

from typing import Iterable, Sequence

TOL = 1e-9


def domina(a: Sequence[float], b: Sequence[float], tol: float = TOL) -> bool:
    """a domina b: nao e pior em nenhum objetivo e e melhor em ao menos um."""
    return (a[0] <= b[0] + tol and a[1] <= b[1] + tol
            and (a[0] < b[0] - tol or a[1] < b[1] - tol))


def filtrar(pontos: Iterable[tuple], tol: float = TOL) -> list[tuple]:
    """Mantem apenas os pontos nao dominados, ordenados por f_1 crescente.

    Com dois objetivos basta ordenar por (f_1, f_2) e varrer uma vez: um ponto
    entra na fronteira quando seu f_2 e estritamente menor que o melhor f_2 ja
    visto, pois todos os anteriores tem f_1 menor ou igual. Custo O(k log k),
    contra O(k^2) da comparacao par a par.
    """
    ordenados = sorted(pontos, key=lambda p: (p[0], p[1]))
    frente: list[tuple] = []
    melhor_f2 = float("inf")
    for ponto in ordenados:
        if ponto[1] < melhor_f2 - tol:
            frente.append(ponto)
            melhor_f2 = ponto[1]
    return frente


def soma_frentes(a: Iterable[tuple], b: Iterable[tuple],
                 juntar=None, tol: float = TOL) -> list[tuple]:
    """Combina duas fronteiras somando os objetivos par a par.

    Como f_1 e f_2 sao aditivos entre rotas e as restricoes sao internas a cada
    rota, a fronteira de atender dois conjuntos disjuntos de solicitacoes esta
    contida na soma das fronteiras de cada conjunto. O argumento juntar define
    como combinar a carga util dos dois pontos.
    """
    lista_b = list(b)
    combinados = []
    for pa in a:
        for pb in lista_b:
            extra = juntar(pa, pb) if juntar else ()
            combinados.append((pa[0] + pb[0], pa[1] + pb[1]) + extra)
    return filtrar(combinados, tol)


def normalizar(frente: Sequence[tuple], referencia: Sequence[tuple] | None = None
               ) -> list[tuple[float, float]]:
    """Leva os objetivos ao intervalo [0, 1] usando os extremos da referencia.

    Emissao e tempo estao em escalas muito diferentes (gramas e minutos), e sem
    essa normalizacao o hipervolume passa a refletir quase so o objetivo de
    maior magnitude.
    """
    base = list(referencia) if referencia is not None else list(frente)
    if not base:
        return []
    min1 = min(p[0] for p in base)
    max1 = max(p[0] for p in base)
    min2 = min(p[1] for p in base)
    max2 = max(p[1] for p in base)
    amp1 = max1 - min1 or 1.0
    amp2 = max2 - min2 or 1.0
    return [((p[0] - min1) / amp1, (p[1] - min2) / amp2) for p in frente]


def hipervolume(frente: Sequence[tuple], referencia: tuple[float, float] = (1.0, 1.0)
                ) -> float:
    """Area dominada pela fronteira em relacao a um ponto de referencia.

    Espera objetivos ja normalizados. Com dois objetivos o calculo e exato:
    ordena-se por f_1 crescente e somam-se as faixas retangulares entre pontos
    consecutivos.
    """
    pontos = [p for p in filtrar(frente)
              if p[0] < referencia[0] and p[1] < referencia[1]]
    area = 0.0
    f2_anterior = referencia[1]
    for f1, f2, *_ in pontos:
        area += (referencia[0] - f1) * (f2_anterior - f2)
        f2_anterior = f2
    return area


def cobertura(a: Sequence[tuple], b: Sequence[tuple], tol: float = TOL) -> float:
    """Fracao dos pontos de b dominados por algum ponto de a.

    Cobertura de 1 significa que a domina b por completo; de 0, que nenhum
    ponto de b e dominado. A medida nao e simetrica, e as duas direcoes devem
    ser relatadas juntas.
    """
    lista_b = list(b)
    if not lista_b:
        return 0.0
    lista_a = list(a)
    dominados = sum(1 for pb in lista_b if any(domina(pa, pb, tol) for pa in lista_a))
    return dominados / len(lista_b)
