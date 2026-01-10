"""
Import centralisé de tous les modèles.

Ce fichier importe tous les modèles pour que SQLAlchemy et Alembic
puissent découvrir les métadonnées de toutes les tables.

Usage dans Alembic (env.py):
    from app.models.base import Base
    target_metadata = Base.metadata

Usage pour créer les tables:
    from app.models.base import Base
    from app.database.session import engine
    Base.metadata.create_all(bind=engine)
"""

# Import de la classe Base depuis le module database
from app.database.base_class import Base

# Import de tous les modèles pour enregistrer leurs métadonnées
# L'ordre est important : les tables référencées doivent être importées en premier

# =============================================================================
# 1. Tables de référence (sans dépendances)
# =============================================================================
from app.models.reference.country import Country

# =============================================================================
# 2. Tables utilisateurs (dépendances simples)
# =============================================================================
from app.models.user.profession import Profession
from app.models.user.role import Role

# =============================================================================
# 3. Tables d'organisation
# =============================================================================
from app.models.organization.entity import Entity  # dépend de Country

# =============================================================================
# 4. Tables utilisateurs (avec dépendances)
# =============================================================================
from app.models.user.user import User  # dépend de Profession

# =============================================================================
# 5. Tables de jonction utilisateurs
# =============================================================================
from app.models.user.user_associations import (
    UserRole,   # dépend de User, Role
    UserEntity, # dépend de User, Entity
)

# =============================================================================
# 6. Tables patient (ordre important pour les dépendances)
# =============================================================================
from app.models.patient.patient import Patient  # dépend de User, Entity

from app.models.patient.patient_access import PatientAccess  # dépend de Patient, User

from app.models.patient.patient_evaluation import PatientEvaluation  # dépend de Patient, User

from app.models.patient.patient_vitals import (
    PatientThreshold,  # dépend de Patient
    PatientDevice,     # dépend de Patient
    PatientVitals,     # dépend de Patient, PatientDevice, User
)

from app.models.patient.patient_document import PatientDocument  # dépend de Patient, User, PatientEvaluation

# =============================================================================
# 7. Tables de coordination
# =============================================================================
from app.models.coordination.coordination_entry import CoordinationEntry  # dépend de Patient, User


# =============================================================================
# Export
# =============================================================================
__all__ = [
    # Base SQLAlchemy
    "Base",
    # Référence
    "Country",
    # Utilisateurs
    "Profession",
    "Role",
    "User",
    "UserRole",
    "UserEntity",
    # Organisation
    "Entity",
    # Patients
    "Patient",
    "PatientAccess",
    "PatientEvaluation",
    "PatientThreshold",
    "PatientDevice",
    "PatientVitals",
    "PatientDocument",
    # Coordination
    "CoordinationEntry",
]