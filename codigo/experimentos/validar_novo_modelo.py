#!/usr/bin/env python3
"""Validacao do Novo Modelo de Rede: Nos Fixos, Matrizes de Custo e Requisicoes Mapeadas.

Baterias de testes de sanidade:
1. Menor caminho em grafo (Dijkstra) vs. Euclidiana (contorno de obstaculo).
2. Compartilhamento de nos fixos por multiplas requisicoes (distancia zero na mesma parada).
3. Avaliacao de rotas e politicas de agendamento (CEDO, BORDO, OTIMO via PL).
4. Persistencia e reconstrucao completa via JSON.
5. Compatibilidade com a fronteira exata de Pareto (exato.py).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from darp import (
    BORDO,
    CEDO,
    OTIMO,
    Avaliador,
    NoFixo,
    Parametros,
    Rede,
    Requisicao,
    Rota,
    Solucao,
    criar_instancia_rede,
    ler_instancia_json,
    salvar_instancia_json,
)
from darp.exato import fronteira_exata

falhas = 0


def conferir(rotulo: str, obtido: float, esperado: float, tol: float = 1e-4) -> bool:
    global falhas
    ok = abs(obtido - esperado) <= tol
    if not ok:
        falhas += 1
    marca = "ok  " if ok else "FALHA"
    print(f"  [{marca}] {rotulo:<50} obtido={obtido:9.2f}  esperado={esperado:9.2f}"
          + ("" if ok else f"   dif={obtido - esperado:+.4f}"))
    return ok


def conferir_booleano(rotulo: str, condicao: bool) -> bool:
    global falhas
    if not condicao:
        falhas += 1
    marca = "ok  " if condicao else "FALHA"
    print(f"  [{marca}] {rotulo}")
    return condicao


print("=" * 78)
print("1. TESTE DE MENOR CAMINHO EM GRAFO (DIJKSTRA) VS. EUCLIDIANA")
print("=" * 78)

# Cria rede com 5 nos fixos:
# 0: Deposito (0, 0)
# 1: Bairro Oeste (10, 0)
# 2: Ponte Norte (10, 10)
# 3: Ponte Sul (10, -10)
# 4: Bairro Leste (20, 0)
# Não ha conexao direta entre 1 e 4 (existe um rio/obstaculo no meio).
# O veiculo deve cruzar pela Ponte Norte (dist=15) ou Ponte Sul (dist=12).
nos_fixos = [
    NoFixo(id=0, x=0.0, y=0.0, nome="Deposito", s_embarque=0.0, s_desembarque=0.0),
    NoFixo(id=1, x=10.0, y=0.0, nome="Bairro Oeste", s_embarque=2.0, s_desembarque=1.0),
    NoFixo(id=2, x=10.0, y=10.0, nome="Ponte Norte", s_embarque=1.0, s_desembarque=1.0),
    NoFixo(id=3, x=10.0, y=-10.0, nome="Ponte Sul", s_embarque=1.0, s_desembarque=1.0),
    NoFixo(id=4, x=20.0, y=0.0, nome="Bairro Leste", s_embarque=2.0, s_desembarque=1.0),
]

arestas = [
    (0, 1, 10.0),  # Deposito <-> Oeste
    (1, 2, 10.0),  # Oeste <-> Ponte Norte
    (2, 4, 15.0),  # Ponte Norte <-> Leste (total via norte = 25)
    (1, 3, 10.0),  # Oeste <-> Ponte Sul
    (3, 4, 12.0),  # Ponte Sul <-> Leste (total via sul = 22)
    (4, 0, 20.0),  # Leste <-> Deposito retorno
]

rede = Rede.from_grafo(nos_fixos, arestas, direcionado=False)

# Distancia 1 -> 4 via grafo deve ser 10 + 12 = 22 (via Sul), enquanto euclidiana seria 10.
conferir("Menor caminho Oeste (1) -> Leste (4) via grafo", rede.dist(1, 4), 22.0)
conferir("Distancia do deposito (0) -> Leste (4) direto", rede.dist(0, 4), 20.0)
conferir("Distancia reflexiva 1 -> 1", rede.dist(1, 1), 0.0)

print()
print("=" * 78)
print("2. MULTIPLAS REQUISICOES COMPARTILHANDO O MESMO NO FIXO")
print("=" * 78)

# Requisicao 1: Oeste (1) -> Leste (4)
# Requisicao 2: Oeste (1) -> Ponte Norte (2)
# Requisicao 3: Ponte Sul (3) -> Leste (4)
reqs = [
    Requisicao(id=1, origem_id=1, destino_id=4, q=1, e_coleta=10.0, l_coleta=30.0,
               e_entrega=50.0, l_entrega=100.0),
    Requisicao(id=2, origem_id=1, destino_id=2, q=1, e_coleta=15.0, l_coleta=35.0,
               e_entrega=30.0, l_entrega=80.0),
    Requisicao(id=3, origem_id=3, destino_id=4, q=1, e_coleta=20.0, l_coleta=60.0,
               e_entrega=60.0, l_entrega=120.0),
]

inst = criar_instancia_rede(
    nome="instancia-teste-rede",
    rede=rede,
    requisicoes=reqs,
    deposito_origem_id=0,
    deposito_destino_id=0,
    m=1,
    T_max=300.0,
    Q=3,
    L_arquivo=90.0,
)

# Coletas: 1 (Req 1 no no fixo 1), 2 (Req 2 no no fixo 1), 3 (Req 3 no no fixo 3)
# Entregas: 4 (Req 1 no no fixo 4), 5 (Req 2 no no fixo 2), 6 (Req 3 no no fixo 4)
conferir("Distancia entre coletas 1 e 2 (mesma parada)", inst.dist(1, 2), 0.0)
conferir("Tempo de viagem entre coletas 1 e 2", inst.tempo(1, 2), 0.0)
conferir("Tempo de servico da coleta 1 (do NoFixo 1)", inst.nos[1].s, 2.0)
conferir("Tempo de servico da entrega 5 (do NoFixo 2)", inst.nos[5].s, 1.0)
conferir("Percurso direto t_direto(1) (1 -> 4)", inst.t_direto(1), 22.0)
conferir("Percurso direto t_direto(2) (1 -> 2)", inst.t_direto(2), 10.0)

print()
print("=" * 78)
print("3. AVALIACAO DE ROTAS E AGENDAMENTO (CEDO, BORDO, OTIMO)")
print("=" * 78)

# Rota valida: Deposito -> Coleta 1 e 2 (no 1) -> Entrega 2 (no 2) -> Coleta 3 (no 3) -> Entrega 1 e 3 (no 4) -> Deposito
# Sequencia de nos de atendimento: [1, 2, 5, 3, 4, 6]
rota = Rota([1, 2, 5, 3, 4, 6])
sol = Solucao(rotas=[rota])

erros_estruturais = sol.conferir_estrutura(inst)
conferir_booleano("Estrutura da solucao valida (sem violacoes)", len(erros_estruturais) == 0)

av = Avaliador(inst, Parametros(phi=1.0))
aval_otimo = av.avaliar(sol, politica=OTIMO)
aval_bordo = av.avaliar(sol, politica=BORDO)
aval_cedo = av.avaliar(sol, politica=CEDO)

print(f"  Politica OTIMO : {aval_otimo}")
print(f"  Politica BORDO : {aval_bordo}")
print(f"  Politica CEDO  : {aval_cedo}")

conferir_booleano("OTIMO gerou agenda viavel", aval_otimo.viavel)
conferir_booleano("BORDO gerou agenda viavel", aval_bordo.viavel)
conferir("f1 identico nas tres politicas (mesma rota)", aval_otimo.f1, aval_cedo.f1)
conferir_booleano("OTIMO alcanca f2 <= BORDO", aval_otimo.f2 <= aval_bordo.f2 + 1e-4)

# Distancia total percorrida esperada:
# Dep(0)->no1: 10 + no1->no1: 0 + no1->no2: 10 + no2->no3: 20 + no3->no4: 12 + no4->no4: 0 + no4->Dep(0): 20
# Total = 10 + 0 + 10 + 20 + 12 + 0 + 20 = 72
conferir("Distancia total da rota na rede em grafo", aval_otimo.distancia, 72.0)

print()
print("=" * 78)
print("4. SERIALIZACAO E DESSERIALIZACAO JSON")
print("=" * 78)

with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
    tmp_path = Path(tmp.name)

try:
    salvar_instancia_json(inst, tmp_path)
    conferir_booleano("Arquivo JSON gravado com sucesso", tmp_path.exists())

    inst_carregada = ler_instancia_json(tmp_path)
    conferir_booleano("Instancia recarregada possui rede", inst_carregada.rede is not None)
    conferir("Mesmo numero de nos fixos", len(inst_carregada.rede.nos_fixos), len(inst.rede.nos_fixos))
    conferir("Mesmo numero de requisicoes", inst_carregada.n, inst.n)
    conferir("Mesma distancia entre paradas compartilhadas", inst_carregada.dist(1, 2), 0.0)

    # Avaliacao sobre a instancia carregada deve bater com precisao de ponto flutuante
    av_carregado = Avaliador(inst_carregada, Parametros(phi=1.0))
    aval_rec = av_carregado.avaliar(sol, politica=OTIMO)
    conferir("f1 preservado apos carregar JSON", aval_rec.f1, aval_otimo.f1)
    conferir("f2 preservado apos carregar JSON", aval_rec.f2, aval_otimo.f2)
finally:
    if tmp_path.exists():
        tmp_path.unlink()

print()
print("=" * 78)
print("5. INTEGRACAO COM FRONTEIRA EXATA (PARETO / ENUMERACAO)")
print("=" * 78)

# Roda a enumeracao exata do modulo exato.py sobre a nova instancia em grafo
pontos_pareto = fronteira_exata(inst, av, politica=OTIMO)
print(f"  Pontos encontrados na fronteira exata: {len(pontos_pareto)}")
for i, (f1, f2, sol_p) in enumerate(pontos_pareto, 1):
    print(f"    Ponto {i}: f1={f1:7.2f} (emissao/distancia)  f2={f2:7.2f} (tempo perdido)")
    diag = sol_p.conferir_estrutura(inst)
    conferir_booleano(f"    Ponto {i} estrutura correta", len(diag) == 0)

conferir_booleano("Fronteira exata retornou ao menos uma solucao viavel", len(pontos_pareto) > 0)

print()
print("=" * 78)
if falhas == 0:
    print("RESULTADO: TODOS OS TESTES DO NOVO MODELO PASSARAM COM SUCESSO!")
else:
    print(f"RESULTADO: {falhas} TESTES FALHARAM!")
print("=" * 78)
