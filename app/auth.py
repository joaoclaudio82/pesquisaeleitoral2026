"""
Autenticação — Flask-Login e decorators de acesso.
"""
from functools import wraps
from urllib.parse import urlparse

from flask import flash, jsonify, redirect, request, url_for
from flask_login import LoginManager, current_user

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Faça login para acessar o sistema.'
login_manager.login_message_category = 'warning'

_PUBLIC_ENDPOINTS = frozenset({
    'auth.login',
    'main.health',
    'main.favicon',
    'static',
})

_ADMIN_ONLY_PREFIXES = (
    'noticias.admin',
    'usuarios.',
    'schema.',
)

_PAPEL_MODULO_ENDPOINT = {
    'consultor': 'modulos.consultoria',
    'campanha': 'modulos.campanha',
    'partido': 'modulos.partido',
}

_MODULO_ENDPOINTS = frozenset(_PAPEL_MODULO_ENDPOINT.values())

_ADMIN_ONLY_EXACT = frozenset({
    'candidatos.criar',
    'candidatos.editar',
    'candidatos.buscar_foto',
    'candidatos.remover_foto',
    'candidatos.desativar',
    'candidatos.descobrir',
    'api.api_criar_candidato',
    'api.api_desativar_candidato',
    'api.api_coletar',
    'api.api_descobrir_candidatos',
    'api.api_atualizar',
})


def login_next_path() -> str:
    """Caminho relativo pós-login (evita http:// gerado atrás de proxy Railway)."""
    path = request.path or '/'
    qs = request.query_string.decode()
    return f'{path}?{qs}' if qs else path


def safe_redirect_target(raw: str | None) -> str:
    """Aceita só caminhos relativos ou URLs do mesmo host; fallback para o dashboard."""
    if not raw:
        return url_for('main.dashboard')
    if raw.startswith('/') and not raw.startswith('//'):
        return raw
    parsed = urlparse(raw)
    if parsed.netloc and parsed.netloc != request.host:
        return url_for('main.dashboard')
    path = parsed.path or '/'
    if parsed.query:
        path = f'{path}?{parsed.query}'
    return path


def home_after_login(usuario) -> str:
    """Destino padrão após autenticação conforme perfil analítico."""
    endpoint = _PAPEL_MODULO_ENDPOINT.get(usuario.papel)
    if endpoint:
        return url_for(endpoint)
    return url_for('main.dashboard')


def modulo_home_for_user(usuario) -> str:
    return home_after_login(usuario)


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
        return redirect(url_for('auth.login', next=login_next_path()))

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

    @app.before_request
    def restringir_modulo_por_perfil():
        endpoint = request.endpoint or ''
        if endpoint not in _MODULO_ENDPOINTS:
            return None
        if not current_user.is_authenticated:
            return None
        if current_user.is_admin or current_user.papel == 'visualizador':
            return None
        permitido = _PAPEL_MODULO_ENDPOINT.get(current_user.papel)
        if permitido and endpoint != permitido:
            flash('Seu perfil tem acesso ao módulo dedicado da sua equipe.', 'warning')
            return redirect(url_for(permitido))
        return None


def admin_required(f):
    """Decorator para views exclusivas de administrador."""

    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=login_next_path()))
        if not current_user.is_admin:
            flash('Acesso restrito a administradores.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)

    return wrapped
