"""
Scheduled Interventions - Planning des interventions futures.

Ce module gère les interventions planifiées (RDV concrets) générées à partir
des services du plan d'aide. C'est le planning opérationnel quotidien.
"""

from __future__ import annotations

from datetime import date, time, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, Text, ForeignKey, Date, Time, DateTime, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin
from app.models.enums import InterventionStatus

if TYPE_CHECKING:
    from app.models.careplan.care_plan_service import CarePlanService
    from app.models.patient.patient import Patient
    from app.models.user.user import User
    from app.models.coordination.coordination_entry import CoordinationEntry


class ScheduledIntervention(Base, TimestampMixin):
    """
    Intervention planifiée (RDV concret).
    
    Représente un RDV spécifique généré à partir d'un service du plan d'aide.
    C'est l'unité de base du planning opérationnel quotidien.
    
    Lifecycle:
        SCHEDULED → CONFIRMED → IN_PROGRESS → COMPLETED
                 ↘ CANCELLED / MISSED / RESCHEDULED
    
    Attributes:
        care_plan_service_id: Service du plan à l'origine
        patient_id: Patient (dénormalisé pour performance)
        user_id: Professionnel affecté
        scheduled_date: Date prévue
        scheduled_start_time: Heure de début prévue
        scheduled_end_time: Heure de fin prévue
        status: Statut de l'intervention
        actual_start_time: Heure réelle de début
        actual_end_time: Heure réelle de fin
        completion_notes: Notes à la fin
        cancellation_reason: Raison d'annulation
        coordination_entry_id: Lien vers l'historique après réalisation
    
    Example:
        >>> intervention = ScheduledIntervention(
        ...     care_plan_service_id=service.id,
        ...     patient_id=patient.id,
        ...     user_id=infirmiere.id,
        ...     scheduled_date=date(2024, 12, 20),
        ...     scheduled_start_time=time(8, 0),
        ...     scheduled_end_time=time(8, 45),
        ...     status=InterventionStatus.SCHEDULED
        ... )
    """
    
    __tablename__ = "scheduled_interventions"
    __table_args__ = (
        # Index composites pour les requêtes fréquentes
        Index("ix_scheduled_interventions_user_date", "user_id", "scheduled_date"),
        Index("ix_scheduled_interventions_patient_date", "patient_id", "scheduled_date"),
        {"comment": "Planning des interventions futures"}
    )
    
    # === Clé primaire ===
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # === Références ===
    care_plan_service_id: Mapped[int] = mapped_column(
        ForeignKey("care_plan_services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Service du plan à l'origine"
    )
    
    # Dénormalisés pour performance des requêtes de planning
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Patient (dénormalisé)"
    )
    
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Professionnel affecté"
    )
    
    # === Planning prévu ===
    scheduled_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Date prévue"
    )
    
    scheduled_start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        comment="Heure de début prévue"
    )
    
    scheduled_end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        comment="Heure de fin prévue"
    )
    
    # === Statut ===
    status: Mapped[InterventionStatus] = mapped_column(
        SQLEnum(InterventionStatus, name="intervention_status_enum", create_constraint=True),
        nullable=False,
        default=InterventionStatus.SCHEDULED,
        index=True,
        comment="Statut de l'intervention"
    )
    
    # === Réalisation effective ===
    actual_start_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        comment="Heure réelle de début"
    )
    
    actual_end_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        comment="Heure réelle de fin"
    )
    
    actual_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Durée réelle en minutes"
    )
    
    # === Notes et commentaires ===
    completion_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Notes à la fin de l'intervention"
    )
    
    cancellation_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Raison d'annulation"
    )
    
    # === Lien avec l'historique ===
    coordination_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("coordination_entries.id", ondelete="SET NULL"),
        nullable=True,
        comment="Lien vers l'historique après réalisation"
    )
    
    # === Reprogrammation ===
    rescheduled_from_id: Mapped[int | None] = mapped_column(
        ForeignKey("scheduled_interventions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Intervention d'origine si reprogrammée"
    )
    
    rescheduled_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("scheduled_interventions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Nouvelle intervention si reprogrammée"
    )
    
    # === Relations ===
    care_plan_service: Mapped["CarePlanService"] = relationship(
        "CarePlanService",
        back_populates="scheduled_interventions"
    )
    
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="scheduled_interventions"
    )
    
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="scheduled_interventions"
    )
    
    coordination_entry: Mapped[Optional["CoordinationEntry"]] = relationship(
        "CoordinationEntry",
        back_populates="scheduled_intervention"
    )
    
    rescheduled_from: Mapped[Optional["ScheduledIntervention"]] = relationship(
        "ScheduledIntervention",
        foreign_keys=[rescheduled_from_id],
        remote_side="ScheduledIntervention.id",
        uselist=False
    )
    
    # === Méthodes ===
    def __str__(self) -> str:
        return f"{self.scheduled_date} {self.scheduled_start_time.strftime('%H:%M')} - {self.status.value}"
    
    def __repr__(self) -> str:
        return f"<ScheduledIntervention(id={self.id}, date={self.scheduled_date}, status='{self.status.value}')>"
    
    @property
    def scheduled_duration_minutes(self) -> int:
        """Calcule la durée prévue en minutes."""
        start_minutes = self.scheduled_start_time.hour * 60 + self.scheduled_start_time.minute
        end_minutes = self.scheduled_end_time.hour * 60 + self.scheduled_end_time.minute
        return end_minutes - start_minutes
    
    @property
    def is_pending(self) -> bool:
        """Indique si l'intervention est en attente."""
        return self.status in (InterventionStatus.SCHEDULED, InterventionStatus.CONFIRMED)
    
    @property
    def is_completed(self) -> bool:
        """Indique si l'intervention est terminée."""
        return self.status == InterventionStatus.COMPLETED
    
    @property
    def is_cancelled(self) -> bool:
        """Indique si l'intervention est annulée."""
        return self.status in (InterventionStatus.CANCELLED, InterventionStatus.MISSED)
    
    def confirm(self) -> None:
        """Confirme l'intervention."""
        self.status = InterventionStatus.CONFIRMED
    
    def start(self, actual_start: time | None = None) -> None:
        """Démarre l'intervention."""
        from datetime import datetime, timezone
        self.status = InterventionStatus.IN_PROGRESS
        self.actual_start_time = actual_start or datetime.now(timezone.utc).time()
    
    def complete(self, actual_end: time | None = None, notes: str | None = None) -> None:
        """Termine l'intervention."""
        from datetime import datetime, timezone
        self.status = InterventionStatus.COMPLETED
        self.actual_end_time = actual_end or datetime.now(timezone.utc).time()
        
        if self.actual_start_time and self.actual_end_time:
            start_min = self.actual_start_time.hour * 60 + self.actual_start_time.minute
            end_min = self.actual_end_time.hour * 60 + self.actual_end_time.minute
            self.actual_duration_minutes = end_min - start_min
        
        if notes:
            self.completion_notes = notes
    
    def cancel(self, reason: str) -> None:
        """Annule l'intervention."""
        self.status = InterventionStatus.CANCELLED
        self.cancellation_reason = reason
    
    def mark_missed(self, reason: str | None = None) -> None:
        """Marque l'intervention comme manquée."""
        self.status = InterventionStatus.MISSED
        self.cancellation_reason = reason or "Intervention non réalisée"
