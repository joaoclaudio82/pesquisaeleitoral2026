"""
Service: DashboardService
Agrega dados de múltiplos serviços para montar o Dashboard.
Todas as métricas de sentimento/notícias vêm das notícias coletadas pelo app.
"""
from .candidato_service import CandidatoService
from .noticia_service   import NoticiaService


class DashboardService:
    """Agrega métricas para a página de Dashboard."""

    PERIODOS = [
        (1,   '1 dia'),
        (7,   '7 dias'),
        (14,  '14 dias'),
        (30,  '1 mês'),
        (60,  '2 meses'),
        (90,  '3 meses'),
        (150, '5 meses'),
    ]

    PERIODOS_VALIDOS = {p[0] for p in PERIODOS}
    CONFIANCA_MINIMA = 30

    @staticmethod
    def periodo_label(dias: int) -> str:
        return dict(DashboardService.PERIODOS).get(dias, f'{dias} dias')

    @staticmethod
    def normalizar_periodo(dias: int) -> int:
        return dias if dias in DashboardService.PERIODOS_VALIDOS else 30

    @staticmethod
    def obter_dados(
        periodo: int = 30,
        categoria: str | None = None,
        uf: str | None = None,
    ) -> dict:
        """
        Retorna KPIs e gráficos com base nas notícias coletadas no período.

        Args:
            periodo: Janela em dias (1, 7, 14, 30, 60, 90, 150).
            categoria: Filtro por cargo eleitoral.
            uf: Filtro por estado (UF).
        """
        periodo = DashboardService.normalizar_periodo(periodo)
        periodo_label = DashboardService.periodo_label(periodo)

        candidatos = CandidatoService.listar_todos(categoria=categoria, uf=uf)
        sentimentos = NoticiaService.contagem_por_sentimento(
            categoria=categoria, uf=uf, dias=periodo
        )
        temas_count = NoticiaService.contagem_por_tema(
            categoria=categoria, uf=uf, dias=periodo
        )
        noticias_recentes = NoticiaService.recentes(
            limite=8, categoria=categoria, uf=uf, dias=periodo
        )

        mencoes_labels = []
        mencoes_data   = []
        mencoes_cores  = []
        ranking        = []

        for c in candidatos:
            stats = NoticiaService.stats_candidato(c.id, dias=periodo)
            mencoes_labels.append(c.nome_abrev)
            mencoes_data.append(stats['total'])
            mencoes_cores.append(c.cor)
            ranking.append({
                'candidato':    c,
                'total':        stats['total'],
                'pct_positivo': stats['pct_positivo'],
                'pct_negativo': stats['pct_negativo'],
                'pct_neutro':   stats['pct_neutro'],
            })

        ranking.sort(key=lambda r: (r['pct_positivo'], r['total']), reverse=True)

        sentimento_por_candidato = {
            'labels':   [],
            'positivo': [],
            'negativo': [],
            'neutro':   [],
            'totais':   [],
            'cores':    [],
        }
        for row in ranking:
            if row['total'] == 0:
                continue
            c = row['candidato']
            sentimento_por_candidato['labels'].append(c.nome_abrev)
            sentimento_por_candidato['positivo'].append(row['pct_positivo'])
            sentimento_por_candidato['negativo'].append(row['pct_negativo'])
            sentimento_por_candidato['neutro'].append(row['pct_neutro'])
            sentimento_por_candidato['totais'].append(row['total'])
            sentimento_por_candidato['cores'].append(c.cor)

        sentimento_labels = ['Positivo', 'Negativo', 'Neutro']
        sentimento_data   = [
            sentimentos['pct_positivo'],
            sentimentos['pct_negativo'],
            sentimentos['pct_neutro'],
        ]

        temas_labels_list = ['Economia', 'Saúde', 'Educação',
                              'Violência', 'Justiça', 'Política']
        temas_data_list   = [
            temas_count.get('economia',  0),
            temas_count.get('saude',     0),
            temas_count.get('educacao',  0),
            temas_count.get('violencia', 0),
            temas_count.get('justica',   0),
            temas_count.get('politica',  0),
        ]

        total = sentimentos['total']

        return {
            'kpi': {
                'positivo':       sentimentos['pct_positivo'],
                'negativo':       sentimentos['pct_negativo'],
                'neutro':         sentimentos['pct_neutro'],
                'total_noticias': sentimentos['total'],
                'noticias_hoje':  NoticiaService.noticias_hoje(categoria=categoria, uf=uf),
            },
            'candidatos':        candidatos,
            'ranking':           ranking,
            'noticias_recentes': noticias_recentes,
            'confianca_baixa': 0 < total < DashboardService.CONFIANCA_MINIMA,
            'confianca_minima': DashboardService.CONFIANCA_MINIMA,
            'grafico_mencoes': {
                'labels': mencoes_labels,
                'data':   mencoes_data,
                'cores':  mencoes_cores,
            },
            'grafico_sentimento': {
                'labels': sentimento_labels,
                'data':   sentimento_data,
            },
            'grafico_sentimento_candidatos': sentimento_por_candidato,
            'grafico_temas': {
                'labels': temas_labels_list,
                'data':   temas_data_list,
            },
            'periodo':          periodo,
            'periodo_label':    periodo_label,
            'periodos_opcoes':  DashboardService.PERIODOS,
            'filtro_categoria': categoria,
            'filtro_uf':        uf,
        }
