"""ACO multiobjetivo propria: insercao de pares, roleta e feromonios.

Variante de Ant System com arquivo de Pareto; nao reproduz uma variante
publicada especifica. O unico solver possivel e o agendador OTIMO separado.

Origem: branch colonia-formiga. Integracao: avaliador compartilhado desta
branch, custo ambiental por rua e auditoria compativel com a rede explicita.
O agendador segue as mesmas regras de fallback dos demais metodos.
"""
from __future__ import annotations

from copy import copy, deepcopy
from dataclasses import dataclass, field, replace
import math
import random
from functools import lru_cache
from time import perf_counter

from comum.avaliador import BORDO, OTIMO, AgendaRota, Avaliador, Parametros
from comum.instancia import Instancia
from comum.pareto import domina
from comum.solucao import Rota, Solucao
from comum.validacao import verificar_solucao
from comum.capacidade import ContextoCapacidades, LimiteBusca, chave_solucao


@dataclass(frozen=True)
class ConfigACO:
    politica: str = BORDO
    seed: int = 0
    formigas: int = 20
    iteracoes: int = 100
    max_avaliacoes: int = 200_000
    limite_segundos: float | None = None
    a: float = 1.0
    b: float = 2.0
    evaporacao: float = 0.1
    tau_inicial: float = 1.0
    tau_min: float = 0.01
    tau_max: float = 10.0
    representantes: int = 20
    aprender: bool = True
    limite_posicoes_insercao: int | None = None

    def __post_init__(self):
        if self.politica not in (BORDO, OTIMO):
            raise ValueError("ACO exige politica bordo ou otimo")
        for nome in ('formigas', 'iteracoes', 'max_avaliacoes', 'representantes'):
            valor = getattr(self, nome)
            if type(valor) is not int or valor <= 0:
                raise ValueError(f"{nome} deve ser inteiro positivo")
        if self.formigas < 2 or self.representantes < 2:
            raise ValueError("usar ao menos duas formigas e dois representantes")
        if self.limite_posicoes_insercao is not None and (
                type(self.limite_posicoes_insercao) is not int or self.limite_posicoes_insercao < 2):
            raise ValueError("limite_posicoes_insercao deve ser inteiro >= 2")
        if type(self.seed) is not int or type(self.aprender) is not bool:
            raise ValueError("seed deve ser inteiro e aprender deve ser booleano")
        valores = [self.a, self.b, self.evaporacao, self.tau_min, self.tau_max, self.tau_inicial]
        if not all(math.isfinite(v) for v in valores):
            raise ValueError("parametro nao finito")
        if self.a < 0 or self.b < 0 or not 0 <= self.evaporacao <= 1:
            raise ValueError("expoentes ou evaporacao invalidos")
        if not 0 < self.tau_min <= self.tau_inicial <= self.tau_max:
            raise ValueError("limites de feromonio invalidos")
        if self.limite_segundos is not None and (
                not math.isfinite(self.limite_segundos) or self.limite_segundos <= 0):
            raise ValueError("limite de tempo deve ser positivo e finito")


@dataclass
class PontoACO:
    f1: float
    f2: float
    solucao: Solucao
    agendas: list[AgendaRota]
    peso: float

    @property
    def objetivos(self):
        return self.f1, self.f2


@dataclass
class ResultadoACO:
    fronteira: list[PontoACO] = field(default_factory=list)
    solucoes: list[PontoACO] = field(default_factory=list)
    historico: list[dict] = field(default_factory=list)
    consultas: int = 0
    acertos_cache: int = 0
    chamadas_pl: int = 0
    rejeicoes_necessarias: int = 0
    construcoes: int = 0
    fracassadas: int = 0
    interrompidas: int = 0
    tempo: float = 0.0
    motivo_parada: str = "iteracoes"
    feromonios: list[list[float]] = field(default_factory=list)
    feromonios_q: dict[int, float] = field(default_factory=dict)


def insercoes_pares(seq: list[int], coleta: int, entrega: int, limite: int | None = None):
    """Gera cada par de posicoes com precedencia, sem alterar a origem."""
    if limite is not None:
        # Importacao local evita ciclo com a fabrica de metaheuristicas.
        from comum.operadores import posicoes_insercao
        for p, d in posicoes_insercao(len(seq), limite):
            nova = list(seq)
            nova.insert(p, coleta)
            nova.insert(d + 1, entrega)
            yield nova
        return
    for p in range(len(seq) + 1):
        com_coleta = seq[:p] + [coleta] + seq[p:]
        for d in range(p + 1, len(com_coleta) + 1):
            yield com_coleta[:d] + [entrega] + com_coleta[d:]


