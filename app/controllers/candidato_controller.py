"""
Controller: Candidatos
CRUD de candidatos e página de detalhe.
"""
from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, abort, current_app)
from ..constants import CATEGORIAS, ESTADOS, categoria_requer_uf
from ..services import CandidatoService, NoticiaService, HistoricoService, DescobertaService

candidato_bp = Blueprint('candidatos', __name__)

TEMAS_DISPONIVEIS = [
    ('economia',  'Economia'),
    ('saude',     'Saúde'),
    ('educacao',  'Educação'),
    ('violencia', 'Violência'),
    ('justica',   'Justiça'),
    ('politica',  'Política'),
]


def _filtros_request():
    categoria = request.args.get('categoria', '').strip() or None
    uf = request.args.get('uf', '').strip().upper() or None
    return categoria, uf


def _static_root() -> str:
    return current_app.static_folder


def _dados_formulario() -> dict | None:
    """Lê e valida o POST do formulário. Retorna None se houver erro (flash já definido)."""
    nome       = request.form.get('nome', '').strip()
    nome_abrev = request.form.get('nome_abrev', '').strip()
    partido    = request.form.get('partido', '').strip()
    categoria  = request.form.get('categoria', 'presidente').strip()
    uf         = request.form.get('uf', '').strip().upper() or None
    cor        = request.form.get('cor', '#6366f1').strip()
    temas      = request.form.getlist('temas')

    if not nome:
        flash('O nome do candidato é obrigatório.', 'error')
        return None
    if not partido:
        flash('O partido é obrigatório.', 'error')
        return None
    if categoria not in CandidatoService.CATEGORIAS_VALIDAS:
        flash('Selecione um cargo válido.', 'error')
        return None
    if categoria_requer_uf(categoria) and not uf:
        flash('Selecione o estado (UF) para este cargo.', 'error')
        return None

    return {
        'nome':       nome,
        'nome_abrev': nome_abrev,
        'partido':    partido,
        'categoria':  categoria,
        'uf':         uf,
        'cor':        cor,
        'temas':      temas,
    }


def _render_form(candidato=None, **extra):
    return render_template(
        'candidatos/form.html',
        candidato=candidato,
        temas_disponiveis=TEMAS_DISPONIVEIS,
        categorias=CATEGORIAS,
        estados=ESTADOS,
        **extra,
    )


@candidato_bp.get('/')
def listar():
    """GET /candidatos/ — lista todos os candidatos."""
    termo = request.args.get('q', '').strip()
    categoria, uf = _filtros_request()

    if termo:
        candidatos = CandidatoService.buscar(termo, categoria=categoria, uf=uf)
    else:
        candidatos = CandidatoService.listar_todos(categoria=categoria, uf=uf)

    return render_template(
        'candidatos/lista.html',
        candidatos=candidatos,
        termo=termo,
        filtro_categoria=categoria,
        filtro_uf=uf,
    )


@candidato_bp.route('/descobrir', methods=['GET', 'POST'])
def descobrir():
    """GET/POST — busca candidatos prováveis na web e importa automaticamente."""
    if request.method == 'POST':
        acao = request.form.get('acao', 'importar')
        categoria = request.form.get('categoria', 'presidente').strip()
        uf = request.form.get('uf', '').strip().upper() or None
        min_mencoes = request.form.get('min_mencoes', 2, type=int)
        max_resultados = request.form.get('max_resultados', 10, type=int)
        coletar_noticias = request.form.get('coletar_noticias') == 'on'
        dias_coleta = request.form.get('dias_coleta', 14, type=int)

        try:
            if acao == 'preview':
                preview = DescobertaService.analisar(
                    categoria=categoria,
                    uf=uf,
                    min_mencoes=min_mencoes,
                    max_resultados=max_resultados,
                )
                return render_template(
                    'candidatos/descobrir.html',
                    categorias=CATEGORIAS,
                    estados=ESTADOS,
                    preview=preview,
                    form=request.form,
                )

            resultado = DescobertaService.importar(
                categoria=categoria,
                uf=uf,
                min_mencoes=min_mencoes,
                max_resultados=max_resultados,
                coletar_noticias=coletar_noticias,
                dias_coleta=dias_coleta,
                static_root=_static_root(),
            )
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('candidatos.descobrir'))

        n = len(resultado['importados'])
        if n:
            flash(
                f'{n} candidato(s) importado(s) da web. '
                f'{resultado["noticias_coletadas"]} notícia(s) coletada(s).',
                'success',
            )
        else:
            flash(
                'Nenhum candidato novo encontrado. Tente outro cargo/UF ou reduza o mínimo de menções.',
                'warning',
            )
        return render_template(
            'candidatos/descobrir.html',
            categorias=CATEGORIAS,
            estados=ESTADOS,
            resultado=resultado,
            form=request.form,
        )

    return render_template(
        'candidatos/descobrir.html',
        categorias=CATEGORIAS,
        estados=ESTADOS,
    )


