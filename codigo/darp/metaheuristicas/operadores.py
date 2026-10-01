"""Operadores de vizinhanca e heuristicas construtivas para DARP."""

from __future__ import annotations

import random
from typing import Sequence

from ..avaliador import Avaliador
from ..instancia import Instancia
from ..solucao import Rota, Solucao, solucao_individual


def encontrar_rota_de_requisicao(sol: Solucao, inst: Instancia, req_id: int) -> int | None:
    """Encontra o indice da rota que contem a solicitacao req_id."""
    for idx, rota in enumerate(sol.rotas):
        if req_id in rota.sequencia:
            return idx
    return None


def remover_requisicao(rota: Rota, req_id: int, inst: Instancia) -> Rota:
    """Retorna nova rota sem a coleta e entrega da solicitacao req_id."""
    entrega_id = inst.entrega_de(req_id)
    nova_seq = [no for no in rota.sequencia if no != req_id and no != entrega_id]
    return Rota(sequencia=nova_seq)


def inserir_requisicao(
    rota: Rota,
    req_id: int,
    pos_coleta: int,
    pos_entrega: int,
    inst: Instancia,
) -> Rota:
    """Insere a coleta e a entrega de req_id na rota respeitando pos_coleta <= pos_entrega."""
    seq = list(rota.sequencia)
    seq.insert(pos_coleta, req_id)
    seq.insert(pos_entrega + 1, inst.entrega_de(req_id))
    return Rota(sequencia=seq)


def mover_requisicao(
    sol: Solucao,
    inst: Instancia,
    req_id: int,
    rota_destino_idx: int,
    pos_coleta: int,
    pos_entrega: int,
) -> Solucao:
    """Move a requisicao de sua rota atual para outra rota e posicoes especificadas."""
    origem_idx = encontrar_rota_de_requisicao(sol, inst, req_id)
    if origem_idx is None:
        return sol.copiar()

    nova_sol = sol.copiar()
    if origem_idx == rota_destino_idx:
        rota_sem = remover_requisicao(nova_sol.rotas[origem_idx], req_id, inst)
        nova_rota = inserir_requisicao(rota_sem, req_id, pos_coleta, pos_entrega, inst)
        nova_sol.rotas[origem_idx] = nova_rota
    else:
        nova_sol.rotas[origem_idx] = remover_requisicao(nova_sol.rotas[origem_idx], req_id, inst)
        nova_rota = inserir_requisicao(
            nova_sol.rotas[rota_destino_idx], req_id, pos_coleta, pos_entrega, inst
        )
        nova_sol.rotas[rota_destino_idx] = nova_rota

    return nova_sol


def trocar_requisicoes(
    sol: Solucao,
    inst: Instancia,
    req1: int,
    req2: int,
) -> Solucao:
    """Troca as atribuicoes de rotas entre duas requisicoes."""
    r1_idx = encontrar_rota_de_requisicao(sol, inst, req1)
    r2_idx = encontrar_rota_de_requisicao(sol, inst, req2)
    if r1_idx is None or r2_idx is None or r1_idx == r2_idx:
        return sol.copiar()

    # Remove req1 da r1 e req2 da r2
    nova_sol = sol.copiar()
    nova_sol.rotas[r1_idx] = remover_requisicao(nova_sol.rotas[r1_idx], req1, inst)
    nova_sol.rotas[r2_idx] = remover_requisicao(nova_sol.rotas[r2_idx], req2, inst)

    # Reinsere trocado no final de cada rota
    r1_seq = list(nova_sol.rotas[r1_idx].sequencia) + [req2, inst.entrega_de(req2)]
    r2_seq = list(nova_sol.rotas[r2_idx].sequencia) + [req1, inst.entrega_de(req1)]

    nova_sol.rotas[r1_idx] = Rota(r1_seq)
    nova_sol.rotas[r2_idx] = Rota(r2_seq)
    return nova_sol


def reordenar_rota_2opt(
    sol: Solucao,
    inst: Instancia,
    rota_idx: int,
    p1: int,
    p2: int,
) -> Solucao | None:
    """Inverte o segmento p1..p2 de uma rota se a precedencia permanecer valida."""
    seq = list(sol.rotas[rota_idx].sequencia)
    if p1 >= p2 or p2 >= len(seq):
        return None

    # Inversao 2-opt
    seq[p1 : p2 + 1] = reversed(seq[p1 : p2 + 1])

    # Verifica precedencia: coleta antes de entrega
    posicao = {no: p for p, no in enumerate(seq)}
    for no in seq:
        if no <= inst.n:
            par = inst.entrega_de(no)
            if par in posicao and posicao[no] > posicao[par]:
                return None  # Invalido

    nova_sol = sol.copiar()
    nova_sol.rotas[rota_idx] = Rota(seq)
    return nova_sol


