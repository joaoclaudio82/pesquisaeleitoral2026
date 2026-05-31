"""
Model: Historico
Armazena a série histórica diária de métricas de cada candidato.
Um registro por candidato por dia.
"""
from datetime import datetime, date
from ..database import db


class Historico(db.Model):
    """
    Tabela: historicos

    Relacionamentos:
        - candidato: Candidato — candidato dono desta série
    """
    __tablename__ = 'historicos'
    __table_args__ = (
        db.UniqueConstraint('candidato_id', 'data', name='uq_candidato_data'),
    )

    # ── Chave primária ─────────────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)

    # ── FK ────────────────────────────────────────────────────────────────
    candidato_id = db.Column(db.Integer, db.ForeignKey('candidatos.id'),
                             nullable=False, index=True)

    # ── Data do registro ──────────────────────────────────────────────────
    data = db.Column(db.Date, nullable=False, index=True, default=date.today)

    # ── Métricas (%) ──────────────────────────────────────────────────────
    aprovacao  = db.Column(db.Float, nullable=False, default=0.0)
    rejeicao   = db.Column(db.Float, nullable=False, default=0.0)
    neutro     = db.Column(db.Float, nullable=False, default=0.0)
    mencoes    = db.Column(db.Integer, nullable=False, default=0)

    # ── Auditoria ──────────────────────────────────────────────────────────
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Relacionamento ────────────────────────────────────────────────────
    candidato = db.relationship('Candidato', back_populates='historicos')

    # ── Serialização ──────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            'id':           self.id,
            'candidato_id': self.candidato_id,
            'data':         self.data.isoformat() if self.data else None,
            'data_br':      self.data.strftime('%d/%m') if self.data else '—',
            'aprovacao':    round(self.aprovacao, 1),
            'rejeicao':     round(self.rejeicao, 1),
            'neutro':       round(self.neutro, 1),
            'mencoes':      self.mencoes,
        }

    # ── Dunder ────────────────────────────────────────────────────────────
    def __repr__(self) -> str:
        return (f'<Historico candidato_id={self.candidato_id} '
                f'data={self.data} aprovacao={self.aprovacao:.1f}%>')
