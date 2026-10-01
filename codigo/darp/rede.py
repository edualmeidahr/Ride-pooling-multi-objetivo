"""Modelagem de redes com nos fixos, matrizes de custo e requisicoes.

Permite representar paradas/pontos de interesse fixos no espaco urbano,
desacoplando a topologia da rede viaria das solicitacoes de viagem dos usuarios.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .instancia import Instancia

JANELA_LIVRE = 1440.0


@dataclass(frozen=True)
class NoFixo:
    """Ponto fixo de interesse ou parada pre-definida na rede viaria."""

    id: int
    x: float
    y: float
    nome: str = ""
    s_embarque: float = 0.0      # tempo base de parada para embarque
    s_desembarque: float = 0.0   # tempo base de parada para desembarque

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "nome": self.nome,
            "s_embarque": self.s_embarque,
            "s_desembarque": self.s_desembarque,
        }

    @classmethod
    def from_dict(cls, dados: dict[str, Any]) -> NoFixo:
        return cls(
            id=int(dados["id"]),
            x=float(dados["x"]),
            y=float(dados["y"]),
            nome=dados.get("nome", ""),
            s_embarque=float(dados.get("s_embarque", 0.0)),
            s_desembarque=float(dados.get("s_desembarque", 0.0)),
        )


@dataclass(frozen=True)
class Requisicao:
    """Solicitacao de transporte que referencia nos fixos de origem e destino."""

    id: int
    origem_id: int               # ID do NoFixo onde o passageiro embarca
    destino_id: int              # ID do NoFixo onde o passageiro desembarca
    q: int = 1                   # quantidade de passageiros
    e_coleta: float = 0.0        # inicio da janela na coleta
    l_coleta: float = JANELA_LIVRE  # fim da janela na coleta
    e_entrega: float = 0.0       # inicio da janela na entrega
    l_entrega: float = JANELA_LIVRE # fim da janela na entrega
    s_coleta: float | None = None   # sobrescreve s_embarque da parada se informado
    s_entrega: float | None = None  # sobrescreve s_desembarque da parada se informado

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "origem_id": self.origem_id,
            "destino_id": self.destino_id,
            "q": self.q,
            "e_coleta": self.e_coleta,
            "l_coleta": self.l_coleta,
            "e_entrega": self.e_entrega,
            "l_entrega": self.l_entrega,
            "s_coleta": self.s_coleta,
            "s_entrega": self.s_entrega,
        }

    @classmethod
    def from_dict(cls, dados: dict[str, Any]) -> Requisicao:
        return cls(
            id=int(dados["id"]),
            origem_id=int(dados["origem_id"]),
            destino_id=int(dados["destino_id"]),
            q=int(dados.get("q", 1)),
            e_coleta=float(dados.get("e_coleta", 0.0)),
            l_coleta=float(dados.get("l_coleta", JANELA_LIVRE)),
            e_entrega=float(dados.get("e_entrega", 0.0)),
            l_entrega=float(dados.get("l_entrega", JANELA_LIVRE)),
            s_coleta=float(dados["s_coleta"]) if dados.get("s_coleta") is not None else None,
            s_entrega=float(dados["s_entrega"]) if dados.get("s_entrega") is not None else None,
        )


@dataclass
class Rede:
    """Grafo ou matriz de custos entre os nos fixos."""

    nos_fixos: dict[int, NoFixo]
    matriz_dist: dict[tuple[int, int], float] = field(default_factory=dict)
    matriz_tempo: dict[tuple[int, int], float] = field(default_factory=dict)

    def dist(self, origem_id: int, destino_id: int) -> float:
        """Distancia real ou de menor caminho entre dois nos fixos."""
        if origem_id == destino_id:
            return 0.0
        if (origem_id, destino_id) in self.matriz_dist:
            return self.matriz_dist[(origem_id, destino_id)]
        # Fallback euclidiano caso o par nao esteja explicitamente mapeado
        if origem_id in self.nos_fixos and destino_id in self.nos_fixos:
            a, b = self.nos_fixos[origem_id], self.nos_fixos[destino_id]
            return math.hypot(a.x - b.x, a.y - b.y)
        raise KeyError(f"Par ({origem_id}, {destino_id}) nao encontrado na rede")

    def tempo(self, origem_id: int, destino_id: int) -> float:
        """Tempo de percurso entre dois nos fixos."""
        if origem_id == destino_id:
            return 0.0
        if (origem_id, destino_id) in self.matriz_tempo:
            return self.matriz_tempo[(origem_id, destino_id)]
        # Se nao houver matriz especifica de tempo, usa a distancia
        return self.dist(origem_id, destino_id)

    @classmethod
    def from_matrizes(
        cls,
        nos_fixos: list[NoFixo] | dict[int, NoFixo],
        matriz_dist: dict[tuple[int, int], float] | list[list[float]],
        matriz_tempo: dict[tuple[int, int], float] | list[list[float]] | None = None,
        velocidade: float = 1.0,
    ) -> Rede:
        """Cria a Rede a partir de dicionario ou matriz 2D indexada por ID."""
        d_nos = (
            {n.id: n for n in nos_fixos}
            if isinstance(nos_fixos, list)
            else dict(nos_fixos)
        )

        d_dist: dict[tuple[int, int], float] = {}
        if isinstance(matriz_dist, dict):
            d_dist = dict(matriz_dist)
        else:
            # Lista de listas
            ids = sorted(d_nos.keys())
            for i_idx, u in enumerate(ids):
                for j_idx, v in enumerate(ids):
                    d_dist[(u, v)] = float(matriz_dist[i_idx][j_idx])

        d_tempo: dict[tuple[int, int], float] = {}
        if matriz_tempo is not None:
            if isinstance(matriz_tempo, dict):
                d_tempo = dict(matriz_tempo)
            else:
                ids = sorted(d_nos.keys())
                for i_idx, u in enumerate(ids):
                    for j_idx, v in enumerate(ids):
                        d_tempo[(u, v)] = float(matriz_tempo[i_idx][j_idx])
        else:
            d_tempo = {par: d / velocidade for par, d in d_dist.items()}

        return cls(nos_fixos=d_nos, matriz_dist=d_dist, matriz_tempo=d_tempo)

    @classmethod
    def from_grafo(
        cls,
        nos_fixos: list[NoFixo] | dict[int, NoFixo],
        arestas: list[tuple[int, int, float]] | list[tuple[int, int, float, float]],
        direcionado: bool = False,
        velocidade: float = 1.0,
    ) -> Rede:
        """Calcula a matriz de distancias por caminhos minimos (Dijkstra).

        arestas: lista de (u, v, distancia) ou (u, v, distancia, tempo).
        """
        d_nos = (
            {n.id: n for n in nos_fixos}
            if isinstance(nos_fixos, list)
            else dict(nos_fixos)
        )

        adj_dist: dict[int, list[tuple[int, float]]] = {u: [] for u in d_nos}
        adj_tempo: dict[int, list[tuple[int, float]]] = {u: [] for u in d_nos}

        for aresta in arestas:
            u, v = aresta[0], aresta[1]
            dist = float(aresta[2])
            tempo = float(aresta[3]) if len(aresta) >= 4 else dist / velocidade

            adj_dist[u].append((v, dist))
            adj_tempo[u].append((v, tempo))
            if not direcionado:
                adj_dist[v].append((u, dist))
                adj_tempo[v].append((u, tempo))

        def _dijkstra(adj: dict[int, list[tuple[int, float]]], inicio: int) -> dict[int, float]:
            dist = {inicio: 0.0}
            fila = [(0.0, inicio)]
            while fila:
                d, atual = heapq.heappop(fila)
                if d > dist[atual]:
                    continue
                for vizinho, peso in adj.get(atual, []):
                    novo = d + peso
                    if vizinho not in dist or novo < dist[vizinho]:
                        dist[vizinho] = novo
                        heapq.heappush(fila, (novo, vizinho))
            return dist

        matriz_dist: dict[tuple[int, int], float] = {}
        matriz_tempo: dict[tuple[int, int], float] = {}

        for u in d_nos:
            sp_dist = _dijkstra(adj_dist, u)
            sp_tempo = _dijkstra(adj_tempo, u)
            for v in d_nos:
                if v in sp_dist:
                    matriz_dist[(u, v)] = sp_dist[v]
                if v in sp_tempo:
                    matriz_tempo[(u, v)] = sp_tempo[v]

        return cls(nos_fixos=d_nos, matriz_dist=matriz_dist, matriz_tempo=matriz_tempo)

    @classmethod
    def euclidiana(
        cls,
        nos_fixos: list[NoFixo] | dict[int, NoFixo],
        velocidade: float = 1.0,
    ) -> Rede:
        """Cria matriz euclidiana completa entre todos os nos fixos."""
        d_nos = (
            {n.id: n for n in nos_fixos}
            if isinstance(nos_fixos, list)
            else dict(nos_fixos)
        )

        matriz_dist: dict[tuple[int, int], float] = {}
        matriz_tempo: dict[tuple[int, int], float] = {}

        for u, a in d_nos.items():
            for v, b in d_nos.items():
                d = math.hypot(a.x - b.x, a.y - b.y)
                matriz_dist[(u, v)] = d
                matriz_tempo[(u, v)] = d / velocidade

        return cls(nos_fixos=d_nos, matriz_dist=matriz_dist, matriz_tempo=matriz_tempo)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nos_fixos": [n.to_dict() for n in self.nos_fixos.values()],
            "matriz_dist": [
                {"origem": u, "destino": v, "valor": valor}
                for (u, v), valor in self.matriz_dist.items()
            ],
            "matriz_tempo": [
                {"origem": u, "destino": v, "valor": valor}
                for (u, v), valor in self.matriz_tempo.items()
            ],
        }

    @classmethod
    def from_dict(cls, dados: dict[str, Any]) -> Rede:
        nos_fixos = [NoFixo.from_dict(n) for n in dados.get("nos_fixos", [])]
        d_nos = {n.id: n for n in nos_fixos}

        # Caso 1: Grafo com arestas especificadas (calcula caminhos minimos via Dijkstra)
        if "arestas" in dados and dados["arestas"]:
            arestas = [
                (
                    int(item["origem"]),
                    int(item["destino"]),
                    float(item["distancia"]),
                    float(item.get("tempo", item["distancia"])),
                )
                for item in dados["arestas"]
            ]
            direcionado = bool(dados.get("direcionado", False))
            velocidade = float(dados.get("velocidade", 1.0))
            return cls.from_grafo(d_nos, arestas, direcionado=direcionado, velocidade=velocidade)

        # Caso 2: Matriz explicita de distancias e tempos
        if "matriz_dist" in dados and dados["matriz_dist"]:
            matriz_dist = {
                (int(item["origem"]), int(item["destino"])): float(item["valor"])
                for item in dados.get("matriz_dist", [])
            }
            matriz_tempo = {
                (int(item["origem"]), int(item["destino"])): float(item["valor"])
                for item in dados.get("matriz_tempo", [])
            }
            return cls(nos_fixos=d_nos, matriz_dist=matriz_dist, matriz_tempo=matriz_tempo)

        # Caso 3: Fallback euclidiano completo
        velocidade = float(dados.get("velocidade", 1.0))
        return cls.euclidiana(d_nos, velocidade=velocidade)


def criar_instancia_rede(
    nome: str,
    rede: Rede,
    requisicoes: list[Requisicao],
    deposito_origem_id: int,
    deposito_destino_id: int | None = None,
    m: int = 1,
    T_max: float = JANELA_LIVRE,
    Q: int = 4,
    L_arquivo: float = JANELA_LIVRE,
    janela_deposito_ini: tuple[float, float] = (0.0, JANELA_LIVRE),
    janela_deposito_fim: tuple[float, float] = (0.0, JANELA_LIVRE),
) -> Instancia:
    """Constroi uma Instancia DARP compativel mapeada sobre a Rede de nos fixos."""
    from .instancia import Instancia, No

    if deposito_destino_id is None:
        deposito_destino_id = deposito_origem_id

    n = len(requisicoes)

    dep_ini_fixo = rede.nos_fixos[deposito_origem_id]
    no_dep_ini = No(
        id=0,
        x=dep_ini_fixo.x,
        y=dep_ini_fixo.y,
        s=0.0,
        q=0,
        e=janela_deposito_ini[0],
        l=janela_deposito_ini[1],
        id_fixo=deposito_origem_id,
    )

    nos: list[No] = [no_dep_ini]

    # Coletas: 1..n
    for idx, req in enumerate(requisicoes, start=1):
        fixo = rede.nos_fixos[req.origem_id]
        s_emb = req.s_coleta if req.s_coleta is not None else fixo.s_embarque
        nos.append(
            No(
                id=idx,
                x=fixo.x,
                y=fixo.y,
                s=s_emb,
                q=req.q,
                e=req.e_coleta,
                l=req.l_coleta,
                id_fixo=req.origem_id,
            )
        )

    # Entregas: n+1..2n
    for idx, req in enumerate(requisicoes, start=1):
        fixo = rede.nos_fixos[req.destino_id]
        s_des = req.s_entrega if req.s_entrega is not None else fixo.s_desembarque
        nos.append(
            No(
                id=n + idx,
                x=fixo.x,
                y=fixo.y,
                s=s_des,
                q=-req.q,
                e=req.e_entrega,
                l=req.l_entrega,
                id_fixo=req.destino_id,
            )
        )

    # Deposito final: 2n+1
    dep_fim_fixo = rede.nos_fixos[deposito_destino_id]
    no_dep_fim = No(
        id=2 * n + 1,
        x=dep_fim_fixo.x,
        y=dep_fim_fixo.y,
        s=0.0,
        q=0,
        e=janela_deposito_fim[0],
        l=janela_deposito_fim[1],
        id_fixo=deposito_destino_id,
    )
    nos.append(no_dep_fim)

    return Instancia(
        nome=nome,
        m=m,
        n=n,
        T_max=T_max,
        Q=Q,
        L_arquivo=L_arquivo,
        nos=nos,
        formato="rede",
        rede=rede,
        requisicoes=list(requisicoes),
    )
