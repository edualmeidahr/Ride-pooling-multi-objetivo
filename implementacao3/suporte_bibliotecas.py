"""Adaptação do DARP aos motores prontos, sem implementar seus ciclos de busca."""
from contextlib import contextmanager
from importlib import import_module, metadata
import math
import random

import numpy as np

from comum.solucao import Rota, Solucao
from implementacao3.base import ResultadoOtimizacao

PESOS_PADRAO = ((0.8, 0.2), (0.5, 0.5), (0.2, 0.8))


def dependencia(nome):
    try:
        return import_module(nome)
    except ImportError as erro:
        raise RuntimeError(f"O método de biblioteca exige {nome}. Instale com: "
                           "python -m pip install -r requirements.txt") from erro


def identificar(dono, pacote, motor):
    dependencia(pacote)
    dono._metadados = {'origem': 'biblioteca', 'biblioteca': pacote,
                      'versao_biblioteca': metadata.version(pacote), 'motor': motor}


def inteiro(valor, nome, minimo=1):
    if type(valor) is not int or valor < minimo:
        raise ValueError(f'{nome} deve ser inteiro >= {minimo}')
    return valor


def pesos_validos(pesos):
    if pesos is not None and not isinstance(pesos, (list, tuple)):
        raise ValueError('pesos devem ser uma lista de pares')
    resultado = []
    for par in PESOS_PADRAO if pesos is None else pesos:
        if not isinstance(par, (list, tuple)) or len(par) != 2 or any(isinstance(x, bool) or not isinstance(x, (int, float))
                               or not math.isfinite(x) or x < 0 for x in par) or sum(par) <= 0:
            raise ValueError('pesos devem conter pares finitos nao negativos com soma positiva')
        resultado.append(tuple(x/sum(par) for x in par))
    if not resultado:
        raise ValueError('informe ao menos um par de pesos')
    return resultado


def semente_valida(seed):
    if type(seed) is not int:
        raise ValueError('seed deve ser inteiro')
    return seed % (2**32)


class CodificacaoRotas:
    """Chaves reais: Q, n veículos, n coletas e n entregas; domínio [0,1]."""
    def __init__(self, contexto):
        self.contexto = contexto
        self.qs = contexto.viaveis
        self.inst = contexto.obter(self.qs[0])[0]
        self.n = self.inst.n
        self.dimensoes = 3*self.n + 1

    @staticmethod
    def indice(chave, tamanho):
        return min(int(chave*tamanho), tamanho-1)

    def decodificar(self, vetor):
        vetor = np.asarray(vetor, dtype=float)
        if vetor.shape != (self.dimensoes,) or not np.all(np.isfinite(vetor)):
            raise ValueError('vetor de rotas com dimensao ou valores invalidos')
        vetor = np.clip(vetor, 0.0, 1.0)
        q = self.qs[self.indice(vetor[0], len(self.qs))]
        pedidos = [[] for _ in range(self.inst.m)]
        for i in range(1, self.n+1):
            pedidos[self.indice(vetor[i], self.inst.m)].append(i)
        rotas = []
        for grupo in pedidos:
            # Uma entrega só fica disponível após sua própria coleta.
            disponiveis, seq = set(grupo), []
            while disponiveis:
                no = min(disponiveis, key=lambda x: (vetor[self.n+x], x))
                disponiveis.remove(no)
                seq.append(no)
                if no <= self.n:
                    disponiveis.add(no+self.n)
            rotas.append(Rota(seq))
        return Solucao(rotas, Q=q)

    def codificar(self, sol):
        if type(sol.Q) is not int or sol.Q not in self.qs or sol.conferir_estrutura(self.inst):
            raise ValueError('solucao nao representavel no contexto')
        vetor = np.full(self.dimensoes, 0.5)
        vetor[0] = (self.qs.index(sol.Q)+0.5)/len(self.qs)
        for k, rota in enumerate(sol.rotas):
            for pos, no in enumerate(rota.sequencia):
                vetor[self.n+no] = (pos+0.5)/len(rota.sequencia)
                if no <= self.n:
                    vetor[no] = (k+0.5)/self.inst.m
        return vetor


