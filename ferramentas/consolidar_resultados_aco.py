"""Relatorio derivado dos CSVs e auditorias realmente produzidos."""
import csv
import importlib.util
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
fonte = ROOT / 'codigo/experimentos/fase3_aco.py'
spec = importlib.util.spec_from_file_location('fase3', fonte)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

campanha = ROOT / 'resultados/aco/campanha'
tempo = ROOT / 'resultados/aco/tempo_pr01'
saida = ROOT / 'resultados/aco/comparacao'
saida.mkdir(parents=True, exist_ok=True)
meta = json.loads((campanha / 'manifesto.json').read_text(encoding='utf-8'))
arquivos = sorted((campanha / 'execucoes').glob('*.json'))
assert len(arquivos) == 720
temporais = sorted((tempo / 'execucoes').glob('*.json'))
assert len(temporais) == 20
arquivos += temporais
casos = meta['casos']
refs = {}
for caso in casos:
    p = campanha / 'referencias' / (caso['nome'] + '.json')
    refs[caso['nome']] = json.loads(p.read_text(encoding='utf-8')) if p.exists() else None
mod.consolidar([str(p) for p in arquivos], casos, saida, refs)
mod.gravar_json(saida / 'origem.json', {'campanha': str(campanha.relative_to(ROOT)),
    'tempo': str(tempo.relative_to(ROOT)), 'execucoes': len(arquivos),
    'observacao': 'Normalizacao conjunta por caso; 30 sementes por avaliacoes, 5 por tempo em pr01.'})

with (saida / 'resumo.csv').open(encoding='utf-8') as f:
    resumo = list(csv.DictReader(f))
with (saida / 'metricas.csv').open(encoding='utf-8') as f:
    metricas = list(csv.DictReader(f))
auditorias = {nome: json.loads((ROOT / 'resultados/aco' / nome / 'auditoria_artefatos.json').read_text())
              for nome in ('piloto', 'campanha', 'tempo_pr01')}

def fmt(x, casas=4):
    return f'{float(x):.{casas}f}'.replace('.', ',')

linhas = ['# Resultados executados da ACO própria', '',
    '## Escopo efetivamente executado', '',
    '- **Piloto:** 120 execuções; cinco sementes, seis casos e quatro tratamentos.',
    '- **Campanha por avaliações:** 720 execuções; sementes 0 a 29 em seis casos e quatro tratamentos. Parada em 100 iterações ou 200 mil consultas.',
    '- **Comparação adicional por tempo:** 20 execuções de pr01; sementes 0 a 4, quatro tratamentos e 60 segundos de busca por execução. Não é uma campanha temporal de 30 sementes em todas as instâncias.',
    '- **Verificações:** 26 testes unittest aprovados, regressões publicadas preservadas, gabaritos por enumeração/MIP e auditoria independente dos JSONs reabertos.',
    '',
    'Os tratamentos são ACO-BORDO, construtivo-BORDO, ACO-OTIMO e construtivo-OTIMO. O construtivo conserva atratividade, roleta e pesos, mas mantém feromônios em 1. O piloto usou quatro processos; as campanhas de avaliações e tempo usaram oito. Não comparar diretamente os tempos do piloto com os das campanhas.',
    '',
    '## Referências pequenas', '',
    '| Recorte | Pedidos | Pontos com OTIMO | Menor recuperação observada, ACO-OTIMO |',
    '|---|---|---:|---:|']
for nome, ids in [('pr01-volta','1,2,3,4,5'),('pr01-ida','13,14,15,16,17'),('pr01-misto','1,2,13,14,15')]:
    rs = [m for m in metricas if m['caso']==nome and m['metodo']=='aco' and m['politica']=='otimo']
    linhas.append(f"| {nome} | {ids} | {len(refs[nome]['otimo'])} | {fmt(100*min(float(r['recuperacao']) for r in rs),1)}% |")
linhas += ['', 'A enumeração e o MIP corrigido coincidem com tolerância 1e-3 nos três recortes. Todas as agendas MIP foram auditadas independentemente. No recorte de volta, ACO-OTIMO recuperou três dos quatro pontos nas sementes 10 e 17 (HV relativo 0,9932 e 0,9895); ACO-BORDO recuperou oito dos dez pontos na semente 19. O piloto de cinco sementes não mostrou essas perdas. Isso reforça a necessidade das repetições e não viola a correção das soluções. A cobertura de igualdade continua sendo estrita: frentes iguais têm C(A,A)=0, enquanto recuperação/HV relativo reconhecem a coincidência.',
    '', '## Qualidade na campanha por avaliações', '',
    'Hipervolume mediano, com normalização comum por caso. A escala abaixo usa a união dos dados da campanha e da comparação temporal; em pr01, pode diferir da escala do CSV isolado de cada pasta. Maior é melhor. Não comparar valores absolutos de casos diferentes.', '',
    '| Caso | ACO-BORDO | Construtivo-BORDO | ACO-OTIMO | Construtivo-OTIMO |',
    '|---|---:|---:|---:|---:|']
