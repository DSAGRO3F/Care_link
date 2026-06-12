"""
Services métier pour le module Validation (Phase 4 bis — B40-J2).

Contient :
- NotificationService : CRUD destinataire-scopé + dispatch automatique des
  notifications sur événement workflow (D11 v3).
- ValidationRequestService : actes du workflow validation (submit, transmit-*,
  decide, withdraw, mark-under-appeal) — table de transitions verrouillée
  Session 27, ping-pong commun interne/externe.
- ValidationEvent : enum interne (non-DB) abstrayant les actes du workflow.

Modèles : `app/models/validation/` + `app/models/patient/patient_evaluation.py`
+ `app/models/careplan/care_plan.py`. RLS atypique par destinataire sur
`notifications` (#130). Schémas : `app/api/v1/validation/schemas.py`.

Conventions : style aligné sur `app/api/v1/careplan/services.py`
(`__init__(db, tenant_id)`, `_base_query()` filtré explicitement par tenant,
RLS en filet de sécurité ; `flush()` partout, `commit()` délégué à `get_db()` ;
exceptions dédiées remontées en HTTPException par la couche router ;
audit horodaté grep-able #109).

Décisions verrouillées Session 27 :
- Abstraction par événement : `notify_validation_event(vr, event, actor)`.
- Dé-duplication par set d'`user_id` (sans concaténation de motif).
- Pas de notification à l'acteur lui-même ; aucune notif pour `WITHDRAWN`.
- Option C statut : le service écrit directement `PatientEvaluation.status` /
  `CarePlan.status` avec les nouvelles valeurs d'enum (refonte des méthodes
  de transition modèle tracée en ticket séparé).
- Point 1 transmit-medical/funding : valide la VR courante (decision=VALIDATED)
  ET crée la VR de l'étape suivante en un seul acte ; un seul événement
  `TRANSMITTED_*` émis (pas de doublon DECIDED_VALIDATED+TRANSMITTED).
- Point 2 invalidation externe (option A) : toute INVALIDATED / MORE_INFO
  externe (MEDICAL/FUNDING) repasse par le GCSMS en remontant d'une étape.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import Query, Session

from app.api.v1.validation.schemas import (
    ExchangeCreate,
    MarkUnderAppealRequest,
    ResubmitRequest,
    ValidationDecisionRequest,
    ValidationRequestFilters,
    ValidationSubmitRequest,
    ValidationTransmitRequest,
    ValidationWithdrawRequest,
)
from app.models.careplan.care_plan import CarePlan
from app.models.enums import (
    CarePlanStatus,
    EvaluationStatus,
    ExchangeActionType,
    ExchangeVisibility,
    NotificationType,
    ValidationDecision,
    ValidationStage,
    ValidationWorkflowType,
)
from app.models.patient.patient_evaluation import PatientEvaluation
from app.models.user.role import Role
from app.models.user.user import User
from app.models.user.user_associations import UserRole
from app.models.user.user_tenant_assignment import UserTenantAssignment
from app.models.validation.notification import Notification
from app.models.validation.validation_exchange import ValidationExchange
from app.models.validation.validation_request import ValidationRequest


# =============================================================================
# CODES DE PERMISSION (constantes greppables — synchro INITIAL_PERMISSIONS)
# =============================================================================

PERM_VALIDATION_VIEW = "VALIDATION_VIEW"
PERM_VALIDATION_SUBMIT = "VALIDATION_SUBMIT"
PERM_VALIDATION_WITHDRAW = "VALIDATION_WITHDRAW"
PERM_VALIDATION_INTERNAL_REVIEW = "VALIDATION_INTERNAL_REVIEW"
PERM_VALIDATION_MEDICAL_REVIEW = "VALIDATION_MEDICAL_REVIEW"
PERM_VALIDATION_FUNDING_REVIEW = "VALIDATION_FUNDING_REVIEW"
PERM_EVALUATION_CREATE = "EVALUATION_CREATE"


if TYPE_CHECKING:
    pass


# =============================================================================
# EXCEPTIONS DÉDIÉES
# =============================================================================


class NotificationServiceError(Exception):
    """Classe de base pour les erreurs du service Notification."""


class NotificationNotFoundError(NotificationServiceError):
    """Notification introuvable pour ce destinataire."""


# =============================================================================
# EXCEPTIONS DÉDIÉES — Validation
# =============================================================================


class ValidationServiceError(Exception):
    """Classe de base pour les erreurs du service Validation."""


class ValidationRequestNotFoundError(ValidationServiceError):
    """Demande de validation introuvable dans ce tenant."""


class EvaluationNotFoundError(ValidationServiceError):
    """Évaluation introuvable dans ce tenant."""


class CarePlanNotFoundError(ValidationServiceError):
    """Plan d'aide introuvable dans ce tenant."""


class ValidatorUserNotFoundError(ValidationServiceError):
    """Utilisateur valideur introuvable dans ce tenant."""


class EvaluationNotSubmittableError(ValidationServiceError):
    """L'évaluation n'est pas dans un statut soumissible (DRAFT / IN_PROGRESS)."""


class CarePlanNotSubmittableError(ValidationServiceError):
    """Le plan d'aide n'est pas dans un statut soumissible (DRAFT)."""


class PendingValidationExistsError(ValidationServiceError):
    """Une demande de validation pendante existe déjà sur cet objet validable."""

    def __init__(self, object_label: str, existing_vr_id: int) -> None:
        self.object_label = object_label
        self.existing_vr_id = existing_vr_id
        super().__init__(
            f"Une demande de validation en cours (#{existing_vr_id}) existe déjà "
            f"sur {object_label}. Tranchez-la ou retirez-la avant d'en démarrer une nouvelle."
        )


class IllegalTransitionError(ValidationServiceError):
    """Transition interdite (VR déjà tranchée, retirée, ou stage incompatible avec l'acte)."""


class WorkflowMismatchError(ValidationServiceError):
    """Acte incompatible avec le `workflow_type` ou le `stage` courant.

    Cas typique : `decide(VALIDATED)` sur `INTERNAL_REVIEW` en `AGGIR_FUNDING`
    → l'avancée positive doit passer par `transmit-medical` (point 1, Session 27).
    """


class SelfValidationError(ValidationServiceError):
    """Anti-self-validation (D24) : l'auteur d'un acte ne peut pas être son destinataire."""


class WithdrawNotAllowedError(ValidationServiceError):
    """Retrait interdit : D14 v2 (cycle interne) ou actor != submitter."""


class MissingValidatorError(ValidationServiceError):
    """Aucun valideur assigné fourni pour une transmission."""


class PermissionDeniedError(ValidationServiceError):
    """L'utilisateur ne porte pas la permission requise."""


class AppealNotAllowedError(ValidationServiceError):
    """Drapeau de recours interdit : éval non FUNDING_REJECTED (D21)."""


# =============================================================================
# ÉVÉNEMENTS DE VALIDATION (enum interne, non-DB)
# =============================================================================


class ValidationEvent(StrEnum):
    """Événements de haut niveau du workflow validation.

    Couche d'abstraction entre `ValidationRequestService` et la table de
    dispatch des destinataires. Ne dépend ni de `ValidationStage` ni de
    `ValidationDecision` directement — découpler permet d'ajouter de nouveaux
    actes (relance, escalade) sans toucher la logique de transition.

    Note : pas d'événement `WITHDRAWN` — décision verrouillée Session 27,
    aucune notification émise sur retrait (trace dans `vr.withdrawn_*`).
    """

    SUBMITTED = "SUBMITTED"
    RESUBMITTED = "RESUBMITTED"
    TRANSMITTED_MEDICAL = "TRANSMITTED_MEDICAL"
    TRANSMITTED_FUNDING = "TRANSMITTED_FUNDING"
    DECIDED_VALIDATED = "DECIDED_VALIDATED"
    DECIDED_INVALIDATED = "DECIDED_INVALIDATED"
    DECIDED_MORE_INFO = "DECIDED_MORE_INFO"
    DECIDED_FUNDING_REJECTED = "DECIDED_FUNDING_REJECTED"


# =============================================================================
# SERVICE NOTIFICATION
# =============================================================================


