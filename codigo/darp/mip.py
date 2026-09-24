"""Modelo de programacao inteira mista e metodo epsilon-restrito.

Transcreve a formulacao da Secao 3.2 do relatorio para o Gurobi. Tem duas
finalidades distintas da enumeracao do modulo exato.

Validacao da formulacao. As restricoes aqui sao escritas direto do texto do
relatorio, sem passar pelo avaliador. Se as duas fronteiras coincidirem, o
modelo escrito e o modelo implementado sao o mesmo, o que e a conferencia que
realmente interessa antes de investir nas metaheuristicas.

Medida da perda do agendamento. O solver escolhe livremente os instantes de
atendimento, enquanto o avaliador os fixa por uma politica heuristica. A
diferenca entre as duas fronteiras quantifica o quanto a politica deixa na mesa.

A fronteira e percorrida pelo metodo epsilon-restrito: minimiza-se f_1 sujeito a
f_2 <= epsilon e, a cada solucao encontrada, aperta-se epsilon um pouco abaixo
do f_2 obtido, ate o problema ficar inviavel. O objetivo leva uma parcela
minuscula de f_2 (forma aumentada) para descartar solucoes fracamente
dominadas, nas quais f_1 e otimo mas f_2 poderia melhorar sem custo.
"""

from __future__ import annotations

from dataclasses import dataclass

from .avaliador import Avaliador, Parametros
from .instancia import Instancia
from .solucao import Rota, Solucao


class SolverIndisponivel(RuntimeError):
    """Gurobi ausente, sem licenca ou com modelo acima do limite da licenca."""


@dataclass
class ResultadoMip:
    f1: float
    f2: float
    solucao: Solucao
    tempo: float
    B: dict[int, float]
    """Instantes de atendimento escolhidos pelo solver.

    Permitem reavaliar a solucao com Avaliador.avaliar_com_B e conferir se as
    duas implementacoes concordam sobre o mesmo ponto.
    """
    partidas: dict[int, float]


def _importar():
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except ImportError as erro:
        raise SolverIndisponivel(f"gurobipy nao disponivel: {erro}") from erro
    return gp, GRB


def construir(inst: Instancia, par: Parametros, silencioso: bool = True):
    """Monta o modelo e devolve (modelo, expressao de f_1, expressao de f_2)."""
    gp, GRB = _importar()

    n = inst.n
    ini, fim = inst.deposito_ini, inst.deposito_fim
    N = list(inst.atendimento)
    P = list(inst.coletas)
    D = list(inst.entregas)
    V = N + [ini, fim]
    K = range(inst.m)

    # Arcos uteis: nao se entra no deposito de saida nem se sai do de retorno,
    # a saida do deposito vai para uma coleta e a chegada vem de uma entrega.
    arcos = [(i, j) for i in V for j in V
             if i != j and j != ini and i != fim
             and not (i == ini and j in D) and not (j == fim and i in P)]

    def M(i: int, j: int) -> float:
        return max(0.0, inst.nos[i].l + inst.nos[i].s + inst.tempo(i, j) - inst.nos[j].e)

    mod = gp.Model("darp-biobjetivo")
    if silencioso:
        mod.Params.OutputFlag = 0

    x = mod.addVars(arcos, K, vtype=GRB.BINARY, name="x")
    y = mod.addVars(K, vtype=GRB.BINARY, name="y")
    B = mod.addVars(N, lb={i: inst.nos[i].e for i in N},
                    ub={i: inst.nos[i].l for i in N}, name="B")
    Bini = mod.addVars(K, lb=inst.nos[ini].e, ub=inst.nos[ini].l, name="Bini")
    Bfim = mod.addVars(K, lb=inst.nos[fim].e, ub=inst.nos[fim].l, name="Bfim")
    w = mod.addVars(N, lb={i: max(0, inst.nos[i].q) for i in N},
                    ub={i: min(inst.Q, inst.Q + inst.nos[i].q) for i in N}, name="w")
    R = mod.addVars(P, lb={i: inst.t_direto(i) for i in P},
                    ub={i: inst.limite_bordo(i, par.alpha) for i in P}, name="R")
    esp = mod.addVars(P, lb=0.0, name="esp")

    def saindo(i, k):
        return gp.quicksum(x[i, j, k] for (a, j) in arcos if a == i)

    def entrando(j, k):
        return gp.quicksum(x[i, j, k] for (i, b) in arcos if b == j)

    def usado(i, j):
        return gp.quicksum(x[i, j, k] for k in K) if (i, j) in arcos else 0

    # Atendimento unico de cada solicitacao.
    mod.addConstrs((gp.quicksum(saindo(i, k) for k in K) == 1 for i in P), "atende")

    # Coleta e entrega no mesmo veiculo.
    mod.addConstrs((saindo(i, k) - saindo(inst.entrega_de(i), k) == 0
                    for i in P for k in K), "par")

    # Conservacao de fluxo nos nos de atendimento.
    mod.addConstrs((entrando(h, k) - saindo(h, k) == 0 for h in N for k in K), "fluxo")

    # Saida e retorno ao deposito condicionados ao uso do veiculo.
    mod.addConstrs((gp.quicksum(x[ini, j, k] for j in P) == y[k] for k in K), "saida")
    mod.addConstrs((gp.quicksum(x[i, fim, k] for i in D) == y[k] for k in K), "retorno")

    # Consistencia temporal ao longo da rota.
    mod.addConstrs((B[j] >= B[i] + inst.nos[i].s + inst.tempo(i, j)
                    - M(i, j) * (1 - usado(i, j))
                    for (i, j) in arcos if i in N and j in N), "tempo")
    mod.addConstrs((B[j] >= Bini[k] + inst.tempo(ini, j) - M(ini, j) * (1 - x[ini, j, k])
                    for j in P for k in K), "tempo_saida")
    mod.addConstrs((Bfim[k] >= B[i] + inst.nos[i].s + inst.tempo(i, fim)
                    - M(i, fim) * (1 - x[i, fim, k])
                    for i in D for k in K), "tempo_retorno")

    # Tempo a bordo (a precedencia decorre do limite inferior t_direto de R).
    mod.addConstrs((R[i] == B[inst.entrega_de(i)] - (B[i] + inst.nos[i].s)
                    for i in P), "bordo")

    # Capacidade.
    mod.addConstrs((w[j] >= w[i] + inst.nos[j].q - inst.Q * (1 - usado(i, j))
                    for (i, j) in arcos if i in N and j in N), "carga")
    mod.addConstrs((w[j] <= inst.nos[j].q
                    + inst.Q * (1 - gp.quicksum(x[ini, j, k] for k in K))
                    for j in P), "carga_inicial")

    # Duracao maxima da rota.
    mod.addConstrs((Bfim[k] - Bini[k] <= inst.T_max for k in K), "duracao")

    # Espera no embarque, parcela de f_2.
    mod.addConstrs((esp[i] >= B[i] - inst.rho[i] for i in P), "espera")

    f1 = par.phi * gp.quicksum(inst.dist(i, j) * x[i, j, k] for (i, j) in arcos for k in K)
    f2 = gp.quicksum(inst.nos[i].q * ((R[i] - inst.t_direto(i)) + esp[i]) for i in P)

    mod._vars = dict(x=x, y=y, B=B, Bini=Bini, Bfim=Bfim, w=w, R=R, esp=esp,
                     arcos=arcos, K=K)
    return mod, f1, f2


