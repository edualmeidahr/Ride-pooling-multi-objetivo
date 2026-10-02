"""Gera figuras PNG/SVG com escalas comuns, variabilidade e guia de leitura."""
import argparse
import json
import os
from pathlib import Path

import numpy as np


def main():
    raiz = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resultados", type=Path, default=raiz / "resultados/comparacao_q1_10")
    args = parser.parse_args()
    dados = json.loads((args.resultados / "execucoes.json").read_text(encoding="utf-8"))
    if "normalizacao" not in dados:
        parser.error("campanha ainda nao terminou; aguarde as metricas finais")
    os.environ.setdefault("MPLCONFIGDIR", str(raiz / ".cache/matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator, PercentFormatter
    from matplotlib.lines import Line2D

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
        "axes.titlesize": 13, "axes.labelsize": 11, "figure.titlesize": 17,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#6b7280", "axes.labelcolor": "#202938",
        "text.color": "#202938", "xtick.color": "#475569", "ytick.color": "#475569",
        "grid.color": "#e2e8f0", "grid.linewidth": 0.7,
        "savefig.facecolor": "white", "figure.facecolor": "white"})
    saida = args.resultados / "graficos"
    saida.mkdir(exist_ok=True)
    cores = {"sa": "#0072b2", "ga": "#d55e00", "grasp": "#009e73"}
    marcadores = {"sa": "o", "ga": "s", "grasp": "^"}
    metodos = list(dados["config"]["algoritmos"])
    nomes = {"sa": "SA", "ga": "GA", "grasp": "GRASP"}
    qs = dados["config"]["capacidades"]
    seeds = dados["config"]["sementes"]
    runs = dados["execucoes"]
    exata = dados.get("tipo_referencia", "exata") == "exata"
    rotulo_ref = "Exata" if exata else "Referência empírica"
    descricao_ref = "gabarito exato" if exata else "união não dominada dos métodos e sementes, para o mesmo Q"
    campo_recuperacao = "recuperacao_exata" if exata else "recuperacao_referencia"
    seed = 42 if 42 in seeds else seeds[0]
    contexto = f"Exemplo sintético · {len(dados['config']['pedidos'])} pedidos · m={dados['config']['m']} · α={dados['config']['parametros_avaliacao']['alpha']} · OTIMO"
    indice = {(r["metodo"], r["Q"], r["seed"]): r for r in runs}
    guias = []

    def eixo(ax):
        ax.set_axisbelow(True)
        ax.grid(True, alpha=0.8)

    def salvar(fig, nome, titulo, leitura, nota):
        fig.savefig(saida / f"{nome}.png", dpi=180, bbox_inches="tight")
        fig.savefig(saida / f"{nome}.svg", bbox_inches="tight")
        plt.close(fig)
        guias.append((nome, titulo, leitura, nota))

    def faixa(ax, campo, percent=False):
        for metodo in metodos:
            values = []
            for Q in qs:
                v = [indice[(metodo, Q, s)]["metricas"].get(campo,
                     indice[(metodo, Q, s)].get(campo)) for s in seeds]
                values.append([np.nan if x is None else x for x in v])
            arr = np.array(values, dtype=float)
            medio = np.nanmedian(arr, axis=1)
            minimo, maximo = np.nanmin(arr, axis=1), np.nanmax(arr, axis=1)
            ax.plot(qs, medio, color=cores[metodo], marker=marcadores[metodo],
                    markersize=4, linewidth=1.8, label=nomes[metodo])
            ax.fill_between(qs, minimo, maximo, color=cores[metodo], alpha=0.12)
        ax.set_xlabel("Capacidade Q (passageiros simultâneos)")
        ticks = qs if len(qs) <= 10 else [q for q in (1, 2, 4, 8, 12, 16, 20) if q in qs]
        ax.set_xticks(ticks or qs)
        ax.set_xlim(min(qs) - 0.3, max(qs) + 0.3)
        ax.legend(frameon=False, ncol=3)
        eixo(ax)
        if percent:
            ax.yaxis.set_major_formatter(PercentFormatter(1))

    def figura(titulo, sub=None):
        fig, ax = plt.subplots(figsize=(10.5, 5.6))
        fig.suptitle(titulo, x=0.07, ha="left", y=0.98)
        ax.set_title(sub or contexto, loc="left", color="#64748b", fontsize=10, pad=12)
        fig.subplots_adjust(top=0.80, bottom=0.14, left=0.09, right=0.97)
        return fig, ax

    # Mesma escala em todos os paineis; nenhum deslocamento dos valores.
    escolhidos = ([1,3,6,10] if not exata and all(q in qs for q in [1,3,6,10]) else
                  list(dict.fromkeys([min(qs), 2 if 2 in qs else qs[0], 3 if 3 in qs else qs[0], max(qs)])))
    fig, axs = plt.subplots(2, 2, figsize=(12, 8.6), sharex=True, sharey=True)
    fig.suptitle(f"Fronteiras de Pareto: heurísticas versus {rotulo_ref.lower()}", x=0.07, ha="left")
    fig.text(0.07, 0.935, contexto + f" · semente {seed}", color="#64748b")
    pts = [p for Q in escolhidos for p in dados["referencias"][str(Q)]["pontos"]]
    pts += [(p["f1"], p["f2"]) for r in runs if r["Q"] in escolhidos and r["seed"] == seed for p in r["pontos"]]
    maxx, maxy = max(p[0] for p in pts), max(p[1] for p in pts)
    for ax, Q in zip(axs.flat, escolhidos):
        exato = sorted(dados["referencias"][str(Q)]["pontos"])
        ax.plot([p[0] for p in exato], [max(0, p[1]) for p in exato], "--", color="#202938", lw=1.4)
        for pos, metodo in enumerate(metodos):
            points = sorted(indice[(metodo, Q, seed)]["pontos"], key=lambda p: p["f1"])
            ax.plot([p["f1"] for p in points], [max(0, p["f2"]) for p in points],
                    color=cores[metodo], marker=marcadores[metodo], markersize=10 - pos * 2,
                    markerfacecolor="none", markeredgewidth=1.4, linestyle=":", lw=0.9)
        ax.set_title(f"Q = {Q}", loc="left")
        ax.set_xlim(0, maxx * 1.08)
        ax.set_ylim(-maxy * 0.045, maxy * 1.1)
        ax.set_xlabel("Distância total da frota (km)")
        ax.set_ylabel("Tempo perdido (passageiro-minutos)")
        eixo(ax)
    legend = [Line2D([0], [0], color="#202938", linestyle="--", label=rotulo_ref)]
    legend += [Line2D([0], [0], color=cores[m], marker=marcadores[m], markerfacecolor="none", label=nomes[m]) for m in metodos]
    fig.legend(handles=legend, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.025))
    fig.subplots_adjust(top=0.86, bottom=0.15, hspace=0.32, wspace=0.20)
    salvar(fig, "01_fronteiras_metodos", "Fronteiras por método e capacidade",
           "Mais à esquerda e abaixo é melhor. Cada símbolo é uma solução viável; os painéis usam a mesma escala.",
           "Uma semente por método. Símbolos sobrepostos indicam soluções coincidentes; linhas só guiam a leitura, não representam soluções contínuas.")

    fig, ax = figura("Qualidade da fronteira por capacidade", contexto + f" · {len(seeds)} sementes · mediana e intervalo mínimo–máximo")
    faixa(ax, "hv_relativo", percent=True)
    ax.axhline(1, color="#202938", ls="--", lw=1, label=rotulo_ref)
    ax.set_ylim(0, 1.06)
    ax.set_ylabel("Hipervolume obtido / hipervolume de referência")
    ax.legend(frameon=False, ncol=4)
    salvar(fig, "02_qualidade_por_q", "Qualidade por Q",
           f"100% significa o mesmo hipervolume da referência: {descricao_ref}. Valores menores revelam alternativas ainda não recuperadas.",
           "Mesma normalização para todas as capacidades e sementes; a faixa é mínimo–máximo, não intervalo de confiança.")

    fig, ax = figura("Distância mínima encontrada por capacidade", contexto + " · mediana e intervalo mínimo–máximo")
    faixa(ax, "min_f1")
    ax.plot(qs, [min(p[0] for p in dados["referencias"][str(q)]["pontos"]) for q in qs],
            color="#202938", linestyle="--", label=rotulo_ref)
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Menor distância da fronteira (km)")
    ax.legend(frameon=False, ncol=4)
    salvar(fig, "03_distancia_por_q", "Benefício e saturação da capacidade",
           "Mostra quanto a capacidade adicional reduz a melhor distância. Um patamar indica saturação nessa instância.",
           "O extremo de distância não representa simultaneamente o melhor serviço; consulte a fronteira completa.")

    fig, ax = figura("Tempo de execução dos métodos", contexto + " · mediana e intervalo mínimo–máximo")
    faixa(ax, "tempo_busca")
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Tempo da busca (segundos)")
    salvar(fig, "04_tempo_execucao", "Custo computacional observado",
           "Compara o tempo efetivamente gasto nesta máquina, incluindo construção e busca, sem incluir validação posterior ou enumeração exata.",
           "Os métodos têm parâmetros e esforços diferentes. Menor tempo isoladamente não certifica maior eficiência.")

    fig, ax = figura("Esforço efetivo: avaliações de rotas", contexto + " · mediana e intervalo mínimo–máximo")
    faixa(ax, "agendamentos")
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Agendamentos de rotas não vazias")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    salvar(fig, "05_esforco_computacional", "Esforço medido",
           "Conta também as avaliações na construção e no cruzamento, omitidas pelos antigos contadores dos métodos.",
           "Conta chamadas de agendamento de rota, não soluções completas, iterações ou necessariamente resoluções bem-sucedidas de PL.")

    q_alvo = (5 if not exata and 5 in qs else 2 if 2 in qs else qs[0])
    fig, ax = figura(f"Evolução da qualidade durante a busca · Q={q_alvo}", contexto + f" · semente {seed} · checkpoints observados")
    for m in metodos:
        hist = indice[(m, q_alvo, seed)]["historico"]
        ax.step([h["agendamentos"] for h in hist], [h["hv_relativo"] for h in hist],
                where="post", color=cores[m], marker=marcadores[m], markersize=4, label=nomes[m])
    ax.axhline(1, color="#202938", ls="--", lw=1)
    ax.set_ylim(0, 1.06)
    ax.set_xlim(left=0)
    ax.set_xlabel("Agendamentos acumulados de rotas não vazias")
    ax.set_ylabel("Hipervolume obtido / hipervolume de referência")
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(frameon=False, ncol=3)
    eixo(ax)
    salvar(fig, "06_evolucao_busca", "Convergência observada",
           "A curva registra a qualidade do arquivo Pareto ao longo do esforço acumulado. Subidas indicam novas alternativas úteis.",
           "Cada método registra checkpoints próprios. Não há interpolação nem observação a cada movimento; só uma semente é mostrada.")

    fig, ax = plt.subplots(figsize=(12, 4.3))
    fig.suptitle(f"Recuperação dos pontos: {rotulo_ref.lower()}", x=0.07, ha="left")
    matrix = [[np.mean([indice[(m, q, s)]["metricas"][campo_recuperacao] for s in seeds]) for q in qs] for m in metodos]
    im = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    ax.set_yticks(range(len(metodos)), [nomes[m] for m in metodos])
    ax.set_xticks(range(len(qs)), qs)
    ax.set_xlabel("Capacidade Q (passageiros simultâneos)")
    for i, row in enumerate(matrix):
        for j, val in enumerate(row):
            ax.text(j, i, f"{val:.0%}", ha="center", va="center", fontsize=9, color="white" if val > 0.55 else "#202938")
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.03)
    cb.ax.yaxis.set_major_formatter(PercentFormatter(1))
    cb.set_label("Fração dos pontos de referência")
    fig.subplots_adjust(top=0.80, bottom=0.20, left=0.10, right=0.91)
    salvar(fig, "07_recuperacao_pontos", "Recuperação de pontos de referência",
           "Cada célula mostra a média da fração de pontos de referência recuperados nas sementes; coincidência usa tolerância 1e-6 nos objetivos.",
           "Essa medida verifica pontos coincidentes, enquanto hipervolume também reconhece aproximações úteis.")

    fig, ax = figura("Quantidade de alternativas não dominadas", contexto + " · mediana e intervalo mínimo–máximo")
    faixa(ax, "cardinalidade")
    ax.plot(qs, [len(dados["referencias"][str(q)]["pontos"]) for q in qs], color="#202938", ls="--", label=rotulo_ref)
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Número de soluções na fronteira")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend(frameon=False, ncol=4)
    salvar(fig, "08_cardinalidade", "Número de alternativas",
           "Mostra quantas escolhas de compromisso cada execução encontrou, usando os mesmos critérios de dominância.",
           "Mais pontos não implica maior qualidade: uma fronteira com muitos pontos pode ser dominada por outra menor.")

    if "concorrencia" in dados:
        fig, axs = plt.subplots(1,2,figsize=(12,5.8))
        fig.suptitle("Uso dos veículos e da capacidade", x=0.07, ha="left")
        fig.text(0.07,0.90,contexto+" · solução de menor distância de cada execução",color="#64748b",fontsize=10)
        for ax,campo,titulo in zip(axs,["veiculos_usados","carga_maxima"],
                                   ["Veículos utilizados","Maior carga em uma rota"]):
            for m in metodos:
                v=np.array([[min(indice[(m,q,s)]["pontos"],key=lambda p:(p["f1"],p["f2"]))[campo]
                             for s in seeds] for q in qs])
                ax.plot(qs,np.median(v,axis=1),color=cores[m],marker=marcadores[m],label=nomes[m])
                ax.fill_between(qs,v.min(axis=1),v.max(axis=1),color=cores[m],alpha=0.12)
            if campo=="veiculos_usados":
                ax.plot(qs,[int(np.ceil(dados["concorrencia"]["passageiros"]/q)) for q in qs],
                        "--",color="#202938",label="Limite inferior por concorrência")
            else:
                ax.plot(qs,qs,"--",color="#202938",label="Capacidade disponível")
            ax.set_xlabel("Capacidade Q (passageiros)")
            ax.set_ylabel("Veículos" if campo=="veiculos_usados" else "Passageiros simultâneos")
            ax.set_title(titulo,loc="left")
            ax.set_xticks(qs)
            ax.set_ylim(bottom=0)
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            ax.legend(frameon=False,fontsize=8,loc="upper center",bbox_to_anchor=(0.5,-0.20),ncol=2)
            eixo(ax)
        fig.subplots_adjust(top=0.78,bottom=0.27,wspace=0.25)
        salvar(fig,"09_uso_capacidade","Uso dos veículos e da capacidade",
               "Mostra o agrupamento efetivamente encontrado: quantidade de veículos e maior ocupação na solução de menor distância de cada execução.",
               "Mediana e mínimo–máximo entre sementes. Carga máxima é um pico, não ocupação média. O limite de veículos vale porque todas as coletas antecedem qualquer entrega neste cenário.")

    if not exata:
        fig,ax=figura("Fronteiras observadas para todas as capacidades",contexto+" · união não dominada de métodos e sementes por Q")
        mapa=plt.get_cmap("viridis")
        for q in qs:
            pontos=sorted(dados["referencias"][str(q)]["pontos"])
            ax.plot([p[0] for p in pontos],[max(0,p[1]) for p in pontos],
                    color=mapa(0.10+0.75*(q-min(qs))/max(1,max(qs)-min(qs))),marker="o",markersize=3,
                    linewidth=1.2,label=f"Q={q}")
        ax.set_xlabel("Distância total da frota (km)")
        ax.set_ylabel("Tempo perdido (passageiro-minutos)")
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.legend(frameon=False,ncol=2,fontsize=9)
        eixo(ax)
        salvar(fig,"10_fronteiras_todos_q","Efeito de Q na fronteira inteira",
               "Cada cor representa a união não dominada observada para um Q. Compare distância em níveis semelhantes de tempo perdido, ou vice-versa.",
               "São referências empíricas. Cruzamentos podem decorrer de buscas incompletas; não provam que aumentar a capacidade piora o ótimo.")

    # Guia autocontido: explica dados, parametros e limites antes das figuras.
    linhas = ["# Guia dos gráficos e resultados", "", "## O que foi executado", "",
        f"{len(runs)} execuções: {len(qs)} capacidades × {len(metodos)} métodos × {len(seeds)} sementes.",
        f"{contexto}. Índices internos dos pedidos: {dados['config']['pedidos']}; sementes: {seeds}.",
        "Dados sintéticos, phi=1: o eixo ambiental é distância em km, não emissão real calibrada.",
        "Todos os pontos retornados foram reavaliados com programação linear para a sequência de cada rota.",
        ("O gabarito foi enumerado: a referência é exata." if exata else
         "A referência é empírica: união não dominada de todos os métodos e sementes, separadamente por Q. Não é gabarito nem prova de otimalidade; mudar a campanha pode mudar essa referência."), "",
        ("Agendas repetidas são reutilizadas em cache separado por execução. O cache foi conferido contra o agendador sem cache e não modifica as decisões. Tempo inclui esse cache; chamadas de agendamento incluem acertos no cache. Resoluções efetivas e acertos estão registrados no CSV/JSON." if dados["config"].get("cache_agendas") else "Agendamento executado sem cache de agendas nesta campanha."), "",
        "Os métodos têm esforços distintos. Esta é uma campanha exploratória, não um ranking definitivo.",
        f"Faixas mostram mínimo–máximo entre {len(seeds)} sementes; não são intervalos de confiança. A linha central é a mediana.",
        "Capacidades maiores que a demanda total tornam-se redundantes. Patamares antes disso também podem ocorrer pela geometria e pelas janelas.", "",
        "## Configuração e dados reproduzíveis", "",
        "Configuração completa, versões, hash da entrada, hash dos fontes, rotas, horários e checkpoints: [execucoes.json](execucoes.json).",
        "Métricas por capacidade/método/semente: [metricas.csv](metricas.csv).", "",
        "## Resumo observado por capacidade", "",
        "A distância abaixo é o menor valor na referência. As três últimas colunas mostram a mediana de qualidade relativa nas sementes; não comparam qualidade absoluta entre capacidades.", "",
        "| Q | Menor distância de referência (km) | Pontos de referência | SA: HV relativo | GA: HV relativo | GRASP: HV relativo |",
        "|---|---:|---:|---:|---:|---:|"]
    for q in qs:
        ref=dados["referencias"][str(q)]["pontos"]
        razoes=[np.median([indice[(m,q,s)]["metricas"]["hv_relativo"] for s in seeds]) for m in ["sa","ga","grasp"]]
        linhas.append(f"| {q} | {min(p[0] for p in ref):.1f} | {len(ref)} | {razoes[0]:.1%} | {razoes[1]:.1%} | {razoes[2]:.1%} |")
    linhas += ["", "## Como ler cada figura", ""]
    explicacoes = {
        "01_fronteiras_metodos": [
            "**Eixos:** X = soma das distâncias de todos os veículos, em km; Y = tempo perdido total, em passageiro-minutos. O segundo objetivo soma espera após o horário desejado de coleta e o excesso de tempo a bordo em relação à viagem direta, ponderados pelo número de passageiros.",
            "**Exemplo de unidade:** dez pessoas perdendo dois minutos cada somam 20 passageiro-minutos. Não é a duração total das viagens nem uma média por pessoa.",
            "**Como comparar:** um ponto com menor X e menor Y domina outro. Quando um melhora X e piora Y, há um compromisso: a decisão depende da prioridade de operação e serviço. Compare também a aproximação ao tracejado dentro de cada painel.",
            "**Limite:** o painel mostra apenas uma semente. Coincidência visual não demonstra que os métodos sempre geram o mesmo resultado. As linhas conectam alternativas discretas; um ponto intermediário na linha não é necessariamente realizável."],
        "02_qualidade_por_q": [
            "**Eixos:** X = capacidade; Y = hipervolume da fronteira de uma execução dividido pelo hipervolume da referência do mesmo Q. Maior é melhor.",
            "**O que é hipervolume:** após colocar os dois objetivos em escalas comparáveis, mede a área coberta pelas soluções em direção ao canto pior de referência. Recompensa simultaneamente proximidade a bons valores e cobertura dos compromissos. Todas as execuções usam uma normalização global e o mesmo canto: x=1,1 e y=1,1.",
            "**Exemplo:** 80% significa 80% da área da referência, não 80% de passageiros atendidos e não um erro de 20% na distância. Um método pode obter uma boa razão sem recuperar exatamente todos os pontos.",
            "**Comparação entre Q:** o denominador muda com Q. Portanto, 100% em Q=1 e Q=10 indica qualidade relativa semelhante; não indica mesmas distâncias ou mesmos tempos perdidos. Consulte os gráficos 1 e 3."],
        "03_distancia_por_q": [
            "**Cálculo:** em cada execução, seleciona o menor f1 entre as soluções da fronteira. Em seguida, resume esses mínimos pelas sementes. Menor é melhor.",
            "**Exemplo do recorte pequeno após a correção de unidade:** o gabarito tem 24 km em Q=1, 16 km em Q=2 e 10 km de Q=3 em diante. Esse recorte possui só três passageiros. Os antigos valores 48/32/20 somavam minutos como quilômetros e foram substituídos.",
            "**Patamares:** agrupar um passageiro a mais nem sempre elimina uma rota ou encurta um trajeto. Igualdade entre Q vizinhos pode ser um efeito legítimo. A solução com menor distância pode exigir mais espera ou desvio; o gráfico não afirma que ela é a melhor nos dois objetivos.",
            "**Monotonicidade:** ao aumentar Q, todas as soluções antes viáveis continuam permitidas, mantendo os demais parâmetros. O ótimo de distância não pode piorar; a melhor solução encontrada por uma busca limitada pode piorar por acaso."],
        "04_tempo_execucao": [
            "**Eixos:** X = Q; Y = segundos gastos por execução na construção e otimização. O relógio é iniciado antes do algoritmo e parado quando ele retorna. A geração de gráficos, a enumeração e a conferência posterior não entram.",
            "**Leitura:** a linha mostra o tempo mediano; a faixa mostra o menor e maior tempo nas sementes. Maior faixa indica variação observada, mas poucos ensaios não permitem caracterizar a distribuição.",
            "**Uso:** avalie custo de obtenção das soluções juntamente com a qualidade. Um método rápido que retorna uma fronteira fraca não é automaticamente mais eficiente. Os tempos dependem da máquina e de outros processos ativos."],
        "05_esforco_computacional": [
            "**Eixos:** X = Q; Y = número de chamadas de agendamento de rotas não vazias durante a busca, incluindo construção inicial e cruzamento. Menor representa menos trabalho desse tipo.",
            "**Distinção:** uma avaliação de solução pode agendar vários veículos. Logo, 500 chamadas não significam 500 soluções completas nem 500 movimentos. Rotas de comprimentos diferentes também têm custos diferentes.",
            "**Uso:** ajuda a explicar o tempo do gráfico 4 e expõe diferenças de orçamento. Se um método recebe mais esforço, a diferença de qualidade pode decorrer desse orçamento. Esta campanha mede as chamadas, mas não impõe o mesmo limite aos três métodos."],
        "06_evolucao_busca": [
            "**Eixos:** X = esforço acumulado até um checkpoint; Y = qualidade relativa do arquivo Pareto naquele instante. São mostrados um Q e uma semente, indicados no título.",
            "**Degraus:** uma subida registra melhora no conjunto de alternativas; um trecho horizontal indica que os checkpoints não registraram ganho de hipervolume. Isso não significa que o algoritmo deixou de testar soluções.",
            "**Uso:** compare quanto esforço foi necessário para chegar a um nível de qualidade. O ponto inicial é o primeiro checkpoint real, não um estado artificial em zero. Os métodos registram checkpoints em momentos diferentes, e não há medição a cada movimento.",
            "**Limite:** a convergência de uma semente não representa a variabilidade de todas as execuções; consulte a faixa do gráfico 2."],
        "07_recuperacao_pontos": [
            "**Eixos:** colunas = Q; linhas = métodos; cada célula = média da proporção dos pontos de referência recuperados nas sementes. Azul mais escuro significa maior proporção.",
            "**Exemplo:** se a referência tem três pontos e uma execução encontra dois deles, ela recupera 66,7%. A célula é a média dessa fração entre as sementes, não a recuperação pela união das execuções.",
            "**Diferença para o gráfico 2:** esta medida exige coincidência dos dois objetivos dentro da tolerância; hipervolume atribui valor a aproximações. Uma solução quase igual à referência pode contribuir muito para o hipervolume e não contar como ponto recuperado.",
            ("**Leitura:** compare as células para identificar quais capacidades ainda têm pontos do gabarito não recuperados. Isso descreve este pequeno teste, não um ranking geral." if exata else
             "**Limite da referência empírica:** ela também foi construída usando estes métodos. Um ponto encontrado exclusivamente por uma semente pode reduzir a recuperação das outras. A medida descreve cobertura do conjunto observado, não acerto contra um ótimo comprovado.")],
        "08_cardinalidade": [
            "**Eixos:** X = Q; Y = quantidade de pares de objetivos não dominados e distintos que a execução retornou. A linha de referência mostra a quantidade de alternativas na referência de cada Q.",
            "**Exemplo:** três pontos significam três compromissos distintos entre distância e tempo perdido. Rotas diferentes com os mesmos objetivos não aparecem como alternativas adicionais neste contador.",
            "**Uso:** avalie variedade junto com qualidade. Dez alternativas ruins podem ser dominadas por duas boas; portanto, mais pontos não significa melhor resultado. Um método também pode retornar mais pontos que a referência se seus pontos forem dominados apenas por soluções encontradas pelos outros métodos."],
        "09_uso_capacidade": [
            "**Seleção da solução:** em cada método/Q/semente, escolhe o menor f1; em caso de empate, o menor f2. Os dois painéis descrevem essa mesma solução, resumida entre sementes.",
            "**Painel esquerdo:** conta veículos com pelo menos um atendimento. O tracejado é ceil(12/Q), um limite inferior comprovado para esta entrada: todos os 12 passageiros precisam ser coletados antes de qualquer entrega. Se a linha ficar acima dele, o método utilizou mais veículos do que esse limite exige; isso não comprova que o limite permite a menor distância ou melhor serviço.",
            "**Painel direito:** mostra a maior carga simultânea em qualquer veículo. Um valor de 8 em Q=10 indica pelo menos um veículo com oito pessoas, mas não indica dois lugares ociosos em todos os veículos. Não é taxa média de ocupação.",
            "**Uso:** esclarece se Q foi efetivamente aproveitado. Mais capacidade disponível não obriga a busca a usá-la: destinos, janelas, qualidade de serviço e orçamento podem favorecer agrupamentos menores."],
        "10_fronteiras_todos_q": [
            "**Eixos:** os mesmos do gráfico 1; agora a comparação é entre capacidades, usando todas as sementes e os três métodos. Mais próximo do canto inferior esquerdo é melhor.",
            "**Leitura:** compare a distância que cada Q conseguiu para um tempo perdido semelhante. Assim você analisa o efeito da capacidade sobre vários compromissos, sem resumir tudo ao extremo de menor distância.",
            "**Sobreposições:** trechos coincidentes são resultados legítimos. Dois Q distintos podem permitir as mesmas boas rotas. Maior quantidade de pedidos e simultaneidade removem a saturação trivial por demanda insuficiente, mas não garantem uma fronteira distinta para cada Q.",
            "**Limite:** as referências são condicionadas ao que foi encontrado nesta campanha. Uma referência pior em Q maior sugere investigar orçamento e operadores; não permite concluir que a capacidade maior prejudicou o conjunto de soluções viáveis."],
    }
    for nome, titulo, leitura, nota in guias:
        linhas += [f"### {titulo}", "", leitura, "", *[p+"\n" for p in explicacoes[nome]], nota, "",
                   f"![{titulo}](graficos/{nome}.png)", "",
                   f"[PNG](graficos/{nome}.png) · [SVG vetorial](graficos/{nome}.svg)", ""]
    linhas += ["## Os gráficos anteriores", "",
        "`fase2_fronteira_pr01r5.png` compara políticas de agendamento OTIMO e BORDO em cinco pedidos de volta; não compara SA, GA e GRASP.",
        "`capacidade_q_comparativo.png` mostra apenas os extremos da amostra antiga de ida com m=3 e m=5. As curvas coincidem porque aquela amostra saturou já em Q=1.", "",
        "## Próximos passos", "",
        "1. Ampliar a concorrência e quantidade de pedidos, usando várias instâncias e diferentes frotas.",
        "2. Igualar o orçamento de busca pelo esforço medido e repetir com mais sementes; a campanha atual só mede o esforço, não o limita igualmente.",
        "3. Calibrar parâmetros de SA/GA/GRASP em instâncias separadas das usadas na comparação final.",
        "4. Padronizar as buscas ponderadas e revisar o tratamento de inviabilidade e diversidade.",
        "5. Estudar alpha=1.5/2 e cenários com mais/menos veículos sem misturar seus efeitos com Q.",
        "6. Para emissões reais, adotar redes e fatores por veículo calibrados; com phi(Q), melhoria de emissão ao aumentar Q deixa de ser garantida.",
        "7. Alinhar o relatório acadêmico ao conjunto de métodos escolhido e consolidar a campanha final."]
    (args.resultados / "GUIA_RESULTADOS.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"{len(guias)} figuras PNG/SVG e guia em {args.resultados}")


if __name__ == "__main__":
    main()
