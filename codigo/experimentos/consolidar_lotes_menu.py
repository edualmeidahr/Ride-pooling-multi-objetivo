"""Reune lotes concluidos de capacidades distintas, sem executar metodos novamente."""
import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from menu import salvar


def consolidar(pastas, destino):
    lotes = [json.loads((p / "execucoes.json").read_text(encoding="utf-8")) for p in pastas]
    base = deepcopy(lotes[0])
    base.update(execucoes=[], referencias={}, lotes=[])
    capacidades, vistos = set(), set()
    for pasta, d in zip(pastas, lotes):
        if not d["concluida"] or d["config"] != base["config"] or d["input_sha256"] != base["input_sha256"]:
            raise ValueError("Lotes incompletos ou com entradas/configuracoes diferentes")
        for k in ("modo", "metodos", "seed", "peso_emissao"):
            if d["opcoes"][k] != base["opcoes"][k]:
                raise ValueError(f"Opcoes diferentes: {k}")
        for r in d["execucoes"]:
            chave = (r["Q"],r["metodo"])
            if chave in vistos:
                raise ValueError(f"Execucao duplicada: {chave}")
            vistos.add(chave)
            base["execucoes"].append(r)
        for q, ref in d["referencias"].items():
            if q in base["referencias"]:
                raise ValueError("Cada Q deve estar integralmente em um lote")
            base["referencias"][q] = ref
        capacidades.update(d["opcoes"]["capacidades"])
        base["lotes"].append({"pasta": str(pasta), "opcoes": d["opcoes"], "fontes_sha256": d["fontes_sha256"]})
        if d["ambiente_emissoes"]:
            for k in ("fatores_arestas", "matriz_ambiental"):
                if d["ambiente_emissoes"][k] != base["ambiente_emissoes"][k]:
                    raise ValueError("Lotes com ruas/caminhos diferentes")
            base["ambiente_emissoes"]["phi_por_q"].update(d["ambiente_emissoes"]["phi_por_q"])
    base["opcoes"]["capacidades"] = sorted(capacidades)
    if base["ambiente_emissoes"]:
        base["ambiente_emissoes"]["config"]["capacidades"] = sorted(capacidades)
    if vistos != {(q,m) for q in capacidades for m in base["opcoes"]["metodos"]}:
        raise ValueError("Faltam execucoes")
    base["execucoes"].sort(key=lambda r: (r["Q"],base["opcoes"]["metodos"].index(r["metodo"])))
    salvar(destino, base)
    print(f"{len(base['execucoes'])} execucoes consolidadas em {destino}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pastas", nargs="+", type=Path)
    p.add_argument("--saida", required=True, type=Path)
    a = p.parse_args()
    consolidar(a.pastas, a.saida)
