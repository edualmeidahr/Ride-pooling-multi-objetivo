"""Insercao gulosa deterministica: uma construcao, sem busca local ou reinicios."""
import math
import time
from dataclasses import dataclass, field

from comum.avaliador import Avaliador, Avaliacao
from comum.instancia import Instancia
from comum.solucao import Rota, Solucao
from comum.operadores import inserir_requisicao, posicoes_insercao


@dataclass
class ResultadoHeuristica:
    status: str
    solucao: Solucao | None
    avaliacao: Avaliacao | None
    pedidos_pendentes: list[int]
    tempo_execucao: float
    candidatos_testados: int
    avaliacoes_rotas: int
    historico: list[dict] = field(default_factory=list)


class HeuristicaGulosa:
    """Escolhe a menor soma ponderada dos acrescimos normalizados por etapa.

    Pesos sao preferencias de insercao, nao garantia de otimo ponderado global.
    Em bloqueio, nao apresenta a construcao parcial como solucao do problema.
    """
    def __init__(self, peso_emissao: float = 0.5, limite_pedidos: int | None = None, limite_posicoes: int | None = None):
        if isinstance(peso_emissao, bool) or not isinstance(peso_emissao, (int, float)) or not math.isfinite(peso_emissao) or not 0 <= peso_emissao <= 1:
            raise ValueError("peso_emissao deve ser um numero entre 0 e 1")
        self.peso_emissao = float(peso_emissao)
        if limite_pedidos is not None and (type(limite_pedidos) is not int or limite_pedidos < 1):
            raise ValueError("limite_pedidos deve ser inteiro positivo ou None")
        self.limite_pedidos = limite_pedidos
        if limite_posicoes is not None and (type(limite_posicoes) is not int or limite_posicoes < 2):
            raise ValueError("limite_posicoes deve ser inteiro >= 2 ou None")
        self.limite_posicoes = limite_posicoes

    def resolver(self, inst: Instancia, av: Avaliador) -> ResultadoHeuristica:
        if av.inst is not inst:
            raise ValueError("avaliador deve usar a mesma instancia da heuristica")
        inicio = time.perf_counter()
        sol = Solucao([Rota() for _ in range(inst.m)])
        pendentes = sorted(inst.coletas, key=lambda i: (inst.rho[i], i)) if self.limite_pedidos else list(inst.coletas)
        historico, cache = [], {(): (True, 0.0, 0.0)}
        candidatos_testados = avaliacoes_rotas = 0

        def custo_rota(rota):
            nonlocal avaliacoes_rotas
            chave = tuple(rota.sequencia)
            if chave not in cache:
                # Podas necessarias: nao excluem uma agenda temporalmente viavel.
                carga, instante, ultimo = 0, inst.nos[inst.deposito_ini].e, inst.deposito_ini
                for no in rota.sequencia:
                    carga += inst.nos[no].q
                    chegada = instante + inst.tempo(ultimo, no)
                    atendimento = max(chegada, inst.nos[no].e)
                    if not 0 <= carga <= inst.Q or atendimento > inst.nos[no].l + av.par.tolerancia:
                        cache[chave] = (False, 0.0, 0.0)
                        return cache[chave]
                    instante, ultimo = atendimento + inst.nos[no].s, no
                agenda, violacoes = av.avaliar_rota(rota)
                avaliacoes_rotas += 1
                if violacoes:
                    cache[chave] = (False, 0.0, 0.0)
                else:
                    desvio, espera, _ = av.contribuicao(agenda)
                    cache[chave] = (True, av.emissao_rota(rota), desvio + espera)
            return cache[chave]

        while pendentes:
            custos_base = [custo_rota(rota) for rota in sol.rotas]
            candidatos = []
            pool = pendentes[:self.limite_pedidos] if self.limite_pedidos else pendentes
            for req in pool:
                for k, rota in enumerate(sol.rotas):
                    tam = len(rota.sequencia)
                    if getattr(av, "coletas_concorrentes", False) and sum(inst.nos[i].q for i in rota.sequencia if i <= inst.n) + inst.nos[req].q > inst.Q:
                        continue
                    for coleta, entrega in posicoes_insercao(tam, self.limite_posicoes):
                            candidatos_testados += 1
                            nova = inserir_requisicao(rota, req, coleta, entrega, inst)
                            viavel, f1, f2 = custo_rota(nova)
                            if viavel:
                                candidatos.append((f1 - custos_base[k][1], f2 - custos_base[k][2],
                                                   req, k, coleta, entrega))
            if not candidatos:
                return ResultadoHeuristica("bloqueada", None, None, list(pendentes),
                    time.perf_counter()-inicio, candidatos_testados, avaliacoes_rotas, historico)
            min1, max1 = min(c[0] for c in candidatos), max(c[0] for c in candidatos)
            min2, max2 = min(c[1] for c in candidatos), max(c[1] for c in candidatos)

            def chave(c):
                z1 = (c[0]-min1)/(max1-min1) if max1 > min1 else 0.0
                z2 = (c[1]-min2)/(max2-min2) if max2 > min2 else 0.0
                nota = self.peso_emissao*z1 + (1-self.peso_emissao)*z2
                return (nota, *c)

            escolhido = min(candidatos, key=chave)
            d1, d2, req, k, coleta, entrega = escolhido
            sol.rotas[k] = inserir_requisicao(sol.rotas[k], req, coleta, entrega, inst)
            pendentes.remove(req)
            historico.append({"etapa": len(historico)+1, "pedido_interno": req, "veiculo_indice": k,
                              "posicao_coleta": coleta, "posicao_entrega_antes_da_insercao": entrega,
                              "acrescimo_f1": d1, "acrescimo_f2": d2, "nota_insercao": chave(escolhido)[0],
                              "candidatos_viaveis": len(candidatos),
                              "faixas_normalizacao": [[min1, max1], [min2, max2]]})
        avaliacao = av.avaliar(sol)
        if not avaliacao.viavel:
            raise RuntimeError(f"construcao completa inconsistente: {avaliacao.violacoes}")
        return ResultadoHeuristica("concluida", sol, avaliacao, [], time.perf_counter()-inicio,
                                   candidatos_testados, avaliacoes_rotas, historico)