def _extrair(mod, inst: Instancia) -> tuple[Solucao, dict[int, float], dict[int, float]]:
    x, Bini = mod._vars["x"], mod._vars["Bini"]
    rotas, partidas = [], {}
    for k in mod._vars["K"]:
        sucessor = {i: j for (i, j) in mod._vars["arcos"] if x[i, j, k].X > 0.5}
        if inst.deposito_ini not in sucessor:
            continue
        seq = []
        atual = sucessor[inst.deposito_ini]
        while atual != inst.deposito_fim:
            seq.append(atual)
            atual = sucessor[atual]
        partidas[len(rotas)] = Bini[k].X
        rotas.append(Rota(seq))

    B = {i: mod._vars["B"][i].X for i in inst.atendimento}
    sol = Solucao(rotas=rotas, partidas=dict(partidas))
    return sol, B, partidas


def fronteira_epsilon(inst: Instancia, par: Parametros | None = None,
                      max_pontos: int = 40, passo: float = 1e-4,
                      limite_tempo: float = 60.0, peso: float = 1e-4
                      ) -> list[ResultadoMip]:
    """Percorre a fronteira exata pelo metodo epsilon-restrito."""
    gp, GRB = _importar()
    par = par or Parametros()

    mod, f1, f2 = construir(inst, par)
    mod.Params.TimeLimit = limite_tempo
    limite = mod.addConstr(f2 <= GRB.INFINITY, name="epsilon")
    mod.setObjective(f1 + peso * f2, GRB.MINIMIZE)

    pontos: list[ResultadoMip] = []
    epsilon = GRB.INFINITY

    for _ in range(max_pontos):
        limite.RHS = epsilon
        mod.optimize()

        if mod.Status == GRB.INFEASIBLE:
            break
        if mod.SolCount == 0:
            raise SolverIndisponivel(
                f"solver terminou sem solucao (status {mod.Status})")

        valor_f1 = f1.getValue()
        valor_f2 = f2.getValue()
        sol, B, partidas = _extrair(mod, inst)
        pontos.append(ResultadoMip(f1=valor_f1, f2=valor_f2, solucao=sol,
                                   tempo=mod.Runtime, B=B, partidas=partidas))
        if valor_f2 <= passo:
            break
        epsilon = valor_f2 - passo

    return pontos
