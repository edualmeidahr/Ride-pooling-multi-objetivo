"""Menu das tres implementacoes e executor comum, tambem acessivel por argumentos."""
import argparse
import csv
import hashlib
import json
import math
import time
import uuid
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from darp import Avaliador, Parametros, HeuristicaGulosa, ler_instancia_json, ler_instancia, obter_metaheuristica
from darp.cenarios import cenario_capacidade
from darp.emissoes import preparar_ambiente, phi_para_q
from darp.exato import fronteira_exata
from darp.instancia import reduzir
from darp.pareto import filtrar

RAIZ = Path(__file__).resolve().parents[1]
LIMITE_EXATO = 6
MODOS = ("exato", "metaheuristica", "heuristica", "comparar", "comparar_aproximados")


class AvaliadorComCache(Avaliador):
    """Mesmo agendamento, reutilizado somente dentro da execucao de um metodo."""
    def __init__(self, inst, par):
        super().__init__(inst, par)
        self._cache = {}

    def agendar(self, rota, partida=None, politica=None):
        chave = (tuple(rota.sequencia), partida, politica or self.par.politica)
        if chave not in self._cache:
            self._cache[chave] = super().agendar(rota, partida, politica)
        return deepcopy(self._cache[chave])


def caminho_projeto(valor):
    caminho = Path(valor)
    return caminho if caminho.is_absolute() else RAIZ / caminho


def preparar(config_path, capacidades=None):
    arquivo = caminho_projeto(config_path)
    c = json.loads(arquivo.read_text(encoding="utf-8"))
    qs = capacidades if capacidades is not None else c["capacidades"]
    if not qs or any(type(q) is not int or q < 1 for q in qs):
        raise ValueError("Capacidades devem ser inteiros positivos.")
    qs = sorted(set(qs))
    entrada = caminho_projeto(c["instancia"])
    base = ler_instancia_json(entrada, Q=min(qs)) if entrada.suffix.lower() == ".json" else ler_instancia(entrada)
    pedidos = c["pedidos"]
    if not pedidos or len(set(pedidos)) != len(pedidos) or any(type(i) is not int or not 1 <= i <= base.n for i in pedidos):
        raise ValueError("Pedidos devem ser indices internos validos e distintos.")
    if type(c["m"]) is not int or c["m"] < 1:
        raise ValueError("Quantidade de veiculos deve ser inteira e positiva.")
    inst = reduzir(base, pedidos, m=c["m"])
    if c.get("coletas_antes_de_qualquer_entrega"):
        if min(inst.nos[i].e + inst.nos[i].s + inst.tempo(i,inst.entrega_de(i)) for i in inst.coletas) <= max(inst.nos[i].l for i in inst.coletas):
            raise ValueError("Entrada declarada concorrente permite entrega antes do fim das coletas.")
    par = Parametros(**c["parametros_avaliacao"])
    ambiente = None
    if c.get("modelo_emissoes"):
        inst, ambiente = preparar_ambiente(inst, json.loads(entrada.read_text(encoding="utf-8")),
                                          {**c["modelo_emissoes"], "capacidades": qs})
    return c, inst, par, qs, ambiente, hashlib.sha256(entrada.read_bytes()).hexdigest()


def serializar_ponto(sol, av):
    calculado = av.avaliar(sol)
    if not calculado.viavel:
        raise RuntimeError(f"Metodo retornou solucao inviavel: {calculado.violacoes}")
    return {"f1": calculado.f1, "f2": calculado.f2, "distancia_km": calculado.distancia,
            "espera": calculado.f2_espera, "desvio": calculado.f2_desvio,
            "veiculos_usados": calculado.veiculos_usados,
            "carga_maxima": max((a.carga_maxima for a in calculado.agendas), default=0),
            "rotas": [r.sequencia for r in sol.rotas],
            "agendas": [{"B": a.B, "partida": a.partida, "carga": a.carga} for a in calculado.agendas]}


