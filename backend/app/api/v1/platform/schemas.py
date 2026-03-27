"""
Schémas Pydantic pour le module Platform.

Gestion des entités côté SuperAdmin.
Réutilise les schémas Organization existants et ajoute
les validations spécifiques au contexte SuperAdmin.


Compatible avec les modèles existants :
- app.models.tenants.tenant.Tenant
- app.models.platform.super_admin.SuperAdmin
- app.models.platform.platform_audit_log.PlatformAuditLog
- app.models.user.user_tenant_assignment.UserTenantAssignment
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.api.v1.organization.schemas import (
    EntityBase,
    EntityFilters,
    EntityResponse,
    EntitySummary,
    EntityUpdate,
)
from app.models.enums import EntityType


# =============================================================================
# ENUMS - Réexportés pour usage dans l'API (doivent matcher les modèles)
# =============================================================================


class TenantStatusAPI(StrEnum):
    """Statuts de tenant - doit matcher TenantStatus du modèle."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


class TenantTypeAPI(StrEnum):
    """Types de tenant - doit matcher TenantType du modèle."""

    GCSMS = "GCSMS"
    SSIAD = "SSIAD"
    SAAD = "SAAD"
    SPASAD = "SPASAD"
    EHPAD = "EHPAD"
    DAC = "DAC"
    CPTS = "CPTS"
    OTHER = "OTHER"


class AssignmentTypeAPI(StrEnum):
    """Types d'affectation cross-tenant."""

    PERMANENT = "PERMANENT"
    TEMPORARY = "TEMPORARY"
    EMERGENCY = "EMERGENCY"


class SuperAdminRoleAPI(StrEnum):
    """Rôles des super-admins - doit matcher SuperAdminRole du modèle."""

    PLATFORM_OWNER = "PLATFORM_OWNER"
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    PLATFORM_SUPPORT = "PLATFORM_SUPPORT"
    PLATFORM_SALES = "PLATFORM_SALES"


# =============================================================================
# TENANT SCHEMAS
# =============================================================================


