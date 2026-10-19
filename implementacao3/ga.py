"""Algoritmo Genetico Multiobjetivo (inspirado no NSGA-II) para o DARP."""

from __future__ import annotations

import random
import time

from comum.avaliador import Avaliador
from comum.instancia import Instancia
from comum.pareto import domina
from comum.solucao import Rota, Solucao
from implementacao3.base import ORCAMENTO_BUSCA, Metaheuristica, ResultadoOtimizacao
from comum.operadores import inserir_requisicao


class AlgoritmoGenetico(Metaheuristica):
    """Algoritmo Genetico Multiobjetivo com ranking de Pareto e elitismo."""

    def __init__(
        self,
        tamanho_populacao: int = 30,
        geracoes: int = ORCAMENTO_BUSCA,
        prob_crossover: float = 0.85,
        prob_mutacao: float = 0.35,
        seed: int | None = None,
    ) -> None:
        super().__init__(nome="Algoritmo Genetico")
        self.tamanho_populacao = tamanho_populacao
        self.geracoes = geracoes
        self.prob_crossover = prob_crossover
        self.prob_mutacao = prob_mutacao
        self.seed = seed

    def _crossover(
        self,
        pai1: Solucao,
        pai2: Solucao,
        inst: Instancia,
        av: Avaliador,
        rng: random.Random,
    ) -> Solucao:
        """Crossover baseado em rotas para o DARP."""
        if rng.random() > self.prob_crossover:
            return pai1.copiar()

        pai1, pai2 = pai1.copiar(), pai2.copiar()
        pai1.rotas.extend(Rota() for _ in range(inst.m - len(pai1.rotas)))
        pai2.rotas.extend(Rota() for _ in range(inst.m - len(pai2.rotas)))

        # Copia uma rota aleatoria do pai 1
        k_selecionado = rng.randint(0, inst.m - 1)
        rota_herdada = pai1.rotas[k_selecionado].copiar()

        filho_rotas = [Rota() for _ in range(inst.m)]
        filho_rotas[k_selecionado] = rota_herdada

        atendidos = {inst.solicitacao_de(no) for no in rota_herdada.sequencia}
        # Preserva a ordem e a atribuicao do segundo pai nas demais rotas.
        for k, rota in enumerate(pai2.rotas):
            if k == k_selecionado:
                continue
            filho_rotas[k] = Rota([no for no in rota.sequencia
                                   if inst.solicitacao_de(no) not in atendidos])
        atendidos = {inst.solicitacao_de(no) for r in filho_rotas for no in r.sequencia}
        faltando = [i for i in inst.coletas if i not in atendidos]
        rng.shuffle(faltando)

        # Insere requisicoes restantes nas rotas mais adequadas
        sol_temp = Solucao(rotas=filho_rotas, Q=inst.Q)
        for req in faltando:
            melhor_sol = None
            melhor_custo = float("inf")
            if inst.matriz_ambiental is not None:
                melhor_custo = (float("inf"), float("inf"))

            for k in range(inst.m):
                tam = len(sol_temp.rotas[k].sequencia)
                pos_c = rng.randint(0, tam)
                pos_e = rng.randint(pos_c, tam)
                cand_rota = inserir_requisicao(sol_temp.rotas[k], req, pos_c, pos_e, inst)

                ag, viol = av.avaliar_rota(cand_rota)
                custo = av.emissao_rota(cand_rota) + len(viol) * 500.0
                if inst.matriz_ambiental is not None:
                    custo = (len(viol), av.emissao_rota(cand_rota))
                if custo < melhor_custo:
                    melhor_custo = custo
                    cand_rotas = [r.copiar() for r in sol_temp.rotas]
                    cand_rotas[k] = cand_rota
                    melhor_sol = Solucao(rotas=cand_rotas, Q=inst.Q)

            sol_temp = melhor_sol if melhor_sol is not None else sol_temp

        erros = sol_temp.conferir_estrutura(inst)
        if erros:
            return pai1.copiar()
        return sol_temp

    @staticmethod
    def _crowding(frente, populacao):
        """Distancia normalizada entre vizinhos em cada objetivo."""
        dist = {i: 0.0 for i in frente}
        for objetivo in (1, 2):
            ordem = sorted(frente, key=lambda i: populacao[i][objetivo])
            amplitude = populacao[ordem[-1]][objetivo] - populacao[ordem[0]][objetivo]
            if amplitude <= 0:
                continue
            dist[ordem[0]] = dist[ordem[-1]] = float("inf")
            for p in range(1, len(ordem) - 1):
                dist[ordem[p]] += (populacao[ordem[p + 1]][objetivo]
                                   - populacao[ordem[p - 1]][objetivo]) / amplitude
        return dist

    def _classificar_frentes(
        self,
        populacao: list[tuple[Solucao, float, float, int]],
    ) -> list[list[int]]:
        """Realiza a ordenacao rapida por dominancia de Pareto (Fast Non-Dominated Sort)."""
        num = len(populacao)
        dominados_por = [0] * num
        domina_quem: list[list[int]] = [[] for _ in range(num)]
        frentes: list[list[int]] = [[]]

        for p in range(num):
            pt_p = (populacao[p][1], populacao[p][2])
            for q in range(num):
                if p == q:
                    continue
                pt_q = (populacao[q][1], populacao[q][2])
                # Penaliza inviabilidade
                viol_p, viol_q = populacao[p][3], populacao[q][3]
                if viol_p < viol_q:
                    domina_quem[p].append(q)
                elif viol_p > viol_q:
                    dominados_por[p] += 1
                elif domina(pt_p, pt_q):
                    domina_quem[p].append(q)
                elif domina(pt_q, pt_p):
                    dominados_por[p] += 1

            if dominados_por[p] == 0:
                frentes[0].append(p)

        i = 0
        while i < len(frentes) and frentes[i]:
            proxima_frente = []
            for p in frentes[i]:
                for q in domina_quem[p]:
                    dominados_por[q] -= 1
                    if dominados_por[q] == 0:
                        proxima_frente.append(q)
            i += 1
            if proxima_frente:
                frentes.append(proxima_frente)

        return [f for f in frentes if f]

    def otimizar(
        self,
        inst: Instancia,
        av: Avaliador,
        **kwargs,
    ) -> ResultadoOtimizacao:
        inicio = time.time()
        rng = random.Random(self.seed)
        arquivo = self._arquivo
        busca = kwargs['contextos']

        # 1. Inicializacao da Populacao
        pop: list[Solucao] = []
        pop.append(busca.individual(busca.viaveis[0]))
        inicial = busca.avaliar(pop[0])
        if inicial.viavel:
            arquivo.adicionar(inicial.f1, inicial.f2, pop[0])

        # Adiciona solucoes gulosas diversificadas
        for i in range(min(self.tamanho_populacao - 1, max(2, self.tamanho_populacao // 3))):
            w = rng.random()
            pop.append(busca.construir(busca.escolher(i + 1, rng), rng, alpha=0.4, peso_f1=w))
            inicial = busca.avaliar(pop[-1])
            if inicial.viavel:
                arquivo.adicionar(inicial.f1, inicial.f2, pop[-1])

        # Completa populacao com mutacoes
        while len(pop) < self.tamanho_populacao:
            base = rng.choice(pop)
            pop.append(busca.perturbar(base, rng))

        total_avals = 0
        historico = self._historico

        for gen in range(self.geracoes):
            # Avaliacao
            avaliados = []
            for sol in pop:
                res = busca.avaliar(sol)
                total_avals += 1
                if res.viavel:
                    arquivo.adicionar(res.f1, res.f2, sol)
                avaliados.append((sol, res.f1, res.f2, len(res.violacoes)))

            # Geracao de descendentes
            descendentes: list[Solucao] = []
            while len(descendentes) < self.tamanho_populacao:
                p1 = rng.choice(pop)
                p2 = rng.choice(pop)
                # Q do pai da rota herdada define o contexto das inserções.
                if len(busca.viaveis) > 1 and rng.random() < 0.5:
                    p1, p2 = p2, p1
                contexto_inst, contexto_av = busca.obter(p1.Q)
                filho = self._crossover(p1, p2, contexto_inst, contexto_av, rng)
                filho.Q = p1.Q
                if p2.Q != p1.Q:
                    reparado = busca.mudar(filho, filho.Q, rng)
                    filho = reparado if reparado is not None else p1.copiar()
                if rng.random() < self.prob_mutacao:
                    filho = busca.perturbar(filho, rng)
                descendentes.append(filho)

            # Avalia descendentes
            desc_avaliados = []
            for sol in descendentes:
                res = busca.avaliar(sol)
                total_avals += 1
                if res.viavel:
                    arquivo.adicionar(res.f1, res.f2, sol)
                desc_avaliados.append((sol, res.f1, res.f2, len(res.violacoes)))

            # Selecao Elitista: uniao e ordenacao por frentes de Pareto
            uniao = avaliados + desc_avaliados
            frentes = self._classificar_frentes(uniao)

            nova_pop: list[Solucao] = []
            for frente in frentes:
                if len(nova_pop) + len(frente) <= self.tamanho_populacao:
                    for idx in frente:
                        nova_pop.append(uniao[idx][0])
                else:
                    # Desempate aleatorio, seguido de diversidade por crowding.
                    rng.shuffle(frente)
                    distancias = self._crowding(frente, uniao)
                    frente.sort(key=lambda i: distancias[i], reverse=True)
                    faltam = self.tamanho_populacao - len(nova_pop)
                    for idx in frente[:faltam]:
                        nova_pop.append(uniao[idx][0])
                    break

            pop = nova_pop
            historico.append({
                "geracao": gen,
                "tamanho_pareto": len(arquivo),
                "fronteira": [(p[0], p[1]) for p in arquivo.pontos],
                "agendamentos": getattr(av, "agendamentos", None),
                "tempo": time.time() - inicio,
            })

        duracao = time.time() - inicio
        return ResultadoOtimizacao(
            algoritmo=self.nome,
            fronteira=arquivo.pontos,
            tempo_execucao=duracao,
            iteracoes=self.geracoes,
            avaliacoes=total_avals,
            historico=historico,
        )
