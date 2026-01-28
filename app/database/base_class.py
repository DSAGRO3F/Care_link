"""
Classe de base SQLAlchemy
Fichier séparé pour éviter les imports circulaires
"""
from sqlalchemy.orm import DeclarativeBase

# Class dont héritent tous les modèles
class Base(DeclarativeBase):
    pass