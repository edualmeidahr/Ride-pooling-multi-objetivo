"""Cria configuracoes ambientais separadas, sem sobrescrever campanhas de distancia."""
import json
from pathlib import Path


def main():
    raiz = Path(__file__).resolve().parents[2]
    perfil = json.loads((raiz / "experimentos/modelo_emissoes.json").read_text(encoding="utf-8"))
    for origem, nome in [("exemplo_pequeno", "validacao_emissoes"),
                         ("comparacao_q1_10", "comparacao_emissoes_q1_10")]:
        config = json.loads((raiz / f"experimentos/{origem}.json").read_text(encoding="utf-8"))
        config["modelo_emissoes"] = perfil
        config["sementes"] = [42]
        config["saida"] = f"resultados/{nome}"
        config["observacao"] = "CO2 sintetico com perfis por Q e fatores de rua fixos. Uma semente; sem estimativa de variabilidade ou prova de otimalidade."
        if nome == "validacao_emissoes":
            config["capacidades"] = [1, 2, 5, 7, 10]
        (raiz / f"experimentos/{nome}.json").write_text(json.dumps(config, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
