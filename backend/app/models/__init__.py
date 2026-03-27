"""
CareLink Models - Export centralisé de tous les modèles SQLAlchemy.

Ce fichier permet d'importer tous les modèles depuis un seul endroit :
    from app.models import User, Patient, Role, Permission, Tenant, SuperAdmin, ...

Structure des sous-dossiers :
    platform/       - Plateforme CareLink (SuperAdmin, PlatformAuditLog)
    tenants/        - Multi-tenant (Tenant, Subscription, SubscriptionUsage)
    organization/   - Structure organisationnelle (Entity)
    reference/      - Données de référence (Country)
    user/           - Utilisateurs et RH (User, Role, Permission, UserTenantAssignment, etc.)
    patient/        - Dossier patient (Patient, Evaluations, Vitals)
    coordination/   - Coordination des soins (CoordinationEntry, ScheduledIntervention)
    careplan/       - Plans d'aide (CarePlan, CarePlanService)
    catalog/        - Catalogue de services (ServiceTemplate, EntityService)

Changelog:
    v4.11: Ajout profession_permissions (S4 — permissions par profession)
    v4.3: Normalisation des permissions (Permission, RolePermission)
    v4.3: Déplacement UserTenantAssignment de platform/ vers user/
    v4.2: Ajout platform (SuperAdmin, PlatformAuditLog)
    v4.1: Ajout tenants (Tenant, Subscription)
"""

# === Modèles plans d'aide ===
from app.models.careplan.care_plan import CarePlan
from app.models.careplan.care_plan_service import CarePlanService
from app.models.catalog.entity_service import EntityService

# === Modèles catalogue ===
from app.models.catalog.service_template import INITIAL_SERVICE_TEMPLATES, ServiceTemplate

# === Modèles coordination ===
from app.models.coordination.coordination_entry import CoordinationEntry
from app.models.coordination.scheduled_intervention import ScheduledIntervention

# === Enums ===
from app.models.enums import (
    # Patients
    AccessType,
    AssignmentStatus,
    # Plans d'aide et interventions
    CarePlanStatus,
    ContractType,
    # Coordination et services
    CoordinationCategory,
    DeviceType,
    DocumentFormat,
    DocumentType,
    # Types d'entités et organisation
    EntityType,
    # Évaluations et documents
    EvaluationSchemaType,
    FrequencyType,
    GirLevel,
    IntegrationType,
    InterventionStatus,
    OrganizationModel,
    PatientStatus,
    PermissionCategory,  # v4.3
    # Professions et rôles
    ProfessionCategory,
    RoleName,
    ServiceCategory,
    ServicePriority,
    ServiceType,
    ServiceUnit,
    TerritoryType,
    VitalSource,
    VitalStatus,
    # Constantes vitales
    VitalType,
)

# === Mixins ===
from app.models.mixins import (
    AuditMixin,
    StatusMixin,
    TimestampMixin,
    VersionedMixin,
)

# === Modèles d'organisation ===
from app.models.organization.entity import Entity
from app.models.patient.evaluation_session import EvaluationSession

# === Modèles patients ===
from app.models.patient.patient import Patient
from app.models.patient.patient_access import PatientAccess
from app.models.patient.patient_document import PatientDocument
from app.models.patient.patient_evaluation import PatientEvaluation
from app.models.patient.patient_vitals import PatientDevice, PatientThreshold, PatientVitals

# === Modèles Platform (v4.2) ===
from app.models.platform import (
    AuditAction,
    PlatformAuditLog,
    SuperAdmin,
    SuperAdminRole,
)

# === Modèles de référence ===
from app.models.reference.country import Country

# === Modèles Tenant (v4.1) ===
from app.models.tenants import (
    BillingCycle,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    SubscriptionUsage,
    Tenant,
    TenantStatus,
    TenantType,
)
from app.models.user.permission import INITIAL_PERMISSIONS, Permission
from app.models.user.profession import INITIAL_PROFESSIONS, Profession
from app.models.user.profession_permissions import (  # S4
    PROFESSION_DEFAULT_PERMISSIONS,
    get_profession_permissions,
)
from app.models.user.role import INITIAL_ROLES, Role
from app.models.user.role_permission import INITIAL_ROLE_PERMISSIONS, RolePermission

# === Modèles utilisateurs et permissions (v4.3) ===
from app.models.user.user import User
from app.models.user.user_associations import UserEntity, UserRole
from app.models.user.user_availability import UserAvailability
from app.models.user.user_tenant_assignment import (
    AssignmentType,
    UserTenantAssignment,
)  # Déplacé depuis platform/ v4.3


# === Export explicite ===
__all__ = [
    "INITIAL_PERMISSIONS",
    "INITIAL_PROFESSIONS",
    "INITIAL_ROLES",
    "INITIAL_ROLE_PERMISSIONS",
    "INITIAL_SERVICE_TEMPLATES",
    "PROFESSION_DEFAULT_PERMISSIONS",  # S4
    # Patients
    "AccessType",
    "AssignmentStatus",
    "AssignmentType",
    "AuditAction",
    "AuditMixin",
    "BillingCycle",
    # Plans d'aide
    "CarePlan",
    "CarePlanService",
    # Plans d'aide et interventions
    "CarePlanStatus",
    "ContractType",
    # Coordination et services
    "CoordinationCategory",
    # Coordination
    "CoordinationEntry",
    # Référence
    "Country",
    "DeviceType",
    "DocumentFormat",
    "DocumentType",
    # Organisation
    "Entity",
    "EntityService",
    # --- Enums ---
    # Organisation
    "EntityType",
    # Évaluations et documents
    "EvaluationSchemaType",
    "EvaluationSession",
    "FrequencyType",
    "GirLevel",
    "IntegrationType",
    "InterventionStatus",
    "OrganizationModel",
    # Patients
    "Patient",
    "PatientAccess",
    "PatientDevice",
    "PatientDocument",
    "PatientEvaluation",
    "PatientStatus",
    "PatientThreshold",
    "PatientVitals",
    "Permission",
    "PermissionCategory",  # v4.3
    "PlatformAuditLog",
    "Profession",
    # Professions et rôles
    "ProfessionCategory",
    "Role",
    "RoleName",
    "RolePermission",
    "ScheduledIntervention",
    "ServiceCategory",
    "ServicePriority",
    # Catalogue
    "ServiceTemplate",
    "ServiceType",
    "ServiceUnit",
    "StatusMixin",
    "Subscription",
    "SubscriptionPlan",
    "SubscriptionStatus",
    "SubscriptionUsage",
    # --- Modèles ---
    # Platform (v4.2)
    "SuperAdmin",
    "SuperAdminRole",
    # Tenant (v4.1)
    "Tenant",
    "TenantStatus",
    "TenantType",
    "TerritoryType",
    # --- Mixins ---
    "TimestampMixin",
    # Utilisateurs et permissions (v4.3)
    "User",
    "UserAvailability",
    "UserEntity",
    "UserRole",
    "UserTenantAssignment",
    "VersionedMixin",
    "VitalSource",
    "VitalStatus",
    # Constantes vitales
    "VitalType",
    "get_profession_permissions",  # S4
]
