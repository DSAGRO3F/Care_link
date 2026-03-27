"""
Schémas Pydantic pour le module Patient.

Contient les schémas pour :
- Patient (dossier patient avec données chiffrées)
- PatientAccess (traçabilité RGPD)
- PatientEvaluation (évaluations AGGIR, etc.)
- PatientThreshold (seuils de constantes)
- PatientVitals (mesures de constantes)
- PatientDevice (devices connectés)
- PatientDocument (documents générés)
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# =============================================================================
# PATIENT SCHEMAS
# =============================================================================


class PatientBase(BaseModel):
    """Champs communs pour Patient."""

    # Données en clair (seront chiffrées côté service)
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    birth_date: date | None = None
    nir: str | None = Field(None, description="N° Sécurité Sociale")
    ins: str | None = Field(None, description="Identifiant National de Santé")
    address: str | None = Field(None, max_length=500)
    postal_code: str | None = Field(None, max_length=10)
    city: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None

    # Références
    entity_id: int = Field(..., description="ID de l'entité de rattachement")
    medecin_traitant_id: int | None = Field(None, description="ID du médecin traitant")

    # Géolocalisation (précision réduite pour RGPD)
    latitude: Decimal | None = Field(None, ge=-90, le=90)
    longitude: Decimal | None = Field(None, ge=-180, le=180)

    @field_validator("nir")
    @classmethod
    def validate_nir(cls, v: str | None) -> str | None:
        if v is not None:
            # NIR = 13 chiffres + 2 chiffres clé
            v = v.replace(" ", "")
            if len(v) not in [13, 15]:
                raise ValueError("Le NIR doit contenir 13 ou 15 chiffres")
        return v


class PatientCreate(PatientBase):
    """Schéma pour créer un patient."""


class PatientUpdate(BaseModel):
    """Schéma pour mettre à jour un patient."""

    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    birth_date: date | None = None
    nir: str | None = None
    ins: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    medecin_traitant_id: int | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None:
            valid = ["ACTIVE", "INACTIVE", "ARCHIVED", "DECEASED"]
            if v.upper() not in valid:
                raise ValueError(f"Statut invalide. Valeurs acceptées: {valid}")
            return v.upper()
        return v


class PatientSummary(BaseModel):
    """Schéma résumé pour les listes."""

    id: int
    # Note: first_name et last_name seront déchiffrés par le service
    first_name: str | None = None
    last_name: str | None = None
    birth_date: date | None = None
    status: str
    entity_id: int
    current_gir: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientResponse(BaseModel):
    """Schéma de réponse complet pour un patient."""

    id: int
    first_name: str | None = None
    last_name: str | None = None
    birth_date: date | None = None
    nir: str | None = None
    ins: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str
    entity_id: int
    entity_name: str | None = None
    medecin_traitant_id: int | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    current_gir: int | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PatientList(BaseModel):
    """Liste paginée de patients."""

    items: list[PatientSummary]
    total: int
    page: int
    size: int
    pages: int


# =============================================================================
# PATIENT ACCESS SCHEMAS (RGPD)
# =============================================================================


class PatientAccessBase(BaseModel):
    """Champs communs pour PatientAccess."""

    access_type: str = Field(..., description="Type d'accès (READ, WRITE, FULL)")
    reason: str = Field(..., min_length=10, max_length=500, description="Justification RGPD")
    expires_at: datetime | None = Field(None, description="Date d'expiration")

    @field_validator("access_type")
    @classmethod
    def validate_access_type(cls, v: str) -> str:
        valid = ["READ", "WRITE", "FULL"]
        if v.upper() not in valid:
            raise ValueError(f"Type d'accès invalide. Valeurs acceptées: {valid}")
        return v.upper()


class PatientAccessCreate(PatientAccessBase):
    """Schéma pour accorder un accès."""

    user_id: int = Field(..., description="ID de l'utilisateur")


class PatientAccessResponse(PatientAccessBase):
    """Schéma de réponse pour un accès."""

    id: int
    patient_id: int
    user_id: int
    granted_by: int
    granted_at: datetime
    revoked_at: datetime | None = None
    revoked_by: int | None = None
    is_active: bool
    is_expired: bool
    is_revoked: bool

    model_config = ConfigDict(from_attributes=True)


class PatientAccessList(BaseModel):
    """Liste des accès."""

    items: list[PatientAccessResponse]
    total: int


# =============================================================================
# PATIENT EVALUATION SCHEMAS
# =============================================================================


class PatientEvaluationBase(BaseModel):
    """Champs communs pour PatientEvaluation."""

    schema_type: str = Field(
        ..., description="Type de schéma (evaluation_complete, aggir_only, etc.)"
    )
    schema_version: str = Field("v1", max_length=20)
    evaluation_data: dict[str, Any] = Field(..., description="Données JSON de l'évaluation")
    evaluation_date: date = Field(..., description="Date de l'évaluation")
    # gir_score: Optional[int] = Field(None, ge=1, le=6, description="Score GIR (1-6)") # gir_score retiré de Base car calculé par backend/app/services/aggir/calculator.py

    @field_validator("schema_type")
    @classmethod
    def validate_schema_type(cls, v: str) -> str:
        valid = ["evaluation_complete", "aggir_only", "social_only", "health_only"]
        if v.lower() not in valid:
            raise ValueError(f"Type de schéma invalide. Valeurs acceptées: {valid}")
        return v.lower()


class PatientEvaluationCreate(PatientEvaluationBase):
    """Schéma pour créer une évaluation."""

    # Champs hérités de Base
    # Pas de gir_score car calculé automatiquement


class PatientEvaluationUpdate(BaseModel):
    """Schéma pour mettre à jour une évaluation."""

    evaluation_data: dict[str, Any] | None = None
    # gir_score: Optional[int] = Field(None, ge=1, le=6)

    # ajout des variables individuelles
    aggir_variable_code: str | None = Field(None, description="Code de la variable AGGIR modifiée")
    aggir_variable_data: dict[str, Any] | None = Field(None, description="Données de la variable")


class PatientEvaluationResponse(PatientEvaluationBase):
    """Schéma de réponse pour une évaluation."""

    id: int
    patient_id: int
    evaluator_id: int

    # Statut et progression (NOUVEAU)
    status: str
    completion_percent: int
    expires_at: datetime | None = None
    days_until_expiration: int | None = None

    # GIR (calculé)
    gir_score: int | None = None

    # Validation simple (existant)
    validated_at: datetime | None = None
    validated_by: int | None = None
    is_validated: bool

    # Double validation (NOUVEAU)
    medical_validated_at: datetime | None = None
    medical_validated_by: int | None = None
    department_validated_at: datetime | None = None
    department_validator_name: str | None = None
    is_fully_validated: bool

    # Métadonnées
    version: int
    created_at: datetime
    updated_at: datetime | None = None

    # Sessions (NOUVEAU)
    sessions_count: int = 0
    current_session_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class PatientEvaluationList(BaseModel):
    """Liste paginée d'évaluations."""

    items: list[PatientEvaluationResponse]
    total: int
    page: int
    size: int
    pages: int


