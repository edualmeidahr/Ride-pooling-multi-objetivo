"""Confere concorrencia, viabilidade em todos os Q e equivalencia do cache."""
import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from darp import Avaliador, Parametros, ler_instancia_json
from darp.solucao import Rota, Solucao, solucao_individual
from executar_campanha import AvaliadorInstrumentado

RAIZ = Path(__file__).resolve().parents[2]


def diagnostico():
    config = json.loads((RAIZ / "experimentos/comparacao_q1_10.json").read_text())
    linhas = []
    for Q in config["capacidades"]:
        inst = ler_instancia_json(RAIZ / config["instancia"], Q=Q)
        av = Avaliador(inst, Parametros(**config["parametros_avaliacao"]))
        ordem = sorted(inst.coletas, key=lambda i: (inst.nos[i].id_fixo, i))
        rotas = []
        for inicio in range(0, inst.n, Q):
            grupo = ordem[inicio:inicio+Q]
            entregas = sorted((inst.entrega_de(i) for i in grupo),
                              key=lambda j: (inst.dist(inst.deposito_ini,j),j))
            rotas.append(Rota(grupo+entregas))
        sol = Solucao(rotas + [Rota() for _ in range(inst.m-len(rotas))])
        res = av.avaliar(sol)
        assert res.viavel, res.violacoes
        assert res.veiculos_usados == math.ceil(inst.n / Q)
        linhas.append({"Q": Q, "minimo_veiculos_por_concorrencia": math.ceil(inst.n/Q),
                       "exemplo_viavel_distancia": res.f1, "exemplo_viavel_tempo_perdido": res.f2,
                       "carga_maxima_exemplo": max(a.carga_maxima for a in res.agendas),
                       "rotas": [r.sequencia for r in sol.rotas if r.usada]})
    return linhas


class TestCenario(unittest.TestCase):
    def test_distancia_separada_do_tempo(self):
        inst = ler_instancia_json(RAIZ / "dados/cenario_concorrente_q10.json", Q=1)
        av = Avaliador(inst,Parametros(alpha=2))
        for politica in ["cedo","bordo","otimo"]:
            agenda = av.agendar(Rota([1,13]),partida=28,politica=politica)
            self.assertAlmostEqual(agenda.distancia,46.0)
            self.assertAlmostEqual(agenda.duracao,92.4)
        self.assertAlmostEqual(av.avaliar(solucao_individual(inst)).f1,600.0)

    def test_concorrencia_real(self):
        inst = ler_instancia_json(RAIZ / "dados/cenario_concorrente_q10.json", Q=10)
        fim_coletas = max(inst.nos[i].l for i in inst.coletas)
        primeira_entrega_possivel = min(inst.nos[i].e+inst.nos[i].s+inst.tempo(i,inst.entrega_de(i)) for i in inst.coletas)
        self.assertGreater(primeira_entrega_possivel, fim_coletas)
        self.assertGreater(inst.n, 10)

    def test_base_individual_viavel(self):
        for Q in range(1,11):
            inst = ler_instancia_json(RAIZ / "dados/cenario_concorrente_q10.json", Q=Q)
            self.assertTrue(Avaliador(inst,Parametros(alpha=2)).avaliar(solucao_individual(inst)).viavel)

    def test_agrupamentos_viaveis_todos_q(self):
        self.assertEqual(len(diagnostico()),10)

    def test_cache_preserva_e_isola_agendas(self):
        inst = ler_instancia_json(RAIZ / "dados/cenario_concorrente_q10.json", Q=3)
        par = Parametros(alpha=2)
        normal = Avaliador(inst,par)
        cache = AvaliadorInstrumentado(inst,par,cache_agendas=True)
        # Inclui uma rota sobrecarregada e uma temporalmente inviavel.
        for seq in [[1,13], [1,5,9,13,17,21], [1,2,3,4,13,14,15,16], [1,13,2,14]]:
            a = normal.agendar(Rota(seq))
            b = cache.agendar(Rota(seq))
            self.assertEqual(a,b)
            b.B[seq[0]] = -999
            self.assertEqual(a,cache.agendar(Rota(seq)))
        self.assertEqual(cache.agendamentos,8)
        self.assertEqual(cache.resolucoes_agendamento,4)
        self.assertEqual(cache.cache_hits,4)


if __name__ == "__main__":
    unittest.main()
