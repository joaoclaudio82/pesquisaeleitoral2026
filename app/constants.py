"""
Constantes eleitorais: cargos, estados e helpers.
"""

CATEGORIAS = [
    ('presidente',         'Presidente'),
    ('governador',         'Governador'),
    ('senador',            'Senador'),
    ('deputado_federal',   'Deputado Federal'),
    ('deputado_estadual',  'Deputado Estadual'),
    ('prefeito',           'Prefeito'),
    ('vereador',           'Vereador'),
]

CATEGORIAS_NACIONAIS = {'presidente'}

ESTADOS = [
    ('AC', 'Acre'),
    ('AL', 'Alagoas'),
    ('AP', 'Amapá'),
    ('AM', 'Amazonas'),
    ('BA', 'Bahia'),
    ('CE', 'Ceará'),
    ('DF', 'Distrito Federal'),
    ('ES', 'Espírito Santo'),
    ('GO', 'Goiás'),
    ('MA', 'Maranhão'),
    ('MT', 'Mato Grosso'),
    ('MS', 'Mato Grosso do Sul'),
    ('MG', 'Minas Gerais'),
    ('PA', 'Pará'),
    ('PB', 'Paraíba'),
    ('PR', 'Paraná'),
    ('PE', 'Pernambuco'),
    ('PI', 'Piauí'),
    ('RJ', 'Rio de Janeiro'),
    ('RN', 'Rio Grande do Norte'),
    ('RS', 'Rio Grande do Sul'),
    ('RO', 'Rondônia'),
    ('RR', 'Roraima'),
    ('SC', 'Santa Catarina'),
    ('SP', 'São Paulo'),
    ('SE', 'Sergipe'),
    ('TO', 'Tocantins'),
]


def categoria_requer_uf(categoria: str) -> bool:
    return categoria not in CATEGORIAS_NACIONAIS


def categoria_label(categoria: str) -> str:
    return dict(CATEGORIAS).get(categoria, categoria)


def uf_label(uf: str | None) -> str:
    if not uf:
        return 'Nacional'
    return dict(ESTADOS).get(uf, uf)


def categorias_dict() -> dict[str, str]:
    return dict(CATEGORIAS)


def estados_dict() -> dict[str, str]:
    return dict(ESTADOS)
