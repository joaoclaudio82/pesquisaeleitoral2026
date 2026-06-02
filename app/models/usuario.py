"""
Model: Usuario
Autenticação e controle de acesso (admin / visualizador).
"""
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..database import db

PAPEIS = ('admin', 'visualizador', 'consultor', 'campanha', 'partido')


class Usuario(UserMixin, db.Model):
    """
    Tabela: usuarios

    papéis:
        - admin: pode inserir, editar e excluir dados
        - visualizador: somente leitura
    """
    __tablename__ = 'usuarios'

    id            = db.Column(db.Integer, primary_key=True)
    nome          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    papel         = db.Column(db.String(20), nullable=False, default='visualizador')
    ativo         = db.Column(db.Boolean, default=True, nullable=False)
    criado_em     = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_senha(self, senha: str) -> None:
        self.password_hash = generate_password_hash(senha)

    def verificar_senha(self, senha: str) -> bool:
        return check_password_hash(self.password_hash, senha)

    @property
    def is_admin(self) -> bool:
        return self.papel == 'admin'

    def pode_escrever(self) -> bool:
        return self.is_admin and self.ativo

    @property
    def papel_label(self) -> str:
        labels = {
            'admin': 'Administrador',
            'visualizador': 'Visualizador',
            'consultor': 'Consultor',
            'campanha': 'Equipe de Campanha',
            'partido': 'Equipe de Partido',
        }
        return labels.get(self.papel, self.papel.capitalize())

    def to_dict(self) -> dict:
        return {
            'id':          self.id,
            'nome':        self.nome,
            'email':       self.email,
            'papel':       self.papel,
            'papel_label': self.papel_label,
            'ativo':       self.ativo,
            'criado_em':   self.criado_em.isoformat() if self.criado_em else None,
        }
