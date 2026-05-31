"""
Service: DescobertaService
Busca candidatos prováveis na web (Google News) e cadastra no sistema.
"""
import re
from collections import Counter
from urllib.parse import quote_plus

import feedparser
import requests

from ..constants import categoria_requer_uf
from ..models import Candidato
from .candidato_service import CandidatoService
from .coleta_service import ColetaService
from .foto_service import FotoService

_USER_AGENT = 'PesquisaEleitoral2026/1.0 (educational; contact: local)'
_WIKI_API = 'https://pt.wikipedia.org/w/api.php'
_TIMEOUT = 12

# Pré-candidatos / nomes frequentes nas eleições 2026 (referência + validação na mídia)
_REFERENCIAS_2026 = [
    {'nome': 'Luiz Inácio Lula da Silva', 'nome_abrev': 'Lula', 'partido': 'PT', 'categoria': 'presidente', 'aliases': ['Lula', 'Luiz Inácio']},
    {'nome': 'Jair Messias Bolsonaro', 'nome_abrev': 'Bolsonaro', 'partido': 'PL', 'categoria': 'presidente', 'aliases': ['Bolsonaro', 'Jair Bolsonaro']},
    {'nome': 'Tarcísio de Freitas', 'nome_abrev': 'Tarcísio', 'partido': 'Republicanos', 'categoria': 'governador', 'uf': 'SP', 'aliases': ['Tarcísio', 'Tarcisio de Freitas']},
    {'nome': 'Ciro Gomes', 'nome_abrev': 'Ciro', 'partido': 'PDT', 'categoria': 'presidente', 'aliases': ['Ciro Gomes', 'Ciro']},
    {'nome': 'Marina Silva', 'nome_abrev': 'Marina', 'partido': 'REDE', 'categoria': 'presidente', 'aliases': ['Marina Silva', 'Marina']},
    {'nome': 'Simone Tebet', 'nome_abrev': 'Simone', 'partido': 'MDB', 'categoria': 'presidente', 'aliases': ['Simone Tebet', 'Simone']},
    {'nome': 'Michelle Bolsonaro', 'nome_abrev': 'Michelle', 'partido': 'PL', 'categoria': 'presidente', 'aliases': ['Michelle Bolsonaro', 'Michelle']},
    {'nome': 'Romeu Zema', 'nome_abrev': 'Zema', 'partido': 'NOVO', 'categoria': 'governador', 'uf': 'MG', 'aliases': ['Romeu Zema', 'Zema']},
    {'nome': 'Eduardo Leite', 'nome_abrev': 'Leite', 'partido': 'PSDB', 'categoria': 'governador', 'uf': 'RS', 'aliases': ['Eduardo Leite', 'Leite']},
    {'nome': 'Flávio Dino', 'nome_abrev': 'Dino', 'partido': 'PSB', 'categoria': 'presidente', 'aliases': ['Flávio Dino', 'Flavio Dino', 'Dino']},
    {'nome': 'Ratinho Júnior', 'nome_abrev': 'Ratinho', 'partido': 'PSD', 'categoria': 'governador', 'uf': 'PR', 'aliases': ['Ratinho Júnior', 'Ratinho Junior', 'Ratinho']},
    {'nome': 'João Doria', 'nome_abrev': 'Doria', 'partido': 'PSDB', 'categoria': 'presidente', 'aliases': ['João Doria', 'Joao Doria', 'Doria']},
]

_PARTIDOS_BR = (
    'REPUBLICANOS', 'PODEMOS', 'SOLIDARIEDADE', 'PROGRESSISTAS',
    'UNIÃO', 'UNIAO', 'PSDB', 'PSOL', 'NOVO', 'REDE', 'PSB',
    'PDT', 'MDB', 'PSD', 'PT', 'PL', 'PP',
)

