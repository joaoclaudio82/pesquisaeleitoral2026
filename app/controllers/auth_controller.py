"""
Controller: Autenticação (login / logout)
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from ..auth import safe_redirect_target
from ..services import UsuarioService

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        from flask import current_app
        if not current_app.config.get('_DB_READY'):
            flash(
                'Banco de dados ainda inicializando. Aguarde alguns segundos e tente novamente.',
                'warning',
            )
            return render_template('auth/login.html')

        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')

        if not email or not senha:
            flash('Informe e-mail e senha.', 'error')
            return render_template('auth/login.html')

        usuario = UsuarioService.autenticar(email, senha)
        if not usuario:
            flash('E-mail ou senha incorretos.', 'error')
            return render_template('auth/login.html')

        login_user(usuario, remember=bool(request.form.get('lembrar')))
        flash(f'Bem-vindo(a), {usuario.nome}!', 'success')

        destino = safe_redirect_target(request.args.get('next'))
        return redirect(destino)

    return render_template('auth/login.html')


@auth_bp.get('/logout')
def logout():
    logout_user()
    flash('Sessão encerrada.', 'info')
    return redirect(url_for('auth.login'))