def perturbar_solucao(
    sol: Solucao,
    inst: Instancia,
    rng: random.Random,
) -> Solucao:
    """Gera uma solucao vizinha aplicando um movimento aleatorio viavel."""
    if inst.n <= 1:
        return sol.copiar()

    tipo_movimento = rng.choice(["relocate", "relocate_intra", "swap", "2opt"])

    if tipo_movimento == "relocate":
        req = rng.choice(list(inst.coletas))
        r_orig = encontrar_rota_de_requisicao(sol, inst, req)
        if r_orig is None:
            return sol.copiar()
        destinos = [k for k in range(inst.m) if k != r_orig]
        if destinos:
            r_dest = rng.choice(destinos)
            tam = len(sol.rotas[r_dest].sequencia)
            pos_c = rng.randint(0, tam)
            pos_e = rng.randint(pos_c, tam)
            return mover_requisicao(sol, inst, req, r_dest, pos_c, pos_e)

    elif tipo_movimento == "relocate_intra":
        req = rng.choice(list(inst.coletas))
        r_orig = encontrar_rota_de_requisicao(sol, inst, req)
        if r_orig is not None:
            tam = len(sol.rotas[r_orig].sequencia) - 2
            if tam >= 0:
                pos_c = rng.randint(0, tam)
                pos_e = rng.randint(pos_c, tam)
                return mover_requisicao(sol, inst, req, r_orig, pos_c, pos_e)

    elif tipo_movimento == "swap":
        req1, req2 = rng.sample(list(inst.coletas), 2)
        r1 = encontrar_rota_de_requisicao(sol, inst, req1)
        r2 = encontrar_rota_de_requisicao(sol, inst, req2)
        if r1 is not None and r2 is not None and r1 != r2:
            return trocar_requisicoes(sol, inst, req1, req2)

    elif tipo_movimento == "2opt":
        rotas_validas = [k for k, r in enumerate(sol.rotas) if len(r.sequencia) >= 4]
        if rotas_validas:
            r_idx = rng.choice(rotas_validas)
            tam = len(sol.rotas[r_idx].sequencia)
            p1 = rng.randint(0, tam - 2)
            p2 = rng.randint(p1 + 1, tam - 1)
            candidata = reordenar_rota_2opt(sol, inst, r_idx, p1, p2)
            if candidata is not None:
                return candidata

    # Fallback seguro
    req = rng.choice(list(inst.coletas))
    r_dest = rng.randint(0, inst.m - 1)
    tam = len(sol.rotas[r_dest].sequencia)
    return mover_requisicao(sol, inst, req, r_dest, rng.randint(0, tam), rng.randint(0, tam))


def construcao_gulosa_randomizada(
    inst: Instancia,
    av: Avaliador,
    alpha: float = 0.3,
    peso_f1: float = 0.5,
    rng: random.Random | None = None,
) -> Solucao:
    """Constroi solucao via insercao com Lista Restrita de Candidatos (RCL)."""
    if rng is None:
        rng = random.Random()

    rotas = [Rota() for _ in range(inst.m)]
    sol = Solucao(rotas=rotas)

    pendentes = list(inst.coletas)
    # Ordena inicialmente por horario desejado rho
    pendentes.sort(key=lambda i: inst.rho.get(i, 0.0))

    while pendentes:
        candidatos = []

        for req in pendentes:
            for k in range(inst.m):
                tam = len(sol.rotas[k].sequencia)
                # Testa amostras de posicoes de insercao
                for pos_c in range(tam + 1):
                    for pos_e in range(pos_c, tam + 1):
                        sol_teste = mover_requisicao(sol, inst, req, k, pos_c, pos_e)
                        # Avalia rota k modificada
                        ag, viol = av.avaliar_rota(sol_teste.rotas[k])
                        if not viol:
                            desvio, espera, _ = av.contribuicao(ag)
                            custo = peso_f1 * ag.distancia + (1.0 - peso_f1) * (desvio + espera)
                            candidatos.append((custo, req, k, pos_c, pos_e, sol_teste))

        if not candidatos:
            # Se restricoes impedem insercao estrita, recorre a solucao_individual
            return solucao_individual(inst)

        candidatos.sort(key=lambda c: c[0])
        c_min = candidatos[0][0]
        c_max = candidatos[-1][0]
        limite = c_min + alpha * (c_max - c_min)

        rcl = [c for c in candidatos if c[0] <= limite]
        escolhido = rng.choice(rcl)

        sol = escolhido[5]
        pendentes.remove(escolhido[1])

    # Validacao final de estrutura
    if sol.conferir_estrutura(inst):
        return solucao_individual(inst)

    return sol
