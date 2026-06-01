"""
Pesquisa Eleitoral 2026 — Factory da aplicação Flask
Padrão Application Factory + Blueprints (MVC)
"""
import os
from flask import Flask
from .database import db
from config import config_map, resolve_production_database_uri


def create_app(env: str = None) -> Flask:
    """
    Cria e configura a instância da aplicação Flask.

    Args:
        env: Nome do ambiente ('development', 'production', 'testing').
             Se None, lê da variável de ambiente FLASK_ENV.

    Returns:
        Flask: Instância configurada da aplicação.
    """
    app = Flask(
        __name__,
        template_folder='views/templates',
        static_folder='static',
        static_url_path='/static',
    )

    # ── Carregar configuração ──────────────────────────────────────────────
    env = env or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config_map.get(env, config_map['default']))
    if env == 'production':
        uri = resolve_production_database_uri()
        app.config['SQLALCHEMY_DATABASE_URI'] = uri
        if 'railway.app' in uri:
            app.config['_USING_PUBLIC_DB'] = True
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1,
        )

    # Pasta instance (logs/uploads locais, se necessário)
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance'), exist_ok=True)

    # ── Inicializar extensões ──────────────────────────────────────────────
    db.init_app(app)

    from .auth import init_auth
    init_auth(app)

    # ── Registrar Blueprints (Controllers) ────────────────────────────────
    _register_blueprints(app)

    # ── Banco: dev/test no boot; produção em background (health check imediato) ──
    from .bootstrap import bootstrap_database, register_db_gate, start_bootstrap_background
    if env == 'testing':
        with app.app_context():
            db.create_all()
    elif env == 'production':
        start_bootstrap_background(app, env)
        register_db_gate(app, env)
    else:
        bootstrap_database(app, env)

    # ── Registrar filtros Jinja2 personalizados ────────────────────────────
    _register_jinja_filters(app)

    # ── Context processors ────────────────────────────────────────────────
    _register_context_processors(app)

    return app


def _register_blueprints(app: Flask) -> None:
    """Registra todos os Blueprints da aplicação."""
    from .controllers.main_controller       import main_bp
    from .controllers.candidato_controller  import candidato_bp
    from .controllers.noticia_controller    import noticia_bp
    from .controllers.tendencia_controller  import tendencia_bp
    from .controllers.api_controller        import api_bp
    from .controllers.auth_controller       import auth_bp
    from .controllers.usuario_controller   import usuario_bp
    from .controllers.schema_controller    import schema_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(candidato_bp,  url_prefix='/candidatos')
    app.register_blueprint(noticia_bp,    url_prefix='/noticias')
    app.register_blueprint(tendencia_bp,  url_prefix='/tendencias')
    app.register_blueprint(api_bp,        url_prefix='/api/v1')
    app.register_blueprint(auth_bp)
    app.register_blueprint(usuario_bp)
    app.register_blueprint(schema_bp)


def _register_jinja_filters(app: Flask) -> None:
    """Filtros customizados disponíveis nos templates."""
    from datetime import datetime, timezone

    @app.template_filter('br_date')
    def br_date_filter(value):
        """Converte datetime para formato brasileiro dd/mm/aaaa."""
        if not value:
            return '—'
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        return value.strftime('%d/%m/%Y')

    @app.template_filter('br_datetime')
    def br_datetime_filter(value):
        """Converte datetime para formato dd/mm/aaaa HH:MM."""
        if not value:
            return '—'
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        return value.strftime('%d/%m/%Y %H:%M')

    @app.template_filter('tempo_relativo')
    def tempo_relativo_filter(value):
        """Retorna '2h atrás', '3 dias atrás', etc."""
        if not value:
            return '—'
        agora = datetime.now(timezone.utc).replace(tzinfo=None)
        if hasattr(value, 'tzinfo') and value.tzinfo:
            value = value.replace(tzinfo=None)
        diff = agora - value
        minutos = int(diff.total_seconds() / 60)
        if minutos < 1:
            return 'agora'
        if minutos < 60:
            return f'há {minutos}min'
        horas = minutos // 60
        if horas < 24:
            return f'há {horas}h'
        dias = horas // 24
        return f'há {dias} dias'

    @app.template_filter('pct')
    def pct_filter(value, decimals=1):
        """Formata número como porcentagem."""
        try:
            return f'{float(value):.{decimals}f}%'
        except (TypeError, ValueError):
            return '0%'

    @app.template_filter('br_number')
    def br_number_filter(value):
        """Formata número no padrão brasileiro (1.234)."""
        try:
            return f'{int(value):,}'.replace(',', '.')
        except (TypeError, ValueError):
            return str(value)

    @app.template_filter('sentimento_icon')
    def sentimento_icon_filter(value):
        icons = {
            'positivo': '😊',
            'negativo': '😟',
            'neutro':   '😐',
        }
        return icons.get(value, '—')

    @app.template_filter('tendencia_icon')
    def tendencia_icon_filter(value):
        icons = {'up': '↑', 'down': '↓', 'stable': '→'}
        return icons.get(value, '—')


def _register_context_processors(app: Flask) -> None:
    """Variáveis disponíveis em todos os templates."""
    from datetime import datetime
    from .constants import CATEGORIAS, ESTADOS, categorias_dict
    from .services import NoticiaService

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        pode_escrever = (
            current_user.is_authenticated and current_user.pode_escrever()
        )
        return {
            'ano_eleicao': 2026,
            'app_nome': 'Eleitoral2026',
            'agora': datetime.now(),
            'pode_escrever': pode_escrever,
            'categorias': CATEGORIAS,
            'categorias_labels': categorias_dict(),
            'estados': ESTADOS,
            'periodos_noticias': NoticiaService.PERIODOS,
            'temas_labels': {
                'economia':  'Economia',
                'saude':     'Saúde',
                'educacao':  'Educação',
                'violencia': 'Violência',
                'justica':   'Justiça',
                'politica':  'Política',
            },
            'temas_cores': {
                'economia':  '#10b981',
                'saude':     '#ef4444',
                'educacao':  '#3b82f6',
                'violencia': '#f59e0b',
                'justica':   '#8b5cf6',
                'politica':  '#06b6d4',
            },
        }
