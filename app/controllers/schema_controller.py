"""
Controller: Schema do banco de dados (somente administrador).
"""
from flask import Blueprint, render_template

from ..auth import admin_required
from ..services import SchemaService

schema_bp = Blueprint('schema', __name__, url_prefix='/admin/banco')


@schema_bp.get('/')
@admin_required
def index():
    """GET /admin/banco/ — documentação de tabelas e relacionamentos."""
    dados = SchemaService.obter_documentacao()
    return render_template('schema/index.html', **dados)
