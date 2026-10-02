"""Cenarios independentes para estudar capacidade sem alterar a instancia base."""
from dataclasses import replace

from .instancia import Instancia


def cenario_capacidade(inst: Instancia, Q: int, m: int | None = None) -> Instancia:
    if isinstance(Q, bool) or not isinstance(Q, int) or Q < 1:
        raise ValueError("Q deve ser inteiro positivo")
    frota = inst.m if m is None else m
    if isinstance(frota, bool) or not isinstance(frota, int) or frota < 1:
        raise ValueError("m deve ser inteiro positivo")
    return replace(inst, Q=Q, m=frota, nome=f"{inst.nome}-Q{Q}-m{frota}")
