"""
Services métier pour le module Patient.

Contient la logique CRUD pour :
- PatientService (MULTI-TENANT)
- PatientAccessService
- PatientEvaluationService
- PatientThresholdService
- PatientVitalsService
- PatientDeviceService
- PatientDocumentService

NOTE: Le chiffrement/déchiffrement des données sensibles est géré
par un service dédié (app.core.encryption) non implémenté ici.
Pour l'instant, les données sont stockées en clair.

MULTI-TENANT: Toutes les opérations Patient sont filtrées par tenant_id.
"""
from typing import Optional, List, Tuple, Dict, TYPE_CHECKING
from datetime import datetime, timezone

if TYPE_CHECKING:
    # Ces imports ne sont utilisés QUE pour les type hints
    # Ils ne sont pas exécutés à runtime → pas d'import circulaire
    from app.models.patient.evaluation_session import EvaluationSession

from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session, selectinload

from app.models.patient.patient import Patient
from app.models.patient.patient_access import PatientAccess
from app.models.patient.patient_evaluation import PatientEvaluation
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
)

from app.services.validation.schema_validator import (
    get_schema_validator,
    SchemaValidationError,
    SchemaNotFoundError,
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


# =============================================================================
# PATIENT SERVICE (MULTI-TENANT)
# =============================================================================

class PatientService:
    """
    Service pour la gestion des patients.

    MULTI-TENANT: Toutes les opérations sont filtrées par tenant_id.
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

    def get_all(
            self,
            page: int = 1,
            size: int = 20,
            sort_by: str = "created_at",
            sort_order: str = "desc",
            filters: Optional[PatientFilters] = None,
    ) -> Tuple[List[Patient], int]:
        """
        Liste les patients avec pagination et filtres.

        MULTI-TENANT: Filtre automatiquement par tenant_id.
        """
        query = self._base_query()

        if filters:
            if filters.entity_id:
                query = query.where(Patient.entity_id == filters.entity_id)

            if filters.status:
                query = query.where(Patient.status == filters.status.upper())

            if filters.medecin_traitant_id:
                query = query.where(Patient.medecin_traitant_id == filters.medecin_traitant_id)

            # Note: La recherche sur nom/prénom nécessiterait le déchiffrement
            # Pour l'instant, on ne supporte pas la recherche textuelle

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        # Tri
        order_column = getattr(Patient, sort_by, Patient.created_at)
        if sort_order.lower() == "desc":
            order_column = order_column.desc()
        query = query.order_by(order_column)

        # Pagination
        query = query.offset((page - 1) * size).limit(size)

        items = self.db.execute(query).scalars().all()
        return list(items), total

    def get_by_id(self, patient_id: int) -> Patient:
        """
        Récupère un patient par son ID.

        MULTI-TENANT: Vérifie que le patient appartient au tenant courant.
        """
        query = self._base_query().where(Patient.id == patient_id)
        patient = self.db.execute(query).scalar_one_or_none()

        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        return patient

    def create(self, data: PatientCreate, created_by: int) -> Patient:
        """
        Crée un nouveau patient.

        MULTI-TENANT: Injecte automatiquement le tenant_id.
        """
        # Vérifier que l'entité existe ET appartient au tenant
        entity = self.db.execute(
            select(Entity).where(
                Entity.id == data.entity_id,
                Entity.tenant_id == self.tenant_id
            )
        ).scalar_one_or_none()

        if not entity:
            raise EntityNotFoundError(f"Entité {data.entity_id} non trouvée")

        # Vérifier le médecin traitant si spécifié (doit appartenir au tenant)
        if data.medecin_traitant_id:
            medecin = self.db.execute(
                select(User).where(
                    User.id == data.medecin_traitant_id,
                    User.tenant_id == self.tenant_id
                )
            ).scalar_one_or_none()

            if not medecin:
                raise UserNotFoundError(f"Médecin {data.medecin_traitant_id} non trouvé")

        # Créer le patient avec tenant_id auto-injecté
        # NOTE: En production, les données sensibles seraient chiffrées ici
        patient = Patient(
            tenant_id=self.tenant_id,  # AUTO-INJECTION DU TENANT
            entity_id=data.entity_id,
            medecin_traitant_id=data.medecin_traitant_id,
            # Données "chiffrées" (en clair pour l'instant)
            first_name_encrypted=data.first_name,
            last_name_encrypted=data.last_name,
            birth_date_encrypted=str(data.birth_date) if data.birth_date else None,
            nir_encrypted=data.nir,
            ins_encrypted=data.ins,
            address_encrypted=data.address,
            phone_encrypted=data.phone,
            email_encrypted=data.email,
            latitude=data.latitude,
            longitude=data.longitude,
            status="ACTIVE",
        )

        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def update(self, patient_id: int, data: PatientUpdate) -> Patient:
        """Met à jour un patient."""
        patient = self.get_by_id(patient_id)

        update_data = data.model_dump(exclude_unset=True)

        # Vérifier l'entité si modifiée (doit appartenir au tenant)
        if "entity_id" in update_data and update_data["entity_id"]:
            entity = self.db.execute(
                select(Entity).where(
                    Entity.id == update_data["entity_id"],
                    Entity.tenant_id == self.tenant_id
                )
            ).scalar_one_or_none()

            if not entity:
                raise EntityNotFoundError(f"Entité {update_data['entity_id']} non trouvée")

        # Vérifier le médecin si modifié
        if "medecin_traitant_id" in update_data and update_data["medecin_traitant_id"]:
            medecin = self.db.execute(
                select(User).where(
                    User.id == update_data["medecin_traitant_id"],
                    User.tenant_id == self.tenant_id
                )
            ).scalar_one_or_none()

            if not medecin:
                raise UserNotFoundError(f"Médecin {update_data['medecin_traitant_id']} non trouvé")

        # Mapper les champs vers les colonnes chiffrées
        field_mapping = {
            "first_name": "first_name_encrypted",
            "last_name": "last_name_encrypted",
            "birth_date": "birth_date_encrypted",
            "nir": "nir_encrypted",
            "ins": "ins_encrypted",
            "address": "address_encrypted",
            "phone": "phone_encrypted",
            "email": "email_encrypted",
        }

        for field, value in update_data.items():
            if field in field_mapping:
                # Convertir en string pour les dates
                if field == "birth_date" and value:
                    value = str(value)
                setattr(patient, field_mapping[field], value)
            else:
                setattr(patient, field, value)

        self.db.commit()
        self.db.refresh(patient)
        return patient

    def delete(self, patient_id: int) -> None:
        """Archive un patient (soft delete)."""
        patient = self.get_by_id(patient_id)
        patient.status = "ARCHIVED"
        self.db.commit()


# =============================================================================
# PATIENT ACCESS SERVICE (RGPD) - Hérite du tenant via patient
# =============================================================================

class PatientAccessService:
    """
    Service pour la gestion des accès patients (RGPD).

    NOTE: Les accès héritent du tenant via le patient.
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant courant
        """
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
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        query = select(PatientAccess).where(PatientAccess.patient_id == patient_id)

        if active_only:
            query = query.where(PatientAccess.revoked_at.is_(None))

        query = query.order_by(PatientAccess.granted_at.desc())
        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, access_id: int, patient_id: int) -> PatientAccess:
        """Récupère un accès par son ID."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        access = self.db.get(PatientAccess, access_id)
        if not access or access.patient_id != patient_id:
            raise AccessNotFoundError(f"Accès {access_id} non trouvé")
        return access

    def grant_access(
            self,
            patient_id: int,
            data: PatientAccessCreate,
            granted_by: int,
    ) -> PatientAccess:
        """Accorde un accès à un dossier patient."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        # Vérifier que l'utilisateur existe et appartient au tenant
        user = self.db.execute(
            select(User).where(
                User.id == data.user_id,
                User.tenant_id == self.tenant_id
            )
        ).scalar_one_or_none()

        if not user:
            raise UserNotFoundError(f"Utilisateur {data.user_id} non trouvé")

        access = PatientAccess(
            patient_id=patient_id,
            user_id=data.user_id,
            tenant_id=self.tenant_id,  # AJOUT
            access_type=data.access_type,
            reason=data.reason,
            expires_at=data.expires_at,
            granted_by=granted_by,
            granted_at=datetime.now(timezone.utc),
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

    def check_access(self, patient_id: int, user_id: int, required_type: str = "READ") -> bool:
        """Vérifie si un utilisateur a accès à un patient."""
        # Vérifier que le patient appartient au tenant
        try:
            self._verify_patient_access(patient_id)
        except PatientNotFoundError:
            return False

        query = select(PatientAccess).where(
            PatientAccess.patient_id == patient_id,
            PatientAccess.user_id == user_id,
            PatientAccess.revoked_at.is_(None),
        )

        access = self.db.execute(query).scalar_one_or_none()

        if not access or not access.is_active:
            return False

        # Vérifier le niveau d'accès
        if required_type == "READ":
            return access.can_read()
        elif required_type == "WRITE":
            return access.can_write()
        else:
            return access.access_type == "FULL"


# =============================================================================
# PATIENT EVALUATION SERVICE - Hérite du tenant via patient
# =============================================================================

class PatientEvaluationService:
    """
    Service pour la gestion des évaluations.

    NOTE: Les évaluations héritent du tenant via le patient.
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant courant
        """
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
            page: int = 1,
            size: int = 20,
    ) -> Tuple[List[PatientEvaluation], int]:
        """Liste les évaluations d'un patient."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        query = select(PatientEvaluation).where(
            PatientEvaluation.patient_id == patient_id
        ).order_by(PatientEvaluation.evaluation_date.desc())

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        # Pagination
        query = query.offset((page - 1) * size).limit(size)

        items = self.db.execute(query).scalars().all()
        return list(items), total

    def get_by_id(self, evaluation_id: int, patient_id: int) -> PatientEvaluation:
        """Récupère une évaluation par son ID."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        evaluation = self.db.get(PatientEvaluation, evaluation_id)
        if not evaluation or evaluation.patient_id != patient_id:
            raise EvaluationNotFoundError(f"Évaluation {evaluation_id} non trouvée")
        return evaluation

    def create(
            self,
            patient_id: int,
            data: PatientEvaluationCreate,
            evaluator_id: int,
    ) -> PatientEvaluation:
        """Crée une évaluation avec expiration automatique."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        # Vérifier qu'il n'y a pas déjà une évaluation en cours
        existing_draft = self.db.execute(
            select(PatientEvaluation).where(
                PatientEvaluation.patient_id == patient_id,
                PatientEvaluation.status.in_(["DRAFT", "PENDING_COMPLETION"]),
                PatientEvaluation.tenant_id == self.tenant_id
            )
        ).scalar_one_or_none()

        if existing_draft:
            raise EvaluationInProgressError(
                f"Une évaluation est déjà en cours pour ce patient (ID: {existing_draft.id})"
            )

        # Validation partielle du JSON Schema (à la création)
        if data.evaluation_data:
            validator = get_schema_validator()
            try:
                # Validation PARTIELLE car c'est un brouillon
                errors = validator.validate_partial(
                    data.schema_type,
                    data.schema_version,
                    data.evaluation_data
                )
                # On log les erreurs mais on ne bloque pas (c'est un DRAFT)
                if errors:
                    # Optionnel : logger les erreurs pour debug
                    pass
            except SchemaNotFoundError as e:
                raise InvalidEvaluationDataError(f"Schema invalide: {e}")

        evaluation = PatientEvaluation(
            patient_id=patient_id,
            tenant_id=self.tenant_id,
            evaluator_id=evaluator_id,
            schema_type=data.schema_type,
            schema_version=data.schema_version,
            evaluation_data=data.evaluation_data or {},
            evaluation_date=data.evaluation_date,
            status="DRAFT",  # NOUVEAU
            completion_percent=0,  # NOUVEAU
        )

        # NOUVEAU : Définir l'expiration à J+7
        evaluation.set_expiration(days=7)

        self.db.add(evaluation)
        self.db.commit()
        self.db.refresh(evaluation)
        return evaluation

    def update(self, evaluation_id: int, patient_id: int, data: PatientEvaluationUpdate) -> PatientEvaluation:
        """Met à jour une évaluation (saisie partielle)."""
        evaluation = self.get_by_id(evaluation_id, patient_id)

        # NOUVEAU : Vérifications
        if evaluation.status == "VALIDATED":
            raise EvaluationNotEditableError("Une évaluation validée ne peut pas être modifiée")

        if evaluation.check_expiration():
            self.db.commit()
            raise EvaluationExpiredError("Cette évaluation a expiré")

        # Validation de la variable AGGIR si fournie
        if data.aggir_variable_code and data.aggir_variable_data:
            validator = get_schema_validator()
            try:
                validator.validate_aggir_variable(
                    data.aggir_variable_data,
                    evaluation.schema_type,
                    evaluation.schema_version,
                )
            except SchemaValidationError as e:
                raise InvalidEvaluationDataError(
                    f"Variable AGGIR invalide: {e.message}",
                    errors=e.errors
                )

            self._update_aggir_variable(
                evaluation,
                data.aggir_variable_code,
                data.aggir_variable_data
            )
        elif data.evaluation_data:
            # Validation partielle du JSON complet
            validator = get_schema_validator()
            errors = validator.validate_partial(
                evaluation.schema_type,
                evaluation.schema_version,
                data.evaluation_data
            )
            # On accepte les erreurs car c'est un brouillon
            evaluation.evaluation_data = data.evaluation_data

        evaluation.update_completion()
        evaluation.version += 1

        self.db.commit()
        self.db.refresh(evaluation)
        return evaluation

    def _update_aggir_variable(
            self,
            evaluation: PatientEvaluation,
            variable_code: str,
            variable_data: Dict
    ) -> None:
        """Met à jour une variable AGGIR spécifique dans le JSON."""
        if not evaluation.evaluation_data:
            evaluation.evaluation_data = {"aggir": {"AggirVariable": []}}

        aggir = evaluation.evaluation_data.setdefault("aggir", {})
        variables = aggir.setdefault("AggirVariable", [])

        # Chercher la variable existante ou créer une nouvelle
        found = False
        for var in variables:
            if var.get("Code") == variable_code:
                var.update(variable_data)
                found = True
                break

        if not found:
            variables.append({"Code": variable_code, **variable_data})

    def validate(self, evaluation_id: int, patient_id: int, validated_by: int) -> PatientEvaluation:
        """Valide une évaluation."""
        evaluation = self.get_by_id(evaluation_id, patient_id)

        if evaluation.is_validated:
            raise EvaluationAlreadyValidatedError("Cette évaluation est déjà validée")

        evaluation.validate(validated_by)
        self.db.commit()
        self.db.refresh(evaluation)
        return evaluation

    def delete(self, evaluation_id: int, patient_id: int) -> None:
        """Supprime une évaluation."""
        evaluation = self.get_by_id(evaluation_id, patient_id)

        if evaluation.is_validated:
            raise EvaluationAlreadyValidatedError("Une évaluation validée ne peut pas être supprimée")

        self.db.delete(evaluation)
        self.db.commit()

    def submit_for_validation(
            self,
            evaluation_id: int,
            patient_id: int,
    ) -> PatientEvaluation:
        """
        Soumet une évaluation pour validation médicale.

        VALIDATION COMPLÈTE du JSON Schema requise ici.
        """
        evaluation = self.get_by_id(evaluation_id, patient_id)

        if evaluation.status not in ["DRAFT", "PENDING_COMPLETION", "COMPLETE"]:
            raise EvaluationNotEditableError(
                f"Impossible de soumettre une évaluation en statut {evaluation.status}"
            )

        # ═══════════════════════════════════════════════════════════════════
        # NOUVEAU : Validation COMPLÈTE obligatoire avant soumission
        # ═══════════════════════════════════════════════════════════════════
        validator = get_schema_validator()
        try:
            validator.validate_full(
                evaluation.schema_type,
                evaluation.schema_version,
                evaluation.evaluation_data,
            )
        except SchemaValidationError as e:
            raise InvalidEvaluationDataError(
                f"L'évaluation est incomplète ou invalide: {e.message}",
                errors=e.errors
            )
        # ═══════════════════════════════════════════════════════════════════

        # Calculer le GIR avant soumission
        evaluation.update_gir_score()

        evaluation.status = "PENDING_MEDICAL"

        self.db.commit()
        self.db.refresh(evaluation)
        return evaluation

    # =============================================================================
    # SESSION MANAGEMENT
    # =============================================================================

    def start_session(
            self,
            evaluation_id: int,
            patient_id: int,
            user_id: int,
            device_info: str = None,
            local_session_id: str = None,
    ) -> "EvaluationSession":
        """Démarre une nouvelle session de saisie."""
        from app.models.patient.evaluation_session import EvaluationSession

        evaluation = self.get_by_id(evaluation_id, patient_id)

        if evaluation.status not in ["DRAFT", "PENDING_COMPLETION"]:
            raise EvaluationNotEditableError("Cette évaluation ne peut plus être modifiée")

        # Fermer toute session en cours
        if evaluation.current_session:
            evaluation.current_session.end_session()

        session = EvaluationSession(
            tenant_id=self.tenant_id,
            evaluation_id=evaluation_id,
            user_id=user_id,
            device_info=device_info,
            local_session_id=local_session_id,
            status="IN_PROGRESS",
            sync_status="SYNCED" if local_session_id is None else "PENDING",
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def end_session(
            self,
            session_id: int,
            evaluation_id: int,
            patient_id: int,
    ) -> "EvaluationSession":
        """Termine une session de saisie."""
        from app.models.patient.evaluation_session import EvaluationSession

        evaluation = self.get_by_id(evaluation_id, patient_id)

        session = self.db.get(EvaluationSession, session_id)
        if not session or session.evaluation_id != evaluation_id:
            raise EntityNotFoundError(f"Session {session_id} non trouvée")

        session.end_session()
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_sessions(
            self,
            evaluation_id: int,
            patient_id: int,
    ) -> List["EvaluationSession"]:
        """Récupère toutes les sessions d'une évaluation."""
        from app.models.patient.evaluation_session import EvaluationSession

        self.get_by_id(evaluation_id, patient_id)  # Vérifie l'accès

        query = select(EvaluationSession).where(
            EvaluationSession.evaluation_id == evaluation_id
        ).order_by(EvaluationSession.started_at.desc())

        return list(self.db.execute(query).scalars().all())

    def sync_offline_changes(
            self,
            evaluation_id: int,
            patient_id: int,
            sync_payload: "SyncPayload",
    ) -> "SyncResponse":
        """Synchronise les modifications hors-ligne."""
        from app.api.v1.patient.schemas import SyncResponse

        evaluation = self.get_by_id(evaluation_id, patient_id)

        conflicts = []
        synced_count = 0

        for change in sync_payload.changes:
            # Vérifier les conflits potentiels
            # (logique de résolution à implémenter selon les besoins)

            # Appliquer le changement
            self._apply_sync_change(evaluation, change)
            synced_count += 1

        evaluation.update_completion()
        self.db.commit()

        return SyncResponse(
            success=True,
            server_timestamp=datetime.now(timezone.utc),
            conflicts=conflicts,
            synced_changes=synced_count,
            evaluation_status=evaluation.status,
            completion_percent=evaluation.completion_percent,
        )

    def _apply_sync_change(self, evaluation: PatientEvaluation, change: Dict) -> None:
        """Applique un changement synchronisé."""
        if change.get("entity") == "aggir_variable":
            self._update_aggir_variable(
                evaluation,
                change["variable_code"],
                change["data"]
            )


# =============================================================================
# PATIENT THRESHOLD SERVICE - Hérite du tenant via patient
# =============================================================================

class PatientThresholdService:
    """
    Service pour la gestion des seuils de constantes.

    NOTE: Les seuils héritent du tenant via le patient.
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant courant
        """
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
        """Liste les seuils d'un patient."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        query = select(PatientThreshold).where(
            PatientThreshold.patient_id == patient_id
        ).order_by(PatientThreshold.vital_type)

        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, threshold_id: int, patient_id: int) -> PatientThreshold:
        """Récupère un seuil par son ID."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        threshold = self.db.get(PatientThreshold, threshold_id)
        if not threshold or threshold.patient_id != patient_id:
            raise ThresholdNotFoundError(f"Seuil {threshold_id} non trouvé")
        return threshold

    def create(
            self,
            patient_id: int,
            data: PatientThresholdCreate,
    ) -> PatientThreshold:
        """Crée un seuil."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        # Vérifier unicité (patient + vital_type)
        existing = self.db.execute(
            select(PatientThreshold).where(
                PatientThreshold.patient_id == patient_id,
                PatientThreshold.vital_type == data.vital_type,
            )
        ).scalar_one_or_none()

        if existing:
            raise DuplicateThresholdError(
                f"Un seuil pour {data.vital_type} existe déjà pour ce patient"
            )

        threshold = PatientThreshold(
            patient_id=patient_id,
            tenant_id=self.tenant_id,
            **data.model_dump(),
        )

        self.db.add(threshold)
        self.db.commit()
        self.db.refresh(threshold)
        return threshold

    def update(self, threshold_id: int, patient_id: int, data: PatientThresholdUpdate) -> PatientThreshold:
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
# PATIENT VITALS SERVICE - Hérite du tenant via patient
# =============================================================================

class PatientVitalsService:
    """
    Service pour la gestion des mesures de constantes.

    NOTE: Les mesures héritent du tenant via le patient.
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant courant
        """
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
            page: int = 1,
            size: int = 50,
            filters: Optional[VitalsFilters] = None,
    ) -> Tuple[List[PatientVitals], int]:
        """Liste les mesures d'un patient."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        query = select(PatientVitals).where(PatientVitals.patient_id == patient_id)

        if filters:
            if filters.vital_type:
                query = query.where(PatientVitals.vital_type == filters.vital_type.upper())
            if filters.date_from:
                query = query.where(PatientVitals.measured_at >= filters.date_from)
            if filters.date_to:
                query = query.where(PatientVitals.measured_at <= filters.date_to)
            if filters.status:
                query = query.where(PatientVitals.status == filters.status)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        # Tri et pagination
        query = query.order_by(PatientVitals.measured_at.desc())
        query = query.offset((page - 1) * size).limit(size)

        items = self.db.execute(query).scalars().all()
        return list(items), total

    def get_by_id(self, vitals_id: int, patient_id: int) -> PatientVitals:
        """Récupère une mesure par son ID."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        vitals = self.db.get(PatientVitals, vitals_id)
        if not vitals or vitals.patient_id != patient_id:
            raise VitalsNotFoundError(f"Mesure {vitals_id} non trouvée")
        return vitals

    def create(
            self,
            patient_id: int,
            data: PatientVitalsCreate,
            recorded_by: Optional[int] = None,
    ) -> PatientVitals:
        """Crée une mesure de constante."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        # Calculer le statut par rapport aux seuils
        status = None
        threshold = self.db.execute(
            select(PatientThreshold).where(
                PatientThreshold.patient_id == patient_id,
                PatientThreshold.vital_type == data.vital_type,
            )
        ).scalar_one_or_none()

        if threshold:
            status = threshold.check_value(data.value).value

        vitals = PatientVitals(
            patient_id=patient_id,
            tenant_id=self.tenant_id,
            vital_type=data.vital_type,
            value=data.value,
            unit=data.unit,
            status=status,
            source=data.source,
            device_id=data.device_id,
            measured_at=data.measured_at,
            recorded_by=recorded_by,
            notes=data.notes,
        )

        self.db.add(vitals)
        self.db.commit()
        self.db.refresh(vitals)
        return vitals

    def delete(self, vitals_id: int, patient_id: int) -> None:
        """Supprime une mesure."""
        vitals = self.get_by_id(vitals_id, patient_id)
        self.db.delete(vitals)
        self.db.commit()

    def get_latest_by_type(
            self,
            patient_id: int,
            vital_type: str,
    ) -> Optional[PatientVitals]:
        """Récupère la dernière mesure d'un type donné."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        query = select(PatientVitals).where(
            PatientVitals.patient_id == patient_id,
            PatientVitals.vital_type == vital_type.upper(),
        ).order_by(PatientVitals.measured_at.desc()).limit(1)

        return self.db.execute(query).scalar_one_or_none()


# =============================================================================
# PATIENT DEVICE SERVICE - Hérite du tenant via patient
# =============================================================================

class PatientDeviceService:
    """
    Service pour la gestion des devices connectés.

    NOTE: Les devices héritent du tenant via le patient.
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant courant
        """
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
    ) -> List[PatientDevice]:
        """Liste les devices d'un patient."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        query = select(PatientDevice).where(PatientDevice.patient_id == patient_id)

        if active_only:
            query = query.where(PatientDevice.is_active == True)

        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, device_id: int, patient_id: int) -> PatientDevice:
        """Récupère un device par son ID."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        device = self.db.get(PatientDevice, device_id)
        if not device or device.patient_id != patient_id:
            raise DeviceNotFoundError(f"Device {device_id} non trouvé")
        return device

    def create(
            self,
            patient_id: int,
            data: PatientDeviceCreate,
    ) -> PatientDevice:
        """Enregistre un nouveau device."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        # Vérifier unicité (device_type + device_identifier)
        existing = self.db.execute(
            select(PatientDevice).where(
                PatientDevice.device_type == data.device_type,
                PatientDevice.device_identifier == data.device_identifier,
            )
        ).scalar_one_or_none()

        if existing:
            raise DuplicateDeviceError(
                f"Ce device est déjà enregistré"
            )

        device = PatientDevice(
            patient_id=patient_id,
            tenant_id=self.tenant_id,
            **data.model_dump(),
        )

        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return device

    def update(self, device_id: int, patient_id: int, data: PatientDeviceUpdate) -> PatientDevice:
        """Met à jour un device."""
        device = self.get_by_id(device_id, patient_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(device, field, value)

        self.db.commit()
        self.db.refresh(device)
        return device

    def delete(self, device_id: int, patient_id: int) -> None:
        """Supprime (désactive) un device."""
        device = self.get_by_id(device_id, patient_id)
        device.deactivate()
        self.db.commit()


# =============================================================================
# PATIENT DOCUMENT SERVICE - Hérite du tenant via patient
# =============================================================================

class PatientDocumentService:
    """
    Service pour la gestion des documents générés.

    NOTE: Les documents héritent du tenant via le patient.
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant courant
        """
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
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        query = select(PatientDocument).where(
            PatientDocument.patient_id == patient_id
        )

        if document_type:
            query = query.where(PatientDocument.document_type == document_type.upper())

        query = query.order_by(PatientDocument.generated_at.desc())
        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, document_id: int, patient_id: int) -> PatientDocument:
        """Récupère un document par son ID."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        document = self.db.get(PatientDocument, document_id)
        if not document or document.patient_id != patient_id:
            raise DocumentNotFoundError(f"Document {document_id} non trouvé")
        return document

    def create(
            self,
            patient_id: int,
            data: PatientDocumentCreate,
            generated_by: int,
            file_path: str,
            file_size_bytes: Optional[int] = None,
            file_hash: Optional[str] = None,
    ) -> PatientDocument:
        """Crée un document."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_access(patient_id)

        document = PatientDocument(
            patient_id=patient_id,
            document_type=data.document_type,
            title=data.title,
            description=data.description,
            source_evaluation_id=data.source_evaluation_id,
            generation_prompt=data.generation_prompt,
            generation_context=data.generation_context,
            file_path=file_path,
            file_format=data.file_format,
            file_size_bytes=file_size_bytes,
            file_hash=file_hash,
            generated_by=generated_by,
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def delete(self, document_id: int, patient_id: int) -> None:
        """Supprime un document."""
        document = self.get_by_id(document_id, patient_id)
        # NOTE: En production, supprimer aussi le fichier physique
        self.db.delete(document)
        self.db.commit()