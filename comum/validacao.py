"""Auditoria independente de rotas e horarios (sem solver ou agendador).

Nao chama Avaliador, conferir_estrutura ou os campos derivados da agenda.
Recalcula objetivos e restricoes usando distancias, tempos e custos ambientais
da instancia. Compatibilidade com a rede explicita da branch abordagem_grafos.
A auditoria compartilha os dados de caminhos, mas nao a logica do avaliador.
"""
from __future__ import annotations

from math import isfinite

from comum.avaliador import AgendaRota, Avaliacao, Parametros
from comum.instancia import Instancia
from comum.solucao import Solucao


def verificar_solucao(inst: Instancia, sol: Solucao, agendas: list[AgendaRota],
                      par: Parametros | None = None) -> Avaliacao:
    par = par or Parametros()
    res = Avaliacao()
    erros, tol = res.violacoes, par.tolerancia
    if sol.Q is not None and (type(sol.Q) is not int or sol.Q != inst.Q):
        erros.append("Q da solucao diverge do contexto")
    seqs = [r.sequencia for r in sol.rotas if r.sequencia]
    nos = [no for seq in seqs for no in seq]
    if len(sol.rotas) > inst.m:
        erros.append("frota excedida")
    if len(nos) != len(set(nos)) or set(nos) != set(range(1, 2 * inst.n + 1)):
        erros.append("cobertura invalida")
    if len(agendas) != len(seqs):
        erros.append("numero de agendas incorreto")
    if erros:
        return res


    for k, (seq, ag) in enumerate(zip(seqs, agendas)):
        prefixo = f"rota {k}: "
        pos = {no: p for p, no in enumerate(seq)}
        if ag.sequencia != seq:
            erros.append(prefixo + "sequencia da agenda divergente")
        for no in seq:
            i = no if no <= inst.n else no - inst.n
            if i not in pos or i + inst.n not in pos or pos[i] >= pos[i + inst.n]:
                erros.append(prefixo + "pareamento ou precedencia")
        if any(no not in ag.B for no in seq):
            erros.append(prefixo + "agenda incompleta")
            continue
        if not all(isfinite(t) for t in [ag.partida, ag.retorno, *[ag.B[n] for n in seq]]):
            erros.append(prefixo + "horario nao finito")
            continue
        dep, fim = inst.nos[0], inst.nos[2 * inst.n + 1]
        if not dep.e - tol <= ag.partida <= dep.l + tol:
            erros.append(prefixo + "janela do deposito de saida")
        if not fim.e - tol <= ag.retorno <= fim.l + tol:
            erros.append(prefixo + "janela do deposito de retorno")
        if ag.retorno - ag.partida > inst.T_max + tol:
            erros.append(prefixo + "duracao")
        anterior, instante, carga, dist = 0, ag.partida, 0, 0.0
        for no in seq:
            dados = inst.nos[no]
            trecho = inst.tempo(anterior, no)
            dist += inst.dist(anterior, no)
            if ag.B[no] < instante + trecho - tol:
                erros.append(prefixo + "encadeamento temporal")
            if not dados.e - tol <= ag.B[no] <= dados.l + tol:
                erros.append(prefixo + "janela de atendimento")
            carga += dados.q
            if carga < -tol or carga > inst.Q + tol:
                erros.append(prefixo + "capacidade")
            instante, anterior = ag.B[no] + dados.s, no
        dist += inst.dist(anterior, fim.id)
        if ag.retorno < instante + inst.tempo(anterior, fim.id) - tol:
            erros.append(prefixo + "retorno impossivel")
        if abs(carga) > tol:
            erros.append(prefixo + "carga final")
        for i in seq:
            if i > inst.n or i + inst.n not in pos:
                continue
            direto = inst.tempo(i, i + inst.n)
            bordo = ag.B[i + inst.n] - ag.B[i] - inst.nos[i].s
            limite = inst.L_arquivo if par.alpha is None else par.alpha * direto
            if bordo < direto - tol or bordo > limite + tol:
                erros.append(prefixo + "tempo a bordo")
            # Independente da classificacao armazenada no objeto Instancia.
            coleta, entrega = inst.nos[i], inst.nos[i + inst.n]
            coleta_livre = coleta.e <= 0 and coleta.l >= 1440
            entrega_livre = entrega.e <= 0 and entrega.l >= 1440
            rho = (entrega.e - coleta.s - direto
                   if coleta_livre and not entrega_livre else coleta.e)
            res.f2_desvio += coleta.q * max(0.0, bordo - direto)
            res.f2_espera += coleta.q * max(0.0, ag.B[i] - rho)
            res.tempo_bordo += bordo
        caminho = [inst.deposito_ini, *seq, inst.deposito_fim]
        res.f1 += par.phi * sum(inst.dist_ambiental(a, b) for a, b in zip(caminho, caminho[1:]))
        res.distancia += dist
        res.veiculos_usados += 1
        res.custo += par.custo_fixo + par.custo_distancia * dist + par.custo_hora * (ag.retorno - ag.partida)
    res.f2 = res.f2_desvio + res.f2_espera
    return res
