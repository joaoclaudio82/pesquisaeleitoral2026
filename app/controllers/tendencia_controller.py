"""
Controller: Tendências
Página de análise comparativa e histórico completo.
"""
from flask import Blueprint, render_template, request
from ..services import (
    CandidatoService,
    NoticiaService,
    HistoricoService,
    TendenciaService,
)

tendencia_bp = Blueprint('tendencias', __name__)

CONFIANCA_MINIMA = 30


def _filtros_request():
    categoria = request.args.get('categoria', '').strip() or None
    uf = request.args.get('uf', '').strip().upper() or None
    try:
        dias = int(request.args.get('periodo', TendenciaService.DIAS_PADRAO))
    except (TypeError, ValueError):
        dias = TendenciaService.DIAS_PADRAO
    dias = TendenciaService.normalizar_periodo(dias)
    return categoria, uf, dias


@tendencia_bp.get('/')
def index():
    """GET /tendencias/ — página de análise de tendências."""
    categoria, uf, dias = _filtros_request()
    periodo_label = TendenciaService.periodo_label(dias)

    candidatos = CandidatoService.listar_todos(categoria=categoria, uf=uf)
    sentimentos = NoticiaService.contagem_por_sentimento(
        categoria=categoria, uf=uf, dias=dias
    )
    temas_count = NoticiaService.contagem_por_tema(
        categoria=categoria, uf=uf, dias=dias
    )
    grafico_hist = HistoricoService.obter_todos_para_grafico(
        dias=dias, categoria=categoria, uf=uf
    )

    stats_por_id = {
        c.id: NoticiaService.stats_candidato(c.id, dias=dias)
        for c in candidatos
    }

    tabela = []
    for c in candidatos:
        stats = stats_por_id[c.id]
        tabela.append({
            'candidato':       c,
            'total_noticias':  stats['total'],
            'pct_positivo':    stats['pct_positivo'],
            'pct_negativo':    stats['pct_negativo'],
        })

    radar_labels = ['Aprovação', 'Rejeição', 'Neutros',
                    'Menções', 'Notícias', 'Relevância']
    max_mencoes = max((c.mencoes for c in candidatos), default=1) or 1
    max_noticias = max((s['total'] for s in stats_por_id.values()), default=1) or 1

    radar_datasets = []
    for c in candidatos[:6]:
        nots = NoticiaService.por_candidato(c.id)
        relevancia = (sum(n.relevancia for n in nots) / len(nots)
                      if nots else 50)
        stats = stats_por_id[c.id]
        radar_datasets.append({
            'label':            c.nome_abrev,
            'cor':              c.cor,
            'data': [
                round(c.aprovacao, 1),
                round(c.rejeicao, 1),
                round(c.neutro, 1),
                round(c.mencoes / max_mencoes * 100, 1),
                round(stats['total'] / max_noticias * 100, 1),
                round(relevancia, 1),
            ],
        })

    return render_template(
        'tendencias/index.html',
        candidatos        = candidatos,
        tabela            = tabela,
        grafico_historico = grafico_hist,
        radar_datasets    = radar_datasets,
        radar_labels      = radar_labels,
        sentimentos       = sentimentos,
        temas_count       = temas_count,
        filtro_categoria  = categoria,
        filtro_uf         = uf,
        periodo           = dias,
        periodo_padrao    = TendenciaService.DIAS_PADRAO,
        periodo_label     = periodo_label,
        periodos_opcoes   = TendenciaService.PERIODOS,
        dias_tendencias   = dias,
        total_noticias    = sentimentos['total'],
        confianca_baixa   = 0 < sentimentos['total'] < CONFIANCA_MINIMA,
        confianca_minima  = CONFIANCA_MINIMA,
    )
