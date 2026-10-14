"""Valida tamanho real da entrada e perfil limitado de construcao."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from menu import preparar
from darp import Avaliador, HeuristicaGulosa
from darp.metaheuristicas.operadores import posicoes_insercao, construcao_gulosa_randomizada
import random


class TestCenario100(unittest.TestCase):
    def test_100_pedidos_reais_e_q1_viavel(self):
        c,inst,par,qs,ambiente,_=preparar("experimentos/comparacao_100_corridas.json", [1])
        self.assertEqual(inst.n,100)
        self.assertEqual(len(inst.requisicoes),100)
        self.assertEqual(inst.m,100)
        self.assertEqual(len(inst.nos),202)
        self.assertEqual(len({r.id for r in inst.requisicoes}),100)
        res=HeuristicaGulosa(limite_pedidos=1,limite_posicoes=8).resolver(inst,Avaliador(inst,par))
        self.assertTrue(res.avaliacao.viavel)
        self.assertEqual(len(res.historico),100)
        self.assertEqual(res.avaliacao.veiculos_usados,100)
        self.assertFalse(res.solucao.conferir_estrutura(inst))

    def test_posicoes_limitadas_validas(self):
        pares=posicoes_insercao(20,8)
        self.assertEqual(len(set(pares)),8)
        self.assertEqual(pares[0],(0,0))
        self.assertEqual(pares[-1],(20,20))
        self.assertTrue(all(0<=c<=e<=20 for c,e in pares))
        with self.assertRaises(ValueError):
            posicoes_insercao(0,1)

    def test_construcao_randomizada_limitada_preserva_cobertura(self):
        _,inst,par,_,_,_=preparar("experimentos/exemplo_pequeno.json",[2])
        av=Avaliador(inst,par)
        av.limite_pedidos_construcao=1
        av.limite_posicoes_construcao=8
        av.coletas_concorrentes=True
        for seed in [7,42]:
            sol=construcao_gulosa_randomizada(inst,av,rng=random.Random(seed))
            self.assertFalse(sol.conferir_estrutura(inst))
            self.assertTrue(av.avaliar(sol).viavel)


if __name__=="__main__":
    unittest.main()
