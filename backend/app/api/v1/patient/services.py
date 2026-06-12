"""
Services métier pour le module Patient.

Contient la logique CRUD pour :
- PatientService (MULTI-TENANT) - AVEC CHIFFREMENT
- PatientAccessService
- PatientEvaluationService
- PatientThresholdService
- PatientVitalsService
- PatientDeviceService
- PatientDocumentService

CHIFFREMENT: Les données sensibles (PII) sont chiffrées AES-256-GCM.
La recherche utilise des blind indexes HMAC-SHA256.

PRINCIPES:
- Chiffrer evaluation_data AVANT le stockage (create/update)
- Déchiffrer evaluation_data APRÈS la lecture (get)
- Les métadonnées (status, completion_percent, etc.) restent en clair

MULTI-TENANT: Toutes les opérations Patient sont filtrées par tenant_id.
"""

import logging
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    # Ces imports ne sont utilisés QUE pour les type hints
    # Ils ne sont pas exécutés à runtime → pas d'import circulaire
    pass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.patient.schemas import (
    PatientAccessCreate,
    PatientCreate,
    PatientDeviceCreate,
    PatientDeviceUpdate,
    PatientDocumentCreate,
    PatientEvaluationCreate,
    PatientEvaluationUpdate,
    PatientFilters,
    PatientThresholdCreate,
    PatientThresholdUpdate,
    PatientUpdate,
    PatientVitalsCreate,
    VitalsFilters,
)
from app.models.organization.entity import Entity
from app.models.patient.evaluation_session import EvaluationSession
from app.models.patient.patient import Patient
from app.models.patient.patient_access import PatientAccess
from app.models.patient.patient_document import PatientDocument
from app.models.patient.patient_evaluation import PatientEvaluation
from app.models.patient.patient_vitals import PatientDevice, PatientThreshold, PatientVitals
from app.models.user.user import User
from app.services.aggir.calculator import (
    AggiralgorithmTable,
    AggirCalculator,
    Variable,
)

# Import du service de chiffrement
from app.services.encryption import (
    decrypt_evaluation_data,
    encrypt_evaluation_data,
    patient_encryptor,
)

# Import des calculateurs cliniques et AGGIR
from app.services.sante.test_calculators import compute_all_sante_tests
from app.services.validation.schema_validator import (
    SchemaNotFoundError,
    SchemaValidationError,
    get_schema_validator,
)


# =============================================================================
# EXCEPTIONS
# =============================================================================


class PatientNotFoundError(Exception):
    """Patient non trouvé."""


class EntityNotFoundError(Exception):
    """Entité non trouvée."""


class UserNotFoundError(Exception):
    """Utilisateur non trouvé."""


class EvaluationNotFoundError(Exception):
    """Évaluation non trouvée."""


class SessionNotFoundError(Exception):
    """Session d'évaluation non trouvée."""


class ThresholdNotFoundError(Exception):
    """Seuil non trouvé."""


class VitalsNotFoundError(Exception):
    """Mesure non trouvée."""


class DeviceNotFoundError(Exception):
    """Device non trouvé."""


class DocumentNotFoundError(Exception):
    """Document non trouvé."""


class AccessNotFoundError(Exception):
    """Accès non trouvé."""


class DuplicateThresholdError(Exception):
    """Seuil déjà défini pour ce type de constante."""


class DuplicateDeviceError(Exception):
    """Device déjà enregistré."""


class AccessDeniedError(Exception):
    """Accès refusé au dossier patient."""


class EvaluationAlreadyValidatedError(Exception):
    """L'évaluation est déjà validée."""


class EvaluationInProgressError(Exception):
    """Une évaluation est déjà en cours pour ce patient.
    Porte l'ID de l'évaluation existante pour que le frontend puisse basculer en mode PATCH.
    """

    def __init__(self, message: str, evaluation_id: int):
        super().__init__(message)
        self.evaluation_id = evaluation_id


class EvaluationNotEditableError(Exception):
    """L'évaluation ne peut plus être modifiée (validée)."""


class InvalidEvaluationDataError(Exception):
    """Données d'évaluation invalides selon le JSON Schema."""

    def __init__(self, message: str, errors: list | None = None):
        self.message = message
        self.errors = errors or []
        super().__init__(message)


class DuplicateNIRError(Exception):
    """Un patient avec ce NIR existe déjà."""


class SessionAlreadyActiveError(Exception):
    """Une session est déjà active pour cette évaluation."""


# =============================================================================
# PATIENT SERVICE (MULTI-TENANT) - AVEC CHIFFREMENT
# =============================================================================


