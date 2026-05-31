"""
Service: TendenciaService
Períodos e normalização para a página de Tendências.
"""


class TendenciaService:
    """Configuração de filtros temporais da análise de tendências."""

    PERIODOS = [
        (7,   '7 dias'),
        (14,  '14 dias'),
        (30,  '30 dias'),
        (60,  '60 dias'),
        (90,  '90 dias'),
        (120, '120 dias'),
        (180, '180 dias'),
    ]

    PERIODOS_VALIDOS = {p[0] for p in PERIODOS}
    DIAS_PADRAO = 60

    @staticmethod
    def normalizar_periodo(dias: int) -> int:
        return dias if dias in TendenciaService.PERIODOS_VALIDOS else TendenciaService.DIAS_PADRAO

    @staticmethod
    def periodo_label(dias: int) -> str:
        return dict(TendenciaService.PERIODOS).get(dias, f'{dias} dias')
