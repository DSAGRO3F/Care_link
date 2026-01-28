"""
Schémas Pydantic pour le module User.

Contient les schémas pour :
- Profession (professions réglementées)
- Role (rôles fonctionnels)
- User (utilisateurs)
- UserRole (attribution de rôles)
- UserEntity (rattachement aux entités)
- UserAvailability (disponibilités)
"""
from datetime import date, time, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


# =============================================================================
# PROFESSION SCHEMAS
# =============================================================================

class ProfessionBase(BaseModel):
    """Champs communs pour Profession."""
    name: str = Field(..., min_length=1, max_length=100, description="Nom de la profession")
    code: Optional[str] = Field(None, max_length=10, description="Code RPPS/ADELI")
    category: Optional[str] = Field(None, max_length=50, description="Catégorie (MEDICAL, PARAMEDICAL, ADMINISTRATIVE)")
    requires_rpps: bool = Field(True, description="Nécessite un numéro RPPS")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid = ["MEDICAL", "PARAMEDICAL", "ADMINISTRATIVE"]
            if v.upper() not in valid:
                raise ValueError(f"Catégorie invalide. Valeurs acceptées: {valid}")
            return v.upper()
        return v


class ProfessionCreate(ProfessionBase):
    """Schéma pour créer une profession."""
    pass


class ProfessionUpdate(BaseModel):
    """Schéma pour mettre à jour une profession."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=10)
    category: Optional[str] = Field(None, max_length=50)
    requires_rpps: Optional[bool] = None


class ProfessionResponse(ProfessionBase):
    """Schéma de réponse pour une profession."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProfessionList(BaseModel):
    """Liste paginée de professions."""
    items: List[ProfessionResponse]
    total: int
    page: int
    size: int
    pages: int


# =============================================================================
# ROLE SCHEMAS (v4.3 - permissions via RolePermission)
# =============================================================================

class RoleBase(BaseModel):
    """Champs communs pour Role."""
    name: str = Field(..., min_length=1, max_length=50, description="Nom technique du rôle")
    description: Optional[str] = Field(None, max_length=255, description="Description du rôle")
    permissions: List[str] = Field(default_factory=list, description="Liste des codes de permissions")
    is_system_role: bool = Field(False, description="Rôle système non modifiable")


class RoleCreate(RoleBase):
    """Schéma pour créer un rôle."""
    pass


class RoleUpdate(BaseModel):
    """Schéma pour mettre à jour un rôle."""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    permissions: Optional[List[str]] = None
    is_system_role: Optional[bool] = None


class RoleResponse(BaseModel):
    """Schéma de réponse pour un rôle (v4.3)."""
    id: int
    name: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    is_system_role: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("permissions", mode="before")
    @classmethod
    def extract_permission_codes(cls, v):
        """Extrait les codes de permissions (v4.3).

        Gère le cas où permissions est une liste d'objets Permission.
        """
        if not v:
            return []
        # Si c'est déjà une liste de strings
        if v and isinstance(v[0], str):
            return v
        # Si c'est une liste d'objets Permission
        try:
            return [p.code if hasattr(p, 'code') else str(p) for p in v]
        except (TypeError, AttributeError):
            return []


class RoleList(BaseModel):
    """Liste paginée de rôles."""
    items: List[RoleResponse]
    total: int
    page: int
    size: int
    pages: int


# =============================================================================
# USER ENTITY ASSOCIATION SCHEMAS
# =============================================================================

class UserEntityBase(BaseModel):
    """Champs communs pour UserEntity."""
    entity_id: int = Field(..., description="ID de l'entité")
    is_primary: bool = Field(False, description="Entité principale")
    contract_type: Optional[str] = Field(None, max_length=50, description="Type de contrat")
    start_date: date = Field(..., description="Date de début")
    end_date: Optional[date] = Field(None, description="Date de fin")
    intervention_radius_km: Optional[int] = Field(None, ge=0, description="Rayon d'intervention en km")
    max_daily_patients: Optional[int] = Field(None, ge=0, description="Max patients par jour")
    max_weekly_hours: Optional[int] = Field(None, ge=0, description="Max heures par semaine")
    default_start_time: Optional[time] = Field(None, description="Heure de début par défaut")
    default_end_time: Optional[time] = Field(None, description="Heure de fin par défaut")

    @field_validator("contract_type")
    @classmethod
    def validate_contract_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid = ["SALARIE", "LIBERAL", "VACATION", "REMPLACEMENT", "BENEVOLE"]
            if v.upper() not in valid:
                raise ValueError(f"Type de contrat invalide. Valeurs acceptées: {valid}")
            return v.upper()
        return v


class UserEntityCreate(UserEntityBase):
    """Schéma pour rattacher un utilisateur à une entité."""
    pass


class UserEntityUpdate(BaseModel):
    """Schéma pour modifier le rattachement."""
    is_primary: Optional[bool] = None
    contract_type: Optional[str] = None
    end_date: Optional[date] = None
    intervention_radius_km: Optional[int] = Field(None, ge=0)
    max_daily_patients: Optional[int] = Field(None, ge=0)
    max_weekly_hours: Optional[int] = Field(None, ge=0)
    default_start_time: Optional[time] = None
    default_end_time: Optional[time] = None


class UserEntityResponse(UserEntityBase):
    """Schéma de réponse pour UserEntity."""
    id: int
    user_id: int
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# USER ROLE ASSOCIATION SCHEMAS
# =============================================================================

class UserRoleCreate(BaseModel):
    """Schéma pour attribuer un rôle à un utilisateur."""
    role_id: int = Field(..., description="ID du rôle à attribuer")