class NotificationService:
    """Couche métier des notifications utilisateur.

    Responsabilités :
    1. CRUD destinataire-scopé pour les endpoints `/notifications/*` (§9.2).
    2. Dispatch automatique des destinataires sur événement workflow
       (D11 v3 : GCSMS + externe selon stage/workflow_type).

    Tenant context : RLS standard ne s'applique pas — la table notifications
    a une policy SELECT/UPDATE/DELETE par `recipient_user_id` (#130). Le
    `tenant_id` reste cohérent avec celui de la VR à l'origine de la notif.
    """

    def __init__(self, db: Session, tenant_id: int) -> None:
        self.db = db
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Requêtes internes
    # ------------------------------------------------------------------

    def _base_query(self) -> Query[Notification]:
        """Requête de base filtrée par tenant (filet : RLS atypique #130 par recipient)."""
        return self.db.query(Notification).filter(Notification.tenant_id == self.tenant_id)

    def _get_for_recipient(self, notification_id: int, user_id: int) -> Notification:
        """Récupère une notification pour un destinataire donné, ou lève."""
        notif = (
            self._base_query()
            .filter(
                Notification.id == notification_id,
                Notification.recipient_user_id == user_id,
            )
            .first()
        )
        if notif is None:
            raise NotificationNotFoundError(
                f"Notification {notification_id} introuvable pour cet utilisateur"
            )
        return notif

    # ------------------------------------------------------------------
    # API publique — endpoints /notifications/*
    # ------------------------------------------------------------------

    def list_for_user(
        self,
        user_id: int,
        page: int = 1,
        size: int = 20,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        """Liste paginée des notifications du destinataire (ordre antéchronologique).

        Retourne `(items, total)`. Pagination 1-indexée, taille >= 1.
        """
        query = self._base_query().filter(Notification.recipient_user_id == user_id)
        if unread_only:
            query = query.filter(Notification.is_read.is_(False))

        total = query.count()
        items = (
            query.order_by(Notification.created_at.desc())
            .offset(max(0, (page - 1) * size))
            .limit(max(1, size))
            .all()
        )
        return items, total

    def count_unread(self, user_id: int) -> int:
        """Compteur de notifications non lues (badge polling 30s, D22 β)."""
        return (
            self._base_query()
            .filter(
                Notification.recipient_user_id == user_id,
                Notification.is_read.is_(False),
            )
            .count()
        )

    def mark_read(self, notification_id: int, user_id: int) -> Notification:
        """Marque une notification comme lue (idempotent via `mark_as_read()` du modèle)."""
        notif = self._get_for_recipient(notification_id, user_id)
        notif.mark_as_read()
        self.db.flush()
        return notif

    def mark_all_read(self, user_id: int) -> int:
        """Marque toutes les notifications non lues du destinataire. Retourne le nombre."""
        unread = (
            self._base_query()
            .filter(
                Notification.recipient_user_id == user_id,
                Notification.is_read.is_(False),
            )
            .all()
        )
        now = datetime.now(UTC)
        for notif in unread:
            notif.is_read = True
            notif.read_at = now
        self.db.flush()
        return len(unread)

    # ------------------------------------------------------------------
    # API publique — dispatch sur événement workflow
    # ------------------------------------------------------------------

    def notify_validation_event(
        self,
        vr: ValidationRequest,
        event: ValidationEvent,
        actor: User,
    ) -> list[Notification]:
        """Crée les notifications correspondant à un événement workflow (D11 v3).

        - Calcule l'ensemble dédupliqué des destinataires (set d'`user_id`).
        - Exclut systématiquement l'acteur de l'événement.
        - Crée une `Notification` par destinataire avec type, title, body, link_url
          et FK relationnelles renseignées selon l'événement.

        Retourne la liste des notifications créées (peut être vide si seul
        l'acteur était destinataire — ou si l'événement n'a pas de destinataire).
        """
        recipient_ids = self._build_recipients(vr, event)
        recipient_ids.discard(actor.id)  # Pas de notif à l'acteur (décision Session 27)

        if not recipient_ids:
            return []

        notif_type, title, body = self._build_message(vr, event)
        link_url = self._build_link_url(vr)
        notifications: list[Notification] = []

        for user_id in recipient_ids:
            notif = Notification(
                tenant_id=self.tenant_id,
                recipient_user_id=user_id,
                type=notif_type,
                title=title,
                body=body,
                link_url=link_url,
                related_evaluation_id=vr.evaluation_id,
                related_care_plan_id=vr.care_plan_id,
                related_validation_request_id=vr.id,
            )
            self.db.add(notif)
            notifications.append(notif)

        self.db.flush()
        return notifications

    # ------------------------------------------------------------------
    # Dispatch interne — calcul des destinataires (D11 v3)
    # ------------------------------------------------------------------

    def _build_recipients(
        self,
        vr: ValidationRequest,
        event: ValidationEvent,
    ) -> set[int]:
        """Calcule l'ensemble dédupliqué des destinataires selon D11 v3.

        Règles par événement :
        - SUBMITTED : admin(s) du tenant (relecteur interne attendu).
        - RESUBMITTED : idem SUBMITTED (relecteur interne re-sollicité après complément).
        - TRANSMITTED_MEDICAL : médecin assigné + GCSMS (admin + IDEC).
        - TRANSMITTED_FUNDING : agent département assigné + GCSMS + médecin.
        - DECIDED_VALIDATED : GCSMS (IDEC + admin) ; selon stage, ajoute
          médecin (transmission externe en cours) ou département.
        - DECIDED_INVALIDATED / DECIDED_MORE_INFO : GCSMS + externe encore actif.
        - DECIDED_FUNDING_REJECTED : GCSMS + département + médecin traitant
          du patient (D11 v3 — suivi clinique du refus APA).
        """
        recipients: set[int] = set()

        # GCSMS = admin(s) du tenant + IDEC (submitter)
        gcsms_user_ids = self._gcsms_user_ids() | {vr.submitted_by_user_id}

        # Médecin assigné (sur la VR courante si stage MEDICAL, ou via une VR
        # médicale antérieure du même objet validable).
        medical_user_id = self._medical_validator_user_id(vr)

        # Département assigné (idem, stage FUNDING).
        funding_user_id = self._funding_validator_user_id(vr)

        # Médecin traitant du patient (suivi clinique, FUNDING_REJECTED — D11 v3)
        treating_doctor_user_id = self._treating_doctor_user_id(vr)

        if event in {ValidationEvent.SUBMITTED, ValidationEvent.RESUBMITTED}:
            # (Re-)soumission : destinataire = l'admin GCSMS qui relit
            recipients |= self._gcsms_user_ids()

        elif event == ValidationEvent.TRANSMITTED_MEDICAL:
            recipients |= gcsms_user_ids
            if medical_user_id:
                recipients.add(medical_user_id)

        elif event == ValidationEvent.TRANSMITTED_FUNDING:
            recipients |= gcsms_user_ids
            if medical_user_id:
                recipients.add(medical_user_id)
            if funding_user_id:
                recipients.add(funding_user_id)

        elif event in {
            ValidationEvent.DECIDED_VALIDATED,
            ValidationEvent.DECIDED_INVALIDATED,
            ValidationEvent.DECIDED_MORE_INFO,
        }:
            recipients |= gcsms_user_ids
            # Si on est sorti côté externe, ajouter les externes encore impliqués
            if (
                vr.stage in {ValidationStage.MEDICAL_REVIEW, ValidationStage.FUNDING_REVIEW}
                and medical_user_id
            ):
                recipients.add(medical_user_id)
            if vr.stage == ValidationStage.FUNDING_REVIEW and funding_user_id:
                recipients.add(funding_user_id)

        elif event == ValidationEvent.DECIDED_FUNDING_REJECTED:
            recipients |= gcsms_user_ids
            if funding_user_id:
                recipients.add(funding_user_id)
            if treating_doctor_user_id:
                # Médecin traitant ajouté aux destinataires pour suivi clinique (D11 v3)
                recipients.add(treating_doctor_user_id)

        return recipients

    # ------------------------------------------------------------------
    # Helpers de résolution des destinataires
    # ------------------------------------------------------------------

    def _gcsms_user_ids(self) -> set[int]:
        """Renvoie les `user_id` des administrateurs du tenant courant.

        Couvre : utilisateurs avec `is_admin=True` ou portant le rôle ADMIN
        sur ce tenant via `UserRole`. Le `submitted_by_user_id` (IDEC) est
        ajouté par l'appelant — il n'est pas systématiquement admin.
        """
        # 1. Admins applicatifs (User.is_admin)
        direct = self.db.scalars(
            select(User.id).where(User.is_admin.is_(True), User.tenant_id == self.tenant_id)
        ).all()

        # 2. Utilisateurs portant le rôle ADMIN sur ce tenant
        via_role = self.db.scalars(
            select(User.id)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(User.tenant_id == self.tenant_id, Role.name == "ADMIN")
        ).all()

        return set(direct) | set(via_role)

    def _medical_validator_user_id(self, vr: ValidationRequest) -> int | None:
        """Récupère le valideur médical assigné sur le workflow courant.

        - Si VR courante au stage MEDICAL_REVIEW : son `assigned_validator_user_id`.
        - Sinon : chercher une VR antérieure du même objet validable au stage
          MEDICAL_REVIEW (cas de notif à FUNDING_REVIEW qui doit aussi toucher
          le médecin qui a transmis).
        """
        if vr.stage == ValidationStage.MEDICAL_REVIEW:
            return vr.assigned_validator_user_id
        return self._prior_validator(vr, ValidationStage.MEDICAL_REVIEW)

    def _funding_validator_user_id(self, vr: ValidationRequest) -> int | None:
        """Récupère l'agent département assigné (stage FUNDING_REVIEW)."""
        if vr.stage == ValidationStage.FUNDING_REVIEW:
            return vr.assigned_validator_user_id
        return self._prior_validator(vr, ValidationStage.FUNDING_REVIEW)

    def _prior_validator(
        self,
        vr: ValidationRequest,
        stage: ValidationStage,
    ) -> int | None:
        """Cherche une VR antérieure du même objet validable à l'étape `stage`.

        Utilise les index `ix_validation_requests_tenant_evaluation` et
        `ix_validation_requests_tenant_care_plan`.
        """
        query = self._base_validation_query().filter(
            ValidationRequest.stage == stage,
            ValidationRequest.id != vr.id,
            ValidationRequest.assigned_validator_user_id.isnot(None),
        )
        if vr.workflow_type == ValidationWorkflowType.AGGIR_FUNDING:
            query = query.filter(ValidationRequest.evaluation_id == vr.evaluation_id)
        else:
            query = query.filter(ValidationRequest.care_plan_id == vr.care_plan_id)

        prior = query.order_by(ValidationRequest.submitted_at.desc()).first()
        return prior.assigned_validator_user_id if prior else None

    def _base_validation_query(self) -> Query[ValidationRequest]:
        """Requête de base sur `validation_requests`, filtrée par tenant (#97 explicite)."""
        return self.db.query(ValidationRequest).filter(
            ValidationRequest.tenant_id == self.tenant_id
        )

    def _treating_doctor_user_id(self, vr: ValidationRequest) -> int | None:
        """Renvoie le `user_id` du médecin traitant du patient concerné par la VR.

        Lecture défensive — la VR peut ne pas porter d'évaluation chargée selon
        le `selectinload` de l'appelant. Pour AGGIR_FUNDING, l'objet validable
        est une `PatientEvaluation` qui pointe `patient_id` → `Patient.medecin_traitant_id`.
        Pour COORDINATION_DOSSIER : pas applicable (event FUNDING_REJECTED n'arrive
        qu'en workflow long).
        """
        if vr.workflow_type != ValidationWorkflowType.AGGIR_FUNDING:
            return None

        # Import local pour éviter cycle d'imports en TYPE_CHECKING
        from app.models.patient.patient import Patient
        from app.models.patient.patient_evaluation import PatientEvaluation

        row = self.db.execute(
            select(Patient.medecin_traitant_id)
            .join(PatientEvaluation, PatientEvaluation.patient_id == Patient.id)
            .where(
                PatientEvaluation.id == vr.evaluation_id,
                Patient.tenant_id == self.tenant_id,
            )
        ).scalar_one_or_none()
        return row

    # ------------------------------------------------------------------
    # Construction du message (type, titre, corps, lien)
    # ------------------------------------------------------------------

    def _build_message(
        self,
        vr: ValidationRequest,
        event: ValidationEvent,
    ) -> tuple[NotificationType, str, str]:
        """Construit `(type, title, body)` pour un événement donné.

        Libellés FR concis. Le body reste générique — pas de motif concaténé
        (décision Session 27 : motif d'envoi lisible implicitement par le rôle
        du destinataire). Le détail (motif d'invalidation, message d'info)
        reste consultable sur la fiche ValidationRequest via `link_url`.
        """
        object_label = self._object_label(vr)

        if event == ValidationEvent.SUBMITTED:
            return (
                NotificationType.VALIDATION_REQUEST_RECEIVED,
                "Nouvelle demande de validation",
                f"Une demande de validation a été soumise sur {object_label}.",
            )

        if event == ValidationEvent.RESUBMITTED:
            return (
                NotificationType.VALIDATION_REQUEST_RECEIVED,
                "Dossier re-soumis après complément",
                f"{object_label} a été re-soumis après une demande de compléments.",
            )

        if event == ValidationEvent.TRANSMITTED_MEDICAL:
            return (
                NotificationType.VALIDATION_REQUEST_RECEIVED,
                "Transmission au médecin",
                f"{object_label} a été transmis pour validation médicale.",
            )

        if event == ValidationEvent.TRANSMITTED_FUNDING:
            return (
                NotificationType.VALIDATION_REQUEST_RECEIVED,
                "Transmission au département",
                f"{object_label} a été transmis au département pour décision APA.",
            )

        if event == ValidationEvent.DECIDED_VALIDATED:
            return (
                NotificationType.VALIDATION_DECISION_TAKEN,
                "Validation prononcée",
                f"Une décision favorable a été prononcée sur {object_label}.",
            )

        if event == ValidationEvent.DECIDED_INVALIDATED:
            return (
                NotificationType.VALIDATION_DECISION_TAKEN,
                "Invalidation prononcée",
                f"Une invalidation motivée a été prononcée sur {object_label}.",
            )

        if event == ValidationEvent.DECIDED_MORE_INFO:
            return (
                NotificationType.VALIDATION_INFO_REQUESTED,
                "Compléments demandés",
                f"Le valideur demande des compléments sur {object_label}.",
            )

        if event == ValidationEvent.DECIDED_FUNDING_REJECTED:
            return (
                NotificationType.EVALUATION_FUNDING_REJECTED,
                "Refus APA notifié",
                f"Un refus APA a été notifié sur {object_label}.",
            )

        # Garde-fou — un nouvel événement non câblé tombe ici
        raise NotificationServiceError(f"Événement non géré : {event}")

    def _object_label(self, vr: ValidationRequest) -> str:
        """Libellé court de l'objet validable, pour les notifications."""
        if vr.workflow_type == ValidationWorkflowType.AGGIR_FUNDING:
            return f"l'évaluation #{vr.evaluation_id}"
        return f"le dossier de coordination #{vr.care_plan_id}"

    def _build_link_url(self, vr: ValidationRequest) -> str:
        """URL de redirection vers la fiche ValidationRequest (relative — résolue côté frontend)."""
        return f"/soins/validation/{vr.id}"


# =============================================================================
# SERVICE VALIDATION REQUEST
# =============================================================================


class ValidationRequestService:
    """Couche métier des demandes de validation.

    Sept actes publics couvrant le ping-pong commun interne/externe :
    `submit_evaluation`, `submit_care_plan`, `transmit_medical`,
    `transmit_funding`, `decide`, `withdraw`, `mark_under_appeal`.

    Compose `NotificationService` pour le dispatch automatique des notifs
    sur événement workflow (un seul événement par acte, dé-dupliqué, acteur
    exclu — décisions Session 27).

    Tenant context : RLS standard via `_base_query()` filtré explicitement
    par `tenant_id` (#97 — filtre explicite, RLS en filet de sécurité).
    """

    def __init__(self, db: Session, tenant_id: int) -> None:
        self.db = db
        self.tenant_id = tenant_id
        # Composition : NotificationService partage le même couple db/tenant_id.
        # Léger (pas de requête en __init__), instanciation eager OK.
        self._notifications = NotificationService(db, tenant_id)

    # ------------------------------------------------------------------
    # Requêtes internes & helpers
    # ------------------------------------------------------------------

    def _base_query(self) -> Query[ValidationRequest]:
        """Requête de base sur `validation_requests`, filtrée par tenant (#97)."""
        return self.db.query(ValidationRequest).filter(
            ValidationRequest.tenant_id == self.tenant_id
        )

    def _get_or_404(self, vr_id: int) -> ValidationRequest:
        """Charge la VR par id+tenant ou lève `ValidationRequestNotFoundError`."""
        vr = self._base_query().filter(ValidationRequest.id == vr_id).first()
        if vr is None:
            raise ValidationRequestNotFoundError(
                f"Demande de validation #{vr_id} introuvable dans ce tenant"
            )
        return vr

    def _get_evaluation(self, evaluation_id: int) -> PatientEvaluation:
        """Charge l'évaluation par id+tenant ou lève."""
        eval_obj = (
            self.db.query(PatientEvaluation)
            .filter(
                PatientEvaluation.id == evaluation_id,
                PatientEvaluation.tenant_id == self.tenant_id,
            )
            .first()
        )
        if eval_obj is None:
            raise EvaluationNotFoundError(f"Évaluation #{evaluation_id} introuvable dans ce tenant")
        return eval_obj

    def _get_care_plan(self, care_plan_id: int) -> CarePlan:
        """Charge le plan d'aide par id+tenant ou lève."""
        plan = (
            self.db.query(CarePlan)
            .filter(CarePlan.id == care_plan_id, CarePlan.tenant_id == self.tenant_id)
            .first()
        )
        if plan is None:
            raise CarePlanNotFoundError(f"Plan d'aide #{care_plan_id} introuvable dans ce tenant")
        return plan

    def _get_validator(self, user_id: int) -> User:
        """Charge l'utilisateur valideur par id+tenant ou lève.

        Note B40-J4/J5 : pour les valideurs externes cross-tenant, ce filtre
        deviendra une jointure via `UserTenantAssignment` (rattachement par
        GCSMS, D16). V1 reste tenant-scopé direct.
        """
        user = (
            self.db.query(User).filter(User.id == user_id, User.tenant_id == self.tenant_id).first()
        )
        if user is None:
            raise ValidatorUserNotFoundError(
                f"Utilisateur valideur #{user_id} introuvable dans ce tenant"
            )
        return user

    def _require_permission(self, user: User, code: str) -> None:
        """Vérifie la permission via `User.has_permission` (wildcard ADMIN_FULL pris en compte)."""
        if not user.has_permission(code):
            raise PermissionDeniedError(f"Permission requise : {code} (utilisateur #{user.id})")

    def _check_anti_self(self, vr: ValidationRequest, actor: User) -> None:
        """Anti-self-validation (D24) : l'auteur de la VR ne peut pas en être le décideur/transmetteur."""
        if vr.submitted_by_user_id == actor.id:
            raise SelfValidationError(
                f"Anti-self-validation (D24) : l'utilisateur #{actor.id} a soumis cette VR "
                "et ne peut pas la valider/transmettre/invalider"
            )

    def _check_pending(self, vr: ValidationRequest) -> None:
        """Refuse tout acte sur une VR déjà tranchée ou retirée."""
        if not vr.is_pending:
            raise IllegalTransitionError(
                f"Demande #{vr.id} déjà tranchée ou retirée — aucun acte possible"
            )

    def _check_no_pending_for_evaluation(self, evaluation_id: int) -> None:
        """Refuse une nouvelle soumission s'il existe déjà une VR pendante sur cette éval."""
        existing = (
            self._base_query()
            .filter(
                ValidationRequest.evaluation_id == evaluation_id,
                ValidationRequest.decision.is_(None),
                ValidationRequest.withdrawn_at.is_(None),
            )
            .first()
        )
        if existing is not None:
            raise PendingValidationExistsError(
                object_label=f"l'évaluation #{evaluation_id}",
                existing_vr_id=existing.id,
            )

    def _check_no_pending_for_care_plan(self, care_plan_id: int) -> None:
        """Refuse une nouvelle soumission s'il existe déjà une VR pendante sur ce plan."""
        existing = (
            self._base_query()
            .filter(
                ValidationRequest.care_plan_id == care_plan_id,
                ValidationRequest.decision.is_(None),
                ValidationRequest.withdrawn_at.is_(None),
            )
            .first()
        )
        if existing is not None:
            raise PendingValidationExistsError(
                object_label=f"le plan d'aide #{care_plan_id}",
                existing_vr_id=existing.id,
            )

    def _last_decided_vr_for_evaluation(self, evaluation_id: int) -> ValidationRequest | None:
        """Dernière VR de cette éval tranchée (chaînage R1 — peu importe la décision).

        Sert à renseigner `previous_vr_id` sur la VR ré-ouverte : on raccroche la
        re-soumission à la VR médicale qui a renvoyé le dossier en interne — qu'il
        s'agisse d'un complément (`MORE_INFO_REQUESTED`) ou d'une invalidation
        (`INVALIDATED`), les deux rebondissant en `PENDING_INTERNAL_REVIEW` (R-T1).
        `decision.isnot(None)` exclut les retraits (sans décision). Renvoie None si
        aucune VR décidée (re-soumission alors non chaînée — défensif).
        """
        return (
            self._base_query()
            .filter(
                ValidationRequest.evaluation_id == evaluation_id,
                ValidationRequest.decision.isnot(None),
            )
            .order_by(ValidationRequest.decided_at.desc())
            .first()
        )

    def _append_audit(
        self,
        vr: ValidationRequest,
        prefix: str,
        actor: User,
        detail: str | None = None,
    ) -> None:
        """Ajoute une ligne d'audit horodatée greppable à `vr.notes` (convention #109).

        Format : `[AUDIT|<iso8601>|<PREFIX>|user_id=<id>] <detail?>`.
        Le préfixe `AUDIT|` permet un grep transverse en base.
        """
        ts = datetime.now(UTC).isoformat()
        line = f"[AUDIT|{ts}|{prefix}|user_id={actor.id}]"
        if detail:
            line += f" {detail}"
        vr.notes = f"{vr.notes}\n{line}" if vr.notes else line

    # ------------------------------------------------------------------
    # Fil d'échange (B40-J3) — registre structuré, remplace l'audit-texte
    # ------------------------------------------------------------------

    @staticmethod
    def _role_for_stage(stage: ValidationStage) -> str:
        """Dérive le libellé de rôle figé pour le fil, à partir du stage de la VR.

        Déterministe et indépendant des rôles applicatifs de l'utilisateur (qui
        peuvent être multiples). Le rôle est un instantané, pas une FK (cf. modèle).
        """
        return {
            ValidationStage.INTERNAL_REVIEW: "INTERNAL_VALIDATOR",
            ValidationStage.MEDICAL_REVIEW: "MEDICAL_VALIDATOR",
            ValidationStage.FUNDING_REVIEW: "FUNDING_VALIDATOR",
        }[stage]

    def _append_exchange(
        self,
        vr: ValidationRequest,
        action_type: ExchangeActionType,
        actor: User,
        author_role: str,
        message: str | None = None,
        visibility: ExchangeVisibility = ExchangeVisibility.SHARED_EXTERNAL,
        attachments: list[dict] | None = None,
    ) -> ValidationExchange:
        """Crée une entrée dans le fil d'échange rattachée à la VR (B40-J3).

        Registre structuré qui remplace `_append_audit` pour la trace visible.
        Visibilité par défaut SHARED_EXTERNAL (transparence de coordination) ;
        l'appelant passe INTERNAL_ONLY pour les actes internes (ex. retrait).
        Ne flush pas : l'appelant gère le flush (la VR doit avoir un id au préalable).
        """
        exchange = ValidationExchange(
            tenant_id=self.tenant_id,
            validation_request_id=vr.id,
            author_user_id=actor.id,
            author_role=author_role,
            action_type=action_type,
            visibility=visibility,
            message=message,
            attachments=attachments or [],
        )
        self.db.add(exchange)
        return exchange

    # ------------------------------------------------------------------
    # API publique — actes de soumission
    # ------------------------------------------------------------------

    def submit_evaluation(
        self,
        evaluation_id: int,
        payload: ValidationSubmitRequest,
        submitted_by: User,
    ) -> ValidationRequest:
        """Soumet une évaluation au workflow AGGIR_FUNDING (étape interne).

        Crée une VR `INTERNAL_REVIEW` et fait passer l'éval en `PENDING_INTERNAL_REVIEW`.
        Notifie le(s) admin(s) GCSMS (SUBMITTED).
        """
        self._require_permission(submitted_by, PERM_VALIDATION_SUBMIT)
        eval_obj = self._get_evaluation(evaluation_id)

        if eval_obj.status not in {EvaluationStatus.DRAFT, EvaluationStatus.IN_PROGRESS}:
            raise EvaluationNotSubmittableError(
                f"Évaluation #{evaluation_id} non soumissible depuis le statut "
                f"{eval_obj.status} (attendu DRAFT ou IN_PROGRESS)"
            )
        self._check_no_pending_for_evaluation(evaluation_id)

        now = datetime.now(UTC)
        vr = ValidationRequest(
            tenant_id=self.tenant_id,
            workflow_type=ValidationWorkflowType.AGGIR_FUNDING,
            evaluation_id=evaluation_id,
            stage=ValidationStage.INTERNAL_REVIEW,
            submitted_by_user_id=submitted_by.id,
            submitted_at=now,
            attachments=[],
            notes="",
        )
        self.db.add(vr)
        eval_obj.status = EvaluationStatus.PENDING_INTERNAL_REVIEW
        self.db.flush()  # vr.id requis pour audit + notification

        self._append_audit(vr, "SUBMIT_EVALUATION", submitted_by, payload.notes)
        self._append_exchange(
            vr,
            ExchangeActionType.SUBMIT,
            submitted_by,
            author_role="COORDINATOR",
            message=payload.notes,
        )
        self._notifications.notify_validation_event(vr, ValidationEvent.SUBMITTED, submitted_by)
        self.db.flush()
        return vr

    def resubmit_evaluation(
        self,
        evaluation_id: int,
        payload: ResubmitRequest,
        actor: User,
    ) -> ValidationRequest:
        """Re-soumet une évaluation renvoyée en interne par le médecin (R1).

        Cas couvert par R1 : l'éval est « garée » en `PENDING_INTERNAL_REVIEW`
        sans VR active, après qu'un valideur médical a renvoyé le dossier —
        que ce soit une demande de complément (`MORE_INFO_REQUESTED`) ou une
        invalidation (`INVALIDATED`) : les deux rebondissent en relecture interne
        (option A / R-T1). L'émetteur répond et ré-ouvre le cycle : nouvelle VR
        `INTERNAL_REVIEW` chaînée (`previous_vr_id`) à la dernière VR médicale
        décidée, exchange `RESUBMIT`, l'éval **reste** `PENDING_INTERNAL_REVIEW`.
        Émet l'événement `RESUBMITTED` (miroir de `SUBMITTED` — relecteur interne).

        Retourne la nouvelle VR interne (le « courant » est désormais elle).
        """
        self._require_permission(actor, PERM_VALIDATION_SUBMIT)
        eval_obj = self._get_evaluation(evaluation_id)

        if eval_obj.status != EvaluationStatus.PENDING_INTERNAL_REVIEW:
            raise EvaluationNotSubmittableError(
                f"Évaluation #{evaluation_id} non re-soumissible depuis le statut "
                f"{eval_obj.status} (R1 attend PENDING_INTERNAL_REVIEW)"
            )
        self._check_no_pending_for_evaluation(evaluation_id)

        previous_vr = self._last_decided_vr_for_evaluation(evaluation_id)

        now = datetime.now(UTC)
        vr = ValidationRequest(
            tenant_id=self.tenant_id,
            workflow_type=ValidationWorkflowType.AGGIR_FUNDING,
            evaluation_id=evaluation_id,
            stage=ValidationStage.INTERNAL_REVIEW,
            submitted_by_user_id=actor.id,
            submitted_at=now,
            previous_vr_id=previous_vr.id if previous_vr else None,
            attachments=[],
            notes="",
        )
        self.db.add(vr)
        # L'éval reste PENDING_INTERNAL_REVIEW : on ré-ouvre le cycle interne.
        self.db.flush()  # vr.id requis pour audit + notification

        self._append_audit(vr, "RESUBMIT_EVALUATION", actor, payload.notes)
        self._append_exchange(
            vr,
            ExchangeActionType.RESUBMIT,
            actor,
            author_role="COORDINATOR",
            message=payload.notes,
        )
        self._notifications.notify_validation_event(vr, ValidationEvent.RESUBMITTED, actor)
        self.db.flush()
        return vr

    def submit_care_plan(
        self,
        care_plan_id: int,
        payload: ValidationSubmitRequest,
        submitted_by: User,
    ) -> ValidationRequest:
        """Soumet un plan d'aide au workflow COORDINATION_DOSSIER (étape interne, terminale positive).

        Crée une VR `INTERNAL_REVIEW` et fait passer le plan en `PENDING_VALIDATION`.
        Notifie le(s) admin(s) GCSMS (SUBMITTED).
        """
        self._require_permission(submitted_by, PERM_VALIDATION_SUBMIT)
        plan = self._get_care_plan(care_plan_id)

        if plan.status != CarePlanStatus.DRAFT:
            raise CarePlanNotSubmittableError(
                f"Plan d'aide #{care_plan_id} non soumissible depuis le statut "
                f"{plan.status} (attendu DRAFT)"
            )
        self._check_no_pending_for_care_plan(care_plan_id)

        now = datetime.now(UTC)
        vr = ValidationRequest(
            tenant_id=self.tenant_id,
            workflow_type=ValidationWorkflowType.COORDINATION_DOSSIER,
            care_plan_id=care_plan_id,
            stage=ValidationStage.INTERNAL_REVIEW,
            submitted_by_user_id=submitted_by.id,
            submitted_at=now,
            attachments=[],
            notes="",
        )
        self.db.add(vr)
        plan.status = CarePlanStatus.PENDING_VALIDATION
        self.db.flush()

        self._append_audit(vr, "SUBMIT_CARE_PLAN", submitted_by, payload.notes)
        self._append_exchange(
            vr,
            ExchangeActionType.SUBMIT,
            submitted_by,
            author_role="COORDINATOR",
            message=payload.notes,
        )
        self._notifications.notify_validation_event(vr, ValidationEvent.SUBMITTED, submitted_by)
        self.db.flush()
        return vr

    # ------------------------------------------------------------------
    # API publique — transmissions externes (point 1 verrouillé Session 27)
    # ------------------------------------------------------------------

    def transmit_medical(
        self,
        vr_id: int,
        payload: ValidationTransmitRequest,
        actor: User,
    ) -> ValidationRequest:
        """Valide la relecture interne ET crée la VR médicale assignée (un seul acte).

        Workflow long uniquement. Clôt la VR `INTERNAL_REVIEW` avec
        `decision=VALIDATED` (validation interne absorbée dans la transmission),
        crée une nouvelle VR `MEDICAL_REVIEW` assignée au médecin choisi, et
        fait passer l'éval en `PENDING_MEDICAL`. Émet **un seul** événement
        `TRANSMITTED_MEDICAL` (pas de `DECIDED_VALIDATED` en doublon).

        Retourne la nouvelle VR médicale (le « courant » est désormais elle).
        """
        self._require_permission(actor, PERM_VALIDATION_INTERNAL_REVIEW)
        vr = self._get_or_404(vr_id)
        self._check_pending(vr)

        if vr.stage != ValidationStage.INTERNAL_REVIEW:
            raise IllegalTransitionError(
                f"transmit-medical exige stage=INTERNAL_REVIEW, reçu {vr.stage}"
            )
        if vr.workflow_type != ValidationWorkflowType.AGGIR_FUNDING:
            raise WorkflowMismatchError(
                "transmit-medical n'existe qu'en workflow long AGGIR_FUNDING"
            )
        self._check_anti_self(vr, actor)

        validator = self._get_validator(payload.assigned_validator_user_id)
        if validator.id == vr.submitted_by_user_id:
            raise SelfValidationError(
                "Anti-self-validation : le valideur médical assigné ne peut pas "
                "être l'auteur de la soumission initiale"
            )

        now = datetime.now(UTC)

        # 1. Clôture de la VR interne (validation absorbée)
        vr.decision = ValidationDecision.VALIDATED
        vr.decided_at = now
        vr.decided_by_user_id = actor.id
        self._append_audit(vr, "TRANSMIT_MEDICAL_CLOSE_INTERNAL", actor, payload.notes)

        # 2. Création de la VR médicale assignée
        new_vr = ValidationRequest(
            tenant_id=self.tenant_id,
            workflow_type=ValidationWorkflowType.AGGIR_FUNDING,
            evaluation_id=vr.evaluation_id,
            stage=ValidationStage.MEDICAL_REVIEW,
            submitted_by_user_id=actor.id,  # admin GCSMS devient soumetteur côté médecin
            submitted_at=now,
            assigned_validator_user_id=validator.id,
            previous_vr_id=vr.id,  # chaînage explicite du relais (B40-J3)
            attachments=[],
            notes="",
        )
        self.db.add(new_vr)

        # 3. Statut éval
        eval_obj = self._get_evaluation(vr.evaluation_id)
        eval_obj.status = EvaluationStatus.PENDING_MEDICAL

        self.db.flush()  # new_vr.id requis pour audit + notification
        self._append_audit(new_vr, "TRANSMIT_MEDICAL_CREATE", actor, payload.notes)
        self._append_exchange(
            new_vr,
            ExchangeActionType.TRANSMIT,
            actor,
            author_role="INTERNAL_VALIDATOR",
            message=payload.notes,
        )
        self._notifications.notify_validation_event(
            new_vr, ValidationEvent.TRANSMITTED_MEDICAL, actor
        )
        self.db.flush()
        return new_vr

    def transmit_funding(
        self,
        vr_id: int,
        payload: ValidationTransmitRequest,
        actor: User,
    ) -> ValidationRequest:
        """Valide la VR médicale ET crée la VR financement assignée (un seul acte).

        Workflow long uniquement. Mécanique miroir de `transmit_medical` :
        clôt la VR `MEDICAL_REVIEW` avec `decision=VALIDATED`, crée une nouvelle
        VR `FUNDING_REVIEW` assignée à l'agent département, fait passer l'éval
        en `AWAITING_FUNDING_DECISION`. Émet `TRANSMITTED_FUNDING`.
        """
        self._require_permission(actor, PERM_VALIDATION_MEDICAL_REVIEW)
        vr = self._get_or_404(vr_id)
        self._check_pending(vr)

        if vr.stage != ValidationStage.MEDICAL_REVIEW:
            raise IllegalTransitionError(
                f"transmit-funding exige stage=MEDICAL_REVIEW, reçu {vr.stage}"
            )
        if vr.workflow_type != ValidationWorkflowType.AGGIR_FUNDING:
            raise WorkflowMismatchError(
                "transmit-funding n'existe qu'en workflow long AGGIR_FUNDING"
            )
        self._check_anti_self(vr, actor)

        validator = self._get_validator(payload.assigned_validator_user_id)
        if validator.id == vr.submitted_by_user_id:
            raise SelfValidationError(
                "Anti-self-validation : l'agent département assigné ne peut pas "
                "être l'auteur de la transmission médicale"
            )

        now = datetime.now(UTC)

        vr.decision = ValidationDecision.VALIDATED
        vr.decided_at = now
        vr.decided_by_user_id = actor.id
        self._append_audit(vr, "TRANSMIT_FUNDING_CLOSE_MEDICAL", actor, payload.notes)

        new_vr = ValidationRequest(
            tenant_id=self.tenant_id,
            workflow_type=ValidationWorkflowType.AGGIR_FUNDING,
            evaluation_id=vr.evaluation_id,
            stage=ValidationStage.FUNDING_REVIEW,
            submitted_by_user_id=actor.id,
            submitted_at=now,
            assigned_validator_user_id=validator.id,
            previous_vr_id=vr.id,  # chaînage explicite du relais (B40-J3)
            attachments=[],
            notes="",
        )
        self.db.add(new_vr)

        eval_obj = self._get_evaluation(vr.evaluation_id)
        eval_obj.status = EvaluationStatus.AWAITING_FUNDING_DECISION

        self.db.flush()
        self._append_audit(new_vr, "TRANSMIT_FUNDING_CREATE", actor, payload.notes)
        self._append_exchange(
            new_vr,
            ExchangeActionType.TRANSMIT,
            actor,
            author_role="MEDICAL_VALIDATOR",
            message=payload.notes,
        )
        self._notifications.notify_validation_event(
            new_vr, ValidationEvent.TRANSMITTED_FUNDING, actor
        )
        self.db.flush()
        return new_vr

    # ------------------------------------------------------------------
    # API publique — decide (routage par stage × decision × workflow)
    # ------------------------------------------------------------------

    def decide(
        self,
        vr_id: int,
        payload: ValidationDecisionRequest,
        actor: User,
    ) -> ValidationRequest:
        """Acte une décision (VALIDATED, INVALIDATED, MORE_INFO_REQUESTED) sur une VR.

        Le routage `_route_decide` détermine selon `(stage, decision, workflow_type)`
        le nouveau statut de l'objet validable et l'événement à émettre. Décisions
        Session 27 :
        - Point 1 : `VALIDATED` sur INTERNAL_REVIEW en AGGIR_FUNDING → erreur
          (utiliser `transmit-medical`) ; sur MEDICAL_REVIEW → erreur (utiliser
          `transmit-funding`).
        - Point 2 / Option A : invalidation/MORE_INFO externe repasse par le GCSMS
          (MEDICAL → PENDING_INTERNAL_REVIEW ; FUNDING → PENDING_MEDICAL).
        - WITHDRAWN refusé au niveau schéma (model_validator) — passe par `/withdraw`.
        """
        vr = self._get_or_404(vr_id)
        self._check_pending(vr)

        perm_by_stage = {
            ValidationStage.INTERNAL_REVIEW: PERM_VALIDATION_INTERNAL_REVIEW,
            ValidationStage.MEDICAL_REVIEW: PERM_VALIDATION_MEDICAL_REVIEW,
            ValidationStage.FUNDING_REVIEW: PERM_VALIDATION_FUNDING_REVIEW,
        }
        self._require_permission(actor, perm_by_stage[vr.stage])
        self._check_anti_self(vr, actor)

        new_eval_status, new_plan_status, event = self._route_decide(vr, payload.decision)

        # Clôture de la VR
        now = datetime.now(UTC)
        vr.decision = payload.decision
        vr.decided_at = now
        vr.decided_by_user_id = actor.id
        vr.decision_motif = payload.decision_motif
        vr.invalidation_reason = payload.invalidation_reason
        vr.info_request_message = payload.info_request_message
        vr.decided_on_behalf_of = payload.decided_on_behalf_of
        if payload.attachments:
            vr.attachments = payload.attachments

        # Mise à jour du statut de l'objet validable
        if new_eval_status is not None:
            eval_obj = self._get_evaluation(vr.evaluation_id)
            eval_obj.status = new_eval_status
        if new_plan_status is not None:
            plan = self._get_care_plan(vr.care_plan_id)
            plan.status = new_plan_status

        self._append_audit(
            vr,
            f"DECIDE_{payload.decision.value}",
            actor,
            payload.decision_motif or payload.info_request_message,
        )
        # Fil structuré (B40-J3) : map décision → action_type + message pertinent
        _decision_to_action = {
            ValidationDecision.VALIDATED: ExchangeActionType.VALIDATE,
            ValidationDecision.INVALIDATED: ExchangeActionType.INVALIDATE,
            ValidationDecision.MORE_INFO_REQUESTED: ExchangeActionType.REQUEST_INFO,
        }
        _decision_to_message = {
            ValidationDecision.VALIDATED: payload.decision_motif,
            ValidationDecision.INVALIDATED: payload.decision_motif,
            ValidationDecision.MORE_INFO_REQUESTED: payload.info_request_message,
        }
        self._append_exchange(
            vr,
            _decision_to_action[payload.decision],
            actor,
            author_role=self._role_for_stage(vr.stage),
            message=_decision_to_message[payload.decision],
            attachments=payload.attachments or [],
        )
        if event is not None:
            self._notifications.notify_validation_event(vr, event, actor)
        self.db.flush()
        return vr

    def _route_decide(
        self,
        vr: ValidationRequest,
        decision: ValidationDecision,
    ) -> tuple[EvaluationStatus | None, CarePlanStatus | None, ValidationEvent | None]:
        """Routage `(stage, decision, workflow_type)` → (statut éval, statut plan, événement).

        Verrouillé Session 27 (points 1, 2 + Option A). Retourne `(None, None, None)`
        n'est jamais possible — les cas non routés lèvent `IllegalTransitionError`.
        """
        stage = vr.stage
        wf = vr.workflow_type

        if stage == ValidationStage.INTERNAL_REVIEW:
            if decision == ValidationDecision.VALIDATED:
                if wf == ValidationWorkflowType.AGGIR_FUNDING:
                    raise WorkflowMismatchError(
                        "decide(VALIDATED) interdit sur INTERNAL_REVIEW en workflow long : "
                        "l'avancée positive passe par transmit-medical (point 1, Session 27)"
                    )
                # COORDINATION_DOSSIER court — terminal positif
                return (None, CarePlanStatus.ACTIVE, ValidationEvent.DECIDED_VALIDATED)
            if decision == ValidationDecision.INVALIDATED:
                if wf == ValidationWorkflowType.AGGIR_FUNDING:
                    return (
                        EvaluationStatus.IN_PROGRESS,
                        None,
                        ValidationEvent.DECIDED_INVALIDATED,
                    )
                return (None, CarePlanStatus.DRAFT, ValidationEvent.DECIDED_INVALIDATED)
            if decision == ValidationDecision.MORE_INFO_REQUESTED:
                if wf == ValidationWorkflowType.AGGIR_FUNDING:
                    return (
                        EvaluationStatus.IN_PROGRESS,
                        None,
                        ValidationEvent.DECIDED_MORE_INFO,
                    )
                return (None, CarePlanStatus.DRAFT, ValidationEvent.DECIDED_MORE_INFO)

        if stage == ValidationStage.MEDICAL_REVIEW:
            # AGGIR_FUNDING uniquement (CHECK polymorphique en garde-fou DB)
            if decision == ValidationDecision.VALIDATED:
                raise WorkflowMismatchError(
                    "decide(VALIDATED) interdit sur MEDICAL_REVIEW : "
                    "utiliser transmit-funding (point 1, Session 27)"
                )
            # Option A : invalidation / MORE_INFO médicale → retour relecture interne
            if decision == ValidationDecision.INVALIDATED:
                return (
                    EvaluationStatus.PENDING_INTERNAL_REVIEW,
                    None,
                    ValidationEvent.DECIDED_INVALIDATED,
                )
            if decision == ValidationDecision.MORE_INFO_REQUESTED:
                return (
                    EvaluationStatus.PENDING_INTERNAL_REVIEW,
                    None,
                    ValidationEvent.DECIDED_MORE_INFO,
                )

        if stage == ValidationStage.FUNDING_REVIEW:
            if decision == ValidationDecision.VALIDATED:
                # Terminal positif du workflow long
                return (
                    EvaluationStatus.VALIDATED,
                    None,
                    ValidationEvent.DECIDED_VALIDATED,
                )
            if decision == ValidationDecision.INVALIDATED:
                # Refus terminal département (D9) — événement dédié pour notif médecin traitant (D11 v3)
                return (
                    EvaluationStatus.FUNDING_REJECTED,
                    None,
                    ValidationEvent.DECIDED_FUNDING_REJECTED,
                )
            if decision == ValidationDecision.MORE_INFO_REQUESTED:
                # D14 v2 : retour à l'étape immédiatement précédente, pas de retour amont
                return (
                    EvaluationStatus.PENDING_MEDICAL,
                    None,
                    ValidationEvent.DECIDED_MORE_INFO,
                )

        raise IllegalTransitionError(
            f"Décision {decision} non gérée à l'étape {stage} (workflow {wf})"
        )

    # ------------------------------------------------------------------
    # API publique — withdraw (D14 v2 : cycle interne uniquement)
    # ------------------------------------------------------------------

    def withdraw(
        self,
        vr_id: int,
        payload: ValidationWithdrawRequest,
        actor: User,
    ) -> ValidationRequest:
        """Retire une soumission (cycle interne uniquement, D14 v2).

        Règles : VR au stage `INTERNAL_REVIEW` + actor == submitter.
        Aucune notification (décision Session 27 — trace dans `vr.withdrawn_*`).
        Restaure l'objet validable en amont (éval → IN_PROGRESS, plan → DRAFT).
        """
        self._require_permission(actor, PERM_VALIDATION_WITHDRAW)
        vr = self._get_or_404(vr_id)
        self._check_pending(vr)

        if vr.stage != ValidationStage.INTERNAL_REVIEW:
            raise WithdrawNotAllowedError(
                "D14 v2 : retrait possible uniquement au cycle interne "
                f"(INTERNAL_REVIEW), VR actuellement {vr.stage}"
            )
        if vr.submitted_by_user_id != actor.id:
            raise WithdrawNotAllowedError(
                f"D14 v2 : seul l'auteur (#{vr.submitted_by_user_id}) peut retirer "
                f"cette soumission, acteur #{actor.id}"
            )

        now = datetime.now(UTC)
        vr.withdrawn_at = now
        vr.withdrawn_by_user_id = actor.id
        vr.withdrawal_reason = payload.withdrawal_reason

        # Restauration du statut amont
        if vr.workflow_type == ValidationWorkflowType.AGGIR_FUNDING:
            eval_obj = self._get_evaluation(vr.evaluation_id)
            eval_obj.status = EvaluationStatus.IN_PROGRESS
        else:
            plan = self._get_care_plan(vr.care_plan_id)
            plan.status = CarePlanStatus.DRAFT

        self._append_audit(vr, "WITHDRAW", actor, payload.withdrawal_reason)
        self._append_exchange(
            vr,
            ExchangeActionType.COMMENT,
            actor,
            author_role="COORDINATOR",
            message=payload.withdrawal_reason,
            visibility=ExchangeVisibility.INTERNAL_ONLY,  # retrait = acte interne
        )
        # Pas de notification (décision Session 27)
        self.db.flush()
        return vr

    # ------------------------------------------------------------------
    # API publique — mark_under_appeal (D21 : drapeau de recours)
    # ------------------------------------------------------------------

    def mark_under_appeal(
        self,
        evaluation_id: int,
        payload: MarkUnderAppealRequest,
        actor: User,
    ) -> PatientEvaluation:
        """Active le drapeau de recours sur une évaluation `FUNDING_REJECTED` (D21).

        Pas de workflow interne, pas de transition automatique — simple drapeau
        indicatif. Recours hors périmètre CareLink (procédure RAPO/TA réelle).
        """
        self._require_permission(actor, PERM_EVALUATION_CREATE)
        eval_obj = self._get_evaluation(evaluation_id)

        if eval_obj.status != EvaluationStatus.FUNDING_REJECTED:
            raise AppealNotAllowedError(
                f"D21 : drapeau de recours autorisé uniquement sur éval FUNDING_REJECTED, "
                f"statut courant {eval_obj.status}"
            )

        eval_obj.is_under_appeal = True
        eval_obj.appeal_notes = payload.appeal_notes
        self.db.flush()
        return eval_obj

    # ------------------------------------------------------------------
    # API publique — listing (consommé par GET /validation-requests)
    # ------------------------------------------------------------------

    def get_by_id(self, vr_id: int) -> ValidationRequest:
        """Charge une VR par id+tenant. La RLS SELECT filtre déjà par destinataire/émetteur/admin."""
        return self._get_or_404(vr_id)

    def list(
        self,
        filters: ValidationRequestFilters | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[ValidationRequest], int]:
        """Liste paginée des VR (ordre antéchronologique).

        Le filtrage par destinataire est porté par la policy RLS SELECT
        (émetteur + valideur assigné + admin du tenant — cf. cadrage §9.3).
        Les filtres applicatifs ci-dessous affinent à l'intérieur de cette
        visibilité RLS.
        """
        query = self._base_query()
        if filters is not None:
            if filters.workflow_type is not None:
                query = query.filter(ValidationRequest.workflow_type == filters.workflow_type)
            if filters.stage is not None:
                query = query.filter(ValidationRequest.stage == filters.stage)
            if filters.decision is not None:
                query = query.filter(ValidationRequest.decision == filters.decision)
            if filters.assigned_validator_user_id is not None:
                query = query.filter(
                    ValidationRequest.assigned_validator_user_id
                    == filters.assigned_validator_user_id
                )
            if filters.submitted_by_user_id is not None:
                query = query.filter(
                    ValidationRequest.submitted_by_user_id == filters.submitted_by_user_id
                )
            if filters.pending_only:
                query = query.filter(
                    ValidationRequest.decision.is_(None),
                    ValidationRequest.withdrawn_at.is_(None),
                )

        total = query.count()
        items = (
            query.order_by(ValidationRequest.created_at.desc())
            .offset(max(0, (page - 1) * size))
            .limit(max(1, size))
            .all()
        )
        return items, total

    # ------------------------------------------------------------------
    # Fil d'échange — lecture filtrée + commentaire manuel (B40-J3)
    # ------------------------------------------------------------------

    def _exchanges_base_query(self) -> Query[ValidationExchange]:
        """Requête de base sur `validation_exchanges`, filtrée par tenant (#97)."""
        return self.db.query(ValidationExchange).filter(
            ValidationExchange.tenant_id == self.tenant_id
        )

    def _actor_is_internal(self, actor: User, submitter_ids: set[int]) -> bool:
        """Détermine si l'acteur accède aux entrées `INTERNAL_ONLY` (A1 / D32).

        Règle verrouillée (session 30/05/2026) : l'interne GCSMS voit tout,
        l'externe (médecin, agent département, famille) ne voit que les entrées
        `SHARED_EXTERNAL`. « Interne » = détient la permission de relecture interne
        (`has_permission` prend déjà en compte le wildcard `ADMIN_FULL`), OU est
        l'émetteur d'une des VR du dossier (le soumetteur est interne par construction
        — c'est lui qui voit ses propres notes de retrait `INTERNAL_ONLY`).

        Le besoin-d'en-connaître est porté ICI, au service — jamais en RLS (D32).
        """
        if actor.has_permission(PERM_VALIDATION_INTERNAL_REVIEW):
            return True
        return actor.id in submitter_ids

    def _filtered_thread_query(
        self, vr_ids: list[int], can_see_internal: bool
    ) -> list[ValidationExchange]:
        """Charge les entrées des VR données, filtrées par visibilité, triées chrono."""
        query = self._exchanges_base_query().filter(
            ValidationExchange.validation_request_id.in_(vr_ids)
        )
        if not can_see_internal:
            query = query.filter(
                ValidationExchange.visibility == ExchangeVisibility.SHARED_EXTERNAL
            )
        return query.order_by(ValidationExchange.created_at.asc()).all()

    def list_exchanges(self, vr_id: int, actor: User) -> list[ValidationExchange]:
        """Fil d'une seule VR, filtré par visibilité selon le rôle de l'acteur (A1/D32).

        Lecture chronologique. `VALIDATION_VIEW` est gaté au router ; la RLS borne
        au tenant ; le filtrage `visibility` est appliqué ici.
        """
        vr = self._get_or_404(vr_id)
        can_internal = self._actor_is_internal(actor, {vr.submitted_by_user_id})
        return self._filtered_thread_query([vr.id], can_internal)

    def list_thread_for_evaluation(
        self, evaluation_id: int, actor: User
    ) -> list[ValidationExchange]:
        """Fil continu du dossier d'une évaluation (A2/A3 — workflow AGGIR_FUNDING).

        Agrège les entrées de TOUTES les VR du même `evaluation_id` (le chaînage
        `previous_vr_id` sert à l'affichage des séparateurs d'étape côté frontend,
        pas à la reconstruction ici). Filtrage `visibility` selon le rôle de l'acteur.
        """
        self._get_evaluation(evaluation_id)  # 404 si hors tenant
        vrs = self._base_query().filter(ValidationRequest.evaluation_id == evaluation_id).all()
        if not vrs:
            return []
        vr_ids = [vr.id for vr in vrs]
        submitter_ids = {vr.submitted_by_user_id for vr in vrs}
        can_internal = self._actor_is_internal(actor, submitter_ids)
        return self._filtered_thread_query(vr_ids, can_internal)

    def list_thread_for_care_plan(self, care_plan_id: int, actor: User) -> list[ValidationExchange]:
        """Fil continu du dossier d'un plan d'aide (A2/A3 — workflow COORDINATION_DOSSIER).

        Symétrique de `list_thread_for_evaluation` côté plan d'aide (typiquement une
        seule VR en workflow court, mais l'agrégation reste générique).
        """
        self._get_care_plan(care_plan_id)  # 404 si hors tenant
        vrs = self._base_query().filter(ValidationRequest.care_plan_id == care_plan_id).all()
        if not vrs:
            return []
        vr_ids = [vr.id for vr in vrs]
        submitter_ids = {vr.submitted_by_user_id for vr in vrs}
        can_internal = self._actor_is_internal(actor, submitter_ids)
        return self._filtered_thread_query(vr_ids, can_internal)

    # ------------------------------------------------------------------
    # Contexte dossier — bandeau patient + pipeline (S2 / décision D-α.2)
    # ------------------------------------------------------------------

    def _patient_identity(self, patient_id: int) -> dict[str, Any]:
        """Sous-ensemble d'identité patient déchiffré pour le bandeau du portail.

        Chemin de déchiffrement unique (décision S2-i / option b) : délégation à
        `PatientService.get_by_id_decrypted` — point d'entrée applicatif unique du
        déchiffrement PII (AES-256-GCM), plutôt qu'un appel en doublon de la
        primitive d'encryptor. Import local pour éviter tout cycle de module
        (idiome déjà en place pour les imports patient de ce service).

        Minimisation RGPD : seuls les 7 champs du bandeau sont retenus (identité +
        adresse + GIR) ; jamais NIR / INS / téléphone / email.
        """
        from app.api.v1.patient.services import PatientService

        decrypted = PatientService(self.db, self.tenant_id).get_by_id_decrypted(patient_id)
        return {
            key: decrypted.get(key)
            for key in (
                "first_name",
                "last_name",
                "birth_date",
                "address",
                "postal_code",
                "city",
                "current_gir",
            )
        }

    def get_dossier_context_for_evaluation(
        self, evaluation_id: int
    ) -> tuple[dict[str, Any], list[ValidationRequest]]:
        """Contexte dossier d'une évaluation (D-α.2 — workflow AGGIR_FUNDING).

        Agrégat porté côté backend (A0) : identité patient (bandeau) + ensemble
        ordonné des VR du dossier (pipeline d'étapes, n° de VR fiables — fini le
        best-effort par index côté frontend). 404 si l'évaluation est hors tenant.
        Les VR sont bornées par la RLS SELECT ; pas de filtrage visibilité ici
        (porté sur les entrées de fil, pas sur les VR elles-mêmes).
        """
        eval_obj = self._get_evaluation(evaluation_id)  # 404 si hors tenant
        identity = self._patient_identity(eval_obj.patient_id)
        requests = (
            self._base_query()
            .filter(ValidationRequest.evaluation_id == evaluation_id)
            .order_by(ValidationRequest.created_at.asc())
            .all()
        )
        return identity, requests

    def get_dossier_context_for_care_plan(
        self, care_plan_id: int
    ) -> tuple[dict[str, Any], list[ValidationRequest]]:
        """Contexte dossier d'un plan d'aide (D-α.2 — workflow COORDINATION_DOSSIER).

        Symétrique de `get_dossier_context_for_evaluation` côté plan d'aide.
        """
        plan = self._get_care_plan(care_plan_id)  # 404 si hors tenant
        identity = self._patient_identity(plan.patient_id)
        requests = (
            self._base_query()
            .filter(ValidationRequest.care_plan_id == care_plan_id)
            .order_by(ValidationRequest.created_at.asc())
            .all()
        )
        return identity, requests

    def add_comment(self, vr_id: int, payload: ExchangeCreate, actor: User) -> ValidationExchange:
        """Ajoute un commentaire manuel (`COMMENT`) au fil d'une VR (B40-J3).

        - Gating service `VALIDATION_VIEW` (#134 — commenter découle du droit de
          voir, D3.5 ; pas de permission distincte).
        - `author_role` figé : `COORDINATOR` si l'acteur est l'émetteur, sinon le
          rôle de l'étape courante (cohérent avec le mapping acte→entrée §4.11.1).
        - Garde-fou : un acteur externe ne peut pas poser une entrée `INTERNAL_ONLY`
          (elle lui serait invisible en relecture) — on retombe sur `SHARED_EXTERNAL`.
        - `flush()` (pas `commit()`, #97) : l'entrée obtient id + `created_at` pour
          la réponse ; le commit final est délégué à la dépendance FastAPI.
        """
        self._require_permission(actor, PERM_VALIDATION_VIEW)
        vr = self._get_or_404(vr_id)

        can_internal = self._actor_is_internal(actor, {vr.submitted_by_user_id})
        visibility = payload.visibility if can_internal else ExchangeVisibility.SHARED_EXTERNAL
        author_role = (
            "COORDINATOR" if vr.submitted_by_user_id == actor.id else self._role_for_stage(vr.stage)
        )

        exchange = self._append_exchange(
            vr,
            ExchangeActionType.COMMENT,
            actor,
            author_role=author_role,
            message=payload.message,
            visibility=visibility,
            attachments=payload.attachments or [],
        )
        self.db.flush()
        return exchange


# =============================================================================
# Suppression d'import non utilisé en fin de fichier
# =============================================================================
# Note : `UserTenantAssignment` importé en tête est volontairement réservé
# pour B40-J4/J5 (résolution des valideurs externes via assignment cross-tenant).
# Sera utilisé dès que les helpers _medical/_funding_validator_user_id
# s'étendront à la lookup par assignment et non plus seulement par VR antérieure.
_ = UserTenantAssignment
