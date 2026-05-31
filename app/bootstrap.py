"""
Bootstrap do banco — create_all, migrate e seed com retry (Railway).
"""
import time

from sqlalchemy.exc import DBAPIError, OperationalError

from .database import db


def _is_connection_error(exc: BaseException) -> bool:
    if isinstance(exc, (OperationalError, DBAPIError, OSError)):
        return True
    msg = str(exc).lower()
    return 'timeout' in msg or 'connection' in msg


def bootstrap_database(app, env: str) -> None:
    """Inicializa schema e dados iniciais; retenta se o Postgres ainda não estiver pronto."""
    if app.config.get('_DB_READY'):
        return

    max_attempts = 15
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            print(f'[bootstrap] tentativa {attempt}/{max_attempts}...', flush=True)
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
            print('[bootstrap] concluido.', flush=True)
            return
        except Exception as exc:
            if not _is_connection_error(exc):
                raise
            last_error = exc
            print(f'[bootstrap] Postgres indisponivel: {exc}', flush=True)
            db.session.remove()
            db.engine.dispose()
            if attempt == max_attempts:
                raise
            time.sleep(min(attempt * 2, 10))

    if last_error:
        raise last_error
