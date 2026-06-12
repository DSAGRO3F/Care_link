"""
Modèle CarePlan - Plans d'aide patient.

Ce module définit la table `care_plans` qui représente le plan d'aide global
d'un patient, issu d'une évaluation, regroupant l'ensemble des services
nécessaires à son maintien à domicile.

Un plan d'aide contient :
- Les références au patient et à l'évaluation source
- La liste des services nécessaires (via care_plan_services)
- Le statut de validation et d'exécution
- La volumétrie prévisionnelle (heures/semaine)
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.enums import CarePlanStatus, RevisionReason
from app.models.mixins import AuditMixin, TimestampMixin


if TYPE_CHECKING:
    from app.models.careplan.care_plan_service import CarePlanService
    from app.models.organization.entity import Entity
    from app.models.patient.patient import Patient
    from app.models.patient.patient_evaluation import PatientEvaluation
    from app.models.user.user import User


class CarePlan(TimestampMixin, AuditMixin, Base):
    """
    Plan d'aide d'un patient.

    Représente le plan global de prise en charge issu d'une évaluation,
    regroupant l'ensemble des services nécessaires avec leurs fréquences.

    Lifecycle:
        DRAFT → PENDING_VALIDATION → ACTIVE → COMPLETED
                                  ↘ SUSPENDED ↗
                                  ↘ CANCELLED

    Attributes:
        id: Identifiant unique
        patient_id: Patient concerné
        source_evaluation_id: Évaluation à l'origine du plan
        entity_id: Entité responsable de la coordination
        title: Titre du plan
        reference_number: Numéro de référence unique
        status: Statut du plan
        start_date: Date de début
        end_date: Date de fin prévue
        total_hours_week: Total heures/semaine prévu
        gir_at_creation: GIR du patient à la création du plan
        validated_by_id: Utilisateur ayant validé
        validated_at: Date de validation
        notes: Observations générales

    Example:
        >>> care_plan = CarePlan(
        ...     patient_id=patient.id,
        ...     entity_id=ssiad.id,
        ...     title="Plan d'aide 2024",
        ...     status=CarePlanStatus.DRAFT,
        ...     start_date=date.today(),
        ... )
    """

    __tablename__ = "care_plans"
    __table_args__ = {"comment": "Plans d'aide patients"}

    # === Clé primaire ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du plan d'aide",
        info={"description": "Clé primaire auto-incrémentée"},
    )

    # === Multi-tenant ===

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant propriétaire de cet enregistrement",
    )

    # === Références ===

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Patient concerné par ce plan",
        info={"description": "FK vers patients. Suppression en cascade", "example": 1},
    )

    source_evaluation_id: Mapped[int | None] = mapped_column(
        ForeignKey("patient_evaluations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Évaluation à l'origine du plan",
        info={"description": "FK vers patient_evaluations. L'évaluation ayant conduit à ce plan"},
    )

    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Entité responsable de la coordination",
        info={"description": "FK vers entities. Structure coordinatrice du plan", "example": 1},
    )

    # === Identification ===

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Titre du plan d'aide",
        info={
            "description": "Titre descriptif du plan",
            "example": "Plan d'aide 2024 - Maintien à domicile",
        },
    )

    reference_number: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        doc="Numéro de référence unique",
        info={
            "description": "Référence administrative unique (format libre)",
            "example": "PA-2024-00123",
        },
    )

    # === Statut ===

    status: Mapped[CarePlanStatus] = mapped_column(
        SQLEnum(CarePlanStatus, name="care_plan_status_enum", create_constraint=True),
        nullable=False,
        default=CarePlanStatus.DRAFT,
        index=True,
        doc="Statut du plan d'aide",
        info={
            "description": "État actuel du plan dans son cycle de vie",
            "enum": [e.value for e in CarePlanStatus],
            "default": "DRAFT",
        },
    )

    # === Période ===

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="Date de début du plan",
        info={
            "description": "Date à partir de laquelle le plan est effectif",
            "example": "2024-01-01",
        },
    )

    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        doc="Date de fin prévue du plan",
        info={
            "description": "Date de fin prévue. NULL = durée indéterminée",
            "example": "2024-12-31",
        },
    )

    # === Volumétrie ===

    total_hours_week: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        doc="Total d'heures par semaine prévu",
        info={
            "description": "Volume horaire hebdomadaire prévu pour l'ensemble des services",
            "unit": "heures/semaine",
            "example": "12.50",
        },
    )

    gir_at_creation: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Score GIR du patient à la création du plan",
        info={
            "description": "Niveau GIR (1-6) issu de l'évaluation source",
            "min": 1,
            "max": 6,
            "example": 4,
        },
    )

    # === Budget ===

    budget_allocated: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        doc="Plafond budgétaire alloué au plan",
        info={
            "description": "Montant plafond saisi par le coordinateur (APA, PCH, autre)",
            "unit": "euros",
            "example": "1250.00",
        },
    )

    # === Validation ===

    validated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Utilisateur ayant validé le plan",
        info={"description": "FK vers users. Coordinateur ou médecin validateur"},
    )

    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date et heure de validation",
        info={"description": "Timestamp de validation du plan"},
    )

    # === Notes ===

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Observations générales sur le plan",
        info={"description": "Notes libres, contexte, recommandations particulières"},
    )

    # === B28b — Filiation plan d'aide (révision de plan) ===

    supersedes_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("care_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Plan parent dont celui-ci est une révision (B28b)",
        info={
            "description": "FK self-référentielle vers care_plans. NULL pour les plans "
            "créés ex nihilo, renseigné pour les plans issus d'un POST /revise. "
            "ON DELETE SET NULL : la suppression du parent ne casse pas la révision.",
            "example": 7,
        },
    )

    revision_reason: Mapped[RevisionReason | None] = mapped_column(
        SQLEnum(RevisionReason, name="revision_reason_enum", create_constraint=True),
        nullable=True,
        doc="Motif de révision (B28b)",
        info={
            "description": "Motif obligatoire à la création d'une révision via /revise, "
            "NULL pour les plans non issus d'une révision. Enum v1 — note de cadrage B28 §5.1.",
            "enum": [e.value for e in RevisionReason],
        },
    )

    revision_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Commentaire libre du coordinateur sur la révision (B28b)",
        info={
            "description": "Précision libre saisie au moment de la révision. "
            "Particulièrement utile quand revision_reason = OTHER.",
            "max_length": 1000,
        },
    )

    gir_inherited_from_evaluation_id: Mapped[int | None] = mapped_column(
        ForeignKey("patient_evaluations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Évaluation source du GIR hérité en cas de révision sans nouvelle évaluation (B28b)",
        info={
            "description": "FK vers patient_evaluations. Renseigné automatiquement par "
            "le service revise() : `parent.source_evaluation_id` si l'IDEC ne référence pas "
            "de nouvelle évaluation. Garantit la traçabilité AGGIR (décision 24, note de "
            "cadrage §3.2). ON DELETE SET NULL : pas de cascade, l'évaluation peut "
            "disparaître sans casser le plan.",
            "example": 12,
        },
    )

    # === Relations ===

    patient: Mapped[Patient] = relationship(
        "Patient", back_populates="care_plans", doc="Patient concerné par ce plan"
    )

    source_evaluation: Mapped[PatientEvaluation | None] = relationship(
        "PatientEvaluation",
        back_populates="care_plans",
        foreign_keys=[source_evaluation_id],
        doc="Évaluation source ayant généré ce plan",
    )

    entity: Mapped[Entity] = relationship(
        "Entity", back_populates="care_plans", doc="Entité responsable de la coordination"
    )

    validated_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[validated_by_id],
        back_populates="validated_care_plans",
        doc="Utilisateur ayant validé le plan",
    )

    services: Mapped[list[CarePlanService]] = relationship(
        "CarePlanService",
        back_populates="care_plan",
        cascade="all, delete-orphan",
        order_by="CarePlanService.id",
        doc="Services composant ce plan d'aide",
    )

    # === B28b — Relations de filiation ===

    supersedes_plan: Mapped[CarePlan | None] = relationship(
        "CarePlan",
        remote_side=[id],
        back_populates="revisions",
        foreign_keys=[supersedes_plan_id],
        doc="Plan parent dont celui-ci est une révision (B28b)",
    )

    revisions: Mapped[list[CarePlan]] = relationship(
        "CarePlan",
        back_populates="supersedes_plan",
        foreign_keys="[CarePlan.supersedes_plan_id]",
        order_by="CarePlan.created_at",
        doc="Liste des révisions issues de ce plan (B28b)",
    )

    # === Méthodes ===

    def __repr__(self) -> str:
        return (
            f"<CarePlan(id={self.id}, patient_id={self.patient_id}, status='{self.status.value}')>"
        )

    def __str__(self) -> str:
        return f"{self.title} ({self.status.value})"

    @property
    def is_active(self) -> bool:
        """Indique si le plan est actuellement actif."""
        return self.status == CarePlanStatus.ACTIVE

    @property
    def is_draft(self) -> bool:
        """Indique si le plan est en brouillon."""
        return self.status == CarePlanStatus.DRAFT

    @property
    def is_editable(self) -> bool:
        """Indique si le plan peut être modifié."""
        return self.status in (CarePlanStatus.DRAFT, CarePlanStatus.PENDING_VALIDATION)

    @property
    def is_validated(self) -> bool:
        """Indique si le plan a été validé."""
        return self.validated_at is not None

    @property
    def is_revision(self) -> bool:
        """Indique si ce plan est une révision d'un plan parent (B28b)."""
        return self.supersedes_plan_id is not None

    # B28c/B51 — `has_pending_revision` et `pending_revision_draft_id` sont
    # exposés comme attributs transitoires posés par
    # CarePlanCRUDService.get_by_id() via une query SQL filtrée par tenant
    # (pattern aligné sur superseded_plan_id pour B28a). Pas de @property
    # ici : la relation `revisions` lazy/selectinload pouvait renvoyer une
    # collection vide à cause du contexte RLS post-transaction. Le calcul
    # explicite côté service est plus robuste et le pattern est cohérent
    # avec le reste du module.
    # Schéma Pydantic : CarePlanResponse expose les deux champs avec
    # défauts (False / None) pour les endpoints qui ne posent pas ces
    # attributs (list, summary).

    @property
    def services_count(self) -> int:
        """Nombre de services dans le plan."""
        return len(self.services) if self.services else 0

    @property
    def assigned_services_count(self) -> int:
        """Nombre de services affectés à un professionnel."""
        if not self.services:
            return 0
        return sum(1 for s in self.services if s.assigned_user_id is not None)

    @property
    def unassigned_services_count(self) -> int:
        """Nombre de services non affectés."""
        return self.services_count - self.assigned_services_count

    @property
    def assignment_completion_rate(self) -> float:
        """Taux de complétion des affectations (0.0 à 1.0)."""
        if not self.services:
            return 1.0
        return self.assigned_services_count / len(self.services)

    @property
    def is_fully_assigned(self) -> bool:
        """Indique si tous les services sont affectés."""
        return self.assignment_completion_rate == 1.0

    @property
    def budget_consumed(self) -> Decimal | None:
        """
        Budget consommé estimé = Σ (tarif × quantity_per_week × 4.33) pour chaque service actif.

        Retourne None si aucun service n'a de tarif renseigné.
        Le coefficient 4.33 convertit la fréquence hebdomadaire en mensuelle.
        """
        if not self.services:
            return Decimal("0.00")

        total = Decimal("0.00")
        has_any_tarif = False

        for s in self.services:
            if s.status != "active":
                continue
            tarif = None
            if s.entity_service and s.entity_service.price_euros is not None:
                tarif = s.entity_service.price_euros
            if tarif is not None:
                has_any_tarif = True
                total += tarif * Decimal(str(s.quantity_per_week)) * Decimal("4.33")

        return total if has_any_tarif else None

    def validate(self, user: User) -> None:
        """
        Valide le plan d'aide.

        Args:
            user: Utilisateur effectuant la validation
        """
        self.status = CarePlanStatus.ACTIVE
        self.validated_by_id = user.id
        self.validated_at = datetime.now(UTC)

    def submit_for_validation(self) -> None:
        """Soumet le plan pour validation."""
        if self.status != CarePlanStatus.DRAFT:
            raise ValueError("Seul un plan en brouillon peut être soumis pour validation")
        self.status = CarePlanStatus.PENDING_VALIDATION

    def suspend(self, reason: str | None = None) -> None:
        """
        Suspend le plan d'aide.

        Args:
            reason: Raison de la suspension (ajoutée aux notes)
        """
        self.status = CarePlanStatus.SUSPENDED
        if reason:
            suspension_note = f"\n[SUSPENSION {datetime.now(UTC).isoformat()}] {reason}"
            self.notes = (self.notes or "") + suspension_note

    def reactivate(self) -> None:
        """Réactive un plan suspendu."""
        if self.status != CarePlanStatus.SUSPENDED:
            raise ValueError("Seul un plan suspendu peut être réactivé")
        self.status = CarePlanStatus.ACTIVE

    def complete(self, reason: str | None = None) -> None:
        """
        Marque le plan comme terminé.

        Args:
            reason: Raison de la fermeture, ajoutée au champ `notes` si fournie.
                    Cas d'usage principal (B28a) : transition automatique lors de
                    l'activation d'un nouveau plan ACTIVE pour le même patient.
        """
        self.status = CarePlanStatus.COMPLETED
        if reason:
            completion_note = f"\n[FERMETURE AUTO B28a {datetime.now(UTC).isoformat()}] {reason}"
            self.notes = (self.notes or "") + completion_note

    def cancel(self, reason: str | None = None) -> None:
        """
        Annule le plan d'aide.

        Args:
            reason: Raison de l'annulation (ajoutée aux notes)
        """
        self.status = CarePlanStatus.CANCELLED
        if reason:
            cancellation_note = f"\n[ANNULATION {datetime.now(UTC).isoformat()}] {reason}"
            self.notes = (self.notes or "") + cancellation_note