class LatestSubmittedEvaluationResponse(BaseModel):
    """
    Réponse légère pour le pré-remplissage d'une nouvelle évaluation.

    Ne retourne que les données nécessaires au frontend :
    evaluation_data (sections stables) + métadonnées de datation.
    """

    evaluation_id: int = Field(..., description="ID de l'évaluation source")
    evaluation_date: date = Field(..., description="Date de l'évaluation source")
    evaluation_data: dict[str, Any] = Field(..., description="Données JSON décryptées")
    gir_score: int | None = Field(None, description="Dernier GIR connu")
    status: str = Field(..., description="Statut de l'évaluation source")

    model_config = ConfigDict(from_attributes=True)


class EvaluationValidate(BaseModel):
    """Schéma pour valider une évaluation."""

    # Pas de données, juste l'action


class DepartmentValidation(BaseModel):
    """Schéma pour validation CD."""

    validator_name: str = Field(..., min_length=2, max_length=200)
    reference: str = Field(..., min_length=1, max_length=100)


# =============================================================================
# EVALUATION SESSION SCHEMAS
# =============================================================================


class EvaluationSessionCreate(BaseModel):
    """Schéma pour démarrer une session de saisie."""

    device_info: str | None = Field(None, max_length=200, description="Info appareil")
    local_session_id: str | None = Field(None, max_length=100, description="ID local (hors-ligne)")


