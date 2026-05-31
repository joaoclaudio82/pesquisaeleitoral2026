"""
Controller: Usuários — gestão de contas (somente admin).
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from ..auth import admin_required
from ..services import UsuarioService

usuario_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')


@usuario_bp.get('/')
@admin_required
def listar():
    usuarios = UsuarioService.listar_todos()
    return render_template('usuarios/lista.html', usuarios=usuarios)


@usuario_bp.route('/novo', methods=['GET', 'POST'])
@admin_required
def criar():
    if request.method == 'POST':
        try:
            UsuarioService.criar(
                nome=request.form.get('nome', ''),
                email=request.form.get('email', ''),
                senha=request.form.get('senha', ''),
                papel=request.form.get('papel', 'visualizador'),
            )
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('usuarios.criar'))

        flash('Usuário cadastrado com sucesso.', 'success')
        return redirect(url_for('usuarios.listar'))

    return render_template(
        'usuarios/form.html',
        usuario=None,
        papeis=UsuarioService.PAPEIS_VALIDOS,
    )


@usuario_bp.route('/<int:usuario_id>/editar', methods=['GET', 'POST'])
@admin_required
def editar(usuario_id: int):
    usuario = UsuarioService.buscar_por_id(usuario_id)
    if not usuario:
        flash('Usuário não encontrado.', 'error')
        return redirect(url_for('usuarios.listar'))

    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha', '').strip() or None
        try:
            UsuarioService.atualizar(
                usuario_id=usuario_id,
                nome=request.form.get('nome', ''),
                email=request.form.get('email', ''),
                papel=request.form.get('papel', 'visualizador'),
                ativo=bool(request.form.get('ativo')),
                nova_senha=nova_senha,
            )
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('usuarios.editar', usuario_id=usuario_id))

        flash('Usuário atualizado.', 'success')
        return redirect(url_for('usuarios.listar'))

    return render_template(
        'usuarios/form.html',
        usuario=usuario,
        papeis=UsuarioService.PAPEIS_VALIDOS,
    )


@usuario_bp.post('/<int:usuario_id>/excluir')
@admin_required
def excluir(usuario_id: int):
    try:
        if UsuarioService.excluir(usuario_id, current_user.id):
            flash('Usuário excluído.', 'success')
        else:
            flash('Usuário não encontrado.', 'error')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('usuarios.listar'))
