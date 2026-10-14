"""Regressoes da construcao deterministica e comparacao com gabarito pequeno."""
import json
import math
import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from darp import HeuristicaGulosa, Avaliador, Parametros, ler_instancia_json
from darp.emissoes import preparar_ambiente
from darp.exato import fronteira_exata
from darp.pareto import domina
from darp.instancia import reduzir

RAIZ = Path(__file__).resolve().parents[2]


class TestHeuristica(unittest.TestCase):
    def setUp(self):
        self.inst = ler_instancia_json(RAIZ / "dados/exemplo_pequeno.json", Q=2)
        self.par = Parametros(alpha=2)

    def test_reprodutibilidade_cobertura_e_original(self):
        antes = [(no.id, no.q, no.e, no.l) for no in self.inst.nos]
        metodo = HeuristicaGulosa()
        a = metodo.resolver(self.inst, Avaliador(self.inst, self.par))
        b = metodo.resolver(self.inst, Avaliador(self.inst, self.par))
        self.assertEqual(a.status, "concluida")
        self.assertTrue(a.avaliacao.viavel)
        self.assertFalse(a.solucao.conferir_estrutura(self.inst))
        self.assertEqual([r.sequencia for r in a.solucao.rotas], [r.sequencia for r in b.solucao.rotas])
        self.assertEqual(a.historico, b.historico)
        self.assertEqual(antes, [(no.id, no.q, no.e, no.l) for no in self.inst.nos])
        self.assertEqual(len(a.historico), self.inst.n)

    def test_pesos_extremos_e_referencia_exata(self):
        exata = fronteira_exata(self.inst, Avaliador(self.inst, self.par))
        dist = HeuristicaGulosa(1).resolver(self.inst, Avaliador(self.inst, self.par))
        tempo = HeuristicaGulosa(0).resolver(self.inst, Avaliador(self.inst, self.par))
        self.assertEqual(dist.avaliacao.objetivos, (46, 4.5))
        self.assertEqual(tempo.avaliacao.objetivos, (92, 0))
        for res in (dist, tempo):
            self.assertTrue(any(abs(p[0]-res.avaliacao.f1)<1e-6 and abs(p[1]-res.avaliacao.f2)<1e-6 for p in exata))
            self.assertFalse(any(domina(p, res.avaliacao.objetivos) for p in exata))

    def test_capacidade_um(self):
        inst = replace(self.inst, Q=1)
        res = HeuristicaGulosa().resolver(inst, Avaliador(inst, self.par))
        self.assertEqual(res.avaliacao.objetivos, (92, 0))
        self.assertEqual(res.avaliacao.veiculos_usados, 2)

    def test_bloqueio_sem_falsa_solucao(self):
        inst = replace(self.inst, Q=1, m=1)
        res = HeuristicaGulosa().resolver(inst, Avaliador(inst, self.par))
        self.assertEqual(res.status, "bloqueada")
        self.assertIsNone(res.solucao)
        self.assertIsNone(res.avaliacao)
        self.assertEqual(len(res.pedidos_pendentes), 1)
        self.assertEqual(fronteira_exata(inst, Avaliador(inst, self.par)), [])

    def test_ambiente_e_invariancia_de_unidades(self):
        entrada = json.loads((RAIZ / "dados/exemplo_pequeno.json").read_text())
        config = json.loads((RAIZ / "experimentos/modelo_emissoes.json").read_text())
        inst, _ = preparar_ambiente(self.inst, entrada, config)
        for peso in (0, 0.5, 1):
            a = HeuristicaGulosa(peso).resolver(inst, Avaliador(inst, replace(self.par, phi=180)))
            b = HeuristicaGulosa(peso).resolver(inst, Avaliador(inst, replace(self.par, phi=0.18)))
            self.assertEqual([r.sequencia for r in a.solucao.rotas], [r.sequencia for r in b.solucao.rotas])
            self.assertAlmostEqual(a.avaliacao.f1/1000, b.avaliacao.f1)
            self.assertEqual(a.avaliacao.f2, b.avaliacao.f2)
            self.assertEqual(a.avaliacao.distancia, b.avaliacao.distancia)

    def test_pesos_invalidos(self):
        for peso in (-1, 2, True, math.nan, math.inf, "0.5"):
            with self.assertRaises(ValueError):
                HeuristicaGulosa(peso)

    def test_saidas_por_arcos_horarios_e_cargas(self):
        for nome in ("heuristica_gulosa_exemplo", "heuristica_gulosa_emissoes_q1_10"):
            dados = json.loads((RAIZ / "resultados" / nome / "execucoes.json").read_text(encoding="utf-8"))
            c = dados["config"]
            entrada = json.loads((RAIZ / c["instancia"]).read_text(encoding="utf-8"))
            inst = reduzir(ler_instancia_json(RAIZ / c["instancia"], Q=1), c["pedidos"], m=c["m"])
            if c.get("modelo_emissoes"):
                inst, ambiente = preparar_ambiente(inst, entrada, {**c["modelo_emissoes"], "capacidades": c["capacidades"]})
                self.assertEqual(ambiente, dados["ambiente_emissoes"])
            for r in dados["execucoes"]:
                self.assertEqual(r["status"], "concluida")
                p = r["ponto"]
                visitas = [i for rota in p["rotas"] for i in rota]
                self.assertEqual(sorted(visitas), list(inst.atendimento))
                km = ponderada = espera = desvio = 0
                usadas = [rota for rota in p["rotas"] if rota]
                self.assertEqual(len(usadas), p["veiculos_usados"])
                for rota, agenda in zip(usadas, p["agendas"]):
                    seq = [inst.deposito_ini] + rota + [inst.deposito_fim]
                    km += sum(inst.dist(a,b) for a,b in zip(seq,seq[1:]))
                    ponderada += sum(inst.dist_ambiental(a,b) for a,b in zip(seq,seq[1:]))
                    carga = 0
                    B = {int(i): t for i,t in agenda["B"].items()}
                    self.assertGreaterEqual(B[rota[0]]+1e-6, agenda["partida"]+inst.tempo(inst.deposito_ini,rota[0]))
                    for i in rota:
                        carga += inst.nos[i].q
                        self.assertTrue(0 <= carga <= r["Q"])
                        self.assertEqual(carga, agenda["carga"][str(i)])
                        self.assertTrue(inst.nos[i].e-1e-6 <= B[i] <= inst.nos[i].l+1e-6)
                        if i <= inst.n:
                            j = inst.entrega_de(i)
                            self.assertLess(rota.index(i), rota.index(j))
                            bordo = B[j]-B[i]-inst.nos[i].s
                            self.assertLessEqual(bordo, inst.limite_bordo(i,c["parametros_avaliacao"]["alpha"])+1e-6)
                            espera += inst.nos[i].q*max(0,B[i]-inst.rho[i])
                            desvio += inst.nos[i].q*max(0,bordo-inst.t_direto(i))
                    self.assertEqual(carga, 0)
                    for a,b in zip(rota,rota[1:]):
                        self.assertGreaterEqual(B[b]+1e-6, B[a]+inst.nos[a].s+inst.tempo(a,b))
                    retorno = B[rota[-1]]+inst.nos[rota[-1]].s+inst.tempo(rota[-1],inst.deposito_fim)
                    self.assertLessEqual(retorno,inst.nos[inst.deposito_fim].l+1e-6)
                    self.assertLessEqual(retorno-agenda["partida"],inst.T_max+1e-6)
                self.assertAlmostEqual(p["distancia"],km)
                self.assertAlmostEqual(p["f1"],r["phi_g_km"]*ponderada)
                self.assertAlmostEqual(p["f2"],espera+desvio)


if __name__ == "__main__":
    unittest.main()
