"""Testes de correcao com unittest; executar: python -m unittest discover -s tests -v."""
import builtins
from copy import deepcopy
from dataclasses import replace
import math
from pathlib import Path
import random
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'codigo'))
from darp import (BORDO, OTIMO, Avaliador, ConfigACO, Parametros, Rota, Solucao,
                  resolver_aco, verificar_solucao, ler_instancia, ler_res)
from darp.aco import (PontoACO, arcos, atualizar_arquivo, atualizar_feromonios,
                      insercoes_pares, probabilidades, representantes, roleta,
                      inviabilidade_necessaria)
from darp.avaliador import ErroAgendamento, RotaTemporalmenteInviavel
from darp.instancia import Instancia, No, reduzir
from darp import pareto

ROOT = Path(__file__).resolve().parents[1]


def pequena(n=1, m=None, Q=2):
    nos = [No(0, 0, 0, 0, 0, 0, 100)]
    nos += [No(i, i, 0, 0, 1, float(i), 100) for i in range(1, n + 1)]
    nos += [No(n + i, i + 2, 0, 0, -1, 0, 100) for i in range(1, n + 1)]
    nos += [No(2 * n + 1, 0, 0, 0, 0, 0, 100)]
    return Instancia('manual', m or n, n, 100, Q, 100, nos, 'manual')


