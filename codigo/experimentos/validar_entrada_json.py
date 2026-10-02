"""Regressoes do contrato JSON e do exemplo canonico de passageiros."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from darp import Avaliador, ler_instancia_json, ler_parametros_json
from darp.solucao import Rota, Solucao

EXEMPLO = Path(__file__).resolve().parents[2] / "dados/exemplo_instancia.json"


class TestEntrada(unittest.TestCase):
    def setUp(self):
        self.dados = json.loads(EXEMPLO.read_text(encoding="utf-8"))

    def ler(self, dados, parametros=False):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "entrada.json"
            caminho.write_text(json.dumps(dados), encoding="utf-8")
            return ler_parametros_json(caminho) if parametros else ler_instancia_json(caminho, Q=4)

    def test_exemplo_com_agenda_viavel(self):
        inst = ler_instancia_json(EXEMPLO, Q=4)
        par = ler_parametros_json(EXEMPLO)
        self.assertEqual((inst.n, inst.m, inst.Q), (5, 3, 4))
        self.assertEqual([r.id for r in inst.requisicoes], [101, 102, 103, 104, 105])
        self.assertEqual((par.phi, par.alpha, par.politica), (180, 2, "otimo"))
        sol = Solucao([Rota([1, 2, 3, 6, 7, 8, 5, 10]), Rota([4, 9]), Rota()])
        res = Avaliador(inst, par).avaliar(sol)
        self.assertTrue(res.viavel, res.violacoes)
        self.assertAlmostEqual(res.f1, 180 * res.distancia)

    def test_demanda_nao_truncada(self):
        self.dados["requisicoes"][0]["q"] = 1.5
        with self.assertRaisesRegex(ValueError, "requisicao.q"):
            self.ler(self.dados)

    def test_janela_invertida(self):
        self.dados["requisicoes"][0]["l_coleta"] = 10
        with self.assertRaisesRegex(ValueError, "inicio maior"):
            self.ler(self.dados)

    def test_ids_duplicados_ou_inexistentes(self):
        for caso in ("no", "pedido", "referencia"):
            d = copy.deepcopy(self.dados)
            if caso == "no":
                d["rede"]["nos_fixos"][1]["id"] = 0
            elif caso == "pedido":
                d["requisicoes"][1]["id"] = 101
            else:
                d["requisicoes"][0]["destino_id"] = 999
            with self.subTest(caso=caso), self.assertRaises(ValueError):
                self.ler(d)

    def test_rede_desconectada_nao_cria_atalho(self):
        self.dados["rede"]["arestas"] = self.dados["rede"]["arestas"][:-1]
        with self.assertRaisesRegex(ValueError, "falta caminho"):
            self.ler(self.dados)

    def test_custos_negativos_e_nao_finitos(self):
        for valor in (-1, float("nan"), float("inf")):
            d = copy.deepcopy(self.dados)
            d["rede"]["arestas"][0]["tempo"] = valor
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                self.ler(d)

    def test_parametros_invalidos(self):
        for campo, valor in (("alpha", 0.5), ("phi", -1), ("politica", "desconhecida"), ("phii", 10)):
            d = copy.deepcopy(self.dados)
            d["parametros_avaliacao"][campo] = valor
            with self.subTest(campo=campo), self.assertRaises(ValueError):
                self.ler(d, parametros=True)

    def test_formato_legado_sem_metadados(self):
        for campo in ("versao_formato", "unidades", "parametros_avaliacao"):
            self.dados.pop(campo)
        self.assertEqual(self.ler(self.dados).n, 5)
        self.assertEqual(self.ler(self.dados, parametros=True).phi, 1)

    def test_capacidade_externa_e_legada(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "entrada.json"
            caminho.write_text(json.dumps(self.dados), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Q nao esta"):
                ler_instancia_json(caminho)
            self.assertEqual(ler_instancia_json(caminho, Q=20).Q, 20)
            self.dados["Q"] = 8
            caminho.write_text(json.dumps(self.dados), encoding="utf-8")
            self.assertEqual(ler_instancia_json(caminho).Q, 8)
            self.assertEqual(ler_instancia_json(caminho, Q=2).Q, 2)


if __name__ == "__main__":
    unittest.main()
