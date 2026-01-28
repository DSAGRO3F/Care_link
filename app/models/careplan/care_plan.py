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

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Integer, Text, ForeignKey, Date, DateTime, Numeric, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin, AuditMixin
from app.models.enums import CarePlanStatus

if TYPE_CHECKING:
    from app.models.patient.patient import Patient
    from app.models.patient.patient_evaluation import PatientEvaluation
    from app.models.organization.entity import Entity
    from app.models.user.user import User
    from app.models.careplan.care_plan_service import CarePlanService
    from app.models.tenants.tenant import Tenant


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
        ...     start_date=date.today()
        ... )
    """

    __tablename__ = "care_plans"
    __table_args__ = {
        "comment": "Plans d'aide patients"
    }

    # === Clé primaire ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du plan d'aide",
        info={
            "description": "Clé primaire auto-incrémentée"
        }
    )

    # === Multi-tenant ===

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant propriétaire de cet enregistrement"
    )

    # === Références ===

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Patient concerné par ce plan",
        info={
            "description": "FK vers patients. Suppression en cascade",
            "example": 1
        }
    )

    source_evaluation_id: Mapped[int | None] = mapped_column(
        ForeignKey("patient_evaluations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Évaluation à l'origine du plan",
        info={
            "description": "FK vers patient_evaluations. L'évaluation ayant conduit à ce plan"
        }
    )

    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Entité responsable de la coordination",
        info={
            "description": "FK vers entities. Structure coordinatrice du plan",
            "example": 1
        }
    )

    # === Identification ===

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Titre du plan d'aide",
        info={
            "description": "Titre descriptif du plan",
            "example": "Plan d'aide 2024 - Maintien à domicile"
        }
    )

    reference_number: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        doc="Numéro de référence unique",
        info={
            "description": "Référence administrative unique (format libre)",
            "example": "PA-2024-00123"
        }
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
            "default": "DRAFT"
        }
    )

    # === Période ===

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="Date de début du plan",
        info={
            "description": "Date à partir de laquelle le plan est effectif",
            "example": "2024-01-01"
        }
    )

    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        doc="Date de fin prévue du plan",
        info={
            "description": "Date de fin prévue. NULL = durée indéterminée",
            "example": "2024-12-31"
        }
    )

    # === Volumétrie ===

    total_hours_week: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        doc="Total d'heures par semaine prévu",
        info={
            "description": "Volume horaire hebdomadaire prévu pour l'ensemble des services",
            "unit": "heures/semaine",
            "example": "12.50"
        }
    )

    gir_at_creation: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Score GIR du patient à la création du plan",
        info={
            "description": "Niveau GIR (1-6) issu de l'évaluation source",
            "min": 1,
            "max": 6,
            "example": 4
        }
    )

    # === Validation ===

    validated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Utilisateur ayant validé le plan",
        info={
            "description": "FK vers users. Coordinateur ou médecin validateur"
        }
    )

    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date et heure de validation",
        info={
            "description": "Timestamp de validation du plan"
        }
    )

    # === Notes ===

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Observations générales sur le plan",
        info={
            "description": "Notes libres, contexte, recommandations particulières"
        }
    )

    # === Relations ===

    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="care_plans",
        doc="Patient concerné par ce plan"
    )

    source_evaluation: Mapped[Optional["PatientEvaluation"]] = relationship(
        "PatientEvaluation",
        back_populates="care_plans",
        doc="Évaluation source ayant généré ce plan"
    )

    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="care_plans",
        doc="Entité responsable de la coordination"
    )

    validated_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[validated_by_id],
        back_populates="validated_care_plans",
        doc="Utilisateur ayant validé le plan"
    )

    services: Mapped[List["CarePlanService"]] = relationship(
        "CarePlanService",
        back_populates="care_plan",
        cascade="all, delete-orphan",
        order_by="CarePlanService.id",
        doc="Services composant ce plan d'aide"
    )

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<CarePlan(id={self.id}, patient_id={self.patient_id}, status='{self.status.value}')>"

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

    def validate(self, user: "User") -> None:
        """
        Valide le plan d'aide.

        Args:
            user: Utilisateur effectuant la validation
        """
        self.status = CarePlanStatus.ACTIVE
        self.validated_by_id = user.id
        self.validated_at = datetime.now(timezone.utc)

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
            suspension_note = f"\n[SUSPENSION {datetime.now(timezone.utc).isoformat()}] {reason}"
            self.notes = (self.notes or "") + suspension_note

    def reactivate(self) -> None:
        """Réactive un plan suspendu."""
        if self.status != CarePlanStatus.SUSPENDED:
            raise ValueError("Seul un plan suspendu peut être réactivé")
        self.status = CarePlanStatus.ACTIVE

    def complete(self) -> None:
        """Marque le plan comme terminé."""
        self.status = CarePlanStatus.COMPLETED

    def cancel(self, reason: str | None = None) -> None:
        """
        Annule le plan d'aide.

        Args:
            reason: Raison de l'annulation (ajoutée aux notes)
        """
        self.status = CarePlanStatus.CANCELLED
        if reason:
            cancellation_note = f"\n[ANNULATION {datetime.now(timezone.utc).isoformat()}] {reason}"
            self.notes = (self.notes or "") + cancellation_note