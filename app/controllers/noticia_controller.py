"""
Controller: Notícias
Listagem, filtros e administração do feed de notícias.
"""
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..services import NoticiaService, CandidatoService, ColetaService

noticia_bp = Blueprint('noticias', __name__)

TEMAS_OPCOES = [
    ('economia',  'Economia'),
    ('saude',     'Saúde'),
    ('educacao',  'Educação'),
    ('violencia', 'Violência'),
    ('justica',   'Justiça'),
    ('politica',  'Política'),
]

SENTIMENTOS_OPCOES = [
    ('positivo', 'Positivo'),
    ('negativo', 'Negativo'),
    ('neutro',   'Neutro'),
]


def _filtros_request():
    periodo = request.args.get('periodo', '').strip() or None
    if periodo and periodo not in dict(NoticiaService.PERIODOS):
        periodo = None
    return {
        'sentimento':   request.args.get('sentimento', '').strip() or None,
        'tema':         request.args.get('tema', '').strip() or None,
        'candidato_id': request.args.get('candidato_id', type=int),
        'categoria':    request.args.get('categoria', '').strip() or None,
        'uf':           request.args.get('uf', '').strip().upper() or None,
        'periodo':      periodo,
        'busca':        request.args.get('q', '').strip() or None,
        'pagina':       request.args.get('pagina', 1, type=int),
        'por_pagina':   request.args.get('por_pagina', 20, type=int),
    }


@noticia_bp.get('/')
def listar():
    """GET /noticias/ — feed público com filtros."""
    f = _filtros_request()

    paginacao = NoticiaService.listar(
        sentimento=f['sentimento'],
        tema=f['tema'],
        candidato_id=f['candidato_id'],
        categoria=f['categoria'],
        uf=f['uf'],
        periodo=f['periodo'],
        busca=f['busca'],
        pagina=f['pagina'],
        por_pagina=f['por_pagina'],
    )

    candidatos = CandidatoService.listar_todos(
        categoria=f['categoria'], uf=f['uf']
    )

    return render_template(
        'noticias/lista.html',
        paginacao=paginacao,
        candidatos=candidatos,
        temas_opcoes=TEMAS_OPCOES,
        filtro_sentimento=f['sentimento'] or '',
        filtro_tema=f['tema'] or '',
        filtro_candidato_id=f['candidato_id'],
        filtro_busca=f['busca'] or '',
        filtro_categoria=f['categoria'],
        filtro_uf=f['uf'],
        filtro_periodo=f['periodo'] or '',
        filtro_periodo_label=NoticiaService.periodo_label(f['periodo']),
    )


@noticia_bp.get('/admin')
def admin():
    """GET /noticias/admin — painel de administração."""
    f = _filtros_request()
    f['por_pagina'] = request.args.get('por_pagina', 50, type=int)

    paginacao = NoticiaService.listar(
        sentimento=f['sentimento'],
        tema=f['tema'],
        candidato_id=f['candidato_id'],
        categoria=f['categoria'],
        uf=f['uf'],
        periodo=f['periodo'],
        busca=f['busca'],
        pagina=f['pagina'],
        por_pagina=f['por_pagina'],
    )

    candidatos = CandidatoService.listar_todos(
        categoria=f['categoria'], uf=f['uf']
    )

    return render_template(
        'noticias/admin.html',
        paginacao=paginacao,
        candidatos=candidatos,
        temas_opcoes=TEMAS_OPCOES,
        total_noticias=NoticiaService.total(),
        filtro_sentimento=f['sentimento'] or '',
        filtro_tema=f['tema'] or '',
        filtro_candidato_id=f['candidato_id'],
        filtro_busca=f['busca'] or '',
        filtro_categoria=f['categoria'],
        filtro_uf=f['uf'],
        filtro_periodo=f['periodo'] or '',
        filtro_periodo_label=NoticiaService.periodo_label(f['periodo']),
    )


