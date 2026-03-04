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
from datetime import datetime, timezone, date, timedelta
from typing import Optional, List, Tuple, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    # Ces imports ne sont utilisés QUE pour les type hints
    # Ils ne sont pas exécutés à runtime → pas d'import circulaire
    pass

from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session

from app.models.patient.patient import Patient
from app.models.patient.patient_access import PatientAccess
from app.models.patient.patient_evaluation import PatientEvaluation
from app.models.patient.evaluation_session import EvaluationSession
from app.models.patient.patient_vitals import PatientThreshold, PatientVitals, PatientDevice
from app.models.patient.patient_document import PatientDocument
from app.models.user.user import User
from app.models.organization.entity import Entity

from app.api.v1.patient.schemas import (
    PatientCreate, PatientUpdate, PatientFilters,
    PatientAccessCreate,
    PatientEvaluationCreate, PatientEvaluationUpdate,
    PatientThresholdCreate, PatientThresholdUpdate,
    PatientVitalsCreate, VitalsFilters,
    PatientDeviceCreate, PatientDeviceUpdate,
    PatientDocumentCreate,
    EvaluationSessionCreate, EvaluationSessionUpdate,
)

from app.services.validation.schema_validator import (
    get_schema_validator,
    SchemaValidationError,
    SchemaNotFoundError,
)

# Import du service de chiffrement
from app.services.encryption import (
    patient_encryptor,
    evaluation_encryptor,
    encrypt_evaluation_data,
    decrypt_evaluation_data,
)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class PatientNotFoundError(Exception):
    """Patient non trouvé."""
    pass


class EntityNotFoundError(Exception):
    """Entité non trouvée."""
    pass


class UserNotFoundError(Exception):
    """Utilisateur non trouvé."""
    pass


class EvaluationNotFoundError(Exception):
    """Évaluation non trouvée."""
    pass


class SessionNotFoundError(Exception):
    """Session d'évaluation non trouvée."""
    pass


class ThresholdNotFoundError(Exception):
    """Seuil non trouvé."""
    pass


class VitalsNotFoundError(Exception):
    """Mesure non trouvée."""
    pass


class DeviceNotFoundError(Exception):
    """Device non trouvé."""
    pass


class DocumentNotFoundError(Exception):
    """Document non trouvé."""
    pass


class AccessNotFoundError(Exception):
    """Accès non trouvé."""
    pass


class DuplicateThresholdError(Exception):
    """Seuil déjà défini pour ce type de constante."""
    pass


class DuplicateDeviceError(Exception):
    """Device déjà enregistré."""
    pass


class AccessDeniedError(Exception):
    """Accès refusé au dossier patient."""
    pass


class EvaluationAlreadyValidatedError(Exception):
    """L'évaluation est déjà validée."""
    pass


class EvaluationInProgressError(Exception):
    """Une évaluation est déjà en cours pour ce patient."""
    pass


class EvaluationExpiredError(Exception):
    """L'évaluation a expiré."""
    pass


class EvaluationNotEditableError(Exception):
    """L'évaluation ne peut plus être modifiée (validée ou expirée)."""
    pass


class InvalidEvaluationDataError(Exception):
    """Données d'évaluation invalides selon le JSON Schema."""
    def __init__(self, message: str, errors: list = None):
        self.message = message
        self.errors = errors or []
        super().__init__(message)


class DuplicateNIRError(Exception):
    """Un patient avec ce NIR existe déjà."""
    pass


