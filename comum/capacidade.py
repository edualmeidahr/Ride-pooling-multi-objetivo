"""Contextos isolados e movimentos de capacidade homogênea."""
from collections import Counter
from copy import deepcopy
from dataclasses import replace
import math

from comum.avaliador import Avaliador
from comum.cenarios import cenario_capacidade
from comum.emissoes import phi_para_q
from comum.solucao import Rota, Solucao, solucao_individual


class LimiteBusca(Exception):
    """Orçamento comum de consultas de rotas esgotado."""


class AvaliadorComCache(Avaliador):
    def __init__(self, inst, par, cache=True, orcamento=None):
        super().__init__(inst, par)
        self._cache = {} if cache else None
        self.orcamento = orcamento

    def agendar(self, rota, partida=None, politica=None):
        if rota.usada and self.orcamento is not None:
            self.orcamento.consumir()
        chave = (tuple(rota.sequencia), partida, politica or self.par.politica)
        if self._cache is None:
            return super().agendar(rota, partida, politica)
        if chave not in self._cache:
            self._cache[chave] = super().agendar(rota, partida, politica)
        else:
            self.contadores['acertos_cache'] += int(rota.usada)
        return deepcopy(self._cache[chave])


class ContextoCapacidades:
    def __init__(self, inst, par, capacidades, modelo_emissoes=None, *, cache=True,
                 construcao=None, concorrentes=False, max_consultas_rotas=None):
        if not capacidades or any(type(q) is not int or q < 1 for q in capacidades):
            raise ValueError("capacidades devem ser inteiros positivos")
        if max_consultas_rotas is not None and (type(max_consultas_rotas) is not int or max_consultas_rotas < 1):
            raise ValueError("max_consultas_rotas deve ser inteiro positivo")
        for nome, minimo in (('limite_pedidos_candidatos', 1), ('limite_posicoes_insercao', 2)):
            valor = (construcao or {}).get(nome)
            if valor is not None and (type(valor) is not int or valor < minimo):
                raise ValueError(f'{nome} deve ser inteiro >= {minimo}')
        self.capacidades = tuple(sorted(set(capacidades)))
        demanda = max((inst.nos[i].q for i in inst.coletas), default=1)
        self.excluidas = [q for q in self.capacidades if q < demanda]
        self.viaveis = tuple(q for q in self.capacidades if q >= demanda)
        self.max_consultas_rotas = max_consultas_rotas
        self.consultas = 0
        self.avaliadores = {}
        self.visitas = Counter()
        self.movimentos = []
        self.reparos = Counter()
        self.modelo_emissoes = modelo_emissoes
        for q in self.capacidades:
            phi = phi_para_q(modelo_emissoes, q) if modelo_emissoes else par.phi
            av = AvaliadorComCache(cenario_capacidade(inst, q), replace(par, phi=phi), cache, self)
            av.limite_pedidos_construcao = (construcao or {}).get('limite_pedidos_candidatos')
            av.limite_posicoes_construcao = (construcao or {}).get('limite_posicoes_insercao')
            av.coletas_concorrentes = concorrentes
            self.avaliadores[q] = av
        # Referência física comum: independe de Q do candidato e da unidade de phi.
        max_phi = max(a.par.phi for a in self.avaliadores.values())
        dist = sum(inst.dist_ambiental(0, i) + inst.dist_ambiental(i, inst.entrega_de(i))
                   + inst.dist_ambiental(inst.entrega_de(i), inst.deposito_fim) for i in inst.coletas)
        tempo = sum(inst.nos[i].q * (max(0, inst.nos[i].l - inst.rho[i])
                    + max(0, inst.limite_bordo(i, par.alpha) - inst.t_direto(i))) for i in inst.coletas)
        self.escalas = (max(1e-12, max_phi * dist), max(1.0, tempo))

    @classmethod
    def fixo(cls, inst, av):
        ctx = cls(inst, av.par, [inst.Q])
        ctx.avaliadores = {inst.Q: av}
        return ctx

    def consumir(self):
        if self.max_consultas_rotas is not None and self.consultas >= self.max_consultas_rotas:
            raise LimiteBusca("consultas_rotas")
        self.consultas += 1

    def obter(self, q):
        if type(q) is not int or q not in self.avaliadores:
            raise ValueError(f"Q={q} fora do dominio autorizado")
        av = self.avaliadores[q]
        return av.inst, av

    def avaliar(self, sol):
        if sol.Q is None:
            raise ValueError("Q obrigatorio no candidato")
        self.visitas[sol.Q] += 1
        return self.obter(sol.Q)[1].avaliar(sol)

    def escolher(self, indice, rng):
        if not self.viaveis:
            raise ValueError("nenhum Q comporta a demanda indivisivel dos pedidos")
        if indice < len(self.viaveis):
            return self.viaveis[indice]
        return self.viaveis[0] if len(self.viaveis) == 1 else rng.choice(self.viaveis)

    def individual(self, q):
        sol = solucao_individual(self.obter(q)[0])
        sol.Q = q
        return sol

    def construir(self, q, rng, alpha=0.3, peso_f1=0.5):
        from comum.operadores import construcao_gulosa_randomizada
        inst, av = self.obter(q)
        sol = construcao_gulosa_randomizada(inst, av, alpha, peso_f1, rng)
        sol.Q = q
        return sol

    def mudar(self, sol, q, rng):
        """Reparo limitado no Q solicitado; nunca eleva capacidade silenciosamente."""
        from comum.operadores import inserir_requisicao, remover_requisicao, posicoes_insercao
        inst, av = self.obter(q)
        nova = sol.copiar()
        nova.Q, nova.partidas = q, None
        evento = {'de': sol.Q, 'para': q, 'aceito': False}
        self.movimentos.append(evento)
        if q in self.excluidas:
            return None
        pendentes = []
        for k, rota in enumerate(nova.rotas):
            while pico_carga(inst, rota) > q:
                self.reparos['pares_removidos'] += 1
                carga, retirar = 0, None
                for no in rota.sequencia:
                    carga += inst.nos[no].q
                    if carga > q:
                        retirar = no
                        break
                pendentes.append(retirar)
                rota = remover_requisicao(rota, retirar, inst)
            nova.rotas[k] = rota
        if pendentes:
            self.reparos['tentativas'] += 1
            nova.rotas.extend(Rota() for _ in range(inst.m - len(nova.rotas)))
            for req in pendentes:
                melhor = None
                for k, rota in enumerate(nova.rotas):
                    for c, e in posicoes_insercao(len(rota), getattr(av, 'limite_posicoes_construcao', None) or 8):
                        teste = inserir_requisicao(rota, req, c, e, inst)
                        if pico_carga(inst, teste) > q:
                            continue
                        ag, erros = av.avaliar_rota(teste)
                        if not erros:
                            custo = av.emissao_rota(teste) - av.emissao_rota(rota)
                            if melhor is None or custo < melhor[0]:
                                melhor = (custo, k, teste)
                if melhor is None:
                    nova = self.construir(q, rng)
                    break
                nova.rotas[melhor[1]] = melhor[2]
        if not self.avaliar(nova).viavel:
            self.reparos['falhas'] += 1
            return None
        evento['aceito'] = True
        if pendentes:
            self.reparos['sucessos'] += 1
        return nova

    def perturbar(self, sol, rng, prob_q=0.35):
        from comum.operadores import perturbar_solucao
        if len(self.viaveis) > 1 and rng.random() < prob_q:
            idx = self.viaveis.index(sol.Q)
            candidatos = [q for i, q in enumerate(self.viaveis) if abs(i-idx) == 1]
            if rng.random() < 0.25:
                candidatos = [q for q in self.viaveis if q != sol.Q]
            nova = self.mudar(sol, rng.choice(candidatos), rng)
            if nova is not None:
                if rng.random() < 0.3:
                    nova = perturbar_solucao(nova, self.obter(nova.Q)[0], rng)
                return nova
        return perturbar_solucao(sol, self.obter(sol.Q)[0], rng)

    def estatisticas(self):
        contadores = Counter()
        for av in self.avaliadores.values():
            contadores.update(av.contadores)
        return {'contadores': dict(contadores), 'visitas_q': dict(self.visitas),
                'movimentos_q': list(self.movimentos), 'reparos': dict(self.reparos),
                'escalas': self.escalas, 'capacidades_excluidas': self.excluidas,
                'consultas_orcamento': self.consultas}


def pico_carga(inst, rota):
    carga = pico = 0
    for no in rota.sequencia:
        carga += inst.nos[no].q
        pico = max(pico, carga)
    return pico


def chave_solucao(sol):
    return (sol.Q if sol.Q is not None else math.inf,
            tuple(sorted(tuple(r.sequencia) for r in sol.rotas if r.usada)),
            tuple(sorted((sol.partidas or {}).items())))
