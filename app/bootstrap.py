"""
Bootstrap do banco — create_all, migrate e seed com retry (Railway).
"""
import time

from sqlalchemy.exc import OperationalError

from .database import db


def bootstrap_database(app, env: str) -> None:
    """Inicializa schema e dados iniciais; retenta se o Postgres ainda não estiver pronto."""
    if app.config.get('_DB_READY'):
        return

    max_attempts = 10
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            with app.app_context():
                from .migrate import migrate_schema
                db.create_all()
                migrate_schema()
                if env == 'production':
                    from .seed import seed_database
                    from .services import UsuarioService
                    seed_database(gerar_historico=False)
                    UsuarioService.seed_admin_padrao()
            app.config['_DB_READY'] = True
            return
        except OperationalError as exc:
            last_error = exc
            db.session.remove()
            db.engine.dispose()
            if attempt == max_attempts:
                raise
            time.sleep(min(attempt * 2, 15))

    if last_error:
        raise last_error


def register_lazy_bootstrap(app, env: str) -> None:
    """Em produção, adia conexão ao Postgres até a primeira requisição (exceto /health)."""

    @app.before_request
    def _ensure_db_ready():
        if app.config.get('_DB_READY'):
            return None
        from flask import request
        endpoint = request.endpoint or ''
        if endpoint in ('main.health',) or endpoint.startswith('static'):
            return None
        bootstrap_database(app, env)
        return None
