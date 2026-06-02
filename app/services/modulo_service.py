"""
Service: ModuloService
Monta visoes por perfil profissional.
"""
from .dashboard_service import DashboardService


class ModuloService:
    @staticmethod
    def obter_visao(perfil: str, categoria: str | None = None, uf: str | None = None) -> dict:
        base = DashboardService.obter_dados(periodo=30, categoria=categoria, uf=uf)
        if perfil == 'campanha':
            foco = 'Monitoramento diario de risco reputacional e reacao rapida.'
        elif perfil == 'partido':
            foco = 'Comparativo multi-candidatos por tema e UF para decisao tatico-estrategica.'
        else:
            foco = 'Leitura executiva com comparativos, alertas e recomendacoes acionaveis.'
        return {
            'perfil': perfil,
            'foco': foco,
            'insights': base.get('insights', {}),
            'alertas': base.get('alertas', []),
            'ranking': base.get('ranking', []),
            'periodo_label': base.get('periodo_label', '30 dias'),
        }
