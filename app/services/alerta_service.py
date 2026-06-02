"""
Service: AlertaService
Converte sinais de inteligencia em alertas priorizados.
"""
from __future__ import annotations

from datetime import date, timedelta

from .inteligencia_service import InteligenciaService, TEMAS_LABEL


class AlertaService:
    @staticmethod
    def _alertas_por_tema(
        candidatos: list,
        dias: int,
        categoria: str | None = None,
        uf: str | None = None,
    ) -> list[dict]:
        from ..models import Noticia
        from .candidato_service import CandidatoService
        from datetime import datetime

        ids = [c.id for c in candidatos] or [
            c.id for c in CandidatoService.listar_todos(categoria=categoria, uf=uf)
        ]
        if not ids:
            return []

        hoje = date.today()
        ini_atual = datetime.combine(hoje - timedelta(days=dias), datetime.min.time())
        ini_prev = datetime.combine(hoje - timedelta(days=dias * 2), datetime.min.time())
        fim_prev = ini_atual

        alertas = []
        for tema, label in TEMAS_LABEL.items():
            q_atual = Noticia.query.filter(
                Noticia.candidato_id.in_(ids),
                Noticia.tema == tema,
                Noticia.publicada_em >= ini_atual,
            )
            total_atual = q_atual.count()
            if total_atual < 3:
                continue
            neg_atual = q_atual.filter(Noticia.sentimento == 'negativo').count()
            pct_atual = neg_atual / total_atual * 100

            q_prev = Noticia.query.filter(
                Noticia.candidato_id.in_(ids),
                Noticia.tema == tema,
                Noticia.publicada_em >= ini_prev,
                Noticia.publicada_em < fim_prev,
            )
            total_prev = q_prev.count()
            pct_prev = 0.0
            if total_prev > 0:
                neg_prev = q_prev.filter(Noticia.sentimento == 'negativo').count()
                pct_prev = neg_prev / total_prev * 100

            delta = pct_atual - pct_prev
            if pct_atual >= 45 and delta >= 10:
                alertas.append({
                    'titulo': f'Tema {label}: pico de negatividade',
                    'nivel': 'critico' if pct_atual >= 60 else 'atencao',
                    'resumo': (
                        f'{label} com {pct_atual:.1f}% de noticias negativas '
                        f'(+{delta:.1f}pp vs janela anterior).'
                    ),
                    'recomendacao': 'Priorizar resposta tematica e monitoramento diario.',
                    'score': round(pct_atual + delta, 1),
                    'candidato_id': None,
                    'tema': tema,
                    'tipo': 'tema_negativo',
                })
        return alertas

    @staticmethod
    def gerar_alertas(
        candidatos: list,
        dias: int = 30,
        limite: int = 8,
        comparacao_dias: int | None = None,
        tipo_sinal: str | None = None,
        categoria: str | None = None,
        uf: str | None = None,
        incluir_temas: bool = True,
    ) -> list[dict]:
        sinais = InteligenciaService.gerar_sinais(
            candidatos,
            dias=dias,
            comparacao_dias=comparacao_dias,
            tipo_sinal=tipo_sinal,
        )
        alertas = []
        for s in sinais:
            nivel = 'critico' if s['severidade'] == 'alta' else 'atencao'
            alertas.append({
                'titulo': f"{s['candidato']}: {s['tipo'].replace('_', ' ')}",
                'nivel': nivel,
                'resumo': s['resumo'],
                'recomendacao': s['recomendacao'],
                'score': s['score'],
                'candidato_id': s['candidato_id'],
                'tipo': s['tipo'],
                'persistencia_dias': s.get('persistencia_dias', 0),
            })

        if incluir_temas and (not tipo_sinal or tipo_sinal == 'tema_negativo'):
            alertas.extend(
                AlertaService._alertas_por_tema(
                    candidatos, dias, categoria=categoria, uf=uf
                )
            )

        alertas.sort(key=lambda a: a['score'], reverse=True)
        return alertas[:limite]

    @staticmethod
    def contar_alertas(
        candidatos: list | None = None,
        dias: int = 30,
        categoria: str | None = None,
        uf: str | None = None,
    ) -> int:
        from .candidato_service import CandidatoService

        if candidatos is None:
            candidatos = CandidatoService.listar_todos(categoria=categoria, uf=uf)
        return len(AlertaService.gerar_alertas(
            candidatos, dias=dias, limite=99,
            categoria=categoria, uf=uf,
        ))
