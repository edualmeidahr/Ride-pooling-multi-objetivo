"""Gera deterministicamente a entrada sintetica concorrente e a campanha Q=1..10."""
import json
from pathlib import Path


def main():
    raiz = Path(__file__).resolve().parents[2]
    coords = [(0,0), (-1,0), (0,1), (1,0), (0,-1),
              (20,0), (22,0), (20,2), (23,-2), (24,3)]
    nos = [{"id": i, "nome": ("Garagem" if i == 0 else f"Parada {i}"),
            "x": x, "y": y, "s_embarque": 0.2, "s_desembarque": 0.2}
           for i,(x,y) in enumerate(coords)]
    nos[0]["s_embarque"] = nos[0]["s_desembarque"] = 0
    conexoes = [(0,1,1), (0,2,1), (0,3,1), (0,4,1), (0,5,20),
                (5,6,2), (5,7,2), (6,8,3), (7,9,5)]
    destinos = [6,7,8,9,7,8,9,6,8,9,6,7]
    pedidos = [{"id": 201+i, "origem_id": 1+i%4, "destino_id": d,
                "q": 1, "e_coleta": 30.0 + i%3, "l_coleta": 50.0,
                "e_entrega": 0.0, "l_entrega": 1440.0}
               for i,d in enumerate(destinos)]
    entrada = {"versao_formato": 1, "nome": "Corredor-concorrente-12-passageiros",
        "descricao": "Cenario sintetico controlado: 12 pedidos unitarios concorrentes, quatro origens e quatro destinos. Sem calibracao real. Q pertence a configuracao experimental.",
        "unidades": {"distancia": "km", "tempo": "min", "demanda": "passageiros"},
        "m": 12, "T_max": 240.0, "L_arquivo": 120.0,
        "deposito_origem_id": 0, "deposito_destino_id": 0,
        "janela_deposito_ini": [0.0,300.0], "janela_deposito_fim": [0.0,300.0],
        "parametros_avaliacao": {"phi": 1.0, "alpha": 2.0, "politica": "otimo"},
        "rede": {"direcionado": False, "nos_fixos": nos,
                 "arestas": [{"origem": a,"destino": b,"distancia": d,"tempo": 2*d} for a,b,d in conexoes]},
        "requisicoes": pedidos}
    config = {"instancia": "dados/cenario_concorrente_q10.json", "pedidos": list(range(1,13)),
        "m": 12, "capacidades": list(range(1,11)), "sementes": [7,42,2026,314,2718],
        "referencia": "empirica", "cache_agendas": True,
        "coletas_antes_de_qualquer_entrega": True,
        "parametros_avaliacao": entrada["parametros_avaliacao"],
        "algoritmos": {
            "sa": {"temp_inicial": 3.0,"temp_final": 0.5,"fator_resfriamento": 0.6,"iter_por_temp": 10},
            "ga": {"tamanho_populacao": 6,"geracoes": 6},
            "grasp": {"max_iteracoes": 4,"max_passos_busca_local": 3}},
        "saida": "resultados/comparacao_q1_10",
        "observacao": "Analise exploratoria controlada com 12 pedidos concorrentes. Referencia empirica por Q, sem prova de otimalidade. Esforcos distintos entre metodos; cinco sementes nao bastam para ranking definitivo."}
    for caminho, dados in [(raiz/"dados/cenario_concorrente_q10.json",entrada),
                            (raiz/"experimentos/comparacao_q1_10.json",config)]:
        caminho.write_text(json.dumps(dados,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(caminho)


if __name__ == "__main__":
    main()