class TenantCreate(BaseModel):
    """Création d'un nouveau tenant."""

    code: str = Field(..., min_length=3, max_length=50, description="Code unique du tenant")
    name: str = Field(..., min_length=2, max_length=255, description="Nom commercial")
    legal_name: str | None = Field(None, max_length=255, description="Raison sociale")
    siret: str | None = Field(None, max_length=14, description="Numéro SIRET")
    tenant_type: TenantTypeAPI = Field(..., description="Type de structure")

    # Contact
    contact_email: EmailStr = Field(..., description="Email du contact principal")
    contact_phone: str | None = Field(None, max_length=20)
    billing_email: EmailStr | None = Field(None, description="Email facturation")

    # Adresse
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    postal_code: str | None = Field(None, max_length=20)
    city: str | None = Field(None, max_length=100)
    country_id: int | None = Field(None, description="ID du pays")

    # Configuration
    timezone: str = Field(default="Europe/Paris", max_length=50)
    locale: str = Field(default="fr_FR", max_length=10)

    # Limites
    max_patients: int | None = Field(None, ge=0, description="Limite patients (null=illimité)")
    max_users: int | None = Field(None, ge=0, description="Limite utilisateurs (null=illimité)")
    max_storage_gb: int = Field(default=50, ge=1, description="Quota stockage en Go")

    # Paramètres personnalisés
    settings: dict[str, Any] = Field(default_factory=dict)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Le code doit être en majuscules, alphanumérique avec tirets."""
        v = v.upper().strip()
        if not all(c.isalnum() or c == "-" for c in v):
            raise ValueError("Le code ne doit contenir que des lettres, chiffres et tirets")
        return v

    @field_validator("siret")
    @classmethod
    def validate_siret(cls, v: str | None) -> str | None:
        """Valide le format SIRET (14 chiffres)."""
        if v is None:
            return None
        v = v.replace(" ", "")
        if not v.isdigit() or len(v) != 14:
            raise ValueError("Le SIRET doit contenir exactement 14 chiffres")
        return v


class TenantUpdate(BaseModel):
    """Mise à jour partielle d'un tenant."""

    name: str | None = Field(None, min_length=2, max_length=255)
    legal_name: str | None = Field(None, max_length=255)
    siret: str | None = Field(None, max_length=14)
    tenant_type: TenantTypeAPI | None = None
    status: TenantStatusAPI | None = None

    # Contact
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(None, max_length=20)
    billing_email: EmailStr | None = None

    # Adresse
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    postal_code: str | None = Field(None, max_length=20)
    city: str | None = Field(None, max_length=100)
    country_id: int | None = None

    # Configuration
    timezone: str | None = Field(None, max_length=50)
    locale: str | None = Field(None, max_length=10)

    # Limites
    max_patients: int | None = Field(None, ge=0)
    max_users: int | None = Field(None, ge=0)
    max_storage_gb: int | None = Field(None, ge=1)

    # Paramètres
    settings: dict[str, Any] | None = None

    @field_validator("siret")
    @classmethod
    def validate_siret(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.replace(" ", "")
        if not v.isdigit() or len(v) != 14:
            raise ValueError("Le SIRET doit contenir exactement 14 chiffres")
        return v


class TenantResponse(BaseModel):
    """Réponse complète d'un tenant."""

    id: int
    code: str
    name: str
    legal_name: str | None = None
    siret: str | None = None
    tenant_type: TenantTypeAPI
    status: TenantStatusAPI

    # Contact
    contact_email: str
    contact_phone: str | None = None
    billing_email: str | None = None

    # Adresse
    address_line1: str | None = None
    address_line2: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country_id: int | None = None

    # Configuration
    timezone: str
    locale: str

    # Limites
    max_patients: int | None = None
    max_users: int | None = None
    max_storage_gb: int

    # Paramètres
    settings: dict[str, Any] = Field(default_factory=dict)

    # Dates
    activated_at: datetime | None = None
    terminated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class TenantFilters(BaseModel):
    """Filtres pour la liste des tenants."""

    status: TenantStatusAPI | None = None
    tenant_type: TenantTypeAPI | None = None
    search: str | None = Field(None, description="Recherche dans code, name, legal_name")
    city: str | None = None
    country_id: int | None = None


class TenantStats(BaseModel):
    """Statistiques d'un tenant."""

    tenant_id: int
    tenant_code: str
    tenant_name: str

    # Compteurs
    entities_count: int = 0
    users_count: int = 0
    patients_count: int = 0

    # Utilisation vs limites
    users_limit: int | None = None
    patients_limit: int | None = None
    users_usage_percent: float | None = None
    patients_usage_percent: float | None = None

    # Activité
    last_activity_at: datetime | None = None


# =============================================================================
# SUPER ADMIN SCHEMAS
# =============================================================================


class SuperAdminLoginRequest(BaseModel):
    """Requête de connexion super admin."""

    email: EmailStr
    password: str


class SuperAdminCreate(BaseModel):
    """Création d'un super admin."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=12, description="Mot de passe (min 12 caractères)")
    role: SuperAdminRoleAPI = Field(
        default=SuperAdminRoleAPI.PLATFORM_SUPPORT, description="Rôle du super admin"
    )
    is_active: bool = Field(default=True)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Valide la complexité du mot de passe."""
        if len(v) < 12:
            raise ValueError("Le mot de passe doit contenir au moins 12 caractères")
        if not any(c.isupper() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not any(c.islower() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins une minuscule")
        if not any(c.isdigit() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        return v


class SuperAdminUpdate(BaseModel):
    """Mise à jour d'un super admin."""

    email: EmailStr | None = None
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    role: SuperAdminRoleAPI | None = None
    is_active: bool | None = None


class SuperAdminPasswordChange(BaseModel):
    """Changement de mot de passe."""

    current_password: str
    new_password: str = Field(..., min_length=12)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Le mot de passe doit contenir au moins 12 caractères")
        if not any(c.isupper() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not any(c.islower() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins une minuscule")
        if not any(c.isdigit() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        return v


class SuperAdminResponse(BaseModel):
    """Réponse d'un super admin."""

    id: int
    email: str
    first_name: str
    last_name: str
    role: SuperAdminRoleAPI
    is_active: bool
    mfa_enabled: bool = False
    last_login: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


# =============================================================================
# AUDIT LOG SCHEMAS
# =============================================================================


class AuditLogResponse(BaseModel):
    """Réponse d'un log d'audit."""

    id: int
    super_admin_id: int
    super_admin_email: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    tenant_id: int | None = None
    tenant_code: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogFilters(BaseModel):
    """Filtres pour les logs d'audit."""

    super_admin_id: int | None = None
    action: str | None = None
    resource_type: str | None = None
    tenant_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


# =============================================================================
# USER TENANT ASSIGNMENT SCHEMAS
# =============================================================================


class UserTenantAssignmentCreate(BaseModel):
    """Création d'une affectation cross-tenant."""

    user_id: int = Field(..., description="ID de l'utilisateur à affecter")
    tenant_id: int = Field(..., description="Tenant de destination")
    assignment_type: AssignmentTypeAPI = Field(default=AssignmentTypeAPI.TEMPORARY)
    start_date: date = Field(..., description="Date de début")
    end_date: date | None = Field(None, description="Date de fin (null=indéterminé)")
    reason: str | None = Field(None, max_length=1000, description="Justification du rattachement")
    permissions: list[str] | None = Field(None, description="Permissions spécifiques (null=hérite)")

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: date | None, info) -> date | None:
        if v is not None and "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("La date de fin doit être postérieure à la date de début")
        return v


class UserTenantAssignmentUpdate(BaseModel):
    """Mise à jour d'une affectation."""

    assignment_type: AssignmentTypeAPI | None = None
    end_date: date | None = None
    reason: str | None = Field(None, max_length=1000)
    permissions: list[str] | None = None
    is_active: bool | None = None


class UserTenantAssignmentResponse(BaseModel):
    """Réponse d'une affectation cross-tenant."""

    id: int
    user_id: int
    user_email: str | None = None
    user_full_name: str | None = None
    tenant_id: int
    tenant_code: str | None = None
    tenant_name: str | None = None
    assignment_type: AssignmentTypeAPI
    start_date: date
    end_date: date | None = None
    reason: str | None = None
    permissions: list[str] | None = None
    is_active: bool
    is_valid: bool = False
    days_remaining: int | None = None
    granted_by_super_admin_id: int | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserTenantAssignmentFilters(BaseModel):
    """Filtres pour les affectations."""

    user_id: int | None = None
    tenant_id: int | None = None
    assignment_type: AssignmentTypeAPI | None = None
    is_active: bool | None = None
    include_expired: bool = Field(default=False, description="Inclure les affectations expirées")


# =============================================================================
# PLATFORM STATS SCHEMAS
# =============================================================================


class PlatformStats(BaseModel):
    """Statistiques globales de la plateforme."""

    # Tenants
    total_tenants: int = 0
    active_tenants: int = 0
    suspended_tenants: int = 0
    terminated_tenants: int = 0

    # Utilisateurs et patients globaux
    total_users: int = 0
    total_patients: int = 0
    total_entities: int = 0

    # Affectations cross-tenant
    active_assignments: int = 0

    # Activité récente
    tenants_created_last_30_days: int = 0
    users_created_last_30_days: int = 0

    # Super admins
    total_super_admins: int = 0
    active_super_admins: int = 0


# =============================================================================
# CONSTANTES ENTITY
# =============================================================================

# Types réservés aux racines de tenant (SuperAdmin uniquement)
ROOT_ENTITY_TYPES = {EntityType.GCSMS, EntityType.GTSMS}


# =============================================================================
# PLATFORM ENTITY SCHEMAS
# =============================================================================


class PlatformEntityCreate(EntityBase):
    """
    Création d'entité côté SuperAdmin.

    Hérite de EntityBase (mêmes champs et validateurs que EntityCreate)
    et ajoute un model_validator pour la cohérence racine/enfant :

    - Type racine (GCSMS/GTSMS) → parent_entity_id DOIT être None,
      integration_type DOIT être None
    - Type enfant → parent_entity_id peut être None
      (le service auto-rattachera à la racine du tenant)

    La validation "1 seule racine par tenant" est dans le service
    (nécessite accès DB).
    """

    @model_validator(mode="after")
    def validate_type_parent_coherence(self) -> "PlatformEntityCreate":
        """Valide la cohérence type ↔ parent ↔ integration_type."""
        if self.entity_type in ROOT_ENTITY_TYPES:
            if self.parent_entity_id is not None:
                raise ValueError(
                    f"Une entité de type {self.entity_type.value} est une racine "
                    f"et ne peut pas avoir de parent_entity_id"
                )
            if self.integration_type is not None:
                raise ValueError(
                    f"Une entité racine ({self.entity_type.value}) ne peut pas "
                    f"avoir de type d'intégration"
                )

        return self


# =============================================================================
# TENANT ADMIN USER SCHEMAS
# =============================================================================


class TenantAdminUserCreate(BaseModel):
    """
    Création d'un admin client par le SuperAdmin.

    Schéma allégé par rapport à UserCreate :
    - Pas de rpps ni profession_id (l'admin est un gestionnaire, pas un soignant)
    - Pas de role_ids (ADMIN_FULL est assigné automatiquement)
    - entity_id optionnel (rattaché à l'entité racine si non fourni)
    """

    first_name: str = Field(
        ..., min_length=1, max_length=100, description="Prénom de l'administrateur"
    )
    last_name: str = Field(..., min_length=1, max_length=100, description="Nom de l'administrateur")
    email: EmailStr = Field(..., description="Email de connexion (sera chiffré AES-256-GCM)")
    phone: str | None = Field(None, max_length=20, description="Téléphone (optionnel)")
    password: str = Field(..., min_length=12, description="Mot de passe initial")
    entity_id: int | None = Field(
        None, description="Entité de rattachement. Si null → rattaché à l'entité racine"
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Valide la complexité du mot de passe."""
        if len(v) < 12:
            raise ValueError("Le mot de passe doit contenir au moins 12 caractères")
        if not any(c.isupper() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not any(c.islower() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins une minuscule")
        if not any(c.isdigit() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        return v

    @property
    def start_date_value(self):
        """Date de début par défaut pour le rattachement entité."""
        from datetime import date

        return date.today()


class TenantAdminUserResponse(BaseModel):
    """Réponse après création d'un admin client."""

    id: int
    tenant_id: int
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    is_admin: bool
    is_active: bool
    entity_id: int | None = None
    entity_name: str | None = None
    role: str
    must_change_password: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
