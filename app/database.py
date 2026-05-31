"""
Instância única do SQLAlchemy.
Importada pelos Models e pelo factory (create_app).
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