class PatientService:
    """
    Service pour la gestion des patients.

    MULTI-TENANT: Toutes les opérations sont filtrées par tenant_id.

    CHIFFREMENT:
    - Les données PII sont chiffrées AES-256-GCM avant stockage
    - Les blind indexes HMAC-SHA256 permettent la recherche
    - Le déchiffrement est effectué à la lecture
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant courant (extrait de l'utilisateur authentifié)
        """
        self.db = db
        self.tenant_id = tenant_id

    def _base_query(self):
        """Retourne une requête de base filtrée par tenant."""
        return select(Patient).where(Patient.tenant_id == self.tenant_id)

    # =========================================================================
    # HELPERS DE DÉCHIFFREMENT
    # =========================================================================

    def _decrypt_patient(self, patient: Patient) -> dict[str, Any]:
        """
        Déchiffre les données d'un patient pour l'API.

        Args:
            patient: Instance Patient avec données chiffrées

        Returns:
            Dict avec données déchiffrées prêtes pour PatientResponse
        """
        # Récupérer les champs déchiffrés
        decrypted = patient_encryptor.decrypt_model(patient)

        # Construire le dict de réponse
        #
        # Résolution du nom de l'entité de rattachement (B5 — évite "Entité #387" côté frontend).
        # Une seule requête supplémentaire, acceptable pour un GET /patients/{id} unitaire.
        entity_name = None
        if patient.entity_id:
            entity = self.db.execute(
                select(Entity.name).where(Entity.id == patient.entity_id)
            ).scalar_one_or_none()
            entity_name = entity  # scalar_one_or_none retourne directement la valeur str

        return {
            "id": patient.id,
            "first_name": decrypted.get("first_name"),
            "last_name": decrypted.get("last_name"),
            "birth_date": decrypted.get("birth_date"),
            "nir": decrypted.get("nir"),
            "ins": decrypted.get("ins"),
            "address": decrypted.get("address"),
            "postal_code": decrypted.get("postal_code"),
            "city": decrypted.get("city"),
            "phone": decrypted.get("phone"),
            "email": decrypted.get("email"),
            "status": patient.status,
            "entity_id": patient.entity_id,
            "entity_name": entity_name,
            "medecin_traitant_id": patient.medecin_traitant_id,
            "latitude": patient.latitude,
            "longitude": patient.longitude,
            "current_gir": patient.current_gir,
            "created_at": patient.created_at,
            "updated_at": patient.updated_at,
        }

    def _decrypt_patient_summary(self, patient: Patient) -> dict[str, Any]:
        """
        Déchiffre les données minimales d'un patient pour les listes.

        Args:
            patient: Instance Patient

        Returns:
            Dict avec données minimales déchiffrées
        """
        decrypted = patient_encryptor.decrypt_model(patient)

        return {
            "id": patient.id,
            "first_name": decrypted.get("first_name"),
            "last_name": decrypted.get("last_name"),
            "birth_date": decrypted.get("birth_date"),
            "status": patient.status,
            "entity_id": patient.entity_id,
            "current_gir": patient.current_gir,
            "created_at": patient.created_at,
        }

    # =========================================================================
    # MÉTHODES CRUD
    # =========================================================================

    def get_all(
        self,
        page: int = 1,
        size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        filters: PatientFilters | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Liste les patients avec pagination et filtres.

        Returns:
            Tuple[List[Dict], int]: (patients déchiffrés, total)
        """
        query = self._base_query()

        # Appliquer les filtres
        if filters:
            if filters.status:
                query = query.where(Patient.status == filters.status)
            if filters.entity_id:
                query = query.where(Patient.entity_id == filters.entity_id)
            if filters.gir_min:
                query = query.where(Patient.current_gir >= filters.gir_min)
            if filters.gir_max:
                query = query.where(Patient.current_gir <= filters.gir_max)

        # Compter le total
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar()

        # Tri
        sort_column = getattr(Patient, sort_by, Patient.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        patients = self.db.execute(query).scalars().all()

        # Déchiffrer pour l'API
        return [self._decrypt_patient_summary(p) for p in patients], total

    def get_by_id(self, patient_id: int) -> Patient:
        """Récupère un patient par son ID."""
        query = self._base_query().where(Patient.id == patient_id)
        patient = self.db.execute(query).scalar_one_or_none()

        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")

        return patient

    def get_by_id_decrypted(self, patient_id: int) -> dict[str, Any]:
        """Récupère un patient déchiffré par son ID."""
        patient = self.get_by_id(patient_id)
        return self._decrypt_patient(patient)

    def create(self, data: PatientCreate, created_by: int) -> Patient:
        """Crée un nouveau patient avec chiffrement."""
        # Vérifier l'entité
        entity = self.db.execute(
            select(Entity).where(Entity.id == data.entity_id, Entity.tenant_id == self.tenant_id)
        ).scalar_one_or_none()

        if not entity:
            raise EntityNotFoundError(f"Entité {data.entity_id} non trouvée")

        # Vérifier l'unicité du NIR
        if data.nir:
            existing = self.search_by_nir(data.nir)
            if existing:
                raise DuplicateNIRError(f"Un patient avec ce NIR existe déjà (ID: {existing.id})")

        # Préparer les données à chiffrer
        plain_data = {
            "first_name": data.first_name,
            "last_name": data.last_name,
            "birth_date": data.birth_date.isoformat() if data.birth_date else None,
            "nir": data.nir,
            "ins": data.ins,
            "address": data.address,
            "postal_code": data.postal_code,
            "city": data.city,
            "phone": data.phone,
            "email": data.email,
        }

        # Chiffrer
        encrypted = patient_encryptor.encrypt_for_db(plain_data, self.tenant_id)

        # Créer le patient
        patient = Patient(
            tenant_id=self.tenant_id,
            entity_id=data.entity_id,
            medecin_traitant_id=data.medecin_traitant_id,
            latitude=data.latitude,
            longitude=data.longitude,
            status="ACTIVE",
            created_by=created_by,
            **encrypted,
        )

        self.db.add(patient)
        self.db.flush()
        return patient

    def update(
        self,
        patient_id: int,
        data: PatientUpdate,
        updated_by: int | None = None,
    ) -> Patient:
        """Met à jour un patient."""
        patient = self.get_by_id(patient_id)
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return patient

        # Vérifier médecin traitant si modifié
        if update_data.get("medecin_traitant_id"):
            medecin = self.db.execute(
                select(User).where(
                    User.id == update_data["medecin_traitant_id"], User.tenant_id == self.tenant_id
                )
            ).scalar_one_or_none()

            if not medecin:
                raise UserNotFoundError(f"Médecin {update_data['medecin_traitant_id']} non trouvé")

        # Vérifier l'unicité du NIR si modifié
        if update_data.get("nir"):
            existing = self.search_by_nir(update_data["nir"])
            if existing and existing.id != patient_id:
                raise DuplicateNIRError(f"Un patient avec ce NIR existe déjà (ID: {existing.id})")

        # Séparer les champs chiffrés des champs non chiffrés
        encrypted_field_names = patient_encryptor.get_encrypted_field_names()

        fields_to_encrypt = {}
        other_fields = {}

        for field, value in update_data.items():
            if field in encrypted_field_names:
                fields_to_encrypt[field] = value
            else:
                other_fields[field] = value

        # Chiffrer les champs PII modifiés
        if fields_to_encrypt:
            encrypted_update = patient_encryptor.encrypt_for_db(fields_to_encrypt, self.tenant_id)
            # Appliquer les valeurs chiffrées
            for db_field, value in encrypted_update.items():
                setattr(patient, db_field, value)

        # Appliquer les champs non chiffrés
        for field, value in other_fields.items():
            setattr(patient, field, value)

        # Mettre à jour updated_by si fourni
        if updated_by:
            patient.updated_by = updated_by

        self.db.flush()
        return patient

    def delete(self, patient_id: int) -> None:
        """Archive un patient (soft delete)."""
        patient = self.get_by_id(patient_id)
        patient.status = "ARCHIVED"
        self.db.flush()

    # =========================================================================
    # MÉTHODES DE RECHERCHE (BLIND INDEX)
    # =========================================================================

    def search_by_nir(self, nir: str) -> Patient | None:
        """Recherche un patient par son NIR."""
        blind = patient_encryptor.search_by_nir(nir, self.tenant_id)
        query = self._base_query().where(Patient.nir_blind == blind)
        return self.db.execute(query).scalar_one_or_none()

    def search_by_ins(self, ins: str) -> Patient | None:
        """Recherche un patient par son INS."""
        blind = patient_encryptor.search_by_ins(ins, self.tenant_id)
        query = self._base_query().where(Patient.ins_blind == blind)
        return self.db.execute(query).scalar_one_or_none()

    def search_by_name(
        self,
        last_name: str | None = None,
        first_name: str | None = None,
    ) -> list[Patient]:
        """Recherche des patients par nom et/ou prénom."""
        query = self._base_query()

        blinds = patient_encryptor.search_by_name(
            last_name=last_name,
            first_name=first_name,
            tenant_id=self.tenant_id,
        )

        if "last_name" in blinds:
            query = query.where(Patient.last_name_blind == blinds["last_name"])

        if "first_name" in blinds:
            query = query.where(Patient.first_name_blind == blinds["first_name"])

        return list(self.db.execute(query).scalars().all())

    def check_duplicate(
        self,
        nir: str | None = None,
        ins: str | None = None,
        exclude_patient_id: int | None = None,
    ) -> Patient | None:
        """Vérifie si un patient avec le même NIR ou INS existe."""
        if nir:
            existing = self.search_by_nir(nir)
            if existing and existing.id != exclude_patient_id:
                return existing

        if ins:
            existing = self.search_by_ins(ins)
            if existing and existing.id != exclude_patient_id:
                return existing

        return None


# =============================================================================
# PATIENT ACCESS SERVICE (RGPD) - Hérite du tenant via patient
# =============================================================================


class PatientAccessService:
    """
    Service pour la gestion des accès patients (RGPD).

    NOTE: Les accès héritent du tenant via le patient.
    """

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    def _verify_patient_access(self, patient_id: int) -> Patient:
        """Vérifie que le patient appartient au tenant."""
        patient = self.db.execute(
            select(Patient).where(Patient.id == patient_id, Patient.tenant_id == self.tenant_id)
        ).scalar_one_or_none()

        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        return patient

    def get_all_for_patient(
        self,
        patient_id: int,
        active_only: bool = True,
    ) -> list[PatientAccess]:
        """Liste les accès d'un patient."""
        self._verify_patient_access(patient_id)

        query = select(PatientAccess).where(PatientAccess.patient_id == patient_id)

        if active_only:
            query = query.where(PatientAccess.revoked_at.is_(None))

        query = query.order_by(PatientAccess.granted_at.desc())
        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, access_id: int, patient_id: int) -> PatientAccess:
        """Récupère un accès par son ID."""
        self._verify_patient_access(patient_id)

        access = self.db.get(PatientAccess, access_id)
        if not access or access.patient_id != patient_id:
            raise AccessNotFoundError(f"Accès {access_id} non trouvé")
        return access

    def grant_access(
        self,
        patient_id: int,
        user_id: int,
        data: PatientAccessCreate,
        granted_by: int,
    ) -> PatientAccess:
        """Accorde un accès à un utilisateur."""
        self._verify_patient_access(patient_id)

        # Vérifier que l'utilisateur existe ET appartient au tenant
        user = self.db.execute(
            select(User).where(User.id == user_id, User.tenant_id == self.tenant_id)
        ).scalar_one_or_none()

        if not user:
            raise UserNotFoundError(f"Utilisateur {user_id} non trouvé")

        access = PatientAccess(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            user_id=user_id,
            access_type=data.access_type,
            reason=data.reason,
            expires_at=data.expires_at,
            granted_by=granted_by,
        )

        self.db.add(access)
        self.db.flush()
        return access

    def revoke_access(self, access_id: int, patient_id: int, revoked_by: int) -> PatientAccess:
        """Révoque un accès."""
        access = self.get_by_id(access_id, patient_id)
        access.revoke(revoked_by)
        self.db.flush()
        return access


