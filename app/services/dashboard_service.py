"""
Service: DashboardService
Agrega dados de múltiplos serviços para montar o Dashboard.
Todas as métricas de sentimento/notícias vêm das notícias coletadas pelo app.
"""
from .candidato_service import CandidatoService
from .noticia_service   import NoticiaService
from .inteligencia_service import InteligenciaService
from .alerta_service import AlertaService


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
    TIPOS_SINAL_OPCOES = [
        ('', 'Todos os sinais'),
        ('ruptura_negativa', 'Ruptura negativa'),
        ('aceleracao_positiva', 'Aceleração positiva'),
        ('pico_visibilidade', 'Pico de visibilidade'),
        ('tema_negativo', 'Tema em risco'),
    ]

    @staticmethod
    def periodo_label(dias: int) -> str:
        return dict(DashboardService.PERIODOS).get(dias, f'{dias} dias')

    @staticmethod
    def normalizar_periodo(dias: int) -> int:
        return dias if dias in DashboardService.PERIODOS_VALIDOS else 30

    @staticmethod
    def normalizar_comparacao(comparacao: int, periodo: int) -> int:
        comparacao = comparacao if comparacao > 0 else periodo
        return min(comparacao, periodo)

    @staticmethod
    def obter_dados(
        periodo: int = 30,
        categoria: str | None = None,
        uf: str | None = None,
        comparacao_dias: int | None = None,
        tipo_sinal: str | None = None,
    ) -> dict:
        """
        Retorna KPIs e gráficos com base nas notícias coletadas no período.

        Args:
            periodo: Janela em dias (1, 7, 14, 30, 60, 90, 150).
            categoria: Filtro por cargo eleitoral.
            uf: Filtro por estado (UF).
        """
        periodo = DashboardService.normalizar_periodo(periodo)
        comparacao = DashboardService.normalizar_comparacao(
            comparacao_dias or periodo, periodo
        )
        tipo_sinal = (tipo_sinal or '').strip() or None
        if tipo_sinal == '':
            tipo_sinal = None
        periodo_label = DashboardService.periodo_label(periodo)
        comparacao_label = DashboardService.periodo_label(comparacao)

        candidatos = CandidatoService.listar_todos(categoria=categoria, uf=uf)
        sentimentos = NoticiaService.contagem_por_sentimento(
            categoria=categoria, uf=uf, dias=periodo
        )
        sentimentos_previos = NoticiaService.contagem_por_sentimento(
            categoria=categoria, uf=uf, dias=periodo * 2
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

        sinais = InteligenciaService.gerar_sinais(
            candidatos,
            dias=periodo,
            comparacao_dias=comparacao,
            tipo_sinal=tipo_sinal,
        )
        alertas = AlertaService.gerar_alertas(
            candidatos,
            dias=periodo,
            comparacao_dias=comparacao,
            tipo_sinal=tipo_sinal,
            categoria=categoria,
            uf=uf,
        )
        ranking_temas_risco = InteligenciaService.ranking_risco_temas(
            categoria=categoria, uf=uf, dias=periodo
        )
        acoes_recomendadas = []
        for s in sinais[:3]:
            acoes_recomendadas.append({
                'titulo': s['resumo'],
                'acao': s['recomendacao'],
                'severidade': s['severidade'],
                'score': s['score'],
            })

        delta_pos = round(
            sentimentos['pct_positivo'] - sentimentos_previos['pct_positivo'], 1
        )
        delta_neg = round(
            sentimentos['pct_negativo'] - sentimentos_previos['pct_negativo'], 1
        )
        delta_total = sentimentos['total'] - sentimentos_previos['total']

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
            'insights': {
                'delta_positivo_pp': delta_pos,
                'delta_negativo_pp': delta_neg,
                'delta_volume': delta_total,
                'sinais': sinais,
                'acoes_recomendadas': acoes_recomendadas,
            },
            'candidatos':        candidatos,
            'ranking':           ranking,
            'noticias_recentes': noticias_recentes,
            'alertas':           alertas,
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
            'comparacao_dias':  comparacao,
            'comparacao_label': comparacao_label,
            'tipo_sinal':       tipo_sinal or '',
            'tipos_sinal_opcoes': DashboardService.TIPOS_SINAL_OPCOES,
            'ranking_temas_risco': ranking_temas_risco,
        }
