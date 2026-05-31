"""
Service: NoticiaService
Lógica de negócio para notícias: filtros, paginação, estatísticas.
"""
from datetime import date, datetime, timedelta
from sqlalchemy import func
from ..database import db
from ..models   import Noticia, Candidato


class NoticiaService:
    """Serviço responsável por operações sobre Noticia."""

    PERIODOS = [
        ('10h', 'Últimas 10 horas'),
        ('24h', 'Últimas 24 horas'),
        ('3d',  'Últimos 3 dias'),
        ('7d',  'Última semana'),
        ('30d', 'Último mês'),
        ('90d', 'Últimos 3 meses'),
    ]

    _PERIODOS_DELTA = {
        '10h': timedelta(hours=10),
        '24h': timedelta(hours=24),
        '3d':  timedelta(days=3),
        '7d':  timedelta(days=7),
        '30d': timedelta(days=30),
        '90d': timedelta(days=90),
    }

    @staticmethod
    def periodo_desde(periodo: str | None) -> datetime | None:
        """Converte slug de período (ex: 24h, 7d) em datetime limite inferior."""
        delta = NoticiaService._PERIODOS_DELTA.get(periodo or '')
        if not delta:
            return None
        return datetime.utcnow() - delta

    @staticmethod
    def periodo_label(periodo: str | None) -> str | None:
        if not periodo:
            return None
        return dict(NoticiaService.PERIODOS).get(periodo)

    @staticmethod
    def _aplicar_filtro_dias(q, dias: int | None = None):
        """Filtra notícias publicadas nos últimos N dias."""
        if dias and dias > 0:
            desde = datetime.utcnow() - timedelta(days=dias)
            q = q.filter(Noticia.publicada_em >= desde)
        return q

    @staticmethod
    def _base_query(categoria: str | None = None, uf: str | None = None):
        from .candidato_service import CandidatoService

        q = Noticia.query
        if categoria or uf:
            ids = CandidatoService.ids_filtrados(categoria=categoria, uf=uf)
            if not ids:
                return None, []
            q = q.filter(Noticia.candidato_id.in_(ids))
        return q, ids if (categoria or uf) else None

    @staticmethod
    def _aplicar_filtro_periodo(q, periodo: str | None):
        desde = NoticiaService.periodo_desde(periodo)
        if desde:
            q = q.filter(Noticia.publicada_em >= desde)
        return q

    # ── Consultas ─────────────────────────────────────────────────────────

    @staticmethod
    def listar(
        sentimento:   str | None = None,
        tema:         str | None = None,
        candidato_id: int | None = None,
        categoria:    str | None = None,
        uf:           str | None = None,
        periodo:      str | None = None,
        busca:        str | None = None,
        pagina:       int = 1,
        por_pagina:   int = 20,
    ):
        """
        Lista notícias com filtros opcionais e paginação.
        Retorna um objeto Pagination do SQLAlchemy.
        """
        from .candidato_service import CandidatoService

        q = Noticia.query.join(Noticia.candidato)

        if categoria or uf:
            ids = CandidatoService.ids_filtrados(categoria=categoria, uf=uf)
            if not ids:
                return Noticia.query.filter(False).paginate(
                    page=pagina, per_page=por_pagina, error_out=False
                )
            q = q.filter(Noticia.candidato_id.in_(ids))

        if sentimento:
            q = q.filter(Noticia.sentimento == sentimento)
        if tema:
            q = q.filter(Noticia.tema == tema)
        if candidato_id:
            q = q.filter(Noticia.candidato_id == candidato_id)
        if busca:
            like = f'%{busca}%'
            q = q.filter(
                db.or_(
                    Noticia.titulo.ilike(like),
                    Noticia.resumo.ilike(like),
                )
            )

        q = NoticiaService._aplicar_filtro_periodo(q, periodo)

        return (q
                .order_by(Noticia.publicada_em.desc())
                .paginate(page=pagina, per_page=por_pagina, error_out=False))

    @staticmethod
    def recentes(
        limite: int = 10,
        categoria: str | None = None,
        uf: str | None = None,
        periodo: str | None = None,
        dias: int | None = None,
    ) -> list[Noticia]:
        """Retorna as N notícias mais recentes."""
        q, _ = NoticiaService._base_query(categoria, uf)
        if q is None:
            return []
        q = NoticiaService._aplicar_filtro_periodo(q, periodo)
        q = NoticiaService._aplicar_filtro_dias(q, dias)
        return q.order_by(Noticia.publicada_em.desc()).limit(limite).all()

    @staticmethod
    def por_candidato(candidato_id: int, limite: int = 50) -> list[Noticia]:
        return (Noticia.query
                .filter_by(candidato_id=candidato_id)
                .order_by(Noticia.publicada_em.desc())
                .limit(limite)
                .all())

    @staticmethod
    def buscar_por_id(noticia_id: int) -> Noticia | None:
        return Noticia.query.get(noticia_id)

    # ── Estatísticas ──────────────────────────────────────────────────────

    @staticmethod
    def contagem_por_sentimento(
        categoria: str | None = None,
        uf: str | None = None,
        dias: int | None = None,
    ) -> dict:
        """Retorna contagens de sentimento nas notícias coletadas."""
        vazio = {'positivo': 0, 'negativo': 0, 'neutro': 0, 'total': 0,
                 'pct_positivo': 0, 'pct_negativo': 0, 'pct_neutro': 0}

        q, _ = NoticiaService._base_query(categoria, uf)
        if q is None:
            return vazio

        q = NoticiaService._aplicar_filtro_dias(q, dias)
        total = q.count()
        if total == 0:
            return vazio

        pos = q.filter(Noticia.sentimento == 'positivo').count()
        neg = q.filter(Noticia.sentimento == 'negativo').count()
        neu = q.filter(Noticia.sentimento == 'neutro').count()

        return {
            'positivo':     pos,
            'negativo':     neg,
            'neutro':       neu,
            'total':        total,
            'pct_positivo': round(pos / total * 100, 1),
            'pct_negativo': round(neg / total * 100, 1),
            'pct_neutro':   round(neu / total * 100, 1),
        }

    @staticmethod
    def contagem_por_tema(
        categoria: str | None = None,
        uf: str | None = None,
        dias: int | None = None,
    ) -> dict:
        """Retorna {tema: contagem} nas notícias coletadas."""
        temas = ['economia', 'saude', 'educacao', 'violencia', 'justica', 'politica']
        q_base, _ = NoticiaService._base_query(categoria, uf)
        if q_base is None:
            return {t: 0 for t in temas}

        resultado = {}
        for tema in temas:
            q = q_base.filter(Noticia.tema == tema)
            q = NoticiaService._aplicar_filtro_dias(q, dias)
            resultado[tema] = q.count()
        return resultado

    @staticmethod
    def noticias_hoje(
        categoria: str | None = None,
        uf: str | None = None,
    ) -> int:
        inicio_dia = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        q, _ = NoticiaService._base_query(categoria, uf)
        if q is None:
            return 0
        return q.filter(Noticia.publicada_em >= inicio_dia).count()

    @staticmethod
    def stats_candidato(
        candidato_id: int,
        dias: int | None = None,
    ) -> dict:
        """Estatísticas de notícias coletadas para um candidato no período."""
        vazio = {'total': 0, 'positivo': 0, 'negativo': 0, 'neutro': 0,
                 'pct_positivo': 0, 'pct_negativo': 0, 'pct_neutro': 0}
        q = Noticia.query.filter_by(candidato_id=candidato_id)
        q = NoticiaService._aplicar_filtro_dias(q, dias)
        total = q.count()
        if total == 0:
            return vazio

        pos = q.filter(Noticia.sentimento == 'positivo').count()
        neg = q.filter(Noticia.sentimento == 'negativo').count()
        neu = q.filter(Noticia.sentimento == 'neutro').count()
        return {
            'total':        total,
            'positivo':     pos,
            'negativo':     neg,
            'neutro':       neu,
            'pct_positivo': round(pos / total * 100, 1),
            'pct_negativo': round(neg / total * 100, 1),
            'pct_neutro':   round(neu / total * 100, 1),
        }

    @staticmethod
    def contagem_por_dia_candidato(
        candidato_id: int,
        dias: int = 60,
    ) -> dict[date, int]:
        """Contagem de notícias por dia de publicação (últimos N dias)."""
        desde = date.today() - timedelta(days=dias)
        desde_dt = datetime.combine(desde, datetime.min.time())
        rows = (
            db.session.query(
                func.date(Noticia.publicada_em).label('dia'),
                func.count(Noticia.id).label('cnt'),
            )
            .filter(
                Noticia.candidato_id == candidato_id,
                Noticia.publicada_em >= desde_dt,
            )
            .group_by(func.date(Noticia.publicada_em))
            .all()
        )
        resultado: dict[date, int] = {}
        for row in rows:
            d = row.dia
            if isinstance(d, str):
                d = date.fromisoformat(d)
            resultado[d] = int(row.cnt)
        return resultado

    @staticmethod
    def _granularidade(dias: int) -> str:
        return 'dia' if dias <= 14 else 'semana'

    @staticmethod
    def _gerar_buckets(dias: int) -> list[tuple[str, datetime, datetime]]:
        """
        Retorna lista (label_exibicao, inicio, fim) para agrupar notícias.
        """
        from datetime import date

        hoje = date.today()
        desde = hoje - timedelta(days=dias)
        granularidade = NoticiaService._granularidade(dias)
        buckets: list[tuple[str, datetime, datetime]] = []

        if granularidade == 'dia':
            d = desde
            while d <= hoje:
                ini = datetime.combine(d, datetime.min.time())
                fim = datetime.combine(d, datetime.max.time())
                buckets.append((d.strftime('%d/%m'), ini, fim))
                d += timedelta(days=1)
        else:
            # Semanas — funciona bem de 15 dias até 5+ meses
            d = desde
            while d <= hoje:
                fim_d = min(d + timedelta(days=6), hoje)
                lbl = f'{d.strftime("%d/%m")}–{fim_d.strftime("%d/%m")}'
                ini = datetime.combine(d, datetime.min.time())
                fim = datetime.combine(fim_d, datetime.max.time())
                buckets.append((lbl, ini, fim))
                d += timedelta(days=7)

        return buckets

    @staticmethod
    def _contar_sentimentos_noticias(noticias: list) -> tuple[int, int, int]:
        pos = sum(1 for n in noticias if n.sentimento == 'positivo')
        neg = sum(1 for n in noticias if n.sentimento == 'negativo')
        neu = len(noticias) - pos - neg
        return pos, neg, neu

    @staticmethod
    def _filtrar_buckets_com_dados(
        labels: list[str],
        dados_candidatos: dict,
    ) -> tuple[list[str], dict, int]:
        """Remove colunas onde nenhum candidato teve notícia."""
        if not dados_candidatos:
            return [], {}, 0

        n = len(labels)
        indices = []
        for i in range(n):
            if any(dados_candidatos[c]['totais'][i] > 0 for c in dados_candidatos):
                indices.append(i)

        if not indices:
            return [], {}, 0

        novos_labels = [labels[i] for i in indices]
        novos_dados = {}
        total = 0
        for slug, info in dados_candidatos.items():
            novos_dados[slug] = {
                'nome':       info['nome'],
                'cor':        info['cor'],
                'aprovacoes': [info['aprovacoes'][i] for i in indices],
                'totais':     [info['totais'][i] for i in indices],
                'positivo':   [info['positivo'][i] for i in indices],
                'negativo':   [info['negativo'][i] for i in indices],
                'neutro':     [info['neutro'][i] for i in indices],
            }
            total += sum(novos_dados[slug]['totais'])

        return novos_labels, novos_dados, total

    @staticmethod
    def obter_grafico_sentimento_diario(
        dias: int = 30,
        categoria: str | None = None,
        uf: str | None = None,
    ) -> dict:
        """
        Série de sentimento nas notícias coletadas.
        ≤14d: buckets diários. >14d: buckets semanais. Sempre expõe % positivo por candidato.
        """
        from .candidato_service import CandidatoService

        candidatos = CandidatoService.listar_todos(categoria=categoria, uf=uf)
        buckets = NoticiaService._gerar_buckets(dias)
        labels = [b[0] for b in buckets]
        granularidade = NoticiaService._granularidade(dias)

        dados = {}
        for cand in candidatos:
            valores, totais = [], []
            cnt_pos, cnt_neg, cnt_neu = [], [], []

            for _, ini, fim in buckets:
                noticias = (Noticia.query
                            .filter(
                                Noticia.candidato_id == cand.id,
                                Noticia.publicada_em >= ini,
                                Noticia.publicada_em <= fim,
                            )
                            .all())
                total = len(noticias)
                totais.append(total)
                if total == 0:
                    valores.append(None)
                    cnt_pos.append(0)
                    cnt_neg.append(0)
                    cnt_neu.append(0)
                else:
                    pos, neg, neu = NoticiaService._contar_sentimentos_noticias(noticias)
                    valores.append(round(pos / total * 100, 1))
                    cnt_pos.append(pos)
                    cnt_neg.append(neg)
                    cnt_neu.append(neu)

            if sum(totais) == 0:
                continue

            dados[cand.slug] = {
                'nome':       cand.nome_abrev,
                'cor':        cand.cor,
                'aprovacoes': valores,
                'totais':     totais,
                'positivo':   cnt_pos,
                'negativo':   cnt_neg,
                'neutro':     cnt_neu,
            }

        labels, dados, total_grafico = NoticiaService._filtrar_buckets_com_dados(
            labels, dados
        )

        # Agregado para barras empilhadas (todas as séries visíveis)
        agg_pos, agg_neg, agg_neu = [], [], []
        for i in range(len(labels)):
            agg_pos.append(sum(dados[c]['positivo'][i] for c in dados))
            agg_neg.append(sum(dados[c]['negativo'][i] for c in dados))
            agg_neu.append(sum(dados[c]['neutro'][i] for c in dados))

        return {
            'labels':          labels,
            'candidatos':      dados,
            'granularidade':   granularidade,
            'total_noticias':  total_grafico,
            'semanas_com_dados': len(labels),
            'volume_agregado': {
                'positivo': agg_pos,
                'negativo': agg_neg,
                'neutro':   agg_neu,
            },
        }

    # ── Mutações ──────────────────────────────────────────────────────────

    @staticmethod
    def criar(
        candidato_id: int,
        titulo:       str,
        resumo:       str,
        fonte:        str,
        sentimento:   str,
        tema:         str,
        relevancia:   int  = 70,
        url:          str | None = None,
        publicada_em: datetime | None = None,
    ) -> Noticia:
        from ..models.noticia import SENTIMENTOS, TEMAS_VALIDOS

        candidato = Candidato.query.filter_by(id=candidato_id, ativo=True).first()
        if not candidato:
            raise ValueError('Candidato não encontrado ou inativo.')
        if sentimento not in SENTIMENTOS:
            raise ValueError('Sentimento inválido.')
        if tema not in TEMAS_VALIDOS:
            raise ValueError('Tema inválido.')
        if not titulo.strip():
            raise ValueError('O título é obrigatório.')
        if not fonte.strip():
            raise ValueError('A fonte é obrigatória.')

        relevancia = max(0, min(100, int(relevancia)))

        noticia = Noticia(
            candidato_id = candidato_id,
            titulo       = titulo.strip(),
            resumo       = (resumo or '').strip(),
            fonte        = fonte.strip(),
            sentimento   = sentimento,
            tema         = tema,
            relevancia   = relevancia,
            url          = url.strip()[:500] if url else None,
            publicada_em = publicada_em or datetime.utcnow(),
        )
        db.session.add(noticia)
        db.session.commit()
        return noticia

    @staticmethod
    def excluir(noticia_id: int) -> bool:
        noticia = Noticia.query.get(noticia_id)
        if not noticia:
            return False
        db.session.delete(noticia)
        db.session.commit()
        return True

    @staticmethod
    def excluir_todas() -> int:
        """Remove todas as notícias. Retorna quantidade excluída."""
        total = Noticia.query.count()
        Noticia.query.delete(synchronize_session=False)
        db.session.commit()
        return total

    @staticmethod
    def total() -> int:
        return Noticia.query.count()

    @staticmethod
    def simular_nova_noticia() -> Noticia | None:
        """
        Cria uma notícia simulada para um candidato aleatório.
        Chamado pelo scheduler a cada ciclo.
        """
        import random
        from datetime import datetime

        candidatos = Candidato.query.filter_by(ativo=True).all()
        if not candidatos:
            return None

        candidato   = random.choice(candidatos)
        sentimentos = ['positivo', 'positivo', 'neutro', 'negativo']
        temas       = ['economia', 'saude', 'educacao', 'violencia', 'justica', 'politica']
        fontes      = ['G1 / Globo', 'UOL', 'Folha de S.Paulo', 'CNN Brasil',
                       'Estadão', 'O Globo', 'Poder360', 'Metrópoles']

        titulos = [
            f'{candidato.nome_abrev} comenta situação econômica do país',
            f'Apoiadores de {candidato.nome_abrev} organizam ato político',
            f'{candidato.nome_abrev} anuncia nova proposta eleitoral',
            f'Mídia repercute declaração de {candidato.nome_abrev}',
            f'Pesquisa mostra opinião sobre {candidato.nome_abrev}',
            f'{candidato.nome_abrev} participa de evento partidário',
        ]

        return NoticiaService.criar(
            candidato_id = candidato.id,
            titulo       = random.choice(titulos),
            resumo       = (
                'Notícia capturada automaticamente pelo sistema de monitoramento '
                'em tempo real da plataforma Eleitoral 2026.'
            ),
            fonte        = random.choice(fontes),
            sentimento   = random.choice(sentimentos),
            tema         = random.choice(temas),
            relevancia   = random.randint(50, 90),
        )
