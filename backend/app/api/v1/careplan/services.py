"""
Services métier pour le module CarePlan.

Contient la logique CRUD pour :
- CarePlanCRUDService (le service métier)
- CarePlanServiceCRUDService (services du plan)

Version multi-tenant : toutes les requêtes filtrent par tenant_id.
"""

import re
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.careplan.schemas import (
    CarePlanCreate,
    CarePlanFilters,
    CarePlanReplaceServicesRequest,
    CarePlanReviseRequest,
    CarePlanServiceCreate,
    CarePlanServiceUpdate,
    CarePlanUpdate,
    ServiceAssignment,
)
from app.models.careplan.care_plan import CarePlan
from app.models.careplan.care_plan_service import CarePlanService
from app.models.catalog.entity_service import EntityService
from app.models.catalog.service_template import ServiceTemplate
from app.models.enums import CarePlanStatus
from app.models.organization.entity import Entity
from app.models.patient.patient import Patient
from app.models.user.user import User

# 🆕 v4.37 — Déchiffrement noms patient sur CarePlanSummary (F8 brouillons)
from app.services.encryption import patient_encryptor


# =============================================================================
# HELPERS
# =============================================================================

# Pattern reconnaissant le suffixe canonique « (révision n°N) » en fin de titre.
# Tolère un espace avant la parenthèse (cas nominal) ou son absence (anomalie).
_REVISION_SUFFIX_RE = re.compile(r"\s*\(révision n°(\d+)\)$")


def _next_revision_title(parent_title: str) -> str:
    """Génère le titre d'une révision avec compteur incrémental (B55).

    Règles :
    - Si le titre parent porte déjà un suffixe « (révision n°N) », incrémenter N.
    - Sinon, le parent est considéré comme l'original ou un titre legacy →
      ajout de « (révision n°1) ».

    Exemples :
        « Plan aide Curie »                  → « Plan aide Curie (révision n°1) »
        « Plan aide Curie (révision n°1) »   → « Plan aide Curie (révision n°2) »
        « Plan aide Curie (révision n°7) »   → « Plan aide Curie (révision n°8) »

    Note legacy : un titre pré-B55 du type « ... (révision) » ou
    « ... (révision) (révision) » ne match pas la regex et reçoit
    « (révision n°1) » ajouté en fin. Comportement acceptable car les fixtures
    pré-B55 sont nettoyées en environnement de dev ; en production, ce cas
    n'apparaîtra que pour les plans antérieurs à la mise en service B55.
    """
    match = _REVISION_SUFFIX_RE.search(parent_title)
    if match:
        next_n = int(match.group(1)) + 1
        base = parent_title[: match.start()].rstrip()
        return f"{base} (révision n°{next_n})"
    return f"{parent_title} (révision n°1)"


# =============================================================================
# EXCEPTIONS
# =============================================================================


class CarePlanNotFoundError(Exception):
    """Plan d'aide non trouvé."""


class CarePlanServiceNotFoundError(Exception):
    """Service de plan non trouvé."""


class PatientNotFoundError(Exception):
    """Patient non trouvé."""


class EntityNotFoundError(Exception):
    """Entité non trouvée."""


class ServiceTemplateNotFoundError(Exception):
    """Service template non trouvé."""


class EntityServiceNotFoundError(Exception):
    """Offre entité non trouvée."""


class UserNotFoundError(Exception):
    """Utilisateur non trouvé."""


class CarePlanNotEditableError(Exception):
    """Le plan n'est pas modifiable."""


class CarePlanStatusError(Exception):
    """Erreur de statut du plan."""


class AssignmentStatusError(Exception):
    """Erreur de statut d'affectation."""


class DuplicateReferenceError(Exception):
    """Numéro de référence déjà existant."""


class CarePlanRevisionError(Exception):
    """Le plan parent ne peut pas être révisé (statut interdit ou règle métier B28b)."""


class PendingRevisionExistsError(Exception):
    """
    Une révision DRAFT existe déjà pour ce plan parent (B28c).

    Garde fail-fast en amont du partial unique index
    `uq_care_plans_pending_revision_parent`. Permet à l'API de retourner
    un 409 Conflict structuré avec l'ID du DRAFT existant pour que l'UI
    puisse rediriger l'IDEC vers le brouillon en cours plutôt que d'en
    démarrer un nouveau.

    Cf. note de cadrage B28 décision 38, contrainte symétrique de B28a.
    """

    def __init__(self, parent_id: int, existing_draft_id: int) -> None:
        self.parent_id = parent_id
        self.existing_draft_id = existing_draft_id
        super().__init__(
            f"Une révision en cours (brouillon #{existing_draft_id}) existe "
            f"déjà pour le plan #{parent_id}. Terminez ou supprimez-la avant "
            f"d'en démarrer une nouvelle."
        )


# =============================================================================
# CARE PLAN SERVICE (le service métier)
# =============================================================================


