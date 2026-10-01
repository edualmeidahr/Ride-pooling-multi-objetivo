"""Modulo de meta-heuristicas multiobjetivo para o DARP."""

from .base import ArquivoPareto, Metaheuristica, ResultadoOtimizacao
from .ga import AlgoritmoGenetico
from .grasp import GRASP
from .operadores import (
    construcao_gulosa_randomizada,
    mover_requisicao,
    perturbar_solucao,
    reordenar_rota_2opt,
    trocar_requisicoes,
)
from .sa import SimulatedAnnealing


def obter_metaheuristica(nome: str, **kwargs) -> Metaheuristica:
    """Fabrica para selecao dinamica de meta-heuristicas (Strategy Pattern).

    Opcoes:
        - "sa" ou "simulated_annealing"
        - "ga" ou "genetico" ou "algoritmo_genetico"
        - "grasp"
    """
    chave = nome.lower().replace("-", "_").strip()
    if chave in ("sa", "simulated_annealing", "annealing"):
        return SimulatedAnnealing(**kwargs)
    if chave in ("ga", "genetico", "algoritmo_genetico", "genetic"):
        return AlgoritmoGenetico(**kwargs)
    if chave == "grasp":
        return GRASP(**kwargs)
    raise ValueError(f"Meta-heuristica '{nome}' nao reconhecida. Opcoes: 'sa', 'ga', 'grasp'")


__all__ = [
    "Metaheuristica",
    "ResultadoOtimizacao",
    "ArquivoPareto",
    "SimulatedAnnealing",
    "AlgoritmoGenetico",
    "GRASP",
    "obter_metaheuristica",
    "construcao_gulosa_randomizada",
    "perturbar_solucao",
    "mover_requisicao",
    "trocar_requisicoes",
    "reordenar_rota_2opt",
]
