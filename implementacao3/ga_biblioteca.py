"""NSGA-II fornecido pelo pymoo, com adaptação numérica do DARP."""
from time import perf_counter

from implementacao3.base import ORCAMENTO_BUSCA, Metaheuristica
from implementacao3.suporte_bibliotecas import (CodificacaoRotas, identificar, inteiro,
    amostra_inicial, problema_pymoo, callback_pymoo, resultado, semente_valida)


class GeneticoBiblioteca(Metaheuristica):
    def __init__(self, tamanho_populacao=16, geracoes=ORCAMENTO_BUSCA, seed=42):
        super().__init__('GA biblioteca (pymoo NSGA-II)')
        self.tamanho_populacao = inteiro(tamanho_populacao, 'tamanho_populacao', 2)
        self.geracoes = inteiro(geracoes, 'geracoes')
        self.seed = semente_valida(seed)

    def otimizar(self, inst, av, **kwargs):
        inicio = perf_counter()
        identificar(self, 'pymoo', 'pymoo.algorithms.moo.nsga2.NSGA2')
        from pymoo.algorithms.moo.nsga2 import NSGA2
        from pymoo.optimize import minimize
        contexto = kwargs['contextos']
        codec = CodificacaoRotas(contexto)
        amostra = amostra_inicial(self, contexto, codec, self.tamanho_populacao, self.seed)
        motor = NSGA2(pop_size=self.tamanho_populacao, sampling=amostra)
        minimize(problema_pymoo(self, contexto, codec), motor, ('n_gen', self.geracoes),
                 seed=self.seed, verbose=False, copy_algorithm=False,
                 callback=callback_pymoo(self, contexto))
        return resultado(self, inicio)
