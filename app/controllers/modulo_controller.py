"""
Controller: Modulos profissionais
Visoes orientadas por perfil (consultor, campanha, partido).
"""
from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..auth import home_after_login
from ..services import ModuloService

modulo_bp = Blueprint('modulos', __name__, url_prefix='/modulos')


def _filtros():
    categoria = request.args.get('categoria', '').strip() or None
    uf = request.args.get('uf', '').strip().upper() or None
    return categoria, uf


@modulo_bp.get('/')
@login_required
def index():
    return redirect(home_after_login(current_user))


@modulo_bp.get('/consultoria')
@login_required
def consultoria():
    categoria, uf = _filtros()
    dados = ModuloService.obter_visao('consultor', categoria=categoria, uf=uf)
    return render_template('modulos/perfil.html', **dados, titulo='Módulo Consultoria')


@modulo_bp.get('/campanha')
@login_required
def campanha():
    categoria, uf = _filtros()
    dados = ModuloService.obter_visao('campanha', categoria=categoria, uf=uf)
    return render_template('modulos/perfil.html', **dados, titulo='Módulo Campanha')


@modulo_bp.get('/partido')
@login_required
def partido():
    categoria, uf = _filtros()
    dados = ModuloService.obter_visao('partido', categoria=categoria, uf=uf)
    return render_template('modulos/perfil.html', **dados, titulo='Módulo Partido')
