"""
Controller: API REST v1
Endpoints JSON para consumo por JavaScript (gráficos, atualização live).
"""
from flask import Blueprint, jsonify, request, abort
from ..services import (CandidatoService, NoticiaService,
                         HistoricoService, DashboardService, ColetaService)

api_bp = Blueprint('api', __name__)


# ── Helpers ───────────────────────────────────────────────────────────────

def _ok(data, status: int = 200):
    return jsonify({'status': 'ok', 'data': data}), status


def _erro(mensagem: str, status: int = 400):
    return jsonify({'status': 'erro', 'mensagem': mensagem}), status


# ── Candidatos ────────────────────────────────────────────────────────────

@api_bp.get('/candidatos')
def api_candidatos():
    """GET /api/v1/candidatos — lista candidatos como JSON."""
    categoria = request.args.get('categoria') or None
    uf = (request.args.get('uf') or '').upper() or None
    candidatos = CandidatoService.listar_todos(categoria=categoria, uf=uf)
    return _ok([c.to_dict() for c in candidatos])


@api_bp.get('/candidatos/<slug>')
def api_candidato_detalhe(slug: str):
    """GET /api/v1/candidatos/<slug>"""
    c = CandidatoService.buscar_por_slug(slug)
    if not c:
        return _erro('Candidato não encontrado.', 404)
    return _ok(c.to_dict())


@api_bp.post('/candidatos')
def api_criar_candidato():
    """
    POST /api/v1/candidatos
    Body JSON: { nome, partido, categoria?, uf?, cor?, temas? }
    """
    body = request.get_json(silent=True) or {}

    nome      = (body.get('nome')      or '').strip()
    partido   = (body.get('partido')   or '').strip()
    categoria = (body.get('categoria') or 'presidente').strip()
    uf        = (body.get('uf')        or '').strip().upper() or None
    cor       = (body.get('cor')       or '#6366f1').strip()
    temas     = body.get('temas')

    if not nome:
        return _erro('O campo "nome" é obrigatório.')
    if not partido:
        return _erro('O campo "partido" é obrigatório.')

    if CandidatoService.existe_duplicata(nome, categoria, uf):
        return _erro(f'"{nome}" já está sendo monitorado para este cargo.', 409)

    try:
        candidato = CandidatoService.criar(
            nome=nome, partido=partido, categoria=categoria,
            uf=uf, cor=cor, temas=temas,
        )
    except ValueError as e:
        return _erro(str(e))

    return _ok(candidato.to_dict(), 201)


@api_bp.delete('/candidatos/<int:candidato_id>')
def api_desativar_candidato(candidato_id: int):
    """DELETE /api/v1/candidatos/<id>"""
    sucesso = CandidatoService.desativar(candidato_id)
    if not sucesso:
        return _erro('Candidato não encontrado.', 404)
    return '', 204


# ── Notícias ──────────────────────────────────────────────────────────────

@api_bp.get('/noticias')
def api_noticias():
    """
    GET /api/v1/noticias
    Query params: sentimento, tema, candidato_id, q, pagina, por_pagina
    """
    paginacao = NoticiaService.listar(
        sentimento   = request.args.get('sentimento')    or None,
        tema         = request.args.get('tema')          or None,
        candidato_id = request.args.get('candidato_id', type=int),
        categoria    = request.args.get('categoria')     or None,
        uf           = (request.args.get('uf') or '').upper() or None,
        periodo      = request.args.get('periodo')       or None,
        busca        = request.args.get('q')             or None,
        pagina       = request.args.get('pagina',    1,  type=int),
        por_pagina   = request.args.get('por_pagina', 20, type=int),
    )
    return _ok({
        'items':    [n.to_dict() for n in paginacao.items],
        'total':    paginacao.total,
        'pagina':   paginacao.page,
        'paginas':  paginacao.pages,
        'por_pagina': paginacao.per_page,
    })


@api_bp.get('/noticias/sentimento')
def api_sentimento():
    """GET /api/v1/noticias/sentimento — estatísticas de sentimento."""
    categoria = request.args.get('categoria') or None
    uf = (request.args.get('uf') or '').upper() or None
    return _ok(NoticiaService.contagem_por_sentimento(categoria=categoria, uf=uf))


@api_bp.get('/noticias/temas')
def api_temas():
    """GET /api/v1/noticias/temas — contagem por tema."""
    categoria = request.args.get('categoria') or None
    uf = (request.args.get('uf') or '').upper() or None
    return _ok(NoticiaService.contagem_por_tema(categoria=categoria, uf=uf))


# ── Histórico ─────────────────────────────────────────────────────────────

@api_bp.get('/historico')
def api_historico():
    """
    GET /api/v1/historico?dias=30
    Retorna dados para gráficos de todos os candidatos.
    """
    dias = request.args.get('dias', 30, type=int)
    dias = dias if dias in (7, 15, 30, 60) else 30
    categoria = request.args.get('categoria') or None
    uf = (request.args.get('uf') or '').upper() or None
    return _ok(HistoricoService.obter_todos_para_grafico(
        dias=dias, categoria=categoria, uf=uf
    ))


@api_bp.get('/historico/<int:candidato_id>')
def api_historico_candidato(candidato_id: int):
    """GET /api/v1/historico/<candidato_id>?dias=60"""
    c = CandidatoService.buscar_por_id(candidato_id)
    if not c:
        return _erro('Candidato não encontrado.', 404)
    dias = request.args.get('dias', 60, type=int)
    historicos = HistoricoService.obter(candidato_id, dias=dias)
    return _ok([h.to_dict() for h in historicos])


# ── Dashboard ─────────────────────────────────────────────────────────────

@api_bp.get('/dashboard')
def api_dashboard():
    """GET /api/v1/dashboard — dados completos do dashboard."""
    periodo = request.args.get('periodo', 30, type=int)
    periodo = DashboardService.normalizar_periodo(periodo)
    categoria = request.args.get('categoria') or None
    uf = (request.args.get('uf') or '').upper() or None
    dados = DashboardService.obter_dados(
        periodo=periodo, categoria=categoria, uf=uf
    )
    # Serializar candidatos
    dados['candidatos'] = [c.to_dict() for c in dados['candidatos']]
    dados['noticias_recentes'] = [n.to_dict() for n in dados['noticias_recentes']]
    return _ok(dados)


# ── Atualização simulada ──────────────────────────────────────────────────

@api_bp.post('/coletar')
def api_coletar():
    """
    POST /api/v1/coletar
    Body JSON: { candidato_id?, dias?, termo_extra? }
    Busca notícias retroativas e salva no banco.
    """
    body = request.get_json(silent=True) or {}
    candidato_id = body.get('candidato_id')
    dias = body.get('dias', 30)
    termo_extra = (body.get('termo_extra') or '').strip() or None

    try:
        dias = int(dias)
        resultado = ColetaService.coletar(
            candidato_id=candidato_id,
            dias=dias,
            termo_extra=termo_extra,
        )
    except ValueError as e:
        return _erro(str(e))

    return _ok(resultado)


@api_bp.post('/atualizar')
def api_atualizar():
    """
    POST /api/v1/atualizar
    Simula um ciclo de coleta: atualiza métricas + cria notícia nova.
    """
    candidatos = CandidatoService.atualizar_todos()
    nova_noticia = NoticiaService.simular_nova_noticia()

    return _ok({
        'candidatos_atualizados': len(candidatos),
        'nova_noticia': nova_noticia.to_dict() if nova_noticia else None,
    })
