"""
Import centralisé de tous les modèles.

Ce fichier importe tous les modèles pour que SQLAlchemy et Alembic
puissent découvrir les métadonnées de toutes les tables.

Usage dans Alembic (env.py):
    from app.database.base_class import Base
    target_metadata = Base.metadata

Usage pour créer les tables:
    from app.database.base_class import Base
    from app.database.session import engine
    Base.metadata.create_all(bind=engine)

Changelog:
    v4.3: Déplacement UserTenantAssignment de platform/ vers user/
"""

# Import de la classe Base depuis le module database
from app.database.base_class import Base
# =============================================================================
# 10. Tables plans d'aide
# =============================================================================
from app.models.careplan.care_plan import CarePlan  # dépend de Patient, Entity, User, PatientEvaluation, Tenant
from app.models.careplan.care_plan_service import CarePlanService  # dépend de CarePlan, ServiceTemplate, User, Tenant
from app.models.catalog.entity_service import EntityService  # dépend de Entity, ServiceTemplate, Tenant
# =============================================================================
# 9. Tables catalogue de services
# =============================================================================
from app.models.catalog.service_template import ServiceTemplate  # dépend de Profession
# =============================================================================
# 11. Tables de coordination
# =============================================================================
from app.models.coordination.coordination_entry import CoordinationEntry  # dépend de Patient, User, Tenant
from app.models.coordination.scheduled_intervention import \
    ScheduledIntervention  # dépend de CarePlanService, Patient, User, Tenant
# =============================================================================
# 5. Tables d'organisation
# =============================================================================
from app.models.organization.entity import Entity  # dépend de Country, Tenant
from app.models.patient.evaluation_session import EvaluationSession
# =============================================================================
# 8. Tables patient (ordre important pour les dépendances)
# =============================================================================
from app.models.patient.patient import Patient  # dépend de User, Entity, Tenant
from app.models.patient.patient_access import PatientAccess  # dépend de Patient, User, Tenant
from app.models.patient.patient_document import PatientDocument  # dépend de Patient, User, PatientEvaluation, Tenant
from app.models.patient.patient_evaluation import PatientEvaluation  # dépend de Patient, User, Tenant
from app.models.patient.patient_vitals import (
    PatientThreshold,  # dépend de Patient, Tenant
    PatientDevice,  # dépend de Patient, Tenant
    PatientVitals,  # dépend de Patient, PatientDevice, User, Tenant
)
from app.models.platform.platform_audit_log import PlatformAuditLog
# =============================================================================
# 3. Tables platform (super-admins CareLink)
# =============================================================================
from app.models.platform.super_admin import SuperAdmin
# =============================================================================
# 1. Tables de référence (sans dépendances)
# =============================================================================
from app.models.reference.country import Country
from app.models.tenants.subscription import Subscription
from app.models.tenants.subscription_usage import SubscriptionUsage
# =============================================================================
# 2. Tables multi-tenant (avant tout ce qui a tenant_id)
# =============================================================================
from app.models.tenants.tenant import Tenant
from app.models.user.permission import Permission  # v4.3 - avant Role
# =============================================================================
# 4. Tables utilisateurs (dépendances simples)
# =============================================================================
from app.models.user.profession import Profession
from app.models.user.role import Role
# =============================================================================
# 4.1 Tables de jonction rôles/permissions (v4.3)
# =============================================================================
from app.models.user.role_permission import RolePermission
# =============================================================================
# 6. Tables utilisateurs (avec dépendances)
# =============================================================================
from app.models.user.user import User  # dépend de Profession, Tenant
# =============================================================================
# 7. Tables de jonction utilisateurs
# =============================================================================
from app.models.user.user_associations import (
    UserRole,  # dépend de User, Role, Tenant
    UserEntity,  # dépend de User, Entity, Tenant
)
from app.models.user.user_availability import UserAvailability  # dépend de User, Entity, Tenant
from app.models.user.user_tenant_assignment import UserTenantAssignment  # Déplacé depuis platform/ v4.3

# Import de tous les modèles pour enregistrer leurs métadonnées
# L'ordre est important : les tables référencées doivent être importées en premier


# =============================================================================
# Export
# =============================================================================
__all__ = [
    # Base SQLAlchemy
    "Base",
    # Référence
    "Country",
    # Multi-tenant
    "Tenant",
    "Subscription",
    "SubscriptionUsage",
    # Platform
    "SuperAdmin",
    "PlatformAuditLog",
    # Utilisateurs et permissions (v4.3)
    "Profession",
    "Permission",
    "Role",
    "RolePermission",
    "User",
    "UserRole",
    "UserEntity",
    "UserAvailability",
    "UserTenantAssignment",
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
    "EvaluationSession",
    # Catalogue
    "ServiceTemplate",
    "EntityService",
    # Plans d'aide
    "CarePlan",
    "CarePlanService",
    # Coordination
    "CoordinationEntry",
    "ScheduledIntervention",
]