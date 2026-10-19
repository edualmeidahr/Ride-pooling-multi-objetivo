"""Integração com motores externos e preservação da interface do projeto."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import random
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from comum.avaliador import Avaliador
from comum.capacidade import ContextoCapacidades, LimiteBusca, chave_solucao
from comum.solucao import Rota, Solucao
from comum.validacao import verificar_solucao
from implementacao3 import (obter_metaheuristica, selecionar_algoritmos,
                            METODOS, METODOS_PADRAO, METODOS_BIBLIOTECAS)
from implementacao3.suporte_bibliotecas import CodificacaoRotas, quota_trajetoria, LimiteTrajetoria
from menu import executar, preparar, menu

RAIZ = Path(__file__).resolve().parents[1]
DEPENDENCIAS = all(importlib.util.find_spec(p) for p in ('pymoo', 'simanneal'))


class BibliotecaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c, cls.inst, cls.par, _, _, _ = preparar('experimentos/q_variavel_exemplo.json')

    def contexto(self, qs=(4,6,10), limite=None):
        return ContextoCapacidades(self.inst, self.par, qs, self.c['modelo_emissoes'],
                                   max_consultas_rotas=limite)

    def rodar(self, nome, qs=(4,6,10), limite=None, seed=42):
        ctx = self.contexto(qs, limite)
        inst, av = ctx.obter(qs[0])
        res = obter_metaheuristica(nome, seed=seed, **self.c['algoritmos'][nome]).otimizar(inst, av, contextos=ctx)
        return ctx, res

    def auditar(self, ctx, res):
        for f1, f2, sol in res.fronteira:
            inst, av = ctx.obter(sol.Q)
            ev = Avaliador(inst, av.par).avaliar(sol)
            audit = verificar_solucao(inst, sol, ev.agendas, av.par)
            self.assertTrue(audit.viavel, audit.violacoes)
            self.assertAlmostEqual(audit.f1, f1)
            self.assertAlmostEqual(audit.f2, f2)

    def test_catalogo_grupos_e_padrao(self):
        self.assertEqual(len(METODOS), 7)
        self.assertEqual(selecionar_algoritmos(), METODOS_PADRAO)
        self.assertEqual(selecionar_algoritmos(['bibliotecas']), METODOS_BIBLIOTECAS)
        self.assertEqual(selecionar_algoritmos('todos'), tuple(METODOS))
        self.assertEqual(selecionar_algoritmos(['ga','sa_lib']), ('ga','sa_lib'))
        for nomes in ([], ['todos','ga'], ['desconhecido']):
            with self.subTest(nomes=nomes), self.assertRaises(ValueError):
                selecionar_algoritmos(nomes)

    def test_importacao_tardia(self):
        proc = subprocess.run([sys.executable, '-c',
            "import implementacao3,menu,sys; assert 'pymoo' not in sys.modules; assert 'simanneal' not in sys.modules"],
            cwd=RAIZ, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_dependencia_ausente_erro_sem_fallback(self):
        for nome in METODOS_BIBLIOTECAS:
            with self.subTest(nome=nome), patch('implementacao3.suporte_bibliotecas.import_module', side_effect=ImportError):
                with self.assertRaisesRegex(RuntimeError, 'python -m pip install -r requirements.txt'):
                    self.rodar(nome)

    def test_codec_extremos_cobertura_e_precedencia(self):
        ctx = self.contexto()
        codec = CodificacaoRotas(ctx)
        vetores = [np.zeros(codec.dimensoes), np.ones(codec.dimensoes),
                   *np.random.default_rng(4).random((40,codec.dimensoes))]
        for x in vetores:
            sol = codec.decodificar(x)
            self.assertFalse(sol.conferir_estrutura(ctx.obter(sol.Q)[0]))
            self.assertIn(sol.Q, ctx.viaveis)
            self.assertEqual(sol.nos_visitados().__len__(), 2*self.inst.n)
            self.assertEqual(chave_solucao(sol), chave_solucao(codec.decodificar(codec.codificar(sol))))
        self.assertEqual(codec.decodificar(vetores[0]).Q, 4)
        self.assertEqual(codec.decodificar(vetores[1]).Q, 10)
        self.assertEqual(codec.decodificar(vetores[0]).rotas[-1].sequencia, [])
        self.assertEqual(codec.decodificar(vetores[1]).rotas[0].sequencia, [])

    def test_codec_nao_presume_viabilidade(self):
        ctx = self.contexto([4])
        sol = CodificacaoRotas(ctx).decodificar(np.zeros(7))
        self.assertFalse(ctx.avaliar(sol).viavel)  # dois grupos de 3 no mesmo veículo Q=4

    def test_codec_valores_invalidos(self):
        codec = CodificacaoRotas(self.contexto())
        for x in ([], [float('nan')]*7, [float('inf')]*7):
            with self.subTest(x=x), self.assertRaises(ValueError):
                codec.decodificar(x)
        with self.assertRaises(ValueError):
            codec.codificar(Solucao([Rota([1,3])], Q=4))

    def test_quotas_incluem_resto_e_restauram_contexto(self):
        ctx = self.contexto(limite=10)
        consumir = ctx.consumir
        tamanhos = []
        for i in range(3):
            inicio = ctx.consultas
            with self.assertRaises(LimiteTrajetoria):
                with quota_trajetoria(ctx, i, 3):
                    while True:
                        ctx.consumir()
            tamanhos.append(ctx.consultas-inicio)
            self.assertEqual(ctx.consumir, consumir)
        self.assertEqual(tamanhos, [3,3,4])
        with self.assertRaises(LimiteBusca):
            ctx.consumir()

    def test_validacao_parametros(self):
        for nome, kwargs in [('ga_lib', {'tamanho_populacao':1}), ('pso_lib', {'iteracoes':0}),
                             ('sa_lib', {'temp_final':0}), ('sa_lib', {'pesos':[]}),
                             ('pso_lib', {'pesos':[[1,-1]]}), ('ga_lib', {'seed':True})]:
            with self.subTest(nome=nome, kwargs=kwargs), self.assertRaises(ValueError):
                obter_metaheuristica(nome, **kwargs)

    @unittest.skipUnless(DEPENDENCIAS, 'instale requirements.txt para as integracoes reais')
    def test_motores_prontos_realmente_executados(self):
        from pymoo.algorithms.moo.nsga2 import NSGA2
        from pymoo.algorithms.soo.nonconvex import pso
        from simanneal import Annealer
        with patch.object(NSGA2, '_advance', autospec=True, side_effect=NSGA2._advance) as motor:
            self.rodar('ga_lib')
            self.assertGreater(motor.call_count, 0)
        with patch.object(pso, 'pso_equation', wraps=pso.pso_equation) as motor:
            self.rodar('pso_lib')
            self.assertGreater(motor.call_count, 0)
        with patch.object(Annealer, 'anneal', autospec=True, side_effect=Annealer.anneal) as motor:
            self.rodar('sa_lib')
            self.assertEqual(motor.call_count, 3)

    @unittest.skipUnless(DEPENDENCIAS, 'instale requirements.txt')
    def test_fronteira_pequena_auditada_e_metadados(self):
        for nome in METODOS_BIBLIOTECAS:
            with self.subTest(nome=nome):
                ctx, res = self.rodar(nome)
                self.auditar(ctx, res)
                self.assertEqual({s.Q for _,_,s in res.fronteira}, {4,6})
                self.assertEqual(res.estatisticas['origem'], 'biblioteca')
                self.assertIn(res.estatisticas['biblioteca'], ['pymoo','simanneal'])
                self.assertTrue(res.estatisticas['versao_biblioteca'])
                self.assertTrue(res.historico)
                self.assertEqual(res.avaliacoes, res.estatisticas['contadores']['solucoes'])

    @unittest.skipUnless(DEPENDENCIAS, 'instale requirements.txt')
    def test_fixo_variavel_unitario_e_reprodutibilidade(self):
        for nome in METODOS_BIBLIOTECAS:
            with self.subTest(nome=nome):
                ctx, primeiro = self.rodar(nome, [6], seed=-7)
                _, segundo = self.rodar(nome, [6], seed=-7)
                chave = lambda r: [(a,b,chave_solucao(s)) for a,b,s in r.fronteira]
                self.assertEqual(chave(primeiro), chave(segundo))
                inst, av = ctx.obter(6)
                fixo = obter_metaheuristica(nome, seed=-7, **self.c['algoritmos'][nome]).otimizar(inst, av)
                self.assertEqual(chave(primeiro), chave(fixo))
                self.auditar(ctx, fixo)

    @unittest.skipUnless(DEPENDENCIAS, 'instale requirements.txt')
    def test_orcamento_interrupcao_e_arquivo(self):
        for nome in METODOS_BIBLIOTECAS:
            for limite in (1, 2, 3, 25):
                with self.subTest(nome=nome, limite=limite):
                    ctx, res = self.rodar(nome, limite=limite)
                    self.assertLessEqual(ctx.consultas, limite)
                    self.assertEqual(res.motivo_parada, 'consultas_rotas')
                    if limite == 25:
                        self.assertTrue(res.fronteira)
                    self.assertEqual(res.estatisticas['origem'], 'biblioteca')
                    self.auditar(ctx, res)

    @unittest.skipUnless(DEPENDENCIAS, 'instale requirements.txt')
    def test_sa_restaura_random_e_handler_mesmo_com_limite(self):
        estado, handler = random.getstate(), signal.getsignal(signal.SIGINT)
        self.rodar('sa_lib', limite=20)
        self.assertEqual(random.getstate(), estado)
        self.assertEqual(signal.getsignal(signal.SIGINT), handler)
        self.rodar('sa_lib')
        self.assertEqual(random.getstate(), estado)
        self.assertEqual(signal.getsignal(signal.SIGINT), handler)

    @unittest.skipUnless(DEPENDENCIAS, 'instale requirements.txt')
    def test_interrupcao_do_sa_preserva_arquivo_e_estado_global(self):
        from simanneal import Annealer
        original = Annealer.anneal
        estado, handler = random.getstate(), signal.getsignal(signal.SIGINT)
        def interromper(motor):
            motor.set_user_exit(signal.SIGINT, None)
            return original(motor)
        with patch.object(Annealer, 'anneal', autospec=True, side_effect=interromper) as chamada:
            ctx, res = self.rodar('sa_lib')
        self.assertEqual(chamada.call_count, 1)
        self.assertEqual(res.motivo_parada, 'interrompida')
        self.assertTrue(res.fronteira)
        self.assertTrue(res.historico)
        self.auditar(ctx, res)
        self.assertEqual(random.getstate(), estado)
        self.assertEqual(signal.getsignal(signal.SIGINT), handler)

    @unittest.skipUnless(DEPENDENCIAS, 'instale requirements.txt')
    def test_exportacao_todos_retomada_e_versao_biblioteca(self):
        with tempfile.TemporaryDirectory(dir=RAIZ/'resultados') as pasta, redirect_stdout(io.StringIO()):
            args = dict(config_path='experimentos/q_variavel_exemplo.json', modo='comparar',
                        algoritmos=['todos'], saida=pasta)
            registro, _ = executar(**args)
            self.assertEqual(len(registro['execucoes']), 9)
            for r in registro['execucoes']:
                if r['metodo'] in METODOS_BIBLIOTECAS:
                    self.assertEqual(r['origem'], 'biblioteca')
                    self.assertTrue(r['versao_biblioteca'])
            self.assertTrue(executar(**args, retomar=True)[0]['concluida'])
            with patch('menu.versao_pacote', return_value='mudou'), self.assertRaises(ValueError):
                executar(**args, retomar=True)
            registro['concluida'] = False
            registro['execucoes'] = registro['execucoes'][:6]
            (Path(pasta)/'execucoes.json').write_text(json.dumps(registro), encoding='utf-8')
            self.assertEqual(len(executar(**args, retomar=True)[0]['execucoes']), 9)

    def test_menu_novas_selecoes_sem_alterar_padrao(self):
        escolhas = {'4':METODOS_PADRAO, '6':('ga_lib',), '7':('sa_lib',), '8':('pso_lib',),
                    '9':METODOS_BIBLIOTECAS, '10':tuple(METODOS)}
        for opcao, esperados in escolhas.items():
            with self.subTest(opcao=opcao), patch('builtins.input', side_effect=['7','2','',opcao,'0']), \
                    patch('menu.executar') as chamada, redirect_stdout(io.StringIO()):
                menu()
                self.assertEqual(chamada.call_args.kwargs['algoritmos'], esperados)

    @unittest.skipUnless(DEPENDENCIAS, 'instale requirements.txt')
    def test_exportacao_e_retomada_em_q_fixo(self):
        with tempfile.TemporaryDirectory(dir=RAIZ/'resultados') as pasta, redirect_stdout(io.StringIO()):
            args = dict(config_path='experimentos/q_variavel_exemplo.json', modo='metaheuristica',
                        algoritmos=['bibliotecas'], capacidades=[6], capacidade='fixo', saida=pasta)
            registro, _ = executar(**args)
            self.assertEqual(len(registro['execucoes']), 3)
            for r in registro['execucoes']:
                self.assertEqual(r['origem'], 'biblioteca')
                self.assertTrue(r['versao_biblioteca'])
                self.assertTrue(r['pontos'])
                self.assertTrue(all(p['Q'] == 6 for p in r['pontos']))
            self.assertEqual(executar(**args, retomar=True)[0], json.loads(json.dumps(registro)))

    def test_retomada_sem_executar_motor_por_demanda_inviavel(self):
        with tempfile.TemporaryDirectory(dir=RAIZ/'resultados') as pasta, redirect_stdout(io.StringIO()):
            args = dict(config_path='experimentos/q_variavel_exemplo.json', modo='metaheuristica',
                        algoritmos=['bibliotecas'], capacidades=[1], capacidade='variavel', saida=pasta)
            registro, _ = executar(**args)
            self.assertTrue(all(r['status'] == 'inviavel_demanda' for r in registro['execucoes']))
            self.assertTrue(executar(**args, retomar=True)[0]['concluida'])


if __name__ == '__main__':
    unittest.main()
