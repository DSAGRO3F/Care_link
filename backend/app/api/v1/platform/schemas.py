"""
Schémas Pydantic pour le module Platform.

Compatible avec les modèles existants :
- app.models.tenants.tenant.Tenant
- app.models.platform.super_admin.SuperAdmin
- app.models.platform.platform_audit_log.PlatformAuditLog
- app.models.user.user_tenant_assignment.UserTenantAssignment
"""
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, EmailStr, field_validator


# =============================================================================
# ENUMS - Réexportés pour usage dans l'API (doivent matcher les modèles)
# =============================================================================

class TenantStatusAPI(str, Enum):
    """Statuts de tenant - doit matcher TenantStatus du modèle."""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


class TenantTypeAPI(str, Enum):
    """Types de tenant - doit matcher TenantType du modèle."""
    GCSMS = "GCSMS"
    SSIAD = "SSIAD"
    SAAD = "SAAD"
    SPASAD = "SPASAD"
    EHPAD = "EHPAD"
    DAC = "DAC"
    CPTS = "CPTS"
    OTHER = "OTHER"


class AssignmentTypeAPI(str, Enum):
    """Types d'affectation cross-tenant."""
    PERMANENT = "PERMANENT"
    TEMPORARY = "TEMPORARY"
    EMERGENCY = "EMERGENCY"


class SuperAdminRoleAPI(str, Enum):
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
    legal_name: Optional[str] = Field(None, max_length=255, description="Raison sociale")
    siret: Optional[str] = Field(None, max_length=14, description="Numéro SIRET")
    tenant_type: TenantTypeAPI = Field(..., description="Type de structure")

    # Contact
    contact_email: EmailStr = Field(..., description="Email du contact principal")
    contact_phone: Optional[str] = Field(None, max_length=20)
    billing_email: Optional[EmailStr] = Field(None, description="Email facturation")

    # Adresse
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    postal_code: Optional[str] = Field(None, max_length=20)
    city: Optional[str] = Field(None, max_length=100)
    country_id: Optional[int] = Field(None, description="ID du pays")

    # Configuration
    timezone: str = Field(default="Europe/Paris", max_length=50)
    locale: str = Field(default="fr_FR", max_length=10)

    # Limites
    max_patients: Optional[int] = Field(None, ge=0, description="Limite patients (null=illimité)")
    max_users: Optional[int] = Field(None, ge=0, description="Limite utilisateurs (null=illimité)")
    max_storage_gb: int = Field(default=50, ge=1, description="Quota stockage en Go")

    # Paramètres personnalisés
    settings: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Le code doit être en majuscules, alphanumérique avec tirets."""
        v = v.upper().strip()
        if not all(c.isalnum() or c == '-' for c in v):
            raise ValueError("Le code ne doit contenir que des lettres, chiffres et tirets")
        return v

    @field_validator('siret')
    @classmethod
    def validate_siret(cls, v: Optional[str]) -> Optional[str]:
        """Valide le format SIRET (14 chiffres)."""
        if v is None:
            return None
        v = v.replace(" ", "")
        if not v.isdigit() or len(v) != 14:
            raise ValueError("Le SIRET doit contenir exactement 14 chiffres")
        return v


class TenantUpdate(BaseModel):
    """Mise à jour partielle d'un tenant."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    siret: Optional[str] = Field(None, max_length=14)
    tenant_type: Optional[TenantTypeAPI] = None
    status: Optional[TenantStatusAPI] = None

    # Contact
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    billing_email: Optional[EmailStr] = None

    # Adresse
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    postal_code: Optional[str] = Field(None, max_length=20)
    city: Optional[str] = Field(None, max_length=100)
    country_id: Optional[int] = None

    # Configuration
    timezone: Optional[str] = Field(None, max_length=50)
    locale: Optional[str] = Field(None, max_length=10)

    # Limites
    max_patients: Optional[int] = Field(None, ge=0)
    max_users: Optional[int] = Field(None, ge=0)
    max_storage_gb: Optional[int] = Field(None, ge=1)

    # Paramètres
    settings: Optional[Dict[str, Any]] = None

    @field_validator('siret')
    @classmethod
    def validate_siret(cls, v: Optional[str]) -> Optional[str]:
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
    legal_name: Optional[str] = None
    siret: Optional[str] = None
    tenant_type: TenantTypeAPI
    status: TenantStatusAPI

    # Contact
    contact_email: str
    contact_phone: Optional[str] = None
    billing_email: Optional[str] = None

    # Adresse
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country_id: Optional[int] = None

    # Configuration
    timezone: str
    locale: str

    # Limites
    max_patients: Optional[int] = None
    max_users: Optional[int] = None
    max_storage_gb: int

    # Paramètres
    settings: Dict[str, Any] = Field(default_factory=dict)

    # Dates
    activated_at: Optional[datetime] = None
    terminated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TenantFilters(BaseModel):
    """Filtres pour la liste des tenants."""
    status: Optional[TenantStatusAPI] = None
    tenant_type: Optional[TenantTypeAPI] = None
    search: Optional[str] = Field(None, description="Recherche dans code, name, legal_name")
    city: Optional[str] = None
    country_id: Optional[int] = None


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
    users_limit: Optional[int] = None
    patients_limit: Optional[int] = None
    users_usage_percent: Optional[float] = None
    patients_usage_percent: Optional[float] = None

    # Activité
    last_activity_at: Optional[datetime] = None


