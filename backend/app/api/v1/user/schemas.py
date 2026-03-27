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

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import ProfessionCategory


# =============================================================================
# PROFESSION SCHEMAS
# =============================================================================


class ProfessionBase(BaseModel):
    """Champs communs pour Profession."""

    name: str = Field(..., min_length=1, max_length=100, description="Nom de la profession")
    code: str | None = Field(None, max_length=10, description="Code RPPS/ADELI")
    category: str | None = Field(
        None, max_length=50, description="Catégorie (MEDICAL, PARAMEDICAL, ADMINISTRATIVE)"
    )
    requires_rpps: bool = Field(True, description="Nécessite un numéro RPPS")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is not None:
            valid = [e.value for e in ProfessionCategory]
            if v.upper() not in valid:
                raise ValueError(f"Catégorie invalide. Valeurs acceptées: {valid}")
            return v.upper()
        return v


class ProfessionCreate(ProfessionBase):
    """Schéma pour créer une profession."""


class ProfessionUpdate(BaseModel):
    """Schéma pour mettre à jour une profession."""

    name: str | None = Field(None, min_length=1, max_length=100)
    code: str | None = Field(None, max_length=10)
    category: str | None = Field(None, max_length=50)
    requires_rpps: bool | None = None


class ProfessionResponse(ProfessionBase):
    """Schéma de réponse pour une profession."""

    id: int
    display_order: int = 0  # AJOUT S2
    status: str = "active"  # AJOUT S2
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ProfessionList(BaseModel):
    """Liste paginée de professions."""

    items: list[ProfessionResponse]
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
    description: str | None = Field(None, max_length=255, description="Description du rôle")
    permissions: list[str] = Field(
        default_factory=list, description="Liste des codes de permissions"
    )
    is_system_role: bool = Field(False, description="Rôle système non modifiable")


class RoleCreate(RoleBase):
    """Schéma pour créer un rôle."""


class RoleUpdate(BaseModel):
    """Schéma pour mettre à jour un rôle."""

    name: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = Field(None, max_length=255)
    permissions: list[str] | None = None
    is_system_role: bool | None = None


class RoleResponse(BaseModel):
    """Schéma de réponse pour un rôle (v4.3)."""

    id: int
    name: str
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)
    is_system_role: bool = False
    created_at: datetime
    updated_at: datetime | None = None

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
            return [p.code if hasattr(p, "code") else str(p) for p in v]
        except (TypeError, AttributeError):
            return []


class RoleList(BaseModel):
    """Liste paginée de rôles."""

    items: list[RoleResponse]
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
    contract_type: str | None = Field(None, max_length=50, description="Type de contrat")
    start_date: date = Field(..., description="Date de début")
    end_date: date | None = Field(None, description="Date de fin")
    intervention_radius_km: int | None = Field(None, ge=0, description="Rayon d'intervention en km")
    max_daily_patients: int | None = Field(None, ge=0, description="Max patients par jour")
    max_weekly_hours: int | None = Field(None, ge=0, description="Max heures par semaine")
    default_start_time: time | None = Field(None, description="Heure de début par défaut")
    default_end_time: time | None = Field(None, description="Heure de fin par défaut")

    @field_validator("contract_type")
    @classmethod
    def validate_contract_type(cls, v: str | None) -> str | None:
        if v is not None:
            valid = ["SALARIE", "LIBERAL", "VACATION", "REMPLACEMENT", "BENEVOLE"]
            if v.upper() not in valid:
                raise ValueError(f"Type de contrat invalide. Valeurs acceptées: {valid}")
            return v.upper()
        return v


class UserEntityCreate(UserEntityBase):
    """Schéma pour rattacher un utilisateur à une entité."""


class UserEntityUpdate(BaseModel):
    """Schéma pour modifier le rattachement."""

    is_primary: bool | None = None
    contract_type: str | None = None
    end_date: date | None = None
    intervention_radius_km: int | None = Field(None, ge=0)
    max_daily_patients: int | None = Field(None, ge=0)
    max_weekly_hours: int | None = Field(None, ge=0)
    default_start_time: time | None = None
    default_end_time: time | None = None


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
    assigned_by: int | None = None
    role: RoleResponse

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# USER AVAILABILITY SCHEMAS
# =============================================================================


