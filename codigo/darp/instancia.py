"""Leitura e representacao das instancias DARP.

Suporta tanto as colecoes classicas de Cordeau & Laporte (nos gerados geometricamente
por solicitacao com distancia euclidiana) quanto o novo modelo com nos fixos
(pontos de interesse / paradas pre-definidas com matriz de distancias/tempos em grafo).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from .rede import NoFixo, Rede, Requisicao, criar_instancia_rede

# Janela [0, 1440] e o valor que os arquivos usam para "sem restricao".
JANELA_LIVRE = 1440.0

# Classificacao de cada solicitacao conforme onde esta a janela apertada.
IDA = "ida"        # janela na coleta: o usuario marca a hora de embarque
VOLTA = "volta"    # janela na entrega: o usuario marca a hora de chegada
LIVRE = "livre"    # nenhuma das duas pontas tem janela apertada


@dataclass(frozen=True)
class No:
    """Um no do grafo de atendimento: deposito, ponto de coleta ou ponto de entrega."""

    id: int
    x: float
    y: float
    s: float    # tempo de servico (embarque/desembarque)
    q: int      # passageiros; positivo na coleta, negativo na entrega
    e: float    # inicio da janela de tempo
    l: float    # fim da janela de tempo
    id_fixo: int | None = None  # ID do no fixo (parada) correspondente na Rede

    @property
    def janela_apertada(self) -> bool:
        return not (self.e <= 0.0 and self.l >= JANELA_LIVRE)


@dataclass
class Instancia:
    nome: str
    m: int                  # veiculos disponiveis
    n: int                  # solicitacoes
    T_max: float            # duracao maxima de rota
    Q: int                  # capacidade do veiculo
    L_arquivo: float        # tempo maximo a bordo declarado no cabecalho
    nos: list[No]           # indexado pelo id; comprimento 2n+2
    formato: str

    # Rede de nos fixos e requisicoes mapeadas (quando aplicavel)
    rede: Rede | None = None
    requisicoes: list[Requisicao] = field(default_factory=list, repr=False)

    # Derivados no __post_init__.
    tipo: dict[int, str] = field(default_factory=dict, repr=False)
    rho: dict[int, float] = field(default_factory=dict, repr=False)

    # ----- indices -----

    @property
    def coletas(self) -> range:
        return range(1, self.n + 1)

    @property
    def entregas(self) -> range:
        return range(self.n + 1, 2 * self.n + 1)

    @property
    def atendimento(self) -> range:
        return range(1, 2 * self.n + 1)

    @property
    def deposito_ini(self) -> int:
        return 0

    @property
    def deposito_fim(self) -> int:
        return 2 * self.n + 1

    def entrega_de(self, i: int) -> int:
        return i + self.n

    def coleta_de(self, j: int) -> int:
        return j - self.n

    def solicitacao_de(self, no: int) -> int:
        """Solicitacao a que um no de atendimento pertence."""
        return no if no <= self.n else no - self.n

    def no_fixo_de(self, no: int) -> NoFixo | None:
        """Retorna o NoFixo associado ao no de atendimento, se existir na Rede."""
        if self.rede is not None and self.nos[no].id_fixo is not None:
            return self.rede.nos_fixos.get(self.nos[no].id_fixo)
        return None

    # ----- geometria e tempo -----

    def dist(self, i: int, j: int) -> float:
        """Distancia entre dois nos de atendimento.

        Se a instancia possuir uma Rede de nos fixos associada, consulta a
        matriz de distancias da rede. Caso contrario, calcula a distancia
        euclidiana classica entre as coordenadas dos nos.
        """
        if self.rede is not None:
            id_i = self.nos[i].id_fixo
            id_j = self.nos[j].id_fixo
            if id_i is not None and id_j is not None:
                return self.rede.dist(id_i, id_j)

        a, b = self.nos[i], self.nos[j]
        return math.hypot(a.x - b.x, a.y - b.y)

    def tempo(self, i: int, j: int) -> float:
        """Tempo de percurso entre dois nos de atendimento.

        Se houver Rede associada com matriz de tempos, faz a consulta direta.
        Nas instancias classicas, segue a convencao de velocidade unitaria.
        """
        if self.rede is not None:
            id_i = self.nos[i].id_fixo
            id_j = self.nos[j].id_fixo
            if id_i is not None and id_j is not None:
                return self.rede.tempo(id_i, id_j)

        return self.dist(i, j)

    def t_direto(self, i: int) -> float:
        """Tempo do percurso direto da solicitacao i (t_barra_i)."""
        return self.tempo(i, self.entrega_de(i))

    def limite_bordo(self, i: int, alpha: float | None = None) -> float:
        """Tempo maximo tolerado a bordo (L_i).

        Com alpha=None usa o limite global do arquivo. Com alpha informado usa
        L_i = alpha * t_direto_i, a definicao proporcional adotada no relatorio.
        """
        if alpha is None:
            return self.L_arquivo
        return alpha * self.t_direto(i)

    # ----- derivados -----

    def __post_init__(self) -> None:
        esperado = 2 * self.n + 2
        if len(self.nos) != esperado:
            raise ValueError(f"esperados {esperado} nos, recebidos {len(self.nos)}")
        self._classificar_solicitacoes()

    def _classificar_solicitacoes(self) -> None:
        """Define o tipo de cada solicitacao e o horario desejado de embarque.

        O arquivo nao traz rho_i explicitamente, entao ele e inferido da ponta
        que tem janela apertada:

            ida    rho_i = e_i, a hora de embarque pedida esta no proprio no
            volta  rho_i = e_{n+i} - s_i - t_direto_i, isto e, a hora de sair
                   para chegar no inicio da janela de entrega pelo caminho direto
            livre  rho_i = e_i, caso degenerado sem hora pedida
        """
        for i in self.coletas:
            coleta, entrega = self.nos[i], self.nos[self.entrega_de(i)]
            if coleta.janela_apertada:
                self.tipo[i] = IDA
                self.rho[i] = coleta.e
            elif entrega.janela_apertada:
                self.tipo[i] = VOLTA
                self.rho[i] = entrega.e - coleta.s - self.t_direto(i)
            else:
                self.tipo[i] = LIVRE
                self.rho[i] = coleta.e

    def resumo(self) -> str:
        contagem = {t: sum(1 for i in self.coletas if self.tipo[i] == t)
                    for t in (IDA, VOLTA, LIVRE)}
        tipo_rede = f" [rede:{len(self.rede.nos_fixos)} paradas]" if self.rede else ""
        return (f"{self.nome}: m={self.m} n={self.n} Q={self.Q} "
                f"T_max={self.T_max:.0f} L={self.L_arquivo:.0f} "
                f"formato={self.formato}{tipo_rede} "
                f"ida={contagem[IDA]} volta={contagem[VOLTA]} livre={contagem[LIVRE]}")


def ler_instancia(caminho: str | Path) -> Instancia:
    caminho = Path(caminho)
    linhas = [l for l in caminho.read_text().splitlines() if l.strip()]

    cabecalho = [float(v) for v in linhas[0].split()]
    if len(cabecalho) < 5:
        raise ValueError(f"cabecalho com {len(cabecalho)} campos, esperados 5")
    m, campo2, T_max, Q, L = cabecalho[:5]

    brutos = [[float(v) for v in l.split()] for l in linhas[1:]]

    # A quantidade de linhas de no desambigua o significado do segundo campo.
    if len(brutos) == 2 * campo2 + 2:
        n, formato = int(campo2), "2n+2"
    elif len(brutos) == campo2 + 1:
        n, formato = int(campo2) // 2, "2n+1"
    else:
        raise ValueError(
            f"{caminho.name}: {len(brutos)} linhas de no nao correspondem a "
            f"2n+2 nem a 2n+1 com o campo 2 igual a {campo2:.0f}"
        )

    nos = [No(id=int(b[0]), x=b[1], y=b[2], s=b[3], q=int(b[4]), e=b[5], l=b[6])
           for b in brutos]

    # Normaliza para que o deposito final seja sempre o no 2n+1.
    if formato == "2n+1":
        origem = nos[0]
        nos.append(No(id=2 * n + 1, x=origem.x, y=origem.y, s=0.0, q=0,
                      e=origem.e, l=origem.l))

    for esperado, no in enumerate(nos):
        if no.id != esperado:
            raise ValueError(f"{caminho.name}: no {esperado} tem id {no.id}")

    return Instancia(nome=caminho.name, m=int(m), n=n, T_max=T_max, Q=int(Q),
                     L_arquivo=L, nos=nos, formato=formato)


def reduzir(inst: Instancia, pedidos: list[int], m: int | None = None) -> Instancia:
    """Recorta uma instancia menor mantendo apenas as solicitacoes escolhidas.

    Os nos sao renumerados para continuar obedecendo a convencao de que a
    entrega da solicitacao i e o no i + n. Preserva o mapeamento da rede de nos fixos.
    """
    pedidos = sorted(pedidos)
    k = len(pedidos)
    if not pedidos or pedidos[0] < 1 or pedidos[-1] > inst.n:
        raise ValueError(f"solicitacoes fora de 1..{inst.n}: {pedidos}")

    nos = [No(id=0, x=inst.nos[0].x, y=inst.nos[0].y, s=inst.nos[0].s,
              q=0, e=inst.nos[0].e, l=inst.nos[0].l, id_fixo=inst.nos[0].id_fixo)]
    for novo, antigo in enumerate(pedidos, start=1):
        fonte = inst.nos[antigo]
        nos.append(No(id=novo, x=fonte.x, y=fonte.y, s=fonte.s, q=fonte.q,
                      e=fonte.e, l=fonte.l, id_fixo=fonte.id_fixo))
    for novo, antigo in enumerate(pedidos, start=1):
        fonte = inst.nos[inst.entrega_de(antigo)]
        nos.append(No(id=k + novo, x=fonte.x, y=fonte.y, s=fonte.s, q=fonte.q,
                      e=fonte.e, l=fonte.l, id_fixo=fonte.id_fixo))
    fim = inst.nos[inst.deposito_fim]
    nos.append(No(id=2 * k + 1, x=fim.x, y=fim.y, s=0.0, q=0, e=fim.e, l=fim.l,
                  id_fixo=fim.id_fixo))

    reqs = (
        [inst.requisicoes[p - 1] for p in pedidos]
        if inst.requisicoes and len(inst.requisicoes) >= inst.n
        else []
    )

    return Instancia(nome=f"{inst.nome}-r{k}", m=m if m is not None else inst.m,
                     n=k, T_max=inst.T_max, Q=inst.Q, L_arquivo=inst.L_arquivo,
                     nos=nos, formato=inst.formato, rede=inst.rede, requisicoes=reqs)


def salvar_instancia_json(inst: Instancia, caminho: str | Path) -> None:
    """Exporta a instancia (e sua rede de nos fixos se houver) para JSON."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    dados: dict = {
        "nome": inst.nome,
        "m": inst.m,
        "n": inst.n,
        "T_max": inst.T_max,
        "Q": inst.Q,
        "L_arquivo": inst.L_arquivo,
        "formato": inst.formato,
    }

    if inst.rede is not None:
        dados["rede"] = inst.rede.to_dict()
        dados["requisicoes"] = [r.to_dict() for r in inst.requisicoes]
        deposito_ini_id = inst.nos[inst.deposito_ini].id_fixo
        deposito_fim_id = inst.nos[inst.deposito_fim].id_fixo
        dados["deposito_origem_id"] = deposito_ini_id
        dados["deposito_destino_id"] = deposito_fim_id
        dados["janela_deposito_ini"] = [inst.nos[0].e, inst.nos[0].l]
        dados["janela_deposito_fim"] = [inst.nos[-1].e, inst.nos[-1].l]
    else:
        dados["nos"] = [
            {
                "id": no.id,
                "x": no.x,
                "y": no.y,
                "s": no.s,
                "q": no.q,
                "e": no.e,
                "l": no.l,
                "id_fixo": no.id_fixo,
            }
            for no in inst.nos
        ]

    caminho.write_text(json.dumps(dados, indent=2), encoding="utf-8")


