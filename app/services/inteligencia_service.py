"""
Service: InteligenciaService
Detecta sinais acionaveis para decisao eleitoral.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta

from .noticia_service import NoticiaService

TIPOS_SINAL = (
    'ruptura_negativa',
    'aceleracao_positiva',
    'pico_visibilidade',
)

TEMAS_LABEL = {
    'economia': 'Economia',
    'saude': 'Saúde',
    'educacao': 'Educação',
    'violencia': 'Violência',
    'justica': 'Justiça',
    'politica': 'Política',
}


@dataclass
class InsightSignal:
    tipo: str
    candidato_id: int | None
    candidato: str
    severidade: str
    score: float
    resumo: str
    recomendacao: str
    variacao_pp: float
    persistencia_dias: int = 0
    tema: str | None = None


class InteligenciaService:
    """Calcula sinais de risco/oportunidade a partir das noticias."""

    @staticmethod
    def _comparar_janelas(candidato_id: int, dias: int, comparacao_dias: int) -> dict:
        janela = max(3, comparacao_dias)
        atual = NoticiaService.stats_candidato(candidato_id, dias=janela)
        anterior = NoticiaService.stats_candidato(candidato_id, dias=janela * 2)
        total_anterior_janela = max(0, anterior['total'] - atual['total'])

        if total_anterior_janela <= 0:
            return {
                'delta_pos': 0.0,
                'delta_neg': 0.0,
                'delta_vol': float(atual['total']),
                'base_total': total_anterior_janela,
            }

        fator = atual['total'] / max(1, anterior['total'])
        pos_prev = max(0.0, anterior['pct_positivo'] - (atual['pct_positivo'] * fator))
        neg_prev = max(0.0, anterior['pct_negativo'] - (atual['pct_negativo'] * fator))
        return {
            'delta_pos': round(atual['pct_positivo'] - pos_prev, 1),
            'delta_neg': round(atual['pct_negativo'] - neg_prev, 1),
            'delta_vol': float(atual['total'] - total_anterior_janela),
            'base_total': total_anterior_janela,
        }

    @staticmethod
    def _persistencia_dias(candidato_id: int, dias: int) -> int:
        """Dias consecutivos recentes com noticias no periodo."""
        por_dia = NoticiaService.contagem_por_dia_candidato(candidato_id, dias=dias)
        if not por_dia:
            return 0
        streak = 0
        d = date.today()
        desde = date.today() - timedelta(days=dias)
        while d >= desde:
            if por_dia.get(d, 0) > 0:
                streak += 1
            else:
                break
            d -= timedelta(days=1)
        return streak

    @staticmethod
    def score_prioridade(stats: dict, delta_neg: float, delta_vol: float,
                         persistencia: int = 0) -> float:
        volume = min(100.0, stats['total'] * 1.2)
        risco = max(0.0, stats['pct_negativo'] + (delta_neg * 1.5))
        momentum = max(-40.0, min(40.0, delta_vol))
        persist = min(20.0, persistencia * 2.5)
        return round(
            (volume * 0.30) + (risco * 0.50) + (max(0.0, momentum) * 0.10) + persist,
            1,
        )

    @staticmethod
    def gerar_sinais(
        candidatos: list,
        dias: int = 30,
        comparacao_dias: int | None = None,
        tipo_sinal: str | None = None,
    ) -> list[dict]:
        comp = comparacao_dias or dias
        sinais: list[InsightSignal] = []

        for c in candidatos:
            stats = NoticiaService.stats_candidato(c.id, dias=dias)
            if stats['total'] == 0:
                continue
            deltas = InteligenciaService._comparar_janelas(c.id, dias, comp)
            delta_neg = deltas['delta_neg']
            delta_pos = deltas['delta_pos']
            delta_vol = deltas['delta_vol']
            persistencia = InteligenciaService._persistencia_dias(c.id, dias)
            score = InteligenciaService.score_prioridade(
                stats, delta_neg, delta_vol, persistencia
            )

            candidato_sinais: list[InsightSignal] = []

            if delta_neg >= 8:
                candidato_sinais.append(InsightSignal(
                    tipo='ruptura_negativa',
                    candidato_id=c.id,
                    candidato=c.nome_abrev,
                    severidade='alta' if delta_neg >= 12 else 'media',
                    score=score,
                    resumo=(
                        f'{c.nome_abrev} piorou {delta_neg:.1f}pp em negatividade '
                        f'({persistencia} dia(s) com cobertura).'
                    ),
                    recomendacao='Revisar temas dominantes e preparar contranarrativa.',
                    variacao_pp=delta_neg,
                    persistencia_dias=persistencia,
                ))
            if delta_pos >= 8:
                candidato_sinais.append(InsightSignal(
                    tipo='aceleracao_positiva',
                    candidato_id=c.id,
                    candidato=c.nome_abrev,
                    severidade='alta' if delta_pos >= 12 else 'media',
                    score=score,
                    resumo=(
                        f'{c.nome_abrev} subiu {delta_pos:.1f}pp em positivo '
                        f'({persistencia} dia(s) com cobertura).'
                    ),
                    recomendacao='Amplificar narrativas de maior tracao em canais-chave.',
                    variacao_pp=delta_pos,
                    persistencia_dias=persistencia,
                ))
            if delta_vol >= 15:
                candidato_sinais.append(InsightSignal(
                    tipo='pico_visibilidade',
                    candidato_id=c.id,
                    candidato=c.nome_abrev,
                    severidade='media',
                    score=score,
                    resumo=f'{c.nome_abrev} ganhou forte volume ({delta_vol:.0f} noticias).',
                    recomendacao='Monitorar qualidade do volume para evitar ruido tatico.',
                    variacao_pp=round(delta_vol, 1),
                    persistencia_dias=persistencia,
                ))

            if tipo_sinal:
                candidato_sinais = [s for s in candidato_sinais if s.tipo == tipo_sinal]
            sinais.extend(candidato_sinais)

        sinais.sort(key=lambda s: s.score, reverse=True)
        return [asdict(s) for s in sinais]

    @staticmethod
    def ranking_risco_temas(
        categoria: str | None = None,
        uf: str | None = None,
        dias: int = 30,
    ) -> list[dict]:
        """Temas com maior concentracao de noticias negativas no periodo."""
        from ..models import Noticia
        from .candidato_service import CandidatoService

        candidatos = CandidatoService.listar_todos(categoria=categoria, uf=uf)
        ids = [c.id for c in candidatos]
        if not ids:
            return []

        desde = date.today() - timedelta(days=dias)
        desde_dt = datetime.combine(desde, datetime.min.time())
        ranking = []
        for tema, label in TEMAS_LABEL.items():
            q = Noticia.query.filter(
                Noticia.candidato_id.in_(ids),
                Noticia.tema == tema,
                Noticia.publicada_em >= desde_dt,
            )
            total = q.count()
            if total == 0:
                continue
            neg = q.filter(Noticia.sentimento == 'negativo').count()
            pct_neg = round(neg / total * 100, 1)
            ranking.append({
                'tema': tema,
                'label': label,
                'total': total,
                'pct_negativo': pct_neg,
            })
        ranking.sort(key=lambda r: (r['pct_negativo'], r['total']), reverse=True)
        return ranking[:6]
