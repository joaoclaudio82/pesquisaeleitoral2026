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
    def obter_todos_para_grafico(
        dias: int = 60,
        categoria: str | None = None,
        uf: str | None = None,
    ) -> dict:
        """
        Retorna dados formatados para Chart.js:
        {
            labels: ['01/01', '02/01', ...],
            candidatos: {
                slug: { nome, cor, aprovacoes: [...], rejeicoes: [...] }
            }
        }
        """
        from .candidato_service import CandidatoService
        from .noticia_service import NoticiaService

        desde = date.today() - timedelta(days=dias)
        candidatos = CandidatoService.listar_todos(categoria=categoria, uf=uf)

        # Gera eixo de datas
        labels = []
        d = desde
        while d <= date.today():
            labels.append(d.strftime('%d/%m'))
            d += timedelta(days=1)

        dados = {}
        for cand in candidatos:
            historicos = (Historico.query
                          .filter(
                              Historico.candidato_id == cand.id,
                              Historico.data >= desde,
                          )
                          .order_by(Historico.data.asc())
                          .all())

            stats = NoticiaService.stats_candidato(cand.id, dias=dias)
            por_dia_not = NoticiaService.contagem_por_dia_candidato(
                cand.id, dias=dias
            )

            # Indexar por data para lookup rápido
            por_data = {h.data.strftime('%d/%m'): h for h in historicos}

            aprovacoes = []
            rejeicoes  = []
            mencoes    = []
            noticias   = []
            d = desde
            while d <= date.today():
                lbl = d.strftime('%d/%m')
                h = por_data.get(lbl)
                aprovacoes.append(round(h.aprovacao, 1) if h else None)
                rejeicoes.append(round(h.rejeicao,  1) if h else None)
                mencoes.append(h.mencoes if h else 0)
                noticias.append(por_dia_not.get(d, 0))
                d += timedelta(days=1)

            dados[cand.slug] = {
                'nome':           cand.nome_abrev,
                'cor':            cand.cor,
                'aprovacoes':     aprovacoes,
                'rejeicoes':      rejeicoes,
                'mencoes':        mencoes,
                'noticias':       noticias,
                'total_noticias': stats['total'],
            }

        return {'labels': labels, 'candidatos': dados, 'dias': dias}

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
