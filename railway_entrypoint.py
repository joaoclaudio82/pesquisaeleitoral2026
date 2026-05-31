"""
Entrypoint Railway — aguarda Postgres, inicializa banco e sobe Gunicorn.
Evita bootstrap bloqueante na primeira requisição HTTP (499/502).
"""
import os
import sys


def main() -> None:
    os.environ.setdefault('FLASK_ENV', 'production')

    from app import create_app
    from app.bootstrap import bootstrap_database

    app = create_app('production')
    print('[railway] Aguardando Postgres e inicializando banco...', flush=True)
    bootstrap_database(app, 'production')
    print('[railway] Banco pronto. Iniciando Gunicorn...', flush=True)

    port = os.environ.get('PORT', '8080')
    os.execvp(
        'gunicorn',
        [
            'gunicorn',
            '--bind', f'0.0.0.0:{port}',
            '--workers', '2',
            '--timeout', '120',
            '--graceful-timeout', '30',
            '--preload',
            'run:app',
        ],
    )


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'[railway] Falha ao iniciar: {exc}', file=sys.stderr, flush=True)
        raise
