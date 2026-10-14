"""Figuras de solucoes pareadas do menu: fronteiras, compromissos e esforco."""
import argparse
import csv
import json
import os
from pathlib import Path
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[2] / ".cache/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def gerar(pasta):
    d = json.loads((pasta / "execucoes.json").read_text(encoding="utf-8"))
    if not d["concluida"]:
        raise ValueError("Execucao incompleta")
    qs = d["opcoes"]["capacidades"]
    metodos = d["opcoes"]["metodos"]
    cores = {"sa": "#0072b2", "ga": "#d55e00", "grasp": "#009e73", "gulosa": "#7b3294", "exato": "#222222"}
    marcadores = {"sa": "o", "ga": "s", "grasp": "^", "gulosa": "D", "exato": "x"}
    fator = 1000 if d["unidade_f1"] == "g_CO2" else 1
    unidade = "CO₂ estimado (kg)" if fator == 1000 else "Distância (km)"
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.alpha": 0.2, "savefig.facecolor": "white"})
    destino = pasta / "graficos"
    destino.mkdir(exist_ok=True)
    def salvar(fig,nome):
        fig.savefig(destino / f"{nome}.png",dpi=150,bbox_inches="tight")
        fig.savefig(destino / f"{nome}.svg",bbox_inches="tight")
        plt.close(fig)
    escolhidos = [1,3,6,10] if all(q in qs for q in [1,3,6,10]) else list(dict.fromkeys([qs[0], qs[len(qs)//3], qs[2*len(qs)//3], qs[-1]]))
    fig,axs = plt.subplots(2,2,figsize=(12,9),sharex=True,sharey=True)
    fig.suptitle(f"{len(d['config']['pedidos'])} corridas: emissão e serviço",fontsize=17)
    for ax,q in zip(axs.flat,escolhidos):
        ref = d["referencias"][str(q)]["pontos"]
        ax.plot([p[0]/fator for p in ref],[p[1] for p in ref],"--",color="#777777",label="Referência observada")
        for r in d["execucoes"]:
            if r["Q"] != q:
                continue
            pts = sorted(r["pontos"],key=lambda p:p["f1"])
            ax.plot([p["f1"]/fator for p in pts],[p["f2"] for p in pts],
                    color=cores[r["metodo"]],marker=marcadores[r["metodo"]],label=r["metodo"].upper(),markersize=4)
        ax.set_title(f"Q={q}",loc="left")
        ax.set_xlabel(unidade)
        ax.set_ylabel("Tempo perdido (passageiro-minutos)")
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
    for ax in list(axs.flat)[len(escolhidos):]:
        ax.set_visible(False)
    handles,labels=axs.flat[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="lower center",ncol=len(labels),frameon=False)
    fig.tight_layout(rect=(0,0.06,1,0.94))
    salvar(fig,"01_fronteiras")
    with (pasta / "metricas.csv").open(encoding="utf-8-sig") as f:
        linhas = list(csv.DictReader(f))
    fig,axs=plt.subplots(1,2,figsize=(12,5))
    fig.suptitle("Soluções reais selecionadas: os dois painéis descrevem o mesmo par",fontsize=14)
    for m in metodos:
        rs = [next(r for r in linhas if int(r["Q"])==q and r["metodo"]==m) for q in qs]
        for ax,campo,divisor in [(axs[0],"f1",fator),(axs[1],"f2",1)]:
            ax.plot(qs,[float(r[campo])/divisor if r[campo] else float("nan") for r in rs],
                    color=cores[m],marker=marcadores[m],label=m.upper())
            ax.set_xlabel("Capacidade Q")
            ax.set_xticks(qs)
            ax.set_ylim(bottom=0)
    axs[0].set_ylabel(unidade)
    axs[1].set_ylabel("Tempo perdido (passageiro-minutos)")
    axs[1].legend(frameon=False)
    fig.tight_layout(rect=(0,0,1,0.90))
    salvar(fig,"02_compromissos_pareados")
    fig,axs=plt.subplots(1,2,figsize=(12,5))
    fig.suptitle("Tempo de busca e uso da frota",fontsize=16)
    for m in metodos:
        rs=[next(r for r in linhas if int(r["Q"])==q and r["metodo"]==m) for q in qs]
        for ax,campo in [(axs[0],"tempo_busca_s"),(axs[1],"veiculos_usados")]:
            ax.plot(qs,[float(r[campo]) if r[campo] else float("nan") for r in rs],
                    color=cores[m],marker=marcadores[m],label=m.upper())
            ax.set_xlabel("Capacidade Q")
            ax.set_xticks(qs)
    axs[0].set_yscale("log")
    axs[0].set_ylabel("Tempo de busca (segundos, escala log)")
    axs[1].set_ylabel("Veículos na solução selecionada")
    axs[1].set_ylim(bottom=0)
    axs[1].legend(frameon=False)
    fig.tight_layout(rect=(0,0,1,0.90))
    salvar(fig,"03_tempo_frota")
    texto = ["# Gráficos do experimento", "",
        "Uma execução por método/Q, sem faixa estatística. Fatores sintéticos; referência empírica, sem prova de ótimo.", "",
        "## 1. Fronteiras", "", "Cada ponto é uma solução completa. Menor emissão e menor tempo perdido são preferíveis. "
        "Linhas apenas conectam alternativas discretas. Escalas comuns entre painéis.", "", "![Fronteiras](graficos/01_fronteiras.png)", "",
        "## 2. Compromissos pareados", "", "Os valores dos dois painéis pertencem à mesma solução de cada método/Q, "
        "selecionada pelo critério de equilíbrio documentado em RESUMO.md. Não são mínimos independentes.", "",
        "![Compromissos](graficos/02_compromissos_pareados.png)", "",
        "## 3. Tempo e frota", "", "Tempo da busca, sem conferência posterior, com eixo logarítmico. "
        "Veículos usados pela mesma solução do gráfico 2. Métodos têm esforços diferentes; tempo isolado não prova eficiência.", "",
        "![Tempo e frota](graficos/03_tempo_frota.png)", "", "[Resumo](RESUMO.md) · [Soluções completas](solucoes.csv)"]
    (pasta / "GUIA_RESULTADOS.md").write_text("\n".join(texto)+"\n",encoding="utf-8")
    print(f"3 figuras PNG/SVG e guia em {pasta}")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("pasta",type=Path)
    gerar(p.parse_args().pasta)
