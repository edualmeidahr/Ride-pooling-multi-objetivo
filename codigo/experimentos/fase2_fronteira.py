#!/usr/bin/env python3
"""Fase 2: fronteira exata de referencia e pontos extremos.

Produz o gabarito contra o qual as metaheuristicas serao medidas, por dois
caminhos independentes que servem de conferencia mutua.

Enumeracao. Percorre todas as rotas viaveis de cada subconjunto de
solicitacoes, agenda cada uma pela politica indicada e combina os subconjuntos
por particao. Usa o avaliador do projeto.

Solver. Resolve a formulacao da Secao 3.2 do relatorio no Gurobi pelo metodo
epsilon-restrito. As restricoes sao transcritas do texto, sem passar pelo
avaliador, de modo que a coincidencia das duas fronteiras indica que o modelo
escrito e o modelo implementado sao o mesmo.

Tambem mede o efeito da politica de agendamento, comparando a fronteira obtida
com agendamento otimo (programacao linear) contra a heuristica de reducao de
tempo a bordo.
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from darp import (BORDO, OTIMO, Avaliador, Parametros, ler_instancia, ler_res,
                  pareto, solucao_individual)
from darp.exato import fronteira_exata
from darp.instancia import reduzir

RAIZ = Path(__file__).resolve().parents[2]
DADOS = RAIZ / "dados"
SAIDA = RAIZ / "resultados"
SAIDA.mkdir(exist_ok=True)

PEDIDOS = [1, 2, 3, 4, 5]   # 5 solicitacoes: 2 de volta e 3 de ida em pr01
TOL = 1e-3


def salvar_csv(caminho: Path, linhas: list[dict]) -> None:
    if not linhas:
        return
    with caminho.open("w", newline="") as fh:
        escritor = csv.DictWriter(fh, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)
    print(f"  gravado: {caminho.relative_to(RAIZ)}")


def grafico(caminho: Path, series: dict[str, list[tuple[float, float]]]) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib ausente: grafico nao gerado")
        return

    fig, ax = plt.subplots(figsize=(7, 4.6))
    estilos = [("o-", "#1f3b73"), ("s--", "#c0392b"), ("^:", "#7f8c8d")]
    for (rotulo, pontos), (marca, cor) in zip(series.items(), estilos):
        ordenados = sorted(pontos)
        ax.plot([p[0] for p in ordenados], [p[1] for p in ordenados],
                marca, color=cor, label=rotulo, markersize=6, linewidth=1.5)

    ax.set_xlabel(r"$f_1$ — distância percorrida (proporcional à emissão de CO$_2$)")
    ax.set_ylabel(r"$f_2$ — tempo perdido pelo usuário (passageiro-minuto)")
    ax.set_title("Fronteira de Pareto exata — pr01 reduzida a 5 solicitações")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(caminho, dpi=150)
    print(f"  gravado: {caminho.relative_to(RAIZ)}")


falhas = 0


def conferir(rotulo: str, ok: bool, detalhe: str = "") -> None:
    global falhas
    if not ok:
        falhas += 1
    print(f"  [{'ok  ' if ok else 'FALHA'}] {rotulo}{'  ' + detalhe if detalhe else ''}")


# ----------------------------------------------------------------------
print("=" * 78)
print("FASE 2 - FRONTEIRA EXATA DE REFERENCIA")
print("=" * 78)

base = ler_instancia(DADOS / "tabu" / "pr01")
inst = reduzir(base, PEDIDOS, m=len(PEDIDOS))
par = Parametros(phi=1.0)
av = Avaliador(inst, par)

print(f"\nInstancia reduzida: {inst.resumo()}")
print(f"Solicitacoes originais mantidas: {PEDIDOS}")

# --- enumeracao com agendamento otimo ---
print("\n1. Enumeracao com agendamento otimo (programacao linear)")
inicio = time.time()
frente_otimo = fronteira_exata(inst, av, politica=OTIMO)
tempo_otimo = time.time() - inicio
print(f"   {len(frente_otimo)} pontos em {tempo_otimo:.2f}s")

# --- enumeracao com agendamento heuristico ---
print("\n2. Enumeracao com agendamento heuristico (reducao de tempo a bordo)")
inicio = time.time()
frente_bordo = fronteira_exata(inst, av, politica=BORDO)
tempo_bordo = time.time() - inicio
print(f"   {len(frente_bordo)} pontos em {tempo_bordo:.2f}s")

# --- solver ---
print("\n3. Solver: formulacao do relatorio pelo metodo epsilon-restrito")
pontos_mip, frente_mip = [], []
try:
    from darp.mip import SolverIndisponivel, fronteira_epsilon

    inicio = time.time()
    pontos_mip = fronteira_epsilon(inst, par, max_pontos=40, limite_tempo=60)
    frente_mip = [(p.f1, p.f2) for p in pontos_mip]
    print(f"   {len(frente_mip)} pontos em {time.time() - inicio:.2f}s")
except SolverIndisponivel as erro:
    print(f"   indisponivel: {erro}")
except ImportError as erro:
    print(f"   indisponivel: {erro}")
except Exception as erro:
    # O Gurobi lança GurobiError (licença ausente, expirada ou host incompatível)
    # apenas em tempo de execução, sem classe importável quando falta o pacote.
    if type(erro).__name__ != "GurobiError":
        raise
    print(f"   licenca indisponivel: {erro}")

# --- conferencia cruzada ---
print("\n4. Conferencia cruzada")
pontos_otimo = [(f1, f2) for f1, f2, _ in frente_otimo]
pontos_bordo = [(f1, f2) for f1, f2, _ in frente_bordo]

if frente_mip:
    mesmo_tamanho = len(frente_mip) == len(pontos_otimo)
    conferir("enumeracao e solver encontram o mesmo numero de pontos",
             mesmo_tamanho, f"{len(pontos_otimo)} x {len(frente_mip)}")
    if mesmo_tamanho:
        maior = max(max(abs(a[0] - b[0]), abs(a[1] - b[1]))
                    for a, b in zip(sorted(pontos_otimo), sorted(frente_mip)))
        conferir("os pontos coincidem nos dois objetivos", maior <= TOL,
                 f"desvio maximo = {maior:.2e}")

    for p in pontos_mip:
        recalculado = av.avaliar_com_B(p.solucao, p.B, p.partidas)
        if abs(recalculado.f1 - p.f1) > TOL or abs(recalculado.f2 - p.f2) > TOL:
            conferir(f"avaliador reproduz o ponto ({p.f1:.2f}, {p.f2:.2f}) do solver",
                     False, f"obteve ({recalculado.f1:.2f}, {recalculado.f2:.2f})")
            break
    else:
        conferir(f"avaliador reproduz os {len(pontos_mip)} pontos do solver", True)

conferir("fronteira ordenada e sem dominancia interna",
         len(pareto.filtrar(pontos_otimo)) == len(pontos_otimo))
conferir("o extremo de servico perfeito atinge f2 = 0",
         abs(min(p[1] for p in pontos_otimo)) <= TOL)

# --- efeito da politica de agendamento ---
print("\n5. Efeito da politica de agendamento")
dominados = pareto.cobertura(pontos_otimo, pontos_bordo)
print(f"   fracao da fronteira heuristica dominada pela exata: {dominados:.0%}")
sobrepostos = pareto.cobertura(pontos_bordo, pontos_otimo)
print(f"   fracao da fronteira exata dominada pela heuristica: {sobrepostos:.0%}")
ref = pontos_otimo + pontos_bordo
hv_otimo = pareto.hipervolume(pareto.normalizar(pontos_otimo, ref))
hv_bordo = pareto.hipervolume(pareto.normalizar(pontos_bordo, ref))
print(f"   hipervolume normalizado: exata={hv_otimo:.4f}  heuristica={hv_bordo:.4f}")
conferir("o agendamento otimo nao e dominado pelo heuristico", sobrepostos == 0.0)

# --- extremos da instancia completa ---
print("\n6. Extremos da instancia pr01 completa")
av_cheio = Avaliador(base, par)
publicada = ler_res(DADOS / "tabu" / "pr01.res")
from darp.solucao import Solucao  # noqa: E402

rotas_publicadas = Solucao(rotas=[r.copiar() for r in publicada.solucao.rotas])
extremo_f1 = av_cheio.avaliar(rotas_publicadas, politica=OTIMO)

m_original = base.m
base.m = base.n
extremo_f2 = av_cheio.avaliar(solucao_individual(base), politica=OTIMO)
base.m = m_original

print(f"   emissao minima ...... f1={extremo_f1.f1:8.2f}  f2={extremo_f1.f2:8.2f}  "
      f"veiculos={extremo_f1.veiculos_usados}")
print(f"   servico perfeito .... f1={extremo_f2.f1:8.2f}  f2={extremo_f2.f2:8.2f}  "
      f"veiculos={extremo_f2.veiculos_usados}")
print(f"   amplitude: f1 varia {100 * (extremo_f2.f1 / extremo_f1.f1 - 1):.0f}%, "
      f"f2 varia de {extremo_f1.f2:.0f} a 0")
conferir("os extremos da instancia completa se opoem",
         extremo_f2.f1 > extremo_f1.f1 and extremo_f2.f2 < extremo_f1.f2)

# --- gravacao ---
print("\n7. Saidas")
linhas = []
for rotulo, pontos in (("exata", pontos_otimo), ("heuristica", pontos_bordo),
                       ("solver", frente_mip)):
    for ordem, (f1, f2) in enumerate(sorted(pontos), start=1):
        linhas.append({"fronteira": rotulo, "ponto": ordem,
                       "f1": round(f1, 4), "f2": round(f2, 4)})
salvar_csv(SAIDA / "fase2_fronteira_pr01r5.csv", linhas)

salvar_csv(SAIDA / "fase2_extremos_pr01.csv", [
    {"extremo": "emissao minima", "f1": round(extremo_f1.f1, 2),
     "f2": round(extremo_f1.f2, 2), "veiculos": extremo_f1.veiculos_usados},
    {"extremo": "servico perfeito", "f1": round(extremo_f2.f1, 2),
     "f2": round(extremo_f2.f2, 2), "veiculos": extremo_f2.veiculos_usados},
])

series = {"exata (agendamento ótimo)": pontos_otimo,
          "heurística (redução de tempo a bordo)": pontos_bordo}
if frente_mip:
    series["solver ε-restrito"] = frente_mip
grafico(SAIDA / "fase2_fronteira_pr01r5.png", series)

print()
print("=" * 78)
print(f"RESULTADO: {'TODAS AS CONFERENCIAS PASSARAM' if falhas == 0 else f'{falhas} FALHA(S)'}")
print("=" * 78)
sys.exit(1 if falhas else 0)
