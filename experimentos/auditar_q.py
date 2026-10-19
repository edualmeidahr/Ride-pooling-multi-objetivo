"""Reconfere arquivos exportados usando somente a auditoria independente."""
import argparse
import json
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from comum.avaliador import AgendaRota
from comum.capacidade import ContextoCapacidades
from comum.pareto import cobertura
from comum.solucao import Rota, Solucao
from comum.validacao import verificar_solucao
from menu import preparar


def auditar(pastas):
    registros = []
    for pasta in pastas:
        for arquivo in sorted(Path(pasta).resolve().rglob('execucoes.json')):
            registro = json.loads(arquivo.read_text(encoding='utf-8'))
            if registro.get('versao_formato') != 2:
                continue
            config = arquivo.parent/'config_auditoria.json'
            # Configuração já preservada no resultado; não depende de configuração
            # de campanha temporária ou de usar outra semente de ruas.
            config.write_text(json.dumps(registro['config']), encoding='utf-8')
            c, inst, par, qs, ambiente, input_hash = preparar(str(config), registro['opcoes']['capacidades'])
            assert input_hash == registro['input_sha256'], (str(arquivo), 'demanda alterada')
            assert ambiente == registro['ambiente_emissoes'], (str(arquivo), 'ambiente alterado')
            ctx = ContextoCapacidades(inst, par, qs, c.get('modelo_emissoes'))
            quantidade = 0
            for execucao in registro['execucoes']:
                for ponto in execucao['pontos']:
                    q = ponto['Q']
                    i, av = ctx.obter(q)
                    sol = Solucao([Rota(seq) for seq in ponto['rotas']], Q=q)
                    agendas = [AgendaRota(sequencia=a['sequencia'], partida=a['partida'], retorno=a['retorno'],
                                          B={int(k):v for k,v in a['B'].items()}) for a in ponto['agendas']]
                    resultado = verificar_solucao(i, sol, agendas, av.par)
                    assert resultado.viavel, (str(arquivo), resultado.violacoes)
                    assert max(abs(resultado.f1-ponto['f1']),abs(resultado.f2-ponto['f2'])) <= 1e-6
                    quantidade += 1
            registros.append({'arquivo': str(arquivo.relative_to(RAIZ)), 'execucoes': len(registro['execucoes']),
                              'solucoes_auditadas': quantidade})
    return registros


def coberturas(pasta):
    arquivo = Path(pasta)/'comparacao.json'
    if not arquivo.exists():
        return []
    registros = json.loads(arquivo.read_text(encoding='utf-8'))['registros']
    resultado = []
    for r in registros:
        if r['capacidade'] != 'fixo':
            continue
        v = next(x for x in registros if x['pedidos']==r['pedidos'] and x['seed']==r['seed']
                 and x['metodo']==r['metodo'] and x['capacidade']=='variavel')
        resultado.append({'pedidos':r['pedidos'], 'seed':r['seed'], 'metodo':r['metodo'],
                          'C_fixo_variavel': cobertura(r['fronteira'],v['fronteira']),
                          'C_variavel_fixo': cobertura(v['fronteira'],r['fronteira'])})
    return resultado


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pastas', nargs='+')
    parser.add_argument('--saida', default='output/auditoria_q_variavel.json')
    args = parser.parse_args()
    resultados = auditar(args.pastas)
    res = {'campanhas': resultados, 'execucoes': sum(r['execucoes'] for r in resultados),
           'solucoes_auditadas': sum(r['solucoes_auditadas'] for r in resultados),
           'coberturas': [r for p in args.pastas for r in coberturas(p)]}
    destino = Path(args.saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(res,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f"{len(resultados)} campanhas; {res['execucoes']} execucoes; {res['solucoes_auditadas']} solucoes: auditoria OK")
