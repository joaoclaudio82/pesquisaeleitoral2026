"""
Model: Noticia
Representa uma notícia coletada e analisada pelo sistema.
"""
from datetime import datetime
from ..database import db

# Valores permitidos para validação no nível de aplicação
SENTIMENTOS  = ('positivo', 'negativo', 'neutro')
TEMAS_VALIDOS = ('economia', 'saude', 'educacao', 'violencia', 'justica', 'politica')


class Noticia(db.Model):
    """
    Tabela: noticias

    Relacionamentos:
        - candidato: Candidato — candidato mencionado na notícia
    """
    __tablename__ = 'noticias'

    # ── Chave primária ─────────────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)

    # ── FK ────────────────────────────────────────────────────────────────
    candidato_id = db.Column(db.Integer, db.ForeignKey('candidatos.id'),
                             nullable=False, index=True)

    # ── Conteúdo ───────────────────────────────────────────────────────────
    titulo   = db.Column(db.String(300), nullable=False)
    resumo   = db.Column(db.Text,        nullable=False, default='')
    url      = db.Column(db.String(500), nullable=True)

    # ── Metadados ─────────────────────────────────────────────────────────
    fonte        = db.Column(db.String(100), nullable=False, default='')
    sentimento   = db.Column(db.String(15),  nullable=False, default='neutro',
                             index=True)
    tema         = db.Column(db.String(20),  nullable=False, default='politica',
                             index=True)
    relevancia   = db.Column(db.Integer,     nullable=False, default=50)   # 0-100
    publicada_em = db.Column(db.DateTime,    nullable=False,
                             default=datetime.utcnow, index=True)
    coletada_em  = db.Column(db.DateTime,    default=datetime.utcnow)

    # ── Relacionamento ────────────────────────────────────────────────────
    candidato = db.relationship('Candidato', back_populates='noticias')

    # ── Propriedades calculadas ────────────────────────────────────────────
    @property
    def sentimento_label(self) -> str:
        labels = {'positivo': 'Positivo', 'negativo': 'Negativo', 'neutro': 'Neutro'}
        return labels.get(self.sentimento, self.sentimento.capitalize())

    @property
    def sentimento_cor(self) -> str:
        cores = {
            'positivo': '#10b981',
            'negativo': '#ef4444',
            'neutro':   '#f59e0b',
        }
        return cores.get(self.sentimento, '#94a3b8')

    @property
    def tempo_relativo(self) -> str:
        agora = datetime.utcnow()
        diff  = agora - self.publicada_em
        mins  = int(diff.total_seconds() / 60)
        if mins < 1:
            return 'agora'
        if mins < 60:
            return f'há {mins}min'
        horas = mins // 60
        if horas < 24:
            return f'há {horas}h'
        return f'há {horas // 24} dias'

    # ── Serialização ──────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        cand = self.candidato
        return {
            'id':            self.id,
            'candidato_id':  self.candidato_id,
            'candidato':     cand.nome_abrev if cand else '—',
            'candidato_cor': cand.cor if cand else '#6366f1',
            'titulo':        self.titulo,
            'resumo':        self.resumo,
            'url':           self.url,
            'fonte':         self.fonte,
            'sentimento':    self.sentimento,
            'tema':          self.tema,
            'relevancia':    self.relevancia,
            'publicada_em':  self.publicada_em.isoformat() if self.publicada_em else None,
            'tempo_relativo': self.tempo_relativo,
        }

    # ── Dunder ────────────────────────────────────────────────────────────
    def __repr__(self) -> str:
        return f'<Noticia id={self.id} sentimento={self.sentimento} tema={self.tema}>'
