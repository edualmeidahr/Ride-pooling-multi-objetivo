"""Piloto reproduzível: orçamento total igual para Q fixo e variável.

Exemplo: python experimentos/comparar_q.py --orcamento 2000 --sementes 42 43 44
As referências são empíricas. Os limites nativos são elevados para que o
orçamento comum de consultas, incluindo cache, controle a comparação.
"""
import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from comum.pareto import filtrar, hipervolume, normalizar
from menu import executar
from implementacao3 import selecionar_algoritmos, METODOS_PADRAO, METODOS, GRUPOS


def comparar(orcamento=2000, sementes=(42, 43, 44), tamanhos=(12, 100), saida=None, algoritmos=METODOS_PADRAO):
    if type(orcamento) is not int or orcamento < 10:
        raise ValueError('orcamento deve ser inteiro >= 10')
    algoritmos = selecionar_algoritmos(algoritmos)
    destino = Path(saida).resolve() if saida else RAIZ / 'resultados/q_variavel_piloto'
    destino.mkdir(parents=True, exist_ok=True)
    registros = []
    for n in tamanhos:
        arquivo = 'comparacao_emissoes_q1_10.json' if n == 12 else 'comparacao_100_corridas.json'
        c = json.loads((RAIZ/'experimentos'/arquivo).read_text(encoding='utf-8'))
        c['algoritmos']['sa'].update(temp_inicial=3, temp_final=0.001, fator_resfriamento=0.999, iter_por_temp=30)
        c['algoritmos']['ga'].update(tamanho_populacao=8, geracoes=10000)
        c['algoritmos']['grasp'].update(max_iteracoes=10000, max_passos_busca_local=25)
        c['algoritmos']['aco'].update(formigas=6, iteracoes=10000, max_avaliacoes=10000000)
        c['algoritmos'].setdefault('ga_lib', {}).update(tamanho_populacao=8, geracoes=10000)
        c['algoritmos'].setdefault('sa_lib', {}).update(iteracoes=10000)
        c['algoritmos'].setdefault('pso_lib', {}).update(tamanho_populacao=8, iteracoes=10000)
        c['construcao'] = {'limite_pedidos_candidatos': 1, 'limite_posicoes_insercao': 8}
        config = destino/f'config_{n}.json'
        config.write_text(json.dumps(c, indent=2, ensure_ascii=False), encoding='utf-8')
        for seed in sementes:
            for modo in ('fixo', 'variavel'):
                pasta = destino/f'{n}_{modo}_seed{seed}'
                with (destino/f'{n}_{modo}_seed{seed}.log').open('w', encoding='utf-8') as log, redirect_stdout(log):
                    registro, _ = executar(str(config), 'metaheuristica', capacidade=modo, seed=seed,
                                          max_consultas_rotas=orcamento, saida=str(pasta), algoritmos=algoritmos)
                for metodo in algoritmos:
                    execucoes = [r for r in registro['execucoes'] if r['metodo'] == metodo]
                    pontos = filtrar([(p['f1'],p['f2'],p['Q']) for r in execucoes for p in r['pontos']])
                    contadores = {}
                    visitas = {}
                    for r in execucoes:
                        for k,v in r['estatisticas']['contadores'].items():
                            contadores[k] = contadores.get(k,0)+v
                        for k,v in r['estatisticas']['visitas_q'].items():
                            visitas[str(k)] = visitas.get(str(k),0)+v
                    consultas = sum(r['estatisticas']['consultas_orcamento'] for r in execucoes)
                    assert consultas <= orcamento, (metodo, modo, consultas)
                    registros.append({'pedidos': n, 'seed': seed, 'capacidade': modo, 'metodo': metodo,
                        'fronteira': pontos, 'tempo_s': sum(r['tempo_busca_s'] for r in execucoes),
                        'orcamento': orcamento, 'consultas': consultas, 'contadores': contadores,
                        'visitas_q': visitas, 'motivos_parada': [r['motivo_parada'] for r in execucoes]})
                print(f'{n} pedidos | {modo} | seed {seed}: concluido', flush=True)
    referencias = {}
    for n in tamanhos:
        referencia = filtrar([p[:2] for r in registros if r['pedidos']==n for p in r['fronteira']])
        referencias[str(n)] = {'tipo': 'empirica', 'pontos': referencia}
        for r in registros:
            if r['pedidos'] == n:
                r['hipervolume'] = hipervolume(normalizar(r['fronteira'], referencia), (1.1,1.1)) if referencia else 0
                r['pontos'] = len(r['fronteira'])
    resultado = {'orcamento_por_metodo': orcamento, 'sementes': list(sementes), 'algoritmos': list(algoritmos), 'referencias': referencias,
        'observacao': 'Piloto com limites curtos, construcao limitada e referencia empirica comum; sem ranking conclusivo.',
        'registros': registros}
    (destino/'comparacao.json').write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding='utf-8')
    texto = ['# Piloto: escolha conjunta de Q', '', resultado['observacao'], '',
        f'Orçamento total por método/semente/modalidade: {orcamento} consultas de rotas não vazias, incluindo cache. '
        'No modo fixo o orçamento é dividido igualmente entre dez Q; no variável é compartilhado. '
        'Todos os pontos exportados passam pela auditoria independente. HV usa os mesmos extremos empíricos '
        'por tamanho e ponto (1,1; 1,1) após normalização.', '',
        '| Pedidos | Semente | Método | Capacidade | Consultas | Pontos | HV | Tempo s |',
        '|---:|---:|---|---|---:|---:|---:|---:|']
    for r in registros:
        texto.append(f"| {r['pedidos']} | {r['seed']} | {r['metodo']} | {r['capacidade']} | {r['consultas']} | "
                     f"{r['pontos']} | {r['hipervolume']:.4f} | {r['tempo_s']:.2f} |")
    texto.extend(['', 'Uma fronteira vazia significa que nenhuma construção completa foi concluída dentro do orçamento. '
                  'Não demonstra inviabilidade. O tempo inclui o custo de busca e depende de aquecimento/caches da máquina. '
                  'O orçamento iguala consultas, não chamadas PL nem tempo; esses esforços são registrados separadamente.', ''])
    (destino/'RESUMO.md').write_text('\n'.join(texto), encoding='utf-8')
    return resultado


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--orcamento', type=int, default=2000)
    parser.add_argument('--sementes', nargs='+', type=int, default=[42,43,44])
    parser.add_argument('--tamanhos', nargs='+', type=int, choices=[12,100], default=[12,100])
    parser.add_argument('--saida')
    parser.add_argument('--algoritmos', nargs='+', choices=(*METODOS, *GRUPOS), default=list(METODOS_PADRAO))
    args = parser.parse_args()
    comparar(args.orcamento, args.sementes, args.tamanhos, args.saida, args.algoritmos)
