#!/usr/bin/env python3
"""Comparativo de desempenho entre as meta-heuristicas: SA, GA e GRASP.

Permite rodar sobre qualquer instancia (arquivo JSON com o novo modelo de rede fixa
ou instancia classica de Cordeau) e comparar diretamente a qualidade das fronteiras
de Pareto, o tempo computacional e os valores extremos dos objetivos.

Uso:
    python codigo/experimentos/comparar_metaheuristicas.py --instancia exemplo_instancia.json
    python codigo/experimentos/comparar_metaheuristicas.py --instancia dados/tabu/pr01 --algoritmos sa grasp
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from darp import (
    BORDO,
    CEDO,
    OTIMO,
    AlgoritmoGenetico,
    Avaliador,
    GRASP,
    Instancia,
    Parametros,
    SimulatedAnnealing,
    ler_instancia,
    ler_instancia_json,
    obter_metaheuristica,
)
from darp.pareto import hipervolume, normalizar


def carregar_instancia_flexivel(caminho_str: str) -> Instancia:
    """Carrega uma instancia seja ela JSON ou formato texto classico."""
    caminho = Path(caminho_str)
    if not caminho.exists():
        # Tenta procurar na raiz ou em dados/
        raiz = Path(__file__).resolve().parents[2]
        if (raiz / caminho_str).exists():
            caminho = raiz / caminho_str
        elif (raiz / "dados" / caminho_str).exists():
            caminho = raiz / "dados" / caminho_str
        else:
            raise FileNotFoundError(f"Arquivo nao encontrado: {caminho_str}")

    if caminho.suffix.lower() == ".json":
        return ler_instancia_json(caminho)
    return ler_instancia(caminho)


def main():
    parser = argparse.ArgumentParser(description="Comparador de Meta-heuristicas para DARP Bi-objetivo")
    parser.add_argument(
        "--instancia",
        type=str,
        default="exemplo_instancia.json",
        help="Caminho do arquivo de instancia (.json ou formato classico)",
    )
    parser.add_argument(
        "--algoritmos",
        nargs="+",
        default=["sa", "ga", "grasp"],
        help="Algoritmos a executar: sa, ga, grasp (padrao: todos)",
    )
    parser.add_argument(
        "--politica",
        type=str,
        default=BORDO,
        choices=[CEDO, BORDO, OTIMO],
        help="Politica de agendamento do avaliador (cedo, bordo ou otimo)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semente para gerador de numeros aleatorios",
    )
    parser.add_argument(
        "--grafico",
        action="store_true",
        help="Salva grafico da fronteira de Pareto em 'fronteira_comparativo.png'",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("COMPARATIVO DE META-HEURISTICAS MULTIOBJETIVO (DARP)")
    print("=" * 80)

    inst = carregar_instancia_flexivel(args.instancia)
    av = Avaliador(inst, Parametros(politica=args.politica))

    print(f"Instancia carregada: {inst.resumo()}")
    print(f"Politica de avaliacao: {args.politica.upper()}")
    print(f"Algoritmos selecionados: {', '.join(a.upper() for a in args.algoritmos)}")
    print("-" * 80)

    resultados = {}
    todos_pontos = []

    for nome_alg in args.algoritmos:
        print(f"-> Executando {nome_alg.upper()}...", end="", flush=True)
        # Instancia via Strategy Pattern
        meta = obter_metaheuristica(nome_alg, seed=args.seed)

        t0 = time.time()
        res = meta.otimizar(inst, av)
        dt = time.time() - t0

        resultados[nome_alg.upper()] = res
        todos_pontos.extend([(p[0], p[1]) for p in res.fronteira])
        print(f" Concluido em {dt:.2f}s! ({res.num_solucoes} solucoes encontradas)")

    print("\n" + "=" * 80)
    print(f"{'ALGORITMO':<15} | {'SOLUCOES':<8} | {'MELHOR f1':<12} | {'MELHOR f2':<12} | {'HIPERVOLUME':<12} | {'TEMPO (s)':<10}")
    print("-" * 80)

    # Base de normalizacao para hipervolume
    for nome, res in resultados.items():
        if res.fronteira and todos_pontos:
            frente_norm = normalizar([(p[0], p[1]) for p in res.fronteira], referencia=todos_pontos)
            hv = hipervolume(frente_norm, referencia=(1.1, 1.1))
            hv_str = f"{hv:10.4f}"
        else:
            hv_str = "       N/A"

        f1_str = f"{res.melhor_f1:10.2f}" if res.melhor_f1 is not None else "       N/A"
        f2_str = f"{res.melhor_f2:10.2f}" if res.melhor_f2 is not None else "       N/A"
        print(f"{nome:<15} | {res.num_solucoes:<8} | {f1_str} | {f2_str} | {hv_str} | {res.tempo_execucao:8.2f}s")

    print("=" * 80)

    for nome, res in resultados.items():
        print(f"\nFronteira de Pareto detalhada - {nome}:")
        if not res.fronteira:
            print("  Nenhuma solucao viavel encontrada.")
            continue
        for i, (f1, f2, sol) in enumerate(res.fronteira, 1):
            rotas_str = " | ".join(str(r.sequencia) for r in sol.rotas if r.usada)
            print(f"  Ponto {i:>2}: f1={f1:8.2f} (emissao/dist) | f2={f2:8.2f} (tempo perdido) | Rotas: [{rotas_str}]")

    if args.grafico:
        try:
            import matplotlib.pyplot as plt

            plt.figure(figsize=(9, 6))
            cores = {"SA": "crimson", "GA": "royalblue", "GRASP": "forestgreen"}

            for nome, res in resultados.items():
                if res.fronteira:
                    x = [p[0] for p in res.fronteira]
                    y = [p[1] for p in res.fronteira]
                    plt.scatter(x, y, label=nome, color=cores.get(nome, "gray"), s=70, alpha=0.85)
                    plt.plot(x, y, linestyle="--", color=cores.get(nome, "gray"), alpha=0.5)

            plt.title(f"Fronteira de Pareto - {inst.nome}")
            plt.xlabel("f1: Emissao de CO2 (Distancia Total)")
            plt.ylabel("f2: Tempo Perdido pelos Usuarios (pass-min)")
            plt.grid(True, linestyle=":", alpha=0.6)
            plt.legend()
            caminho_fig = Path("fronteira_comparativo.png")
            plt.savefig(caminho_fig, dpi=200, bbox_inches="tight")
            print(f"\n[Grafico salvo com sucesso em '{caminho_fig.resolve()}']")
        except ImportError:
            print("\n[matplotlib nao disponivel para salvar grafico]")


if __name__ == "__main__":
    main()
