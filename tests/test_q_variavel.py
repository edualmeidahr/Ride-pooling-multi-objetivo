"""Regressões do modelo temporal e da decisão homogênea de capacidade."""
import contextlib
from copy import deepcopy
from dataclasses import replace
import io
import json
from pathlib import Path
import random
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from comum.avaliador import Avaliador
from comum.capacidade import ContextoCapacidades, chave_solucao
from comum.instancia import reduzir
from comum.solucao import Rota, Solucao
from comum.validacao import verificar_solucao
from implementacao1.exato import fronteira_exata
from implementacao3 import obter_metaheuristica
from implementacao3.base import ArquivoPareto
from implementacao3.base import ORCAMENTO_BUSCA
from implementacao3.colonia_formigas import ConfigACO, resolver_aco
from menu import executar, frente_global, preparar
from menu import menu

RAIZ = Path(__file__).resolve().parents[1]


class QVariavelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c, cls.inst, cls.par, _, _, _ = preparar('experimentos/validacao_emissoes.json')

    def contexto(self, qs=(1, 2, 5, 7, 10), **kw):
        return ContextoCapacidades(self.inst, self.par, qs, self.c['modelo_emissoes'], **kw)

    def agrupada(self, q=2):
        return Solucao([Rota([1, 2, 4, 3])], Q=q)

    def auditar(self, ctx, frente):
        for f1, f2, sol in frente:
            inst, av = ctx.obter(sol.Q)
            ev = Avaliador(inst, av.par).avaliar(sol)
            aud = verificar_solucao(inst, sol, ev.agendas, av.par)
            self.assertTrue(ev.viavel, ev.violacoes)
            self.assertTrue(aud.viavel, aud.violacoes)
            self.assertAlmostEqual(aud.f1, f1)
            self.assertAlmostEqual(aud.f2, f2)

    def test_regressao_exata_distancia(self):
        _, inst, par, _, _, _ = preparar('experimentos/exemplo_pequeno.json', [2])
        self.assertEqual([(a, b) for a, b, _ in fronteira_exata(inst, Avaliador(inst, par))],
                         [(46, 4.5), (92, 0)])

    def test_saida_deposito_limitada_permite_espera(self):
        inst = replace(self.inst, Q=2, nos=[replace(self.inst.nos[0], l=0), *self.inst.nos[1:]])
        av = Avaliador(inst, self.par)
        sol = self.agrupada()
        ev = av.avaliar(sol)
        self.assertTrue(ev.viavel, ev.violacoes)
        self.assertEqual(ev.agendas[0].partida, 0)
        self.assertTrue(verificar_solucao(inst, sol, ev.agendas, self.par).viavel)

    def test_duracao_inclui_espera_apos_saida_limitada(self):
        inst = replace(self.inst, Q=2, T_max=100,
                       nos=[replace(self.inst.nos[0], l=0), *self.inst.nos[1:]])
        self.assertFalse(Avaliador(inst, self.par).avaliar(self.agrupada()).viavel)

    def test_janela_inferior_retorno(self):
        inst = replace(self.inst, Q=2, nos=[*self.inst.nos[:-1], replace(self.inst.nos[-1], e=150, l=180)])
        ev = Avaliador(inst, self.par).avaliar(self.agrupada())
        self.assertTrue(ev.viavel, ev.violacoes)
        self.assertEqual(ev.agendas[0].retorno, 150)
        self.assertTrue(verificar_solucao(inst, self.agrupada(), ev.agendas, self.par).viavel)
        curto = replace(inst, T_max=100)
        self.assertFalse(Avaliador(curto, self.par).avaliar(self.agrupada()).viavel)

    def test_falha_numerica_nao_vira_bordo(self):
        av = self.contexto().obter(2)[1]
        with patch('scipy.optimize.linprog', return_value=SimpleNamespace(success=False, status=4)):
            with self.assertRaisesRegex(RuntimeError, 'Falha técnica'):
                av.avaliar(self.agrupada())

    def test_pl_respeita_minimo_bordo_em_matriz_explicita(self):
        inst = replace(self.inst, Q=2)
        tempo_original = inst.tempo
        inst.tempo = lambda i,j: 100 if (i,j) == (1,3) else tempo_original(i,j)
        ev = Avaliador(inst, self.par).avaliar(self.agrupada())
        self.assertTrue(ev.viavel, ev.violacoes)
        self.assertGreaterEqual(ev.agendas[0].R[1], 100-1e-6)
        self.assertTrue(verificar_solucao(inst, self.agrupada(), ev.agendas, self.par).viavel)

    def test_inviabilidade_linear_nao_e_aceita_por_fallback(self):
        av = self.contexto().obter(2)[1]
        with patch('scipy.optimize.linprog', return_value=SimpleNamespace(success=False, status=2)):
            self.assertFalse(av.avaliar(self.agrupada()).viavel)

    def test_agendas_externas_invalidas(self):
        av = self.contexto().obter(2)[1]
        for b in ({}, dict.fromkeys(range(1, 5), 0), dict.fromkeys(range(1, 5), float('nan'))):
            with self.subTest(b=b):
                self.assertFalse(av.avaliar_com_B(self.agrupada(), b, {0: 0}).viavel)

    def test_dominio_e_perfis_invalidos(self):
        for qs in ([], [True], [0], [1.5]):
            with self.subTest(qs=qs), self.assertRaises(ValueError):
                self.contexto(qs)
        with self.assertRaises(ValueError):
            self.contexto([21])
        modelo = deepcopy(self.c['modelo_emissoes'])
        modelo['veiculos'].append(dict(modelo['veiculos'][0]))
        with self.assertRaises(ValueError):
            ContextoCapacidades(self.inst, self.par, [2], modelo)
        with self.assertRaises(ValueError):
            self.contexto([2], construcao={'limite_pedidos_candidatos': 0})

    def test_demanda_indivisivel(self):
        inst = replace(self.inst, nos=[replace(n, q=2*n.q) for n in self.inst.nos])
        ctx = ContextoCapacidades(inst, self.par, [1, 2])
        self.assertEqual(ctx.excluidas, [1])
        self.assertEqual(ctx.viaveis, (2,))
        ctx = ContextoCapacidades(inst, self.par, [1])
        self.assertEqual(obter_metaheuristica('sa').otimizar(inst, Avaliador(inst), contextos=ctx).motivo_parada,
                         'inviavel_demanda')

    def test_contextos_q_phi_e_cache(self):
        ctx = self.contexto([1, 2, 4, 5, 6, 7])
        valores = {}
        for q in ctx.capacidades:
            ev = ctx.avaliar(self.agrupada(q))
            valores[q] = ev.f1
            self.assertEqual(ev.viavel, q >= 2)
        self.assertAlmostEqual(valores[5]/valores[4], 250/180)
        self.assertAlmostEqual(valores[7]/valores[6], 350/250)
        antes = ctx.obter(2)[1].contadores['chamadas_pl']
        ctx.avaliar(self.agrupada(2))
        self.assertEqual(antes, ctx.obter(2)[1].contadores['chamadas_pl'])
        with self.assertRaises(ValueError):
            ctx.obter(2)[1].avaliar(self.agrupada(5))
        with self.assertRaises(ValueError):
            ctx.avaliar(self.agrupada(3))
        with self.assertRaises(ValueError):
            ctx.avaliar(Solucao())

    def test_copia_e_arquivo_preservam_q(self):
        sol = self.agrupada(5)
        sol.partidas = {0: 28}
        copia = sol.copiar()
        copia.rotas[0].sequencia.clear()
        copia.partidas[0] = 0
        self.assertEqual(sol.rotas[0].sequencia, [1, 2, 4, 3])
        self.assertEqual(sol.partidas[0], 28)
        arquivo = ArquivoPareto()
        arquivo.adicionar(10, 5, sol)
        arquivo.adicionar(10, 5, self.agrupada(2))
        self.assertEqual(arquivo.pontos[0][2].Q, 2)
        arquivo.adicionar(9, 4, self.agrupada(7))
        self.assertEqual(len(arquivo), 1)
        self.assertEqual(arquivo.pontos[0][2].Q, 7)

    def test_reducao_repara_cobertura_e_frota(self):
        ctx = self.contexto([1, 2])
        sol = self.agrupada()
        nova = ctx.mudar(sol, 1, random.Random(42))
        self.assertIsNotNone(nova)
        self.assertEqual(nova.Q, 1)
        self.assertEqual(nova.veiculos_usados, 2)
        self.assertEqual(sol.Q, 2)
        self.assertFalse(nova.conferir_estrutura(ctx.obter(1)[0]))
        self.assertTrue(ctx.avaliar(nova).viavel)

    def test_reducao_sem_frota_rejeita(self):
        inst = replace(self.inst, m=1)
        ctx = ContextoCapacidades(inst, self.par, [1, 2])
        self.assertIsNone(ctx.mudar(self.agrupada(), 1, random.Random(42)))
        self.assertEqual(ctx.movimentos[-1]['para'], 1)
        self.assertFalse(ctx.movimentos[-1]['aceito'])

    def test_movimento_q_com_um_pedido(self):
        inst = reduzir(self.inst, [1])
        ctx = ContextoCapacidades(inst, self.par, [2, 5, 10])
        nova = ctx.perturbar(ctx.individual(2), random.Random(1), prob_q=1)
        self.assertIn(nova.Q, [5, 10])
        self.assertTrue(ctx.avaliar(nova).viavel)

    def test_normalizacao_global_invariante_unidade(self):
        ctx = self.contexto([4, 5, 6, 7])
        modelo = deepcopy(self.c['modelo_emissoes'])
        for p in modelo['veiculos']:
            p['phi_g_km'] /= 1000
        kg = ContextoCapacidades(self.inst, self.par, [4, 5, 6, 7], modelo)
        notas = []
        for q in ctx.capacidades:
            f1 = ctx.avaliar(self.agrupada(q)).f1 / ctx.escalas[0]
            self.assertAlmostEqual(f1, kg.avaliar(self.agrupada(q)).f1 / kg.escalas[0])
            notas.append(f1)
        self.assertGreater(notas[1], notas[0])
        self.assertGreater(notas[3], notas[2])

    def test_algoritmos_alteram_q_e_auditam(self):
        for nome in ('sa', 'ga', 'grasp', 'aco'):
            with self.subTest(nome=nome):
                ctx = self.contexto([1, 2, 5])
                res = obter_metaheuristica(nome, seed=42, **self.c['algoritmos'][nome]).otimizar(
                    self.inst, Avaliador(self.inst, self.par), contextos=ctx)
                self.assertTrue(res.fronteira)
                self.auditar(ctx, res.fronteira)
                if nome == 'aco':
                    self.assertGreaterEqual(len(res.estatisticas['visitas_q']), 2)
                    self.assertEqual(set(res.historico[-1]['feromonios_q']), {1, 2, 5})
                else:
                    self.assertTrue(any(e['de'] != e['para'] and e['aceito']
                                        for e in res.estatisticas['movimentos_q']))

    def test_dominio_unitario_equivale_a_fixo(self):
        for nome in ('sa', 'ga', 'grasp', 'aco'):
            with self.subTest(nome=nome):
                inst, av = self.contexto([2]).obter(2)
                parametros = self.c['algoritmos'][nome]
                fixo = obter_metaheuristica(nome, seed=42, **parametros).otimizar(inst, av)
                ctx = self.contexto([2])
                variavel = obter_metaheuristica(nome, seed=42, **parametros).otimizar(inst, av, contextos=ctx)
                self.assertEqual([(a,b,chave_solucao(s)) for a,b,s in fixo.fronteira],
                                 [(a,b,chave_solucao(s)) for a,b,s in variavel.fronteira])

    def test_orcamento_preserva_solucoes_completas(self):
        for nome in ('sa', 'ga', 'grasp', 'aco'):
            with self.subTest(nome=nome):
                ctx = self.contexto([1, 2, 5], max_consultas_rotas=25)
                res = obter_metaheuristica(nome, seed=42, **self.c['algoritmos'][nome]).otimizar(
                    self.inst, Avaliador(self.inst, self.par), contextos=ctx)
                self.assertLessEqual(ctx.consultas, 25)
                self.assertEqual(ctx.consultas, res.estatisticas['contadores']['consultas_rotas'])
                self.assertEqual(res.avaliacoes, res.estatisticas['contadores']['solucoes'])
                self.auditar(ctx, res.fronteira)

    def test_orcamento_padrao_eh_dez(self):
        from implementacao3.ga import AlgoritmoGenetico
        from implementacao3.grasp import GRASP
        from implementacao3.ga_biblioteca import GeneticoBiblioteca
        from implementacao3.pso_biblioteca import PSOBiblioteca
        from implementacao3.sa_biblioteca import AnnealingBiblioteca
        self.assertEqual(ORCAMENTO_BUSCA, 10)
        self.assertEqual(ConfigACO().iteracoes, 10)
        self.assertEqual(ConfigACO().formigas, 10)
        self.assertEqual(AlgoritmoGenetico().geracoes, 10)
        self.assertEqual(GRASP().max_iteracoes, 10)
        self.assertEqual(GeneticoBiblioteca().geracoes, 10)
        self.assertEqual(PSOBiblioteca().iteracoes, 10)
        self.assertEqual(AnnealingBiblioteca().iteracoes, 10)

    def test_aco_sem_aprendizado(self):
        ctx = self.contexto([1, 2, 5])
        cfg = ConfigACO(politica='otimo', formigas=3, iteracoes=2, aprender=False)
        res = resolver_aco(self.inst, self.par, cfg, contextos=ctx)
        self.assertEqual(set(res.feromonios_q.values()), {1})
        self.assertTrue(all(t == 1 for linha in res.feromonios for t in linha))

    def test_referencia_completa_equivale_reduzida(self):
        frentes = []
        for qs in (list(range(1, 11)), [4, 6, 10]):
            ctx = self.contexto(qs)
            pontos = []
            for q in qs:
                inst, av = ctx.obter(q)
                for a, b, sol in fronteira_exata(inst, av):
                    sol.Q = q
                    pontos.append((a,b,sol))
            frentes.append([(a,b) for a,b,_ in frente_global(pontos)])
        self.assertEqual(*frentes)

    def test_exemplo_compete_entre_categorias(self):
        c, inst, par, qs, _, _ = preparar('experimentos/q_variavel_exemplo.json')
        ctx = ContextoCapacidades(inst, par, qs, c['modelo_emissoes'])
        pontos = []
        for q in qs:
            i, a = ctx.obter(q)
            for f1, f2, sol in fronteira_exata(i, a):
                sol.Q = q
                pontos.append((f1,f2,sol))
        frente = frente_global(pontos)
        self.assertEqual({sol.Q for _,_,sol in frente}, {4, 6})
        self.auditar(ctx, frente)

    def test_exportacao_retomada_e_referencia_global(self):
        with tempfile.TemporaryDirectory(dir=RAIZ / 'resultados') as temp, contextlib.redirect_stdout(io.StringIO()):
            args = dict(config_path='experimentos/q_variavel_exemplo.json', modo='comparar', saida=temp)
            registro, _ = executar(**args)
            self.assertEqual(registro['versao_formato'], 2)
            self.assertEqual(registro['referencias']['global']['tipo'], 'exata')
            exata = registro['referencias']['global']['pontos']
            for r in registro['execucoes']:
                self.assertIsNone(r['Q'])
                for p in r['pontos']:
                    self.assertIn(p['Q'], [4,6,10])
                    self.assertIn('retorno', p['agendas'][0])
                    self.assertTrue(any(a <= p['f1']+1e-6 and b <= p['f2']+1e-6 for a,b in exata))
            retomado, _ = executar(**args, retomar=True)
            self.assertEqual(retomado['execucoes'], json.loads(json.dumps(registro['execucoes'])))
            with self.assertRaises(ValueError):
                executar(**args, retomar=True, capacidades=[4,6])
            parcial = deepcopy(retomado)
            parcial['concluida'] = False
            parcial['execucoes'] = parcial['execucoes'][:2]
            (Path(temp)/'execucoes.json').write_text(json.dumps(parcial), encoding='utf-8')
            terminado, _ = executar(**args, retomar=True)
            self.assertEqual(len(terminado['execucoes']), 6)

    def test_modo_fixo_exportacao_e_retomada(self):
        with tempfile.TemporaryDirectory(dir=RAIZ / 'resultados') as temp, contextlib.redirect_stdout(io.StringIO()):
            args = dict(config_path='experimentos/exemplo_pequeno.json', modo='comparar', saida=temp,
                        capacidades=[2], capacidade='fixo')
            registro, _ = executar(**args)
            self.assertEqual(len(registro['execucoes']), 6)
            self.assertTrue(all(p['Q'] == 2 for r in registro['execucoes'] for p in r['pontos']))
            self.assertTrue(executar(**args, retomar=True)[0]['concluida'])

    def test_menu_opcao_sete_seleciona_busca_variavel(self):
        with patch('builtins.input', side_effect=['7', '2', '1, 2, 5', '4', '0']), \
                patch('menu.executar') as chamada, contextlib.redirect_stdout(io.StringIO()):
            menu()
        self.assertEqual(chamada.call_count, 1)
        self.assertEqual(chamada.call_args.kwargs['capacidade'], 'variavel')
        self.assertEqual(chamada.call_args.kwargs['capacidades'], [1, 2, 5])

    def test_menu_atalho_cem_preserva_modo_fixo(self):
        with patch('builtins.input', side_effect=['6', '0']), \
                patch('menu.executar') as chamada, contextlib.redirect_stdout(io.StringIO()):
            menu()
        self.assertEqual(chamada.call_args.args[0], 'experimentos/comparacao_100_corridas.json')
        self.assertEqual(chamada.call_args.args[1], 'comparar_aproximados')
        self.assertNotIn('capacidade', chamada.call_args.kwargs)


if __name__ == '__main__':
    unittest.main()
