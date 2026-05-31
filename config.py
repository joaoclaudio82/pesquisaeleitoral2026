"""
Pesquisa Eleitoral 2026 — Configurações da Aplicação
Separa ambientes: Development, Testing, Production
"""
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _database_uri(*, exigir_database_url: bool = False) -> str:
    """
    Monta a URI do PostgreSQL a partir de DATABASE_URL ou variáveis POSTGRES_*.
    Usa driver psycopg v3 (postgresql+psycopg://).

    Em produção (Railway), DATABASE_URL deve apontar para o Postgres do serviço —
    não use POSTGRES_HOST=localhost do ambiente local.
    """
    url = os.environ.get('DATABASE_URL', '').strip()
    if url:
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
    elif exigir_database_url:
        raise RuntimeError(
            'DATABASE_URL não configurada. No Railway: serviço Web → Variables → '
            'Add Reference → Postgres → DATABASE_URL. '
            'Remova POSTGRES_HOST/POSTGRES_PORT locais (localhost/5433).'
        )
    else:
        user = os.environ.get('POSTGRES_USER', 'eleitoral')
        password = os.environ.get('POSTGRES_PASSWORD', 'eleitoral')
        host = os.environ.get('POSTGRES_HOST', 'localhost')
        port = os.environ.get('POSTGRES_PORT', '5432')
        db_name = os.environ.get('POSTGRES_DB', 'eleitoral2026')
        url = f'postgresql://{user}:{password}@{host}:{port}/{db_name}'

    if url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return url


class Config:
    """Configuração base compartilhada por todos os ambientes."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'eleitoral2026-secret-key-dev')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False          # suporte a caracteres UTF-8 no JSON
    JSON_SORT_KEYS = False
    SCHEDULER_API_ENABLED = True
    # Intervalo de simulação de coleta (segundos)
    UPDATE_INTERVAL_SECONDS = int(os.environ.get('UPDATE_INTERVAL', 120))


class DevelopmentConfig(Config):
    """Ambiente de desenvolvimento local."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_ECHO = False   # True para ver queries SQL no terminal


class TestingConfig(Config):
    """Ambiente de testes automatizados."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Ambiente de produção."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _database_uri(exigir_database_url=True)


# Mapeamento de ambientes
config_map = {
    'development': DevelopmentConfig,
    'testing':     TestingConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}
