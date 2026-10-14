"""Valida soma por ruas, repetibilidade, unidades e preservacao de tempo/distancia."""
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from darp import ler_instancia_json, Avaliador, Parametros
from darp.solucao import solucao_individual
from darp.emissoes import preparar_ambiente, phi_para_q
from darp.instancia import reduzir
from darp.metaheuristicas.sa import SimulatedAnnealing
from darp.metaheuristicas.ga import AlgoritmoGenetico
from darp.metaheuristicas.grasp import GRASP

RAIZ = Path(__file__).resolve().parents[2]


class TestEmissoes(unittest.TestCase):
    def setUp(self):
        self.entrada = json.loads((RAIZ / "dados/exemplo_pequeno.json").read_text())
        self.inst = ler_instancia_json(RAIZ / "dados/exemplo_pequeno.json", Q=2)
        self.config = json.loads((RAIZ / "experimentos/modelo_emissoes.json").read_text())

    def test_fator_uniforme_e_percurso_com_garagem(self):
        self.config["ruas"].update(fator_min=1.1, fator_max=1.1)
        inst, _ = preparar_ambiente(self.inst, self.entrada, self.config)
        sol = solucao_individual(inst)
        antes = Avaliador(self.inst, Parametros(alpha=2)).avaliar(sol)
        depois = Avaliador(inst, Parametros(phi=180, alpha=2)).avaliar(sol)
        self.assertAlmostEqual(depois.f1, 180 * 1.1 * 92)
        self.assertEqual(depois.distancia, antes.distancia)
        self.assertEqual(depois.f2, antes.f2)
        self.assertEqual([a.B for a in depois.agendas], [a.B for a in antes.agendas])
        self.assertEqual(reduzir(inst, [1]).matriz_ambiental, inst.matriz_ambiental)

    def test_reproducibilidade_e_limites(self):
        inst, registro = preparar_ambiente(self.inst, self.entrada, self.config)
        self.entrada["rede"]["arestas"].reverse()
        inst2, registro2 = preparar_ambiente(self.inst, self.entrada, self.config)
        self.assertEqual(registro, registro2)
        self.assertEqual(inst.matriz_ambiental, inst2.matriz_ambiental)
        for p in registro["matriz_ambiental"]:
            self.assertGreaterEqual(p["distancia_ponderada"] + 1e-9, p["distancia"])
            self.assertLessEqual(p["distancia_ponderada"], 1.15 * p["distancia"] + 1e-9)
        caminho = next(p for p in registro["matriz_ambiental"] if p["origem"] == 0 and p["destino"] == 3)
        self.assertEqual(caminho["caminho"], [0, 1, 2, 3])
        soma = sum(p["distancia"] * p["fator"] for p in registro["fatores_arestas"])
        self.assertAlmostEqual(caminho["distancia_ponderada"], soma)

    def test_perfis_e_erros(self):
        self.assertEqual([phi_para_q(self.config, q) for q in [1, 4, 5, 6, 7, 10, 11, 20]],
                         [180, 180, 250, 250, 350, 350, 500, 500])
        with self.assertRaises(ValueError):
            phi_para_q(self.config, 21)
        self.config["veiculos"][0]["phi_g_km"] = float("nan")
        with self.assertRaises(ValueError):
            phi_para_q(self.config, 1)

    def test_caminhos_incompativeis_rejeitados(self):
        self.inst.rede.matriz_tempo[(0, 3)] = 0
        with self.assertRaises(ValueError):
            preparar_ambiente(self.inst, self.entrada, self.config)

    def test_buscas_invariantes_a_unidade_ambiental(self):
        inst, _ = preparar_ambiente(self.inst, self.entrada, self.config)
        for metodo in (SimulatedAnnealing(temp_inicial=1, temp_final=0.5, fator_resfriamento=0.6, iter_por_temp=3, seed=42),
                       AlgoritmoGenetico(tamanho_populacao=6, geracoes=2, seed=42),
                       GRASP(max_iteracoes=2, max_passos_busca_local=2, seed=42)):
            gramas = metodo.otimizar(inst, Avaliador(inst, Parametros(phi=180, alpha=2)))
            kg = metodo.otimizar(inst, Avaliador(inst, Parametros(phi=0.180, alpha=2)))
            self.assertEqual(len(gramas.fronteira), len(kg.fronteira))
            for a, b in zip(gramas.fronteira, kg.fronteira):
                self.assertAlmostEqual(a[0] / 1000, b[0])
                self.assertAlmostEqual(a[1], b[1])
                self.assertEqual([r.sequencia for r in a[2].rotas], [r.sequencia for r in b[2].rotas])


if __name__ == "__main__":
    unittest.main()
