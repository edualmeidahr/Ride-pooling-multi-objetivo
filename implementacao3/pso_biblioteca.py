"""PSO pronto do pymoo; pesos exploram os dois objetivos do DARP."""
from time import perf_counter

from comum.capacidade import LimiteBusca
from implementacao3.base import Metaheuristica
from implementacao3.suporte_bibliotecas import (CodificacaoRotas, identificar, inteiro,
    pesos_validos, amostra_inicial, problema_pymoo, callback_pymoo, quota_trajetoria,
    LimiteTrajetoria, resultado, semente_valida)


class PSOBiblioteca(Metaheuristica):
    def __init__(self, tamanho_populacao=16, iteracoes=20, pesos=None, seed=42):
        super().__init__('PSO biblioteca (pymoo)')
        self.tamanho_populacao = inteiro(tamanho_populacao, 'tamanho_populacao', 2)
        self.iteracoes = inteiro(iteracoes, 'iteracoes')
        self.pesos = pesos_validos(pesos)
        self.seed = semente_valida(seed)

    def otimizar(self, inst, av, **kwargs):
        inicio = perf_counter()
        identificar(self, 'pymoo', 'pymoo.algorithms.soo.nonconvex.pso.PSO')
        from pymoo.algorithms.soo.nonconvex.pso import PSO
        from pymoo.optimize import minimize
        contexto = kwargs['contextos']
        codec = CodificacaoRotas(contexto)
        motivo = 'iteracoes'
        for indice, pesos in enumerate(self.pesos):
            try:
                with quota_trajetoria(contexto, indice, len(self.pesos)):
                    amostra = amostra_inicial(self, contexto, codec, self.tamanho_populacao,
                                             self.seed+indice, len(self.pesos))
                    motor = PSO(pop_size=self.tamanho_populacao, sampling=amostra)
                    minimize(problema_pymoo(self, contexto, codec, pesos), motor, ('n_gen', self.iteracoes),
                             seed=self.seed+indice, verbose=False, copy_algorithm=False,
                             callback=callback_pymoo(self, contexto, indice))
            except (LimiteTrajetoria, LimiteBusca):
                motivo = 'consultas_rotas'
                self._historico.append({'trajetoria': indice, 'pesos': pesos,
                    'motivo_parada': 'consultas_rotas', 'consultas': contexto.consultas})
        return resultado(self, inicio, motivo)
