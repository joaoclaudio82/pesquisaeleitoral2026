"""
Bootstrap do banco — create_all, migrate e seed com retry (Railway).
"""
import os
import time

from sqlalchemy.exc import DBAPIError, OperationalError

from config import _database_uri, rebind_database
from .database import db


def _is_connection_error(exc: BaseException) -> bool:
    if isinstance(exc, (OperationalError, DBAPIError, OSError)):
        return True
    msg = str(exc).lower()
    return 'timeout' in msg or 'connection' in msg


def _log_db_target(app) -> None:
    from urllib.parse import urlparse
    uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    parsed = urlparse(uri.replace('postgresql+psycopg://', 'postgresql://'))
    host = parsed.hostname or '(sem host)'
    port = parsed.port or 5432
    db_name = (parsed.path or '/').lstrip('/') or '?'
    print(f'[bootstrap] destino: {host}:{port}/{db_name}', flush=True)


def _try_public_url_fallback(app) -> bool:
    """Se a rede privada falhar, tenta DATABASE_PUBLIC_URL (Railway)."""
    if app.config.get('_USING_PUBLIC_DB'):
        return False
    public_uri = _database_uri(public=True)
    if not public_uri:
        return False
    current = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'railway.app' in current:
        return False
    print('[bootstrap] rede interna falhou; tentando DATABASE_PUBLIC_URL...', flush=True)
    rebind_database(app, public_uri)
    app.config['_USING_PUBLIC_DB'] = True
    return True


def _run_bootstrap_once(app, env: str) -> None:
    with app.app_context():
        from .migrate import migrate_schema
        db.create_all()
        migrate_schema()
        if env == 'production':
            from .seed import seed_database
            from .services import UsuarioService
            seed_database(gerar_historico=False)
            UsuarioService.seed_admin_padrao()


def bootstrap_database(app, env: str) -> None:
    """Inicializa schema e dados iniciais; retenta se o Postgres ainda não estiver pronto."""
    if app.config.get('_DB_READY'):
        return

    _log_db_target(app)
    last_error = None
    tried_public = False

    while True:
        max_attempts = 8
        for attempt in range(1, max_attempts + 1):
            try:
                print(f'[bootstrap] tentativa {attempt}/{max_attempts}...', flush=True)
                _run_bootstrap_once(app, env)
                app.config['_DB_READY'] = True
                print('[bootstrap] concluido.', flush=True)
                return
            except Exception as exc:
                if not _is_connection_error(exc):
                    raise
                last_error = exc
                print(f'[bootstrap] Postgres indisponivel: {exc}', flush=True)
                db.session.remove()
                db.engine.dispose()
                if attempt < max_attempts:
                    time.sleep(min(attempt * 2, 10))

        if env == 'production' and not tried_public and _try_public_url_fallback(app):
            tried_public = True
            _log_db_target(app)
            continue
        break

    if last_error:
        raise last_error
