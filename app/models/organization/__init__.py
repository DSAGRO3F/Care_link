"""
Organization models - Structure organisationnelle.

Ce module contient les modèles liés à l'organisation :
- Entity : Entités de soins (SSIAD, EHPAD, SAAD...)
- Organization : Groupements (GCSMS) - à venir
"""

from app.models.organization.entity import Entity

__all__ = [
    "Entity",
]