_CORES_AUTO = (
    '#6366f1', '#e63946', '#2196f3', '#10b981', '#f59e0b',
    '#8b5cf6', '#ef4444', '#06b6d4', '#2d6a4f', '#ff6b35',
    '#ffd60a', '#7209b7',
)

_STOP_TOKENS = frozenset({
    'Brasil', 'Eleições', 'Eleicoes', 'Eleição', 'Pesquisa', 'Datafolha',
    'Ipec', 'Quaest', 'Google', 'News', 'Presidente', 'Governador',
    'Senador', 'Deputado', 'Candidato', 'Candidatos', 'Pré', 'Pre',
    'Candidatura', 'Disputa', 'Campanha', 'Partido', 'Opinião', 'Opiniao',
    'Mercado', 'Economia', 'Política', 'Politica', 'Diz', 'Anuncia',
    'Critica', 'Crítica', 'Após', 'Apos', 'Sobre', 'Contra', 'Para',
    'Com', 'Sem', 'Mais', 'Menos', 'Novo', 'Nova', 'Primeira', 'Segundo',
})

_QUERY_TEMPLATES = {
    'presidente': [
        'pré-candidatos presidenciais 2026 Brasil',
        'candidatos presidente eleições 2026',
        'disputa presidencial 2026 Brasil',
        'corrida presidencial 2026',
    ],
    'governador': [
        'pré-candidatos governador {uf} eleições 2026',
        'candidatos governador {uf} 2026',
        'disputa governo {uf} 2026',
    ],
}