# =============================================================================
# PATIENT EVALUATION SERVICE (MULTI-SESSION + JSON SCHEMA)
# =============================================================================


class PatientEvaluationService:
    """
    Service pour la gestion des évaluations patients.

    Fonctionnalités:
    - CRUD des évaluations
    - Gestion multi-session (saisie sur plusieurs jours)
    - Validation JSON Schema (partielle/complète)
    - Workflow de validation double (médecin + CD)
    - Gestion expiration (J+7)
    - Synchronisation offline
    """

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    def _verify_patient_access(self, patient_id: int) -> Patient:
        """Vérifie que le patient appartient au tenant."""
        patient = self.db.execute(
            select(Patient).where(Patient.id == patient_id, Patient.tenant_id == self.tenant_id)
        ).scalar_one_or_none()

        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        return patient

    def _check_evaluation_editable(self, evaluation: PatientEvaluation) -> None:
        """Vérifie que l'évaluation peut être modifiée."""
        if evaluation.status == "VALIDATED":
            raise EvaluationAlreadyValidatedError(f"L'évaluation {evaluation.id} est déjà validée")
        if evaluation.status not in ["DRAFT", "IN_PROGRESS"]:
            raise EvaluationNotEditableError(
                f"L'évaluation {evaluation.id} ne peut plus être modifiée (statut: {evaluation.status})"
            )

    def _validate_evaluation_data(
        self, data: dict[str, Any], schema_type: str, schema_version: str, partial: bool = True
    ) -> None:
        """
        Valide les données d'évaluation contre le JSON Schema.

        Args:
            data: Données à valider
            schema_type: Type de schéma (ex: "evaluation_complete")
            schema_version: Version du schéma (ex: "v1")
            partial: True pour validation partielle, False pour complète
        """
        try:
            validator = get_schema_validator()  # ✅ singleton sans args
            if partial:
                validator.validate_partial(
                    schema_type, schema_version, data
                )  # ✅ signature correcte
            else:
                validator.validate_full(
                    schema_type, schema_version, data
                )  # ✅ validate_full (pas validate_complete)
        except SchemaNotFoundError as e:
            raise InvalidEvaluationDataError(f"Schéma inconnu: {e}") from e
        except SchemaValidationError as e:
            raise InvalidEvaluationDataError(
                message=f"Données invalides: {e.message}", errors=e.errors
            ) from e

    def _compute_gir_from_data(self, aggir_variables: list) -> int | None:
        """
        Calcule le score GIR à partir des Resultat pré-calculés dans AggirVariable[].

        Le wizard stocke les variables AGGIR avec des noms français
        (ex: "Transferts", "Cohérence") et des Resultat déjà calculés (A/B/C).
        Cette méthode lit ces Resultat directement et applique l'algorithme
        officiel (décret 1997-04-28) via les tables de scoring.

        Args:
            aggir_variables: liste AggirVariable depuis evaluation_data["aggir"]["AggirVariable"]

        Returns:
            Score GIR (1-6) ou None si données insuffisantes
        """
        # Mapping noms français → Variable enum (10 discriminantes)
        NOM_TO_VARIABLE = {  # noqa: N806
            "Cohérence": Variable.COHERENCE,
            "Orientation": Variable.ORIENTATION,
            "Toilette": Variable.TOILETTE,
            "Habillage": Variable.HABILLAGE,
            "Alimentation": Variable.ALIMENTATION,
            "Élimination": Variable.ELIMINATION,
            "Elimination": Variable.ELIMINATION,  # variante sans accent (wizard)
            "Transferts": Variable.TRANSFERTS,
            "Déplacements intérieurs": Variable.DEPLACEMENTS_INTERNES,
            "Déplacements extérieurs": Variable.DEPLACEMENTS_EXTERNES,
            "Alerter": Variable.ALERTER,
        }

        try:
            lettres_principales = {}
            for var in aggir_variables:
                nom = var.get("Nom", "")
                resultat = var.get("Resultat")
                variable_enum = NOM_TO_VARIABLE.get(nom)
                if variable_enum and resultat in ("A", "B", "C"):
                    lettres_principales[variable_enum] = resultat

            # Il faut les 10 variables discriminantes pour un calcul fiable
            if len(lettres_principales) < 10:
                return None

            # Appliquer l'algorithme officiel directement sur les lettres
            ordre_groupes = ["A", "B", "C", "D", "E", "F", "G", "H"]

            for groupe_name in ordre_groupes:
                groupe = AggiralgorithmTable.GROUPES[groupe_name]
                score = AggirCalculator.calculer_score_groupe(lettres_principales, groupe)
                gir = AggirCalculator.determiner_gir_depuis_score(score, groupe_name)
                if gir is not None:
                    return gir

            return 6  # Défaut (autonome) si aucun groupe ne matche
        except Exception as e:
            # Logger l'erreur au lieu de l'avaler silencieusement
            logger.error(f"GIR calculation failed: {type(e).__name__}: {e}")
            return None

    # =========================================================================
    # CRUD ÉVALUATIONS
    # =========================================================================

    # ---------- Lire évaluations d'un patient ---------------
    def get_all_for_patient(
        self,
        patient_id: int,
    ) -> list[PatientEvaluation]:
        """
        Liste les évaluations d'un patient.

        CHIFFREMENT: evaluation_data est déchiffré pour chaque évaluation.
        """
        self._verify_patient_access(patient_id)

        query = select(PatientEvaluation).where(
            PatientEvaluation.patient_id == patient_id,
            PatientEvaluation.tenant_id == self.tenant_id,
        )

        query = query.order_by(PatientEvaluation.evaluation_date.desc())
        evaluations = list(self.db.execute(query).scalars().all())

        # NOUVEAU: Déchiffrer evaluation_data de chaque évaluation
        for evaluation in evaluations:
            if evaluation.evaluation_data:
                evaluation.evaluation_data = decrypt_evaluation_data(evaluation.evaluation_data)

        return evaluations

    # ---------- Récupérer une évaluations d'un patient ---------------

    def get_by_id(self, evaluation_id: int, patient_id: int) -> PatientEvaluation:
        """Récupère une évaluation par son ID.
        CHIFFREMENT: evaluation_data est déchiffré avant retour.
        """
        self._verify_patient_access(patient_id)

        evaluation = self.db.execute(
            select(PatientEvaluation).where(
                PatientEvaluation.id == evaluation_id,
                PatientEvaluation.patient_id == patient_id,
                PatientEvaluation.tenant_id == self.tenant_id,
            )
        ).scalar_one_or_none()

        if not evaluation:
            raise EvaluationNotFoundError(f"Évaluation {evaluation_id} non trouvée")

        # Déchiffrer evaluation_data
        if evaluation.evaluation_data:
            evaluation.evaluation_data = decrypt_evaluation_data(evaluation.evaluation_data)

        return evaluation

    # ---------- Dernière évaluation soumise (pré-remplissage) ---------------

    def get_latest_submitted(self, patient_id: int) -> PatientEvaluation | None:
        """
        Retourne la dernière évaluation soumise (non-brouillon) d'un patient.

        Utilisé pour pré-remplir une nouvelle évaluation avec les sections
        stables (usager, contacts, social, matériels, dispositifs).

        Statuts considérés comme "soumis" (workflow B40-J1 — Phase 4 bis) :
        PENDING_INTERNAL_REVIEW, PENDING_MEDICAL, AWAITING_FUNDING_DECISION,
        VALIDATED. `DRAFT` / `IN_PROGRESS` sont exclus (saisie en cours),
        `FUNDING_REJECTED` / `OBSOLETE` aussi (états non-réutilisables).

        CHIFFREMENT: evaluation_data est déchiffré avant retour.

        Returns:
            PatientEvaluation ou None si aucune évaluation soumise n'existe.
        """
        self._verify_patient_access(patient_id)

        SUBMITTED_STATUSES = [  # noqa: N806
            "PENDING_INTERNAL_REVIEW",
            "PENDING_MEDICAL",
            "AWAITING_FUNDING_DECISION",
            "VALIDATED",
        ]

        evaluation = (
            self.db.execute(
                select(PatientEvaluation)
                .where(
                    PatientEvaluation.patient_id == patient_id,
                    PatientEvaluation.tenant_id == self.tenant_id,
                    PatientEvaluation.status.in_(SUBMITTED_STATUSES),
                )
                .order_by(PatientEvaluation.evaluation_date.desc())
            )
            .scalars()
            .first()
        )

        if not evaluation:
            return None

        # Déchiffrer evaluation_data
        if evaluation.evaluation_data:
            evaluation.evaluation_data = decrypt_evaluation_data(evaluation.evaluation_data)

        return evaluation

    # ---------- Créer Nouvelle évaluation patient ---------------

    def create(
        self,
        patient_id: int,
        data: PatientEvaluationCreate,
        evaluator_id: int,
    ) -> PatientEvaluation:
        """
        Crée une nouvelle évaluation.

        La validation JSON Schema est partielle (tolère champs manquants).
        CHIFFREMENT: evaluation_data est chiffré avant stockage.
        """
        self._verify_patient_access(patient_id)

        # Vérifier qu'il n'y a pas d'évaluation DRAFT/IN_PROGRESS
        existing = self.db.execute(
            select(PatientEvaluation).where(
                PatientEvaluation.patient_id == patient_id,
                PatientEvaluation.tenant_id == self.tenant_id,
                PatientEvaluation.status.in_(["DRAFT", "IN_PROGRESS"]),
            )
        ).scalar_one_or_none()

        if existing:
            raise EvaluationInProgressError(
                f"Une évaluation est déjà en cours (ID: {existing.id})",
                evaluation_id=existing.id,
            )

        # Validation partielle des données (EN CLAIR - avant chiffrement)
        if data.evaluation_data:
            self._validate_evaluation_data(
                data.evaluation_data, data.schema_type, data.schema_version, partial=True
            )

        evaluation = PatientEvaluation(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            evaluator_id=evaluator_id,
            schema_type=data.schema_type,
            schema_version=data.schema_version,
            evaluation_data=data.evaluation_data or {},  # En clair pour les calculs
            evaluation_date=data.evaluation_date or date.today(),
            status="DRAFT",
            completion_percent=0,
        )

        # Calculer complétion initiale (besoin des données EN CLAIR)
        evaluation.update_completion()

        # Extraire GIR si présent (besoin des données EN CLAIR)
        evaluation.update_gir_score()

        # Chiffrer evaluation_data APRÈS les calculs, AVANT le stockage
        if evaluation.evaluation_data:
            evaluation.evaluation_data = encrypt_evaluation_data(evaluation.evaluation_data)

        self.db.add(evaluation)
        self.db.flush()

        # Déchiffrer pour le retour API
        if evaluation.evaluation_data:
            evaluation.evaluation_data = decrypt_evaluation_data(evaluation.evaluation_data)

        return evaluation

    # ---------- Mise à jour évaluation patient ---------------

    def update(
        self,
        evaluation_id: int,
        patient_id: int,
        data: PatientEvaluationUpdate,
    ) -> PatientEvaluation:
        """
        Met à jour une évaluation (validation partielle).

        CHIFFREMENT: evaluation_data est déchiffré par get_by_id(),
        les calculs se font en clair, puis on re-chiffre avant commit.
        """
        # get_by_id() retourne evaluation_data DÉCHIFFRÉ
        evaluation = self.get_by_id(evaluation_id, patient_id)
        self._check_evaluation_editable(evaluation)

        update_data = data.model_dump(exclude_unset=True)

        # Valider les nouvelles données si fournies (EN CLAIR)
        if "evaluation_data" in update_data:
            # Fusionner avec les données existantes (les deux sont en clair)
            merged_data = {**evaluation.evaluation_data, **update_data["evaluation_data"]}
            self._validate_evaluation_data(
                merged_data, evaluation.schema_type, evaluation.schema_version, partial=True
            )
            evaluation.evaluation_data = merged_data

        # Appliquer autres champs
        for field, value in update_data.items():
            if field != "evaluation_data" and hasattr(evaluation, field):
                setattr(evaluation, field, value)

        # Mettre à jour statut si DRAFT → IN_PROGRESS
        if evaluation.status == "DRAFT" and evaluation.completion_percent > 0:
            evaluation.status = "IN_PROGRESS"

        # Recalculer complétion et GIR (besoin des données EN CLAIR)
        evaluation.update_completion()
        evaluation.update_gir_score()

        # NOUVEAU: Chiffrer AVANT le commit
        if evaluation.evaluation_data:
            evaluation.evaluation_data = encrypt_evaluation_data(evaluation.evaluation_data)

        self.db.flush()

        # NOUVEAU: Déchiffrer pour le retour API
        if evaluation.evaluation_data:
            evaluation.evaluation_data = decrypt_evaluation_data(evaluation.evaluation_data)

        return evaluation

    # ---------- Supprimer évaluation patient ---------------

    def delete(self, evaluation_id: int, patient_id: int) -> None:
        """Supprime une évaluation (uniquement si DRAFT)."""
        evaluation = self.get_by_id(evaluation_id, patient_id)

        if evaluation.status != "DRAFT":
            raise EvaluationNotEditableError("Seules les évaluations DRAFT peuvent être supprimées")

        self.db.delete(evaluation)
        self.db.flush()

    # =========================================================================
    # WORKFLOW DE VALIDATION
    # =========================================================================

    def submit(
        self,
        evaluation_id: int,
        patient_id: int,
        current_user: User,
    ) -> PatientEvaluation:
        """
        Soumet l'évaluation au workflow de validation (Phase 4 bis — B40-J1+).

        Étapes :
        1. Calcul de tous les tests cliniques (injection dans sante.blocs[].test[])
        2. Calcul du score GIR via calculator.py (décret 1997)
        3. Mise à jour du current_gir du patient
        4. Validation JSON Schema COMPLÈTE
        5. Chiffrement de evaluation_data
        6. Délégation à ValidationRequestService (B40-J2) :
             - création d'une ValidationRequest INTERNAL_REVIEW
             - transition eval.status → PENDING_INTERNAL_REVIEW
             - notification admin GCSMS
             - audit horodaté

        🔄 B40-J2 — refacto (Voie B / Option C) : la transition de statut et la
        création de la VR sont déléguées à `ValidationRequestService.submit_evaluation`
        (workflow long AGGIR_FUNDING via étape interne admin GCSMS). Les anciennes
        méthodes modèle `submit_for_validation` / `validate_medical` / `validate_department`
        ont été supprimées, l'écriture du statut passe désormais exclusivement par
        la nouvelle couche de validation (décision Session 27, point « Option C statut »).

        CHIFFREMENT: get_by_id() déchiffre, on re-chiffre AVANT la délégation
        (ValidationRequestService ne touche pas evaluation_data).

        Exceptions remontées par la délégation (à mapper côté router) :
        - `PermissionDeniedError` (validation) si l'user n'a pas VALIDATION_SUBMIT
        - `EvaluationNotSubmittableError` si statut ≠ DRAFT / IN_PROGRESS
        - `PendingValidationExistsError` si une VR pending existe déjà
        """
        # get_by_id() retourne evaluation_data DÉCHIFFRÉ
        evaluation = self.get_by_id(evaluation_id, patient_id)
        self._check_evaluation_editable(evaluation)

        # =====================================================================
        # 1) Calcul des tests cliniques (injecte les résultats dans test[])
        # =====================================================================
        sante_data = evaluation.evaluation_data.get("sante", {})
        sante_blocs = sante_data.get("blocs", [])
        aggir_data = evaluation.evaluation_data.get("aggir", {})
        aggir_variables = aggir_data.get("AggirVariable", [])

        # Nom patient pour les interprétations textuelles des tests
        usager = evaluation.evaluation_data.get("usager", {})
        nom = usager.get("nom", usager.get("Nom", ""))
        prenom = usager.get("prenom", usager.get("Prénom", ""))
        patient_display = f"{prenom} {nom}".strip() or "Le patient"

        if sante_blocs:
            updated_blocs = compute_all_sante_tests(sante_blocs, aggir_variables, patient_display)
            # Réécrire les blocs avec les test[] calculés
            if "sante" not in evaluation.evaluation_data:
                evaluation.evaluation_data["sante"] = {}
            evaluation.evaluation_data["sante"]["blocs"] = updated_blocs

        # =====================================================================
        # 2) Calcul du score GIR
        # =====================================================================
        if aggir_variables:
            gir_score = self._compute_gir_from_data(aggir_variables)
            if gir_score is not None:
                evaluation.gir_score = gir_score
                # Stocker aussi dans evaluation_data pour export JSON
                if "aggir" not in evaluation.evaluation_data:
                    evaluation.evaluation_data["aggir"] = {}
                evaluation.evaluation_data["aggir"]["GIR"] = gir_score

        # =====================================================================
        # 3) Mise à jour du GIR courant du patient
        # =====================================================================
        if evaluation.gir_score:
            patient = self._verify_patient_access(patient_id)
            patient.current_gir = evaluation.gir_score

        # =====================================================================
        # 4) Validation JSON Schema COMPLÈTE (EN CLAIR)
        # =====================================================================
        # Schéma evaluation_v1.json aligné avec buildEvaluationData() — v5.9+
        # (5 écarts corrigés : poaAutonomie, blocSocial enum, seuilVital,
        #  materiels wrapper, _wizard_meta — session 16/03/2026)
        self._validate_evaluation_data(
            evaluation.evaluation_data,
            evaluation.schema_type,
            evaluation.schema_version,
            partial=False,
        )

        # =====================================================================
        # 5) Chiffrement AVANT délégation
        # =====================================================================
        # ValidationRequestService.submit_evaluation ne touche pas evaluation_data ;
        # on chiffre maintenant pour que l'éval soit prête à être committée à la
        # fin de la requête HTTP (commit délégué à get_db, convention #97).
        if evaluation.evaluation_data:
            evaluation.evaluation_data = encrypt_evaluation_data(evaluation.evaluation_data)

        # =====================================================================
        # 6) Délégation à ValidationRequestService (B40-J2)
        # =====================================================================
        # Imports locaux pour éviter tout risque de cycle (le module validation
        # importe `PatientEvaluation` modèle mais pas `PatientEvaluationService`).
        from app.api.v1.validation.schemas import ValidationSubmitRequest
        from app.api.v1.validation.services import ValidationRequestService

        validation_service = ValidationRequestService(self.db, self.tenant_id)
        validation_service.submit_evaluation(
            evaluation_id=evaluation_id,
            payload=ValidationSubmitRequest(notes=""),
            submitted_by=current_user,
        )
        # submit_evaluation a déjà :
        # - écrit evaluation.status = PENDING_INTERNAL_REVIEW
        # - créé la VR INTERNAL_REVIEW
        # - notifié les admin GCSMS
        # - posé l'audit horodaté
        # - flushé deux fois (vr.id requis pour audit + notification)

        # =====================================================================
        # 7) Déchiffrer pour le retour API
        # =====================================================================
        if evaluation.evaluation_data:
            evaluation.evaluation_data = decrypt_evaluation_data(evaluation.evaluation_data)

        return evaluation

    # =========================================================================
    # GESTION DES SESSIONS
    # =========================================================================

    def get_sessions(self, evaluation_id: int, patient_id: int) -> list[EvaluationSession]:
        """Liste les sessions d'une évaluation."""
        evaluation = self.get_by_id(evaluation_id, patient_id)
        return list(evaluation.sessions)

    def start_session(
        self,
        evaluation_id: int,
        patient_id: int,
        user_id: int,
        device_info: str | None = None,
    ) -> EvaluationSession:
        """
        Démarre une nouvelle session de saisie.

        CHIFFREMENT: Re-chiffrer l'évaluation avant commit pour éviter
        que SQLAlchemy persiste les données déchiffrées par get_by_id().
        """
        evaluation = self.get_by_id(evaluation_id, patient_id)
        self._check_evaluation_editable(evaluation)

        # Auto-fermer une session orpheline (rechargement page, crash navigateur, etc.)
        # Avant ce fix, une session non fermée proprement bloquait indéfiniment
        # la création de nouvelles sessions (409 en boucle).
        if evaluation.current_session:
            stale_id = evaluation.current_session.id
            evaluation.current_session.end_session()
            logger.info(f"Auto-closed stale session {stale_id} for evaluation {evaluation_id}")

        session = EvaluationSession(
            tenant_id=self.tenant_id,
            evaluation_id=evaluation_id,
            user_id=user_id,
            device_info=device_info,
            status="IN_PROGRESS",
        )

        # NOUVEAU: Re-chiffrer l'évaluation avant commit
        if evaluation.evaluation_data:
            evaluation.evaluation_data = encrypt_evaluation_data(evaluation.evaluation_data)

        self.db.add(session)
        self.db.flush()
        return session

    def end_session(
        self,
        session_id: int,
        evaluation_id: int,
        patient_id: int,
        variables_recorded: list[str] | None = None,
        notes: str | None = None,
    ) -> EvaluationSession:
        """
        Termine une session de saisie.

        CHIFFREMENT: Re-chiffrer l'évaluation avant commit.
        """
        evaluation = self.get_by_id(evaluation_id, patient_id)

        session = self.db.execute(
            select(EvaluationSession).where(
                EvaluationSession.id == session_id,
                EvaluationSession.evaluation_id == evaluation_id,
                EvaluationSession.tenant_id == self.tenant_id,
            )
        ).scalar_one_or_none()

        if not session:
            raise SessionNotFoundError(f"Session {session_id} non trouvée")

        session.end_session()

        if variables_recorded:
            session.variables_recorded = ",".join(variables_recorded)
        if notes:
            session.notes = notes

        # NOUVEAU: Re-chiffrer l'évaluation avant commit
        if evaluation.evaluation_data:
            evaluation.evaluation_data = encrypt_evaluation_data(evaluation.evaluation_data)

        self.db.flush()
        return session

    # =========================================================================
    # SYNCHRONISATION OFFLINE
    # =========================================================================

    def sync_offline_data(
        self,
        evaluation_id: int,
        patient_id: int,
        evaluation_data: dict[str, Any],
        local_session_id: str | None = None,
    ) -> PatientEvaluation:
        """
        Synchronise les données saisies hors-ligne.
        Fusionne intelligemment les données locales avec les données serveur.

        CHIFFREMENT: Fusion en clair, chiffrement avant commit,
        déchiffrement pour le retour.
        """
        # get_by_id() retourne evaluation_data DÉCHIFFRÉ
        evaluation = self.get_by_id(evaluation_id, patient_id)
        self._check_evaluation_editable(evaluation)

        # Fusionner les données (last-write-wins au niveau des champs)
        # Les deux sont en clair : evaluation.evaluation_data et evaluation_data (paramètre)
        merged = {**evaluation.evaluation_data}

        for key, value in evaluation_data.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                # Fusion récursive pour les objets
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value

        # Valider les données fusionnées (EN CLAIR)
        self._validate_evaluation_data(
            merged, evaluation.schema_type, evaluation.schema_version, partial=True
        )

        evaluation.evaluation_data = merged
        evaluation.update_completion()
        evaluation.update_gir_score()

        # NOUVEAU: Chiffrer avant commit
        if evaluation.evaluation_data:
            evaluation.evaluation_data = encrypt_evaluation_data(evaluation.evaluation_data)

        self.db.flush()

        # NOUVEAU: Déchiffrer pour le retour API
        if evaluation.evaluation_data:
            evaluation.evaluation_data = decrypt_evaluation_data(evaluation.evaluation_data)

        return evaluation