class UserAvailabilityBase(BaseModel):
    """Champs communs pour UserAvailability."""

    entity_id: int | None = Field(None, description="ID de l'entité (None = toutes)")
    day_of_week: int = Field(..., ge=1, le=7, description="Jour (1=Lundi, 7=Dimanche)")
    start_time: time = Field(..., description="Heure de début")
    end_time: time = Field(..., description="Heure de fin")
    is_recurring: bool = Field(True, description="Récurrent chaque semaine")
    valid_from: date | None = Field(None, description="Date de début de validité")
    valid_until: date | None = Field(None, description="Date de fin de validité")
    max_patients: int | None = Field(None, ge=0, description="Max patients sur ce créneau")
    notes: str | None = Field(None, description="Notes particulières")
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


class UserAvailabilityUpdate(BaseModel):
    """Schéma pour modifier une disponibilité."""

    entity_id: int | None = None
    day_of_week: int | None = Field(None, ge=1, le=7)
    start_time: time | None = None
    end_time: time | None = None
    is_recurring: bool | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    max_patients: int | None = Field(None, ge=0)
    notes: str | None = None
    is_active: bool | None = None


class UserAvailabilityResponse(UserAvailabilityBase):
    """Schéma de réponse pour une disponibilité."""

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime | None = None
    # Propriétés calculées (optionnelles si non implémentées)
    day_name: str | None = None
    duration_minutes: int | None = None
    time_range_display: str | None = None

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
            from datetime import datetime

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

    items: list[UserAvailabilityResponse]
    total: int


# =============================================================================
# USER SCHEMAS
# =============================================================================


class UserBase(BaseModel):
    """Champs communs pour User."""

    email: EmailStr = Field(..., description="Email de connexion")
    first_name: str = Field(..., min_length=1, max_length=100, description="Prénom")
    last_name: str = Field(..., min_length=1, max_length=100, description="Nom")
    rpps: str | None = Field(
        None, min_length=11, max_length=11, description="Numéro RPPS (11 chiffres)"
    )
    profession_id: int | None = Field(None, description="ID de la profession")
    is_admin: bool = Field(False, description="Est administrateur")
    is_active: bool = Field(True, description="Compte actif")

    @field_validator("rpps")
    @classmethod
    def validate_rpps(cls, v: str | None) -> str | None:
        if v is not None:
            if not v.isdigit():
                raise ValueError("Le RPPS doit contenir uniquement des chiffres")
            if len(v) != 11:
                raise ValueError("Le RPPS doit contenir exactement 11 chiffres")
        return v


class UserCreate(UserBase):
    """Schéma pour créer un utilisateur."""

    password: str | None = Field(None, min_length=8, description="Mot de passe (min 8 caractères)")


class UserUpdate(BaseModel):
    """Schéma pour mettre à jour un utilisateur."""

    email: EmailStr | None = None
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    rpps: str | None = Field(None, min_length=11, max_length=11)
    profession_id: int | None = None
    is_admin: bool | None = None
    is_active: bool | None = None
    password: str | None = Field(None, min_length=8)

    @field_validator("rpps")
    @classmethod
    def validate_rpps(cls, v: str | None) -> str | None:
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
    rpps: str | None = None
    is_active: bool
    must_change_password: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    """Schéma de réponse complet pour un utilisateur."""

    id: int
    created_at: datetime
    updated_at: datetime | None = None
    last_login: datetime | None = None
    must_change_password: bool = False
    # Propriétés calculées
    full_name: str
    display_name: str
    # Relations
    profession: ProfessionResponse | None = None
    roles: list[RoleResponse] = []
    role_names: list[str] = []
    # S4 — Permissions effectives (profession ∪ rôles)
    # Alimenté par le service AVANT expunge (approche B)
    effective_permissions: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class UserWithEntities(UserResponse):
    """Schéma avec les entités rattachées."""

    entity_associations: list[UserEntityResponse] = []


class UserList(BaseModel):
    """Liste paginée d'utilisateurs."""

    items: list[UserSummary]
    total: int
    page: int
    size: int
    pages: int


# =============================================================================
# FILTER SCHEMAS
# =============================================================================


class UserFilters(BaseModel):
    """Filtres pour la recherche d'utilisateurs."""

    profession_id: int | None = None
    role_name: str | None = None
    entity_id: int | None = None
    is_active: bool | None = None
    is_admin: bool | None = None
    search: str | None = Field(None, description="Recherche sur nom, prénom, email, RPPS")
