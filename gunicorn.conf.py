"""
Config Gunicorn — bootstrap do banco em cada worker (compatível com --preload).
Sem post_fork, _DB_READY fica True só no master e os workers bloqueiam para sempre.
"""
import os


def post_fork(server, worker):
    os.environ.setdefault('FLASK_ENV', 'production')
    from run import app
    from app.bootstrap import bootstrap_database

    print(f'[bootstrap] worker pid={worker.pid} iniciando...', flush=True)
    try:
        bootstrap_database(app, 'production')
    except Exception as exc:
        print(f'[bootstrap] worker pid={worker.pid} falhou: {exc}', flush=True)
