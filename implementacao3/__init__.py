"""Modulo de meta-heuristicas multiobjetivo para o DARP."""

from implementacao3.base import ArquivoPareto, Metaheuristica, ResultadoOtimizacao
from implementacao3.aco import ColoniaFormigas
from implementacao3.ga import AlgoritmoGenetico
from implementacao3.grasp import GRASP
from comum.operadores import construcao_gulosa_randomizada, mover_requisicao, perturbar_solucao, reordenar_rota_2opt, trocar_requisicoes
from implementacao3.sa import SimulatedAnnealing
from implementacao3.ga_biblioteca import GeneticoBiblioteca
from implementacao3.sa_biblioteca import AnnealingBiblioteca
from implementacao3.pso_biblioteca import PSOBiblioteca

METODOS = {
    'sa': SimulatedAnnealing, 'ga': AlgoritmoGenetico, 'grasp': GRASP, 'aco': ColoniaFormigas,
    'ga_lib': GeneticoBiblioteca, 'sa_lib': AnnealingBiblioteca, 'pso_lib': PSOBiblioteca,
}
METODOS_PADRAO = ('sa', 'ga', 'grasp', 'aco')
METODOS_BIBLIOTECAS = ('ga_lib', 'sa_lib', 'pso_lib')
GRUPOS = {'bibliotecas': METODOS_BIBLIOTECAS, 'todos': tuple(METODOS)}
ALIASES = {'simulated_annealing': 'sa', 'annealing': 'sa', 'genetico': 'ga',
           'algoritmo_genetico': 'ga', 'genetic': 'ga', 'colonia_formiga': 'aco', 'colonia_formigas': 'aco'}


def selecionar_algoritmos(nomes=None):
    """Expande grupos uma vez, preservando ordem e recusando repetições."""
    if nomes is None:
        return METODOS_PADRAO
    if isinstance(nomes, str):
        nomes = [nomes]
    selecionados = []
    for nome in nomes:
        chave = nome.lower().replace('-', '_').strip()
        chave = ALIASES.get(chave, chave)
        for metodo in GRUPOS.get(chave, (chave,)):
            if metodo not in METODOS or metodo in selecionados:
                raise ValueError(f'Metodo invalido ou repetido: {metodo}. Opcoes: {", ".join(METODOS)}')
            selecionados.append(metodo)
    if not selecionados:
        raise ValueError('Selecione ao menos uma metaheuristica')
    return tuple(selecionados)


def obter_metaheuristica(nome: str, **kwargs) -> Metaheuristica:
    """Fabrica para selecao dinamica de meta-heuristicas (Strategy Pattern).

    Opcoes:
        - "sa" ou "simulated_annealing"
        - "ga" ou "genetico" ou "algoritmo_genetico"
        - "grasp"
        - "aco" ou "colonia_formiga"
        - "ga_lib", "sa_lib" ou "pso_lib" (motores de bibliotecas)
    """
    chave = nome.lower().replace("-", "_").strip()
    chave = ALIASES.get(chave, chave)
    if chave not in METODOS:
        raise ValueError(f'Metaheuristica {nome!r} desconhecida. Opcoes: {", ".join(METODOS)}')
    return METODOS[chave](**kwargs)


__all__ = [
    "Metaheuristica",
    "ResultadoOtimizacao",
    "ArquivoPareto",
    "SimulatedAnnealing",
    "AlgoritmoGenetico",
    "GRASP",
    "ColoniaFormigas",
    "GeneticoBiblioteca", "AnnealingBiblioteca", "PSOBiblioteca",
    "METODOS", "METODOS_PADRAO", "METODOS_BIBLIOTECAS", "selecionar_algoritmos",
    "obter_metaheuristica",
    "construcao_gulosa_randomizada",
    "perturbar_solucao",
    "mover_requisicao",
    "trocar_requisicoes",
    "reordenar_rota_2opt",
]
