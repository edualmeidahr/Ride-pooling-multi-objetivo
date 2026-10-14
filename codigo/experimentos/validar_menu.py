"""Integracao das tres categorias, menu, limites e objetivos pareados."""
import csv
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from menu import executar, menu, RAIZ


class TestMenu(unittest.TestCase):
    def rodar(self, config, modo, **kwargs):
        with tempfile.TemporaryDirectory() as pasta, redirect_stdout(StringIO()):
            registro, saida = executar(config, modo, saida=pasta, **kwargs)
            with (saida / "metricas.csv").open(encoding="utf-8-sig") as f:
                linhas = list(csv.DictReader(f))
            self.assertTrue((saida / "RESUMO.md").is_file())
            self.assertTrue((saida / "solucoes.csv").is_file())
            self.assertEqual(json.loads((saida / "execucoes.json").read_text(encoding="utf-8")), json.loads(json.dumps(registro)))
            indice = {p["solucao_id"]: p for r in registro["execucoes"] for p in r["pontos"]}
            for l in linhas:
                if l["solucao_id"]:
                    p = indice[l["solucao_id"]]
                    self.assertEqual(float(l["f1"]), p["f1"])
                    self.assertEqual(float(l["f2"]), p["f2"])
                    self.assertEqual(int(l["veiculos_usados"]), p["veiculos_usados"])
            return registro

    def test_tres_categorias_no_mesmo_exemplo(self):
        d = self.rodar("experimentos/exemplo_pequeno.json", "comparar")
        self.assertTrue(d["concluida"])
        self.assertEqual(len(d["execucoes"]), 10)
        self.assertEqual({r["categoria"] for r in d["execucoes"]}, {"exato", "metaheuristica", "heuristica"})
        self.assertEqual(d["referencias"]["1"]["pontos"], [[92.0, 0.0]])
        self.assertEqual(d["referencias"]["2"]["pontos"], [[46.0, 4.5], [92.0, 0.0]])
        self.assertEqual({r["seed"] for r in d["execucoes"] if r["categoria"] == "metaheuristica"}, {42})

    def test_opcoes_independentes_e_ambiente(self):
        for modo, metodos in (("exato", {"exato"}), ("heuristica", {"gulosa"}),
                              ("metaheuristica", {"ga"}), ("comparar_aproximados", {"ga", "gulosa"})):
            d = self.rodar("experimentos/validacao_emissoes.json", modo, algoritmos=["ga"], capacidades=[2])
            self.assertEqual({r["metodo"] for r in d["execucoes"]}, metodos)
            self.assertEqual(d["unidade_f1"], "g_CO2")
            self.assertEqual(d["ambiente_emissoes"]["phi_por_q"], {"2": 180.0})
            for r in d["execucoes"]:
                for p in r["pontos"]:
                    self.assertGreater(p["f1"], p["distancia_km"])

    def test_exato_grande_rejeitado_sem_recortar(self):
        for modo in ("exato", "comparar"):
            with self.assertRaisesRegex(ValueError, "entrada tem 12"):
                executar("experimentos/comparacao_emissoes_q1_10.json", modo)

    def test_bloqueio_e_inviabilidade_sem_objetivos_falsos(self):
        c = json.loads((RAIZ / "experimentos/exemplo_pequeno.json").read_text())
        c["m"] = 1
        with tempfile.TemporaryDirectory() as pasta:
            config = Path(pasta) / "config.json"
            config.write_text(json.dumps(c))
            for modo, status in (("heuristica", "bloqueada"), ("exato", "inviavel")):
                d = self.rodar(config, modo, capacidades=[1])
                self.assertEqual(d["execucoes"][0]["status"], status)
                self.assertEqual(d["execucoes"][0]["pontos"], [])

    def test_menu_escolhas_e_saida(self):
        with patch("builtins.input", side_effect=["4", "", "2", "2", "123", "0,8", "0"]), \
             patch("menu.executar") as chamada, redirect_stdout(StringIO()):
            menu()
            chamada.assert_called_once_with("experimentos/exemplo_pequeno.json", "comparar",
                algoritmos=("ga",), seed=123, peso_emissao=0.8, capacidades=[2])

    def test_retomada_preserva_execucoes_e_recusa_mudancas(self):
        with tempfile.TemporaryDirectory() as pasta, redirect_stdout(StringIO()):
            d,saida = executar("experimentos/exemplo_pequeno.json", "comparar", capacidades=[2], saida=pasta)
            d = json.loads(json.dumps(d))
            anteriores = d["execucoes"][:-1]
            d["execucoes"] = anteriores
            d["concluida"] = False
            arquivo = saida / "execucoes.json"
            arquivo.write_text(json.dumps(d), encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"opcoes mudou"):
                executar("experimentos/exemplo_pequeno.json", "comparar", capacidades=[2], seed=7, saida=pasta, retomar=True)
            with patch("menu.fronteira_exata", side_effect=AssertionError("Nao repetir exato")):
                retomado,_ = executar("experimentos/exemplo_pequeno.json", "comparar", capacidades=[2], saida=pasta, retomar=True)
            self.assertEqual(json.loads(json.dumps(retomado["execucoes"][:4])), anteriores)
            self.assertEqual(len(retomado["execucoes"]),5)
            self.assertTrue(retomado["concluida"])
            self.assertEqual(retomado["retomadas"][0]["execucoes_preservadas"],4)


if __name__ == "__main__":
    unittest.main()
