"""
Schémas Pydantic pour le module d'authentification.

Contient les schémas pour :
- Authentification PSC (Pro Santé Connect)
- Authentification locale (email/mot de passe)
- Tokens JWT
- Informations utilisateur PSC
- Gestion des accès patients
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =============================================================================
# ENUMS
# =============================================================================


class AccessType(StrEnum):
    """Types d'accès aux données patient."""

    READ = "READ"
    WRITE = "WRITE"
    FULL = "FULL"


class AuthMethod(StrEnum):
    """Méthodes d'authentification."""

    PSC = "psc"
    PASSWORD = "password"  # noqa: S105


# =============================================================================
# AUTHENTIFICATION LOCALE (EMAIL/MOT DE PASSE)
# =============================================================================


class LoginRequest(BaseModel):
    """Requête de connexion avec email/mot de passe."""

    tenant_code: str = Field(..., min_length=2, description="Code de la structure (ex: SSIAD-NORD)")
    email: EmailStr = Field(..., description="Email de connexion")
    password: str = Field(..., min_length=1, description="Mot de passe")


class PasswordChangeRequest(BaseModel):
    """Requête de changement de mot de passe."""

    current_password: str = Field(..., min_length=1, description="Mot de passe actuel")
    new_password: str = Field(
        ..., min_length=8, description="Nouveau mot de passe (min 8 caractères)"
    )


# =============================================================================
# TOKENS JWT
# =============================================================================


class TokenResponse(BaseModel):
    """Réponse contenant les tokens JWT."""

    access_token: str = Field(..., description="Token JWT d'accès")
    refresh_token: str = Field(..., description="Token JWT de refresh")
    token_type: str = Field(default="Bearer", description="Type de token")
    expires_in: int = Field(..., description="Durée de validité en secondes")


class RefreshTokenRequest(BaseModel):
    """Requête de renouvellement de token."""

    refresh_token: str = Field(..., description="Token de refresh")


class TokenPayload(BaseModel):
    """Payload décodé d'un token JWT CareLink."""

    sub: str = Field(..., description="Subject (user ID)")
    type: str = Field(..., description="Type de token (access/refresh)")
    exp: datetime = Field(..., description="Date d'expiration")
    iat: datetime = Field(..., description="Date d'émission")
    iss: str = Field(..., description="Issuer")
    # Claims personnalisés
    rpps: str | None = Field(None, description="Numéro RPPS")
    email: str | None = Field(None, description="Email")
    roles: list[str] = Field(default_factory=list, description="Rôles")
    tenant_id: int | None = Field(None, description="ID du tenant")
    is_admin: bool = Field(default=False, description="Est administrateur")

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# PRO SANTÉ CONNECT
# =============================================================================


class PSCAuthorizationResponse(BaseModel):
    """Réponse de génération d'URL d'autorisation PSC."""

    authorization_url: str = Field(..., description="URL de redirection vers PSC")
    state: str = Field(..., description="State à vérifier au callback (stocké en session)")


class PSCCallbackRequest(BaseModel):
    """
    Paramètres reçus lors du callback PSC.

    Ces paramètres sont passés en query string par PSC après
    l'authentification de l'utilisateur.
    """

    code: str = Field(..., description="Code d'autorisation")
    state: str = Field(..., description="State pour vérification CSRF")
    # Erreurs possibles
    error: str | None = Field(None, description="Code d'erreur (si échec)")
    error_description: str | None = Field(None, description="Description de l'erreur")


class PSCUserInfo(BaseModel):
    """
    Informations utilisateur retournées par PSC.

    Contient les données d'identité et professionnelles
    du professionnel de santé authentifié.
    """

    # Identifiant PSC
    sub: str = Field(..., description="Identifiant unique PSC")

    # Identifiant national (RPPS ou ADELI)
    subject_name_id: str = Field(..., alias="SubjectNameID", description="Numéro RPPS ou ADELI")

    # Identité
    family_name: str = Field(..., description="Nom de famille")
    given_name: str = Field(..., description="Prénom")
    preferred_username: str | None = Field(None, description="Nom d'usage")
    email: str | None = Field(None, description="Email (si disponible)")

    # Profession
    subject_role: list[str] | None = Field(None, alias="SubjectRole", description="Profession(s)")

    # Données sectorielles
    subject_ref_pro: dict[str, Any] | None = Field(
        None, alias="SubjectRefPro", description="Données d'exercice professionnel"
    )

    # Structure d'exercice
    subject_organization: str | None = Field(
        None, alias="SubjectOrganization", description="Structure d'exercice"
    )

    model_config = ConfigDict(populate_by_name=True)


