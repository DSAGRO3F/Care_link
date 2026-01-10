"""
CareLink Models - Export centralisé de tous les modèles SQLAlchemy.

Ce fichier permet d'importer tous les modèles depuis un seul endroit :
    from app.models import User, Patient, Role, ...

Structure des sous-dossiers :
    organization/   - Structure organisationnelle (Entity, Organization)
    reference/      - Données de référence (Country, GirLevel)
    user/           - Utilisateurs et RH (User, Role, Profession)
    patient/        - Dossier patient (Patient, Evaluations, Vitals)
    coordination/   - Coordination des soins (CoordinationEntry)
    careplan/       - Plans d'aide (à venir)
    catalog/        - Catalogue de services (à venir)
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
    Permission,
    ContractType,
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
    # Plans d'aide
    CarePlanStatus,
    InterventionStatus,
)

# === Mixins ===
from app.models.mixins import (
    TimestampMixin,
    AuditMixin,
    VersionedMixin,
    StatusMixin,
)

# === Modèles de référence ===
from app.models.reference.country import Country

# === Modèles d'organisation ===
from app.models.organization.entity import Entity

# === Modèles utilisateurs ===
from app.models.user.user import User
from app.models.user.role import Role, INITIAL_ROLES
from app.models.user.profession import Profession, INITIAL_PROFESSIONS
from app.models.user.user_associations import UserRole, UserEntity

# === Modèles patients ===
from app.models.patient.patient import Patient
from app.models.patient.patient_access import PatientAccess
from app.models.patient.patient_evaluation import PatientEvaluation
from app.models.patient.patient_vitals import PatientThreshold, PatientVitals, PatientDevice
from app.models.patient.patient_document import PatientDocument

# === Modèles coordination ===
from app.models.coordination.coordination_entry import CoordinationEntry


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
    "Permission",
    "ContractType",
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
    # Plans d'aide
    "CarePlanStatus",
    "InterventionStatus",
    
    # --- Mixins ---
    "TimestampMixin",
    "AuditMixin",
    "VersionedMixin",
    "StatusMixin",
    
    # --- Modèles ---
    # Référence
    "Country",
    # Organisation
    "Entity",
    # Utilisateurs
    "User",
    "Role",
    "INITIAL_ROLES",
    "Profession",
    "INITIAL_PROFESSIONS",
    "UserRole",
    "UserEntity",
    # Patients
    "Patient",
    "PatientAccess",
    "PatientEvaluation",
    "PatientThreshold",
    "PatientVitals",
    "PatientDevice",
    "PatientDocument",
    # Coordination
    "CoordinationEntry",
]
