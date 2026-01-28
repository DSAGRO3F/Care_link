"""
Modèle ScheduledIntervention - Planning des interventions futures.

Ce module définit la table `scheduled_interventions` qui gère les interventions
planifiées (RDV concrets) générées à partir des services du plan d'aide.
C'est le planning opérationnel quotidien.

Flux de données :
    CarePlanService (récurrence) → ScheduledIntervention (RDV concret) → CoordinationEntry (historique)
"""

from __future__ import annotations

from datetime import date, time, datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Integer, Text, ForeignKey, Date, Time, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.enums import InterventionStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.careplan.care_plan_service import CarePlanService
    from app.models.patient.patient import Patient
    from app.models.user.user import User
    from app.models.coordination.coordination_entry import CoordinationEntry


class ScheduledIntervention(TimestampMixin, Base):
    """
    Intervention planifiée (RDV concret).

    Représente un RDV spécifique généré à partir d'un service du plan d'aide.
    C'est l'unité de base du planning opérationnel quotidien.

    Lifecycle:
        SCHEDULED → CONFIRMED → IN_PROGRESS → COMPLETED
                 ↘ CANCELLED
                 ↘ MISSED
                 ↘ RESCHEDULED → nouvelle ScheduledIntervention

    Attributes:
        id: Identifiant unique
        care_plan_service_id: Service du plan à l'origine
        patient_id: Patient (dénormalisé pour performance)
        user_id: Professionnel affecté
        scheduled_date: Date prévue
        scheduled_start_time: Heure de début prévue
        scheduled_end_time: Heure de fin prévue
        status: Statut de l'intervention
        actual_start_time: Heure réelle de début
        actual_end_time: Heure réelle de fin
        actual_duration_minutes: Durée réelle
        completion_notes: Notes à la fin
        cancellation_reason: Raison d'annulation
        coordination_entry_id: Lien vers l'historique après réalisation
        rescheduled_from_id: Intervention d'origine si reprogrammée
        rescheduled_to_id: Nouvelle intervention si reprogrammée

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
        # Index composites pour les requêtes fréquentes de planning
        Index("ix_sched_interv_user_date", "user_id", "scheduled_date"),
        Index("ix_sched_interv_patient_date", "patient_id", "scheduled_date"),
        Index("ix_sched_interv_date_status", "scheduled_date", "status"),
        {"comment": "Planning des interventions futures"}
    )

    # === Clé primaire ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de l'intervention planifiée",
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

    care_plan_service_id: Mapped[int] = mapped_column(
        ForeignKey("care_plan_services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Service du plan à l'origine de cette intervention",
        info={
            "description": "FK vers care_plan_services. Suppression en cascade",
            "example": 1
        }
    )

    # Dénormalisé pour performance des requêtes de planning
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Patient concerné",
        info={
            "description": "FK vers patients. Dénormalisé pour performance des requêtes de planning",
            "example": 1
        }
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Professionnel affecté à cette intervention",
        info={
            "description": "FK vers users. NULL si pas encore affecté ou professionnel supprimé"
        }
    )

    # === Planning prévu ===

    scheduled_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        doc="Date prévue de l'intervention",
        info={
            "description": "Date à laquelle l'intervention est planifiée",
            "example": "2024-12-20"
        }
    )

    scheduled_start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        doc="Heure de début prévue",
        info={
            "description": "Heure de début planifiée",
            "format": "HH:MM",
            "example": "08:00"
        }
    )

    scheduled_end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        doc="Heure de fin prévue",
        info={
            "description": "Heure de fin planifiée",
            "format": "HH:MM",
            "example": "08:45"
        }
    )

    # === Statut ===

    status: Mapped[InterventionStatus] = mapped_column(
        SQLEnum(InterventionStatus, name="intervention_status_enum", create_constraint=True),
        nullable=False,
        default=InterventionStatus.SCHEDULED,
        index=True,
        doc="Statut de l'intervention",
        info={
            "description": "État actuel de l'intervention dans son cycle de vie",
            "enum": [e.value for e in InterventionStatus],
            "default": "SCHEDULED"
        }
    )

    # === Réalisation effective ===

    actual_start_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        doc="Heure réelle de début",
        info={
            "description": "Heure à laquelle l'intervention a réellement commencé",
            "format": "HH:MM"
        }
    )

    actual_end_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        doc="Heure réelle de fin",
        info={
            "description": "Heure à laquelle l'intervention s'est réellement terminée",
            "format": "HH:MM"
        }
    )

    actual_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Durée réelle en minutes",
        info={
            "description": "Durée effective de l'intervention (calculée ou saisie)",
            "unit": "minutes"
        }
    )

    # === Notes et commentaires ===

    completion_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Notes à la fin de l'intervention",
        info={
            "description": "Observations du professionnel après réalisation"
        }
    )

    cancellation_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Raison d'annulation ou de non-réalisation",
        info={
            "description": "Motif en cas d'annulation, manquée ou reprogrammation"
        }
    )

    # === Lien avec l'historique ===

    coordination_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("coordination_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Lien vers l'entrée de coordination après réalisation",
        info={
            "description": "FK vers coordination_entries. Créé quand l'intervention est complétée"
        }
    )

    # === Reprogrammation (auto-référence) ===

    rescheduled_from_id: Mapped[int | None] = mapped_column(
        ForeignKey("scheduled_interventions.id", ondelete="SET NULL"),
        nullable=True,
        doc="Intervention d'origine si celle-ci est une reprogrammation",
        info={
            "description": "FK auto-référencée. Pointe vers l'intervention originale reprogrammée"
        }
    )

    rescheduled_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("scheduled_interventions.id", ondelete="SET NULL"),
        nullable=True,
        doc="Nouvelle intervention si celle-ci a été reprogrammée",
        info={
            "description": "FK auto-référencée. Pointe vers la nouvelle intervention de remplacement"
        }
    )

    # === Relations ===

    care_plan_service: Mapped["CarePlanService"] = relationship(
        "CarePlanService",
        back_populates="scheduled_interventions",
        doc="Service du plan d'aide à l'origine de cette intervention"
    )

    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="scheduled_interventions",
        doc="Patient concerné par cette intervention"
    )

    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="scheduled_interventions",
        doc="Professionnel affecté à cette intervention"
    )

    coordination_entry: Mapped[Optional["CoordinationEntry"]] = relationship(
        "CoordinationEntry",
        back_populates="scheduled_intervention",
        doc="Entrée de coordination créée après réalisation"
    )

    rescheduled_from: Mapped[Optional["ScheduledIntervention"]] = relationship(
        "ScheduledIntervention",
        foreign_keys=[rescheduled_from_id],
        remote_side="ScheduledIntervention.id",
        uselist=False,
        doc="Intervention originale dont celle-ci est la reprogrammation"
    )

    rescheduled_to: Mapped[Optional["ScheduledIntervention"]] = relationship(
        "ScheduledIntervention",
        foreign_keys=[rescheduled_to_id],
        remote_side="ScheduledIntervention.id",
        uselist=False,
        doc="Nouvelle intervention remplaçant celle-ci"
    )

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<ScheduledIntervention(id={self.id}, date={self.scheduled_date}, status='{self.status.value}')>"

    def __str__(self) -> str:
        return f"{self.scheduled_date} {self.scheduled_start_time.strftime('%H:%M')} - {self.status.value}"

    # === Propriétés de durée ===

    @property
    def scheduled_duration_minutes(self) -> int:
        """Calcule la durée prévue en minutes."""
        start_minutes = self.scheduled_start_time.hour * 60 + self.scheduled_start_time.minute
        end_minutes = self.scheduled_end_time.hour * 60 + self.scheduled_end_time.minute
        return end_minutes - start_minutes

    @property
    def scheduled_duration_hours(self) -> float:
        """Calcule la durée prévue en heures."""
        return self.scheduled_duration_minutes / 60

    @property
    def effective_duration_minutes(self) -> int | None:
        """Retourne la durée effective (réelle si complétée, prévue sinon)."""
        if self.actual_duration_minutes is not None:
            return self.actual_duration_minutes
        if self.is_completed and self.actual_start_time and self.actual_end_time:
            start_min = self.actual_start_time.hour * 60 + self.actual_start_time.minute
            end_min = self.actual_end_time.hour * 60 + self.actual_end_time.minute
            return end_min - start_min
        return None

    @property
    def duration_variance_minutes(self) -> int | None:
        """Calcule l'écart entre durée prévue et réelle (positif = plus long que prévu)."""
        effective = self.effective_duration_minutes
        if effective is not None:
            return effective - self.scheduled_duration_minutes
        return None

    # === Propriétés de statut ===

    @property
    def is_pending(self) -> bool:
        """Indique si l'intervention est en attente (pas encore réalisée)."""
        return self.status in (InterventionStatus.SCHEDULED, InterventionStatus.CONFIRMED)

    @property
    def is_confirmed(self) -> bool:
        """Indique si l'intervention est confirmée."""
        return self.status == InterventionStatus.CONFIRMED

    @property
    def is_in_progress(self) -> bool:
        """Indique si l'intervention est en cours."""
        return self.status == InterventionStatus.IN_PROGRESS

    @property
    def is_completed(self) -> bool:
        """Indique si l'intervention est terminée avec succès."""
        return self.status == InterventionStatus.COMPLETED

    @property
    def is_cancelled(self) -> bool:
        """Indique si l'intervention est annulée."""
        return self.status == InterventionStatus.CANCELLED

    @property
    def is_missed(self) -> bool:
        """Indique si l'intervention a été manquée."""
        return self.status == InterventionStatus.MISSED

    @property
    def is_rescheduled(self) -> bool:
        """Indique si l'intervention a été reprogrammée."""
        return self.status == InterventionStatus.RESCHEDULED

    @property
    def is_terminal(self) -> bool:
        """Indique si l'intervention est dans un état final (ne peut plus évoluer)."""
        return self.status in (
            InterventionStatus.COMPLETED,
            InterventionStatus.CANCELLED,
            InterventionStatus.MISSED,
            InterventionStatus.RESCHEDULED
        )

    @property
    def can_be_started(self) -> bool:
        """Indique si l'intervention peut être démarrée."""
        return self.status in (InterventionStatus.SCHEDULED, InterventionStatus.CONFIRMED)

    # === Propriétés d'affichage ===

    @property
    def time_slot_display(self) -> str:
        """Affiche le créneau horaire de manière lisible."""
        return f"{self.scheduled_start_time.strftime('%H:%M')}-{self.scheduled_end_time.strftime('%H:%M')}"

    @property
    def full_display(self) -> str:
        """Affiche l'intervention complète de manière lisible."""
        return f"{self.scheduled_date.isoformat()} {self.time_slot_display} [{self.status.value}]"

    # === Méthodes de transition d'état ===

    def confirm(self) -> None:
        """Confirme l'intervention."""
        if self.status != InterventionStatus.SCHEDULED:
            raise ValueError("Seule une intervention planifiée peut être confirmée")
        self.status = InterventionStatus.CONFIRMED

    def start(self, actual_start: time | None = None) -> None:
        """
        Démarre l'intervention.

        Args:
            actual_start: Heure réelle de début (défaut: maintenant)
        """
        if not self.can_be_started:
            raise ValueError("L'intervention ne peut pas être démarrée dans son état actuel")
        self.status = InterventionStatus.IN_PROGRESS
        self.actual_start_time = actual_start or datetime.now(timezone.utc).time()

    def complete(self, actual_end: time | None = None, notes: str | None = None) -> None:
        """
        Termine l'intervention avec succès.

        Args:
            actual_end: Heure réelle de fin (défaut: maintenant)
            notes: Notes de fin d'intervention
        """
        if self.status != InterventionStatus.IN_PROGRESS:
            raise ValueError("Seule une intervention en cours peut être terminée")

        self.status = InterventionStatus.COMPLETED
        self.actual_end_time = actual_end or datetime.now(timezone.utc).time()

        # Calculer la durée réelle
        if self.actual_start_time and self.actual_end_time:
            start_min = self.actual_start_time.hour * 60 + self.actual_start_time.minute
            end_min = self.actual_end_time.hour * 60 + self.actual_end_time.minute
            self.actual_duration_minutes = end_min - start_min

        if notes:
            self.completion_notes = notes

    def cancel(self, reason: str) -> None:
        """
        Annule l'intervention.

        Args:
            reason: Motif de l'annulation
        """
        if self.is_terminal:
            raise ValueError("Une intervention terminée ne peut pas être annulée")
        self.status = InterventionStatus.CANCELLED
        self.cancellation_reason = reason

    def mark_missed(self, reason: str | None = None) -> None:
        """
        Marque l'intervention comme manquée.

        Args:
            reason: Motif (ex: patient absent, porte fermée...)
        """
        if self.is_terminal:
            raise ValueError("Une intervention terminée ne peut pas être marquée manquée")
        self.status = InterventionStatus.MISSED
        self.cancellation_reason = reason or "Intervention non réalisée"

    def reschedule(self, new_intervention: "ScheduledIntervention", reason: str | None = None) -> None:
        """
        Reprogramme l'intervention vers une nouvelle date/heure.

        Args:
            new_intervention: Nouvelle intervention de remplacement
            reason: Motif de la reprogrammation
        """
        if self.is_terminal:
            raise ValueError("Une intervention terminée ne peut pas être reprogrammée")

        self.status = InterventionStatus.RESCHEDULED
        self.rescheduled_to_id = new_intervention.id
        new_intervention.rescheduled_from_id = self.id

        if reason:
            self.cancellation_reason = reason

    def link_to_coordination_entry(self, entry: "CoordinationEntry") -> None:
        """
        Lie l'intervention à une entrée de coordination (historique).

        Args:
            entry: Entrée de coordination créée après réalisation
        """
        self.coordination_entry_id = entry.id