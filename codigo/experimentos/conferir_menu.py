"""Confere solucoes do menu por arcos, horarios e cargas, sem refazer a busca."""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def conferir(pasta):
    pasta = Path(pasta)
    d = json.loads((pasta / "execucoes.json").read_text(encoding="utf-8"))
    if not d["concluida"]:
        raise AssertionError("Execucao incompleta")
    # Configuracao efetiva em memoria evita depender de um arquivo de configuracao alterado.
    from darp import ler_instancia_json, ler_instancia
    from darp.instancia import reduzir
    from darp.emissoes import preparar_ambiente
    import hashlib
    raiz = Path(__file__).resolve().parents[2]
    c = d["config"]
    caminho = raiz / c["instancia"]
    assert hashlib.sha256(caminho.read_bytes()).hexdigest() == d["input_sha256"]
    base = ler_instancia_json(caminho, Q=1) if caminho.suffix == ".json" else ler_instancia(caminho)
    inst = reduzir(base, c["pedidos"], m=c["m"])
    if c.get("modelo_emissoes"):
        inst, ambiente = preparar_ambiente(inst, json.loads(caminho.read_text(encoding="utf-8")),
                                          {**c["modelo_emissoes"], "capacidades": d["opcoes"]["capacidades"]})
        assert ambiente == d["ambiente_emissoes"]
    esperado = {(q,m) for q in d["opcoes"]["capacidades"] for m in d["opcoes"]["metodos"]}
    assert {(r["Q"],r["metodo"]) for r in d["execucoes"]} == esperado
    assert len(d["execucoes"]) == len(esperado)
    indice = {}
    for r in d["execucoes"]:
        for p in r["pontos"]:
            visitas = [i for rota in p["rotas"] for i in rota]
            assert sorted(visitas) == list(inst.atendimento), "Cobertura incompleta ou duplicada"
            usadas = [rota for rota in p["rotas"] if rota]
            assert len(usadas) == len(p["agendas"]) == p["veiculos_usados"] <= inst.m
            km = ponderada = espera = desvio = max_carga = 0
            for rota, agenda in zip(usadas,p["agendas"]):
                caminho_rota = [inst.deposito_ini]+rota+[inst.deposito_fim]
                km += sum(inst.dist(a,b) for a,b in zip(caminho_rota,caminho_rota[1:]))
                ponderada += sum(inst.dist_ambiental(a,b) for a,b in zip(caminho_rota,caminho_rota[1:]))
                B = {int(i):t for i,t in agenda["B"].items()}
                carga = 0
                assert inst.nos[0].e-1e-6 <= agenda["partida"] <= inst.nos[0].l+1e-6
                assert B[rota[0]]+1e-6 >= agenda["partida"]+inst.tempo(inst.deposito_ini,rota[0])
                for i in rota:
                    carga += inst.nos[i].q
                    max_carga = max(max_carga,carga)
                    assert 0 <= carga <= r["Q"]
                    assert agenda["carga"][str(i)] == carga
                    assert inst.nos[i].e-1e-6 <= B[i] <= inst.nos[i].l+1e-6
                    if i <= inst.n:
                        j = inst.entrega_de(i)
                        assert j in rota and rota.index(i) < rota.index(j)
                        bordo = B[j]-B[i]-inst.nos[i].s
                        assert bordo <= inst.limite_bordo(i,c["parametros_avaliacao"].get("alpha"))+1e-6
                        espera += inst.nos[i].q*max(0,B[i]-inst.rho[i])
                        desvio += inst.nos[i].q*max(0,bordo-inst.t_direto(i))
                assert carga == 0
                for a,b in zip(rota,rota[1:]):
                    assert B[b]+1e-6 >= B[a]+inst.nos[a].s+inst.tempo(a,b)
                retorno = B[rota[-1]]+inst.nos[rota[-1]].s+inst.tempo(rota[-1],inst.deposito_fim)
                assert retorno <= inst.nos[inst.deposito_fim].l+1e-6
                assert retorno-agenda["partida"] <= inst.T_max+1e-6
            assert abs(p["f1"]-r["phi_g_km"]*ponderada) < 1e-6
            assert abs(p["distancia_km"]-km) < 1e-6
            assert abs(p["f2"]-espera-desvio) < 1e-6
            assert abs(p["espera"]-espera) < 1e-6 and abs(p["desvio"]-desvio)<1e-6
            assert max_carga == p["carga_maxima"]
            assert p["solucao_id"] not in indice
            indice[p["solucao_id"]] = p
    from darp.pareto import filtrar
    for q in d["opcoes"]["capacidades"]:
        ref = d["referencias"][str(q)]
        pontos = [(p["f1"],p["f2"]) for r in d["execucoes"] if r["Q"] == q for p in r["pontos"]]
        if ref["tipo"] == "empirica":
            assert ref["pontos"] == [list(p) for p in filtrar(pontos)]
        else:
            exatos = [(p["f1"],p["f2"]) for r in d["execucoes"] if r["Q"]==q and r["metodo"]=="exato" for p in r["pontos"]]
            assert ref["pontos"] == [list(p) for p in exatos]
            assert all(any(a<=p[0]+1e-6 and b<=p[1]+1e-6 for a,b in exatos) for p in pontos)
    with (pasta / "metricas.csv").open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["solucao_id"]:
                p = indice[r["solucao_id"]]
                assert float(r["f1"]) == p["f1"] and float(r["f2"]) == p["f2"]
    print(f"{inst.n} pedidos; {len(esperado)} execucoes; {len(indice)} solucoes completas conferidas: {pasta}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pasta", type=Path)
    conferir(parser.parse_args().pasta)