class UserRoleResponse(BaseModel):
    """Schéma de réponse pour UserRole."""
    user_id: int
    role_id: int
    assigned_at: datetime
    assigned_by: Optional[int] = None
    role: RoleResponse

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# USER AVAILABILITY SCHEMAS
# =============================================================================

class UserAvailabilityBase(BaseModel):
    """Champs communs pour UserAvailability."""
    entity_id: Optional[int] = Field(None, description="ID de l'entité (None = toutes)")
    day_of_week: int = Field(..., ge=1, le=7, description="Jour (1=Lundi, 7=Dimanche)")
    start_time: time = Field(..., description="Heure de début")
    end_time: time = Field(..., description="Heure de fin")
    is_recurring: bool = Field(True, description="Récurrent chaque semaine")
    valid_from: Optional[date] = Field(None, description="Date de début de validité")
    valid_until: Optional[date] = Field(None, description="Date de fin de validité")
    max_patients: Optional[int] = Field(None, ge=0, description="Max patients sur ce créneau")
    notes: Optional[str] = Field(None, description="Notes particulières")
    is_active: bool = Field(True, description="Disponibilité active")

    @field_validator("end_time")
    @classmethod
    def validate_time_range(cls, v: time, info) -> time:
        start = info.data.get("start_time")
        if start and v <= start:
            raise ValueError("L'heure de fin doit être après l'heure de début")
        return v


class UserAvailabilityCreate(UserAvailabilityBase):
    """Schéma pour créer une disponibilité."""
    pass


class UserAvailabilityUpdate(BaseModel):
    """Schéma pour modifier une disponibilité."""
    entity_id: Optional[int] = None
    day_of_week: Optional[int] = Field(None, ge=1, le=7)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_recurring: Optional[bool] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    max_patients: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class UserAvailabilityResponse(UserAvailabilityBase):
    """Schéma de réponse pour une disponibilité."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Propriétés calculées (optionnelles si non implémentées)
    day_name: Optional[str] = None
    duration_minutes: Optional[int] = None
    time_range_display: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("day_name", mode="before")
    @classmethod
    def compute_day_name(cls, v, info):
        """Calcule le nom du jour si non fourni."""
        if v is not None:
            return v
        day_of_week = info.data.get("day_of_week")
        if day_of_week:
            days = ["", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
            return days[day_of_week] if 1 <= day_of_week <= 7 else None
        return None

    @field_validator("duration_minutes", mode="before")
    @classmethod
    def compute_duration(cls, v, info):
        """Calcule la durée si non fournie."""
        if v is not None:
            return v
        start = info.data.get("start_time")
        end = info.data.get("end_time")
        if start and end:
            from datetime import datetime, timedelta
            start_dt = datetime.combine(datetime.today(), start)
            end_dt = datetime.combine(datetime.today(), end)
            return int((end_dt - start_dt).total_seconds() / 60)
        return None

    @field_validator("time_range_display", mode="before")
    @classmethod
    def compute_time_range(cls, v, info):
        """Calcule l'affichage du créneau si non fourni."""
        if v is not None:
            return v
        start = info.data.get("start_time")
        end = info.data.get("end_time")
        if start and end:
            return f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"
        return None


class UserAvailabilityList(BaseModel):
    """Liste de disponibilités."""
    items: List[UserAvailabilityResponse]
    total: int


# =============================================================================
# USER SCHEMAS
# =============================================================================

class UserBase(BaseModel):
    """Champs communs pour User."""
    email: EmailStr = Field(..., description="Email de connexion")
    first_name: str = Field(..., min_length=1, max_length=100, description="Prénom")
    last_name: str = Field(..., min_length=1, max_length=100, description="Nom")
    rpps: Optional[str] = Field(None, min_length=11, max_length=11, description="Numéro RPPS (11 chiffres)")
    profession_id: Optional[int] = Field(None, description="ID de la profession")
    is_admin: bool = Field(False, description="Est administrateur")
    is_active: bool = Field(True, description="Compte actif")

    @field_validator("rpps")
    @classmethod
    def validate_rpps(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.isdigit():
                raise ValueError("Le RPPS doit contenir uniquement des chiffres")
            if len(v) != 11:
                raise ValueError("Le RPPS doit contenir exactement 11 chiffres")
        return v


class UserCreate(UserBase):
    """Schéma pour créer un utilisateur."""
    password: Optional[str] = Field(None, min_length=8, description="Mot de passe (min 8 caractères)")


class UserUpdate(BaseModel):
    """Schéma pour mettre à jour un utilisateur."""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    rpps: Optional[str] = Field(None, min_length=11, max_length=11)
    profession_id: Optional[int] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)

    @field_validator("rpps")
    @classmethod
    def validate_rpps(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.isdigit():
            raise ValueError("Le RPPS doit contenir uniquement des chiffres")
        return v


class UserSummary(BaseModel):
    """Schéma résumé pour un utilisateur (listes, références)."""
    id: int
    email: str
    first_name: str
    last_name: str
    full_name: str
    rpps: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    """Schéma de réponse complet pour un utilisateur."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    # Propriétés calculées
    full_name: str
    display_name: str
    # Relations
    profession: Optional[ProfessionResponse] = None
    roles: List[RoleResponse] = []
    role_names: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class UserWithEntities(UserResponse):
    """Schéma avec les entités rattachées."""
    entity_associations: List[UserEntityResponse] = []


class UserList(BaseModel):
    """Liste paginée d'utilisateurs."""
    items: List[UserSummary]
    total: int
    page: int
    size: int
    pages: int


# =============================================================================
# FILTER SCHEMAS
# =============================================================================

class UserFilters(BaseModel):
    """Filtres pour la recherche d'utilisateurs."""
    profession_id: Optional[int] = None
    role_name: Optional[str] = None
    entity_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    search: Optional[str] = Field(None, description="Recherche sur nom, prénom, email, RPPS")