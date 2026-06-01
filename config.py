"""
Pesquisa Eleitoral 2026 — Configurações da Aplicação
Separa ambientes: Development, Testing, Production
"""
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _normalize_psycopg_url(url: str, *, ssl: bool = False) -> str:
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    if url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    if ssl and 'sslmode=' not in url:
        sep = '&' if '?' in url else '?'
        url = f'{url}{sep}sslmode=require'
    return url


def _database_uri(*, exigir_database_url: bool = False, public: bool = False) -> str:
    """
    Monta a URI do PostgreSQL a partir de DATABASE_URL ou variáveis POSTGRES_*.
    Usa driver psycopg v3 (postgresql+psycopg://).

    Em produção (Railway), DATABASE_URL deve apontar para o Postgres do serviço —
    não use POSTGRES_HOST=localhost do ambiente local.
    """
    if public:
        url = os.environ.get('DATABASE_PUBLIC_URL', '').strip()
        if not url and exigir_database_url:
            raise RuntimeError('DATABASE_PUBLIC_URL não configurada.')
        return _normalize_psycopg_url(url, ssl=True) if url else ''

    url = os.environ.get('DATABASE_URL', '').strip()
    if url:
        return _normalize_psycopg_url(url)
    if exigir_database_url:
        raise RuntimeError(
            'DATABASE_URL não configurada. No Railway: serviço Web → Variables → '
            'Add Reference → Postgres → DATABASE_URL e DATABASE_PUBLIC_URL. '
            'Remova POSTGRES_HOST/POSTGRES_PORT locais (localhost/5433).'
        )

    user = os.environ.get('POSTGRES_USER', 'eleitoral')
    password = os.environ.get('POSTGRES_PASSWORD', 'eleitoral')
    host = os.environ.get('POSTGRES_HOST', 'localhost')
    port = os.environ.get('POSTGRES_PORT', '5432')
    db_name = os.environ.get('POSTGRES_DB', 'eleitoral2026')
    return _normalize_psycopg_url(
        f'postgresql://{user}:{password}@{host}:{port}/{db_name}'
    )


def _use_public_database() -> bool:
    return os.environ.get('USE_PUBLIC_DATABASE', '').strip().lower() in ('1', 'true', 'yes')


def resolve_production_database_uri() -> str:
    """
    URI de producao. Padrao: DATABASE_URL (rede interna Railway).
    USE_PUBLIC_DATABASE=1 usa DATABASE_PUBLIC_URL quando configurada;
    se a URL publica nao existir, faz fallback para DATABASE_URL (nao derruba o boot).
    """
    public = _database_uri(public=True)
    if _use_public_database() and public:
        return public
    if _use_public_database() and not public:
        print(
            '[config] USE_PUBLIC_DATABASE=1 mas DATABASE_PUBLIC_URL ausente; '
            'usando DATABASE_URL. Remova USE_PUBLIC_DATABASE ou adicione a referencia '
            'Postgres → DATABASE_PUBLIC_URL no servico Web.',
            flush=True,
        )
    return _database_uri(exigir_database_url=True)


def rebind_database(app, uri: str) -> None:
    """Troca a URI do banco em runtime (fallback Railway public URL)."""
    from app.database import db
    app.config['SQLALCHEMY_DATABASE_URI'] = uri
    db.session.remove()
    db.engine.dispose()


class Config:
    """Configuração base compartilhada por todos os ambientes."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'eleitoral2026-secret-key-dev')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {'connect_timeout': 10},
    }
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
    PREFERRED_URL_SCHEME = 'https'
    SESSION_COOKIE_SECURE = True
    # URI definida em create_app() — exige DATABASE_URL só ao subir em produção


# Mapeamento de ambientes
config_map = {
    'development': DevelopmentConfig,
    'testing':     TestingConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}