class DescobertaService:
    """Descobre candidatos mencionados na mídia e importa para o banco."""

    @staticmethod
    def _url_rss(termo: str) -> str:
        return (
            'https://news.google.com/rss/search?q='
            f'{quote_plus(termo)}&hl=pt-BR&gl=BR&ceid=BR:pt-419'
        )

    @staticmethod
    def _buscar_titulos(queries: list[str], max_por_query: int = 40) -> list[str]:
        titulos = []
        for q in queries:
            feed = feedparser.parse(DescobertaService._url_rss(q))
            for entry in feed.entries[:max_por_query]:
                t = re.sub(r'<[^>]+>', '', entry.get('title', '') or '').strip()
                if t:
                    titulos.append(t)
        return titulos

    @staticmethod
    def _contar_referencias(titulos: list[str], categoria: str, uf: str | None) -> Counter:
        contagem = Counter()
        texto = '\n'.join(titulos).lower()
        for ref in _REFERENCIAS_2026:
            if ref['categoria'] != categoria:
                continue
            if categoria_requer_uf(categoria):
                if (ref.get('uf') or '').upper() != (uf or '').upper():
                    continue
            for alias in ref.get('aliases', [ref['nome_abrev']]):
                n = len(re.findall(re.escape(alias.lower()), texto))
                if n:
                    contagem[ref['nome']] += n
        return contagem

    @staticmethod
    def _extrair_nomes_titulo(titulo: str) -> list[str]:
        """Extrai sequências tipo Nome Sobrenome de manchetes."""
        padrao = re.compile(
            r'\b([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç]+'
            r'(?: (?:de |da |do |dos |das |e )?[A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç]+){1,4})\b'
        )
        nomes = []
        for m in padrao.finditer(titulo):
            nome = m.group(1).strip()
            partes = nome.split()
            if any(p in _STOP_TOKENS for p in partes):
                continue
            if len(partes) < 2:
                continue
            if len(nome) > 60:
                continue
            nomes.append(nome)
        return nomes

    @staticmethod
    def _partido_do_texto(texto: str) -> str | None:
        if not texto:
            return None
        upper = texto.upper()
        for sigla in _PARTIDOS_BR:
            if re.search(rf'\b{re.escape(sigla)}\b', upper):
                return 'UNIÃO' if sigla == 'UNIAO' else sigla
        m = re.search(
            r'(?:partido|filia(?:do|da|ção)|membro)\s+(?:do\s+)?([A-ZÀ-Ú][\w\s]{2,30})',
            texto,
            re.I,
        )
        if m:
            cand = m.group(1).strip().split('.')[0].strip()
            if len(cand) <= 30:
                return cand
        return None

    @staticmethod
    def _enriquecer_wikipedia(nome: str) -> dict:
        """Busca nome completo, resumo e partido na Wikipedia pt."""
        resultado = {'nome': nome, 'partido': None, 'descricao': None}
        try:
            r = requests.get(
                _WIKI_API,
                params={
                    'action': 'query',
                    'generator': 'search',
                    'gsrsearch': nome,
                    'gsrlimit': 3,
                    'prop': 'extracts|pageprops',
                    'exintro': True,
                    'explaintext': True,
                    'exchars': 400,
                    'format': 'json',
                },
                headers={'User-Agent': _USER_AGENT},
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            pages = r.json().get('query', {}).get('pages', {})
            for page in pages.values():
                extract = page.get('extract', '') or ''
                title = page.get('title', nome)
                if not extract:
                    continue
                low = extract.lower()
                if 'polític' not in low and 'politic' not in low and 'presidente' not in low:
                    if 'governador' not in low and 'ministro' not in low and 'deputad' not in low:
                        continue
                resultado['nome'] = title.replace('_', ' ')
                resultado['descricao'] = extract[:300]
                resultado['partido'] = DescobertaService._partido_do_texto(extract)
                return resultado
        except requests.RequestException:
            pass
        return resultado

    @staticmethod
    def _ref_por_nome(nome: str) -> dict | None:
        nome_l = nome.lower()
        for ref in _REFERENCIAS_2026:
            if ref['nome'].lower() == nome_l:
                return ref
            for alias in ref.get('aliases', []):
                if alias.lower() in nome_l or nome_l in alias.lower():
                    return ref
        return None

    @staticmethod
    def _montar_queries(categoria: str, uf: str | None) -> list[str]:
        if categoria == 'governador' and uf:
            return [q.format(uf=uf) for q in _QUERY_TEMPLATES['governador']]
        return list(_QUERY_TEMPLATES.get(categoria, _QUERY_TEMPLATES['presidente']))

    @staticmethod
    def _candidatos_sugeridos(
        titulos: list[str],
        categoria: str,
        uf: str | None,
        min_mencoes: int,
        max_resultados: int,
    ) -> list[dict]:
        contagem_ref = DescobertaService._contar_referencias(titulos, categoria, uf)
        contagem_livre = Counter()
        for titulo in titulos:
            for nome in DescobertaService._extrair_nomes_titulo(titulo):
                contagem_livre[nome] += 1

        sugeridos: dict[str, dict] = {}

        for ref in _REFERENCIAS_2026:
            if ref['categoria'] != categoria:
                continue
            if categoria_requer_uf(categoria) and (ref.get('uf') or '').upper() != (uf or '').upper():
                continue
            mencoes = contagem_ref.get(ref['nome'], 0)
            if mencoes >= max(1, min_mencoes - 1):
                sugeridos[ref['nome']] = {
                    'nome': ref['nome'],
                    'nome_abrev': ref['nome_abrev'],
                    'partido': ref['partido'],
                    'categoria': ref['categoria'],
                    'uf': ref.get('uf'),
                    'mencoes': mencoes,
                    'fonte': 'referencia+midia',
                    'confianca': 'alta',
                }

        for nome, mencoes in contagem_livre.most_common(max_resultados * 3):
            if mencoes < min_mencoes:
                continue
            if nome in sugeridos:
                continue
            ref = DescobertaService._ref_por_nome(nome)
            if ref:
                continue
            wiki = DescobertaService._enriquecer_wikipedia(nome)
            if not wiki.get('descricao'):
                continue
            sugeridos[wiki['nome']] = {
                'nome': wiki['nome'],
                'nome_abrev': wiki['nome'].split()[0][:40],
                'partido': wiki.get('partido') or 'A confirmar',
                'categoria': categoria,
                'uf': uf if categoria_requer_uf(categoria) else None,
                'mencoes': mencoes,
                'fonte': 'midia+wikipedia',
                'confianca': 'media' if mencoes >= min_mencoes + 1 else 'baixa',
            }

        ordenados = sorted(
            sugeridos.values(),
            key=lambda x: (-x['mencoes'], x['nome']),
        )
        return ordenados[:max_resultados]

    @staticmethod
    def analisar(
        categoria: str = 'presidente',
        uf: str | None = None,
        min_mencoes: int = 2,
        max_resultados: int = 12,
    ) -> dict:
        """Busca na web e retorna candidatos sugeridos (sem gravar)."""
        if categoria not in CandidatoService.CATEGORIAS_VALIDAS:
            raise ValueError(f'Categoria inválida: {categoria}')
        if categoria_requer_uf(categoria) and not uf:
            raise ValueError('Selecione o estado (UF) para este cargo.')

        queries = DescobertaService._montar_queries(categoria, uf)
        titulos = DescobertaService._buscar_titulos(queries)
        sugeridos = DescobertaService._candidatos_sugeridos(
            titulos, categoria, uf, min_mencoes, max_resultados,
        )

        ja_monitorados = []
        novos = []
        for s in sugeridos:
            if CandidatoService.existe_duplicata(s['nome'], s['categoria'], s.get('uf')):
                ja_monitorados.append(s)
            else:
                novos.append(s)

        return {
            'categoria': categoria,
            'uf': uf,
            'queries': queries,
            'noticias_lidas': len(titulos),
            'sugeridos': sugeridos,
            'novos': novos,
            'ja_monitorados': ja_monitorados,
        }

    @staticmethod
    def importar(
        categoria: str = 'presidente',
        uf: str | None = None,
        min_mencoes: int = 2,
        max_resultados: int = 10,
        coletar_noticias: bool = True,
        dias_coleta: int = 14,
        static_root: str | None = None,
    ) -> dict:
        """Descobre candidatos na web, cadastra novos e opcionalmente coleta notícias."""
        analise = DescobertaService.analisar(
            categoria=categoria,
            uf=uf,
            min_mencoes=min_mencoes,
            max_resultados=max_resultados,
        )

        resultado = {
            **{k: analise[k] for k in ('categoria', 'uf', 'queries', 'noticias_lidas')},
            'importados': [],
            'ignorados': analise['ja_monitorados'],
            'noticias_coletadas': 0,
            'erros': [],
        }

        cor_idx = Candidato.query.count()

        for sug in analise['novos']:
            try:
                cor = _CORES_AUTO[cor_idx % len(_CORES_AUTO)]
                cor_idx += 1
                cand = CandidatoService.criar(
                    nome=sug['nome'],
                    partido=sug['partido'],
                    categoria=sug['categoria'],
                    uf=sug.get('uf'),
                    cor=cor,
                    nome_abrev=sug.get('nome_abrev'),
                    buscar_foto=bool(static_root),
                    static_root=static_root,
                    gerar_noticias_exemplo=not coletar_noticias,
                )
                item = {
                    'nome': cand.nome,
                    'slug': cand.slug,
                    'partido': cand.partido,
                    'mencoes_midia': sug['mencoes'],
                    'confianca': sug['confianca'],
                    'foto': cand.tem_foto,
                    'noticias_importadas': 0,
                }
                if coletar_noticias:
                    r = ColetaService.coletar_candidato(
                        cand, dias=dias_coleta, max_itens=60,
                    )
                    item['noticias_importadas'] = r.get('importadas', 0)
                    resultado['noticias_coletadas'] += item['noticias_importadas']
                resultado['importados'].append(item)
            except ValueError as exc:
                resultado['erros'].append(f'{sug["nome"]}: {exc}')
            except Exception as exc:
                resultado['erros'].append(f'{sug["nome"]}: {exc}')

        return resultado
