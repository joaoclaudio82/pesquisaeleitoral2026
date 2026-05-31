"""
Services — lógica de negócio da aplicação.
Intermediários entre Controllers e Models.
"""
from .candidato_service  import CandidatoService
from .noticia_service    import NoticiaService
from .historico_service  import HistoricoService
from .dashboard_service  import DashboardService
from .coleta_service     import ColetaService
from .usuario_service    import UsuarioService
from .schema_service     import SchemaService
from .tendencia_service  import TendenciaService
from .foto_service       import FotoService
from .descoberta_service import DescobertaService

__all__ = [
    'CandidatoService',
    'NoticiaService',
    'HistoricoService',
    'DashboardService',
    'ColetaService',
    'UsuarioService',
    'SchemaService',
    'TendenciaService',
    'FotoService',
    'DescobertaService',
]