class PSCUserInfoParsed(BaseModel):
    """Informations utilisateur PSC parsées et normalisées."""

    rpps: str = Field(..., description="Numéro RPPS")
    family_name: str = Field(..., description="Nom de famille (majuscules)")
    given_name: str = Field(..., description="Prénom")
    email: str | None = Field(None, description="Email (si disponible)")
    profession: str = Field(..., description="Libellé profession")
    profession_code: str | None = Field(None, description="Code profession ANS")
    speciality: str | None = Field(None, description="Code spécialité")
    exercise_modes: list[str] = Field(
        default_factory=list, description="Modes d'exercice (LIBERAL, SALARIE...)"
    )

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# RÉPONSES D'AUTHENTIFICATION
# =============================================================================


class AuthenticatedUser(BaseModel):
    """Informations de l'utilisateur authentifié."""

    id: int = Field(..., description="ID utilisateur CareLink")
    email: str = Field(..., description="Email")
    first_name: str = Field(..., description="Prénom")
    last_name: str = Field(..., description="Nom")
    full_name: str = Field(..., description="Nom complet")
    rpps: str | None = Field(None, description="Numéro RPPS")
    profession: str | None = Field(None, description="Profession")
    speciality: str | None = Field(None, description="Spécialité")
    roles: list[str] = Field(default_factory=list, description="Rôles")
    is_admin: bool = Field(default=False, description="Est administrateur")
    must_change_password: bool = Field(default=False, description="Doit changer son mot de passe")
    tenant_id: int = Field(..., description="ID du tenant")

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    """Réponse complète après authentification réussie."""

    user: AuthenticatedUser = Field(..., description="Informations utilisateur")
    tokens: TokenResponse = Field(..., description="Tokens JWT")
    auth_method: AuthMethod = Field(..., description="Méthode d'authentification")


class AuthStatusResponse(BaseModel):
    """Statut de l'authentification."""

    authenticated: bool = Field(..., description="L'utilisateur est-il authentifié ?")
    user: AuthenticatedUser | None = Field(None, description="Utilisateur si authentifié")
    psc_configured: bool = Field(..., description="PSC est-il configuré ?")
    psc_environment: str = Field(..., description="Environnement PSC (bas/prod)")


# =============================================================================
# SESSIONS PSC
# =============================================================================


class PSCSessionData(BaseModel):
    """
    Données de session PSC stockées côté serveur (Redis).

    Ces données sont stockées temporairement entre la redirection
    vers PSC et le callback.
    """

    state: str = Field(..., description="State CSRF")
    nonce: str = Field(..., description="Nonce pour id_token")
    code_verifier: str = Field(..., description="Code verifier PKCE")
    created_at: datetime = Field(..., description="Date de création")
    redirect_after: str | None = Field(None, description="URL de redirection après login")

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# GESTION DES ACCÈS PATIENTS
# =============================================================================


class PatientAccessRequest(BaseModel):
    """Requête d'attribution d'accès à un patient."""

    patient_id: int = Field(..., description="ID du patient")
    user_id: int = Field(..., description="ID de l'utilisateur")
    access_type: AccessType = Field(..., description="Type d'accès")
    reason: str = Field(..., min_length=10, description="Raison de l'accès (audit)")
    expires_in_days: int | None = Field(
        None, ge=1, le=365, description="Expiration en jours (None = permanent)"
    )


class PatientAccessResponse(BaseModel):
    """Réponse d'attribution d'accès."""

    patient_id: int
    user_id: int
    access_type: AccessType
    granted_by: int
    granted_at: datetime
    expires_at: datetime | None
    reason: str


class PatientAccessCheck(BaseModel):
    """Résultat de vérification d'accès patient."""

    has_access: bool = Field(..., description="L'utilisateur a-t-il accès ?")
    access_type: AccessType | None = Field(None, description="Type d'accès si autorisé")
    reason: str | None = Field(None, description="Raison du refus si applicable")


# =============================================================================
# ERREURS
# =============================================================================


class AuthErrorResponse(BaseModel):
    """Réponse d'erreur d'authentification."""

    error: str = Field(..., description="Code d'erreur")
    error_description: str = Field(..., description="Description de l'erreur")
    detail: str | None = Field(None, description="Détails supplémentaires")