def arcos(seq: list[int], fim: int) -> set[tuple[int, int]]:
    if not seq:
        return set()
    nos = [0, *seq, fim]
    return set(zip(nos, nos[1:]))


def capacidade_valida(inst: Instancia, seq: list[int]) -> bool:
    carga = 0
    for no in seq:
        carga += inst.nos[no].q
        if not 0 <= carga <= inst.Q:
            return False
    return carga == 0


def inviabilidade_necessaria(inst: Instancia, seq: list[int], par: Parametros) -> bool:
    """Podas seguras: atrasar horarios nao conserta chegada mais cedo tardia,
    percurso minimo a bordo excessivo ou duracao puramente fisica excessiva.
    Nao usa CEDO para rejeitar tempo a bordo, pois isso seria incorreto no DARP.
    """
    instante, comprimento, anterior = inst.nos[0].e, 0.0, 0
    prefixos = {}
    for no in seq:
        trecho, dados = inst.tempo(anterior, no), inst.nos[no]
        instante = max(instante + trecho, dados.e)
        if instante > dados.l + par.tolerancia:
            return True
        comprimento += trecho
        prefixos[no] = comprimento
        comprimento += dados.s
        instante += dados.s
        anterior = no
    saida = inst.tempo(anterior, inst.deposito_fim)
    if instante + saida > inst.nos[inst.deposito_fim].l + par.tolerancia:
        return True
    if comprimento + saida > inst.T_max + par.tolerancia:
        return True
    for i in seq:
        if i <= inst.n:
            minimo = prefixos[i + inst.n] - prefixos[i] - inst.nos[i].s
            if minimo > inst.limite_bordo(i, par.alpha) + par.tolerancia:
                return True
    return False


def probabilidades(incrementos: list[tuple[float, float]], feromonios: list[float],
                   peso: float, a: float, b: float) -> list[float]:
    if not incrementos or len(incrementos) != len(feromonios):
        raise ValueError("candidatos e feromonios inconsistentes")
    if not 0 <= peso <= 1 or a < 0 or b < 0:
        raise ValueError("peso/expoente invalido")
    if any(not math.isfinite(x) for par in incrementos for x in par) or any(
            not math.isfinite(t) or t <= 0 for t in feromonios):
        raise ValueError("incremento ou feromonio invalido")
    mins = [min(p[j] for p in incrementos) for j in (0, 1)]
    amps = [max(p[j] for p in incrementos) - mins[j] for j in (0, 1)]
    logs = []
    for delta, tau in zip(incrementos, feromonios):
        normal = [(delta[j] - mins[j]) / amps[j] if amps[j] else 0.0 for j in (0, 1)]
        custo = peso * normal[0] + (1 - peso) * normal[1]
        logs.append(a * math.log(tau) - b * math.log1p(custo))
    maior = max(logs)
    valores = [math.exp(v - maior) for v in logs]
    total = math.fsum(valores)
    return [v / total for v in valores]


def roleta(probs: list[float], rng: random.Random) -> int:
    sorteio, acumulado = rng.random(), 0.0
    for i, p in enumerate(probs):
        acumulado += p
        if sorteio < acumulado:
            return i
    return len(probs) - 1


def atualizar_arquivo(arquivo: list[PontoACO], ponto: PontoACO) -> None:
    tol = 1e-9
    for i, p in enumerate(arquivo):
        if domina(p.objetivos, ponto.objetivos):
            return
        if all(abs(x-y) <= tol for x, y in zip(p.objetivos, ponto.objetivos)):
            if chave_solucao(ponto.solucao) < chave_solucao(p.solucao):
                arquivo[i] = deepcopy(ponto)
            return
    arquivo[:] = [p for p in arquivo if not domina(ponto.objetivos, p.objetivos)]
    arquivo.append(deepcopy(ponto))
    arquivo.sort(key=lambda p: p.objetivos)


