"""Estrutura base, interfaces e tipos para as meta-heuristicas."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Sequence

from ..avaliador import Avaliador
from ..instancia import Instancia
from ..pareto import domina, filtrar
from ..solucao import Solucao


@dataclass
class ResultadoOtimizacao:
    """Resultado da execucao de uma meta-heuristica."""

    algoritmo: str
    fronteira: list[tuple[float, float, Solucao]] = field(default_factory=list)
    tempo_execucao: float = 0.0
    iteracoes: int = 0
    avaliacoes: int = 0
    historico: list[dict] = field(default_factory=list)

    @property
    def num_solucoes(self) -> int:
        return len(self.fronteira)

    @property
    def melhor_f1(self) -> float | None:
        return min((p[0] for p in self.fronteira), default=None)

    @property
    def melhor_f2(self) -> float | None:
        return min((p[1] for p in self.fronteira), default=None)

    def resumo(self) -> str:
        f1_str = f"{self.melhor_f1:.2f}" if self.melhor_f1 is not None else "N/A"
        f2_str = f"{self.melhor_f2:.2f}" if self.melhor_f2 is not None else "N/A"
        return (
            f"[{self.algoritmo}] {self.num_solucoes} solucoes nao-dominadas em "
            f"{self.tempo_execucao:.2f}s | Melhor f1={f1_str}, Melhor f2={f2_str} "
            f"({self.iteracoes} iters, {self.avaliacoes} avals)"
        )


class ArquivoPareto:
    """Arquivo externo de solucoes nao-dominadas."""

    def __init__(self, tol: float = 1e-6) -> None:
        self.tol = tol
        self._pontos: list[tuple[float, float, Solucao]] = []

    @property
    def pontos(self) -> list[tuple[float, float, Solucao]]:
        return list(self._pontos)

    def adicionar(self, f1: float, f2: float, solucao: Solucao) -> bool:
        """Adiciona solucao se nao for dominada, removendo as dominadas por ela.

        Retorna True se a solucao entrou no arquivo.
        """
        candidato = (f1, f2)
        # Se algum ponto ja domina ou e identico, descarta
        for atual in self._pontos:
            if domina(atual, candidato, self.tol):
                return False
            if abs(atual[0] - f1) <= self.tol and abs(atual[1] - f2) <= self.tol:
                return False

        # Remove pontos dominados pelo novo candidato
        nova_lista = [p for p in self._pontos if not domina(candidato, p, self.tol)]
        nova_lista.append((f1, f2, solucao.copiar()))
        self._pontos = filtrar(nova_lista, self.tol)
        return True

    def __len__(self) -> int:
        return len(self._pontos)


class Metaheuristica(ABC):
    """Classe base (Strategy Pattern) para algoritmos de otimizacao multiobjetivo."""

    def __init__(self, nome: str) -> None:
        self.nome = nome

    @abstractmethod
    def otimizar(
        self,
        inst: Instancia,
        av: Avaliador,
        **kwargs,
    ) -> ResultadoOtimizacao:
        """Executa a otimizacao sobre a instancia e devolve o ResultadoOtimizacao."""
        pass