class AvaliadorTests(unittest.TestCase):
    def test_calculo_manual_e_espera(self):
        inst = pequena()
        inst.nos[1] = replace(inst.nos[1], q=2)
        inst.nos[2] = replace(inst.nos[2], q=-2)
        sol, av = Solucao([Rota([1, 2])]), Avaliador(inst)
        r = av.avaliar_com_B(sol, {1: 1, 2: 3}, {0: 0})
        self.assertTrue(r.viavel, r.violacoes)
        self.assertEqual(r.objetivos, (6, 0))
        self.assertEqual(verificar_solucao(inst, sol, r.agendas).objetivos, (6, 0))
        self.assertEqual(av.avaliar_com_B(sol, {1: 5, 2: 7}, {0: 0}).f2, 8)

    def test_agenda_impossivel_rejeitada(self):
        inst = pequena()
        inst.nos[1] = replace(inst.nos[1], e=10)
        sol = Solucao([Rota([1, 2])])
        r = Avaliador(inst).avaliar_com_B(sol, {1: 0, 2: 0}, {0: 0})
        self.assertFalse(r.viavel)
        self.assertFalse(verificar_solucao(inst, sol, r.agendas).viavel)
        self.assertTrue(any('inferior' in e for e in r.violacoes))
        self.assertTrue(any('deslocamento' in e for e in r.violacoes))

    def test_estrutura_invalida_nao_agendada(self):
        inst = pequena(2)
        for seq in ([1, 1, 3, 2, 4], [1, 99], [3, 1, 2, 4], []):
            with self.subTest(seq=seq), patch.object(Avaliador, 'agendar', side_effect=AssertionError):
                self.assertFalse(Avaliador(inst).avaliar(Solucao([Rota(seq)])).viavel)

    def test_agenda_incompleta_ou_nao_finita(self):
        inst, sol = pequena(), Solucao([Rota([1, 2])])
        av = Avaliador(inst)
        self.assertFalse(av.avaliar_com_B(sol, {}, {}).viavel)
        self.assertFalse(av.avaliar_com_B(sol, {1: math.nan, 2: 3}, {0: 0}).viavel)

    def test_restricoes_isoladas(self):
        for caso in ('janela', 'deposito', 'capacidade', 'duracao', 'bordo'):
            inst, sol = pequena(), Solucao([Rota([1, 2])])
            if caso == 'janela': inst.nos[2] = replace(inst.nos[2], l=2)
            if caso == 'deposito': inst.nos[0] = replace(inst.nos[0], e=1)
            if caso == 'capacidade': inst.Q = 0
            if caso == 'duracao': inst.T_max = 5
            if caso == 'bordo': inst.L_arquivo = 1
            with self.subTest(caso=caso):
                r = Avaliador(inst).avaliar_com_B(sol, {1: 1, 2: 3}, {0: 0})
                self.assertFalse(r.viavel)
                self.assertFalse(verificar_solucao(inst, sol, r.agendas).viavel)

    def test_carga_negativa_e_final_nao_nula(self):
        for demanda_coleta, demanda_entrega in ((-1, 1), (1, 0)):
            inst = pequena()
            inst.nos[1] = replace(inst.nos[1], q=demanda_coleta)
            inst.nos[2] = replace(inst.nos[2], q=demanda_entrega)
            sol = Solucao([Rota([1, 2])])
            r = Avaliador(inst).avaliar_com_B(sol, {1: 1, 2: 3}, {0: 0})
            self.assertFalse(r.viavel)
            self.assertFalse(verificar_solucao(inst, sol, r.agendas).viavel)

    def test_auditor_independe_de_campos_derivados(self):
        inst, sol = pequena(), Solucao([Rota([1, 2])])
        r = Avaliador(inst).avaliar(sol, politica=BORDO)
        ag = r.agendas[0]
        ag.distancia, ag.R, ag.carga = -999, {}, {}
        with patch.object(Avaliador, 'avaliar', side_effect=AssertionError):
            check = verificar_solucao(inst, sol, r.agendas)
        self.assertTrue(check.viavel)
        self.assertEqual(check.objetivos, (6, 0))

    def test_solucoes_publicadas_e_tolerancia(self):
        for nome in ('pr01', 'pr07'):
            inst = ler_instancia(ROOT / 'dados/tabu' / nome)
            pub = ler_res(ROOT / 'dados/tabu' / (nome + '.res'))
            par = Parametros(tolerancia=.02)
            r = Avaliador(inst, par).avaliar_com_B(pub.solucao, pub.B, pub.partidas)
            check = verificar_solucao(inst, pub.solucao, r.agendas, par)
            self.assertTrue(r.viavel, r.violacoes)
            self.assertTrue(check.viavel, check.violacoes)
            self.assertAlmostEqual(check.f1, pub.distancia, delta=.005)
            self.assertAlmostEqual(check.f2, r.f2)

    def test_otimo_sem_dependencia_nao_faz_fallback(self):
        original = builtins.__import__
        def importar(nome, *args, **kwargs):
            if nome.startswith(('scipy', 'numpy')): raise ImportError('teste')
            return original(nome, *args, **kwargs)
        av = Avaliador(pequena(), Parametros(exigir_otimo=True))
        with patch('builtins.__import__', side_effect=importar):
            with self.assertRaises(ErroAgendamento): av.agendar(Rota([1, 2]))
            with self.assertRaises(ErroAgendamento):
                resolver_aco(pequena(), config=ConfigACO(politica=OTIMO))
            fallback = Avaliador(pequena()).agendar(Rota([1, 2]))
            self.assertEqual(fallback.politica_efetiva, BORDO)
            self.assertEqual(fallback.status_agendamento, 'fallback_dependencia')

    def test_status_pl_estrito(self):
        for status, excecao in ((2, RotaTemporalmenteInviavel), (4, ErroAgendamento)):
            with patch('scipy.optimize.linprog', return_value=SimpleNamespace(
                    success=False, status=status, message='teste')):
                with self.assertRaises(excecao):
                    Avaliador(pequena(), Parametros(exigir_otimo=True)).agendar(Rota([1, 2]))

    def test_otimo_respeita_janelas_do_deposito(self):
        inst = pequena()
        inst.nos[0] = replace(inst.nos[0], l=0)
        inst.nos[1] = replace(inst.nos[1], e=10)
        inst.nos[3] = replace(inst.nos[3], e=20)
        par = Parametros(exigir_otimo=True)
        sol = Solucao([Rota([1, 2])])
        r = Avaliador(inst, par).avaliar(sol)
        self.assertTrue(r.viavel, r.violacoes)
        self.assertTrue(verificar_solucao(inst, sol, r.agendas, par).viavel)
        self.assertEqual(r.agendas[0].partida, 0)
        self.assertGreaterEqual(r.agendas[0].retorno, 20)