def ler_instancia_json(caminho: str | Path, *, Q: int | None = None) -> Instancia:
    """Carrega uma instancia a partir de um arquivo JSON."""
    caminho = Path(caminho)
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if not isinstance(dados, dict):
        raise ValueError("entrada JSON: esperado objeto")
    if Q is not None:
        if isinstance(Q, bool) or not isinstance(Q, int) or Q < 1:
            raise ValueError("Q do experimento deve ser inteiro positivo")
        dados["Q"] = Q
    if "Q" not in dados:
        raise ValueError("Q nao esta na demanda: informe a capacidade do experimento ao carregar a instancia")
    if "parametros_avaliacao" in dados:
        ler_parametros_json(caminho)

    if "rede" in dados:
        _validar_entrada_rede(dados)
        rede = Rede.from_dict(dados["rede"])
        # Nao permitir que pares ausentes em uma rede viaria virem atalhos
        # euclidianos pelo fallback da API generica de Rede.
        ids = rede.nos_fixos
        if "arestas" in dados["rede"] or "matriz_dist" in dados["rede"]:
            for u in ids:
                for v in ids:
                    if u != v and ((u, v) not in rede.matriz_dist
                                   or (u, v) not in rede.matriz_tempo):
                        raise ValueError(f"rede: falta caminho/distancia/tempo de {u} para {v}")
        reqs = [Requisicao.from_dict(r) for r in dados.get("requisicoes", [])]
        dep_ini = dados.get("deposito_origem_id", 0)
        dep_fim = dados.get("deposito_destino_id", dep_ini)
        j_ini = tuple(dados.get("janela_deposito_ini", [0.0, JANELA_LIVRE]))
        j_fim = tuple(dados.get("janela_deposito_fim", [0.0, JANELA_LIVRE]))

        return criar_instancia_rede(
            nome=dados["nome"],
            rede=rede,
            requisicoes=reqs,
            deposito_origem_id=dep_ini,
            deposito_destino_id=dep_fim,
            m=int(dados["m"]),
            T_max=float(dados["T_max"]),
            Q=int(dados["Q"]),
            L_arquivo=float(dados["L_arquivo"]),
            janela_deposito_ini=j_ini,
            janela_deposito_fim=j_fim,
        )

    nos = [
        No(
            id=int(item["id"]),
            x=float(item["x"]),
            y=float(item["y"]),
            s=float(item["s"]),
            q=int(item["q"]),
            e=float(item["e"]),
            l=float(item["l"]),
            id_fixo=item.get("id_fixo"),
        )
        for item in dados["nos"]
    ]

    return Instancia(
        nome=dados["nome"],
        m=int(dados["m"]),
        n=int(dados["n"]),
        T_max=float(dados["T_max"]),
        Q=int(dados["Q"]),
        L_arquivo=float(dados["L_arquivo"]),
        nos=nos,
        formato=dados.get("formato", "json"),
    )


