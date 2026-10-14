"""Modelo sintetico de emissoes em caminhos fisicos, com aleatoriedade fixa."""
import heapq
import math
import random
from dataclasses import replace


def numero(valor, nome):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor <= 0:
        raise ValueError(f"{nome}: esperado numero positivo finito")
    return float(valor)


def phi_para_q(config, q):
    encontrados = []
    for perfil in config["veiculos"]:
        lo, hi = perfil["q_min"], perfil["q_max"]
        if type(lo) is not int or type(hi) is not int or not 1 <= lo <= hi:
            raise ValueError("faixa Q invalida")
        if lo <= q <= hi:
            encontrados.append(numero(perfil["phi_g_km"], "phi_g_km"))
    if len(encontrados) != 1:
        raise ValueError(f"Q={q}: exige exatamente um tipo de veiculo")
    return encontrados[0]


def escalas_busca(inst, av):
    """Escalas fixas por execucao ambiental, independentes de g versus kg."""
    from .solucao import solucao_individual
    f1 = av.avaliar(solucao_individual(inst)).f1
    f2 = sum(inst.nos[i].q * (max(0, inst.nos[i].l - inst.rho[i])
             + max(0, inst.limite_bordo(i, av.par.alpha) - inst.t_direto(i)))
             for i in inst.coletas)
    return max(1e-12, f1), max(1.0, f2)


def preparar_ambiente(inst, entrada, config):
    """Soma d*r ao longo do caminho minimo de distancia ja usado pela rede.

    Exige que seu tempo coincida com a matriz temporal: evita inventar um
    caminho ambiental diferente daquele percorrido. Nao otimiza caminhos por CO2.
    """
    rede = entrada.get("rede", {})
    if inst.rede is None or not rede.get("arestas"):
        raise ValueError("modelo ambiental exige rede com arestas explicitas")
    ruas = config["ruas"]
    seed = ruas["seed"]
    if type(seed) is not int:
        raise ValueError("ruas.seed deve ser inteiro")
    lo = numero(ruas["fator_min"], "fator_min")
    hi = numero(ruas["fator_max"], "fator_max")
    if lo > hi:
        raise ValueError("fator_min maior que fator_max")
    rng = random.Random(seed)
    adj = {i: [] for i in inst.rede.nos_fixos}
    fatores = []
    dirigido = rede.get("direcionado", False)
    # Ordenacao torna a geracao independente da ordem das arestas no JSON.
    arestas = sorted(rede["arestas"], key=lambda a: (a["origem"], a["destino"]) if dirigido
                     else tuple(sorted((a["origem"], a["destino"]))))
    for a in arestas:
        u, v = a["origem"], a["destino"]
        d = a["distancia"]
        t = a.get("tempo", d)  # mesma convencao do leitor de arestas JSON
        fator = rng.uniform(lo, hi)
        fatores.append({"origem": u, "destino": v, "distancia": d, "fator": fator})
        adj[u].append((v, d, t, d * fator))
        if not dirigido:
            adj[v].append((u, d, t, d * fator))
    matriz = {}
    caminhos = []
    for inicio in sorted(adj):
        dist = {inicio: 0.0}
        tempos, ambiental, paths = {inicio: 0.0}, {inicio: 0.0}, {inicio: [inicio]}
        fila = [(0.0, inicio)]
        while fila:
            d, u = heapq.heappop(fila)
            if d != dist[u]:
                continue
            for v, trecho, t, custo in sorted(adj[u]):
                novo = d + trecho
                if novo < dist.get(v, math.inf):
                    dist[v] = novo
                    tempos[v] = tempos[u] + t
                    ambiental[v] = ambiental[u] + custo
                    paths[v] = paths[u] + [v]
                    heapq.heappush(fila, (novo, v))
        for fim in sorted(adj):
            if fim not in dist or abs(dist[fim] - inst.rede.dist(inicio, fim)) > 1e-6:
                raise ValueError("caminho ambiental inconsistente com distancia")
            if abs(tempos[fim] - inst.rede.tempo(inicio, fim)) > 1e-6:
                raise ValueError("distancia e tempo usam caminhos diferentes; harmonize a rede antes de simular emissoes")
            matriz[(inicio, fim)] = ambiental[fim]
            caminhos.append({"origem": inicio, "destino": fim, "caminho": paths[fim],
                             "distancia": dist[fim], "distancia_ponderada": ambiental[fim]})
    registro = {"unidade_f1": "g_CO2", "config": config,
                "fatores_arestas": fatores, "matriz_ambiental": caminhos,
                "phi_por_q": {str(q): phi_para_q(config, q) for q in config.get("capacidades", [inst.Q])}}
    return replace(inst, matriz_ambiental=matriz), registro
