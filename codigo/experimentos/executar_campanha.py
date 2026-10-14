"""Executa Q x sementes x metodos, com referencia exata ou empirica e registro reproduzivel."""
import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
import time
from dataclasses import replace
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from darp import Avaliador, Parametros, ler_instancia, ler_instancia_json, obter_metaheuristica
from darp.cenarios import cenario_capacidade
from darp.exato import fronteira_exata
from darp.instancia import reduzir
from darp.pareto import normalizar, hipervolume, filtrar
from darp.emissoes import preparar_ambiente, phi_para_q
from resumir_campanha import gerar_resumos


class AvaliadorInstrumentado(Avaliador):
    """Conta todo agendamento de rota nao vazia, inclusive na construcao/cruzamento."""
    def __init__(self, inst, par, cache_agendas=False):
        super().__init__(inst, par)
        self.agendamentos = 0
        self.resolucoes_agendamento = 0
        self.cache_hits = 0
        self.cache_agendas = cache_agendas
        self._cache = {}

    def agendar(self, rota, partida=None, politica=None):
        if rota.usada:
            self.agendamentos += 1
        chave = (tuple(rota.sequencia), partida, politica or self.par.politica)
        if self.cache_agendas and chave in self._cache:
            if rota.usada:
                self.cache_hits += 1
            return deepcopy(self._cache[chave])
        if rota.usada:
            self.resolucoes_agendamento += 1
        agenda = super().agendar(rota, partida, politica)
        if self.cache_agendas:
            self._cache[chave] = deepcopy(agenda)
        return agenda