def _validar_entrada_rede(dados: dict) -> None:
    """Valida o contrato de entrada de rede antes de converter os tipos."""
    def numero(valor, campo, minimo=0):
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor < minimo:
            raise ValueError(f"{campo}: esperado numero finito >= {minimo}")

    def inteiro(valor, campo, minimo=0):
        if isinstance(valor, bool) or not isinstance(valor, int) or valor < minimo:
            raise ValueError(f"{campo}: esperado inteiro >= {minimo}")

    def janela(valor, campo):
        if not isinstance(valor, (list, tuple)) or len(valor) != 2:
            raise ValueError(f"{campo}: esperado [inicio, fim]")
        for v in valor:
            numero(v, campo)
        if valor[0] > valor[1]:
            raise ValueError(f"{campo}: inicio maior que fim")

    inteiro(dados.get("versao_formato", 1), "versao_formato", 1)
    if dados.get("versao_formato", 1) != 1:
        raise ValueError("versao_formato: apenas versao 1 suportada")
    if not isinstance(dados.get("nome"), str) or not dados["nome"].strip():
        raise ValueError("nome: esperado texto nao vazio")
    for campo in ("m", "Q"):
        inteiro(dados.get(campo), campo, 1)
    for campo in ("T_max", "L_arquivo"):
        numero(dados.get(campo), campo)
    for campo in ("janela_deposito_ini", "janela_deposito_fim"):
        janela(dados.get(campo, [0, JANELA_LIVRE]), campo)
    unidades = dados.get("unidades")
    if unidades is not None and unidades != {"distancia": "km", "tempo": "min", "demanda": "passageiros"}:
        raise ValueError("unidades: o contrato urbano usa km, min e passageiros")
    rede = dados["rede"]
    if not isinstance(rede, dict) or not isinstance(rede.get("nos_fixos"), list) or not rede["nos_fixos"]:
        raise ValueError("rede.nos_fixos: esperado lista nao vazia")
    ids = set()
    for no in rede["nos_fixos"]:
        if not isinstance(no, dict):
            raise ValueError("rede.nos_fixos: cada parada deve ser objeto")
        inteiro(no.get("id"), "no.id")
        if no["id"] in ids:
            raise ValueError(f"no.id duplicado: {no['id']}")
        ids.add(no["id"])
        for c in ("x", "y"):
            numero(no.get(c), f"no.{c}", -float("inf"))
        for c in ("s_embarque", "s_desembarque"):
            numero(no.get(c, 0), f"no.{c}")
    for campo in ("deposito_origem_id", "deposito_destino_id"):
        valor = dados.get(campo, dados.get("deposito_origem_id", 0))
        inteiro(valor, campo)
        if valor not in ids:
            raise ValueError(f"{campo}: parada inexistente {valor}")
    if not isinstance(rede.get("direcionado", False), bool):
        raise ValueError("rede.direcionado: esperado booleano")
    numero(rede.get("velocidade", 1), "rede.velocidade", 1e-12)
    if rede.get("arestas") and rede.get("matriz_dist"):
        raise ValueError("rede: escolha arestas ou matrizes, nao ambas")
    if rede.get("matriz_tempo") and not rede.get("matriz_dist"):
        raise ValueError("rede: matriz_tempo exige matriz_dist")
    for campo in ("arestas", "matriz_dist", "matriz_tempo"):
        pares = set()
        if not isinstance(rede.get(campo, []), list):
            raise ValueError(f"rede.{campo}: esperado lista")
        if campo in rede and not rede[campo]:
            raise ValueError(f"rede.{campo}: lista vazia; omita o campo ou informe os custos")
        for item in rede.get(campo, []):
            if not isinstance(item, dict):
                raise ValueError(f"rede.{campo}: cada item deve ser objeto")
            par = (item.get("origem"), item.get("destino"))
            for v in par:
                inteiro(v, f"{campo}.parada")
                if v not in ids:
                    raise ValueError(f"{campo}: parada inexistente {v}")
            chave = tuple(sorted(par)) if campo == "arestas" and not rede.get("direcionado", False) else par
            if chave in pares:
                raise ValueError(f"{campo}: par duplicado {par}")
            pares.add(chave)
            numero(item.get("distancia") if campo == "arestas" else item.get("valor"), campo)
            if campo == "arestas" and "tempo" in item:
                numero(item["tempo"], "aresta.tempo")
    reqs = dados.get("requisicoes")
    if not isinstance(reqs, list) or not reqs:
        raise ValueError("requisicoes: esperado lista nao vazia")
    pedidos = set()
    for req in reqs:
        if not isinstance(req, dict):
            raise ValueError("requisicoes: cada pedido deve ser objeto")
        inteiro(req.get("id"), "requisicao.id", 1)
        if req["id"] in pedidos:
            raise ValueError(f"requisicao.id duplicado: {req['id']}")
        pedidos.add(req["id"])
        inteiro(req.get("q", 1), "requisicao.q", 1)
        for c in ("origem_id", "destino_id"):
            inteiro(req.get(c), f"requisicao.{c}")
            if req[c] not in ids:
                raise ValueError(f"requisicao.{c}: parada inexistente")
        if req["origem_id"] == req["destino_id"]:
            raise ValueError("requisicao: origem e destino devem ser distintos")
        for ponta in ("coleta", "entrega"):
            janela([req.get(f"e_{ponta}", 0), req.get(f"l_{ponta}", JANELA_LIVRE)], f"requisicao.{ponta}")
            if req.get(f"s_{ponta}") is not None:
                numero(req[f"s_{ponta}"], f"requisicao.s_{ponta}")