class ACOTests(unittest.TestCase):
    def test_insercoes_preservam_pares_e_origem(self):
        seq = [1, 3]
        saidas = list(insercoes_pares(seq, 2, 4))
        self.assertEqual(len(saidas), 6)
        self.assertEqual(seq, [1, 3])
        for s in saidas:
            self.assertLess(s.index(1), s.index(3))
            self.assertLess(s.index(2), s.index(4))
            self.assertEqual(sorted(s), [1, 2, 3, 4])

    def test_probabilidades_e_roleta(self):
        for deltas in ([(1, 2), (2, 1)], [(0, 0)] * 3, [(-5, 2), (0, 2)]):
            ps = probabilidades(deltas, [1.] * len(deltas), .5, 1, 2)
            self.assertAlmostEqual(sum(ps), 1)
            self.assertTrue(all(math.isfinite(p) and p > 0 for p in ps))
            rng = random.Random(4)
            self.assertTrue(all(0 <= roleta(ps, rng) < len(ps) for _ in range(100)))
        with self.assertRaises(ValueError): probabilidades([(1, 2)], [0], .5, 1, 2)

    def test_feromonios_e_extremos(self):
        pontos = [PontoACO(i, 30 - i, Solucao([Rota([1, 2])]), [], .5) for i in range(25)]
        elite = representantes(pontos, 20)
        self.assertEqual(len(elite), 20)
        self.assertIs(elite[0], pontos[0])
        self.assertIs(elite[-1], pontos[-1])
        tau = [[1.] * 4 for _ in range(4)]
        atualizar_feromonios(tau, pontos, ConfigACO(), 3)
        self.assertAlmostEqual(tau[0][1], 1.9)
        self.assertAlmostEqual(tau[1][0], .9)
        atualizar_feromonios(tau, [], ConfigACO(evaporacao=1), 3)
        self.assertTrue(all(t == .01 for linha in tau for t in linha))
        self.assertEqual(arcos([], 3), set())

    def test_arquivo_sem_alias_duplicatas_ou_dominados(self):
        arquivo = []
        for x, y in ((1, 4), (2, 2), (4, 1), (3, 3), (2, 2)):
            ponto = PontoACO(x, y, Solucao([Rota([1, 2])]), [], .5)
            atualizar_arquivo(arquivo, ponto)
            ponto.solucao.rotas[0].sequencia.clear()
        self.assertEqual([p.objetivos for p in arquivo], [(1, 4), (2, 2), (4, 1)])
        self.assertTrue(all(p.solucao.rotas[0].sequencia == [1, 2] for p in arquivo))
        self.assertEqual(pareto.hipervolume([p.objetivos for p in arquivo], (5, 5)), 11)
        self.assertEqual(pareto.cobertura([p.objetivos for p in arquivo], [p.objetivos for p in arquivo]), 0)

    def test_aco_bordo_sem_solvers(self):
        original = builtins.__import__
        def importar(nome, *args, **kwargs):
            if nome.startswith(('numpy', 'scipy', 'gurobipy')):
                raise AssertionError('solver chamado pela ACO-BORDO')
            return original(nome, *args, **kwargs)
        with patch('builtins.__import__', side_effect=importar):
            r = resolver_aco(pequena(3), config=ConfigACO(formigas=4, iteracoes=3))
        self.assertTrue(r.fronteira)
        self.assertEqual(r.chamadas_pl, 0)

    def test_repetibilidade_orcamento_e_auditoria(self):
        for politica in (BORDO, OTIMO):
            inst = pequena(3)
            config = ConfigACO(politica=politica, formigas=4, iteracoes=10, max_avaliacoes=91)
            a, b = resolver_aco(inst, config=config), resolver_aco(inst, config=config)
            self.assertEqual(a.consultas, 91)
            self.assertEqual(a.motivo_parada, 'avaliacoes')
            self.assertEqual([(p.objetivos, p.solucao) for p in a.solucoes],
                             [(p.objetivos, p.solucao) for p in b.solucoes])
            for p in a.solucoes:
                self.assertTrue(verificar_solucao(inst, p.solucao, p.agendas).viavel)
            if a.solucoes and a.fronteira:
                antes = deepcopy(a.fronteira)
                a.solucoes[0].solucao.rotas[0].sequencia.clear()
                self.assertEqual(a.fronteira, antes)

    def test_fracasso_nao_declara_instancia_inviavel(self):
        inst = pequena()
        inst.nos[1] = replace(inst.nos[1], q=3)
        inst.nos[2] = replace(inst.nos[2], q=-3)
        r = resolver_aco(inst, config=ConfigACO(formigas=2, iteracoes=3))
        self.assertEqual(r.fracassadas, 6)
        self.assertEqual(r.solucoes, [])
        self.assertEqual(inst.m, 1)
        self.assertEqual(r.motivo_parada, 'iteracoes')

    def test_baseline_feromonio_fixo(self):
        r = resolver_aco(pequena(2), config=ConfigACO(formigas=2, iteracoes=3, aprender=False))
        self.assertTrue(all(v == 1 for linha in r.feromonios for v in linha))

    def test_primeira_iteracao_iguala_baseline_antes_do_reforco(self):
        inst = pequena(3)
        config = ConfigACO(formigas=4, iteracoes=1, seed=9)
        a = resolver_aco(inst, config=config)
        b = resolver_aco(inst, config=replace(config, aprender=False))
        self.assertEqual(a.consultas, b.consultas)
        self.assertEqual([(p.objetivos, p.solucao) for p in a.solucoes],
                         [(p.objetivos, p.solucao) for p in b.solucoes])

    def test_interrupcao_sem_solucao_parcial(self):
        r = resolver_aco(pequena(3), config=ConfigACO(formigas=2, max_avaliacoes=1))
        self.assertEqual(r.consultas, 1)
        self.assertEqual(r.interrompidas, 1)
        self.assertEqual(r.solucoes, [])
        r = resolver_aco(pequena(3), config=ConfigACO(limite_segundos=1e-12))
        self.assertEqual(r.motivo_parada, 'tempo')

    def test_parametros_invalidos(self):
        for kwargs in ({'formigas': 1}, {'evaporacao': 2}, {'b': math.nan},
                       {'tau_min': 0}, {'max_avaliacoes': 0}, {'politica': 'cedo'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): ConfigACO(**kwargs)
        with self.assertRaises(ValueError): reduzir(pequena(2), [1, 1])

    def test_operadores_em_milhares_de_construcoes(self):
        inst = pequena(3)
        rng = random.Random(75)
        for _ in range(10000):
            seq = []
            ordem = [1, 2, 3]
            rng.shuffle(ordem)
            for i in ordem:
                candidatos = list(insercoes_pares(seq, i, i + 3))
                seq = rng.choice(candidatos)
            self.assertEqual(Solucao([Rota(seq)]).conferir_estrutura(inst), [])

    def test_escalas_e_simetria_de_rotas(self):
        inst = pequena(2)
        config = ConfigACO(formigas=2, iteracoes=2)
        r = resolver_aco(inst, config=config)
        for ponto in r.fronteira:
            dobro = verificar_solucao(inst, ponto.solucao, ponto.agendas, Parametros(phi=2))
            self.assertAlmostEqual(dobro.f1, 2 * ponto.f1)
            self.assertAlmostEqual(dobro.f2, ponto.f2)
            sol = Solucao(list(reversed(ponto.solucao.rotas)))
            rev = verificar_solucao(inst, sol, list(reversed(ponto.agendas)))
            self.assertAlmostEqual(rev.f1, ponto.f1)
            self.assertAlmostEqual(rev.f2, ponto.f2)

    def test_podas_necessarias_nao_eliminam_rotas_viaveis(self):
        from darp.exato import sequencias_viaveis
        inst, par = pequena(3), Parametros(exigir_otimo=True)
        av = Avaliador(inst, par)
        for seq in sequencias_viaveis(inst, (1, 2, 3)):
            try:
                ag, erros = av.avaliar_rota(Rota(seq))
            except RotaTemporalmenteInviavel:
                continue
            if not erros:
                self.assertFalse(inviabilidade_necessaria(inst, seq, par))


class ReferenciasTests(unittest.TestCase):
    def test_mip_e_enumeracao_em_tres_recortes(self):
        from darp.exato import fronteira_exata
        from darp.mip import SolverIndisponivel, fronteira_epsilon
        base = ler_instancia(ROOT / 'dados/tabu/pr01')
        for ids in ([1, 2, 3, 4, 5], [13, 14, 15, 16, 17], [1, 2, 13, 14, 15]):
            with self.subTest(ids=ids):
                inst = reduzir(base, ids, m=5)
                av = Avaliador(inst, Parametros(exigir_otimo=True))
                enum = fronteira_exata(inst, av, politica=OTIMO)
                try:
                    mip = fronteira_epsilon(inst)
                except SolverIndisponivel as erro:
                    self.skipTest(str(erro))
                except Exception as erro:
                    if type(erro).__name__ == 'GurobiError':
                        self.skipTest(str(erro))
                    raise
                self.assertEqual(len(enum), len(mip))
                for (f1, f2, _), ponto in zip(enum, mip):
                    self.assertEqual(ponto.status, 2)
                    self.assertAlmostEqual(ponto.f1, f1, delta=1e-3)
                    self.assertAlmostEqual(ponto.f2, f2, delta=1e-3)
                    r = av.avaliar_com_B(ponto.solucao, ponto.B, ponto.partidas)
                    self.assertTrue(verificar_solucao(inst, ponto.solucao, r.agendas).viavel)


if __name__ == '__main__':
    unittest.main()
