"""Gera 100 pedidos concorrentes e uma campanha ambiental de uma semente."""
import json
from pathlib import Path


def main():
    raiz = Path(__file__).resolve().parents[2]
    entrada = json.loads((raiz / "dados/cenario_concorrente_q10.json").read_text(encoding="utf-8"))
    modelos = entrada["requisicoes"]
    entrada["requisicoes"] = [{**modelos[i % len(modelos)], "id": 1001+i} for i in range(100)]
    entrada["m"] = 100
    entrada["nome"] = "Corredor-concorrente-100-passageiros"
    entrada["descricao"] = "100 pedidos sinteticos concorrentes, 100 veiculos disponiveis fixos para viabilidade de Q=1. Mesma rede e geometria do piloto; nao sao 100 instancias independentes."
    config = json.loads((raiz / "experimentos/comparacao_emissoes_q1_10.json").read_text(encoding="utf-8"))
    config.update(instancia="dados/cenario_100_corridas.json", pedidos=list(range(1,101)), m=100,
                  sementes=[42], saida="resultados/comparacao_100_corridas",
                  construcao={"limite_pedidos_candidatos": 1,
                              "limite_posicoes_insercao": 8,
                              "descricao": "Construcao escalavel: proximo pedido por horario desejado; todos os veiculos com capacidade disponivel e ate 8 pares de posicoes por rota, espalhados deterministicamente. Todos os 100 pedidos sao atendidos. Nao usa a construcao exaustiva do piloto de 12."})
    config["observacao"] = "100 pedidos, Q=1..10, uma execucao por SA/GA/GRASP/gulosa. Construcao sequencial para escala; parametros exploratorios, sem ranking nem referencia exata."
    for path, dados in [(raiz / "dados/cenario_100_corridas.json", entrada),
                         (raiz / "experimentos/comparacao_100_corridas.json", config)]:
        path.write_text(json.dumps(dados, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
