"""
Migrações leves de schema (sem Flask-Migrate).
Adiciona colunas novas em bancos já existentes.
"""
from sqlalchemy import inspect, text

from .database import db


# Ajuste de dados para registros do seed em bancos já populados
_BACKFILL_CANDIDATOS = {
    'tarcisio-de-freitas': ('governador', 'SP'),
    'marina-silva':        ('senador', 'AC'),
    'flavio-dino':         ('senador', 'MA'),
}


def migrate_schema() -> None:
    """Aplica alterações incrementais no schema."""
    inspector = inspect(db.engine)
    if 'candidatos' not in inspector.get_table_names():
        return

    colunas = {c['name'] for c in inspector.get_columns('candidatos')}
    dialect = db.engine.dialect.name

    if 'categoria' not in colunas:
        if dialect == 'postgresql':
            db.session.execute(text(
                "ALTER TABLE candidatos "
                "ADD COLUMN categoria VARCHAR(30) NOT NULL DEFAULT 'presidente'"
            ))
        else:
            db.session.execute(text(
                "ALTER TABLE candidatos "
                "ADD COLUMN categoria VARCHAR(30) NOT NULL DEFAULT 'presidente'"
            ))

    if 'uf' not in colunas:
        db.session.execute(text(
            "ALTER TABLE candidatos ADD COLUMN uf VARCHAR(2)"
        ))

    colunas = {c['name'] for c in inspector.get_columns('candidatos')}
    if 'foto_url' not in colunas:
        db.session.execute(text(
            "ALTER TABLE candidatos ADD COLUMN foto_url VARCHAR(500)"
        ))

    db.session.commit()
    _backfill_categorias()


def _backfill_categorias() -> None:
    """Atualiza cargo/UF de candidatos do seed em bancos antigos."""
    from .models import Candidato

    for slug, (categoria, uf) in _BACKFILL_CANDIDATOS.items():
        cand = Candidato.query.filter_by(slug=slug).first()
        if cand and cand.categoria == 'presidente' and cand.uf is None:
            cand.categoria = categoria
            cand.uf = uf

    db.session.commit()
