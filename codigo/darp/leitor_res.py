"""Leitura das solucoes publicadas (.res) que acompanham a colecao tabu.

Essas solucoes minimizam apenas a distancia, ou seja, sao o extremo de f_1 do
modelo deste projeto. Servem a dois propositos: testar o avaliador contra
valores independentes e entrar no experimento como ponto conhecido da fronteira.

O formato nao e uniforme na colecao. Em pr01.res os campos vem rotulados,

    1 D: 84.33 Q: 2.00 W: 8.37 T: 30.22  0 (b:188.54; t:0.00; q:0.00)
      10 (w:0.00 a:191.99; t:0.00; q:1.00) ...

e em pr07.res os mesmos campos vem sem rotulo,

    1     370.68       4.00 0 (79.43; 0.00; 0.00) 4 (0.00 81.66; 0.00; 1.00) ...

Em ambos, cada visita e um par "id (campos)". A leitura ignora os rotulos e se
apoia na quantidade de numeros entre parenteses: tres identificam a saida do
deposito (instante, 0, 0) e quatro identificam uma visita (espera, inicio do
atendimento, tempo a bordo, carga).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .solucao import Rota, Solucao

_VISITA = re.compile(r"(\d+)\s*\(([^)]*)\)")
_NUMERO = re.compile(r"-?\d+\.?\d*")


@dataclass
class SolucaoPublicada:
    """Solucao lida de um .res, com os valores do arquivo preservados."""

    nome: str
    distancia: float
    solucao: Solucao
    B: dict[int, float] = field(default_factory=dict)
    espera: dict[int, float] = field(default_factory=dict)
    bordo: dict[int, float] = field(default_factory=dict)
    carga: dict[int, float] = field(default_factory=dict)
    partidas: dict[int, float] = field(default_factory=dict)
    totais: dict[str, float] = field(default_factory=dict)


def ler_res(caminho: str | Path) -> SolucaoPublicada:
    caminho = Path(caminho)
    linhas = caminho.read_text().splitlines()

    distancia = float(_NUMERO.search(linhas[0]).group())

    pub = SolucaoPublicada(nome=caminho.name, distancia=distancia,
                           solucao=Solucao(rotas=[]))

    for linha in linhas[1:]:
        visitas = _VISITA.findall(linha)
        if len(visitas) < 2:
            _coletar_totais(linha, pub.totais)
            continue

        k = len(pub.solucao.rotas)
        rota = Rota()

        for bruto_id, corpo in visitas:
            no = int(bruto_id)
            campos = [float(v) for v in _NUMERO.findall(corpo)]

            if len(campos) == 3:
                # Saida do deposito: o primeiro campo e o instante de partida.
                pub.partidas[k] = campos[0]
                continue
            if len(campos) != 4:
                raise ValueError(
                    f"{caminho.name}: visita ao no {no} com {len(campos)} campos")

            espera, inicio, bordo, carga = campos
            if no == 0:
                continue  # retorno ao deposito

            rota.sequencia.append(no)
            pub.B[no] = inicio
            pub.espera[no] = espera
            pub.bordo[no] = bordo
            pub.carga[no] = carga

        pub.solucao.rotas.append(rota)

    pub.solucao.partidas = dict(pub.partidas)
    return pub


def _coletar_totais(linha: str, destino: dict[str, float]) -> None:
    """Extrai as linhas de totalizacao do fim do arquivo, quando existirem."""
    chaves = {
        "Total duration": "duracao",
        "Total waiting time": "espera",
        "Total transit time": "bordo",
    }
    for prefixo, chave in chaves.items():
        if linha.strip().startswith(prefixo):
            numeros = _NUMERO.findall(linha)
            if numeros:
                destino[chave] = float(numeros[0])
            if len(numeros) > 1:
                destino[f"{chave}_media"] = float(numeros[1])