# =============================================================================
# PATIENT THRESHOLD SERVICE (SEUILS PERSONNALISÉS)
# =============================================================================


class PatientThresholdService:
    """
    Service pour la gestion des seuils de constantes vitales.

    Chaque patient peut avoir des seuils personnalisés pour chaque
    type de constante (tension, pouls, température, etc.).
    """

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    def _verify_patient_access(self, patient_id: int) -> Patient:
        """Vérifie que le patient appartient au tenant."""
        patient = self.db.execute(
            select(Patient).where(Patient.id == patient_id, Patient.tenant_id == self.tenant_id)
        ).scalar_one_or_none()

        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        return patient

    def get_all_for_patient(self, patient_id: int) -> list[PatientThreshold]:
        """Liste tous les seuils d'un patient."""
        self._verify_patient_access(patient_id)

        query = (
            select(PatientThreshold)
            .where(
                PatientThreshold.patient_id == patient_id,
                PatientThreshold.tenant_id == self.tenant_id,
            )
            .order_by(PatientThreshold.vital_type)
        )

        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, threshold_id: int, patient_id: int) -> PatientThreshold:
        """Récupère un seuil par son ID."""
        self._verify_patient_access(patient_id)

        threshold = self.db.execute(
            select(PatientThreshold).where(
                PatientThreshold.id == threshold_id,
                PatientThreshold.patient_id == patient_id,
                PatientThreshold.tenant_id == self.tenant_id,
            )
        ).scalar_one_or_none()

        if not threshold:
            raise ThresholdNotFoundError(f"Seuil {threshold_id} non trouvé")
        return threshold

    def get_by_vital_type(self, patient_id: int, vital_type: str) -> PatientThreshold | None:
        """Récupère le seuil d'un patient pour un type de constante."""
        self._verify_patient_access(patient_id)

        return self.db.execute(
            select(PatientThreshold).where(
                PatientThreshold.patient_id == patient_id,
                PatientThreshold.vital_type == vital_type,
                PatientThreshold.tenant_id == self.tenant_id,
            )
        ).scalar_one_or_none()

    def create(self, patient_id: int, data: PatientThresholdCreate) -> PatientThreshold:
        """Crée un nouveau seuil."""
        self._verify_patient_access(patient_id)

        # Vérifier l'unicité patient + vital_type
        existing = self.get_by_vital_type(patient_id, data.vital_type)
        if existing:
            raise DuplicateThresholdError(
                f"Un seuil existe déjà pour {data.vital_type} (ID: {existing.id})"
            )

        threshold = PatientThreshold(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            vital_type=data.vital_type,
            min_value=data.min_value,
            max_value=data.max_value,
            unit=data.unit,
            surveillance_frequency=data.surveillance_frequency,
        )

        self.db.add(threshold)
        self.db.flush()
        return threshold

    def update(
        self,
        threshold_id: int,
        patient_id: int,
        data: PatientThresholdUpdate,
    ) -> PatientThreshold:
        """Met à jour un seuil."""
        threshold = self.get_by_id(threshold_id, patient_id)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(threshold, field, value)

        self.db.flush()
        return threshold

    def delete(self, threshold_id: int, patient_id: int) -> None:
        """Supprime un seuil."""
        threshold = self.get_by_id(threshold_id, patient_id)
        self.db.delete(threshold)
        self.db.flush()