class SessionAlreadyActiveError(Exception):
    """Une session est déjà active pour cette évaluation."""
    pass


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

    def _decrypt_patient(self, patient: Patient) -> Dict[str, Any]:
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
        return {
            "id": patient.id,
            "first_name": decrypted.get("first_name"),
            "last_name": decrypted.get("last_name"),
            "birth_date": decrypted.get("birth_date"),
            "nir": decrypted.get("nir"),
            "ins": decrypted.get("ins"),
            "address": decrypted.get("address"),
            "phone": decrypted.get("phone"),
            "email": decrypted.get("email"),
            "status": patient.status,
            "entity_id": patient.entity_id,
            "medecin_traitant_id": patient.medecin_traitant_id,
            "latitude": patient.latitude,
            "longitude": patient.longitude,
            "current_gir": patient.current_gir,
            "created_at": patient.created_at,
            "updated_at": patient.updated_at,
        }

    def _decrypt_patient_summary(self, patient: Patient) -> Dict[str, Any]:
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
            filters: Optional[PatientFilters] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
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
        """Récupère un patient par son ID.
        """
        query = self._base_query().where(Patient.id == patient_id)
        patient = self.db.execute(query).scalar_one_or_none()

        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")

        return patient

    def get_by_id_decrypted(self, patient_id: int) -> Dict[str, Any]:
        """Récupère un patient déchiffré par son ID."""
        patient = self.get_by_id(patient_id)
        return self._decrypt_patient(patient)

    def create(self, data: PatientCreate, created_by: int) -> Patient:
        """Crée un nouveau patient avec chiffrement."""
        # Vérifier l'entité
        entity = self.db.execute(
            select(Entity).where(
                Entity.id == data.entity_id,
                Entity.tenant_id == self.tenant_id
            )
        ).scalar_one_or_none()

        if not entity:
            raise EntityNotFoundError(f"Entité {data.entity_id} non trouvée")

        # Vérifier l'unicité du NIR
        if data.nir:
            existing = self.search_by_nir(data.nir)
            if existing:
                raise DuplicateNIRError(
                    f"Un patient avec ce NIR existe déjà (ID: {existing.id})"
                )

        # Préparer les données à chiffrer
        plain_data = {
            "first_name": data.first_name,
            "last_name": data.last_name,
            "birth_date": data.birth_date.isoformat() if data.birth_date else None,
            "nir": data.nir,
            "ins": data.ins,
            "address": data.address,
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
            **encrypted
        )

        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def update(
            self,
            patient_id: int,
            data: PatientUpdate,
            updated_by: Optional[int] = None,
    ) -> Patient:
        """Met à jour un patient."""
        patient = self.get_by_id(patient_id)
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return patient

        # Vérifier médecin traitant si modifié
        if "medecin_traitant_id" in update_data and update_data["medecin_traitant_id"]:
            medecin = self.db.execute(
                select(User).where(
                    User.id == update_data["medecin_traitant_id"],
                    User.tenant_id == self.tenant_id
                )
            ).scalar_one_or_none()

            if not medecin:
                raise UserNotFoundError(f"Médecin {update_data['medecin_traitant_id']} non trouvé")

        # Vérifier l'unicité du NIR si modifié
        if "nir" in update_data and update_data["nir"]:
            existing = self.search_by_nir(update_data["nir"])
            if existing and existing.id != patient_id:
                raise DuplicateNIRError(
                    f"Un patient avec ce NIR existe déjà (ID: {existing.id})"
                )

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
            encrypted_update = patient_encryptor.encrypt_for_db(
                fields_to_encrypt, self.tenant_id
            )
            # Appliquer les valeurs chiffrées
            for db_field, value in encrypted_update.items():
                setattr(patient, db_field, value)

        # Appliquer les champs non chiffrés
        for field, value in other_fields.items():
            setattr(patient, field, value)

        # Mettre à jour updated_by si fourni
        if updated_by:
            patient.updated_by = updated_by

        self.db.commit()
        self.db.refresh(patient)
        return patient

    def delete(self, patient_id: int) -> None:
        """Archive un patient (soft delete)."""
        patient = self.get_by_id(patient_id)
        patient.status = "ARCHIVED"
        self.db.commit()

    # =========================================================================
    # MÉTHODES DE RECHERCHE (BLIND INDEX)
    # =========================================================================

    def search_by_nir(self, nir: str) -> Optional[Patient]:
        """Recherche un patient par son NIR."""
        blind = patient_encryptor.search_by_nir(nir, self.tenant_id)
        query = self._base_query().where(Patient.nir_blind == blind)
        return self.db.execute(query).scalar_one_or_none()

    def search_by_ins(self, ins: str) -> Optional[Patient]:
        """Recherche un patient par son INS."""
        blind = patient_encryptor.search_by_ins(ins, self.tenant_id)
        query = self._base_query().where(Patient.ins_blind == blind)
        return self.db.execute(query).scalar_one_or_none()

    def search_by_name(
        self,
        last_name: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> List[Patient]:
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
        nir: Optional[str] = None,
        ins: Optional[str] = None,
        exclude_patient_id: Optional[int] = None,
    ) -> Optional[Patient]:
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
            select(Patient).where(
                Patient.id == patient_id,
                Patient.tenant_id == self.tenant_id
            )
        ).scalar_one_or_none()

        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        return patient

    def get_all_for_patient(
            self,
            patient_id: int,
            active_only: bool = True,
    ) -> List[PatientAccess]:
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
            select(User).where(
                User.id == user_id,
                User.tenant_id == self.tenant_id
            )
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
        self.db.commit()
        self.db.refresh(access)
        return access

    def revoke_access(self, access_id: int, patient_id: int, revoked_by: int) -> PatientAccess:
        """Révoque un accès."""
        access = self.get_by_id(access_id, patient_id)
        access.revoke(revoked_by)
        self.db.commit()
        self.db.refresh(access)
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
            select(Patient).where(
                Patient.id == patient_id,
                Patient.tenant_id == self.tenant_id
            )
        ).scalar_one_or_none()

        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        return patient

    def _check_evaluation_editable(self, evaluation: PatientEvaluation) -> None:
        """Vérifie que l'évaluation peut être modifiée."""
        if evaluation.status == "VALIDATED":
            raise EvaluationAlreadyValidatedError(
                f"L'évaluation {evaluation.id} est déjà validée"
            )
        if evaluation.is_expired:
            raise EvaluationExpiredError(
                f"L'évaluation {evaluation.id} a expiré"
            )
        if evaluation.status not in ["DRAFT", "IN_PROGRESS"]:
            raise EvaluationNotEditableError(
                f"L'évaluation {evaluation.id} ne peut plus être modifiée (statut: {evaluation.status})"
            )

    def _validate_evaluation_data(
            self,
            data: Dict[str, Any],
            schema_type: str,
            schema_version: str,
            partial: bool = True
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
            validator = get_schema_validator(schema_type, schema_version)
            if partial:
                validator.validate_partial(data)
            else:
                validator.validate_complete(data)
        except SchemaNotFoundError as e:
            raise InvalidEvaluationDataError(f"Schéma inconnu: {e}")
        except SchemaValidationError as e:
            raise InvalidEvaluationDataError(
                message=f"Données invalides: {e.message}",
                errors=e.errors
            )

    # =========================================================================
    # CRUD ÉVALUATIONS
    # =========================================================================

    # ---------- Lire évaluations d'un patient ---------------
    def get_all_for_patient(
            self,
            patient_id: int,
            include_expired: bool = False,
    ) -> List[PatientEvaluation]:
        """
        Liste les évaluations d'un patient.

        CHIFFREMENT: evaluation_data est déchiffré pour chaque évaluation.
        """
        self._verify_patient_access(patient_id)

        query = select(PatientEvaluation).where(
            PatientEvaluation.patient_id == patient_id,
            PatientEvaluation.tenant_id == self.tenant_id
        )

        if not include_expired:
            query = query.where(PatientEvaluation.status != "EXPIRED")

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
                PatientEvaluation.tenant_id == self.tenant_id
            )
        ).scalar_one_or_none()

        if not evaluation:
            raise EvaluationNotFoundError(f"Évaluation {evaluation_id} non trouvée")

        # Vérifier expiration
        evaluation.check_expiration()

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
                PatientEvaluation.status.in_(["DRAFT", "IN_PROGRESS"])
            )
        ).scalar_one_or_none()

        if existing:
            raise EvaluationInProgressError(
                f"Une évaluation est déjà en cours (ID: {existing.id})"
            )

        # Validation partielle des données (EN CLAIR - avant chiffrement)
        if data.evaluation_data:
            self._validate_evaluation_data(
                data.evaluation_data,
                data.schema_type,
                data.schema_version,
                partial=True
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

        # Définir expiration J+7
        evaluation.set_expiration(days=7)

        # Calculer complétion initiale (besoin des données EN CLAIR)
        evaluation.update_completion()

        # Extraire GIR si présent (besoin des données EN CLAIR)
        evaluation.update_gir_score()

        # Chiffrer evaluation_data APRÈS les calculs, AVANT le stockage
        if evaluation.evaluation_data:
            evaluation.evaluation_data = encrypt_evaluation_data(evaluation.evaluation_data)

        self.db.add(evaluation)
        self.db.commit()
        self.db.refresh(evaluation)

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
                merged_data,
                evaluation.schema_type,
                evaluation.schema_version,
                partial=True
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

        self.db.commit()
        self.db.refresh(evaluation)

        # NOUVEAU: Déchiffrer pour le retour API
        if evaluation.evaluation_data:
            evaluation.evaluation_data = decrypt_evaluation_data(evaluation.evaluation_data)

        return evaluation

    # ---------- Supprimer évaluation patient ---------------

    def delete(self, evaluation_id: int, patient_id: int) -> None:
        """Supprime une évaluation (uniquement si DRAFT)."""
        evaluation = self.get_by_id(evaluation_id, patient_id)

        if evaluation.status != "DRAFT":
            raise EvaluationNotEditableError(
                f"Seules les évaluations DRAFT peuvent être supprimées"
            )

        self.db.delete(evaluation)
        self.db.commit()

    # =========================================================================
    # WORKFLOW DE VALIDATION
    # =========================================================================

    def submit(self, evaluation_id: int, patient_id: int) -> PatientEvaluation:
        """
        Soumet l'évaluation pour validation (validation JSON Schema complète).

        CHIFFREMENT: get_by_id() déchiffre, on re-chiffre avant commit.
        """
        # get_by_id() retourne evaluation_data DÉCHIFFRÉ
        evaluation = self.get_by_id(evaluation_id, patient_id)
        self._check_evaluation_editable(evaluation)

        # Validation COMPLÈTE des données (EN CLAIR)
        self._validate_evaluation_data(
            evaluation.evaluation_data,
            evaluation.schema_type,
            evaluation.schema_version,
            partial=False  # Validation stricte
        )

        evaluation.submit_for_validation()

        # NOUVEAU: Re-chiffrer avant commit
        if evaluation.evaluation_data:
            evaluation.evaluation_data = encrypt_evaluation_data(evaluation.evaluation_data)

        self.db.commit()
        self.db.refresh(evaluation)

        # NOUVEAU: Déchiffrer pour le retour API
        if evaluation.evaluation_data:
            evaluation.evaluation_data = decrypt_evaluation_data(evaluation.evaluation_data)

        return evaluation

    def validate_medical(
            self,
            evaluation_id: int,
            patient_id: int,
            validator_id: int,
    ) -> PatientEvaluation:
        """
        Validation par le médecin coordonnateur.

        CHIFFREMENT: get_by_id() déchiffre, on re-chiffre avant commit.
        """
        # get_by_id() retourne evaluation_data DÉCHIFFRÉ
        evaluation = self.get_by_id(evaluation_id, patient_id)

        if evaluation.status != "PENDING_MEDICAL":
            raise EvaluationNotEditableError(
                f"L'évaluation doit être en attente de validation médicale"
            )

        evaluation.validate_medical(validator_id)

        # NOUVEAU: Re-chiffrer avant commit
        if evaluation.evaluation_data:
            evaluation.evaluation_data = encrypt_evaluation_data(evaluation.evaluation_data)

        self.db.commit()
        self.db.refresh(evaluation)

        # NOUVEAU: Déchiffrer pour le retour API
        if evaluation.evaluation_data:
            evaluation.evaluation_data = decrypt_evaluation_data(evaluation.evaluation_data)

        return evaluation

    def validate_department(
            self,
            evaluation_id: int,
            patient_id: int,
            validator_name: str,
            validator_reference: str,
    ) -> PatientEvaluation:
        """
        Validation par le Conseil Départemental.

        CHIFFREMENT: get_by_id() déchiffre, on re-chiffre avant commit.
        """
        # get_by_id() retourne evaluation_data DÉCHIFFRÉ
        evaluation = self.get_by_id(evaluation_id, patient_id)

        if evaluation.status != "PENDING_DEPARTMENT":
            raise EvaluationNotEditableError(
                f"L'évaluation doit être en attente de validation CD"
            )

        evaluation.validate_department(validator_name, validator_reference)

        # Mettre à jour le GIR du patient
        patient = self._verify_patient_access(patient_id)
        if evaluation.gir_score:
            patient.current_gir = evaluation.gir_score

        # NOUVEAU: Re-chiffrer avant commit
        if evaluation.evaluation_data:
            evaluation.evaluation_data = encrypt_evaluation_data(evaluation.evaluation_data)

        self.db.commit()
        self.db.refresh(evaluation)

        # NOUVEAU: Déchiffrer pour le retour API
        if evaluation.evaluation_data:
            evaluation.evaluation_data = decrypt_evaluation_data(evaluation.evaluation_data)

        return evaluation

    # =========================================================================
    # GESTION DES SESSIONS
    # =========================================================================

    def get_sessions(self, evaluation_id: int, patient_id: int) -> List[EvaluationSession]:
        """Liste les sessions d'une évaluation."""
        evaluation = self.get_by_id(evaluation_id, patient_id)
        return list(evaluation.sessions)

    def start_session(
            self,
            evaluation_id: int,
            patient_id: int,
            user_id: int,
            device_info: Optional[str] = None,
    ) -> EvaluationSession:
        """
        Démarre une nouvelle session de saisie.

        CHIFFREMENT: Re-chiffrer l'évaluation avant commit pour éviter
        que SQLAlchemy persiste les données déchiffrées par get_by_id().
        """
        evaluation = self.get_by_id(evaluation_id, patient_id)
        self._check_evaluation_editable(evaluation)

        # Vérifier qu'il n'y a pas de session active
        if evaluation.current_session:
            raise SessionAlreadyActiveError(
                f"Une session est déjà active (ID: {evaluation.current_session.id})"
            )

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
        self.db.commit()
        self.db.refresh(session)
        return session

    def end_session(
            self,
            session_id: int,
            evaluation_id: int,
            patient_id: int,
            variables_recorded: Optional[List[str]] = None,
            notes: Optional[str] = None,
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
                EvaluationSession.tenant_id == self.tenant_id
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

        self.db.commit()
        self.db.refresh(session)
        return session

    # =========================================================================
    # SYNCHRONISATION OFFLINE
    # =========================================================================

    def sync_offline_data(
            self,
            evaluation_id: int,
            patient_id: int,
            evaluation_data: Dict[str, Any],
            local_session_id: Optional[str] = None,
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
            merged,
            evaluation.schema_type,
            evaluation.schema_version,
            partial=True
        )

        evaluation.evaluation_data = merged
        evaluation.update_completion()
        evaluation.update_gir_score()

        # NOUVEAU: Chiffrer avant commit
        if evaluation.evaluation_data:
            evaluation.evaluation_data = encrypt_evaluation_data(evaluation.evaluation_data)

        self.db.commit()
        self.db.refresh(evaluation)

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
            select(Patient).where(
                Patient.id == patient_id,
                Patient.tenant_id == self.tenant_id
            )
        ).scalar_one_or_none()

        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        return patient

    def get_all_for_patient(self, patient_id: int) -> List[PatientThreshold]:
        """Liste tous les seuils d'un patient."""
        self._verify_patient_access(patient_id)

        query = select(PatientThreshold).where(
            PatientThreshold.patient_id == patient_id,
            PatientThreshold.tenant_id == self.tenant_id
        ).order_by(PatientThreshold.vital_type)

        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, threshold_id: int, patient_id: int) -> PatientThreshold:
        """Récupère un seuil par son ID."""
        self._verify_patient_access(patient_id)

        threshold = self.db.execute(
            select(PatientThreshold).where(
                PatientThreshold.id == threshold_id,
                PatientThreshold.patient_id == patient_id,
                PatientThreshold.tenant_id == self.tenant_id
            )
        ).scalar_one_or_none()

        if not threshold:
            raise ThresholdNotFoundError(f"Seuil {threshold_id} non trouvé")
        return threshold

    def get_by_vital_type(self, patient_id: int, vital_type: str) -> Optional[PatientThreshold]:
        """Récupère le seuil d'un patient pour un type de constante."""
        self._verify_patient_access(patient_id)

        return self.db.execute(
            select(PatientThreshold).where(
                PatientThreshold.patient_id == patient_id,
                PatientThreshold.vital_type == vital_type,
                PatientThreshold.tenant_id == self.tenant_id
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
        self.db.commit()
        self.db.refresh(threshold)
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

        self.db.commit()
        self.db.refresh(threshold)
        return threshold

    def delete(self, threshold_id: int, patient_id: int) -> None:
        """Supprime un seuil."""
        threshold = self.get_by_id(threshold_id, patient_id)
        self.db.delete(threshold)
        self.db.commit()


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
            select(Patient).where(
                Patient.id == patient_id,
                Patient.tenant_id == self.tenant_id
            )
        ).scalar_one_or_none()

        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        return patient

    def get_all_for_patient(
            self,
            patient_id: int,
            filters: Optional[VitalsFilters] = None,
            page: int = 1,
            size: int = 50,
    ) -> Tuple[List[PatientVitals], int]:
        """Liste les mesures d'un patient avec filtres et pagination."""
        self._verify_patient_access(patient_id)

        query = select(PatientVitals).where(
            PatientVitals.patient_id == patient_id,
            PatientVitals.tenant_id == self.tenant_id
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
                PatientVitals.tenant_id == self.tenant_id
            )
        ).scalar_one_or_none()

        if not vital:
            raise VitalsNotFoundError(f"Mesure {vital_id} non trouvée")
        return vital

    def get_latest(self, patient_id: int, vital_type: str) -> Optional[PatientVitals]:
        """Récupère la dernière mesure d'un type pour un patient."""
        self._verify_patient_access(patient_id)

        return self.db.execute(
            select(PatientVitals).where(
                PatientVitals.patient_id == patient_id,
                PatientVitals.vital_type == vital_type,
                PatientVitals.tenant_id == self.tenant_id
            ).order_by(PatientVitals.measured_at.desc()).limit(1)
        ).scalar_one_or_none()

    def create(
            self,
            patient_id: int,
            data: PatientVitalsCreate,
            recorded_by: Optional[int] = None,
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
            measured_at=data.measured_at or datetime.now(timezone.utc),
            recorded_by=recorded_by,
            notes=data.notes,
        )

        self.db.add(vital)
        self.db.commit()
        self.db.refresh(vital)
        return vital

    def delete(self, vital_id: int, patient_id: int) -> None:
        """Supprime une mesure."""
        vital = self.get_by_id(vital_id, patient_id)
        self.db.delete(vital)
        self.db.commit()


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
            select(Patient).where(
                Patient.id == patient_id,
                Patient.tenant_id == self.tenant_id
            )
        ).scalar_one_or_none()

        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        return patient

    def get_all_for_patient(self, patient_id: int, active_only: bool = True) -> List[PatientDevice]:
        """Liste les devices d'un patient."""
        self._verify_patient_access(patient_id)

        query = select(PatientDevice).where(
            PatientDevice.patient_id == patient_id,
            PatientDevice.tenant_id == self.tenant_id
        )

        if active_only:
            query = query.where(PatientDevice.is_active == True)

        query = query.order_by(PatientDevice.device_name)
        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, device_id: int, patient_id: int) -> PatientDevice:
        """Récupère un device par son ID."""
        self._verify_patient_access(patient_id)

        device = self.db.execute(
            select(PatientDevice).where(
                PatientDevice.id == device_id,
                PatientDevice.patient_id == patient_id,
                PatientDevice.tenant_id == self.tenant_id
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
                PatientDevice.device_identifier == data.device_identifier
            )
        ).scalar_one_or_none()

        if existing:
            raise DuplicateDeviceError(
                f"Ce device est déjà enregistré (ID: {existing.id})"
            )

        device = PatientDevice(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            device_type=data.device_type,
            device_identifier=data.device_identifier,
            device_name=data.device_name,
            is_active=True,
        )

        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
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

        self.db.commit()
        self.db.refresh(device)
        return device

    def deactivate(self, device_id: int, patient_id: int) -> PatientDevice:
        """Désactive un device."""
        device = self.get_by_id(device_id, patient_id)
        device.deactivate()
        self.db.commit()
        self.db.refresh(device)
        return device

    def update_sync_time(self, device_id: int, patient_id: int) -> PatientDevice:
        """Met à jour le timestamp de dernière synchronisation."""
        device = self.get_by_id(device_id, patient_id)
        device.update_sync_time()
        self.db.commit()
        self.db.refresh(device)
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
            select(Patient).where(
                Patient.id == patient_id,
                Patient.tenant_id == self.tenant_id
            )
        ).scalar_one_or_none()

        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        return patient

    def get_all_for_patient(
            self,
            patient_id: int,
            document_type: Optional[str] = None,
    ) -> List[PatientDocument]:
        """Liste les documents d'un patient."""
        self._verify_patient_access(patient_id)

        query = select(PatientDocument).where(
            PatientDocument.patient_id == patient_id,
            PatientDocument.tenant_id == self.tenant_id
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
                PatientDocument.tenant_id == self.tenant_id
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
                    PatientEvaluation.tenant_id == self.tenant_id
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
        self.db.commit()
        self.db.refresh(document)
        return document

    def delete(self, document_id: int, patient_id: int) -> None:
        """
        Supprime un document.

        Note: Le fichier physique doit être supprimé séparément.
        """
        document = self.get_by_id(document_id, patient_id)
        self.db.delete(document)
        self.db.commit()