@candidato_bp.get('/<slug>')
def detalhe(slug: str):
    """GET /candidatos/<slug> — detalhe de um candidato."""
    candidato = CandidatoService.buscar_por_slug(slug)
    if not candidato:
        abort(404)

    noticias  = NoticiaService.por_candidato(candidato.id, limite=20)
    historico = HistoricoService.obter(candidato.id, dias=60)
    sentimentos = {
        'positivo': sum(1 for n in noticias if n.sentimento == 'positivo'),
        'negativo': sum(1 for n in noticias if n.sentimento == 'negativo'),
        'neutro':   sum(1 for n in noticias if n.sentimento == 'neutro'),
    }

    historico_labels  = [h.data.strftime('%d/%m') for h in historico]
    historico_aprov   = [round(h.aprovacao, 1)    for h in historico]
    historico_rejeit  = [round(h.rejeicao, 1)     for h in historico]

    return render_template(
        'candidatos/detalhe.html',
        candidato          = candidato,
        noticias           = noticias,
        sentimentos        = sentimentos,
        historico_labels   = historico_labels,
        historico_aprov    = historico_aprov,
        historico_rejeit   = historico_rejeit,
    )


@candidato_bp.route('/novo', methods=['GET', 'POST'])
def criar():
    """GET/POST /candidatos/novo — formulário para adicionar candidato."""
    if request.method == 'POST':
        dados = _dados_formulario()
        if not dados:
            return redirect(url_for('candidatos.criar'))

        if CandidatoService.existe_duplicata(
            dados['nome'], dados['categoria'], dados['uf']
        ):
            flash(
                f'"{dados["nome"]}" já está sendo monitorado para este cargo e estado.',
                'warning',
            )
            return redirect(url_for('candidatos.listar'))

        buscar_foto = request.form.get('buscar_foto') == 'on'

        try:
            candidato = CandidatoService.criar(
                nome=dados['nome'],
                partido=dados['partido'],
                categoria=dados['categoria'],
                uf=dados['uf'],
                cor=dados['cor'],
                temas=dados['temas'] or None,
                nome_abrev=dados['nome_abrev'] or None,
                buscar_foto=buscar_foto,
                static_root=_static_root(),
            )
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('candidatos.criar'))

        msg = (
            f'{candidato.nome_abrev} ({candidato.escopo_label}) '
            f'foi adicionado e está sendo monitorado!'
        )
        if buscar_foto and candidato.tem_foto:
            msg += ' Foto obtida automaticamente.'
        elif buscar_foto:
            flash(
                msg + ' Não foi possível localizar uma foto na internet — '
                'você pode tentar novamente em Editar.',
                'warning',
            )
            return redirect(url_for('candidatos.detalhe', slug=candidato.slug))

        flash(msg, 'success')
        return redirect(url_for('candidatos.detalhe', slug=candidato.slug))

    return _render_form()


@candidato_bp.route('/<slug>/editar', methods=['GET', 'POST'])
def editar(slug: str):
    """GET/POST /candidatos/<slug>/editar — editar candidato."""
    candidato = CandidatoService.buscar_por_slug(slug)
    if not candidato:
        abort(404)

    if request.method == 'POST':
        dados = _dados_formulario()
        if not dados:
            return redirect(url_for('candidatos.editar', slug=slug))

        if CandidatoService.existe_duplicata(
            dados['nome'],
            dados['categoria'],
            dados['uf'],
            excluir_id=candidato.id,
        ):
            flash(
                f'Outro candidato já usa este nome para o mesmo cargo e estado.',
                'warning',
            )
            return redirect(url_for('candidatos.editar', slug=slug))

        try:
            CandidatoService.atualizar(
                candidato,
                nome=dados['nome'],
                nome_abrev=dados['nome_abrev'],
                partido=dados['partido'],
                categoria=dados['categoria'],
                uf=dados['uf'],
                cor=dados['cor'],
                temas=dados['temas'],
            )
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('candidatos.editar', slug=slug))

        flash(f'Dados de {candidato.nome_abrev} atualizados com sucesso.', 'success')
        return redirect(url_for('candidatos.detalhe', slug=candidato.slug))

    return _render_form(candidato=candidato)


@candidato_bp.post('/<slug>/buscar-foto')
def buscar_foto(slug: str):
    """POST — busca foto na Wikipedia e salva localmente."""
    candidato = CandidatoService.buscar_por_slug(slug)
    if not candidato:
        abort(404)

    if CandidatoService.atualizar_foto(candidato, _static_root()):
        flash(f'Foto de {candidato.nome_abrev} atualizada com sucesso.', 'success')
    else:
        flash(
            'Não encontramos uma foto confiável na Wikipedia para este nome. '
            'Tente ajustar o nome completo e buscar novamente.',
            'warning',
        )
    return redirect(url_for('candidatos.editar', slug=slug))


@candidato_bp.post('/<slug>/remover-foto')
def remover_foto(slug: str):
    """POST — remove foto local do candidato."""
    candidato = CandidatoService.buscar_por_slug(slug)
    if not candidato:
        abort(404)

    CandidatoService.remover_foto(candidato, _static_root())
    flash('Foto removida.', 'success')
    return redirect(url_for('candidatos.editar', slug=slug))


@candidato_bp.post('/<int:candidato_id>/desativar')
def desativar(candidato_id: int):
    """POST /candidatos/<id>/desativar — remove candidato do monitoramento."""
    sucesso = CandidatoService.desativar(candidato_id)
    if sucesso:
        flash('Candidato removido do monitoramento.', 'success')
    else:
        flash('Candidato não encontrado.', 'error')
    return redirect(url_for('candidatos.listar'))
