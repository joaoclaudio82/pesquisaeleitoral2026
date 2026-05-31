"""
Service: ColetaService
Busca notícias na web (Google News RSS) e persiste no banco.
"""
import re
from calendar import timegm
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse

import feedparser

from ..database import db
from ..models   import Candidato, Noticia
from .noticia_service import NoticiaService


class ColetaService:
    """Coleta retroativa de notícias via RSS e grava em `noticias`."""

    PERIODOS = [
        (1,   '1 dia',    '1d'),
        (7,   '7 dias',   '7d'),
        (14,  '14 dias',  '7d'),
        (30,  '1 mês',    '30d'),
        (60,  '2 meses',  '1y'),
        (90,  '3 meses',  '1y'),
        (150, '5 meses',  '1y'),
    ]

    PERIODOS_VALIDOS = {p[0] for p in PERIODOS}

    _PALAVRAS_POSITIVAS = (
        'vitória', 'vitoria', 'crescimento', 'aprovação', 'aprovacao', 'líder',
        'lider', 'avança', 'avanca', 'anuncia', 'elogia', 'recorde', 'alta',
        'fortalece', 'apoio', 'avanço', 'avanco', 'sucesso', 'benefício',
    )
    _PALAVRAS_NEGATIVAS = (
        'crítica', 'critica', 'rejeição', 'rejeicao', 'queda', 'escândalo',
        'escandalo', 'condena', 'denúncia', 'denuncia', 'investiga', 'fraude',
        'derrota', 'polêmica', 'polemica', 'impeachment', 'prisão', 'prisao',
    )
    _TEMAS = {
        'economia':  ('economia', 'inflação', 'inflacao', 'emprego', 'dólar',
                      'dolar', 'tribut', 'fiscal', 'pib', 'salário', 'salario'),
        'saude':     ('saúde', 'saude', 'sus', 'hospital', 'vacina', 'médic',
                      'medic', 'epidemia'),
        'educacao':  ('educação', 'educacao', 'escola', 'universidade', 'enem'),
        'violencia': ('violência', 'violencia', 'crime', 'segurança', 'seguranca',
                      'polícia', 'policia', 'homicídio', 'homicidio'),
        'justica':   ('justiça', 'justica', 'stf', 'supremo', 'judicial',
                      'tribunal', 'processo', 'condenação', 'condenacao'),
        'politica':  ('eleição', 'eleicao', 'candidat', 'partido', 'governo',
                      'congresso', 'presidente', 'voto', 'campanha'),
    }

    @staticmethod
    def periodo_label(dias: int) -> str:
        return dict((p[0], p[1]) for p in ColetaService.PERIODOS).get(dias, f'{dias} dias')

    @staticmethod
    def normalizar_dias(dias: int) -> int:
        return dias if dias in ColetaService.PERIODOS_VALIDOS else 30

    @staticmethod
    def _google_when(dias: int) -> str | None:
        """Filtro `when:` do Google News. Períodos longos usam 1y e filtram no app."""
        if dias <= 1:
            return '1d'
        if dias <= 7:
            return '7d'
        if dias <= 30:
            return '30d'
        return '1y'

    @staticmethod
    def _url_rss(termo: str, dias: int) -> str:
        when = ColetaService._google_when(dias)
        query = termo.strip()
        if when:
            query = f'{query} when:{when}'
        return (
            'https://news.google.com/rss/search?q='
            f'{quote_plus(query)}&hl=pt-BR&gl=BR&ceid=BR:pt-419'
        )

    @staticmethod
    def _parse_publicada(entry) -> datetime:
        if getattr(entry, 'published_parsed', None):
            return datetime.utcfromtimestamp(timegm(entry.published_parsed))
        if entry.get('published'):
            try:
                dt = parsedate_to_datetime(entry.published)
                return dt.replace(tzinfo=None) if dt.tzinfo else dt
            except (TypeError, ValueError, OverflowError):
                pass
        if getattr(entry, 'updated_parsed', None):
            return datetime.utcfromtimestamp(timegm(entry.updated_parsed))
        return datetime.utcnow()

    @staticmethod
    def _extrair_fonte(entry) -> str:
        if entry.get('source') and entry.source.get('title'):
            return entry.source.title[:100]
        link = entry.get('link', '')
        if link:
            host = urlparse(link).netloc.replace('www.', '')
            if host:
                return host[:100]
        return 'Google News'

    @staticmethod
    def _limpar_html(texto: str) -> str:
        return re.sub(r'<[^>]+>', '', texto or '').strip()

    @staticmethod
    def _analisar_sentimento(texto: str) -> str:
        t = texto.lower()
        pos = sum(1 for p in ColetaService._PALAVRAS_POSITIVAS if p in t)
        neg = sum(1 for p in ColetaService._PALAVRAS_NEGATIVAS if p in t)
        if pos > neg:
            return 'positivo'
        if neg > pos:
            return 'negativo'
        return 'neutro'

    @staticmethod
    def _detectar_tema(texto: str) -> str:
        t = texto.lower()
        scores = {tema: sum(1 for kw in kws if kw in t)
                  for tema, kws in ColetaService._TEMAS.items()}
        melhor = max(scores, key=scores.get)
        return melhor if scores[melhor] > 0 else 'politica'

    @staticmethod
    def _ja_existe(url: str | None, titulo: str, candidato_id: int) -> bool:
        if url:
            if Noticia.query.filter_by(url=url).first():
                return True
        titulo_curto = titulo[:300]
        return (Noticia.query
                .filter_by(candidato_id=candidato_id, titulo=titulo_curto)
                .first() is not None)

    @staticmethod
    def _montar_termo(candidato: Candidato, termo_extra: str | None = None) -> str:
        partes = [candidato.nome_abrev, candidato.nome.split()[0]]
        if termo_extra:
            partes.append(termo_extra.strip())
        partes.append('Brasil')
        return ' '.join(dict.fromkeys(p for p in partes if p))

    @staticmethod
    def coletar_candidato(
        candidato: Candidato,
        dias: int = 30,
        termo_extra: str | None = None,
        max_itens: int = 80,
    ) -> dict:
        """
        Busca notícias no Google News RSS e salva no banco.

        Returns:
            dict com contadores importadas, ignoradas, erros.
        """
        dias = ColetaService.normalizar_dias(dias)
        desde = datetime.utcnow() - timedelta(days=dias)
        termo = ColetaService._montar_termo(candidato, termo_extra)
        url_rss = ColetaService._url_rss(termo, dias)
        max_itens = min(250, max(80, dias + 50))

        feed = feedparser.parse(url_rss)
        resultado = {
            'candidato':     candidato.nome_abrev,
            'termo_busca':  termo,
            'importadas':    0,
            'duplicadas':    0,
            'fora_periodo':  0,
            'sem_conteudo':  0,
            'erros':         [],
        }

        if feed.bozo and not feed.entries:
            resultado['erros'].append(
                'Não foi possível ler o feed RSS. Verifique a conexão com a internet.'
            )
            return resultado

        for entry in feed.entries[:max_itens]:
            titulo = ColetaService._limpar_html(entry.get('title', '')).strip()
            if not titulo:
                resultado['sem_conteudo'] += 1
                continue

            link = (entry.get('link') or '').strip() or None
            if link and len(link) > 500:
                link = link[:500]
            resumo = ColetaService._limpar_html(
                entry.get('summary') or entry.get('description') or titulo
            )[:2000]
            publicada_em = ColetaService._parse_publicada(entry)

            if publicada_em < desde:
                resultado['fora_periodo'] += 1
                continue

            if ColetaService._ja_existe(link, titulo, candidato.id):
                resultado['duplicadas'] += 1
                continue

            texto_analise = f'{titulo} {resumo}'
            try:
                NoticiaService.criar(
                    candidato_id = candidato.id,
                    titulo       = titulo[:300],
                    resumo       = resumo,
                    fonte        = ColetaService._extrair_fonte(entry),
                    sentimento   = ColetaService._analisar_sentimento(texto_analise),
                    tema         = ColetaService._detectar_tema(texto_analise),
                    relevancia   = min(95, 55 + len(titulo) % 40),
                    url          = link,
                    publicada_em = publicada_em,
                )
                resultado['importadas'] += 1
            except ValueError as e:
                resultado['erros'].append(str(e))

        return resultado

    @staticmethod
    def coletar(
        candidato_id: int | None = None,
        dias: int = 30,
        termo_extra: str | None = None,
    ) -> dict:
        """
        Coleta para um candidato ou para todos os ativos.

        Returns:
            dict agregado com totais e detalhes por candidato.
        """
        if candidato_id:
            candidatos = [Candidato.query.filter_by(id=candidato_id, ativo=True).first()]
            if not candidatos[0]:
                raise ValueError('Candidato não encontrado ou inativo.')
        else:
            candidatos = Candidato.query.filter_by(ativo=True).all()
            if not candidatos:
                raise ValueError('Nenhum candidato ativo para coletar notícias.')

        agregado = {
            'dias':           ColetaService.normalizar_dias(dias),
            'periodo_label':  ColetaService.periodo_label(dias),
            'importadas':     0,
            'duplicadas':     0,
            'fora_periodo':   0,
            'sem_conteudo':   0,
            'erros':          [],
            'detalhes':       [],
        }

        for cand in candidatos:
            r = ColetaService.coletar_candidato(
                cand, dias=dias, termo_extra=termo_extra
            )
            agregado['importadas']   += r['importadas']
            agregado['duplicadas']   += r['duplicadas']
            agregado['fora_periodo'] += r['fora_periodo']
            agregado['sem_conteudo'] += r['sem_conteudo']
            agregado['erros'].extend(r['erros'])
            agregado['detalhes'].append(r)

        return agregado
