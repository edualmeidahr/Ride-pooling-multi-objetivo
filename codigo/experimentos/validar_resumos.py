"""Testa pareamento, escolha de compromisso e invariancia de unidades."""
import unittest
import csv
import json
from pathlib import Path

from resumir_campanha import escolher, escore


class TestResumo(unittest.TestCase):
    def linhas(self, escala=1):
        limites = ([0, 0], [100 * escala, 100])
        return [{"f1": x * escala, "f2": y, "solucao_id": str(i),
                 "escore_equilibrio": escore({"f1": x * escala, "f2": y}, limites)}
                for i, (x, y) in enumerate([(0, 100), (40, 40), (100, 0)])]

    def test_compromisso_real_sem_combinar_extremos(self):
        linhas = self.linhas()
        escolhido = escolher(linhas, "equilibrada")
        self.assertIs(escolhido, linhas[1])
        self.assertEqual((escolhido["f1"], escolhido["f2"]), (40, 40))
        self.assertIs(escolher(linhas, "menor_distancia"), linhas[0])
        self.assertIs(escolher(linhas, "menor_tempo_perdido"), linhas[2])

    def test_troca_de_unidades_nao_altera_escolha(self):
        self.assertEqual(escolher(self.linhas(), "equilibrada")["solucao_id"],
                         escolher(self.linhas(1000), "equilibrada")["solucao_id"])

    def test_objetivo_constante(self):
        self.assertEqual(escore({"f1": 600, "f2": 0}, ([600, 0], [600, 0])), 0)

    def test_empate_deterministico(self):
        linhas = self.linhas()
        self.assertIs(escolher([linhas[2], linhas[0]], "equilibrada"), linhas[0])

    def test_exportacoes_correspondem_a_rotas_originais(self):
        raiz = Path(__file__).resolve().parents[2]
        for nome in ("comparacao_q1_10", "comparacao_exemplo", "exemplo_pequeno", "validacao_emissoes", "comparacao_emissoes_q1_10"):
            pasta = raiz / "resultados" / nome
            dados = json.loads((pasta / "execucoes.json").read_text(encoding="utf-8"))
            execucoes = {(r["Q"], r["metodo"], r["seed"]): r for r in dados["execucoes"]}
            def ler(nome):
                with (pasta / nome).open(encoding="utf-8-sig", newline="") as f:
                    return list(csv.DictReader(f))
            todas = ler("solucoes.csv")
            self.assertEqual(len(todas), sum(len(r["pontos"]) for r in execucoes.values()))
            indice = {p["solucao_id"]: p for p in todas}
            self.assertEqual(len(indice), len(todas))
            for linha in todas:
                r = execucoes[(int(linha["Q"]), linha["metodo"], int(linha["seed"]))]
                p = r["pontos"][int(linha["indice_ponto_json"])]
                for campo in ("f1", "f2", "espera", "desvio", "veiculos_usados", "carga_maxima"):
                    self.assertEqual(float(linha[campo]), p[campo])
                self.assertEqual(json.loads(linha["rotas_json"]), p["rotas"])
            representantes = ler("solucoes_representativas.csv")
            self.assertEqual(len(representantes), 3 * len(execucoes))
            for p in representantes + ler("solucoes_equilibradas_por_q.csv"):
                for campo, valor in indice[p["solucao_id"]].items():
                    self.assertEqual(p[campo], valor)
            for linha in ler("metricas.csv"):
                p = indice[linha["solucao_id"]]
                for campo in ("f1", "f2", "veiculos_usados"):
                    self.assertEqual(linha[campo], p[campo])
            for linha in ler("metricas_tecnicas.csv"):
                for identificador, f1, f2 in (
                    ("solucao_equilibrada_id", "f1_equilibrada", "f2_equilibrada"),
                    ("solucao_menor_distancia_id", "f1_menor_distancia", "f2_menor_distancia"),
                    ("solucao_menor_tempo_id", "f1_menor_tempo", "f2_menor_tempo")):
                    p = indice[linha[identificador]]
                    self.assertEqual(linha[f1], p["f1"])
                    self.assertEqual(linha[f2], p["f2"])


if __name__ == "__main__":
    unittest.main()
