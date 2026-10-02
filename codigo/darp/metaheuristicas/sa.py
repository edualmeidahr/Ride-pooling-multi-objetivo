"""Simulated Annealing Multiobjetivo (MOSA) para o DARP."""

from __future__ import annotations

import math
import random
import time

from ..avaliador import Avaliador
from ..instancia import Instancia
from ..solucao import solucao_individual
from .base import ArquivoPareto, Metaheuristica, ResultadoOtimizacao
from .operadores import construcao_gulosa_randomizada, perturbar_solucao


class SimulatedAnnealing(Metaheuristica):
    """Simulated Annealing com arquivo externo de Pareto e exploracao multivetorial."""

    def __init__(
        self,
        temp_inicial: float = 100.0,
        temp_final: float = 0.5,
        fator_resfriamento: float = 0.92,
        iter_por_temp: int = 15,
        pesos: list[tuple[float, float]] | None = None,
        seed: int | None = None,
    ) -> None:
        super().__init__(nome="Simulated Annealing")
        self.temp_inicial = temp_inicial
        self.temp_final = temp_final
        self.fator_resfriamento = fator_resfriamento
        self.iter_por_temp = iter_por_temp
        self.pesos = pesos or [(0.8, 0.2), (0.5, 0.5), (0.2, 0.8)]
        self.seed = seed

    def otimizar(
        self,
        inst: Instancia,
        av: Avaliador,
        **kwargs,
    ) -> ResultadoOtimizacao:
        inicio = time.time()
        rng = random.Random(self.seed)
        arquivo = ArquivoPareto()

        # Solucao de partida
        sol_base = solucao_individual(inst)
        aval_base = av.avaliar(sol_base)
        if aval_base.viavel:
            arquivo.adicionar(aval_base.f1, aval_base.f2, sol_base)

        total_iter = 0
        total_avals = 1
        historico = []

        # Executa uma trajetoria de resfriamento para cada vetor de pesos de exploracao
        for idx_peso, (w1, w2) in enumerate(self.pesos):
            # Solucao inicial gerada de forma gulosa ponderada
            sol_atual = construcao_gulosa_randomizada(inst, av, alpha=0.3, peso_f1=w1, rng=rng)
            aval_atual = av.avaliar(sol_atual)
            total_avals += 1
            if aval_atual.viavel:
                arquivo.adicionar(aval_atual.f1, aval_atual.f2, sol_atual)

            # Normalizacao da energia pelo ponto base para manter escalas balanceadas
            ref_f1 = max(1.0, aval_base.f1)
            ref_f2 = max(1.0, aval_base.f2)

            def energia(f1: float, f2: float, violacoes: int) -> float:
                penalidade = violacoes * 1000.0
                return w1 * (f1 / ref_f1) + w2 * (f2 / ref_f2) + penalidade

            e_atual = energia(aval_atual.f1, aval_atual.f2, len(aval_atual.violacoes))
            T = self.temp_inicial

            while T > self.temp_final:
                for _ in range(self.iter_por_temp):
                    total_iter += 1
                    vizinho = perturbar_solucao(sol_atual, inst, rng)
                    aval_viz = av.avaliar(vizinho)
                    total_avals += 1

                    if aval_viz.viavel:
                        arquivo.adicionar(aval_viz.f1, aval_viz.f2, vizinho)

                    e_viz = energia(aval_viz.f1, aval_viz.f2, len(aval_viz.violacoes))
                    delta_e = e_viz - e_atual

                    if delta_e <= 0.0 or rng.random() < math.exp(-delta_e / max(1e-4, T)):
                        sol_atual = vizinho
                        e_atual = e_viz

                historico.append({
                    "trajetoria": idx_peso,
                    "temperatura": T,
                    "tamanho_pareto": len(arquivo),
                    "fronteira": [(p[0], p[1]) for p in arquivo.pontos],
                    "agendamentos": getattr(av, "agendamentos", None),
                    "tempo": time.time() - inicio,
                })
                T *= self.fator_resfriamento

        duracao = time.time() - inicio
        return ResultadoOtimizacao(
            algoritmo=self.nome,
            fronteira=arquivo.pontos,
            tempo_execucao=duracao,
            iteracoes=total_iter,
            avaliacoes=total_avals,
            historico=historico,
        )