@noticia_bp.route('/admin/coletar', methods=['GET', 'POST'])
def admin_coletar():
    """GET/POST /noticias/admin/coletar — busca notícias do passado via RSS."""
    candidatos = CandidatoService.listar_todos()
    periodos = ColetaService.PERIODOS

    if not candidatos:
        flash('Cadastre candidatos antes de iniciar a coleta.', 'warning')
        return redirect(url_for('candidatos.criar'))

    if request.method == 'POST':
        candidato_id = request.form.get('candidato_id', type=int) or None
        dias         = request.form.get('dias', 30, type=int)
        termo_extra  = request.form.get('termo_extra', '').strip() or None

        try:
            resultado = ColetaService.coletar(
                candidato_id=candidato_id,
                dias=dias,
                termo_extra=termo_extra,
            )
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('noticias.admin_coletar'))

        imp = resultado['importadas']
        dup = resultado['duplicadas']
        if imp > 0:
            flash(
                f'Coleta concluída ({resultado["periodo_label"]}): '
                f'{imp} notícia(s) importada(s) e salvas no banco. '
                f'{dup} duplicata(s) ignorada(s).',
                'success',
            )
        else:
            flash(
                f'Nenhuma notícia nova encontrada para {resultado["periodo_label"]}. '
                f'{dup} já existiam no banco.',
                'warning',
            )
        if resultado['erros']:
            flash(resultado['erros'][0], 'error')

        return redirect(url_for('noticias.admin'))

    return render_template(
        'noticias/coletar.html',
        candidatos=candidatos,
        periodos=periodos,
    )


@noticia_bp.route('/admin/nova', methods=['GET', 'POST'])
def admin_criar():
    """GET/POST /noticias/admin/nova — cadastro manual de notícia."""
    candidatos = CandidatoService.listar_todos()

    if not candidatos:
        flash('Cadastre ao menos um candidato antes de adicionar notícias.', 'warning')
        return redirect(url_for('candidatos.criar'))

    if request.method == 'POST':
        candidato_id = request.form.get('candidato_id', type=int)
        titulo       = request.form.get('titulo', '').strip()
        resumo       = request.form.get('resumo', '').strip()
        fonte        = request.form.get('fonte', '').strip()
        sentimento   = request.form.get('sentimento', 'neutro').strip()
        tema         = request.form.get('tema', 'politica').strip()
        url          = request.form.get('url', '').strip() or None
        relevancia   = request.form.get('relevancia', 70, type=int)
        pub_raw      = request.form.get('publicada_em', '').strip()

        publicada_em = None
        if pub_raw:
            try:
                publicada_em = datetime.fromisoformat(pub_raw)
            except ValueError:
                flash('Data de publicação inválida.', 'error')
                return redirect(url_for('noticias.admin_criar'))

        try:
            noticia = NoticiaService.criar(
                candidato_id=candidato_id,
                titulo=titulo,
                resumo=resumo,
                fonte=fonte,
                sentimento=sentimento,
                tema=tema,
                relevancia=relevancia,
                url=url,
                publicada_em=publicada_em,
            )
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('noticias.admin_criar'))

        titulo_msg = noticia.titulo if len(noticia.titulo) <= 60 else noticia.titulo[:60] + '…'
        flash(f'Notícia "{titulo_msg}" cadastrada com sucesso!', 'success')
        return redirect(url_for('noticias.admin'))

    return render_template(
        'noticias/form.html',
        candidatos=candidatos,
        temas_opcoes=TEMAS_OPCOES,
        sentimentos_opcoes=SENTIMENTOS_OPCOES,
    )


@noticia_bp.post('/admin/<int:noticia_id>/excluir')
def admin_excluir(noticia_id: int):
    """POST /noticias/admin/<id>/excluir — remove uma notícia."""
    if NoticiaService.excluir(noticia_id):
        flash('Notícia excluída.', 'success')
    else:
        flash('Notícia não encontrada.', 'error')
    return redirect(request.referrer or url_for('noticias.admin'))


@noticia_bp.post('/admin/limpar-todas')
def admin_limpar_todas():
    """POST /noticias/admin/limpar-todas — remove todas as notícias."""
    confirmacao = request.form.get('confirmacao', '').strip()
    if confirmacao != 'LIMPAR':
        flash('Digite LIMPAR para confirmar a exclusão de todas as notícias.', 'error')
        return redirect(url_for('noticias.admin'))

    total = NoticiaService.excluir_todas()
    flash(f'{total} notícia(s) removida(s) do banco.', 'success')
    return redirect(url_for('noticias.admin'))
