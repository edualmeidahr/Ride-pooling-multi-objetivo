"""Regressoes estruturais, construcao real, cruzamento e agendas exatas."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from darp import Avaliador, Parametros, NoFixo, Rede, Requisicao, criar_instancia_rede
from darp.solucao import Rota, Solucao, solucao_individual
from darp.cenarios import cenario_capacidade
from darp.metaheuristicas.operadores import inserir_requisicao, perturbar_solucao, construcao_gulosa_randomizada
from darp.metaheuristicas.ga import AlgoritmoGenetico
from darp.exato import fronteira_exata
from darp.metaheuristicas.sa import SimulatedAnnealing
from darp.metaheuristicas.grasp import GRASP


class TestOperadores(unittest.TestCase):
    def setUp(self):
        rede = Rede.euclidiana([NoFixo(0, 0, 0), NoFixo(1, 1, 0), NoFixo(2, 2, 0)])
        self.inst = criar_instancia_rede("teste", rede,
            [Requisicao(i, 1, 2) for i in range(1, 5)], 0, m=4, Q=4)
        self.av = Avaliador(self.inst, Parametros())

    def test_insercao_e_precedencia(self):
        self.assertEqual(inserir_requisicao(Rota(), 1, 0, 0, self.inst).sequencia, [1, 5])
        with self.assertRaises(ValueError):
            inserir_requisicao(Rota([2, 6]), 1, 2, 0, self.inst)

    def test_construcao_nao_retorna_fallback(self):
        sol = construcao_gulosa_randomizada(self.inst, self.av, alpha=0, peso_f1=1, rng=random.Random(7))
        self.assertFalse(sol.conferir_estrutura(self.inst))
        self.assertTrue(self.av.avaliar(sol).viavel)
        self.assertEqual(sol.veiculos_usados, 1)
        self.assertLess(self.av.avaliar(sol).f1, self.av.avaliar(solucao_individual(self.inst)).f1)

    def test_mil_perturbacoes_preservam_estrutura_e_original(self):
        sol = solucao_individual(self.inst)
        rng = random.Random(42)
        for _ in range(1000):
            original = [list(r.sequencia) for r in sol.rotas]
            nova = perturbar_solucao(sol, self.inst, rng)
            self.assertFalse(nova.conferir_estrutura(self.inst))
            self.assertEqual(original, [r.sequencia for r in sol.rotas])
            sol = nova

    def test_cruzamentos(self):
        pai1 = solucao_individual(self.inst)
        pai2 = Solucao([Rota([4, 8, 3, 7]), Rota([2, 6, 1, 5]), Rota(), Rota()])
        ga = AlgoritmoGenetico(prob_crossover=1)
        for seed in range(100):
            filho = ga._crossover(pai1, pai2, self.inst, self.av, random.Random(seed))
            self.assertFalse(filho.conferir_estrutura(self.inst))
        alternate = Solucao([Rota([3, 7, 4, 8]), Rota([1, 5, 2, 6]), Rota(), Rota()])
        a = ga._crossover(pai1, pai2, self.inst, self.av, random.Random(3))
        b = ga._crossover(pai1, alternate, self.inst, self.av, random.Random(3))
        self.assertNotEqual([r.sequencia for r in a.rotas], [r.sequencia for r in b.rotas])

    def test_cenarios_independentes(self):
        atual = cenario_capacidade(self.inst, 20, m=2)
        self.assertEqual((self.inst.Q, self.inst.m), (4, 4))
        self.assertEqual((atual.Q, atual.m), (20, 2))

    def test_capacidade_realmente_altera_fronteira(self):
        # Pedidos coincidentes e servico nulo: capacidade controla agrupamento.
        extremos = []
        for Q in (1, 2, 4, 20):
            inst = cenario_capacidade(self.inst, Q)
            frente = fronteira_exata(inst, Avaliador(inst, Parametros()))
            self.assertTrue(frente)
            extremos.append(min(f1 for f1, _, _ in frente))
        # Um veiculo pode repetir 1->2 sem voltar ao deposito a cada pedido.
        self.assertEqual(extremos, [10.0, 6.0, 4.0, 4.0])

    def test_rotas_compactas(self):
        sol = Solucao([Rota([1, 5, 2, 6, 3, 7, 4, 8])])
        for seed in range(50):
            self.assertFalse(perturbar_solucao(sol, self.inst, random.Random(seed)).conferir_estrutura(self.inst))

    def test_integracao_metaheuristicas(self):
        metodos = [SimulatedAnnealing(temp_inicial=2, temp_final=1, fator_resfriamento=0.5,
                                      iter_por_temp=2, seed=7),
                   AlgoritmoGenetico(tamanho_populacao=4, geracoes=2, seed=7),
                   GRASP(max_iteracoes=2, max_passos_busca_local=2, seed=7)]
        for metodo in metodos:
            with self.subTest(metodo=metodo.nome):
                resultado = metodo.otimizar(self.inst, self.av)
                self.assertTrue(resultado.fronteira)
                for f1, f2, sol in resultado.fronteira:
                    res = self.av.avaliar(sol)
                    self.assertTrue(res.viavel)
                    self.assertAlmostEqual(res.f1, f1)
                    self.assertAlmostEqual(res.f2, f2)


if __name__ == "__main__":
    unittest.main()
