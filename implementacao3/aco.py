"""Adaptador da colonia de formigas para a interface comum do menu."""
from dataclasses import replace

from implementacao3.colonia_formigas import ConfigACO, resolver_aco
from implementacao3.base import Metaheuristica, ResultadoOtimizacao


class ColoniaFormigas(Metaheuristica):
    def __init__(self, seed: int = 42, **parametros):
        super().__init__("ACO")
        if "politica" in parametros:
            raise ValueError("A politica do ACO no menu vem de parametros_avaliacao.politica")
        self.config = ConfigACO(seed=seed, **parametros)

    def otimizar(self, inst, av, **kwargs):
        config = replace(self.config, politica=av.par.politica)
        if config.limite_posicoes_insercao is None:
            config = replace(config, limite_posicoes_insercao=getattr(av, "limite_posicoes_construcao", None))
        res = resolver_aco(inst, av.par, config)
        estatisticas = {"tipo": "resumo_aco", "motivo_parada": res.motivo_parada,
                       "consultas": res.consultas, "acertos_cache": res.acertos_cache,
                       "chamadas_pl": res.chamadas_pl, "construcoes": res.construcoes,
                       "fracassadas": res.fracassadas, "interrompidas": res.interrompidas,
                       "rejeicoes_necessarias": res.rejeicoes_necessarias}
        return ResultadoOtimizacao(
            algoritmo=self.nome,
            fronteira=[(p.f1, p.f2, p.solucao) for p in res.fronteira],
            tempo_execucao=res.tempo, iteracoes=len(res.historico), avaliacoes=res.consultas,
            historico=[*res.historico, estatisticas],
        )
