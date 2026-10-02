"""Recalcula objetivos dos registros diretamente dos arcos e horarios salvos."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from darp import ler_instancia_json, ler_instancia
from darp.instancia import reduzir
from darp.pareto import filtrar, hipervolume, normalizar


def conferir(pasta):
    raiz=Path(__file__).resolve().parents[2]
    d=json.loads((pasta/"execucoes.json").read_text())
    c=d["config"]
    assert "normalizacao" in d, "campanha incompleta"
    assert hashlib.sha256((raiz/c["instancia"]).read_bytes()).hexdigest()==d["input_sha256"]
    esperado={(q,m,s) for q in c["capacidades"] for m in c["algoritmos"] for s in c["sementes"]}
    encontrado=[(r["Q"],r["metodo"],r["seed"]) for r in d["execucoes"]]
    assert len(encontrado)==len(esperado) and set(encontrado)==esperado
    caminho=raiz/c["instancia"]
    base=(ler_instancia_json(caminho,Q=min(c["capacidades"])) if caminho.suffix.lower()==".json" else ler_instancia(caminho))
    inst=reduzir(base,c["pedidos"],m=c["m"])
    n_pontos=0
    for r in d["execucoes"]:
        assert r["agendamentos"]==r["resolucoes_agendamento"]+r["cache_hits"]
        for p in r["pontos"]:
            visitados=[i for rota in p["rotas"] for i in rota]
            assert len(visitados)==2*inst.n and set(visitados)==set(inst.atendimento)
            rotas=[rota for rota in p["rotas"] if rota]
            assert len(rotas)<=inst.m and len(rotas)==len(p["agendas"])
            km=desvio=espera=0.0
            max_carga=0
            for rota,agenda in zip(rotas,p["agendas"]):
                caminho=[inst.deposito_ini]+rota+[inst.deposito_fim]
                km+=sum(inst.dist(a,b) for a,b in zip(caminho,caminho[1:]))
                B={int(i):v for i,v in agenda["B"].items()}
                partida=agenda["partida"]
                retorno=B[rota[-1]]+inst.nos[rota[-1]].s+inst.tempo(rota[-1],inst.deposito_fim)
                assert inst.nos[inst.deposito_ini].e-1e-6<=partida<=inst.nos[inst.deposito_ini].l+1e-6
                assert B[rota[0]]>=partida+inst.tempo(inst.deposito_ini,rota[0])-1e-6
                assert retorno<=inst.nos[inst.deposito_fim].l+1e-6 and retorno-partida<=inst.T_max+1e-6
                carga=0
                for i in rota:
                    carga+=inst.nos[i].q
                    assert 0<=carga<=r["Q"]
                    assert abs(agenda["carga"][str(i)]-carga)<1e-6
                    max_carga=max(max_carga,carga)
                    assert inst.nos[i].e-1e-6<=B[i]<=inst.nos[i].l+1e-6
                    if i<=inst.n:
                        j=inst.entrega_de(i)
                        assert j in rota and rota.index(i)<rota.index(j)
                        bordo=B[j]-B[i]-inst.nos[i].s
                        assert bordo<=inst.limite_bordo(i,c["parametros_avaliacao"]["alpha"])+1e-6
                        desvio+=inst.nos[i].q*max(0,bordo-inst.tempo(i,j))
                        espera+=inst.nos[i].q*max(0,B[i]-inst.rho[i])
                assert carga==0
                for a,b in zip(rota,rota[1:]):
                    assert B[b]>=B[a]+inst.nos[a].s+inst.tempo(a,b)-1e-6
            assert abs(p["f1"]-c["parametros_avaliacao"]["phi"]*km)<1e-6
            assert abs(p["f2"]-desvio-espera)<1e-6
            assert abs(p["desvio"]-desvio)<1e-6 and abs(p["espera"]-espera)<1e-6
            assert p["veiculos_usados"]==len(rotas) and p["carga_maxima"]==max_carga
            n_pontos+=1
    todos=[tuple(p) for ref in d["referencias"].values() for p in ref["pontos"]]
    todos += [(p["f1"],p["f2"]) for r in d["execucoes"] for p in r["pontos"]]
    for r in d["execucoes"]:
        pts=[(p["f1"],p["f2"]) for p in r["pontos"]]
        ref=d["referencias"][str(r["Q"])]["pontos"]
        if d["tipo_referencia"]=="empirica":
            union=[(p["f1"],p["f2"]) for other in d["execucoes"] if other["Q"]==r["Q"] for p in other["pontos"]]
            assert ref==[list(p) for p in filtrar(union,tol=1e-6)]
        hv=hipervolume(normalizar(pts,todos),referencia=(1.1,1.1))
        hvref=hipervolume(normalizar(ref,todos),referencia=(1.1,1.1))
        assert abs(r["metricas"]["hv"]-hv)<1e-9
        assert abs(r["metricas"]["hv_relativo"]-hv/hvref)<1e-9
        assert 0<=r["metricas"]["hv_relativo"]<=1+1e-6
    print(f"{len(encontrado)} execucoes e {n_pontos} pontos conferidos por arcos, horarios, carga e metricas: {pasta}")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pasta",type=Path)
    conferir(parser.parse_args().pasta)
