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
    v4.3: Normalisation des permissions (Permission, RolePermission)
    v4.3: Déplacement UserTenantAssignment de platform/ vers user/
    v4.2: Ajout platform (SuperAdmin, PlatformAuditLog)
    v4.1: Ajout tenants (Tenant, Subscription)
"""

# === Enums ===
from app.models.enums import (
    # Types d'entités et organisation
    EntityType,
    IntegrationType,
    OrganizationModel,
    TerritoryType,
    # Professions et rôles
    ProfessionCategory,
    RoleName,
    ContractType,
    PermissionCategory,  # v4.3
    # Patients
    AccessType,
    PatientStatus,
    GirLevel,
    # Constantes vitales
    VitalType,
    VitalStatus,
    VitalSource,
    DeviceType,
    # Évaluations et documents
    EvaluationSchemaType,
    DocumentType,
    DocumentFormat,
    # Coordination et services
    CoordinationCategory,
    ServiceCategory,
    ServiceType,
    ServiceUnit,
    # Plans d'aide et interventions
    CarePlanStatus,
    FrequencyType,
    ServicePriority,
    AssignmentStatus,
    InterventionStatus,
)

# === Mixins ===
from app.models.mixins import (
    TimestampMixin,
    AuditMixin,
    VersionedMixin,
    StatusMixin,
)

# === Modèles Tenant (v4.1) ===
from app.models.tenants import (
    Tenant,
    TenantStatus,
    TenantType,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    BillingCycle,
    SubscriptionUsage,
)

# === Modèles Platform (v4.2) ===
from app.models.platform import (
    SuperAdmin,
    SuperAdminRole,
    PlatformAuditLog,
    AuditAction,
)

# === Modèles de référence ===
from app.models.reference.country import Country

# === Modèles d'organisation ===
from app.models.organization.entity import Entity

# === Modèles utilisateurs et permissions (v4.3) ===
from app.models.user.user import User
from app.models.user.role import Role, INITIAL_ROLES
from app.models.user.permission import Permission, INITIAL_PERMISSIONS
from app.models.user.role_permission import RolePermission, INITIAL_ROLE_PERMISSIONS
from app.models.user.profession import Profession, INITIAL_PROFESSIONS
from app.models.user.user_associations import UserRole, UserEntity
from app.models.user.user_availability import UserAvailability
from app.models.user.user_tenant_assignment import UserTenantAssignment, AssignmentType  # Déplacé depuis platform/ v4.3

# === Modèles patients ===
from app.models.patient.patient import Patient
from app.models.patient.patient_access import PatientAccess
from app.models.patient.patient_evaluation import PatientEvaluation
from app.models.patient.evaluation_session import EvaluationSession
from app.models.patient.patient_vitals import PatientThreshold, PatientVitals, PatientDevice
from app.models.patient.patient_document import PatientDocument

# === Modèles catalogue ===
from app.models.catalog.service_template import ServiceTemplate, INITIAL_SERVICE_TEMPLATES
from app.models.catalog.entity_service import EntityService

# === Modèles plans d'aide ===
from app.models.careplan.care_plan import CarePlan
from app.models.careplan.care_plan_service import CarePlanService

# === Modèles coordination ===
from app.models.coordination.coordination_entry import CoordinationEntry
from app.models.coordination.scheduled_intervention import ScheduledIntervention


# === Export explicite ===
__all__ = [
    # --- Enums ---
    # Organisation
    "EntityType",
    "IntegrationType",
    "OrganizationModel",
    "TerritoryType",
    # Professions et rôles
    "ProfessionCategory",
    "RoleName",
    "ContractType",
    "PermissionCategory",  # v4.3
    # Patients
    "AccessType",
    "PatientStatus",
    "GirLevel",
    # Constantes vitales
    "VitalType",
    "VitalStatus",
    "VitalSource",
    "DeviceType",
    # Évaluations et documents
    "EvaluationSchemaType",
    "DocumentType",
    "DocumentFormat",
    # Coordination et services
    "CoordinationCategory",
    "ServiceCategory",
    "ServiceType",
    "ServiceUnit",
    # Plans d'aide et interventions
    "CarePlanStatus",
    "FrequencyType",
    "ServicePriority",
    "AssignmentStatus",
    "InterventionStatus",

    # --- Mixins ---
    "TimestampMixin",
    "AuditMixin",
    "VersionedMixin",
    "StatusMixin",

    # --- Modèles ---

    # Platform (v4.2)
    "SuperAdmin",
    "SuperAdminRole",
    "PlatformAuditLog",
    "AuditAction",

    # Tenant (v4.1)
    "Tenant",
    "TenantStatus",
    "TenantType",
    "Subscription",
    "SubscriptionPlan",
    "SubscriptionStatus",
    "BillingCycle",
    "SubscriptionUsage",

    # Référence
    "Country",

    # Organisation
    "Entity",

    # Utilisateurs et permissions (v4.3)
    "User",
    "Role",
    "INITIAL_ROLES",
    "Permission",
    "INITIAL_PERMISSIONS",
    "RolePermission",
    "INITIAL_ROLE_PERMISSIONS",
    "Profession",
    "INITIAL_PROFESSIONS",
    "UserRole",
    "UserEntity",
    "UserAvailability",
    "UserTenantAssignment",
    "AssignmentType",

    # Patients
    "Patient",
    "PatientAccess",
    "PatientEvaluation",
    "EvaluationSession",
    "PatientThreshold",
    "PatientVitals",
    "PatientDevice",
    "PatientDocument",

    # Catalogue
    "ServiceTemplate",
    "INITIAL_SERVICE_TEMPLATES",
    "EntityService",

    # Plans d'aide
    "CarePlan",
    "CarePlanService",

    # Coordination
    "CoordinationEntry",
    "ScheduledIntervention",
]