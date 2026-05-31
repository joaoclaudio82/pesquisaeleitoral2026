"""
Model: Candidato
Representa um candidato monitorado pelo sistema, por cargo e estado.
"""
from datetime import datetime
from ..constants import categoria_label as _categoria_label, uf_label as _uf_label
from ..database import db


class Candidato(db.Model):
    """
    Tabela: candidatos

    Relacionamentos:
        - noticias  : List[Noticia]  — notícias que mencionam este candidato
        - historicos: List[Historico] — série histórica diária de métricas
    """
    __tablename__ = 'candidatos'

    # ── Chave primária ─────────────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)

    # ── Dados pessoais / políticos ─────────────────────────────────────────
    slug        = db.Column(db.String(80),  unique=True, nullable=False, index=True)
    nome        = db.Column(db.String(120), nullable=False)
    nome_abrev  = db.Column(db.String(40),  nullable=False)
    partido     = db.Column(db.String(30),  nullable=False)
    cor         = db.Column(db.String(10),  nullable=False, default='#6366f1')
    foto_url    = db.Column(db.String(500), nullable=True)  # path em static/ ou URL

    # ── Escopo eleitoral ───────────────────────────────────────────────────
    categoria   = db.Column(db.String(30),  nullable=False, default='presidente', index=True)
    uf          = db.Column(db.String(2),   nullable=True,  index=True)  # None = nacional

    # ── Métricas atuais (%) ────────────────────────────────────────────────
    aprovacao   = db.Column(db.Float, nullable=False, default=0.0)
    rejeicao    = db.Column(db.Float, nullable=False, default=0.0)
    neutro      = db.Column(db.Float, nullable=False, default=0.0)

    # ── Contadores ────────────────────────────────────────────────────────
    mencoes     = db.Column(db.Integer, nullable=False, default=0)

    # ── Tendência: 'up' | 'down' | 'stable' ───────────────────────────────
    tendencia   = db.Column(db.String(10), nullable=False, default='stable')

    # ── Temas principais (CSV: "economia,saude,politica") ──────────────────
    temas_csv   = db.Column(db.String(200), nullable=False, default='politica')

    # ── Auditoria ──────────────────────────────────────────────────────────
    criado_em   = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow,
                              onupdate=datetime.utcnow)
    ativo       = db.Column(db.Boolean, default=True, nullable=False)

    # ── Relacionamentos ────────────────────────────────────────────────────
    noticias    = db.relationship('Noticia',   back_populates='candidato',
                                  lazy='dynamic', cascade='all, delete-orphan')
    historicos  = db.relationship('Historico', back_populates='candidato',
                                  lazy='dynamic', cascade='all, delete-orphan',
                                  order_by='Historico.data')

    # ── Propriedades calculadas ────────────────────────────────────────────
    @property
    def temas(self) -> list[str]:
        """Retorna lista de temas a partir do campo CSV."""
        if not self.temas_csv:
            return []
        return [t.strip() for t in self.temas_csv.split(',') if t.strip()]

    @temas.setter
    def temas(self, lista: list[str]) -> None:
        self.temas_csv = ','.join(lista)

    @property
    def tem_foto(self) -> bool:
        return bool(self.foto_url and self.foto_url.strip())

    @property
    def iniciais(self) -> str:
        """Primeiras duas letras do nome abreviado."""
        return self.nome_abrev[:2].upper()

    @property
    def total_noticias(self) -> int:
        return self.noticias.count()

    @property
    def noticias_positivas(self) -> int:
        return self.noticias.filter_by(sentimento='positivo').count()

    @property
    def noticias_negativas(self) -> int:
        return self.noticias.filter_by(sentimento='negativo').count()

    @property
    def tendencia_label(self) -> str:
        labels = {'up': 'Alta', 'down': 'Queda', 'stable': 'Estável'}
        return labels.get(self.tendencia, '—')

    @property
    def categoria_label(self) -> str:
        return _categoria_label(self.categoria)

    @property
    def uf_label(self) -> str:
        return _uf_label(self.uf)

    @property
    def escopo_label(self) -> str:
        if self.uf:
            return f'{self.categoria_label} — {self.uf}'
        return self.categoria_label

    # ── Serialização ──────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            'id':          self.id,
            'slug':        self.slug,
            'nome':        self.nome,
            'nome_abrev':  self.nome_abrev,
            'partido':     self.partido,
            'cor':         self.cor,
            'foto_url':    self.foto_url,
            'tem_foto':    self.tem_foto,
            'categoria':   self.categoria,
            'categoria_label': self.categoria_label,
            'uf':          self.uf,
            'uf_label':    self.uf_label,
            'escopo_label': self.escopo_label,
            'aprovacao':   round(self.aprovacao, 1),
            'rejeicao':    round(self.rejeicao, 1),
            'neutro':      round(self.neutro, 1),
            'mencoes':     self.mencoes,
            'tendencia':   self.tendencia,
            'temas':       self.temas,
            'total_noticias': self.total_noticias,
            'noticias_positivas': self.noticias_positivas,
            'noticias_negativas': self.noticias_negativas,
        }

    # ── Dunder ────────────────────────────────────────────────────────────
    def __repr__(self) -> str:
        escopo = f'/{self.uf}' if self.uf else ''
        return f'<Candidato {self.nome_abrev} ({self.categoria}{escopo})>'
