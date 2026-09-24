#!/usr/bin/env python3
"""Validacao da Fase 1: leitor de instancias e avaliador.

Roda tres baterias de conferencia.

1. Leitura de todas as instancias disponiveis, nas duas convencoes de formato.

2. Reconstrucao das solucoes publicadas em .res. Cada visita do arquivo traz o
   instante de atendimento, a espera, o tempo a bordo e a carga; o avaliador
   recalcula esses valores a partir das coordenadas da instancia e cada um e
   confrontado com o do arquivo. Como o arquivo nao informa distancias, a
   conferencia da espera no no j equivale a conferir o tempo de percurso do no
   anterior ate j, de modo que a matriz de distancias e testada trecho a trecho.

3. Comparacao entre a agenda publicada e a produzida pela politica de inicio
   mais cedo do avaliador, para medir o que a politica deixa na mesa.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from darp import (BORDO, CEDO, OTIMO, Avaliador, Parametros, Solucao, ler_instancia,
                  ler_res, solucao_individual)
from darp.instancia import IDA, LIVRE, VOLTA

RAIZ = Path(__file__).resolve().parents[2] / "dados"
# Os .res gravam os instantes com 2 casas decimais, entao cada um carrega erro
# de arredondamento de ate 0,005. As grandezas conferidas sao diferencas entre
# dois instantes (espera e tempo a bordo), o que dobra o limite para 0,01;
# adota-se 0,02 por folga. Os totais somam dezenas dessas diferencas.
TOL = 2e-2
TOL_TOTAL = 5e-2
TOL_DIST = 5e-3  # a distancia nao depende de instantes arredondados

falhas = 0


def conferir(rotulo: str, obtido: float, esperado: float, tol: float = TOL) -> bool:
    global falhas
    ok = abs(obtido - esperado) <= tol
    if not ok:
        falhas += 1
    marca = "ok  " if ok else "FALHA"
    print(f"  [{marca}] {rotulo:<42} obtido={obtido:11.2f}  esperado={esperado:11.2f}"
          + ("" if ok else f"   dif={obtido - esperado:+.4f}"))
    return ok


def conferir_serie(rotulo: str, obtidos: dict, esperados: dict, tol: float = TOL) -> None:
    global falhas
    comuns = sorted(set(obtidos) & set(esperados))
    piores = sorted(comuns, key=lambda k: -abs(obtidos[k] - esperados[k]))
    erro_max = abs(obtidos[piores[0]] - esperados[piores[0]]) if piores else 0.0
    ok = erro_max <= tol
    if not ok:
        falhas += 1
    marca = "ok  " if ok else "FALHA"
    print(f"  [{marca}] {rotulo:<42} {len(comuns):3d} valores  erro maximo={erro_max:.4f}"
          + ("" if ok else f"  no no {piores[0]}"))
    if not ok:
        for k in piores[:5]:
            print(f"          no {k:>3}: obtido={obtidos[k]:.4f} esperado={esperados[k]:.4f}")


# ----------------------------------------------------------------------
print("=" * 78)
print("1. LEITURA DAS INSTANCIAS")
print("=" * 78)

instancias = {}
for pasta in ("bnc", "tabu"):
    for caminho in sorted((RAIZ / pasta).iterdir()):
        if caminho.suffix == ".res" or caminho.suffix == ".py":
            continue
        try:
            inst = ler_instancia(caminho)
        except Exception as erro:
            falhas += 1
            print(f"  [FALHA] {caminho.name}: {erro}")
            continue
        instancias[f"{pasta}/{caminho.name}"] = inst
        print(f"  [ok  ] {pasta}/{inst.resumo()}")


# ----------------------------------------------------------------------
print()
print("=" * 78)
print("2. RECONSTRUCAO DAS SOLUCOES PUBLICADAS")
print("=" * 78)

for nome in ("pr01", "pr07"):
    inst = instancias[f"tabu/{nome}"]
    pub = ler_res(RAIZ / "tabu" / f"{nome}.res")
    av = Avaliador(inst, Parametros(phi=1.0))

    print(f"\n--- {nome} ---")
    print(f"  rotas lidas: {len(pub.solucao.rotas)} (m={inst.m})   "
          f"nos lidos: {len(pub.B)} (2n={2 * inst.n})")

    erros = pub.solucao.conferir_estrutura(inst)
    if erros:
        falhas += 1
        print(f"  [FALHA] estrutura da solucao: {erros[:3]}")
    else:
        print("  [ok  ] estrutura: cobertura, pareamento e precedencia consistentes")

    res = av.avaliar_com_B(pub.solucao, pub.B, pub.partidas)

    print("\n  Conferencia contra os valores do arquivo:")
    conferir("distancia total", res.distancia, pub.distancia, TOL_DIST)
    conferir_serie("espera por no (valida a matriz de tempos)",
                   {n: a.espera[n] for a in res.agendas for n in a.espera},
                   pub.espera)
    conferir_serie("tempo a bordo por solicitacao",
                   {inst.entrega_de(i): v for a in res.agendas for i, v in a.R.items()},
                   {n: v for n, v in pub.bordo.items() if n > inst.n})
    conferir_serie("carga apos cada visita",
                   {n: a.carga[n] for a in res.agendas for n in a.carga},
                   pub.carga)
    if "espera" in pub.totais:
        conferir("espera total (linha de totais)", res.espera_bruta,
                 pub.totais["espera"], TOL_TOTAL)
    if "bordo" in pub.totais:
        conferir("tempo a bordo total (linha de totais)", res.tempo_bordo,
                 pub.totais["bordo"], TOL_TOTAL)

    print("\n  Objetivos desta solucao no modelo do projeto:")
    print(f"    f1  distancia percorrida .................. {res.f1:9.2f}")
    print(f"    f2  tempo perdido (passageiro-minuto) ..... {res.f2:9.2f}")
    print(f"        desvio de rota ........................ {res.f2_desvio:9.2f}")
    print(f"        espera no embarque .................... {res.f2_espera:9.2f}")
    soma_direta = sum(inst.t_direto(i) for i in inst.coletas)
    print(f"    soma dos percursos diretos ................ {soma_direta:9.2f}")
    print(f"    tempo a bordo total ....................... {res.tempo_bordo:9.2f}"
          f"   -> inflacao {res.tempo_bordo / soma_direta:.1f}x")
    if res.violacoes:
        print(f"    restricoes violadas: {len(res.violacoes)}")
        for v in res.violacoes[:3]:
            print(f"      {v}")
    else:
        print("    todas as restricoes satisfeitas")


# ----------------------------------------------------------------------
print()
print("=" * 78)
print("3. POLITICAS DE AGENDAMENTO x AGENDA PUBLICADA")
print("=" * 78)
print("A rota fixa a ordem das visitas, nao os instantes. Aplicar cada politica")
print("sobre a MESMA sequencia publicada isola o efeito do agendamento.")


def tipos_de_violacao(violacoes: list[str]) -> dict[str, int]:
    contagem: dict[str, int] = {}
    for v in violacoes:
        for chave in ("tempo a bordo", "janela", "capacidade", "duracao"):
            if chave in v:
                contagem[chave] = contagem.get(chave, 0) + 1
                break
    return contagem


for nome in ("pr01", "pr07"):
    inst = instancias[f"tabu/{nome}"]
    pub = ler_res(RAIZ / "tabu" / f"{nome}.res")
    av = Avaliador(inst, Parametros(phi=1.0))

    publicada = av.avaliar_com_B(pub.solucao, pub.B, pub.partidas)
    livre = Solucao(rotas=[r.copiar() for r in pub.solucao.rotas])  # sem partidas
    cedo = av.avaliar(livre, politica=CEDO)
    bordo = av.avaliar(livre, politica=BORDO)
    otimo = av.avaliar(livre, politica=OTIMO)

    print(f"\n--- {nome} ---")
    print(f"  {'':22} {'publicada':>12} {'CEDO':>12} {'BORDO':>12} {'OTIMO':>12}")
    for rotulo, campo in (("f1 (distancia)", "f1"), ("f2 total", "f2"),
                          ("  desvio", "f2_desvio"), ("  espera", "f2_espera"),
                          ("tempo a bordo", "tempo_bordo")):
        print(f"  {rotulo:22} {getattr(publicada, campo):12.2f} "
              f"{getattr(cedo, campo):12.2f} {getattr(bordo, campo):12.2f} "
              f"{getattr(otimo, campo):12.2f}")
    print(f"  {'violacoes':22} {len(publicada.violacoes):12d} "
          f"{len(cedo.violacoes):12d} {len(bordo.violacoes):12d} "
          f"{len(otimo.violacoes):12d}")
    print(f"  CEDO  viola: {tipos_de_violacao(cedo.violacoes)}")

    conferir(f"{nome}: f1 independe da agenda", otimo.f1, publicada.f1, TOL_DIST)
    for rotulo, res in (("BORDO", bordo), ("OTIMO", otimo)):
        conferir(f"{nome}: {rotulo} sem violacao de tempo a bordo",
                 tipos_de_violacao(res.violacoes).get("tempo a bordo", 0), 0, 0)
    conferir(f"{nome}: OTIMO alcanca f2 menor ou igual ao da agenda publicada",
             1.0 if otimo.f2 <= publicada.f2 + TOL else 0.0, 1.0, 0)


# ----------------------------------------------------------------------
print()
print("=" * 78)
print("4. CLASSIFICACAO DAS SOLICITACOES E HORARIO DESEJADO (rho)")
print("=" * 78)
inst = instancias["tabu/pr01"]
for tipo, titulo in ((IDA, "ida (janela na coleta)"),
                     (VOLTA, "volta (janela na entrega)"),
                     (LIVRE, "sem janela apertada")):
    ids = [i for i in inst.coletas if inst.tipo[i] == tipo]
    print(f"  {titulo:<28} {len(ids):2d} solicitacoes  {ids[:6]}{' ...' if len(ids) > 6 else ''}")

print("\n  Exemplos de rho inferido em pr01:")
for i in (1, 2, 13, 14):
    no = inst.nos[i]
    ent = inst.nos[inst.entrega_de(i)]
    print(f"    solicitacao {i:2d} ({inst.tipo[i]:5}): coleta [{no.e:6.1f},{no.l:6.1f}]  "
          f"entrega [{ent.e:6.1f},{ent.l:6.1f}]  t_direto={inst.t_direto(i):5.2f}  "
          f"rho={inst.rho[i]:7.2f}")


# ----------------------------------------------------------------------
print()
print("=" * 78)
print("5. EXTREMO SEM AGRUPAMENTO: A PROPOSICAO PREVE DESVIO NULO")
print("=" * 78)
print("Atendendo uma solicitacao por vez, nenhum no e visitado entre a coleta e")
print("a entrega, logo R_i = t_direto_i e a parcela de desvio deve ser zero.")
print("Com um veiculo por solicitacao a espera tambem zera, e f_2 = 0.")

inst = instancias["tabu/pr01"]
m_original = inst.m
av = Avaliador(inst, Parametros(phi=1.0))

print(f"\n  {'m':>4} {'f1':>9} {'f2':>9} {'desvio':>9} {'espera':>9} {'violacoes':>10}")
for m in (m_original, 2 * m_original, 4 * m_original, inst.n):
    inst.m = m
    res = av.avaliar(solucao_individual(inst), politica=OTIMO)
    print(f"  {m:4d} {res.f1:9.2f} {res.f2:9.2f} {res.f2_desvio:9.2f} "
          f"{res.f2_espera:9.2f} {len(res.violacoes):10d}")
    conferir(f"m={m}: desvio nulo sem agrupamento", res.f2_desvio, 0.0, 1e-6)

inst.m = inst.n
extremo_f2 = av.avaliar(solucao_individual(inst), politica=OTIMO)
conferir("m=n: f2 nulo (extremo de servico perfeito)", extremo_f2.f2, 0.0, 1e-6)

pub = ler_res(RAIZ / "tabu" / "pr01.res")
livre = Solucao(rotas=[r.copiar() for r in pub.solucao.rotas])
extremo_f1 = av.avaliar(livre, politica=OTIMO)
print(f"\n  Amplitude da fronteira em pr01:")
print(f"    extremo de emissao minima .... f1={extremo_f1.f1:8.2f}  f2={extremo_f1.f2:8.2f}")
print(f"    extremo de servico perfeito ... f1={extremo_f2.f1:8.2f}  f2={extremo_f2.f2:8.2f}")
print(f"    custo do servico perfeito ..... +{100 * (extremo_f2.f1 / extremo_f1.f1 - 1):.0f}% de emissao")
if extremo_f2.f1 <= extremo_f1.f1:
    falhas += 1
    print("  [FALHA] o extremo de servico perfeito deveria emitir mais")
else:
    print("  [ok  ] os extremos sao distintos e se opoem nos dois objetivos")

inst.m = m_original


# ----------------------------------------------------------------------
print()
print("=" * 78)
print(f"RESULTADO: {'TODAS AS CONFERENCIAS PASSARAM' if falhas == 0 else f'{falhas} FALHA(S)'}")
print("=" * 78)
sys.exit(1 if falhas else 0)
