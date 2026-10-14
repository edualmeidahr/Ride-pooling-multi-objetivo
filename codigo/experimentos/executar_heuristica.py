"""Executa a heuristica gulosa, usando a mesma entrada experimental das campanhas."""
import argparse
import csv
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from darp import Avaliador, Parametros, HeuristicaGulosa, ler_instancia_json, ler_instancia
from darp.instancia import reduzir
from darp.cenarios import cenario_capacidade
from darp.emissoes import preparar_ambiente, phi_para_q


def main():
    raiz = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=raiz / "experimentos/exemplo_pequeno.json")
    parser.add_argument("--peso-emissao", type=float, default=0.5)
    parser.add_argument("--saida", type=Path, default=raiz / "resultados/heuristica_gulosa_exemplo")
    args = parser.parse_args()
    metodo = HeuristicaGulosa(args.peso_emissao)
    c = json.loads(args.config.read_text(encoding="utf-8"))
    metodo = HeuristicaGulosa(args.peso_emissao,
        limite_pedidos=c.get("construcao", {}).get("limite_pedidos_candidatos"),
        limite_posicoes=c.get("construcao", {}).get("limite_posicoes_insercao"))
    qs = sorted(set(c["capacidades"]))
    if not qs or any(type(q) is not int or q < 1 for q in qs):
        parser.error("capacidades devem ser inteiros positivos")
    caminho = raiz / c["instancia"]
    base = ler_instancia_json(caminho, Q=min(qs)) if caminho.suffix.lower() == ".json" else ler_instancia(caminho)
    pedidos = c["pedidos"]
    if not pedidos or len(set(pedidos)) != len(pedidos) or any(type(i) is not int or not 1 <= i <= base.n for i in pedidos):
        parser.error("pedidos devem ser indices internos validos e distintos")
    if type(c["m"]) is not int or c["m"] < 1:
        parser.error("m deve ser inteiro positivo")
    inst = reduzir(base, pedidos, m=c["m"])
    if c.get("coletas_antes_de_qualquer_entrega") and min(inst.nos[i].e+inst.nos[i].s+inst.tempo(i,inst.entrega_de(i)) for i in inst.coletas) <= max(inst.nos[i].l for i in inst.coletas):
        parser.error("Entrada declarada concorrente permite entrega antes do fim das coletas")
    par_base = Parametros(**c["parametros_avaliacao"])
    ambiental = c.get("modelo_emissoes")
    ambiente = None
    if ambiental:
        inst, ambiente = preparar_ambiente(inst, json.loads(caminho.read_text(encoding="utf-8")),
                                          {**ambiental, "capacidades": qs})
    args.saida.mkdir(parents=True, exist_ok=True)
    registro = {"metodo": "heuristica_gulosa", "config": c, "peso_emissao": metodo.peso_emissao,
                "peso_tempo": 1-metodo.peso_emissao, "input_sha256": hashlib.sha256(caminho.read_bytes()).hexdigest(),
                "fontes_sha256": {str(p.relative_to(raiz)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (raiz / "codigo").rglob("*.py")},
                "unidade_f1": "g_CO2" if ambiental or par_base.phi != 1 else "km",
                "ambiente_emissoes": ambiente, "execucoes": []}
    linhas = []
    for q in qs:
        atual = cenario_capacidade(inst, q)
        par = replace(par_base, phi=phi_para_q(ambiental, q)) if ambiental else par_base
        av = Avaliador(atual, par)
        av.coletas_concorrentes = c.get("coletas_antes_de_qualquer_entrega", False)
        res = metodo.resolver(atual, av)
        ponto = None
        if res.solucao is not None:
            av = res.avaliacao
            ponto = {"f1": av.f1, "f2": av.f2, "distancia": av.distancia,
                     "espera": av.f2_espera, "desvio": av.f2_desvio, "veiculos_usados": av.veiculos_usados,
                     "carga_maxima": max((a.carga_maxima for a in av.agendas), default=0),
                     "rotas": [r.sequencia for r in res.solucao.rotas],
                     "agendas": [{"B": a.B, "partida": a.partida, "carga": a.carga} for a in av.agendas]}
        r = {"Q": q, "status": res.status, "phi_g_km": par.phi, "ponto": ponto,
             "pedidos_pendentes": res.pedidos_pendentes, "tempo_execucao": res.tempo_execucao,
             "candidatos_testados": res.candidatos_testados, "avaliacoes_rotas": res.avaliacoes_rotas,
             "historico": res.historico}
        registro["execucoes"].append(r)
        linhas.append({"Q": q, "status": res.status, "f1": ponto["f1"] if ponto else None,
                       "f2": ponto["f2"] if ponto else None,
                       "veiculos_usados": ponto["veiculos_usados"] if ponto else None,
                       "tempo_execucao": res.tempo_execucao})
        (args.saida / "execucoes.json").write_text(json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Q={q}: {res.status}" + (f"; f1={ponto['f1']:.2f}, f2={ponto['f2']:.2f}" if ponto else "; nenhuma solucao completa encontrada"), flush=True)
    with (args.saida / "metricas.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)


if __name__ == "__main__":
    main()