class EvaluationSessionUpdate(BaseModel):
    """Schéma pour mettre à jour une session."""

    status: str | None = None
    notes: str | None = None
    variables_recorded: list[str] | None = None


class EvaluationSessionResponse(BaseModel):
    """Schéma de réponse pour une session."""

    id: int
    evaluation_id: int
    user_id: int
    started_at: datetime
    ended_at: datetime | None = None
    status: str
    sync_status: str
    device_info: str | None = None
    variables_recorded: list[str] | None = None
    duration_minutes: int | None = None
    is_active: bool
    is_synced: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationSessionList(BaseModel):
    """Liste des sessions."""

    items: list[EvaluationSessionResponse]
    total: int


# =============================================================================
# AGGIR VARIABLE SCHEMAS
# =============================================================================


class AggirAdverbeInput(BaseModel):
    """Saisie d'un adverbe AGGIR."""

    question: str = Field(..., pattern="^[STCH]$", description="S, T, C ou H")
    reponse: bool = Field(..., description="Oui/Non")


class AggirVariableInput(BaseModel):
    """Saisie d'une variable AGGIR."""

    code: str = Field(..., description="Code de la variable (ex: TOILETTE_HAUT)")
    adverbes: list[AggirAdverbeInput] = Field(..., min_length=4, max_length=4)
    commentaire: str | None = Field(None, max_length=500)


class AggirVariableResponse(BaseModel):
    """Réponse pour une variable AGGIR."""

    code: str
    nom: str
    resultat: str | None = None  # A, B, C ou null
    status: str  # PENDING, COMPLETED
    recorded_at: datetime | None = None
    recorded_by_user_id: int | None = None
    recorded_by_name: str | None = None
    session_id: int | None = None
    adverbes: list[dict[str, Any]]
    commentaire: str | None = None


# =============================================================================
# GIR COMPUTE SCHEMAS (CALCUL PRÉLIMINAIRE — MODE DRAFT)
# =============================================================================


class GirComputeRequest(BaseModel):
    """
    Body pour le calcul préliminaire du GIR pendant la saisie (mode DRAFT).

    Accepte les sous-variables (TOILETTE_HAUT, TOILETTE_BAS, etc.) —
    calculator.py gère lui-même la combinaison en variables principales.
    """

    variables: list[AggirVariableInput] = Field(
        ...,
        description="Liste des variables AGGIR cotées (sous-variables incluses)",
    )


class GirComputeResponse(BaseModel):
    """Résultat du calcul GIR préliminaire — lecture seule, sans écriture en base."""

    gir_score: int = Field(
        ...,
        ge=1,
        le=6,
        description="Score GIR calculé (1 = très dépendant, 6 = autonome)",
    )


# =============================================================================
# SYNC SCHEMAS (MODE HORS-LIGNE)
# =============================================================================


class SyncPayload(BaseModel):
    """Payload de synchronisation depuis le client."""

    local_session_id: str
    evaluation_id: int
    changes: list[dict[str, Any]]
    client_timestamp: datetime
    device_info: str | None = None


class SyncResponse(BaseModel):
    """Réponse de synchronisation."""

    success: bool
    server_timestamp: datetime
    conflicts: list[dict[str, Any]] = []
    synced_changes: int
    evaluation_status: str
    completion_percent: int


class SyncConflict(BaseModel):
    """Détail d'un conflit de synchronisation."""

    variable_code: str
    client_value: dict[str, Any]
    server_value: dict[str, Any]
    server_timestamp: datetime
    resolution: str = "SERVER_WINS"  # ou CLIENT_WINS


