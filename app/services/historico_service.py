"""
Service: HistoricoService
Geração e consulta da série histórica de métricas por candidato.
"""
import random
from datetime import date, datetime, timedelta
from ..database import db
from ..models   import Historico


class HistoricoService:
    """Serviço responsável pela série histórica de candidatos."""

    # ── Consultas ─────────────────────────────────────────────────────────

    @staticmethod
    def obter(candidato_id: int, dias: int = 60) -> list[Historico]:
        """Retorna os últimos N dias de histórico de um candidato."""
        desde = date.today() - timedelta(days=dias)
        return (Historico.query
                .filter(
                    Historico.candidato_id == candidato_id,
                    Historico.data >= desde,
                )
                .order_by(Historico.data.asc())
                .all())

    @staticmethod
    def _propagar_serie(valores: list[float | None]) -> list[float | None]:
        """Repete o último valor medido em buckets sem notícia (continuidade visual)."""
        out: list[float | None] = []
        ultimo: float | None = None
        for v in valores:
            if v is not None:
                ultimo = v
            out.append(ultimo)
        return out

    @staticmethod
    def obter_todos_para_grafico(
        dias: int = 60,
        categoria: str | None = None,
        uf: str | None = None,
    ) -> dict:
        """
        Retorna dados formatados para Chart.js com base nas notícias coletadas.
        ≤14 dias: buckets diários; >14 dias: buckets semanais.
        Aprovação/rejeição = % de sentimento positivo/negativo no bucket.
        """
        from .candidato_service import CandidatoService
        from .noticia_service import NoticiaService
        from ..models import Noticia

        candidatos = CandidatoService.listar_todos(categoria=categoria, uf=uf)
        buckets = NoticiaService._gerar_buckets(dias)
        labels = [b[0] for b in buckets]
        granularidade = NoticiaService._granularidade(dias)

        dados = {}
        for cand in candidatos:
            aprovacoes: list[float | None] = []
            rejeicoes: list[float | None] = []
            noticias: list[int] = []

            for _, ini, fim in buckets:
                noticias_bucket = (Noticia.query
                                   .filter(
                                       Noticia.candidato_id == cand.id,
                                       Noticia.publicada_em >= ini,
                                       Noticia.publicada_em <= fim,
                                   )
                                   .all())
                total = len(noticias_bucket)
                noticias.append(total)

                if total == 0:
                    aprovacoes.append(None)
                    rejeicoes.append(None)
                else:
                    pos, neg, _ = NoticiaService._contar_sentimentos_noticias(
                        noticias_bucket
                    )
                    aprovacoes.append(round(pos / total * 100, 1))
                    rejeicoes.append(round(neg / total * 100, 1))

            stats = NoticiaService.stats_candidato(cand.id, dias=dias)

            dados[cand.slug] = {
                'nome':           cand.nome_abrev,
                'cor':            cand.cor,
                'aprovacoes':     HistoricoService._propagar_serie(aprovacoes),
                'rejeicoes':      HistoricoService._propagar_serie(rejeicoes),
                'aprovacoes_raw': aprovacoes,
                'rejeicoes_raw':  rejeicoes,
                'mencoes':        noticias,
                'noticias':       noticias,
                'total_noticias': stats['total'],
            }

        return {
            'labels': labels,
            'candidatos': dados,
            'dias': dias,
            'granularidade': granularidade,
        }

    # ── Mutações ──────────────────────────────────────────────────────────

    @staticmethod
    def registrar_dia(candidato) -> Historico:
        """
        Insere ou atualiza o snapshot do dia atual para o candidato.
        Usa upsert via constraint única (candidato_id, data).
        """
        hoje = date.today()
        h = (Historico.query
             .filter_by(candidato_id=candidato.id, data=hoje)
             .first())

        if h:
            h.aprovacao = round(candidato.aprovacao, 1)
            h.rejeicao  = round(candidato.rejeicao, 1)
            h.neutro    = round(candidato.neutro, 1)
            h.mencoes   = candidato.mencoes
        else:
            h = Historico(
                candidato_id = candidato.id,
                data         = hoje,
                aprovacao    = round(candidato.aprovacao, 1),
                rejeicao     = round(candidato.rejeicao, 1),
                neutro       = round(candidato.neutro, 1),
                mencoes      = candidato.mencoes,
            )
            db.session.add(h)

        return h

    @staticmethod
    def gerar_historico(candidato, dias: int = 60) -> list[Historico]:
        """
        Gera uma série histórica simulada para os últimos `dias` dias.
        Usada ao criar um novo candidato ou popular o banco pela primeira vez.
        """
        historicos = []
        aprovacao  = candidato.aprovacao
        tendencia  = candidato.tendencia

        # Ponto de partida ajustado pela tendência
        if tendencia == 'up':
            aprovacao -= 8
        elif tendencia == 'down':
            aprovacao += 8

        for i in range(dias, -1, -1):
            data_dia = date.today() - timedelta(days=i)

            # Variação com drift tendencial
            drift = 0.12 if tendencia == 'up' else (-0.12 if tendencia == 'down' else 0)
            variacao  = random.gauss(drift, 0.8)
            aprovacao = max(8.0, min(72.0, aprovacao + variacao))
            rejeicao  = max(12.0, min(78.0,
                            100 - aprovacao - random.uniform(8, 20)))
            neutro    = max(4.0, round(100 - aprovacao - rejeicao, 1))

            # Evita duplicata
            existe = Historico.query.filter_by(
                candidato_id=candidato.id, data=data_dia
            ).first()
            if not existe:
                h = Historico(
                    candidato_id = candidato.id,
                    data         = data_dia,
                    aprovacao    = round(aprovacao, 1),
                    rejeicao     = round(rejeicao, 1),
                    neutro       = round(neutro, 1),
                    mencoes      = random.randint(30, 300),
                )
                db.session.add(h)
                historicos.append(h)

        return historicos

    @staticmethod
    def calcular_tendencia(candidato) -> str:
        """
        Calcula tendência comparando média dos últimos 7 dias
        com a dos 7 dias anteriores.
        """
        hoje = date.today()
        semana_nova = (Historico.query
                       .filter(
                           Historico.candidato_id == candidato.id,
                           Historico.data > hoje - timedelta(days=7),
                       ).all())
        semana_velha = (Historico.query
                        .filter(
                            Historico.candidato_id == candidato.id,
                            Historico.data > hoje - timedelta(days=14),
                            Historico.data <= hoje - timedelta(days=7),
                        ).all())

        if not semana_nova or not semana_velha:
            return candidato.tendencia  # sem dados suficientes

        media_nova  = sum(h.aprovacao for h in semana_nova)  / len(semana_nova)
        media_velha = sum(h.aprovacao for h in semana_velha) / len(semana_velha)
        diff = media_nova - media_velha

        if diff > 0.8:
            return 'up'
        if diff < -0.8:
            return 'down'
        return 'stable'
