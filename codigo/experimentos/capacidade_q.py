"""Gabarito exato por Q=1..20; guarda rotas, objetivos e parametros em JSON/CSV."""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from darp import Avaliador, Parametros, OTIMO, ler_instancia, ler_instancia_json
from darp.cenarios import cenario_capacidade
from darp.exato import fronteira_exata
from darp.instancia import reduzir


def main():
    raiz = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instancia", type=Path, default=raiz / "dados/tabu/pr01")
    parser.add_argument("--pedidos", type=int, nargs="+", default=[13, 14, 15, 16, 17])
    parser.add_argument("--m", type=int, default=5)
    parser.add_argument("--alpha", type=float, default=2.0)
    parser.add_argument("--q", type=int, nargs="+", default=list(range(1, 21)))
    parser.add_argument("--saida", type=Path, default=raiz / "resultados/capacidade_q")
    args = parser.parse_args()
    if args.alpha < 1:
        parser.error("alpha deve ser >= 1")
    if not args.q or any(isinstance(q, bool) or q < 1 for q in args.q):
        parser.error("capacidades devem ser inteiros positivos")
    base = (ler_instancia_json(args.instancia, Q=min(args.q)) if args.instancia.suffix == ".json"
            else ler_instancia(args.instancia))
    if len(set(args.pedidos)) != len(args.pedidos):
        parser.error("pedidos repetidos")
    if len(args.pedidos) > 6:
        parser.error("enumeracao restrita a ate seis pedidos; use metaheuristicas para instancias maiores")
    inst = reduzir(base, args.pedidos, m=args.m)
    par = Parametros(alpha=args.alpha, phi=1.0, politica=OTIMO)
    saida = {"instancia": str(args.instancia.resolve()), "pedidos": args.pedidos,
             "m": args.m, "alpha": args.alpha, "phi": par.phi, "politica": OTIMO,
             "escopo": "passageiros", "cenarios": []}
    linhas, cache, anteriores = [], {}, []
    demanda = sum(inst.nos[i].q for i in inst.coletas)
    for Q in sorted(set(args.q)):
        atual = cenario_capacidade(inst, Q)
        # Acima da demanda total a restricao de capacidade e redundante.
        efetivo = min(Q, demanda)
        if efetivo not in cache:
            cache[efetivo] = fronteira_exata(atual, Avaliador(atual, par), politica=OTIMO)
        frente = cache[efetivo]
        pontos = []
        for f1, f2, sol in sorted(frente, key=lambda p: p[:2]):
            res = Avaliador(atual, par).avaliar(sol)
            assert res.viavel and abs(res.f1 - f1) < 1e-6 and abs(res.f2 - f2) < 1e-6
            pontos.append({"f1": f1, "f2": f2, "rotas": [r.sequencia for r in sol.rotas],
                           "partidas": [a.partida for a in res.agendas],
                           "horarios": [a.B for a in res.agendas],
                           "carga_maxima": max(a.carga_maxima for a in res.agendas)})
            linhas.append({"Q": Q, "m": args.m, "alpha": args.alpha, "f1": f1, "f2": f2})
        # Cada ponto viavel com Q menor deve ser igualado ou dominado com Q maior.
        assert all(any(p[0] <= a[0] + 1e-6 and p[1] <= a[1] + 1e-6 for p in frente)
                   for a in anteriores), "violacao da inclusao dos conjuntos viaveis"
        anteriores = frente
        saida["cenarios"].append({"Q": Q, "status": "viavel" if frente else "inviavel",
                                   "pontos": pontos})
        print(f"Q={Q:2}: {len(frente)} pontos", flush=True)
    args.saida.mkdir(parents=True, exist_ok=True)
    (args.saida / "fronteiras.json").write_text(json.dumps(saida, indent=2), encoding="utf-8")
    with (args.saida / "fronteiras.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Q", "m", "alpha", "f1", "f2"])
        writer.writeheader()
        writer.writerows(linhas)


if __name__ == "__main__":
    main()
