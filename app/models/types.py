"""
Types SQLAlchemy personnalisés pour CareLink.

Ce module définit des types compatibles SQLite (tests) et PostgreSQL (production).
"""

from sqlalchemy import JSON, Text
from sqlalchemy.dialects.postgresql import JSONB


# ============================================================================
# JSONBCompatible - Type JSON compatible multi-dialecte
# ============================================================================
#
# Utilise with_variant() pour une compatibilité native avec Alembic.
#
# - Sur PostgreSQL : utilise JSONB (indexable, performant, opérateurs @>, ?, etc.)
# - Sur SQLite/autres : utilise JSON standard
#
# Usage dans les modèles:
#     from app.models.types import JSONBCompatible
#
#     class MyModel(Base):
#         data: Mapped[dict] = mapped_column(JSONBCompatible, nullable=False, default=dict)
#
# Avantages de with_variant vs TypeDecorator:
#   1. Alembic génère automatiquement les bonnes migrations
#   2. Pas de sérialisation/désérialisation manuelle
#   3. Support natif des opérateurs JSONB PostgreSQL
#
# ============================================================================

JSONBCompatible = JSON().with_variant(JSONB(astext_type=Text()), 'postgresql')


# ============================================================================
# Alias pour clarté sémantique
# ============================================================================

# Pour les colonnes qui stockent des paramètres/configuration
JSONSettings = JSONBCompatible

# Pour les colonnes qui stockent des données d'évaluation structurées
JSONEvaluationData = JSONBCompatible

# Pour les colonnes qui stockent un contexte de génération
JSONContext = JSONBCompatible
