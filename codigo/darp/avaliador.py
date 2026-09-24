"""Agendamento e avaliacao de solucoes do DARP bi-objetivo.

O avaliador e a peca compartilhada por todas as metaheuristicas do projeto:
recebe uma solucao como conjunto de rotas, calcula os instantes de atendimento,
verifica a viabilidade e devolve os dois objetivos

    f_1  emissao de CO2, igual a phi vezes a distancia total percorrida
    f_2  tempo perdido pelo usuario, em passageiro-minuto, somando o desvio
         de rota (R_i - t_direto_i) e a espera no embarque (B_i - rho_i)

Politica de agendamento
-----------------------
A rota fixa a ordem das visitas, mas nao os instantes: sobra liberdade para
adiantar ou atrasar cada atendimento dentro da janela. Duas politicas estao
disponiveis.

CEDO -- inicio mais cedo. Cada no e atendido no primeiro instante admissivel e
o veiculo sai do deposito na hora exata de chegar sem espera ao primeiro no.
Minimiza a parcela de espera de f_2, mas ignora o tempo a bordo: quando a
janela esta na entrega, embarcar cedo faz o passageiro esperar sentado no
veiculo ate a janela abrir, o que infla R_i e viola o limite L_i.

BORDO -- reducao do tempo a bordo, pelo procedimento de oito passos de Cordeau
& Laporte (2003). Atrasa de proposito a saida do deposito e os embarques, na
medida em que a espera ja existente adiante possa absorver o atraso, o que
encurta o tempo a bordo sem quebrar janelas. Resolve a inviabilidade da
politica CEDO, mas persegue o tempo a bordo, nao f_2, e por isso troca desvio
por espera alem do que conviria.

OTIMO -- agendamento que minimiza f_2 para a sequencia dada, por programacao
linear. Dada a ordem das visitas, nenhuma agenda alcanca f_2 menor, o que
elimina a distorcao das duas politicas anteriores. E o padrao do modulo. Custa
uma resolucao de PL por rota, e por isso as politicas heuristicas seguem
disponiveis para o laco interno das metaheuristicas.

O modulo aceita ainda uma agenda externa, via Solucao.partidas e da funcao
avaliar_com_B, o que permite conferir as formulas contra solucoes publicadas ou
contra a saida do solver sem depender de politica alguma.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .instancia import Instancia
from .solucao import Rota, Solucao

INF = float("inf")

CEDO = "cedo"
BORDO = "bordo"
OTIMO = "otimo"


@dataclass
class Parametros:
    """Parametros que o arquivo de instancia nao fornece."""

    phi: float = 1.0
    """Fator de emissao em g CO2 por unidade de distancia.

    Com phi = 1 o objetivo f_1 coincide numericamente com a distancia total,
    conveniente para validacao contra valores publicados.
    """

    alpha: float | None = None
    """Tolerancia proporcional a bordo: L_i = alpha * t_direto_i.

    Com None usa o limite global L do cabecalho do arquivo.
    """

    custo_fixo: float = 0.0
    custo_distancia: float = 0.0
    custo_hora: float = 0.0

    tolerancia: float = 1e-6
    """Folga numerica na verificacao de restricoes, para absorver erro de
    ponto flutuante acumulado na soma de raizes quadradas."""

    politica: str = OTIMO
    """Politica de agendamento: CEDO, BORDO ou OTIMO."""


@dataclass
class AgendaRota:
    """Resultado do agendamento de uma rota."""

    sequencia: list[int]
    partida: float = 0.0
    retorno: float = 0.0
    distancia: float = 0.0
    B: dict[int, float] = field(default_factory=dict)
    espera: dict[int, float] = field(default_factory=dict)
    carga: dict[int, float] = field(default_factory=dict)
    R: dict[int, float] = field(default_factory=dict)

    @property
    def duracao(self) -> float:
        return self.retorno - self.partida

    @property
    def carga_maxima(self) -> float:
        return max(self.carga.values(), default=0.0)


@dataclass
class Avaliacao:
    """Os dois objetivos e o diagnostico de viabilidade de uma solucao."""

    f1: float = 0.0
    f2: float = 0.0
    distancia: float = 0.0
    f2_desvio: float = 0.0
    f2_espera: float = 0.0
    espera_bruta: float = 0.0
    tempo_bordo: float = 0.0
    custo: float = 0.0
    veiculos_usados: int = 0
    agendas: list[AgendaRota] = field(default_factory=list)
    violacoes: list[str] = field(default_factory=list)

    @property
    def viavel(self) -> bool:
        return not self.violacoes

    @property
    def objetivos(self) -> tuple[float, float]:
        return (self.f1, self.f2)

    def __str__(self) -> str:
        estado = "viavel" if self.viavel else f"INVIAVEL ({len(self.violacoes)})"
        return (f"f1={self.f1:9.2f}  f2={self.f2:10.2f}  "
                f"(desvio={self.f2_desvio:.2f} espera={self.f2_espera:.2f})  "
                f"veiculos={self.veiculos_usados}  {estado}")


class Avaliador:
    def __init__(self, inst: Instancia, par: Parametros | None = None) -> None:
        self.inst = inst
        self.par = par or Parametros()

    # ------------------------------------------------------------------
    # Agendamento
    # ------------------------------------------------------------------

    def _percorrer(self, seq: list[int], partida: float,
                   atraso: dict[int, float] | None = None) -> AgendaRota:
        """Passada para frente: propaga o tempo ao longo da sequencia.

        O dicionario atraso permite impor espera adicional em nos escolhidos,
        alem da que a janela de tempo ja obriga. E o mecanismo usado pelo
        procedimento de reducao do tempo a bordo.
        """
        inst = self.inst
        ag = AgendaRota(sequencia=list(seq), partida=partida)

        anterior = inst.deposito_ini
        instante = partida
        a_bordo = 0.0

        for no in seq:
            trecho = inst.tempo(anterior, no)
            ag.distancia += trecho
            chegada = instante + trecho

            dados = inst.nos[no]
            inicio = max(chegada, dados.e)
            if atraso:
                inicio += atraso.get(no, 0.0)
            ag.B[no] = inicio
            ag.espera[no] = inicio - chegada

            a_bordo += dados.q
            ag.carga[no] = a_bordo

            instante = inicio + dados.s
            anterior = no

        ag.distancia += inst.tempo(anterior, inst.deposito_fim)
        ag.retorno = instante + inst.tempo(anterior, inst.deposito_fim)
        self._calcular_bordo(ag)
        return ag

    # ------------------------------------------------------------------
    # Folga de tempo para frente
    # ------------------------------------------------------------------

    def _folga_apos(self, ag: AgendaRota, pos: int) -> float:
        """Maior atraso admissivel na saida da posicao pos da sequencia.

        Com pos = -1 refere-se a saida do deposito. Atrasar a saida de pos em
        delta desloca o atendimento de cada no j adiante em
        max(0, delta - soma das esperas entre pos e j), porque a espera ja
        existente absorve parte do atraso. O limite vem de tres fontes:

          janela         o deslocamento em j nao pode levar B_j acima de l_j;
          tempo a bordo  se j e a entrega de alguem embarcado ANTES de pos, a
                         coleta nao se desloca e o tempo a bordo cresce junto
                         com o deslocamento, entao ele cabe em L_i - R_i;
          duracao        o retorno ao deposito nao pode estourar T_max.

        Passageiros embarcados em pos ou depois nao entram: o deslocamento e
        nao crescente ao longo da rota, logo a coleta se desloca pelo menos
        tanto quanto a entrega e o tempo a bordo nao aumenta.
        """
        inst, seq = self.inst, ag.sequencia
        posicao = {no: p for p, no in enumerate(seq)}

        folga = INF
        absorvido = 0.0

        for j in range(pos + 1, len(seq)):
            no = seq[j]
            absorvido += ag.espera[no]

            limite = inst.nos[no].l - ag.B[no]
            if no > inst.n:
                i = inst.coleta_de(no)
                if i in ag.R and posicao.get(i, -1) < pos:
                    limite = min(limite,
                                 inst.limite_bordo(i, self.par.alpha) - ag.R[i])

            folga = min(folga, absorvido + limite)

        # Retorno ao deposito: janela do deposito e duracao maxima da rota.
        limite_fim = min(inst.nos[inst.deposito_fim].l - ag.retorno,
                         inst.T_max - ag.duracao)
        folga = min(folga, absorvido + limite_fim)

        return max(0.0, folga)

    # ------------------------------------------------------------------
    # Politica de reducao do tempo a bordo (oito passos)
    # ------------------------------------------------------------------

    def _penalidade(self, ag: AgendaRota) -> tuple[float, float]:
        """Criterio de aceitacao dos atrasos.

        O primeiro termo soma toda a violacao de janela, de tempo a bordo e de
        duracao; o segundo soma o tempo a bordo. Um atraso so e mantido se nao
        piorar esse par, o que torna o procedimento seguro mesmo nos casos em
        que o calculo de folga e conservador.
        """
        inst = self.inst
        violacao = max(0.0, ag.duracao - inst.T_max)
        for no in ag.sequencia:
            violacao += max(0.0, ag.B[no] - inst.nos[no].l)
        for i, valor in ag.R.items():
            violacao += max(0.0, valor - inst.limite_bordo(i, self.par.alpha))
        return (violacao, sum(ag.R.values()))

    def _agendar_bordo(self, seq: list[int], partida: float | None) -> AgendaRota:
        """Procedimento de oito passos de Cordeau & Laporte (2003)."""
        inst = self.inst
        base = inst.nos[inst.deposito_ini].e
        atraso: dict[int, float] = {}

        # Passos 1 e 2: agenda de inicio mais cedo.
        ag = self._percorrer(seq, base if partida is None else partida)

        # Passos 3 a 5: atrasar a saida do deposito ate onde a espera adiante
        # absorva, o que encurta o tempo a bordo de todos sem mover mais nada.
        if partida is None:
            avanco = min(self._folga_apos(ag, -1), sum(ag.espera.values()))
            if avanco > 0:
                candidata = self._percorrer(seq, base + avanco)
                if self._penalidade(candidata) <= self._penalidade(ag):
                    ag = candidata

        # Passos 6 a 8: atrasar cada embarque, na ordem da rota. Atrasar uma
        # coleta encurta o percurso de quem embarca ali e prolonga o de quem ja
        # esta a bordo; a folga limita o segundo efeito e o criterio de
        # aceitacao descarta o atraso que nao compense.
        for pos, no in enumerate(seq):
            if no > inst.n:
                continue

            absorvivel = sum(ag.espera[seq[j]] for j in range(pos + 1, len(seq)))
            margem = min(inst.nos[no].l - ag.B[no], self._folga_apos(ag, pos))
            avanco = min(margem, absorvivel)
            if avanco <= self.par.tolerancia:
                continue

            atraso[no] = atraso.get(no, 0.0) + avanco
            candidata = self._percorrer(seq, ag.partida, atraso)
            if self._penalidade(candidata) <= self._penalidade(ag):
                ag = candidata
            else:
                atraso[no] -= avanco

        return ag

    def _calcular_bordo(self, ag: AgendaRota) -> None:
        """Tempo a bordo: R_i = B_{n+i} - (B_i + s_i)."""
        inst = self.inst
        for no in ag.sequencia:
            if no > inst.n:
                continue
            entrega = inst.entrega_de(no)
            if entrega in ag.B:
                ag.R[no] = ag.B[entrega] - (ag.B[no] + inst.nos[no].s)

    # ------------------------------------------------------------------
    # Politica de agendamento otimo (programacao linear)
    # ------------------------------------------------------------------

    def _montar_com_B(self, seq: list[int], partida: float,
                      B: dict[int, float]) -> AgendaRota:
        """Monta a agenda a partir de instantes de atendimento ja definidos."""
        inst = self.inst
        ag = AgendaRota(sequencia=list(seq), partida=partida)

        anterior = inst.deposito_ini
        instante = partida
        a_bordo = 0.0

        for no in seq:
            trecho = inst.tempo(anterior, no)
            ag.distancia += trecho
            ag.B[no] = B[no]
            ag.espera[no] = B[no] - (instante + trecho)
            a_bordo += inst.nos[no].q
            ag.carga[no] = a_bordo
            instante = B[no] + inst.nos[no].s
            anterior = no

        ag.distancia += inst.tempo(anterior, inst.deposito_fim)
        ag.retorno = instante + inst.tempo(anterior, inst.deposito_fim)
        self._calcular_bordo(ag)
        return ag

    def _agendar_otimo(self, seq: list[int], partida: float | None) -> AgendaRota:
        """Agenda que minimiza a contribuicao da rota para f_2.

        Para uma sequencia fixa, f_2 e linear nos instantes de atendimento e
        todas as restricoes temporais tambem o sao, de modo que o agendamento
        otimo e um programa linear pequeno, com uma variavel por no visitado
        mais uma por embarque (a espera, que lineariza o max com zero).

        Nao e uma heuristica: dada a ordem das visitas, nenhuma agenda alcanca
        f_2 menor. A ordem em si continua sendo decidida pela metaheuristica.
        """
        try:
            import numpy as np
            from scipy.optimize import linprog
        except ImportError:
            return self._agendar_bordo(seq, partida)

        inst = self.inst
        ini, fim = inst.deposito_ini, inst.deposito_fim
        coletas = [no for no in seq if no <= inst.n]
        pos_B = {no: p for p, no in enumerate(seq)}
        pos_esp = {no: len(seq) + p for p, no in enumerate(coletas)}
        total = len(seq) + len(coletas)

        primeiro, ultimo = seq[0], seq[-1]
        t_entrada = inst.tempo(ini, primeiro)
        t_saida = inst.tempo(ultimo, fim)

        custo = np.zeros(total)
        for i in coletas:
            q = inst.nos[i].q
            entrega = inst.entrega_de(i)
            if entrega in pos_B:
                custo[pos_B[entrega]] += q
                custo[pos_B[i]] -= q
            custo[pos_esp[i]] += q

        A: list[list[float]] = []
        b: list[float] = []

        def restricao(termos: dict[int, float], limite: float) -> None:
            linha = [0.0] * total
            for indice, coef in termos.items():
                linha[indice] += coef
            A.append(linha)
            b.append(limite)

        # Encadeamento temporal ao longo da sequencia.
        for anterior, seguinte in zip(seq, seq[1:]):
            restricao({pos_B[anterior]: 1.0, pos_B[seguinte]: -1.0},
                      -(inst.nos[anterior].s + inst.tempo(anterior, seguinte)))

        # Tempo maximo a bordo.
        for i in coletas:
            entrega = inst.entrega_de(i)
            if entrega in pos_B:
                restricao({pos_B[entrega]: 1.0, pos_B[i]: -1.0},
                          inst.limite_bordo(i, self.par.alpha) + inst.nos[i].s)

        # Espera no embarque: esp_i >= B_i - rho_i, com esp_i >= 0 pelos limites.
        for i in coletas:
            restricao({pos_B[i]: 1.0, pos_esp[i]: -1.0}, inst.rho[i])

        # Duracao maxima da rota e janela do deposito de retorno.
        folga_fim = inst.nos[ultimo].s + t_saida
        if partida is None:
            # A saida do deposito acompanha o primeiro atendimento, o que torna
            # a duracao dependente apenas da diferenca entre o ultimo e o primeiro.
            restricao({pos_B[ultimo]: 1.0, pos_B[primeiro]: -1.0},
                      inst.T_max - folga_fim - t_entrada)
        else:
            restricao({pos_B[ultimo]: 1.0}, inst.T_max + partida - folga_fim)
        restricao({pos_B[ultimo]: 1.0}, inst.nos[fim].l - folga_fim)

        limites: list[tuple[float, float]] = []
        for no in seq:
            inferior = inst.nos[no].e
            if no == primeiro:
                base = (inst.nos[ini].e if partida is None else partida)
                inferior = max(inferior, base + t_entrada)
            limites.append((inferior, inst.nos[no].l))
        limites += [(0.0, None)] * len(coletas)

        saida = linprog(custo, A_ub=A, b_ub=b, bounds=limites, method="highs")
        if not saida.success:
            # Rota temporalmente inviavel: devolve a agenda heuristica para que
            # as violacoes sejam diagnosticadas normalmente.
            return self._agendar_bordo(seq, partida)

        B = {no: float(saida.x[pos_B[no]]) for no in seq}
        escolhida = partida if partida is not None else B[primeiro] - t_entrada
        return self._montar_com_B(seq, escolhida, B)

    def _agendar_cedo(self, seq: list[int], partida: float | None) -> AgendaRota:
        inst = self.inst
        if partida is None:
            base = inst.nos[inst.deposito_ini].e
            provisoria = self._percorrer(seq, base)
            primeiro = seq[0]
            partida = max(base, provisoria.B[primeiro]
                          - inst.tempo(inst.deposito_ini, primeiro))
        return self._percorrer(seq, partida)

    def agendar(self, rota: Rota, partida: float | None = None,
                politica: str | None = None) -> AgendaRota:
        """Agenda uma rota segundo a politica escolhida.

        Com partida informada, o instante de saida do deposito e respeitado e
        apenas os embarques intermediarios podem ser atrasados.
        """
        if not rota.sequencia:
            return AgendaRota(sequencia=[])

        politica = politica or self.par.politica
        if politica == CEDO:
            return self._agendar_cedo(rota.sequencia, partida)
        if politica == BORDO:
            return self._agendar_bordo(rota.sequencia, partida)
        if politica == OTIMO:
            return self._agendar_otimo(rota.sequencia, partida)
        raise ValueError(f"politica de agendamento desconhecida: {politica}")

    # ------------------------------------------------------------------
    # Viabilidade
    # ------------------------------------------------------------------

    def _violacoes(self, k: int, ag: AgendaRota) -> list[str]:
        inst, tol = self.inst, self.par.tolerancia
        fora: list[str] = []

        for no in ag.sequencia:
            if ag.B[no] > inst.nos[no].l + tol:
                fora.append(f"rota {k}: janela no no {no} "
                            f"(B={ag.B[no]:.2f} > l={inst.nos[no].l:.2f})")
            if ag.carga[no] > inst.Q + tol:
                fora.append(f"rota {k}: capacidade no no {no} "
                            f"(carga={ag.carga[no]:.0f} > Q={inst.Q})")

        for i, valor in ag.R.items():
            limite = inst.limite_bordo(i, self.par.alpha)
            if valor > limite + tol:
                fora.append(f"rota {k}: tempo a bordo da solicitacao {i} "
                            f"(R={valor:.2f} > L={limite:.2f})")

        if ag.duracao > inst.T_max + tol:
            fora.append(f"rota {k}: duracao {ag.duracao:.2f} > T_max={inst.T_max:.2f}")

        return fora

    # ------------------------------------------------------------------
    # Objetivos
    # ------------------------------------------------------------------

    def contribuicao(self, ag: AgendaRota) -> tuple[float, float, float]:
        """Parcelas de f_2 e tempo a bordo aportados por uma rota agendada.

        Devolve (desvio, espera, tempo a bordo), todos em passageiro-minuto
        exceto o ultimo, que e minuto.
        """
        inst = self.inst
        desvio = espera = bordo = 0.0
        for no in ag.sequencia:
            if no > inst.n:
                continue
            q = inst.nos[no].q
            # O desvio e nao negativo pela desigualdade triangular; o max
            # apenas absorve o residuo numerico do agendamento por PL.
            desvio += q * max(0.0, ag.R.get(no, 0.0) - inst.t_direto(no))
            espera += q * max(0.0, ag.B[no] - inst.rho[no])
            bordo += ag.R.get(no, 0.0)
        return desvio, espera, bordo

    def avaliar_rota(self, rota: Rota, partida: float | None = None,
                     politica: str | None = None) -> tuple[AgendaRota, list[str]]:
        """Agenda e verifica uma rota isolada, sem exigir cobertura global.

        Usado pela enumeracao exata e pela busca local, que trabalham rota a
        rota. Os objetivos sao aditivos entre rotas e as restricoes sao todas
        internas a rota, o que torna essa avaliacao independente valida.
        """
        ag = self.agendar(rota, partida, politica)
        return ag, self._violacoes(0, ag)

    def avaliar(self, sol: Solucao, politica: str | None = None) -> Avaliacao:
        inst, par = self.inst, self.par
        res = Avaliacao()

        res.violacoes.extend(sol.conferir_estrutura(inst))

        for k, rota in enumerate(sol.rotas):
            if not rota.usada:
                continue
            partida = (sol.partidas or {}).get(k)
            ag = self.agendar(rota, partida, politica)
            res.agendas.append(ag)
            res.violacoes.extend(self._violacoes(k, ag))

            res.distancia += ag.distancia
            res.veiculos_usados += 1
            res.custo += (par.custo_fixo
                          + par.custo_distancia * ag.distancia
                          + par.custo_hora * ag.duracao)

            desvio, espera, bordo = self.contribuicao(ag)
            res.f2_desvio += desvio
            res.f2_espera += espera
            res.tempo_bordo += bordo
            res.espera_bruta += sum(ag.espera.values())

        res.f1 = par.phi * res.distancia
        res.f2 = res.f2_desvio + res.f2_espera
        return res

    def avaliar_com_B(self, sol: Solucao, B: dict[int, float],
                      partidas: dict[int, float]) -> Avaliacao:
        """Avalia usando instantes de atendimento fornecidos de fora.

        Contorna a politica de agendamento para conferir as formulas de
        distancia, tempo a bordo, espera e carga contra uma solucao publicada.
        """
        inst, par = self.inst, self.par
        res = Avaliacao()
        res.violacoes.extend(sol.conferir_estrutura(inst))

        for k, rota in enumerate(sol.rotas):
            if not rota.usada:
                continue

            ag = self._montar_com_B(rota.sequencia, partidas[k], B)
            res.agendas.append(ag)
            res.violacoes.extend(self._violacoes(k, ag))
            res.distancia += ag.distancia
            res.veiculos_usados += 1
            res.espera_bruta += sum(ag.espera.values())

            desvio, espera, bordo = self.contribuicao(ag)
            res.f2_desvio += desvio
            res.f2_espera += espera
            res.tempo_bordo += bordo

        res.f1 = par.phi * res.distancia
        res.f2 = res.f2_desvio + res.f2_espera
        return res
