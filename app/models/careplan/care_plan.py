"""
Care Plans - Plans d'aide patient.

Ce module définit le plan d'aide global d'un patient, issu d'une évaluation,
regroupant l'ensemble des services nécessaires.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Integer, Text, ForeignKey, Date, DateTime, Numeric, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, AuditMixin
from app.models.enums import CarePlanStatus

if TYPE_CHECKING:
    from app.models.patient.patient import Patient
    from app.models.patient.patient_evaluation import PatientEvaluation
    from app.models.organization.entity import Entity
    from app.models.user.user import User
    from app.models.careplan.care_plan_service import CarePlanService


class CarePlan(Base, TimestampMixin, AuditMixin):
    """
    Plan d'aide d'un patient.
    
    Représente le plan global de prise en charge issu d'une évaluation,
    regroupant l'ensemble des services nécessaires avec leurs fréquences.
    
    Attributes:
        patient_id: Patient concerné
        source_evaluation_id: Évaluation à l'origine du plan
        entity_id: Entité responsable de la coordination
        title: Titre du plan
        status: Statut (DRAFT, PENDING_VALIDATION, ACTIVE, SUSPENDED, COMPLETED)
        start_date: Date de début
        end_date: Date de fin prévue
        total_hours_week: Total heures/semaine prévu
        gir_at_creation: GIR du patient à la création du plan
        validated_by: Utilisateur ayant validé
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
    __table_args__ = (
        {"comment": "Plans d'aide patients"}
    )
    
    # === Clé primaire ===
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # === Références ===
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Patient concerné"
    )
    
    source_evaluation_id: Mapped[int | None] = mapped_column(
        ForeignKey("patient_evaluations.id", ondelete="SET NULL"),
        nullable=True,
        comment="Évaluation à l'origine du plan"
    )
    
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Entité responsable de la coordination"
    )
    
    # === Identification ===
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Titre du plan"
    )
    
    reference_number: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        comment="Numéro de référence unique"
    )
    
    # === Statut ===
    status: Mapped[CarePlanStatus] = mapped_column(
        SQLEnum(CarePlanStatus, name="care_plan_status_enum", create_constraint=True),
        nullable=False,
        default=CarePlanStatus.DRAFT,
        index=True,
        comment="Statut du plan"
    )
    
    # === Période ===
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date de début"
    )
    
    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Date de fin prévue (NULL = indéterminée)"
    )
    
    # === Volumétrie ===
    total_hours_week: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Total heures/semaine prévu"
    )
    
    gir_at_creation: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Score GIR du patient à la création du plan (1-6)"
    )
    
    # === Validation ===
    validated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Utilisateur ayant validé"
    )
    
    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Date de validation"
    )
    
    # === Notes ===
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Observations générales"
    )
    
    # === Relations ===
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="care_plans"
    )
    
    source_evaluation: Mapped[Optional["PatientEvaluation"]] = relationship(
        "PatientEvaluation",
        back_populates="care_plans"
    )
    
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="care_plans"
    )
    
    validated_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[validated_by_id],
        back_populates="validated_care_plans"
    )
    
    services: Mapped[List["CarePlanService"]] = relationship(
        "CarePlanService",
        back_populates="care_plan",
        cascade="all, delete-orphan",
        order_by="CarePlanService.id"
    )
    
    # === Méthodes ===
    def __str__(self) -> str:
        return f"{self.title} ({self.status.value})"
    
    def __repr__(self) -> str:
        return f"<CarePlan(id={self.id}, patient_id={self.patient_id}, status='{self.status.value}')>"
    
    @property
    def is_active(self) -> bool:
        """Indique si le plan est actuellement actif."""
        return self.status == CarePlanStatus.ACTIVE
    
    @property
    def is_editable(self) -> bool:
        """Indique si le plan peut être modifié."""
        return self.status in (CarePlanStatus.DRAFT, CarePlanStatus.PENDING_VALIDATION)
    
    @property
    def services_count(self) -> int:
        """Nombre de services dans le plan."""
        return len(self.services)
    
    @property
    def assigned_services_count(self) -> int:
        """Nombre de services affectés à un professionnel."""
        return sum(1 for s in self.services if s.assigned_user_id is not None)
    
    @property
    def assignment_completion_rate(self) -> float:
        """Taux de complétion des affectations (0.0 à 1.0)."""
        if not self.services:
            return 1.0
        return self.assigned_services_count / len(self.services)
    
    def validate(self, user: "User") -> None:
        """Valide le plan d'aide."""
        from datetime import datetime, timezone
        self.status = CarePlanStatus.ACTIVE
        self.validated_by_id = user.id
        self.validated_at = datetime.now(timezone.utc)
    
    def suspend(self) -> None:
        """Suspend le plan d'aide."""
        self.status = CarePlanStatus.SUSPENDED
    
    def complete(self) -> None:
        """Marque le plan comme terminé."""
        self.status = CarePlanStatus.COMPLETED
