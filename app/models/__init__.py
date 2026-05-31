"""
Models — camada de dados (M do MVC).
Exporta todos os modelos para facilitar importações.
"""
from .candidato import Candidato
from .noticia   import Noticia
from .historico import Historico
from .usuario   import Usuario

__all__ = ['Candidato', 'Noticia', 'Historico', 'Usuario']