# =============================================================================
# PATIENT VITALS SERVICE (CONSTANTES VITALES)
# =============================================================================


class PatientVitalsService:
    """
    Service pour la gestion des mesures de constantes vitales.

    Fonctionnalités:
    - Enregistrement des mesures (manuelles ou automatiques)
    - Vérification automatique des seuils
    - Historique et statistiques
    """

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self._threshold_service = PatientThresholdService(db, tenant_id)

    def _verify_patient_access(self, patient_id: int) -> Patient:
        """Vérifie que le patient appartient au tenant."""
        patient = self.db.execute(
            select(Patient).where(Patient.id == patient_id, Patient.tenant_id == self.tenant_id)
        ).scalar_one_or_none()

        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        return patient

    def get_all_for_patient(
        self,
        patient_id: int,
        filters: VitalsFilters | None = None,
        page: int = 1,
        size: int = 50,
    ) -> tuple[list[PatientVitals], int]:
        """Liste les mesures d'un patient avec filtres et pagination."""
        self._verify_patient_access(patient_id)

        query = select(PatientVitals).where(
            PatientVitals.patient_id == patient_id, PatientVitals.tenant_id == self.tenant_id
        )

        # Appliquer les filtres
        if filters:
            if filters.vital_type:
                query = query.where(PatientVitals.vital_type == filters.vital_type)
            if filters.status:
                query = query.where(PatientVitals.status == filters.status)
            if filters.date_from:
                query = query.where(PatientVitals.measured_at >= filters.date_from)
            if filters.date_to:
                query = query.where(PatientVitals.measured_at <= filters.date_to)

        # Compter le total
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar()

        # Tri et pagination
        query = query.order_by(PatientVitals.measured_at.desc())
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        vitals = self.db.execute(query).scalars().all()
        return list(vitals), total

    def get_by_id(self, vital_id: int, patient_id: int) -> PatientVitals:
        """Récupère une mesure par son ID."""
        self._verify_patient_access(patient_id)

        vital = self.db.execute(
            select(PatientVitals).where(
                PatientVitals.id == vital_id,
                PatientVitals.patient_id == patient_id,
                PatientVitals.tenant_id == self.tenant_id,
            )
        ).scalar_one_or_none()

        if not vital:
            raise VitalsNotFoundError(f"Mesure {vital_id} non trouvée")
        return vital

    def get_latest(self, patient_id: int, vital_type: str) -> PatientVitals | None:
        """Récupère la dernière mesure d'un type pour un patient."""
        self._verify_patient_access(patient_id)

        return self.db.execute(
            select(PatientVitals)
            .where(
                PatientVitals.patient_id == patient_id,
                PatientVitals.vital_type == vital_type,
                PatientVitals.tenant_id == self.tenant_id,
            )
            .order_by(PatientVitals.measured_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    def create(
        self,
        patient_id: int,
        data: PatientVitalsCreate,
        recorded_by: int | None = None,
    ) -> PatientVitals:
        """
        Enregistre une nouvelle mesure.

        Vérifie automatiquement les seuils et définit le statut.
        """
        self._verify_patient_access(patient_id)

        # Récupérer le seuil pour ce type de constante
        threshold = self._threshold_service.get_by_vital_type(patient_id, data.vital_type)

        # Déterminer le statut
        status = None
        if threshold:
            status = threshold.check_value(float(data.value)).value

        vital = PatientVitals(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            vital_type=data.vital_type,
            value=data.value,
            unit=data.unit,
            status=status,
            source=data.source,
            device_id=data.device_id,
            measured_at=data.measured_at or datetime.now(UTC),
            recorded_by=recorded_by,
            notes=data.notes,
        )

        self.db.add(vital)
        self.db.flush()
        return vital

    def delete(self, vital_id: int, patient_id: int) -> None:
        """Supprime une mesure."""
        vital = self.get_by_id(vital_id, patient_id)
        self.db.delete(vital)
        self.db.flush()


# =============================================================================
# PATIENT DEVICE SERVICE (DEVICES CONNECTÉS)
# =============================================================================


class PatientDeviceService:
    """
    Service pour la gestion des devices connectés des patients.

    Permet l'enregistrement et la gestion des appareils qui
    transmettent automatiquement des mesures.
    """

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    def _verify_patient_access(self, patient_id: int) -> Patient:
        """Vérifie que le patient appartient au tenant."""
        patient = self.db.execute(
            select(Patient).where(Patient.id == patient_id, Patient.tenant_id == self.tenant_id)
        ).scalar_one_or_none()

        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        return patient

    def get_all_for_patient(self, patient_id: int, active_only: bool = True) -> list[PatientDevice]:
        """Liste les devices d'un patient."""
        self._verify_patient_access(patient_id)

        query = select(PatientDevice).where(
            PatientDevice.patient_id == patient_id, PatientDevice.tenant_id == self.tenant_id
        )

        if active_only:
            query = query.where(PatientDevice.is_active == True)  # noqa: E712

        query = query.order_by(PatientDevice.device_name)
        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, device_id: int, patient_id: int) -> PatientDevice:
        """Récupère un device par son ID."""
        self._verify_patient_access(patient_id)

        device = self.db.execute(
            select(PatientDevice).where(
                PatientDevice.id == device_id,
                PatientDevice.patient_id == patient_id,
                PatientDevice.tenant_id == self.tenant_id,
            )
        ).scalar_one_or_none()

        if not device:
            raise DeviceNotFoundError(f"Device {device_id} non trouvé")
        return device

    def create(self, patient_id: int, data: PatientDeviceCreate) -> PatientDevice:
        """Enregistre un nouveau device."""
        self._verify_patient_access(patient_id)

        # Vérifier l'unicité device_type + device_identifier
        existing = self.db.execute(
            select(PatientDevice).where(
                PatientDevice.device_type == data.device_type,
                PatientDevice.device_identifier == data.device_identifier,
            )
        ).scalar_one_or_none()

        if existing:
            raise DuplicateDeviceError(f"Ce device est déjà enregistré (ID: {existing.id})")

        device = PatientDevice(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            device_type=data.device_type,
            device_identifier=data.device_identifier,
            device_name=data.device_name,
            is_active=True,
        )

        self.db.add(device)
        self.db.flush()
        return device

    def update(
        self,
        device_id: int,
        patient_id: int,
        data: PatientDeviceUpdate,
    ) -> PatientDevice:
        """Met à jour un device."""
        device = self.get_by_id(device_id, patient_id)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(device, field, value)

        self.db.flush()
        return device

    def deactivate(self, device_id: int, patient_id: int) -> PatientDevice:
        """Désactive un device."""
        device = self.get_by_id(device_id, patient_id)
        device.deactivate()
        self.db.flush()
        return device

    def update_sync_time(self, device_id: int, patient_id: int) -> PatientDevice:
        """Met à jour le timestamp de dernière synchronisation."""
        device = self.get_by_id(device_id, patient_id)
        device.update_sync_time()
        self.db.flush()
        return device


# =============================================================================
# PATIENT DOCUMENT SERVICE (DOCUMENTS GÉNÉRÉS)
# =============================================================================


class PatientDocumentService:
    """
    Service pour la gestion des documents générés pour les patients.

    Gère les métadonnées des documents PPA, PPCS, Recommandations
    générés par LLM/RAG à partir des évaluations.
    """

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    def _verify_patient_access(self, patient_id: int) -> Patient:
        """Vérifie que le patient appartient au tenant."""
        patient = self.db.execute(
            select(Patient).where(Patient.id == patient_id, Patient.tenant_id == self.tenant_id)
        ).scalar_one_or_none()

        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        return patient

    def get_all_for_patient(
        self,
        patient_id: int,
        document_type: str | None = None,
    ) -> list[PatientDocument]:
        """Liste les documents d'un patient."""
        self._verify_patient_access(patient_id)

        query = select(PatientDocument).where(
            PatientDocument.patient_id == patient_id, PatientDocument.tenant_id == self.tenant_id
        )

        if document_type:
            query = query.where(PatientDocument.document_type == document_type)

        query = query.order_by(PatientDocument.generated_at.desc())
        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, document_id: int, patient_id: int) -> PatientDocument:
        """Récupère un document par son ID."""
        self._verify_patient_access(patient_id)

        document = self.db.execute(
            select(PatientDocument).where(
                PatientDocument.id == document_id,
                PatientDocument.patient_id == patient_id,
                PatientDocument.tenant_id == self.tenant_id,
            )
        ).scalar_one_or_none()

        if not document:
            raise DocumentNotFoundError(f"Document {document_id} non trouvé")
        return document

    def create(
        self,
        patient_id: int,
        data: PatientDocumentCreate,
        generated_by: int,
    ) -> PatientDocument:
        """
        Crée un enregistrement de document.

        Note: Le fichier physique doit être généré et stocké séparément.
        """
        self._verify_patient_access(patient_id)

        # Vérifier l'évaluation source si fournie
        if data.source_evaluation_id:
            evaluation = self.db.execute(
                select(PatientEvaluation).where(
                    PatientEvaluation.id == data.source_evaluation_id,
                    PatientEvaluation.patient_id == patient_id,
                    PatientEvaluation.tenant_id == self.tenant_id,
                )
            ).scalar_one_or_none()

            if not evaluation:
                raise EvaluationNotFoundError(
                    f"Évaluation source {data.source_evaluation_id} non trouvée"
                )

        document = PatientDocument(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            document_type=data.document_type,
            title=data.title,
            description=data.description,
            source_evaluation_id=data.source_evaluation_id,
            generation_prompt=data.generation_prompt,
            generation_context=data.generation_context,
            file_path=data.file_path,
            file_format=data.file_format,
            file_size_bytes=data.file_size_bytes,
            file_hash=data.file_hash,
            generated_by=generated_by,
        )

        self.db.add(document)
        self.db.flush()
        return document

    def delete(self, document_id: int, patient_id: int) -> None:
        """
        Supprime un document.

        Note: Le fichier physique doit être supprimé séparément.
        """
        document = self.get_by_id(document_id, patient_id)
        self.db.delete(document)
        self.db.flush()