def salvar(saida, registro):
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "execucoes.json").write_text(json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")
    linhas, solucoes = [], []
    for r in registro["execucoes"]:
        pontos = r["pontos"]
        if pontos:
            ref = registro["referencias"][str(r["Q"])]["pontos"]
            mins = [min(p[i] for p in ref) for i in (0, 1)]
            amps = [max(p[i] for p in ref)-mins[i] for i in (0, 1)]
            def nota(p):
                z = [(p[f"f{i+1}"]-mins[i])/(amps[i] or 1) for i in (0, 1)]
                return math.sqrt(0.5*z[0]**2 + 0.5*z[1]**2)
            indice = min(range(len(pontos)), key=lambda i: (nota(pontos[i]), pontos[i]["f1"], pontos[i]["f2"], i))
            p = pontos[indice]
            selecionado = p["solucao_id"]
        else:
            p, selecionado = {}, None
        linhas.append({"Q": r["Q"], "categoria": r["categoria"], "metodo": r["metodo"], "status": r["status"],
                       "f1": p.get("f1"), "f2": p.get("f2"), "veiculos_usados": p.get("veiculos_usados"),
                       "tempo_busca_s": r["tempo_busca_s"], "pontos": len(pontos), "solucao_id": selecionado})
        for p in pontos:
            solucoes.append({"solucao_id": p["solucao_id"], "Q": r["Q"], "categoria": r["categoria"], "metodo": r["metodo"],
                "f1": p["f1"], "f2": p["f2"], "distancia_km": p["distancia_km"], "veiculos_usados": p["veiculos_usados"],
                "rotas_json": json.dumps(p["rotas"], separators=(",", ":"))})
    for nome, dados, campos in (("metricas.csv", linhas, list(linhas[0]) if linhas else ["Q", "status"]),
                               ("solucoes.csv", solucoes, list(solucoes[0]) if solucoes else ["solucao_id", "f1", "f2"])):
        with (saida / nome).open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=campos)
            w.writeheader()
            w.writerows(dados)
    texto = ["# Resultados das implementações", "",
        f"Entrada: {len(registro['config']['pedidos'])} pedidos completos; {registro['config']['m']} veículos disponíveis; capacidades {registro['opcoes']['capacidades']}.", "",
        f"Unidades: f1 = {registro['unidade_f1']}; f2 = passageiro-minutos. Distância física é registrada separadamente em km.", "",
        "Cada linha representa uma solução real. Para métodos com vários pontos, o resumo escolhe a menor distância euclidiana "
        "ao ideal dos objetivos normalizados, com pesos iguais e extremos da referência do mesmo Q. "
        "A referência é exata se a enumeração foi executada; caso contrário, é a união não dominada dos métodos selecionados. "
        "Esta escolha de apresentação não muda a busca e não garante um ótimo único. Não combinar mínimos de soluções diferentes.", "",
        "| Q | Categoria | Método | Status | f1 | f2 | Veículos | Pontos |",
        "|---|---|---|---|---:|---:|---:|---:|"]
    for r in linhas:
        f1 = f"{r['f1']:.2f}" if r["f1"] is not None else "—"
        f2 = f"{r['f2']:.2f}" if r["f2"] is not None else "—"
        texto.append(f"| {r['Q']} | {r['categoria']} | {r['metodo']} | {r['status']} | "
                     f"{f1} | {f2} | "
                     f"{r['veiculos_usados'] if r['veiculos_usados'] is not None else '—'} | {r['pontos']} |")
    texto += ["", "[Resumo CSV](metricas.csv) · [Todas as soluções](solucoes.csv) · [Rotas, agendas e histórico](execucoes.json)", "",
        "O tempo de busca inclui a execução do método, sem a reavaliação posterior para exportação. "
        "Bloqueio de construção ou ausência de soluções em uma metaheurística não comprovam inviabilidade. "
        "Enumeração concluída sem soluções informa inviabilidade do modelo. Comparações com uma semente e orçamentos "
        "diferentes não constituem ranking científico dos métodos.", ""]
    (saida / "RESUMO.md").write_text("\n".join(texto), encoding="utf-8")