# =============================================================================
# SUPER ADMIN SCHEMAS
# =============================================================================

class SuperAdminCreate(BaseModel):
    """Création d'un super admin."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=12, description="Mot de passe (min 12 caractères)")
    role: SuperAdminRoleAPI = Field(
        default=SuperAdminRoleAPI.PLATFORM_SUPPORT,
        description="Rôle du super admin"
    )
    is_active: bool = Field(default=True)

    @field_validator('password')
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
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[SuperAdminRoleAPI] = None
    is_active: Optional[bool] = None


class SuperAdminPasswordChange(BaseModel):
    """Changement de mot de passe."""
    current_password: str
    new_password: str = Field(..., min_length=12)

    @field_validator('new_password')
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
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

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
    super_admin_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    tenant_id: Optional[int] = None
    tenant_code: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogFilters(BaseModel):
    """Filtres pour les logs d'audit."""
    super_admin_id: Optional[int] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    tenant_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# =============================================================================
# USER TENANT ASSIGNMENT SCHEMAS
# =============================================================================

class UserTenantAssignmentCreate(BaseModel):
    """Création d'une affectation cross-tenant."""
    user_id: int = Field(..., description="ID de l'utilisateur à affecter")
    tenant_id: int = Field(..., description="Tenant de destination")
    assignment_type: AssignmentTypeAPI = Field(default=AssignmentTypeAPI.TEMPORARY)
    start_date: date = Field(..., description="Date de début")
    end_date: Optional[date] = Field(None, description="Date de fin (null=indéterminé)")
    reason: Optional[str] = Field(None, max_length=1000, description="Justification du rattachement")
    permissions: Optional[List[str]] = Field(None, description="Permissions spécifiques (null=hérite)")

    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v: Optional[date], info) -> Optional[date]:
        if v is not None and 'start_date' in info.data:
            if v < info.data['start_date']:
                raise ValueError("La date de fin doit être postérieure à la date de début")
        return v


class UserTenantAssignmentUpdate(BaseModel):
    """Mise à jour d'une affectation."""
    assignment_type: Optional[AssignmentTypeAPI] = None
    end_date: Optional[date] = None
    reason: Optional[str] = Field(None, max_length=1000)
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None


class UserTenantAssignmentResponse(BaseModel):
    """Réponse d'une affectation cross-tenant."""
    id: int
    user_id: int
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None
    tenant_id: int
    tenant_code: Optional[str] = None
    tenant_name: Optional[str] = None
    assignment_type: AssignmentTypeAPI
    start_date: date
    end_date: Optional[date] = None
    reason: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: bool
    is_valid: bool = False
    days_remaining: Optional[int] = None
    granted_by_super_admin_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserTenantAssignmentFilters(BaseModel):
    """Filtres pour les affectations."""
    user_id: Optional[int] = None
    tenant_id: Optional[int] = None
    assignment_type: Optional[AssignmentTypeAPI] = None
    is_active: Optional[bool] = None
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