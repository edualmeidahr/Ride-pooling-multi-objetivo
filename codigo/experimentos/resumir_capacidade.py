"""Resume fronteiras exatas de capacidade e gera figura com eixos comuns."""
import argparse
import csv
import json
import os
from pathlib import Path


def main():
    raiz = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pastas", type=Path, nargs="*", default=[raiz / "resultados/capacidade_q"])
    args = parser.parse_args()
    os.environ.setdefault("MPLCONFIGDIR", str(raiz / ".cache/matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for pasta in args.pastas:
        dados = json.loads((pasta / "fronteiras.json").read_text(encoding="utf-8"))
        linhas, assinaturas = [], set()
        for c in dados["cenarios"]:
            pontos = c["pontos"]
            assinatura = tuple((round(p["f1"], 6), round(p["f2"], 6)) for p in pontos)
            assinaturas.add(assinatura)
            linhas.append({"Q": c["Q"], "status": c["status"], "pontos": len(pontos),
                           "min_f1": min((p["f1"] for p in pontos), default=None),
                           "min_f2": min((p["f2"] for p in pontos), default=None),
                           "carga_maxima": max((p["carga_maxima"] for p in pontos), default=None)})
        with (pasta / "resumo.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(linhas[0]))
            writer.writeheader()
            writer.writerows(linhas)
        print(f"{pasta.name}: {len(assinaturas)} fronteiras distintas em {len(linhas)} valores de Q")
        label = f"m={dados['m']}, alpha={dados['alpha']}"
        axes[0].plot([p["Q"] for p in linhas], [p["min_f1"] for p in linhas], "o-", label=label)
        axes[1].plot([p["Q"] for p in linhas],
                     [0.0 if p["min_f2"] is not None and abs(p["min_f2"]) < 1e-6
                      else p["min_f2"] for p in linhas], "o-", label=label)
    for ax, titulo in zip(axes, ("Menor distância da fronteira", "Menor tempo perdido da fronteira")):
        ax.set_title(titulo)
        ax.set_xlabel("Q (passageiros simultâneos)")
        ax.grid(alpha=0.3)
        ax.legend()
        ax.set_xticks([1, 4, 8, 12, 16, 20])
    axes[0].set_ylabel("Distância (unidades da instância)")
    axes[1].set_ylabel("Passageiro-minutos")
    fig.suptitle("Sensibilidade de capacidade — pr01, pedidos 13 a 17")
    fig.tight_layout()
    fig.savefig(raiz / "resultados/capacidade_q_comparativo.png", dpi=160)


if __name__ == "__main__":
    main()