class CarePlanCRUDService:
    """
    Service pour la gestion des plans d'aide.

    Version multi-tenant : toutes les requêtes filtrent par tenant_id.
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec la session DB et le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant pour le filtrage multi-tenant
        """
        self.db = db
        self.tenant_id = tenant_id

    def _base_query(self):
        """Retourne une requête de base filtrée par tenant_id."""
        return select(CarePlan).where(CarePlan.tenant_id == self.tenant_id)

    def _verify_entity_service(self, entity_service_id: int) -> EntityService:
        """Vérifie qu'une offre entité existe et appartient au tenant."""
        query = select(EntityService).where(
            EntityService.id == entity_service_id, EntityService.tenant_id == self.tenant_id
        )
        entity_service = self.db.execute(query).scalar_one_or_none()
        if not entity_service:
            raise EntityServiceNotFoundError(f"Offre entité {entity_service_id} non trouvée")
        return entity_service

    def _attach_patient_names(self, plan: CarePlan) -> CarePlan:
        """🆕 v4.37 — Pose les noms patient déchiffrés en transient sur le plan.

        Pattern aligné convention #108 (attribut Python transitoire sur ORM,
        exposé via from_attributes=True / model_validate sans persistence DB).

        Anti-N+1 : suppose que `selectinload(CarePlan.patient)` a été appelé en
        amont par le caller. Si `plan.patient` est None (cas non-eager ou plan
        orphelin), pose des valeurs nulles plutôt que de lever.

        Utilisé par get_all() pour enrichir CarePlanSummary multi-patients
        (consommateur principal : F8 « Mes brouillons » centralisée, mais
        bénéficie aussi à CarePlanListPage qui peut désormais afficher le
        patient en colonne).
        """
        if plan.patient is not None:
            decrypted = patient_encryptor.decrypt_model(plan.patient)
            plan.patient_first_name = decrypted.get("first_name")
            plan.patient_last_name = decrypted.get("last_name")
        else:
            plan.patient_first_name = None
            plan.patient_last_name = None
        return plan

    @staticmethod
    def _attach_transient_defaults(plan: CarePlan) -> CarePlan:
        """Pose les attributs Python transient B28a/B28c avec valeurs par défaut.

        Convention #108 — Garantit la présence des attributs `has_pending_revision`,
        `pending_revision_draft_id`, `superseded_plan_id` sur l'objet ORM avant
        sérialisation Pydantic via `CarePlanResponse.model_validate(plan)`.
        Sans ces defaults, model_validate lèverait AttributeError sur les
        endpoints qui ne posent pas explicitement ces attributs (revise, create…).

        Idempotent : si la méthode appelante a déjà posé un override
        (ex. validate() pose superseded_plan_id à la vraie valeur en cas de
        transition auto B28a), `hasattr` est True et la valeur est préservée.

        Cf. commentaire L381-391 de app/models/careplan/care_plan.py qui
        justifie le pattern transient (vs @property) pour B28c.
        """
        if not hasattr(plan, "has_pending_revision"):
            plan.has_pending_revision = False
        if not hasattr(plan, "pending_revision_draft_id"):
            plan.pending_revision_draft_id = None
        if not hasattr(plan, "superseded_plan_id"):
            plan.superseded_plan_id = None
        # 🆕 v4.37 — Noms patient déchiffrés (pattern #108) — défaut à None pour
        # éviter AttributeError de Schema.model_validate sur les chemins qui ne
        # passent pas par get_all() avec selectinload(patient).
        if not hasattr(plan, "patient_first_name"):
            plan.patient_first_name = None
        if not hasattr(plan, "patient_last_name"):
            plan.patient_last_name = None
        return plan

    def get_all(
        self,
        page: int = 1,
        size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        filters: CarePlanFilters | None = None,
    ) -> tuple[list[CarePlan], int]:
        """Liste les plans d'aide avec pagination et filtres."""
        query = self._base_query().options(
            selectinload(CarePlan.services),
            selectinload(CarePlan.patient),  # 🆕 v4.37 — Anti-N+1 pour patient_first_name/last_name
        )

        if filters:
            if filters.patient_id:
                query = query.where(CarePlan.patient_id == filters.patient_id)

            if filters.entity_id:
                query = query.where(CarePlan.entity_id == filters.entity_id)

            if filters.status:
                query = query.where(CarePlan.status == CarePlanStatus(filters.status.upper()))

            if filters.start_date_from:
                query = query.where(CarePlan.start_date >= filters.start_date_from)

            if filters.start_date_to:
                query = query.where(CarePlan.start_date <= filters.start_date_to)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        # Tri
        order_column = getattr(CarePlan, sort_by, CarePlan.created_at)
        if sort_order.lower() == "desc":
            order_column = order_column.desc()
        query = query.order_by(order_column)

        # Pagination
        query = query.offset((page - 1) * size).limit(size)

        items = self.db.execute(query).scalars().unique().all()

        # Filtrer par is_fully_assigned si demandé (après chargement)
        if filters and filters.is_fully_assigned is not None:
            items = [p for p in items if p.is_fully_assigned == filters.is_fully_assigned]
            total = len(items)

        # 🆕 v4.37 — Enrichir chaque plan avec les noms patient déchiffrés (F8 brouillons).
        # Le selectinload(patient) ci-dessus garantit que plan.patient est chargé sans N+1.
        items = [self._attach_patient_names(p) for p in items]

        return list(items), total

    def get_by_id(self, plan_id: int) -> CarePlan:
        """Récupère un plan d'aide par son ID."""
        query = (
            self._base_query()
            .where(CarePlan.id == plan_id)
            .options(
                selectinload(CarePlan.services).selectinload(CarePlanService.service_template),
                selectinload(CarePlan.services).selectinload(CarePlanService.entity_service),
            )
        )
        plan = self.db.execute(query).scalar_one_or_none()
        if not plan:
            raise CarePlanNotFoundError(f"Plan d'aide {plan_id} non trouvé")

        # B28c/B51 — Calcul explicite des indicateurs transitoires via _base_query
        # (pattern aligné sur superseded_plan_id pour B28a, posé par validate()).
        # On évite la relation `revisions` lazy/selectinload : la sub-query
        # interne SQLAlchemy ne porte pas le filtre tenant explicite, et le
        # RLS PostgreSQL seul ne suffit pas dans certains contextes
        # post-transaction (rotation pool, fenêtre transactionnelle).
        # has_pending_revision et pending_revision_draft_id sont exposés sur
        # CarePlanResponse uniquement (pas CarePlanSummary), donc ce calcul
        # 1 query/appel détail ne risque pas de N+1 sur les listes paginées.
        pending_draft_query = (
            self._base_query()
            .where(
                CarePlan.supersedes_plan_id == plan.id,
                CarePlan.status.in_([CarePlanStatus.DRAFT, CarePlanStatus.PENDING_VALIDATION]),
            )
            .limit(1)
        )
        pending_draft = self.db.execute(pending_draft_query).scalar_one_or_none()
        plan.has_pending_revision = pending_draft is not None
        plan.pending_revision_draft_id = pending_draft.id if pending_draft else None

        return self._attach_transient_defaults(plan)

    def get_by_patient(self, patient_id: int) -> list[CarePlan]:
        """Récupère tous les plans d'un patient."""
        query = (
            self._base_query()
            .where(CarePlan.patient_id == patient_id)
            .options(selectinload(CarePlan.services))
            .order_by(CarePlan.created_at.desc())
        )

        return list(self.db.execute(query).scalars().unique().all())

    def create(
        self,
        data: CarePlanCreate,
        created_by: int,
    ) -> CarePlan:
        """Crée un nouveau plan d'aide."""
        # Vérifier que le patient existe et appartient au tenant
        patient_query = select(Patient).where(
            Patient.id == data.patient_id, Patient.tenant_id == self.tenant_id
        )
        patient = self.db.execute(patient_query).scalar_one_or_none()
        if not patient:
            raise PatientNotFoundError(f"Patient {data.patient_id} non trouvé")

        # Vérifier que l'entité existe et appartient au tenant
        entity_query = select(Entity).where(
            Entity.id == data.entity_id, Entity.tenant_id == self.tenant_id
        )
        entity = self.db.execute(entity_query).scalar_one_or_none()
        if not entity:
            raise EntityNotFoundError(f"Entité {data.entity_id} non trouvée")

        # Vérifier unicité du numéro de référence dans le tenant
        if data.reference_number:
            existing = self.db.execute(
                self._base_query().where(CarePlan.reference_number == data.reference_number)
            ).scalar_one_or_none()
            if existing:
                raise DuplicateReferenceError(
                    f"Le numéro de référence '{data.reference_number}' existe déjà"
                )

        # Créer le plan avec le tenant_id
        plan = CarePlan(
            tenant_id=self.tenant_id,
            patient_id=data.patient_id,
            entity_id=data.entity_id,
            source_evaluation_id=data.source_evaluation_id,
            title=data.title,
            reference_number=data.reference_number,
            start_date=data.start_date,
            end_date=data.end_date,
            total_hours_week=data.total_hours_week,
            gir_at_creation=data.gir_at_creation,
            budget_allocated=data.budget_allocated,
            notes=data.notes,
            status=CarePlanStatus.DRAFT,
            created_by=created_by,
        )

        self.db.add(plan)
        self.db.flush()

        # Ajouter les services initiaux si fournis
        if data.services:
            for service_data in data.services:
                # ServiceTemplate est global (pas de tenant_id)
                template = self.db.get(ServiceTemplate, service_data.service_template_id)
                if not template:
                    raise ServiceTemplateNotFoundError(
                        f"Service template {service_data.service_template_id} non trouvé"
                    )

                # Vérifier l'offre entité si fournie
                if service_data.entity_service_id:
                    self._verify_entity_service(service_data.entity_service_id)

                service = CarePlanService(
                    tenant_id=self.tenant_id,
                    care_plan_id=plan.id,
                    service_template_id=service_data.service_template_id,
                    entity_service_id=service_data.entity_service_id,
                    quantity_per_week=service_data.quantity_per_week,
                    frequency_type=service_data.frequency_type,
                    frequency_days=service_data.frequency_days,
                    preferred_time_start=service_data.preferred_time_start,
                    preferred_time_end=service_data.preferred_time_end,
                    duration_minutes=service_data.duration_minutes,
                    priority=service_data.priority,
                    special_instructions=service_data.special_instructions,
                )
                self.db.add(service)

        self.db.flush()
        return self._attach_transient_defaults(plan)

    def update(self, plan_id: int, data: CarePlanUpdate) -> CarePlan:
        """Met à jour un plan d'aide."""
        plan = self.get_by_id(plan_id)

        if not plan.is_editable:
            raise CarePlanNotEditableError(
                f"Le plan en statut '{plan.status.value}' ne peut pas être modifié"
            )

        update_data = data.model_dump(exclude_unset=True)

        # Vérifier unicité du numéro de référence si modifié (dans le tenant)
        if update_data.get("reference_number"):
            existing = self.db.execute(
                self._base_query().where(
                    CarePlan.reference_number == update_data["reference_number"],
                    CarePlan.id != plan_id,
                )
            ).scalar_one_or_none()
            if existing:
                raise DuplicateReferenceError(
                    f"Le numéro de référence '{update_data['reference_number']}' existe déjà"
                )

        for field, value in update_data.items():
            setattr(plan, field, value)

        self.db.flush()
        return self._attach_transient_defaults(plan)

    def delete(self, plan_id: int) -> None:
        """Supprime un plan d'aide (seulement si en brouillon)."""
        plan = self.get_by_id(plan_id)

        if plan.status != CarePlanStatus.DRAFT:
            raise CarePlanStatusError("Seul un plan en brouillon peut être supprimé")

        self.db.delete(plan)
        self.db.flush()

    # === Actions de workflow ===

    def submit_for_validation(self, plan_id: int) -> CarePlan:
        """Soumet le plan pour validation."""
        plan = self.get_by_id(plan_id)

        try:
            plan.submit_for_validation()
        except ValueError as e:
            raise CarePlanStatusError(str(e)) from e

        self.db.flush()
        return self._attach_transient_defaults(plan)

    def validate(self, plan_id: int, validated_by: int) -> CarePlan:
        """
        Valide le plan d'aide (DRAFT/PENDING_VALIDATION → ACTIVE).

        B28a — Garantie d'unicité du plan ACTIVE par patient.
        Avant de basculer le plan vers ACTIVE, détecte tout autre plan ACTIVE
        du même patient dans le tenant et le ferme automatiquement (statut
        COMPLETED + note d'audit). Cette transition automatique constitue la
        voie nominale ; l'index unique partiel `care_plans_active_unique_per_patient`
        sert de filet de dernier recours côté DB.

        Returns:
            Le plan validé. Si une transition auto a eu lieu, l'attribut
            transitoire `superseded_plan_id` est posé pour exposition au
            frontend (toast silencieux, décision 36).
        """
        plan = self.get_by_id(plan_id)

        # Vérifier que l'utilisateur existe et appartient au tenant
        user_query = select(User).where(User.id == validated_by, User.tenant_id == self.tenant_id)
        user = self.db.execute(user_query).scalar_one_or_none()

        if not user:
            raise UserNotFoundError(f"Utilisateur {validated_by} non trouvé")

        if plan.status not in (CarePlanStatus.DRAFT, CarePlanStatus.PENDING_VALIDATION):
            raise CarePlanStatusError(
                f"Le plan en statut '{plan.status.value}' ne peut pas être validé"
            )

        # B28a — Détection d'un autre plan ACTIVE pour ce patient (même tenant)
        active_query = self._base_query().where(
            CarePlan.patient_id == plan.patient_id,
            CarePlan.status == CarePlanStatus.ACTIVE,
            CarePlan.id != plan.id,
        )
        existing_active_plans = list(self.db.execute(active_query).scalars().all())

        # Fermeture automatique des plans ACTIVE concurrents (≤ 1 attendu en
        # régime nominal post-migration ; on supporte N par robustesse)
        superseded_id: int | None = None
        for old_plan in existing_active_plans:
            old_plan.complete(
                reason=f"Terminé automatiquement suite à activation du plan #{plan.id}"
            )
            if superseded_id is None:
                superseded_id = old_plan.id

        # Double flush : garantit que les UPDATE de fermeture partent à PG
        # AVANT l'UPDATE d'activation. Indispensable car l'index unique partiel
        # `care_plans_active_unique_per_patient` est évalué en fin de statement
        # (non DEFERRABLE) — un ordre inverse provoquerait IntegrityError.
        if existing_active_plans:
            self.db.flush()

        plan.validate(user)
        self.db.flush()

        # Attribut transitoire pour exposition au frontend (CarePlanResponse.superseded_plan_id)
        plan.superseded_plan_id = superseded_id
        return self._attach_transient_defaults(plan)

    def revise(
        self,
        parent_id: int,
        data: CarePlanReviseRequest,
        created_by: int,
    ) -> CarePlan:
        """
        Révise un plan d'aide en créant un nouveau DRAFT clone (B28b — Approche 4).

        Crée un nouveau plan en statut DRAFT à partir d'un plan parent,
        en clonant ses services et fréquences (sans les affectations).
        Le plan parent reste intact ; il sera fermé par B28a au moment où
        la révision sera validée (transition automatique vers ACTIVE).

        Règles métier (note de cadrage B28 §4) :
        - Le parent doit être en statut ACTIVE, SUSPENDED, ou COMPLETED le plus
          récent du patient (décision 27).
        - Les statuts DRAFT, PENDING_VALIDATION, CANCELLED ne sont jamais révisables.
        - Les COMPLETED non-récents (= un autre COMPLETED plus récent existe pour
          ce patient) ne sont pas révisables.

        Clonage (décision 28) :
        - Cloné : title (préfixé), entity_id, source_evaluation_id, gir_at_creation,
          budget_allocated, services (template + entity_service + fréquence + durée
          + jours + horaires + priorité + instructions).
        - Reset : status=DRAFT, validated_at=None, validated_by_id=None, reference_number=None.
        - Exclu : assigned_user_id, assignment_status, assigned_at, assigned_by_id
          sur chaque service. Pas de copie des ScheduledIntervention (cascade
          delete-orphan, repart vide par construction).

        Args:
            parent_id: ID du plan parent à réviser.
            data: Payload contenant revision_reason (obligatoire), revision_comment,
                  inherit_services, inherit_gir.
            created_by: ID de l'utilisateur qui crée la révision.

        Returns:
            Le nouveau plan DRAFT (avec ses services clonés si inherit_services=True).

        Raises:
            CarePlanNotFoundError: parent inexistant ou hors tenant.
            UserNotFoundError: created_by inexistant ou hors tenant.
            CarePlanRevisionError: parent en statut non révisable, ou
                COMPLETED non-récent.
        """
        # Charger le plan parent (avec services pour le clonage)
        parent = self.get_by_id(parent_id)

        # Vérifier que l'utilisateur appartient au tenant
        user_query = select(User).where(User.id == created_by, User.tenant_id == self.tenant_id)
        user = self.db.execute(user_query).scalar_one_or_none()
        if not user:
            raise UserNotFoundError(f"Utilisateur {created_by} non trouvé")

        # Règles d'éligibilité du parent (décision 27)
        revisable_statuses = (
            CarePlanStatus.ACTIVE,
            CarePlanStatus.SUSPENDED,
            CarePlanStatus.COMPLETED,
        )
        if parent.status not in revisable_statuses:
            raise CarePlanRevisionError(
                f"Le plan en statut '{parent.status.value}' ne peut pas être révisé. "
                f"Statuts révisables : ACTIVE, SUSPENDED, COMPLETED le plus récent."
            )

        # Cas COMPLETED : ne révisable que s'il est le plus récent COMPLETED du patient
        if parent.status == CarePlanStatus.COMPLETED:
            more_recent_query = (
                self._base_query()
                .where(
                    CarePlan.patient_id == parent.patient_id,
                    CarePlan.status == CarePlanStatus.COMPLETED,
                    CarePlan.created_at > parent.created_at,
                    CarePlan.id != parent.id,
                )
                .limit(1)
            )
            more_recent = self.db.execute(more_recent_query).scalar_one_or_none()
            if more_recent is not None:
                raise CarePlanRevisionError(
                    f"Le plan COMPLETED #{parent.id} n'est pas le plus récent "
                    f"du patient (plan #{more_recent.id} plus récent existe). "
                    f"Seul le COMPLETED le plus récent est révisable."
                )

        # B28c — Unicité : interdire les révisions concurrentes (décision 38).
        # Filet de sécurité ultime côté DB via partial unique index
        # uq_care_plans_pending_revision_parent ; ce check fail-fast permet
        # un 409 structuré avec l'ID du DRAFT existant, exploité par l'UI
        # pour orienter l'IDEC vers le brouillon en cours.
        existing_draft_query = (
            self._base_query()
            .where(
                CarePlan.supersedes_plan_id == parent.id,
                CarePlan.status.in_([CarePlanStatus.DRAFT, CarePlanStatus.PENDING_VALIDATION]),
            )
            .limit(1)
        )
        existing_draft = self.db.execute(existing_draft_query).scalar_one_or_none()
        if existing_draft is not None:
            raise PendingRevisionExistsError(
                parent_id=parent.id,
                existing_draft_id=existing_draft.id,
            )

        # Note d'audit grep-able dans le nouveau plan DRAFT (convention #109)
        audit_note = (
            f"[RÉVISION B28b {datetime.now(UTC).isoformat()}] "
            f"Plan révisé issu de #{parent.id}, motif: {data.revision_reason.value}"
        )
        if data.revision_comment:
            audit_note += f"\nCommentaire: {data.revision_comment}"

        # Construire le nouveau plan DRAFT (clone-into-DRAFT, décision arbitrée Jalon 1)
        new_plan = CarePlan(
            tenant_id=self.tenant_id,
            patient_id=parent.patient_id,
            entity_id=parent.entity_id,
            source_evaluation_id=parent.source_evaluation_id,
            title=_next_revision_title(parent.title),
            reference_number=None,  # Reset — saisie manuelle si besoin
            start_date=parent.start_date,
            end_date=parent.end_date,
            total_hours_week=parent.total_hours_week,
            gir_at_creation=parent.gir_at_creation,
            budget_allocated=parent.budget_allocated,
            notes=audit_note,
            status=CarePlanStatus.DRAFT,
            created_by=created_by,
            # B28b — Filiation
            supersedes_plan_id=parent.id,
            revision_reason=data.revision_reason,
            revision_comment=data.revision_comment,
            gir_inherited_from_evaluation_id=(
                parent.source_evaluation_id if data.inherit_gir else None
            ),
        )

        self.db.add(new_plan)
        self.db.flush()

        # Cloner les services si demandé (décision 28)
        if data.inherit_services and parent.services:
            for parent_svc in parent.services:
                new_svc = CarePlanService(
                    tenant_id=self.tenant_id,
                    care_plan_id=new_plan.id,
                    service_template_id=parent_svc.service_template_id,
                    entity_service_id=parent_svc.entity_service_id,
                    quantity_per_week=parent_svc.quantity_per_week,
                    frequency_type=parent_svc.frequency_type,
                    frequency_days=parent_svc.frequency_days,
                    preferred_time_start=parent_svc.preferred_time_start,
                    preferred_time_end=parent_svc.preferred_time_end,
                    duration_minutes=parent_svc.duration_minutes,
                    priority=parent_svc.priority,
                    special_instructions=parent_svc.special_instructions,
                    # Champs explicitement EXCLUS du clonage (décision 28) :
                    # - assigned_user_id : repart à NULL
                    # - assignment_status : default UNASSIGNED
                    # - assigned_at, assigned_by_id : NULL
                    # - status : default ACTIVE (du modèle CarePlanService)
                )
                self.db.add(new_svc)

        self.db.flush()
        return self._attach_transient_defaults(new_plan)

    def replace_services(
        self,
        plan_id: int,
        data: CarePlanReplaceServicesRequest,
    ) -> CarePlan:
        """
        Remplace l'intégralité du panier de services d'un plan DRAFT.

        Sémantique « delete-all + insert-all » en une seule transaction
        SQLAlchemy. La cohérence atomique est garantie par la transaction
        du get_db() (convention #97 : commit en dépendance, pas en service).

        Cas d'usage principal : sauvegarde d'une révision (B28b/B28c) où
        l'IDEC a ajouté/retiré/modifié des prestations dans le wizard avant
        soumission. Cf. F6.6 du chantier B28.

        Pourquoi DRAFT strict (et pas is_editable) :
            is_editable autorise aussi PENDING_VALIDATION. Or à ce stade
            le plan est soumis au médecin pour validation — modifier son
            contenu reviendrait à perturber un workflow médical en cours.
            Le DRAFT strict impose à l'IDEC de repasser explicitement le
            plan en DRAFT avant édition.

        Pas de note d'audit timestampée (convention #109) :
            Replace-services est une édition de brouillon, pas un événement
            métier majeur (contrairement à revise/validate/cancel).
            L'audit du contenu finalisé se fait au /submit.

        Args:
            plan_id: ID du plan DRAFT à modifier.
            data: Payload contenant la liste cible complète des services.

        Returns:
            Le plan rechargé avec ses nouveaux services.

        Raises:
            CarePlanNotFoundError: plan inexistant ou hors tenant.
            CarePlanNotEditableError: plan dans un statut autre que DRAFT.
                Garde-fou anti delete-all destructeur sur les plans actifs.
            ServiceTemplateNotFoundError: si l'un des service_template_id
                référencés est introuvable. Levée AVANT le delete-all pour
                ne pas laisser le plan dans un état partiel.
            EntityServiceNotFoundError: idem pour entity_service_id.
        """
        plan = self.get_by_id(plan_id)

        if plan.status != CarePlanStatus.DRAFT:
            raise CarePlanNotEditableError(
                f"Le plan en statut '{plan.status.value}' ne peut pas faire "
                f"l'objet d'un remplacement complet du panier. Seuls les plans "
                f"en DRAFT sont éligibles."
            )

        # Fail-fast : valider toutes les références AVANT le delete-all
        # pour éviter de laisser le plan dans un état partiel si une
        # référence est invalide.
        #
        # Note : ServiceTemplate est un référentiel national partagé entre
        # tous les tenants (catalogue SERAFIN-PH) — PAS de filtre tenant_id.
        # Cf. architecture multi-tenant : modèles ServiceTemplate, Profession,
        # Country, Role n'ont pas tenant_id. L'isolation est garantie en aval
        # par EntityService (tenant-scoped) qui référence le template.
        for svc_data in data.services:
            template_query = select(ServiceTemplate).where(
                ServiceTemplate.id == svc_data.service_template_id,
            )
            if self.db.execute(template_query).scalar_one_or_none() is None:
                raise ServiceTemplateNotFoundError(
                    f"Service template {svc_data.service_template_id} non trouvé"
                )
            if svc_data.entity_service_id is not None:
                self._verify_entity_service(svc_data.entity_service_id)

        # Delete-all : effacer tous les services existants du plan
        delete_stmt = delete(CarePlanService).where(
            CarePlanService.care_plan_id == plan.id,
            CarePlanService.tenant_id == self.tenant_id,
        )
        self.db.execute(delete_stmt)

        # Insert-all : créer les nouveaux services depuis le payload
        for svc_data in data.services:
            new_svc = CarePlanService(
                tenant_id=self.tenant_id,
                care_plan_id=plan.id,
                service_template_id=svc_data.service_template_id,
                entity_service_id=svc_data.entity_service_id,
                quantity_per_week=svc_data.quantity_per_week,
                frequency_type=svc_data.frequency_type,
                frequency_days=svc_data.frequency_days,
                preferred_time_start=svc_data.preferred_time_start,
                preferred_time_end=svc_data.preferred_time_end,
                duration_minutes=svc_data.duration_minutes,
                priority=svc_data.priority,
                special_instructions=svc_data.special_instructions,
                # Champs explicitement EXCLUS (cohérent avec le clonage
                # de revise() — décision 28) :
                # - assigned_user_id : repart à NULL (default)
                # - assignment_status : default UNASSIGNED
                # - assigned_at, assigned_by_id : NULL (defaults)
                # - status : default ACTIVE (du modèle CarePlanService)
            )
            self.db.add(new_svc)

        self.db.flush()

        # Recharger le plan avec ses nouveaux services à jour
        return self.get_by_id(plan.id)

    def suspend(self, plan_id: int, reason: str | None = None) -> CarePlan:
        """Suspend le plan d'aide."""
        plan = self.get_by_id(plan_id)

        if plan.status != CarePlanStatus.ACTIVE:
            raise CarePlanStatusError("Seul un plan actif peut être suspendu")

        plan.suspend(reason)
        self.db.flush()
        return self._attach_transient_defaults(plan)

    def reactivate(self, plan_id: int) -> CarePlan:
        """Réactive un plan suspendu."""
        plan = self.get_by_id(plan_id)

        try:
            plan.reactivate()
        except ValueError as e:
            raise CarePlanStatusError(str(e)) from e

        self.db.flush()
        return self._attach_transient_defaults(plan)

    def complete(self, plan_id: int) -> CarePlan:
        """Marque le plan comme terminé."""
        plan = self.get_by_id(plan_id)
        plan.complete()
        self.db.flush()
        return self._attach_transient_defaults(plan)

    def cancel(self, plan_id: int, reason: str | None = None) -> CarePlan:
        """Annule le plan d'aide."""
        plan = self.get_by_id(plan_id)
        plan.cancel(reason)
        self.db.flush()
        return self._attach_transient_defaults(plan)


