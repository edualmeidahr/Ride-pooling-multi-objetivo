"""Exporta solucoes reais e seleciona compromissos sem combinar extremos distintos."""
import argparse
import csv
import json
import math
from pathlib import Path


def limites_por_q(dados):
    # Escala comum a todos os metodos/sementes do mesmo Q.
    return {int(q): ([min(p[i] for p in ref["pontos"]) for i in (0, 1)],
                     [max(p[i] for p in ref["pontos"]) for i in (0, 1)])
            for q, ref in dados["referencias"].items()}


def escore(ponto, limites):
    minimo, maximo = limites
    z = [(ponto[f"f{i+1}"] - minimo[i]) / (maximo[i] - minimo[i] or 1.0)
         for i in (0, 1)]
    return math.sqrt(0.5 * z[0] ** 2 + 0.5 * z[1] ** 2)


def escolher(linhas, perfil):
    if perfil == "equilibrada":
        chave = lambda p: (p["escore_equilibrio"], p["f1"], p["f2"], p["solucao_id"])
    elif perfil == "menor_distancia":
        chave = lambda p: (p["f1"], p["f2"], p["solucao_id"])
    elif perfil == "menor_tempo_perdido":
        chave = lambda p: (p["f2"], p["f1"], p["solucao_id"])
    else:
        raise ValueError(perfil)
    return min(linhas, key=chave)


def escrever_csv(caminho, linhas):
    with caminho.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(linhas[0]))
        writer.writeheader()
        writer.writerows(linhas)


