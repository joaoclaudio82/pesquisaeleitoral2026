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
