#!/usr/bin/env python3
"""ACO propria x construtivo, BORDO x OTIMO, gabaritos e campanhas.

Exemplos e protocolo completos em relatorio/ACO.md. Importar nao executa buscas.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
from datetime import datetime, timezone
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from darp import (BORDO, OTIMO, Avaliador, ConfigACO, Parametros, Rota, Solucao,
                  ler_instancia, resolver_aco, verificar_solucao)
from darp import pareto
from darp.avaliador import RotaTemporalmenteInviavel
from darp.exato import fronteira_exata
from darp.instancia import reduzir

RAIZ = Path(__file__).resolve().parents[2]
RECORTES = {'volta': [1, 2, 3, 4, 5], 'ida': [13, 14, 15, 16, 17],
            'misto': [1, 2, 13, 14, 15]}


def gravar_json(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix('.tmp')
    temporario.write_text(json.dumps(dados, ensure_ascii=False, allow_nan=False,
                                     separators=(',', ':')), encoding='utf-8')
    temporario.replace(caminho)


def gravar_csv(caminho, linhas):
    if not linhas:
        return
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)


def ambiente():
    versoes = {}
    for nome in ('numpy', 'scipy', 'matplotlib', 'gurobipy'):
        try:
            versoes[nome] = importlib.metadata.version(nome)
        except importlib.metadata.PackageNotFoundError:
            versoes[nome] = None
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=RAIZ, capture_output=True,
                            text=True, check=True).stdout.strip()
    fontes = sorted((RAIZ / 'codigo').rglob('*.py'))
    hashes = {str(p.relative_to(RAIZ)): hashlib.sha256(p.read_bytes()).hexdigest() for p in fontes}
    return {'python': platform.python_version(), 'plataforma': platform.platform(),
            'versoes': versoes, 'commit': commit, 'sha256_fontes': hashes,
            'utc': datetime.now(timezone.utc).isoformat()}


def carregar(caso):
    inst = ler_instancia(RAIZ / caso['arquivo'])
    if caso['pedidos']:
        inst = reduzir(inst, caso['pedidos'], m=caso['m'] or len(caso['pedidos']))
    elif caso['m'] is not None:
        inst.m = caso['m']
    return inst


def serializar(res):
    # Cada sequencia completa distinta e salva uma vez; o indice de ocorrencias
    # preserva TODAS as construcoes, inclusive duplicadas e dominadas.
    unicas, ids, ocorrencias = [], {}, []
    for ponto in res.solucoes:
        chave = tuple(tuple(r.sequencia) for r in ponto.solucao.rotas)
        if chave not in ids:
            ids[chave] = len(unicas)
            unicas.append(asdict(ponto))
        ocorrencias.append([ids[chave], ponto.peso])
    dados = {k: v for k, v in vars(res).items()
             if k not in ('solucoes', 'fronteira', 'feromonios')}
    dados.update(solucoes=unicas, construcoes_completas=ocorrencias,
                 fronteira=[asdict(p) for p in res.fronteira],
                 feromonios=res.feromonios)
    return dados


def executar_tarefa(tarefa):
    caminho = Path(tarefa['saida'])
    # Retomada so aceita a mesma entrada, configuracao e hash das fontes.
    if caminho.exists():
        anterior = json.loads(caminho.read_text(encoding='utf-8'))
        if anterior.get('assinatura') == tarefa['assinatura']:
            return str(caminho), True
        raise ValueError(f"saida existente de outro experimento: {caminho}")
    inst = carregar(tarefa['caso'])
    config = ConfigACO(**tarefa['config'])
    res = resolver_aco(inst, Parametros(), config)
    dados = {'assinatura': tarefa['assinatura'], 'caso': tarefa['caso'],
             'config': tarefa['config'], 'modalidade': tarefa['modalidade'],
             'processos_concorrentes': tarefa['jobs'],
             'parametros': asdict(Parametros(politica=config.politica,
                                            exigir_otimo=config.politica == OTIMO)),
             'resultado': serializar(res)}
    gravar_json(caminho, dados)
    return str(caminho), False


def objetivos(pontos):
    return [(p['f1'], p['f2']) for p in pontos]


def conferir_frente(frente, referencia=None):
    for i, p in enumerate(frente):
        if any(pareto.domina(q, p) for j, q in enumerate(frente) if i != j):
            raise AssertionError('dominancia interna na fronteira')
        if referencia and any(pareto.domina(p, q, tol=1e-6) for q in referencia):
            raise AssertionError('solucao domina gabarito com os mesmos parametros')


def gabaritos(caso, pasta, exigir_mip=False):
    inst = carregar(caso)
    if inst.n > 5:
        return None
    caminho = pasta / f"{caso['nome']}.json"
    # Calculados novamente em cada campanha: custos fora da busca registrados.
    inicio = perf_counter()
    av = Avaliador(inst, Parametros(exigir_otimo=True))
    dados = {}
    for politica in (BORDO, OTIMO):
        frente = fronteira_exata(inst, av, politica=politica)
        dados[politica] = [(f1, f2) for f1, f2, _ in frente]
    if exigir_mip:
        from darp.mip import fronteira_epsilon
        mip = fronteira_epsilon(inst)
        pontos = sorted((p.f1, p.f2) for p in mip)
        if len(pontos) != len(dados[OTIMO]) or any(
                max(abs(x - y) for x, y in zip(a, b)) > 1e-3
                for a, b in zip(pontos, dados[OTIMO])):
            raise AssertionError('MIP certificado diverge da enumeracao')
        dados['mip'] = [{'f1': p.f1, 'f2': p.f2, 'status': p.status, 'gap': p.gap} for p in mip]
        # Confere tambem os horarios do solver por uma terceira implementacao.
        for ponto in mip:
            externo = av.avaliar_com_B(ponto.solucao, ponto.B, ponto.partidas)
            check = verificar_solucao(inst, ponto.solucao, externo.agendas, av.par)
            if not check.viavel or max(abs(check.f1 - ponto.f1), abs(check.f2 - ponto.f2)) > 1e-3:
                raise AssertionError('agenda do MIP falhou na auditoria independente')
    dados['tempo'] = perf_counter() - inicio
    dados['caso'] = caso
    gravar_json(caminho, dados)
    return dados


def normalizador(base):
    # Limites definidos sobre TODOS os resultados e os gabaritos do mesmo caso.
    mins = [min(p[j] for p in base) for j in (0, 1)] if base else [0., 0.]
    maxs = [max(p[j] for p in base) for j in (0, 1)] if base else [1., 1.]
    amps = [maxs[j] - mins[j] or 1. for j in (0, 1)]
    def normalizar(frente):
        return [tuple((p[j] - mins[j]) / amps[j] for j in (0, 1)) for p in frente]
    return normalizar, {'min': mins, 'max': maxs, 'referencia_hv': [1.1, 1.1]}


def consolidar(arquivos, casos, pasta, refs):
    execucoes = [json.loads(Path(p).read_text(encoding='utf-8')) for p in arquivos]
    metricas, coberturas, limites = [], [], {}
    for caso in casos:
        grupo = [e for e in execucoes if e['caso']['nome'] == caso['nome']]
        ref = refs.get(caso['nome'])
        base = [p for e in grupo for p in objetivos(e['resultado']['solucoes'])]
        if ref:
            base += ref[BORDO] + ref[OTIMO]
        normalizar, limites[caso['nome']] = normalizador(base)
        for e in grupo:
            r, config = e['resultado'], e['config']
            frente = objetivos(r['fronteira'])
            referencia = ref[config['politica']] if ref else None
            conferir_frente(frente, referencia)
            hv = pareto.hipervolume(normalizar(frente), (1.1, 1.1))
            hv_ref = pareto.hipervolume(normalizar(referencia), (1.1, 1.1)) if referencia else None
            recuperados = sum(any(max(abs(x-y) for x, y in zip(p, q)) <= 1e-3
                                  for p in frente) for q in referencia) if referencia else None
            completas = len(r['construcoes_completas'])
            metricas.append({'caso': caso['nome'], 'modalidade': e['modalidade'],
                'metodo': 'aco' if config['aprender'] else 'construtivo',
                'politica': config['politica'], 'seed': config['seed'],
                'hv': hv, 'hv_relativo': hv / hv_ref if hv_ref else '',
                'recuperacao': recuperados / len(referencia) if referencia else '',
                'cardinalidade': len(frente), 'tempo': r['tempo'], 'consultas': r['consultas'],
                'chamadas_pl': r['chamadas_pl'], 'acertos_cache': r['acertos_cache'],
                'rejeicoes_necessarias': r['rejeicoes_necessarias'],
                'construcoes': r['construcoes'], 'completas': completas,
                'fracassadas': r['fracassadas'], 'interrompidas': r['interrompidas'],
                'taxa_sucesso_construcao': completas / r['construcoes'],
                'taxa_viabilidade_saidas': 1.0 if completas else '',
                'motivo_parada': r['motivo_parada']})
        for i, a in enumerate(grupo):
            for b in grupo[i+1:]:
                if a['config']['seed'] != b['config']['seed'] or a['modalidade'] != b['modalidade']:
                    continue
                fa, fb = objetivos(a['resultado']['fronteira']), objetivos(b['resultado']['fronteira'])
                nome = lambda e: ('aco' if e['config']['aprender'] else 'construtivo') + '-' + e['config']['politica']
                coberturas.append({'caso': caso['nome'], 'modalidade': a['modalidade'],
                    'seed': a['config']['seed'], 'A': nome(a), 'B': nome(b),
                    'C_estrita_A_B': pareto.cobertura(fa, fb),
                    'C_estrita_B_A': pareto.cobertura(fb, fa)})
    gravar_csv(pasta / 'metricas.csv', metricas)
    gravar_csv(pasta / 'cobertura.csv', coberturas)
    gravar_json(pasta / 'normalizacao.json', limites)
    resumos = []
    chaves = sorted({(m['caso'], m['modalidade'], m['metodo'], m['politica']) for m in metricas})
    for chave in chaves:
        grupo = [m for m in metricas if tuple(m[k] for k in ('caso', 'modalidade', 'metodo', 'politica')) == chave]
        linha = dict(zip(('caso', 'modalidade', 'metodo', 'politica'), chave))
        linha['execucoes'] = len(grupo)
        for campo in ('hv', 'tempo', 'cardinalidade', 'taxa_sucesso_construcao'):
            vs = sorted(m[campo] for m in grupo)
            q = statistics.quantiles(vs, n=4, method='inclusive') if len(vs) > 1 else vs * 3
            linha[campo + '_mediana'] = statistics.median(vs)
            linha[campo + '_q1'], linha[campo + '_q3'] = q[0], q[2]
        resumos.append(linha)
    gravar_csv(pasta / 'resumo.csv', resumos)
    graficos(execucoes, casos, pasta, limites, metricas)


def graficos(execucoes, casos, pasta, limites, metricas):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for caso in casos:
        grupo = [e for e in execucoes if e['caso']['nome'] == caso['nome']]
        for modalidade in sorted({e['modalidade'] for e in grupo}):
            fig, axs = plt.subplots(1, 2, figsize=(11, 4))
            for politica, cor in ((BORDO, '#c85135'), (OTIMO, '#147787')):
                for aprender, marca in ((True, 'o'), (False, 'x')):
                    gs = [e for e in grupo if e['config']['politica'] == politica
                          and e['config']['aprender'] == aprender and e['modalidade'] == modalidade]
                    pontos = pareto.filtrar([p for e in gs for p in objetivos(e['resultado']['fronteira'])])
                    nome = ('ACO-' if aprender else 'Construtivo-') + politica.upper()
                    if pontos:
                        axs[0].scatter([p[0] for p in pontos], [p[1] for p in pontos],
                                       label=nome, s=22, marker=marca, color=cor)
                    valores = [m['hv'] for m in metricas if m['caso'] == caso['nome']
                               and m['modalidade'] == modalidade and m['politica'] == politica
                               and m['metodo'] == ('aco' if aprender else 'construtivo')]
                    if valores:
                        pos = (0 if politica == BORDO else 2) + (1 if aprender else 2)
                        axs[1].boxplot([valores], positions=[pos], widths=.6)
            axs[0].set(xlabel='f1: distancia (phi=1)', ylabel='f2: passageiro-minuto')
            if axs[0].collections:
                axs[0].legend(fontsize=7)
            axs[1].set(xticks=[1, 2, 3, 4], xticklabels=['ACO B', 'Base B', 'ACO O', 'Base O'], ylabel='Hipervolume normalizado')
            for ax in axs:
                ax.grid(alpha=.2)
            fig.suptitle(caso['nome'] + ' | ' + modalidade + ' | uniao empirica por metodo')
            fig.tight_layout()
            fig.savefig(pasta / f"{caso['nome']}_{modalidade}.png", dpi=150)
            plt.close(fig)
        # Curvas de mediana por iteracao, com todos os metodos na mesma escala.
        normalizar, _ = normalizador([tuple(v) for e in grupo for h in e['resultado']['historico'] for v in h['fronteira']]
                                    + [tuple(limites[caso['nome']]['min']), tuple(limites[caso['nome']]['max'])])
        fig, ax = plt.subplots(figsize=(7, 4))
        for politica in (BORDO, OTIMO):
            for aprender in (True, False):
                gs = [e for e in grupo if e['config']['politica'] == politica and e['config']['aprender'] == aprender
                      and e['modalidade'] == 'avaliacoes']
                if not gs:
                    continue
                # Checkpoints comuns em consultas; carrega o ultimo arquivo conhecido.
                limite = min(e['config']['max_avaliacoes'] for e in gs)
                xs = [limite * i / 20 for i in range(21)]
                ys = []
                for x in xs:
                    hvs = []
                    for e in gs:
                        hs = [h for h in e['resultado']['historico'] if h['consultas'] <= x]
                        frente = hs[-1]['fronteira'] if hs else []
                        hvs.append(pareto.hipervolume(normalizar(frente), (1.1, 1.1)))
                    ys.append(statistics.median(hvs))
                ax.plot(xs, ys, label=('ACO-' if aprender else 'Base-') + politica)
        ax.set(xlabel='Consultas de rota', ylabel='Mediana do hipervolume', title=caso['nome'])
        if ax.lines:
            ax.legend()
        ax.grid(alpha=.2)
        fig.tight_layout()
        fig.savefig(pasta / f"{caso['nome']}_convergencia.png", dpi=150)
        plt.close(fig)


def reavaliar(arquivos, casos, pasta):
    linhas = []
    for caso in casos:
        inst = carregar(caso)
        unicas = {}
        for arquivo in arquivos:
            e = json.loads(Path(arquivo).read_text(encoding='utf-8'))
            if e['caso']['nome'] != caso['nome']:
                continue
            for p in e['resultado']['solucoes']:
                chave = tuple(sorted(tuple(r['sequencia']) for r in p['solucao']['rotas']))
                unicas[chave] = None
        avs = {p: Avaliador(inst, Parametros(politica=p, exigir_otimo=p == OTIMO)) for p in (BORDO, OTIMO)}
        caches = {p: {} for p in avs}
        inicio = perf_counter()
        for sid, chave in enumerate(sorted(unicas)):
            sol = Solucao([Rota(list(seq)) for seq in chave])
            for politica, av in avs.items():
                agendas, erros = [], []
                for seq in chave:
                    if seq not in caches[politica]:
                        try:
                            caches[politica][seq] = av.avaliar_rota(Rota(list(seq)))
                        except RotaTemporalmenteInviavel:
                            caches[politica][seq] = None, ['PL inviavel']
                    ag, violacoes = caches[politica][seq]
                    if violacoes:
                        erros += violacoes
                    else:
                        agendas.append(ag)
                check = verificar_solucao(inst, sol, agendas, av.par) if not erros else None
                if check is not None and not check.viavel:
                    raise AssertionError(check.violacoes)
                linhas.append({'caso': caso['nome'], 'solucao': sid, 'politica': politica,
                    'viavel': not erros, 'f1': check.f1 if check else '', 'f2': check.f2 if check else '',
                    'rotas': json.dumps(chave), 'diagnostico': '; '.join(erros)})
        # Mesmo conjunto bruto, inclusive dominadas: refiltra DEPOIS de reagendar.
        novas_frentes = {}
        for politica in (BORDO, OTIMO):
            novas_frentes[politica] = pareto.filtrar([(r['f1'], r['f2']) for r in linhas
                if r['caso'] == caso['nome'] and r['politica'] == politica and r['viavel']])
        gravar_json(pasta / f"{caso['nome']}_reavaliacao.json", {
            'solucoes_unicas': len(unicas), 'fronteiras': novas_frentes,
            'tempo_fora_da_busca': perf_counter() - inicio,
            'chamadas_pl_fora_da_busca': avs[OTIMO].chamadas_pl})
    gravar_csv(pasta / 'reavaliacao.csv', linhas)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=['unica', 'validacao', 'piloto', 'campanha'], default='unica')
    parser.add_argument('--instancia', default='dados/tabu/pr01')
    parser.add_argument('--pedidos', type=int, nargs='+')
    parser.add_argument('--veiculos', type=int)
    parser.add_argument('--politica', choices=[BORDO, OTIMO, 'ambas'], default='ambas')
    parser.add_argument('--metodo', choices=['aco', 'construtivo', 'ambos'], default='ambos')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--sementes', type=int, nargs='+')
    parser.add_argument('--formigas', type=int, default=20)
    parser.add_argument('--iteracoes', type=int, default=100)
    parser.add_argument('--orcamento', type=int, default=200_000)
    parser.add_argument('--modalidade', choices=['avaliacoes', 'tempo', 'ambas'], default='avaliacoes')
    parser.add_argument('--segundos', type=float, default=60.)
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--saida', type=Path, default=RAIZ / 'resultados/aco')
    parser.add_argument('--mip', action='store_true', help='confere referencias pequenas com MIP certificado')
    parser.add_argument('--sem-reavaliacao', action='store_true', help='apenas adia a auditoria cruzada de horarios')
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error('--jobs deve ser positivo')
    if args.suite == 'unica':
        relativo = Path(args.instancia)
        if relativo.is_absolute():
            relativo = relativo.relative_to(RAIZ)
        nome = relativo.stem + ('-r' + '-'.join(map(str, args.pedidos)) if args.pedidos else '')
        casos = [{'nome': nome, 'arquivo': str(relativo), 'pedidos': args.pedidos, 'm': args.veiculos}]
    else:
        casos = [{'nome': 'pr01-' + nome, 'arquivo': 'dados/tabu/pr01', 'pedidos': pedidos, 'm': 5}
                 for nome, pedidos in RECORTES.items()]
        if args.suite in ('piloto', 'campanha'):
            casos += [{'nome': Path(p).name, 'arquivo': p, 'pedidos': None, 'm': None}
                      for p in ('dados/bnc/a2-16', 'dados/bnc/b2-16', 'dados/tabu/pr01')]
    seeds = args.sementes if args.sementes is not None else (
        list(range(30 if args.suite == 'campanha' else 5)) if args.suite != 'unica' else [args.seed])
    if len(seeds) != len(set(seeds)):
        parser.error('sementes repetidas')
    politicas = (BORDO, OTIMO) if args.politica == 'ambas' else (args.politica,)
    metodos = (True, False) if args.metodo == 'ambos' else (args.metodo == 'aco',)
    modos = ('avaliacoes', 'tempo') if args.modalidade == 'ambas' else (args.modalidade,)
    pasta = args.saida.resolve()
    pasta.mkdir(parents=True, exist_ok=True)
    meta = ambiente()
    tarefas = []
    for caso in casos:
        for modo in modos:
            for politica in politicas:
                for aprender in metodos:
                    for seed in seeds:
                        config = ConfigACO(politica=politica, seed=seed, formigas=args.formigas,
                            iteracoes=args.iteracoes if modo == 'avaliacoes' else 10**9,
                            max_avaliacoes=args.orcamento if modo == 'avaliacoes' else 10**12,
                            limite_segundos=args.segundos if modo == 'tempo' else None, aprender=aprender)
                        entrada = {'caso': caso, 'config': asdict(config), 'modalidade': modo,
                                   'fontes': meta['sha256_fontes'],
                                   'versoes': meta['versoes'], 'python': meta['python'],
                                   'jobs': args.jobs,
                                   'dados': hashlib.sha256((RAIZ / caso['arquivo']).read_bytes()).hexdigest()}
                        assinatura = hashlib.sha256(json.dumps(entrada, sort_keys=True).encode()).hexdigest()
                        nome = f"{caso['nome']}_{modo}_{'aco' if aprender else 'base'}_{politica}_{seed:02d}.json"
                        tarefas.append({'caso': caso, 'config': asdict(config), 'modalidade': modo,
                                        'jobs': args.jobs, 'assinatura': assinatura,
                                        'saida': str(pasta / 'execucoes' / nome)})
    # Distribui tratamentos/casos ao longo da campanha para reduzir o efeito
    # da ordem e da carga do computador; nao altera o RNG de cada algoritmo.
    random.Random(0).shuffle(tarefas)
    meta.update(casos=casos, sementes=seeds, jobs=args.jobs, tarefas=len(tarefas),
                cobertura='estrita', argumentos={k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()})
    gravar_json(pasta / 'manifesto.json', meta)
    for nome in meta['sha256_fontes']:
        destino = pasta / 'fontes' / nome
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes((RAIZ / nome).read_bytes())
    arquivos = []
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        pendentes = [pool.submit(executar_tarefa, t) for t in tarefas]
        for futuro in as_completed(pendentes):
            caminho, retomado = futuro.result()
            arquivos.append(caminho)
            print(f"[{len(arquivos)}/{len(tarefas)}] {'retomado' if retomado else 'feito'} {Path(caminho).name}", flush=True)
    arquivos.sort()
    if meta['sha256_fontes'] != ambiente()['sha256_fontes']:
        raise RuntimeError('Fontes alteradas durante a execucao; dados exploratorios preservados, repetir a campanha.')
    refs = {c['nome']: gabaritos(c, pasta / 'referencias', args.mip) for c in casos}
    consolidar(arquivos, casos, pasta, refs)
    if not args.sem_reavaliacao:
        reavaliar(arquivos, casos, pasta)
    print(f"Concluido: {pasta}", flush=True)


if __name__ == '__main__':
    main()