def gerar_resumos(pasta, dados=None):
    pasta = Path(pasta)
    if dados is None:
        dados = json.loads((pasta / "execucoes.json").read_text(encoding="utf-8"))
    if "normalizacao" not in dados:
        raise ValueError("A campanha precisa estar completa para gerar o resumo.")
    limites = limites_por_q(dados)
    todas, representantes, metricas = [], [], []
    for r in dados["execucoes"]:
        linhas = []
        ref = dados["referencias"][str(r["Q"])]["pontos"]
        for indice, p in enumerate(r["pontos"]):
            linha = {"solucao_id": f"Q{r['Q']}_{r['metodo']}_seed{r['seed']}_p{indice}",
                     "Q": r["Q"], "metodo": r["metodo"], "seed": r["seed"],
                     "indice_ponto_json": indice, "f1": p["f1"], "f2": p["f2"],
                     "espera": p["espera"], "desvio": p["desvio"],
                     "veiculos_usados": p["veiculos_usados"], "carga_maxima": p["carga_maxima"],
                     "escore_equilibrio": escore(p, limites[r["Q"]]),
                     "na_referencia": any(max(abs(p["f1"]-a), abs(p["f2"]-b)) <= 1e-6
                                          for a, b in ref),
                     "rotas_json": json.dumps(p["rotas"], separators=(",", ":"))}
            linhas.append(linha)
        todas.extend(linhas)
        for perfil in ("equilibrada", "menor_distancia", "menor_tempo_perdido"):
            representantes.append({"perfil": perfil, **escolher(linhas, perfil)})
        equilibrada = escolher(linhas, "equilibrada")
        distancia = escolher(linhas, "menor_distancia")
        tempo = escolher(linhas, "menor_tempo_perdido")
        # Metricas da fronteira permanecem separadas dos objetivos de uma solucao.
        resumo = {"Q": r["Q"], "metodo": r["metodo"], "seed": r["seed"],
                  "solucao_equilibrada_id": equilibrada["solucao_id"],
                  "f1_equilibrada": equilibrada["f1"], "f2_equilibrada": equilibrada["f2"],
                  "veiculos_equilibrada": equilibrada["veiculos_usados"],
                  "escore_equilibrio": equilibrada["escore_equilibrio"],
                  "solucao_menor_distancia_id": distancia["solucao_id"],
                  "f1_menor_distancia": distancia["f1"], "f2_menor_distancia": distancia["f2"],
                  "solucao_menor_tempo_id": tempo["solucao_id"],
                  "f1_menor_tempo": tempo["f1"], "f2_menor_tempo": tempo["f2"],
                  "tempo_busca": r["tempo_busca"], "agendamentos": r["agendamentos"]}
        resumo.update({k: v for k, v in r["metricas"].items() if k not in ("min_f1", "min_f2")})
        resumo.update(resolucoes_agendamento=r["resolucoes_agendamento"], cache_hits=r["cache_hits"])
        metricas.append(resumo)
    recomendadas = [escolher([p for p in todas if p["Q"] == q and p["na_referencia"]], "equilibrada")
                    for q in dados["config"]["capacidades"]]
    escrever_csv(pasta / "solucoes.csv", todas)
    escrever_csv(pasta / "solucoes_representativas.csv", representantes)
    escrever_csv(pasta / "solucoes_equilibradas_por_q.csv", recomendadas)
    escrever_csv(pasta / "metricas_tecnicas.csv", metricas)
    simples = [{"Q": r["Q"], "metodo": r["metodo"], "seed": r["seed"],
                "f1": r["f1_equilibrada"], "f2": r["f2_equilibrada"],
                "veiculos_usados": r["veiculos_equilibrada"], "tempo_busca": r["tempo_busca"],
                "hv_relativo": r["hv_relativo"], "cardinalidade": r["cardinalidade"],
                "solucao_id": r["solucao_equilibrada_id"]} for r in metricas]
    escrever_csv(pasta / "metricas.csv", simples)
    texto = ["# Resumo de soluções reais", "",
        "Cada linha abaixo representa uma única solução encontrada, com distância e tempo perdido do mesmo conjunto completo de rotas. "
        "A seleção é feita entre as soluções da referência empírica (ou exata, no caso reduzido), reunindo métodos e sementes por Q. "
        "O método e a semente identificam a origem; não são um ranking dos algoritmos.", "",
        "## Critério de equilíbrio", "",
        "Não existe uma melhor solução única sem definir preferências. Adotamos pesos iguais para os dois objetivos normalizados: "
        "escore = sqrt(0,5 × z1² + 0,5 × z2²). Menor é melhor segundo esse critério. "
        "zi = (fi − mínimo_i)/(máximo_i − mínimo_i), usando os extremos da referência do mesmo Q, comuns aos métodos e sementes. "
        "Se a amplitude for zero, usa-se divisor 1. O ponto ideal formado pelos mínimos é apenas um alvo matemático; "
        "não é apresentado como solução realizável. A escolha sempre copia uma solução efetivamente registrada. "
        "Empates são resolvidos por f1, f2 e identificador. O escore não é hipervolume, não prova otimalidade "
        "e não deve ser comparado entre Q com escalas distintas.", "",
        ("Nesta campanha, f1 representa gramas de CO2 estimado pelo modelo sintético e f2 passageiro-minutos. Os fatores não são calibrados."
         if dados.get("ambiente_emissoes") else
         "Na campanha com phi=1, f1 representa km e f2 passageiro-minutos. Não são emissões calibradas."), "",
        "| Q | Origem | Semente | f1 | f2 | Espera | Desvio | Veículos | Carga máxima | ID |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for p in recomendadas:
        texto.append(f"| {p['Q']} | {p['metodo'].upper()} | {p['seed']} | {p['f1']:.2f} | {p['f2']:.2f} | "
                     f"{p['espera']:.2f} | {p['desvio']:.2f} | {p['veiculos_usados']} | {p['carga_maxima']:g} | {p['solucao_id']} |")
    texto += ["", "## Arquivos e rastreabilidade", "",
        "- [solucoes_equilibradas_por_q.csv](solucoes_equilibradas_por_q.csv): uma escolha equilibrada por Q, com os dois objetivos e as rotas.",
        "- [solucoes_representativas.csv](solucoes_representativas.csv): três escolhas por execução: equilibrada, menor distância e menor tempo perdido. Os perfis podem selecionar a mesma solução.",
        "- [solucoes.csv](solucoes.csv): todas as soluções finais, uma por linha, com objetivos pareados e rotas.",
        "- [metricas.csv](metricas.csv): resumo simples, uma linha por execução. f1/f2/veiculos_usados descrevem a mesma solução equilibrada; tempo_busca (segundos), hv_relativo (fração) e cardinalidade descrevem a execução/fronteira.",
        "- [metricas_tecnicas.csv](metricas_tecnicas.csv): detalhamento dos três perfis, escore, agendamentos e cache.",
        "- [execucoes.json](execucoes.json): registro original completo, preservado. Localize Q/metodo/seed e use indice_ponto_json (começa em zero) em pontos para acessar horários e cargas.", "",
        "rotas_json lista as sequências de atendimento de todos os veículos; listas vazias representam veículos não utilizados. "
        "As garagens são implícitas. agendas no JSON acompanha somente as rotas não vazias, na mesma ordem. "
        "Os identificadores são nós de coleta/entrega, não os IDs das paradas físicas.", "",
        "Os antigos min_f1/min_f2 permanecem no JSON como estatísticas históricas da fronteira. "
        "No resumo simples, f1 e f2 são os objetivos da solução equilibrada identificada. "
        "No detalhamento técnico, os três perfis têm pares de objetivos identificados. "
        "Nenhuma média ou mediana dos objetivos é apresentada como uma rota real.", ""]
    (pasta / "RESUMO_SOLUCOES.md").write_text("\n".join(texto), encoding="utf-8")
    return todas, representantes, recomendadas


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resultados", type=Path,
                        default=Path(__file__).resolve().parents[2] / "resultados/comparacao_q1_10")
    args = parser.parse_args()
    todas, representantes, recomendadas = gerar_resumos(args.resultados)
    print(f"{len(todas)} soluções reais, {len(representantes)} perfis e {len(recomendadas)} escolhas por Q exportados.")