def main():
    raiz = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=raiz / "experimentos/comparacao_q1_10.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    capacidades = sorted(set(config["capacidades"]))
    sementes = config["sementes"]
    if not capacidades or any(type(q) is not int or q < 1 for q in capacidades):
        parser.error("capacidades devem ser inteiros positivos")
    if not sementes or len(set(sementes)) != len(sementes) or any(type(s) is not int for s in sementes):
        parser.error("sementes devem ser inteiros distintos")
    caminho = raiz / config["instancia"]
    base = (ler_instancia_json(caminho, Q=min(capacidades)) if caminho.suffix == ".json"
            else ler_instancia(caminho))
    pedidos = config["pedidos"]
    tipo_referencia = config.get("referencia", "exata")
    if tipo_referencia not in ("exata", "empirica"):
        parser.error("referencia deve ser exata ou empirica")
    if not pedidos or len(set(pedidos)) != len(pedidos) or any(type(i) is not int or not 1 <= i <= base.n for i in pedidos):
        parser.error("pedidos devem ser indices internos validos e distintos")
    if tipo_referencia == "exata" and len(pedidos) > 6:
        parser.error("enumeracao exata limitada a seis pedidos; use referencia empirica para instancias maiores")
    inst = reduzir(base, pedidos, m=config["m"])
    if config.get("coletas_antes_de_qualquer_entrega", False):
        fim_coletas = max(inst.nos[i].l for i in inst.coletas)
        primeira_entrega = min(inst.nos[i].e + inst.nos[i].s + inst.tempo(i,inst.entrega_de(i)) for i in inst.coletas)
        if primeira_entrega <= fim_coletas:
            parser.error("cenario declarado concorrente permite entrega antes do fim das coletas")
    par = Parametros(**config["parametros_avaliacao"])
    if par.politica != "otimo":
        parser.error("campanha com gabarito exige politica otimo para todos os metodos")
    ambiental = config.get("modelo_emissoes")
    ambiente = None
    if ambiental:
        inst, ambiente = preparar_ambiente(inst, json.loads(caminho.read_text(encoding="utf-8")),
                                          {**ambiental, "capacidades": capacidades})
    if par.phi != 1 and not ambiental:
        parser.error("graficos desta campanha usam distancia: mantenha phi=1")
    saida = raiz / config["saida"]
    saida.mkdir(parents=True, exist_ok=True)
    registro = {"config": config, "input_sha256": hashlib.sha256(caminho.read_bytes()).hexdigest(),
                "python": platform.python_version(),
                "dependencias": {n: importlib.metadata.version(n) for n in ("numpy", "scipy", "matplotlib")},
                "fontes_sha256": {str(p.relative_to(raiz)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (raiz / "codigo").rglob("*.py")},
                "tipo_referencia": tipo_referencia, "referencias": {}, "execucoes": []}
    if ambiente:
        registro["ambiente_emissoes"] = ambiente
        (saida / "ambiente_emissoes.json").write_text(json.dumps(ambiente, indent=2), encoding="utf-8")
    demanda = sum(inst.nos[i].q for i in inst.coletas)
    if config.get("coletas_antes_de_qualquer_entrega", False):
        registro["concorrencia"] = {"passageiros": demanda, "fim_coletas": fim_coletas,
                                   "primeira_entrega_limite_inferior": primeira_entrega}
    cache, anterior = {}, []
    for Q in capacidades:
        atual = cenario_capacidade(inst, Q)
        if ambiental:
            par = replace(par, phi=phi_para_q(ambiental, Q))
        efetivo = min(Q, demanda)
        chave_exata = (efetivo, par.phi)
        if tipo_referencia == "exata" and chave_exata not in cache:
            t0 = time.perf_counter()
            frente = fronteira_exata(atual, Avaliador(atual, par))
            cache[chave_exata] = {"pontos": [[f1, f2] for f1, f2, _ in frente],
                              "tempo_enumeracao": time.perf_counter() - t0,
                              "rotas": [[r.sequencia for r in sol.rotas] for _, _, sol in frente]}
        if tipo_referencia == "exata":
            referencia = cache[chave_exata]
            for a in (anterior if not ambiental else []):
                if not any(p[0] <= a[0] + 1e-6 and p[1] <= a[1] + 1e-6 for p in referencia["pontos"]):
                    raise AssertionError("fronteira exata viola inclusao por capacidade")
            anterior = referencia["pontos"]
            registro["referencias"][str(Q)] = referencia
        for nome, parametros in config["algoritmos"].items():
            for seed in sementes:
                av = AvaliadorInstrumentado(atual, par, cache_agendas=config.get("cache_agendas", False))
                av.limite_pedidos_construcao = config.get("construcao", {}).get("limite_pedidos_candidatos")
                av.limite_posicoes_construcao = config.get("construcao", {}).get("limite_posicoes_insercao")
                av.coletas_concorrentes = config.get("coletas_antes_de_qualquer_entrega", False)
                metodo = obter_metaheuristica(nome, seed=seed, **parametros)
                t0 = time.perf_counter()
                res = metodo.otimizar(atual, av)
                tempo_busca = time.perf_counter() - t0
                calls = av.agendamentos
                pontos = []
                validador = Avaliador(atual, par)
                for f1, f2, sol in res.fronteira:
                    calculado = validador.avaliar(sol)
                    if not calculado.viavel or abs(calculado.f1 - f1) > 1e-6 or abs(calculado.f2 - f2) > 1e-6:
                        raise AssertionError("fronteira retornou ponto inconsistente")
                    pontos.append({"f1": f1, "f2": f2, "rotas": [r.sequencia for r in sol.rotas],
                                   "distancia": calculado.distancia,
                                   "agendas": [{"B": a.B, "partida": a.partida, "carga": a.carga} for a in calculado.agendas],
                                   "desvio": calculado.f2_desvio, "espera": calculado.f2_espera,
                                   "veiculos_usados": calculado.veiculos_usados,
                                   "carga_maxima": max((a.carga_maxima for a in calculado.agendas), default=0)})
                if not pontos:
                    raise AssertionError(f"nenhuma solucao viavel: Q={Q}, metodo={nome}, seed={seed}")
                registro["execucoes"].append({"Q": Q, "metodo": nome, "seed": seed,
                    "phi_g_km": par.phi,
                    "tempo_busca": tempo_busca, "agendamentos": calls,
                    "resolucoes_agendamento": av.resolucoes_agendamento, "cache_hits": av.cache_hits,
                    "avaliacoes_reportadas_metodo": res.avaliacoes, "pontos": pontos, "historico": res.historico})
                print(f"Q={Q:2} {nome:5} seed={seed:4}: {len(pontos)} pontos, {calls} rotas, {tempo_busca:.2f}s", flush=True)
        # Checkpoint para preservar as execucoes em caso de interrupcao.
        (saida / "execucoes.json").write_text(json.dumps(registro, indent=2), encoding="utf-8")
    if tipo_referencia == "empirica":
        # Uniao nao dominada de TODOS os metodos e sementes. Nao prova otimalidade.
        for Q in capacidades:
            pontos_q = [(p["f1"],p["f2"]) for r in registro["execucoes"] if r["Q"] == Q for p in r["pontos"]]
            registro["referencias"][str(Q)] = {"pontos": [list(p) for p in filtrar(pontos_q,tol=1e-6)]}
    todos = [p for r in registro["referencias"].values() for p in r["pontos"]]
    todos += [(p["f1"], p["f2"]) for r in registro["execucoes"] for p in r["pontos"]]
    registro["normalizacao"] = {"min": [min(p[i] for p in todos) for i in (0, 1)],
                                "max": [max(p[i] for p in todos) for i in (0, 1)],
                                "referencia_hv": [1.1, 1.1]}
    def hv(pontos):
        return hipervolume(normalizar(pontos, todos), referencia=(1.1, 1.1))
    for r in registro["execucoes"]:
        pts = [(p["f1"], p["f2"]) for p in r["pontos"]]
        exatos = registro["referencias"][str(r["Q"])]["pontos"]
        hv_exato = hv(exatos)
        hv_atual = hv(pts)
        if hv_atual > hv_exato + 1e-6:
            raise AssertionError("hipervolume da heuristica ultrapassa referencia")
        nome_hv = "hv_exato" if tipo_referencia == "exata" else "hv_referencia"
        nome_recuperacao = "recuperacao_exata" if tipo_referencia == "exata" else "recuperacao_referencia"
        metricas = {"hv": hv_atual, "hv_exato": hv_exato,
                    "hv_relativo": hv_atual / hv_exato if hv_exato else None,
                    "recuperacao_exata": sum(any(max(abs(a-b) for a,b in zip(e,p)) < 1e-6 for p in pts)
                                                for e in exatos) / len(exatos) if exatos else None,
                    "cardinalidade": len(pts), "min_f1": min((p[0] for p in pts), default=None),
                    "min_f2": min((p[1] for p in pts), default=None)}
        if tipo_referencia == "empirica":
            metricas[nome_hv] = metricas.pop("hv_exato")
            metricas[nome_recuperacao] = metricas.pop("recuperacao_exata")
        r["metricas"] = metricas
        for h in r["historico"]:
            h["hv_relativo"] = hv(h["fronteira"]) / hv_exato if hv_exato else None
    (saida / "execucoes.json").write_text(json.dumps(registro, indent=2), encoding="utf-8")
    gerar_resumos(saida, registro)
    print(f"Campanha completa: {len(registro['execucoes'])} execucoes em {saida}")


if __name__ == "__main__":
    main()
