"""
Controller: Main (Dashboard)
Rota raiz e dashboard principal.
"""
from flask import Blueprint, render_template, request
from ..services import DashboardService

main_bp = Blueprint('main', __name__)


def _filtros_request():
    categoria = request.args.get('categoria', '').strip() or None
    uf = request.args.get('uf', '').strip().upper() or None
    return categoria, uf


@main_bp.get('/health')
def health():
    """Health check para Railway — sem auth e sem consulta ao banco."""
    from flask import current_app
    db_status = 'ready' if current_app.config.get('_DB_READY') else 'pending'
    return {'status': 'ok', 'db': db_status}, 200


@main_bp.get('/favicon.ico')
def favicon():
    """Evita 404/500 no favicon do navegador."""
    return '', 204


@main_bp.get('/')
def dashboard():
    """
    GET /
    Renderiza o Dashboard com KPIs, gráficos e feed de notícias.
    """
    periodo = int(request.args.get('periodo', 30))
    periodo = DashboardService.normalizar_periodo(periodo)
    categoria, uf = _filtros_request()

    dados = DashboardService.obter_dados(
        periodo=periodo,
        categoria=categoria,
        uf=uf,
    )
    return render_template('dashboard.html', **dados)