# =============================================================================
# PATIENT THRESHOLD SCHEMAS
# =============================================================================


class PatientThresholdBase(BaseModel):
    """Champs communs pour PatientThreshold."""

    vital_type: str = Field(..., description="Type de constante (FC, TA_SYS, TA_DIA, etc.)")
    min_value: float | None = Field(None, description="Valeur minimale")
    max_value: float | None = Field(None, description="Valeur maximale")
    unit: str = Field(..., max_length=20, description="Unité de mesure")
    surveillance_frequency: str | None = Field(
        None, max_length=50, description="Fréquence de surveillance"
    )

    @field_validator("vital_type")
    @classmethod
    def validate_vital_type(cls, v: str) -> str:
        valid = ["FC", "TA_SYS", "TA_DIA", "SPO2", "TEMP", "GLYC", "POIDS", "DOULEUR"]
        if v.upper() not in valid:
            raise ValueError(f"Type de constante invalide. Valeurs acceptées: {valid}")
        return v.upper()


class PatientThresholdCreate(PatientThresholdBase):
    """Schéma pour créer un seuil."""


class PatientThresholdUpdate(BaseModel):
    """Schéma pour mettre à jour un seuil."""

    min_value: float | None = None
    max_value: float | None = None
    unit: str | None = None
    surveillance_frequency: str | None = None


class PatientThresholdResponse(PatientThresholdBase):
    """Schéma de réponse pour un seuil."""

    id: int
    patient_id: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PatientThresholdList(BaseModel):
    """Liste des seuils."""

    items: list[PatientThresholdResponse]
    total: int


# =============================================================================
# PATIENT VITALS SCHEMAS
# =============================================================================


class PatientVitalsBase(BaseModel):
    """Champs communs pour PatientVitals."""

    vital_type: str = Field(..., description="Type de constante")
    value: float = Field(..., description="Valeur mesurée")
    unit: str = Field(..., max_length=20)
    source: str = Field("MANUAL", description="Source de la mesure")
    measured_at: datetime = Field(..., description="Date/heure de la mesure")
    notes: str | None = Field(None, max_length=500)

    @field_validator("vital_type")
    @classmethod
    def validate_vital_type(cls, v: str) -> str:
        valid = ["FC", "TA_SYS", "TA_DIA", "SPO2", "TEMP", "GLYC", "POIDS", "DOULEUR"]
        if v.upper() not in valid:
            raise ValueError(f"Type de constante invalide. Valeurs acceptées: {valid}")
        return v.upper()

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        valid = ["MANUAL", "DEVICE", "IMPORT", "PATIENT"]
        if v.upper() not in valid:
            raise ValueError(f"Source invalide. Valeurs acceptées: {valid}")
        return v.upper()


class PatientVitalsCreate(PatientVitalsBase):
    """Schéma pour créer une mesure."""

    device_id: int | None = Field(None, description="ID du device source")


class PatientVitalsResponse(PatientVitalsBase):
    """Schéma de réponse pour une mesure."""

    id: int
    patient_id: int
    status: str | None = None
    device_id: int | None = None
    recorded_by: int | None = None
    is_manual: bool
    is_abnormal: bool
    is_critical: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientVitalsList(BaseModel):
    """Liste paginée de mesures."""

    items: list[PatientVitalsResponse]
    total: int
    page: int
    size: int
    pages: int


# =============================================================================
# PATIENT DEVICE SCHEMAS
# =============================================================================


class PatientDeviceBase(BaseModel):
    """Champs communs pour PatientDevice."""

    device_type: str = Field(..., description="Type de device")
    device_identifier: str = Field(..., max_length=100, description="Identifiant unique du device")
    device_name: str | None = Field(None, max_length=100, description="Nom personnalisé")

    @field_validator("device_type")
    @classmethod
    def validate_device_type(cls, v: str) -> str:
        valid = [
            "WITHINGS_SCALE",
            "WITHINGS_BPM",
            "APPLE_WATCH",
            "FITBIT",
            "SAMSUNG_HEALTH",
            "OTHER",
        ]
        if v.upper() not in valid:
            raise ValueError(f"Type de device invalide. Valeurs acceptées: {valid}")
        return v.upper()


