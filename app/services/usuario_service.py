"""
Service: UsuarioService
CRUD e autenticação de usuários.
"""
import os
import re

from ..database import db
from ..models.usuario import PAPEIS, Usuario

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class UsuarioService:
    PAPEIS_VALIDOS = PAPEIS
    SENHA_MIN = 6

    @staticmethod
    def listar_todos() -> list[Usuario]:
        return Usuario.query.order_by(Usuario.nome).all()

    @staticmethod
    def buscar_por_id(usuario_id: int) -> Usuario | None:
        return Usuario.query.get(usuario_id)

    @staticmethod
    def buscar_por_email(email: str) -> Usuario | None:
        return Usuario.query.filter_by(email=email.strip().lower()).first()

    @staticmethod
    def autenticar(email: str, senha: str) -> Usuario | None:
        usuario = UsuarioService.buscar_por_email(email)
        if not usuario or not usuario.ativo:
            return None
        if not usuario.verificar_senha(senha):
            return None
        return usuario

    @staticmethod
    def _validar_email(email: str) -> str:
        email = email.strip().lower()
        if not email or not _EMAIL_RE.match(email):
            raise ValueError('Informe um e-mail válido.')
        return email

    @staticmethod
    def _validar_senha(senha: str, obrigatoria: bool = True) -> None:
        if not obrigatoria and not senha:
            return
        if len(senha) < UsuarioService.SENHA_MIN:
            raise ValueError(
                f'A senha deve ter pelo menos {UsuarioService.SENHA_MIN} caracteres.'
            )

    @staticmethod
    def criar(nome: str, email: str, senha: str, papel: str = 'visualizador') -> Usuario:
        nome = nome.strip()
        email = UsuarioService._validar_email(email)
        UsuarioService._validar_senha(senha)

        if not nome:
            raise ValueError('O nome é obrigatório.')
        if papel not in PAPEIS:
            raise ValueError('Papel inválido.')
        if UsuarioService.buscar_por_email(email):
            raise ValueError('Este e-mail já está cadastrado.')

        usuario = Usuario(nome=nome, email=email, papel=papel, ativo=True)
        usuario.set_senha(senha)
        db.session.add(usuario)
        db.session.commit()
        return usuario

    @staticmethod
    def atualizar(
        usuario_id: int,
        nome: str,
        email: str,
        papel: str,
        ativo: bool,
        nova_senha: str | None = None,
    ) -> Usuario:
        usuario = UsuarioService.buscar_por_id(usuario_id)
        if not usuario:
            raise ValueError('Usuário não encontrado.')

        nome = nome.strip()
        email = UsuarioService._validar_email(email)
        if not nome:
            raise ValueError('O nome é obrigatório.')
        if papel not in PAPEIS:
            raise ValueError('Papel inválido.')

        outro = Usuario.query.filter(
            Usuario.email == email,
            Usuario.id != usuario_id,
        ).first()
        if outro:
            raise ValueError('Este e-mail já está em uso por outro usuário.')

        if usuario.is_admin and not ativo:
            admins_ativos = Usuario.query.filter_by(papel='admin', ativo=True).count()
            if admins_ativos <= 1:
                raise ValueError('Não é possível desativar o único administrador ativo.')

        if usuario.is_admin and papel != 'admin':
            admins = Usuario.query.filter_by(papel='admin', ativo=True).count()
            if admins <= 1:
                raise ValueError('Deve existir pelo menos um administrador ativo.')

        usuario.nome = nome
        usuario.email = email
        usuario.papel = papel
        usuario.ativo = ativo

        if nova_senha:
            UsuarioService._validar_senha(nova_senha)
            usuario.set_senha(nova_senha)

        db.session.commit()
        return usuario

    @staticmethod
    def excluir(usuario_id: int, usuario_atual_id: int) -> bool:
        if usuario_id == usuario_atual_id:
            raise ValueError('Você não pode excluir sua própria conta.')

        usuario = UsuarioService.buscar_por_id(usuario_id)
        if not usuario:
            return False

        if usuario.is_admin:
            admins = Usuario.query.filter_by(papel='admin').count()
            if admins <= 1:
                raise ValueError('Não é possível excluir o único administrador.')

        db.session.delete(usuario)
        db.session.commit()
        return True

    @staticmethod
    def seed_admin_padrao() -> Usuario | None:
        """Cria administrador inicial se não houver usuários."""
        if Usuario.query.first():
            return None

        email = os.environ.get('ADMIN_EMAIL', 'admin@eleitoral.local').strip().lower()
        senha = os.environ.get('ADMIN_PASSWORD', 'admin123')
        nome  = os.environ.get('ADMIN_NOME', 'Administrador')

        usuario = Usuario(nome=nome, email=email, papel='admin', ativo=True)
        usuario.set_senha(senha)
        db.session.add(usuario)
        db.session.commit()
        print(f'✅ Usuário admin criado: {email} (altere a senha em produção)')
        return usuario