for caso in sorted({r['caso'] for r in resumo}):
    vals = []
    for metodo, politica in [('aco','bordo'),('construtivo','bordo'),('aco','otimo'),('construtivo','otimo')]:
        r = next(r for r in resumo if r['caso']==caso and r['modalidade']=='avaliacoes' and r['metodo']==metodo and r['politica']==politica)
        vals.append(fmt(r['hv_mediana']))
    linhas.append('| '+caso+' | '+' | '.join(vals)+' |')

linhas += ['', '## Custo e comparação adicional por tempo em pr01', '',
    '| Regime | Método | Horários | Sementes | HV mediano | Tempo mediano (s) |',
    '|---|---|---|---:|---:|---:|']
for r in resumo:
    if r['caso']=='pr01':
        linhas.append(f"| {r['modalidade']} | {r['metodo']} | {r['politica']} | {r['execucoes']} | {fmt(r['hv_mediana'])} | {fmt(r['tempo_mediana'],2)} |")
linhas += ['', 'O limite de tempo é cooperativo, conferido antes de cada consulta: a consulta em andamento e a conclusão da construção podem produzir pequeno excedente. Exportação, métricas, gabaritos e reagendamento cruzado são medidos fora da busca.',
    '', 'Em pr01, o regime por avaliações favorece a mediana de ACO-OTIMO; com 60 segundos iguais, a mediana favorece ACO-BORDO nesta amostra. O custo do PL muda o compromisso entre avaliações realizadas e qualidade. A comparação temporal usa cinco sementes e não demonstra superioridade geral de um agendador.',
    '', '## Auditoria dos artefatos reabertos', '',
    '| Etapa | Execuções | Construções completas | Soluções distintas por execução | Pontos de fronteira | Falhas |',
    '|---|---:|---:|---:|---:|---:|']
for nome, a in auditorias.items():
    linhas.append(f"| {nome} | {a['execucoes_auditadas']} | {a['construcoes_completas']} | {a['solucoes_unicas_por_execucao']} | {a['pontos_de_fronteira']} | {a['falhas']} |")
linhas += ['', 'O contador de soluções distintas acima é somado por execução; a mesma solução encontrada em sementes diferentes aparece mais de uma vez. Agendas, objetivos, pareamento, capacidade, janelas, duração, políticas efetivas e orçamento foram conferidos nos JSONs, sem depender dos CSVs consolidados.',
    '', '## O que estes resultados permitem concluir', '',
    'A implementação manual produz soluções válidas, é reproduzível no regime por avaliações e recupera referências pequenas. O ganho de OTIMO pode ser maior que o ganho do reforço por feromônios; BORDO e OTIMO também podem aceitar conjuntos diferentes de rotas. Os CSVs de reagendamento usam a mesma união bruta de sequências para isolar esse efeito.',
    '', 'Comparar ACO com o construtivo dentro do mesmo caso, política e regime. As medianas não são prova de superioridade universal: não se realizou teste de significância, ajuste extensivo ou avaliação de carros/vans nesta etapa. O experimento temporal é complementar e limitado a pr01 com cinco sementes. Nas instâncias completas, a referência é empírica; não há certificado de ótimo global.',
    '', '## Arquivos para conferir e reproduzir', '',
    '- [Descrição, pseudocódigo e comandos](ACO.md).',
    '- [Métricas com escala conjunta](../resultados/aco/comparacao/metricas.csv).',
    '- [Medianas e quartis](../resultados/aco/comparacao/resumo.csv).',
    '- [Cobertura estrita nos dois sentidos](../resultados/aco/comparacao/cobertura.csv).',
    '- [Piloto](../resultados/aco/piloto/manifesto.json), [campanha](../resultados/aco/campanha/manifesto.json) e [comparação temporal](../resultados/aco/tempo_pr01/manifesto.json).',
    '- `resultados/aco/*/execucoes/`: JSONs brutos com todas as construções completas, inclusive dominadas, e índice de ocorrências.',
    '- `resultados/aco/campanha/fontes/` e `tempo_pr01/fontes/`: cópias das fontes usadas; versões, hashes, argumentos e sementes nos manifestos.',
    '- `reavaliacao.csv` e `*_reavaliacao.json` em cada pasta: agendas comparadas sobre a mesma união bruta, custo e PLs fora da busca.',
    '', '![Fronteiras e distribuições de HV em pr01](../resultados/aco/comparacao/pr01_avaliacoes.png)',
    '', '![Comparação de 60 segundos em pr01](../resultados/aco/comparacao/pr01_tempo.png)', '']
(ROOT / 'relatorio/RESULTADOS_ACO.md').write_text('\n'.join(linhas), encoding='utf-8')
print('Relatorio de resultados criado.', flush=True)
