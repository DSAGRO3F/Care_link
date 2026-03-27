"""
Base de données SQLAlchemy - Configuration centrale
Importe tous les modèles pour que SQLAlchemy connaisse toutes les relations
"""

from app.database.base_class import Base

# === IMPORTS DES MODÈLES ===
# IMPORTANT : Tous les modèles doivent être importés ici pour que :
# 1. SQLAlchemy connaisse toutes les relations entre tables
# 2. Alembic puisse détecter tous les modèles pour les migrations
# 3. Les métadonnées soient complètes lors de create_all()
# Import centralisé depuis app/models/__init__.py
from app.models import (  # noqa: F401
    INITIAL_PERMISSIONS,
    INITIAL_PROFESSIONS,
    INITIAL_ROLE_PERMISSIONS,
    INITIAL_ROLES,
    AccessType,
    AuditMixin,
    # CarePlan
    CarePlan,
    CarePlanService,
    ContractType,
    # Coordination
    CoordinationEntry,
    # Reference
    Country,
    DeviceType,
    # Organization
    Entity,
    EntityService,
    # Enums
    EntityType,
    EvaluationSchemaType,
    # Patient
    Patient,
    PatientAccess,
    PatientDevice,
    PatientDocument,
    PatientEvaluation,
    PatientStatus,
    PatientThreshold,
    PatientVitals,
    Permission,
    PlatformAuditLog,
    Profession,
    ProfessionCategory,
    Role,
    RoleName,
    RolePermission,
    ScheduledIntervention,
    # Catalog
    ServiceTemplate,
    StatusMixin,
    Subscription,
    SubscriptionUsage,
    # Platform
    SuperAdmin,
    # Tenant
    Tenant,
    # Mixins
    TimestampMixin,
    # User
    User,
    UserAvailability,
    UserEntity,
    UserRole,
    UserTenantAssignment,
    VersionedMixin,
    VitalSource,
    VitalStatus,
    VitalType,
)

# Import EvaluationSession (manquant dans app/models/__init__.py)
from app.models.patient import EvaluationSession  # noqa: F401


# Note : Le noqa: F401 supprime l'avertissement "imported but unused"
# Ces imports sont volontairement "inutilisés" ici mais essentiels pour SQLAlchemy


# === MÉTADONNÉES ===
metadata = Base.metadata


# === FONCTIONS UTILITAIRES ===


def get_all_models() -> list:
    """Retourne la liste de tous les modèles SQLAlchemy enregistrés."""
    return [mapper.class_ for mapper in Base.registry.mappers]


def get_table_names() -> list[str]:
    """Retourne la liste des noms de toutes les tables."""
    return list(metadata.tables.keys())


def print_database_schema() -> None:
    """Affiche un résumé du schéma de la base de données."""
    print("\n=== SCHÉMA BASE DE DONNÉES CARELINK ===\n")

    tables = get_table_names()
    print(f"Tables ({len(tables)}):")
    for table in sorted(tables):
        print(f"  - {table}")

    models = get_all_models()
    print(f"\nModèles ({len(models)}):")
    for model in sorted(models, key=lambda m: m.__name__):
        print(f"  - {model.__name__}")

    print("\n" + "=" * 40 + "\n")