def executar(config_path, modo, algoritmos=("sa", "ga", "grasp"), seed=42, peso_emissao=0.5, capacidades=None, saida=None, retomar=False):
    if modo not in MODOS:
        raise ValueError("Implementacao desconhecida.")
    if not algoritmos or any(m not in ("sa", "ga", "grasp") for m in algoritmos) or len(set(algoritmos)) != len(algoritmos):
        raise ValueError("Selecione SA, GA e/ou GRASP, sem repeticoes.")
    if type(seed) is not int:
        raise ValueError("Semente deve ser inteira.")
    gulosa = HeuristicaGulosa(peso_emissao)
    c, inst, par_base, qs, ambiente, input_hash = preparar(config_path, capacidades)
    limite_pedidos = c.get("construcao", {}).get("limite_pedidos_candidatos")
    if limite_pedidos is not None and (type(limite_pedidos) is not int or limite_pedidos < 1):
        raise ValueError("limite_pedidos_candidatos deve ser inteiro positivo.")
    limite_posicoes = c.get("construcao", {}).get("limite_posicoes_insercao")
    gulosa = HeuristicaGulosa(peso_emissao, limite_pedidos=limite_pedidos, limite_posicoes=limite_posicoes)
    usar_exato = modo in ("exato", "comparar")
    if usar_exato and inst.n > LIMITE_EXATO:
        raise ValueError(f"Enumeracao exata limitada a {LIMITE_EXATO} pedidos; entrada tem {inst.n}. "
                         "Use comparar_aproximados para manter a entrada inteira.")
    if usar_exato and par_base.politica != "otimo":
        raise ValueError("Metodo exato exige politica de agendamento otimo.")
    metodos = (["exato"] if usar_exato else [])
    if modo in ("metaheuristica", "comparar", "comparar_aproximados"):
        metodos += list(algoritmos)
    if modo in ("heuristica", "comparar", "comparar_aproximados"):
        metodos += ["gulosa"]
    destino = caminho_projeto(saida) if saida is not None else RAIZ / "resultados/menu" / f"execucao-{uuid.uuid4().hex[:8]}"
    registro = {"config": c, "opcoes": {"modo": modo, "metodos": metodos, "seed": seed, "peso_emissao": peso_emissao,
                "capacidades": qs}, "unidade_f1": "g_CO2" if ambiente or par_base.phi != 1 else "km",
                "input_sha256": input_hash, "ambiente_emissoes": ambiente,
                "fontes_sha256": {str(p.relative_to(RAIZ)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (RAIZ / "codigo").rglob("*.py")},
                "referencias": {}, "execucoes": [], "concluida": False}
    existentes = set()
    if retomar:
        if saida is None:
            raise ValueError("Retomada exige a pasta original em --saida.")
        anterior = json.loads((destino / "execucoes.json").read_text(encoding="utf-8"))
        for k in ("config", "opcoes", "input_sha256", "ambiente_emissoes"):
            if anterior[k] != registro[k]:
                raise ValueError(f"Retomada recusada: {k} mudou.")
        for path, hash_atual in registro["fontes_sha256"].items():
            if path.startswith("codigo\\darp\\") or path.startswith("codigo/darp/"):
                if anterior["fontes_sha256"].get(path) != hash_atual:
                    raise ValueError(f"Retomada recusada: algoritmo/modelo alterado ({path}).")
        existentes = {(r["Q"],r["metodo"]) for r in anterior["execucoes"]}
        if len(existentes) != len(anterior["execucoes"]) or not existentes <= {(q,m) for q in qs for m in metodos}:
            raise ValueError("Retomada recusada: registros duplicados ou inesperados.")
        if anterior.get("concluida"):
            print(f"Execucao ja concluida: {destino}")
            return anterior, destino
        hashes = registro["fontes_sha256"]
        registro = anterior
        registro.setdefault("retomadas", []).append({"execucoes_preservadas": len(existentes), "fontes_sha256": hashes})
    for q in qs:
        atual = cenario_capacidade(inst, q)
        par = replace(par_base, phi=phi_para_q(c["modelo_emissoes"], q)) if ambiente else par_base
        for nome in metodos:
            if (q,nome) in existentes:
                continue
            av = AvaliadorComCache(atual, par) if c.get("cache_agendas") else Avaliador(atual, par)
            av.limite_pedidos_construcao = limite_pedidos
            av.limite_posicoes_construcao = limite_posicoes
            av.coletas_concorrentes = c.get("coletas_antes_de_qualquer_entrega", False)
            t0 = time.perf_counter()
            historico, pendentes = [], []
            if nome == "exato":
                frente = fronteira_exata(atual, av)
                status = "otimo" if frente else "inviavel"
                categoria = "exato"
            elif nome == "gulosa":
                res = gulosa.resolver(atual, av)
                frente = [(res.avaliacao.f1, res.avaliacao.f2, res.solucao)] if res.solucao is not None else []
                status, historico, pendentes = res.status, res.historico, res.pedidos_pendentes
                categoria = "heuristica"
            else:
                parametros = c.get("algoritmos", {}).get(nome, {})
                res = obter_metaheuristica(nome, seed=seed, **parametros).otimizar(atual, av)
                frente = res.fronteira
                status = "concluida" if frente else "sem_solucao_encontrada"
                historico, categoria = res.historico, "metaheuristica"
            tempo = time.perf_counter()-t0
            pontos = []
            for i, (f1, f2, sol) in enumerate(frente):
                ponto = serializar_ponto(sol, Avaliador(atual, par))
                if max(abs(ponto["f1"]-f1), abs(ponto["f2"]-f2)) > 1e-6:
                    raise RuntimeError("Objetivos inconsistentes na reavaliacao.")
                pontos.append({"solucao_id": f"Q{q}_{nome}_p{i}", **ponto})
            registro["execucoes"].append({"Q": q, "categoria": categoria, "metodo": nome, "status": status,
                "phi_g_km": par.phi, "seed": seed if categoria == "metaheuristica" else None,
                "tempo_busca_s": tempo, "pontos": pontos, "historico": historico, "pedidos_pendentes": pendentes})
            if usar_exato:
                ref = next(r for r in registro["execucoes"] if r["Q"] == q and r["metodo"] == "exato")
                referencia = [(p["f1"], p["f2"]) for p in ref["pontos"]]
            else:
                referencia = filtrar([(p["f1"], p["f2"]) for r in registro["execucoes"] if r["Q"] == q for p in r["pontos"]])
            registro["referencias"][str(q)] = {"tipo": "exata" if usar_exato else "empirica",
                                               "pontos": [list(p) for p in referencia]}
            salvar(destino, registro)
            print(f"Q={q} | {categoria} | {nome.upper()} | {status} | {len(pontos)} solucao(oes) | {tempo:.2f}s", flush=True)
    registro["concluida"] = True
    salvar(destino, registro)
    print(f"Resultados: {destino / 'RESUMO.md'}", flush=True)
    return registro, destino


def menu():
    while True:
        print("\nDARP — escolha a implementacao\n1 — Metodo exato\n2 — Metaheuristica\n3 — Heuristica gulosa\n"
              "4 — Comparar as tres categorias (entrada pequena)\n5 — Comparar heuristica e metaheuristicas\n0 — Sair")
        opcao = input("Opcao: ").strip()
        if opcao == "0":
            return
        modos = {"1": "exato", "2": "metaheuristica", "3": "heuristica", "4": "comparar", "5": "comparar_aproximados"}
        if opcao not in modos:
            print("Opcao invalida.")
            continue
        try:
            print("Configuracoes: experimentos/exemplo_pequeno.json (2 pedidos); "
                  "experimentos/validacao_emissoes.json (2 pedidos, CO2); "
                  "experimentos/comparacao_emissoes_q1_10.json (12 pedidos, CO2).")
            print("Teste grande: experimentos/comparacao_100_corridas.json (100 pedidos, opcoes 2/3/5).")
            config = input("Configuracao [Enter = exemplo_pequeno]: ").strip() or "experimentos/exemplo_pequeno.json"
            q = input("Q [Enter = todas as capacidades da configuracao]: ").strip()
            qs = [int(q)] if q else None
            algoritmos = ("sa", "ga", "grasp")
            seed, peso = 42, 0.5
            if opcao in ("2", "4", "5"):
                print("Metaheuristica: 1 — SA; 2 — GA; 3 — GRASP; 4 — Todas")
                a = input("Opcao [Enter = todas]: ").strip() or "4"
                escolhas = {"1": ("sa",), "2": ("ga",), "3": ("grasp",), "4": algoritmos}
                if a not in escolhas:
                    raise ValueError("Metaheuristica invalida.")
                algoritmos = escolhas[a]
                seed = int(input("Semente [Enter = 42]: ").strip() or "42")
            if opcao in ("3", "4", "5"):
                peso = float((input("Peso da emissao de 0 a 1 [Enter = 0,5]: ").strip() or "0.5").replace(",", "."))
            executar(config, modos[opcao], algoritmos=algoritmos, seed=seed, peso_emissao=peso, capacidades=qs)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            print(f"Nao foi possivel executar: {exc}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modo", choices=MODOS)
    parser.add_argument("--config", default="experimentos/exemplo_pequeno.json")
    parser.add_argument("--algoritmos", nargs="+", choices=("sa", "ga", "grasp"), default=["sa", "ga", "grasp"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--peso-emissao", type=float, default=0.5)
    parser.add_argument("--q", nargs="+", type=int)
    parser.add_argument("--saida")
    parser.add_argument("--retomar", action="store_true", help="Preserva resultados existentes e executa apenas os metodos/Q pendentes")
    args = parser.parse_args()
    try:
        if args.modo is None:
            menu()
        else:
            executar(args.config, args.modo, args.algoritmos, args.seed, args.peso_emissao, args.q, args.saida, retomar=args.retomar)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"Erro: {exc}\n")
    except (EOFError, KeyboardInterrupt):
        print("\nExecucao encerrada. Registros ja exportados permanecem na pasta de saida.")


if __name__ == "__main__":
    main()