class PatientDeviceCreate(PatientDeviceBase):
    """Schéma pour créer un device."""


class PatientDeviceUpdate(BaseModel):
    """Schéma pour mettre à jour un device."""

    device_name: str | None = None
    is_active: bool | None = None


class PatientDeviceResponse(PatientDeviceBase):
    """Schéma de réponse pour un device."""

    id: int
    patient_id: int
    is_active: bool
    last_sync_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PatientDeviceList(BaseModel):
    """Liste des devices."""

    items: list[PatientDeviceResponse]
    total: int


# =============================================================================
# PATIENT DOCUMENT SCHEMAS
# =============================================================================


class PatientDocumentBase(BaseModel):
    """Champs communs pour PatientDocument."""

    document_type: str = Field(..., description="Type de document (PPA, PPCS, RECOMMENDATION)")
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

    @field_validator("document_type")
    @classmethod
    def validate_document_type(cls, v: str) -> str:
        valid = ["PPA", "PPCS", "RECOMMENDATION", "OTHER"]
        if v.upper() not in valid:
            raise ValueError(f"Type de document invalide. Valeurs acceptées: {valid}")
        return v.upper()


class PatientDocumentCreate(PatientDocumentBase):
    """Schéma pour créer un document."""

    source_evaluation_id: int | None = None
    generation_prompt: str | None = None
    generation_context: dict[str, Any] | None = None
    file_format: str = Field("pdf", description="Format du fichier (pdf, docx)")

    @field_validator("file_format")
    @classmethod
    def validate_file_format(cls, v: str) -> str:
        valid = ["pdf", "docx"]
        if v.lower() not in valid:
            raise ValueError(f"Format invalide. Valeurs acceptées: {valid}")
        return v.lower()


class PatientDocumentResponse(PatientDocumentBase):
    """Schéma de réponse pour un document."""

    id: int
    patient_id: int
    source_evaluation_id: int | None = None
    file_path: str
    file_format: str
    file_size_bytes: int | None = None
    generated_at: datetime
    generated_by: int
    is_ppa: bool
    is_ppcs: bool
    is_recommendation: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientDocumentList(BaseModel):
    """Liste des documents."""

    items: list[PatientDocumentResponse]
    total: int


# =============================================================================
# FILTER SCHEMAS
# =============================================================================


class PatientFilters(BaseModel):
    """Filtres pour la recherche de patients."""

    entity_id: int | None = None
    status: str | None = None
    medecin_traitant_id: int | None = None
    gir_min: int | None = Field(None, ge=1, le=6)
    gir_max: int | None = Field(None, ge=1, le=6)
    search: str | None = Field(None, description="Recherche sur nom, prénom")


class VitalsFilters(BaseModel):
    """Filtres pour les mesures de constantes."""

    vital_type: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    status: str | None = None


# =============================================================================
# VALIDATION ERROR SCHEMAS
# =============================================================================


class ValidationErrorDetail(BaseModel):
    """Détail d'une erreur de validation JSON Schema."""

    path: str = Field(..., description="Chemin vers le champ en erreur (ex: aggir.GIR)")
    message: str = Field(..., description="Message d'erreur")
    value: Any | None = Field(None, description="Valeur rejetée")


class ValidationErrorResponse(BaseModel):
    """Réponse en cas d'erreur de validation JSON Schema."""

    detail: str = Field(..., description="Message d'erreur principal")
    errors: list[ValidationErrorDetail] = Field(
        default_factory=list, description="Liste détaillée des erreurs"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Validation échouée: 3 erreur(s) détectée(s)",
                "errors": [
                    {"path": "aggir.GIR", "message": "1 is not of type 'integer'"},
                    {"path": "usager.adresse", "message": "'adresse' is a required property"},
                ],
            }
        }
    )