def avaliar(dono, contexto, sol):
    res = contexto.avaliar(sol)
    if res.viavel:
        dono._arquivo.adicionar(res.f1, res.f2, sol)
    return res


def amostra_inicial(dono, contexto, codec, tamanho, seed, trajetorias=1):
    rng = random.Random(seed)
    vetores = []
    consumir_original, inicio = contexto.consumir, contexto.consultas
    limite = contexto.max_consultas_rotas
    quota = None if limite is None else max(1, limite//(4*trajetorias))

    class LimiteAmostra(Exception):
        pass

    def consumir():
        if quota is not None and contexto.consultas-inicio >= quota:
            raise LimiteAmostra()
        consumir_original()
    contexto.consumir = consumir
    try:
        # Inicialização ocupa até 1/4 da quota; reserva esforço para o motor.
        for q in contexto.viaveis[:max(1, tamanho-1)]:
            sol = contexto.individual(q)
            avaliar(dono, contexto, sol)
            vetores.append(codec.codificar(sol))
        q = contexto.viaveis[len(contexto.viaveis)//2]
        sol = contexto.construir(q, rng, alpha=0.3, peso_f1=0.5)
        avaliar(dono, contexto, sol)
        vetores.append(codec.codificar(sol))
    except LimiteAmostra:
        pass
    finally:
        contexto.consumir = consumir_original
    gerador = np.random.default_rng(seed)
    while len(vetores) < tamanho:
        vetores.append(gerador.random(codec.dimensoes))
    return np.asarray(vetores)


def problema_pymoo(dono, contexto, codec, pesos=None):
    # Import tardio: os quatro métodos próprios não exigem pymoo instalado.
    from pymoo.core.problem import ElementwiseProblem

    class ProblemaRotas(ElementwiseProblem):
        def __init__(self):
            super().__init__(n_var=codec.dimensoes, n_obj=2 if pesos is None else 1,
                             n_ieq_constr=1, xl=0.0, xu=1.0)

        def _evaluate(self, x, out, *args, **kwargs):
            res = avaliar(dono, contexto, codec.decodificar(x))
            f = (res.f1/contexto.escalas[0], res.f2/contexto.escalas[1])
            out['F'] = f if pesos is None else [sum(w*v for w,v in zip(pesos, f))]
            out['G'] = [len(res.violacoes)]
    return ProblemaRotas()


def callback_pymoo(dono, contexto, trajetoria=None):
    def registrar(algoritmo):
        dono._historico.append({'iteracao': int(algoritmo.n_iter), 'trajetoria': trajetoria,
            'tamanho_pareto': len(dono._arquivo), 'consultas': contexto.consultas,
            'visitas_q': dict(contexto.visitas)})
    return registrar


class LimiteTrajetoria(Exception):
    """Quota local; outra trajetória ainda pode usar o restante do método."""


@contextmanager
def quota_trajetoria(contexto, indice, quantidade):
    limite_global = contexto.max_consultas_rotas
    consumir_original = contexto.consumir
    inicio = contexto.consultas
    if limite_global is None:
        yield
        return
    quota = limite_global//quantidade
    if indice == quantidade-1:
        quota += limite_global % quantidade

    def consumir():
        if contexto.consultas-inicio >= quota:
            raise LimiteTrajetoria()
        consumir_original()
    contexto.consumir = consumir
    try:
        yield
    finally:
        contexto.consumir = consumir_original


@contextmanager
def semente_simanneal(seed):
    # O motor simanneal usa random global para a aceitação. Execuções são seriais.
    estado = random.getstate()
    random.seed(seed)
    try:
        yield
    finally:
        random.setstate(estado)


def resultado(dono, inicio, motivo='iteracoes'):
    from time import perf_counter
    return ResultadoOtimizacao(dono.nome, dono._arquivo.pontos,
        tempo_execucao=perf_counter()-inicio, iteracoes=len(dono._historico),
        historico=dono._historico, motivo_parada=motivo)