def ler_parametros_json(caminho: str | Path):
    """Le parametros operacionais opcionais; a leitura da instancia e separada."""
    from .avaliador import BORDO, CEDO, OTIMO, Parametros
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    if not isinstance(dados, dict):
        raise ValueError("entrada JSON: esperado objeto")
    valores = dados.get("parametros_avaliacao", {})
    if not isinstance(valores, dict):
        raise ValueError("parametros_avaliacao: esperado objeto")
    permitidos = set(Parametros.__dataclass_fields__)
    desconhecidos = set(valores) - permitidos
    if desconhecidos:
        raise ValueError(f"parametros_avaliacao: campos desconhecidos {sorted(desconhecidos)}")
    par = Parametros(**valores)
    for campo in ("phi", "custo_fixo", "custo_distancia", "custo_hora", "tolerancia"):
        v = getattr(par, campo)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError(f"parametros_avaliacao.{campo}: esperado numero finito nao negativo")
    if par.alpha is not None and (isinstance(par.alpha, bool) or not isinstance(par.alpha, (int, float))
                                  or not math.isfinite(par.alpha) or par.alpha < 1):
        raise ValueError("parametros_avaliacao.alpha: esperado null ou numero >= 1")
    if par.politica not in (CEDO, BORDO, OTIMO):
        raise ValueError("parametros_avaliacao.politica: escolha cedo, bordo ou otimo")
    return par
