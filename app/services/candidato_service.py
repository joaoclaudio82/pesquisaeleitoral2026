"""
Service: CandidatoService
Toda a lógica de negócio relacionada a candidatos.
"""
import random
from datetime import datetime
from slugify import slugify

from ..constants import CATEGORIAS, categoria_requer_uf
from ..database import db
from ..models   import Candidato, Historico, Noticia
from .historico_service import HistoricoService
from .foto_service import FotoService


class CandidatoService:
    """Serviço responsável por operações sobre Candidato."""

    CATEGORIAS_VALIDAS = {c[0] for c in CATEGORIAS}

    # ── Consultas ─────────────────────────────────────────────────────────

    @staticmethod
    def _aplicar_filtros(q, categoria: str | None = None, uf: str | None = None):
        if categoria:
            q = q.filter(Candidato.categoria == categoria)
        if uf:
            q = q.filter(Candidato.uf == uf.upper())
        return q

    @staticmethod
    def listar_todos(
        apenas_ativos: bool = True,
        categoria: str | None = None,
        uf: str | None = None,
    ) -> list[Candidato]:
        """Retorna candidatos ordenados por aprovação decrescente."""
        q = Candidato.query
        if apenas_ativos:
            q = q.filter_by(ativo=True)
        q = CandidatoService._aplicar_filtros(q, categoria, uf)
        return q.order_by(Candidato.aprovacao.desc()).all()

    @staticmethod
    def ids_filtrados(categoria: str | None = None, uf: str | None = None) -> list[int]:
        """IDs de candidatos ativos, opcionalmente filtrados por cargo/UF."""
        q = db.session.query(Candidato.id).filter(Candidato.ativo == True)
        q = CandidatoService._aplicar_filtros(q, categoria, uf)
        return [row[0] for row in q.all()]

    @staticmethod
    def buscar_por_id(candidato_id: int) -> Candidato | None:
        return Candidato.query.get(candidato_id)

    @staticmethod
    def buscar_por_slug(slug: str) -> Candidato | None:
        return Candidato.query.filter_by(slug=slug, ativo=True).first()

    @staticmethod
    def buscar(
        termo: str,
        categoria: str | None = None,
        uf: str | None = None,
    ) -> list[Candidato]:
        """Busca candidatos pelo nome ou partido."""
        like = f'%{termo}%'
        q = (Candidato.query
             .filter(
                 db.or_(
                     Candidato.nome.ilike(like),
                     Candidato.partido.ilike(like),
                     Candidato.nome_abrev.ilike(like),
                 ),
                 Candidato.ativo == True,
             ))
        q = CandidatoService._aplicar_filtros(q, categoria, uf)
        return q.order_by(Candidato.aprovacao.desc()).all()

    @staticmethod
    def existe_duplicata(
        nome: str,
        categoria: str,
        uf: str | None,
        excluir_id: int | None = None,
    ) -> bool:
        q = Candidato.query.filter(
            Candidato.nome.ilike(nome),
            Candidato.categoria == categoria,
            Candidato.ativo == True,
        )
        if excluir_id:
            q = q.filter(Candidato.id != excluir_id)
        if uf:
            q = q.filter(Candidato.uf == uf.upper())
        else:
            q = q.filter(Candidato.uf.is_(None))
        return q.first() is not None

    @staticmethod
    def _normalizar_cor(cor: str) -> str:
        cor = (cor or '#6366f1').strip()
        if not cor.startswith('#'):
            cor = f'#{cor}'
        if len(cor) == 7:
            return cor.lower()
        return '#6366f1'

    # ── Mutações ──────────────────────────────────────────────────────────

    @staticmethod
    def criar(
        nome: str,
        partido: str,
        categoria: str = 'presidente',
        uf: str | None = None,
        cor: str = '#6366f1',
        temas: list[str] | None = None,
        nome_abrev: str | None = None,
        buscar_foto: bool = True,
        static_root: str | None = None,
    ) -> Candidato:
        """
        Cria um novo candidato, gera slug único, persiste no banco
        e cria histórico de 60 dias.
        """
        if categoria not in CandidatoService.CATEGORIAS_VALIDAS:
            raise ValueError(f'Categoria inválida: {categoria}')

        uf = uf.upper() if uf else None
        if categoria_requer_uf(categoria) and not uf:
            raise ValueError('Estado (UF) é obrigatório para este cargo.')
        if not categoria_requer_uf(categoria):
            uf = None

        if temas is None:
            temas_disponiveis = ['economia', 'saude', 'educacao',
                                  'violencia', 'justica', 'politica']
            temas = random.sample(temas_disponiveis, k=random.randint(2, 4))

        slug_base  = slugify(f'{nome}-{categoria}' + (f'-{uf}' if uf else ''))
        slug_final = CandidatoService._slug_unico(slug_base)

        aprovacao = round(random.uniform(18, 38), 1)
        rejeicao  = round(random.uniform(25, 50), 1)
        rejeicao  = min(rejeicao, 100 - aprovacao - 5)
        neutro    = round(100 - aprovacao - rejeicao, 1)
        tendencia = random.choice(['up', 'down', 'stable'])

        abrev = (nome_abrev or nome.split()[0]).strip()[:40] or nome[:40]

        candidato = Candidato(
            slug       = slug_final,
            nome       = nome,
            nome_abrev = abrev,
            partido    = partido or 'Independente',
            cor        = CandidatoService._normalizar_cor(cor),
            categoria  = categoria,
            uf         = uf,
            aprovacao  = aprovacao,
            rejeicao   = rejeicao,
            neutro     = neutro,
            mencoes    = random.randint(50, 300),
            tendencia  = tendencia,
            temas_csv  = ','.join(temas),
        )

        db.session.add(candidato)
        db.session.flush()

        HistoricoService.gerar_historico(candidato, dias=60)
        CandidatoService._gerar_noticias_iniciais(candidato)

        if buscar_foto and static_root:
            CandidatoService.atualizar_foto(candidato, static_root, commit=False)

        db.session.commit()
        return candidato

    @staticmethod
    def atualizar(
        candidato: Candidato,
        nome: str,
        nome_abrev: str,
        partido: str,
        categoria: str,
        uf: str | None,
        cor: str,
        temas: list[str] | None = None,
    ) -> Candidato:
        """Atualiza dados cadastrais do candidato (slug permanece o mesmo)."""
        if categoria not in CandidatoService.CATEGORIAS_VALIDAS:
            raise ValueError(f'Categoria inválida: {categoria}')

        uf = uf.upper() if uf else None
        if categoria_requer_uf(categoria) and not uf:
            raise ValueError('Estado (UF) é obrigatório para este cargo.')
        if not categoria_requer_uf(categoria):
            uf = None

        abrev = (nome_abrev or nome.split()[0]).strip()[:40] or nome[:40]

        candidato.nome       = nome.strip()
        candidato.nome_abrev = abrev
        candidato.partido    = partido.strip() or 'Independente'
        candidato.categoria  = categoria
        candidato.uf         = uf
        candidato.cor        = CandidatoService._normalizar_cor(cor)
        if temas is not None:
            candidato.temas = temas
        candidato.atualizado_em = datetime.utcnow()

        db.session.commit()
        return candidato

    @staticmethod
    def atualizar_foto(
        candidato: Candidato,
        static_root: str,
        commit: bool = True,
    ) -> bool:
        """Busca foto na Wikipedia e salva localmente."""
        path = FotoService.buscar_e_salvar(
            static_root,
            candidato.slug,
            candidato.nome,
            candidato.partido,
            candidato.categoria,
        )
        if not path:
            return False
        candidato.foto_url = path
        candidato.atualizado_em = datetime.utcnow()
        if commit:
            db.session.commit()
        return True

    @staticmethod
    def remover_foto(candidato: Candidato, static_root: str) -> None:
        FotoService.remover_foto_local(static_root, candidato.slug)
        candidato.foto_url = None
        candidato.atualizado_em = datetime.utcnow()
        db.session.commit()

    @staticmethod
    def atualizar_metricas(candidato: Candidato) -> Candidato:
        """
        Simula uma rodada de coleta: aplica variação aleatória nas métricas
        e salva o snapshot do dia no histórico.
        """
        variacao = random.uniform(-1.5, 1.5)
        candidato.aprovacao = max(5.0,  min(75.0, candidato.aprovacao + variacao))
        candidato.rejeicao  = max(10.0, min(80.0, candidato.rejeicao  - variacao * 0.7))
        candidato.neutro    = max(5.0,  round(100 - candidato.aprovacao - candidato.rejeicao, 1))
        candidato.mencoes  += random.randint(5, 30)
        candidato.atualizado_em = datetime.utcnow()

        candidato.tendencia = HistoricoService.calcular_tendencia(candidato)

        HistoricoService.registrar_dia(candidato)
        db.session.commit()
        return candidato

    @staticmethod
    def atualizar_todos(
        categoria: str | None = None,
        uf: str | None = None,
    ) -> list[Candidato]:
        """Atualiza métricas de candidatos ativos (com filtros opcionais)."""
        candidatos = CandidatoService.listar_todos(categoria=categoria, uf=uf)
        for c in candidatos:
            CandidatoService.atualizar_metricas(c)
        return candidatos

    @staticmethod
    def desativar(candidato_id: int) -> bool:
        c = CandidatoService.buscar_por_id(candidato_id)
        if not c:
            return False
        c.ativo = False
        db.session.commit()
        return True

    # ── Helpers privados ──────────────────────────────────────────────────

    @staticmethod
    def _slug_unico(base: str) -> str:
        slug = base
        contador = 1
        while Candidato.query.filter_by(slug=slug).first():
            slug = f'{base}-{contador}'
            contador += 1
        return slug

    @staticmethod
    def _gerar_noticias_iniciais(candidato: Candidato) -> None:
        """Cria 3-5 notícias de exemplo para um candidato recém-adicionado."""
        from datetime import timedelta

        fontes = ['G1 / Globo', 'UOL Notícias', 'Folha de S.Paulo',
                  'CNN Brasil', 'O Globo', 'Estadão']
        temas  = candidato.temas or ['politica']
        sentimentos = ['positivo', 'positivo', 'neutro', 'negativo', 'neutro']
        escopo = candidato.uf_label if candidato.uf else 'Brasil'

        titulos = [
            f'{candidato.nome_abrev} apresenta plano para {candidato.categoria_label}',
            f'Pesquisa aponta crescimento de {candidato.nome_abrev} em {escopo}',
            f'{candidato.nome_abrev} participa de debate eleitoral',
            f'Críticas à posição de {candidato.nome_abrev} sobre reforma tributária',
            f'Aliados de {candidato.nome_abrev} intensificam campanha',
        ]
        resumo_base = (
            f'O candidato {candidato.nome} ({candidato.categoria_label}'
            f'{f" — {candidato.uf}" if candidato.uf else ""}) '
            f'do partido {candidato.partido} demonstrou posição firme '
            f'sobre os principais temas da agenda política.'
        )

        for i in range(random.randint(3, 5)):
            n = Noticia(
                candidato_id = candidato.id,
                titulo       = titulos[i % len(titulos)],
                resumo       = resumo_base,
                fonte        = random.choice(fontes),
                sentimento   = sentimentos[i % len(sentimentos)],
                tema         = random.choice(temas),
                relevancia   = random.randint(50, 90),
                publicada_em = datetime.utcnow() - timedelta(hours=i * 4),
            )
            db.session.add(n)