# =============================================================================
# CARE PLAN SERVICE SERVICE (services du plan)
# =============================================================================


class CarePlanServiceCRUDService:
    """
    Service pour la gestion des services de plan d'aide.

    Version multi-tenant : toutes les requêtes filtrent par tenant_id.
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec la session DB et le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant pour le filtrage multi-tenant
        """
        self.db = db
        self.tenant_id = tenant_id

    def _base_query(self):
        """Retourne une requête de base filtrée par tenant_id."""
        return select(CarePlanService).where(CarePlanService.tenant_id == self.tenant_id)

    def get_all_for_plan(self, plan_id: int) -> list[CarePlanService]:
        """Liste les services d'un plan."""
        query = (
            self._base_query()
            .where(CarePlanService.care_plan_id == plan_id)
            .options(
                selectinload(CarePlanService.service_template),
                selectinload(CarePlanService.entity_service),
            )
            .order_by(CarePlanService.id)
        )

        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, service_id: int) -> CarePlanService:
        """Récupère un service par son ID."""
        query = (
            self._base_query()
            .where(CarePlanService.id == service_id)
            .options(
                selectinload(CarePlanService.service_template),
                selectinload(CarePlanService.entity_service),
            )
        )
        service = self.db.execute(query).scalar_one_or_none()
        if not service:
            raise CarePlanServiceNotFoundError(f"Service {service_id} non trouvé")
        return service

    def create(
        self,
        plan_id: int,
        data: CarePlanServiceCreate,
    ) -> CarePlanService:
        """Ajoute un service à un plan."""
        # Vérifier que le plan existe, appartient au tenant et est éditable
        plan_query = select(CarePlan).where(
            CarePlan.id == plan_id, CarePlan.tenant_id == self.tenant_id
        )
        plan = self.db.execute(plan_query).scalar_one_or_none()
        if not plan:
            raise CarePlanNotFoundError(f"Plan {plan_id} non trouvé")

        if not plan.is_editable:
            raise CarePlanNotEditableError(
                f"Le plan en statut '{plan.status.value}' ne peut pas être modifié"
            )

        # ServiceTemplate est global (pas de tenant_id)
        template = self.db.get(ServiceTemplate, data.service_template_id)
        if not template:
            raise ServiceTemplateNotFoundError(
                f"Service template {data.service_template_id} non trouvé"
            )

        # Vérifier l'offre entité si fournie
        if data.entity_service_id:
            es_query = select(EntityService).where(
                EntityService.id == data.entity_service_id,
                EntityService.tenant_id == self.tenant_id,
            )
            entity_service = self.db.execute(es_query).scalar_one_or_none()
            if not entity_service:
                raise EntityServiceNotFoundError(
                    f"Offre entité {data.entity_service_id} non trouvée"
                )

        service = CarePlanService(
            tenant_id=self.tenant_id,
            care_plan_id=plan_id,
            service_template_id=data.service_template_id,
            entity_service_id=data.entity_service_id,
            quantity_per_week=data.quantity_per_week,
            frequency_type=data.frequency_type,
            frequency_days=data.frequency_days,
            preferred_time_start=data.preferred_time_start,
            preferred_time_end=data.preferred_time_end,
            duration_minutes=data.duration_minutes,
            priority=data.priority,
            special_instructions=data.special_instructions,
        )

        self.db.add(service)
        self.db.flush()
        return service

    def update(
        self,
        service_id: int,
        data: CarePlanServiceUpdate,
    ) -> CarePlanService:
        """Met à jour un service de plan."""
        service = self.get_by_id(service_id)

        # Vérifier que le plan est éditable
        plan_query = select(CarePlan).where(
            CarePlan.id == service.care_plan_id, CarePlan.tenant_id == self.tenant_id
        )
        plan = self.db.execute(plan_query).scalar_one_or_none()
        if plan and not plan.is_editable:
            raise CarePlanNotEditableError(
                f"Le plan en statut '{plan.status.value}' ne peut pas être modifié"
            )

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(service, field, value)

        self.db.flush()
        return service

    def delete(self, service_id: int) -> None:
        """Supprime un service de plan."""
        service = self.get_by_id(service_id)

        # Vérifier que le plan est éditable
        plan_query = select(CarePlan).where(
            CarePlan.id == service.care_plan_id, CarePlan.tenant_id == self.tenant_id
        )
        plan = self.db.execute(plan_query).scalar_one_or_none()
        if plan and not plan.is_editable:
            raise CarePlanNotEditableError(
                f"Le plan en statut '{plan.status.value}' ne peut pas être modifié"
            )

        self.db.delete(service)
        self.db.flush()

    # === Affectation ===

    def assign(
        self,
        service_id: int,
        data: ServiceAssignment,
        assigned_by: int,
    ) -> CarePlanService:
        """Affecte un service à un professionnel."""
        service = self.get_by_id(service_id)

        # Vérifier que l'utilisateur à affecter appartient au tenant
        user_query = select(User).where(User.id == data.user_id, User.tenant_id == self.tenant_id)
        user = self.db.execute(user_query).scalar_one_or_none()
        if not user:
            raise UserNotFoundError(f"Utilisateur {data.user_id} non trouvé")

        # Vérifier que l'assigneur appartient au tenant
        assigner_query = select(User).where(
            User.id == assigned_by, User.tenant_id == self.tenant_id
        )
        assigner = self.db.execute(assigner_query).scalar_one_or_none()
        if not assigner:
            raise UserNotFoundError(f"Utilisateur {assigned_by} non trouvé")

        if data.mode == "assign":
            service.assign_to(user, assigner)
        else:
            service.propose_to(user, assigner)

        self.db.flush()
        return service

    def unassign(self, service_id: int) -> CarePlanService:
        """Retire l'affectation d'un service."""
        service = self.get_by_id(service_id)
        service.unassign()
        self.db.flush()
        return service

    def confirm_assignment(self, service_id: int) -> CarePlanService:
        """Confirme l'affectation (acceptée par le professionnel)."""
        service = self.get_by_id(service_id)

        try:
            service.confirm_assignment()
        except ValueError as e:
            raise AssignmentStatusError(str(e)) from e

        self.db.flush()
        return service

    def reject_assignment(self, service_id: int) -> CarePlanService:
        """Rejette l'affectation (refusée par le professionnel)."""
        service = self.get_by_id(service_id)

        try:
            service.reject_assignment()
        except ValueError as e:
            raise AssignmentStatusError(str(e)) from e

        self.db.flush()
        return service