def representantes(arquivo: list[PontoACO], limite: int) -> list[PontoACO]:
    ordenados = sorted(arquivo, key=lambda p: p.objetivos)
    if len(ordenados) <= limite:
        return ordenados
    return [ordenados[i * (len(ordenados) - 1) // (limite - 1)] for i in range(limite)]


def atualizar_feromonios(tau: list[list[float]], arquivo: list[PontoACO],
                         config: ConfigACO, fim: int) -> None:
    if not config.aprender:
        return
    for linha in tau:
        for j in range(len(linha)):
            linha[j] *= 1 - config.evaporacao
    elite = representantes(arquivo, config.representantes)
    for ponto in elite:
        for rota in ponto.solucao.rotas:
            for i, j in sorted(arcos(rota.sequencia, fim)):
                tau[i][j] += 1 / len(elite)
    for linha in tau:
        for j in range(len(linha)):
            linha[j] = min(config.tau_max, max(config.tau_min, linha[j]))


class _Limite(Exception):
    def __init__(self, motivo):
        self.motivo = motivo


def resolver_aco(instancia: Instancia, parametros: Parametros | None = None,
                 config: ConfigACO | None = None, *, contextos=None, arquivo_comum=None) -> ResultadoACO:
    config = config or ConfigACO()
    par = replace(parametros or Parametros(), politica=config.politica)
    if not math.isfinite(par.phi) or par.phi <= 0 or not math.isfinite(par.tolerancia) or par.tolerancia < 0:
        raise ValueError("phi deve ser positivo e tolerancia nao negativa, ambos finitos")
    if instancia.m <= 0 or instancia.n <= 0 or instancia.Q <= 0:
        raise ValueError("instancia exige frota, pedidos e capacidade positivos")
    if config.politica == OTIMO:
        try:
            from scipy.optimize import linprog  # noqa: F401 - checa dependencia antes da busca
        except ImportError as erro:
            raise RuntimeError("ACO-OTIMO exige SciPy") from erro
    # Cache geometrico privado por execucao: nao modifica a instancia recebida
    # nem mistura estados/tempos entre sementes. O agendamento consulta muitos
    # trechos repetidos nas passadas de folga de BORDO.
    geometria = copy(instancia)
    geometria.dist = lru_cache(maxsize=None)(instancia.dist)
    geometria.tempo = lru_cache(maxsize=None)(instancia.tempo)
    contextos = contextos or ContextoCapacidades.fixo(geometria, Avaliador(geometria, par))
    if not contextos.viaveis:
        return ResultadoACO(motivo_parada='inviavel_demanda')
    if any(av.par.politica != config.politica for av in contextos.avaliadores.values()):
        raise ValueError('A politica ACO deve coincidir com a politica dos contextos')
    rng, res = random.Random(config.seed), ResultadoACO()
    inicio = perf_counter()
    tamanho = 2 * instancia.n + 2
    tau_por_q = {q: [[config.tau_inicial if config.aprender else 1.0 for _ in range(tamanho)]
                    for _ in range(tamanho)] for q in contextos.viaveis}
    tau_q = {q: config.tau_inicial if config.aprender else 1.0 for q in contextos.viaveis}
    geometria, av = contextos.obter(contextos.viaveis[0])
    tau = tau_por_q[geometria.Q]
    cache = {}

    def consultar(seq):
        if config.limite_segundos is not None and perf_counter() - inicio >= config.limite_segundos:
            raise _Limite("tempo")
        if res.consultas >= config.max_avaliacoes:
            raise _Limite("avaliacoes")
        res.consultas += 1
        chave = (geometria.Q, tuple(seq))
        if chave in cache:
            contextos.consumir()
            av.contadores['consultas_rotas'] += 1
            av.contadores['acertos_cache'] += 1
            res.acertos_cache += 1
            return cache[chave]
        if inviabilidade_necessaria(geometria, seq, par):
            contextos.consumir()
            av.contadores['consultas_rotas'] += 1
            res.rejeicoes_necessarias += 1
            entrada = None, ['inviabilidade necessaria'], (0.0, 0.0)
            cache[chave] = entrada
            return entrada
        # Usa o mesmo custo ambiental dos demais metodos, incluindo ruas.
        ag, erros = av.avaliar_rota(Rota(seq))
        res.chamadas_pl += int(config.politica == OTIMO)
        desvio, espera, _ = av.contribuicao(ag)
        entrada = ag, erros, (av.emissao_rota(Rota(seq)), desvio + espera)
        cache[chave] = entrada
        return entrada

    for it in range(config.iteracoes):
        parar = False
        for ant in range(config.formigas):
            indice = res.construcoes
            qs = contextos.viaveis
            if indice < len(qs):
                q = qs[indice]
            elif len(qs) == 1:
                q = qs[0]
            else:
                # Exploração uniforme de 10%; sem aprendizado é toda uniforme.
                total_tau = sum(tau_q.values())
                probs_q = [(0.1 / len(qs) + 0.9 * tau_q[x] / total_tau)
                           if config.aprender else 1 / len(qs) for x in qs]
                q = qs[roleta(probs_q, rng)]
            geometria, av = contextos.obter(q)
            par = av.par
            tau = tau_por_q[q]
            contextos.visitas[q] += 1
            peso = ant / (config.formigas - 1)
            pendentes = list(instancia.coletas)
            rng.shuffle(pendentes)
            rotas: list[list[int]] = []
            agendas: list[AgendaRota] = []
            objetivos: list[tuple[float, float]] = []
            res.construcoes += 1
            try:
                for pedido in pendentes:
                    candidatos, deltas, trilhas = [], [], []
                    for k in range(len(rotas) + (len(rotas) < instancia.m)):
                        anterior = rotas[k] if k < len(rotas) else []
                        obj_anterior = objetivos[k] if k < len(rotas) else (0.0, 0.0)
                        antigos = arcos(anterior, instancia.deposito_fim)
                        for seq in insercoes_pares(anterior, pedido, instancia.entrega_de(pedido),
                                                  config.limite_posicoes_insercao):
                            if not capacidade_valida(geometria, seq):
                                continue
                            ag, erros, obj = consultar(seq)
                            if erros:
                                continue
                            novos = sorted(arcos(seq, instancia.deposito_fim) - antigos)
                            trilha = math.exp(math.fsum(math.log(tau[i][j]) for i, j in novos) / len(novos))
                            candidatos.append((k, seq, ag, obj))
                            deltas.append((obj[0] - obj_anterior[0], obj[1] - obj_anterior[1]))
                            trilhas.append(trilha)
                    if not candidatos:
                        res.fracassadas += 1
                        break
                    probs = probabilidades(deltas, trilhas, peso, config.a, config.b)
                    k, seq, ag, obj = candidatos[roleta(probs, rng)]
                    if k == len(rotas):
                        rotas.append(seq)
                        agendas.append(ag)
                        objetivos.append(obj)
                    else:
                        rotas[k], agendas[k], objetivos[k] = seq, ag, obj
                else:
                    sol = Solucao([Rota(seq) for seq in rotas], Q=q)
                    av.contadores['solucoes'] += 1
                    auditoria = verificar_solucao(geometria, sol, agendas, par)
                    if not auditoria.viavel:
                        raise AssertionError(f"ACO produziu solucao invalida: {auditoria.violacoes}")
                    ponto = PontoACO(auditoria.f1, auditoria.f2, sol, agendas, peso)
                    res.solucoes.append(deepcopy(ponto))
                    atualizar_arquivo(res.fronteira, ponto)
                    if arquivo_comum is not None:
                        arquivo_comum.adicionar(ponto.f1, ponto.f2, sol)
            except (_Limite, LimiteBusca) as limite:
                res.motivo_parada = limite.motivo if isinstance(limite, _Limite) else 'consultas_rotas'
                res.interrompidas += 1
                parar = True
                break
        for capacidade, trilhas in tau_por_q.items():
            atualizar_feromonios(trilhas, [p for p in res.fronteira if p.solucao.Q == capacidade],
                                 config, instancia.deposito_fim)
        if config.aprender:
            for capacidade in tau_q:
                tau_q[capacidade] *= 1 - config.evaporacao
            elite = representantes(res.fronteira, config.representantes)
            for ponto in elite:
                tau_q[ponto.solucao.Q] += 1 / len(elite)
            tau_q = {q: min(config.tau_max, max(config.tau_min, t)) for q, t in tau_q.items()}
        res.historico.append({"iteracao": it + 1, "consultas": res.consultas,
                              "tempo": perf_counter() - inicio,
                              "fronteira": [p.objetivos for p in res.fronteira],
                              "completas": len(res.solucoes), "fracassadas": res.fracassadas,
                              "visitas_q": dict(contextos.visitas), "feromonios_q": dict(tau_q)})
        if parar:
            break
    res.tempo = perf_counter() - inicio
    res.feromonios = tau
    res.feromonios_q = tau_q
    return res
