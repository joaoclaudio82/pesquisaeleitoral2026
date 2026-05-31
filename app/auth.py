"""
Autenticação — Flask-Login e decorators de acesso.
"""
from functools import wraps

from flask import flash, jsonify, redirect, request, url_for
from flask_login import LoginManager, current_user

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Faça login para acessar o sistema.'
login_manager.login_message_category = 'warning'

_PUBLIC_ENDPOINTS = frozenset({
    'auth.login',
    'static',
})

_ADMIN_ONLY_PREFIXES = (
    'noticias.admin',
    'usuarios.',
    'schema.',
)

_ADMIN_ONLY_EXACT = frozenset({
    'candidatos.criar',
    'candidatos.editar',
    'candidatos.buscar_foto',
    'candidatos.remover_foto',
    'candidatos.desativar',
    'api.api_criar_candidato',
    'api.api_desativar_candidato',
    'api.api_coletar',
    'api.api_atualizar',
})


def _endpoint_requer_admin(endpoint: str) -> bool:
    if endpoint in _ADMIN_ONLY_EXACT:
        return True
    return any(endpoint.startswith(p) for p in _ADMIN_ONLY_PREFIXES)


def init_auth(app) -> None:
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        from .models import Usuario
        return Usuario.query.get(int(user_id))

    @app.before_request
    def exigir_login():
        endpoint = request.endpoint
        if not endpoint:
            return None
        if endpoint in _PUBLIC_ENDPOINTS or endpoint.startswith('static'):
            return None
        if current_user.is_authenticated:
            return None
        return redirect(url_for('auth.login', next=request.url))

    @app.before_request
    def bloquear_acesso_admin():
        if not current_user.is_authenticated or current_user.pode_escrever():
            return None

        endpoint = request.endpoint or ''
        if not _endpoint_requer_admin(endpoint):
            return None

        flash('Acesso restrito a administradores.', 'error')
        if request.path.startswith('/api/'):
            return jsonify({
                'status': 'erro',
                'mensagem': 'Perfil somente leitura.',
            }), 403
        return redirect(url_for('main.dashboard'))


def admin_required(f):
    """Decorator para views exclusivas de administrador."""

    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_admin:
            flash('Acesso restrito a administradores.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)

    return wrapped
