"""Simulated Annealing do simanneal, sem reimplementar resfriamento ou aceitação."""
import math
import random
from time import perf_counter

from comum.capacidade import LimiteBusca
from implementacao3.base import Metaheuristica
from implementacao3.suporte_bibliotecas import (identificar, inteiro, pesos_validos,
    avaliar, quota_trajetoria, LimiteTrajetoria, semente_simanneal, resultado, semente_valida)


class AnnealingBiblioteca(Metaheuristica):
    def __init__(self, iteracoes=300, temp_inicial=2.0, temp_final=0.01, pesos=None, seed=42):
        super().__init__('SA biblioteca (simanneal)')
        self.iteracoes = inteiro(iteracoes, 'iteracoes')
        if any(isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t)
               for t in (temp_inicial, temp_final)) or not 0 < temp_final < temp_inicial:
            raise ValueError('temperaturas exigem 0 < temp_final < temp_inicial')
        self.temp_inicial, self.temp_final = temp_inicial, temp_final
        self.pesos, self.seed = pesos_validos(pesos), semente_valida(seed)

    def otimizar(self, inst, av, **kwargs):
        inicio = perf_counter()
        identificar(self, 'simanneal', 'simanneal.Annealer.anneal')
        from simanneal import Annealer
        contexto, dono = kwargs['contextos'], self
        motivo = 'iteracoes'

        class AnnealerRotas(Annealer):
            def copy_state(self, state):
                return state.copiar()

            def move(self):
                self.state = contexto.perturbar(self.state, self.rng)

            def energy(self):
                res = avaliar(dono, contexto, self.state)
                return sum(w*f/s for w,f,s in zip(self.pesos, res.objetivos, contexto.escalas)) + 1000*len(res.violacoes)

            def update(self, step, T, E, acceptance, improvement):
                dono._historico.append({'trajetoria': self.indice, 'iteracao': step,
                    'temperatura': T, 'energia': E, 'tamanho_pareto': len(dono._arquivo),
                    'consultas': contexto.consultas, 'Q': self.state.Q})

        for indice, pesos in enumerate(self.pesos):
            try:
                with quota_trajetoria(contexto, indice, len(self.pesos)), semente_simanneal(self.seed+indice):
                    rng = random.Random(self.seed+indice)
                    q = contexto.escolher(indice, rng)
                    base = contexto.individual(q)
                    avaliar(self, contexto, base)
                    construida, viavel = base, False
                    try:
                        with quota_trajetoria(contexto, 0, 4*len(self.pesos)):
                            construida = contexto.construir(q, rng, peso_f1=pesos[0])
                            viavel = avaliar(self, contexto, construida).viavel
                    except LimiteTrajetoria:
                        pass
                    # O motor instala um handler SIGINT; restaurá-lo evita interferir no menu.
                    import signal
                    handler = signal.getsignal(signal.SIGINT)
                    try:
                        motor = AnnealerRotas(construida if viavel else base)
                        motor.rng, motor.pesos, motor.indice = rng, pesos, indice
                        motor.Tmax, motor.Tmin, motor.steps = self.temp_inicial, self.temp_final, self.iteracoes
                        motor.updates = min(20, self.iteracoes)
                        motor.anneal()
                    finally:
                        signal.signal(signal.SIGINT, handler)
                    if motor.user_exit:
                        motivo = 'interrompida'
                        break
            except (LimiteTrajetoria, LimiteBusca):
                motivo = 'consultas_rotas'
                self._historico.append({'trajetoria': indice, 'pesos': pesos,
                    'motivo_parada': 'consultas_rotas', 'consultas': contexto.consultas})
        return resultado(self, inicio, motivo)
