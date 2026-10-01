"""GRASP (Greedy Randomized Adaptive Search Procedure) Multiobjetivo para o DARP."""

from __future__ import annotations

import random
import time

from ..avaliador import Avaliador
from ..instancia import Instancia
from ..pareto import domina
from ..solucao import Solucao, solucao_individual
from .base import ArquivoPareto, Metaheuristica, ResultadoOtimizacao
from .operadores import construcao_gulosa_randomizada, perturbar_solucao


class GRASP(Metaheuristica):
    """GRASP com diversificacao de pesos na construcao RCL e busca local multiobjetivo."""

    def __init__(
        self,
        max_iteracoes: int = 30,
        alpha_rcl: float = 0.3,
        max_passos_busca_local: int = 25,
        seed: int | None = None,
    ) -> None:
        super().__init__(nome="GRASP")
        self.max_iteracoes = max_iteracoes
        self.alpha_rcl = alpha_rcl
        self.max_passos_busca_local = max_passos_busca_local
        self.seed = seed

    def _busca_local(
        self,
        sol_inicial: Solucao,
        inst: Instancia,
        av: Avaliador,
        peso_f1: float,
        rng: random.Random,
    ) -> tuple[Solucao, int]:
        """Busca local por primeiro aprimoramento (First Improvement) no objetivo ponderado."""
        atual = sol_inicial
        res_atual = av.avaliar(atual)
        avaliacoes = 1

        def custo(f1: float, f2: float, viol: int) -> float:
            return peso_f1 * f1 + (1.0 - peso_f1) * f2 + viol * 1000.0

        c_atual = custo(res_atual.f1, res_atual.f2, len(res_atual.violacoes))

        for _ in range(self.max_passos_busca_local):
            melhorou = False
            # Amostra de vizinhos
            for _ in range(15):
                vizinho = perturbar_solucao(atual, inst, rng)
                res_viz = av.avaliar(vizinho)
                avaliacoes += 1

                c_viz = custo(res_viz.f1, res_viz.f2, len(res_viz.violacoes))
                # Criterio: aprimoramento na funcao ponderada ou dominancia de Pareto
                if c_viz < c_atual - 1e-4 or domina(res_viz.objetivos, res_atual.objetivos):
                    atual = vizinho
                    res_atual = res_viz
                    c_atual = c_viz
                    melhorou = True
                    break

            if not melhorou:
                break

        return atual, avaliacoes

    def otimizar(
        self,
        inst: Instancia,
        av: Avaliador,
        **kwargs,
    ) -> ResultadoOtimizacao:
        inicio = time.time()
        rng = random.Random(self.seed)
        arquivo = ArquivoPareto()

        # Inclui ponto de referencia
        base = solucao_individual(inst)
        aval_base = av.avaliar(base)
        if aval_base.viavel:
            arquivo.adicionar(aval_base.f1, aval_base.f2, base)

        total_avals = 1
        historico = []

        for it in range(self.max_iteracoes):
            # Varia o peso sistematicamente em [0.05, 0.95] para cobrir toda a curva de Pareto
            peso_f1 = 0.05 + 0.90 * (it / max(1, self.max_iteracoes - 1))

            # Fase 1: Construcao Gulosa Randomizada (RCL)
            sol_construida = construcao_gulosa_randomizada(
                inst, av, alpha=self.alpha_rcl, peso_f1=peso_f1, rng=rng
            )
            res_c = av.avaliar(sol_construida)
            total_avals += 1
            if res_c.viavel:
                arquivo.adicionar(res_c.f1, res_c.f2, sol_construida)

            # Fase 2: Busca Local
            sol_otimizada, avals_bl = self._busca_local(
                sol_construida, inst, av, peso_f1, rng
            )
            total_avals += avals_bl

            res_bl = av.avaliar(sol_otimizada)
            total_avals += 1
            if res_bl.viavel:
                arquivo.adicionar(res_bl.f1, res_bl.f2, sol_otimizada)

            historico.append({
                "iteracao": it,
                "peso_f1": peso_f1,
                "tamanho_pareto": len(arquivo),
            })

        duracao = time.time() - inicio
        return ResultadoOtimizacao(
            algoritmo=self.nome,
            fronteira=arquivo.pontos,
            tempo_execucao=duracao,
            iteracoes=self.max_iteracoes,
            avaliacoes=total_avals,
            historico=historico,
        )
