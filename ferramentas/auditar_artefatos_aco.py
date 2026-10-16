"""QA dos artefatos JSON reabertos, sem confiar em metricas prontas."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'codigo'))
from darp import Parametros, Rota, Solucao, ler_instancia, verificar_solucao
from darp.avaliador import AgendaRota
from darp.instancia import reduzir
from darp.pareto import domina

for pasta in sys.argv[1:]:
    pasta = Path(pasta)
    arquivos = sorted((pasta / 'execucoes').glob('*.json'))
    total_unicas = total_completas = total_fronteira = 0
    for arquivo in arquivos:
        d = json.loads(arquivo.read_text(encoding='utf-8'))
        caso, r, config = d['caso'], d['resultado'], d['config']
        inst = ler_instancia(ROOT / caso['arquivo'])
        if caso['pedidos']:
            inst = reduzir(inst, caso['pedidos'], m=caso['m'] or len(caso['pedidos']))
        elif caso['m']:
            inst.m = caso['m']
        par = Parametros(**d['parametros'])
        assert r['consultas'] <= config['max_avaliacoes'], arquivo
        assert r['chamadas_pl'] <= r['consultas'], arquivo
        assert r['acertos_cache'] <= r['consultas'], arquivo
        if config['politica'] == 'bordo':
            assert r['chamadas_pl'] == 0, arquivo
        assert len(r['construcoes_completas']) + r['fracassadas'] + r['interrompidas'] == r['construcoes'], arquivo
        assert all(0 <= i < len(r['solucoes']) for i, peso in r['construcoes_completas']), arquivo
        for ponto in r['solucoes'] + r['fronteira']:
            sol = Solucao([Rota(ro['sequencia']) for ro in ponto['solucao']['rotas']])
            agendas = []
            for ag in ponto['agendas']:
                ag = dict(ag)
                for campo in ('B', 'espera', 'carga', 'R'):
                    ag[campo] = {int(k): v for k, v in ag[campo].items()}
                agendas.append(AgendaRota(**ag))
            ver = verificar_solucao(inst, sol, agendas, par)
            assert ver.viavel, (arquivo, ver.violacoes)
            assert abs(ver.f1 - ponto['f1']) < 1e-6 and abs(ver.f2 - ponto['f2']) < 1e-6, arquivo
            assert all(ag.politica_efetiva == config['politica'] for ag in agendas), arquivo
        f = [(p['f1'], p['f2']) for p in r['fronteira']]
        assert all(not domina(a, b) for i, a in enumerate(f) for j, b in enumerate(f) if i != j), arquivo
        total_unicas += len(r['solucoes'])
        total_completas += len(r['construcoes_completas'])
        total_fronteira += len(r['fronteira'])
    resultado = {'execucoes_auditadas': len(arquivos), 'solucoes_unicas_por_execucao': total_unicas,
                 'construcoes_completas': total_completas, 'pontos_de_fronteira': total_fronteira,
                 'falhas': 0}
    (pasta / 'auditoria_artefatos.json').write_text(json.dumps(resultado, indent=2), encoding='utf-8')
    print(pasta, resultado, flush=True)
