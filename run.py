"""
Pesquisa Eleitoral 2026 — Ponto de entrada da aplicação
Execute: python run.py
Gunicorn (Railway): gunicorn --preload run:app
"""
import os

from app import create_app
from app.bootstrap import bootstrap_database
from app.seed import seed_database

app = create_app()

if os.environ.get('FLASK_ENV') == 'production':
    bootstrap_database(app, 'production')

if __name__ == '__main__':
    with app.app_context():
        seed_database()
        from app.services import UsuarioService
        UsuarioService.seed_admin_padrao()
    app.run(debug=True, host='0.0.0.0', port=5000)
