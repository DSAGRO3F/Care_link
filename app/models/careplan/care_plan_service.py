"""
Care Plan Services - Services du plan d'aide avec fréquence et affectation.

Ce module définit les services individuels d'un plan d'aide avec leurs
caractéristiques (fréquence, créneau horaire, affectation à un professionnel).
"""

from __future__ import annotations

from datetime import time, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Integer, Text, ForeignKey, Time, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin
from app.models.enums import FrequencyType, ServicePriority, AssignmentStatus

if TYPE_CHECKING:
    from app.models.careplan.care_plan import CarePlan
    from app.models.catalog.service_template import ServiceTemplate
    from app.models.user.user import User
    from app.models.coordination.scheduled_intervention import ScheduledIntervention


class CarePlanService(Base, TimestampMixin):
    """
    Service individuel dans un plan d'aide.
    
    Représente un service spécifique avec sa fréquence, son créneau horaire
    préféré, et son affectation à un professionnel.
    
    Attributes:
        care_plan_id: Plan d'aide parent
        service_template_id: Type de service (du catalogue)
        quantity_per_week: Nombre de fois par semaine
        frequency_type: Type de fréquence (DAILY, WEEKLY, SPECIFIC_DAYS...)
        frequency_days: Jours concernés [1,2,3,4,5] = Lun-Ven
        preferred_time_start: Heure de début souhaitée
        preferred_time_end: Heure de fin souhaitée
        duration_minutes: Durée prévue
        priority: Priorité (LOW, MEDIUM, HIGH, CRITICAL)
        assigned_user_id: Professionnel affecté
        assignment_status: Statut d'affectation
        special_instructions: Instructions spécifiques
    
    Example:
        >>> service = CarePlanService(
        ...     care_plan_id=plan.id,
        ...     service_template_id=toilette.id,
        ...     frequency_type=FrequencyType.SPECIFIC_DAYS,
        ...     frequency_days=[1, 2, 3, 4, 5],  # Lun-Ven
        ...     preferred_time_start=time(7, 0),
        ...     preferred_time_end=time(9, 0),
        ...     duration_minutes=45
        ... )
    """
    
    __tablename__ = "care_plan_services"
    __table_args__ = (
        {"comment": "Services individuels des plans d'aide"}
    )
    
    # === Clé primaire ===
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # === Références ===
    care_plan_id: Mapped[int] = mapped_column(
        ForeignKey("care_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Plan d'aide parent"
    )
    
    service_template_id: Mapped[int] = mapped_column(
        ForeignKey("service_templates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Type de service (du catalogue)"
    )
    
    # === Fréquence ===
    quantity_per_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Nombre de fois par semaine"
    )
    
    frequency_type: Mapped[FrequencyType] = mapped_column(
        SQLEnum(FrequencyType, name="frequency_type_enum", create_constraint=True),
        nullable=False,
        default=FrequencyType.WEEKLY,
        comment="Type de fréquence"
    )
    
    frequency_days: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Jours concernés [1=Lun, 2=Mar, ..., 7=Dim]"
    )
    
    # === Créneau horaire préféré ===
    preferred_time_start: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        comment="Heure de début souhaitée"
    )
    
    preferred_time_end: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        comment="Heure de fin souhaitée"
    )
    
    # === Durée ===
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Durée prévue en minutes"
    )
    
    # === Priorité ===
    priority: Mapped[ServicePriority] = mapped_column(
        SQLEnum(ServicePriority, name="service_priority_enum", create_constraint=True),
        nullable=False,
        default=ServicePriority.MEDIUM,
        comment="Priorité du service"
    )
    
    # === Affectation ===
    assigned_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Professionnel affecté"
    )
    
    assignment_status: Mapped[AssignmentStatus] = mapped_column(
        SQLEnum(AssignmentStatus, name="assignment_status_enum", create_constraint=True),
        nullable=False,
        default=AssignmentStatus.UNASSIGNED,
        index=True,
        comment="Statut d'affectation"
    )
    
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Date d'affectation"
    )
    
    assigned_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Coordinateur ayant affecté"
    )
    
    # === Instructions ===
    special_instructions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Instructions spécifiques pour ce service"
    )
    
    # === Statut ===
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        comment="active, paused, completed"
    )
    
    # === Relations ===
    care_plan: Mapped["CarePlan"] = relationship(
        "CarePlan",
        back_populates="services"
    )
    
    service_template: Mapped["ServiceTemplate"] = relationship(
        "ServiceTemplate",
        back_populates="care_plan_services"
    )
    
    assigned_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_user_id],
        back_populates="assigned_services"
    )
    
    assigned_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_by_id]
    )
    
    scheduled_interventions: Mapped[List["ScheduledIntervention"]] = relationship(
        "ScheduledIntervention",
        back_populates="care_plan_service",
        cascade="all, delete-orphan"
    )
    
    # === Méthodes ===
    def __str__(self) -> str:
        freq = f"{self.quantity_per_week}x/sem"
        return f"{self.service_template.name} ({freq})"
    
    def __repr__(self) -> str:
        return f"<CarePlanService(id={self.id}, service='{self.service_template_id}', status='{self.assignment_status.value}')>"
    
    @property
    def is_assigned(self) -> bool:
        """Indique si le service est affecté à un professionnel."""
        return self.assigned_user_id is not None
    
    @property
    def time_slot_display(self) -> str:
        """Affiche le créneau horaire de manière lisible."""
        if self.preferred_time_start and self.preferred_time_end:
            return f"{self.preferred_time_start.strftime('%H:%M')}-{self.preferred_time_end.strftime('%H:%M')}"
        elif self.preferred_time_start:
            return f"à partir de {self.preferred_time_start.strftime('%H:%M')}"
        return "Horaire flexible"
    
    @property
    def days_display(self) -> str:
        """Affiche les jours de manière lisible."""
        if not self.frequency_days:
            return "Tous les jours"
        
        day_names = {1: "Lun", 2: "Mar", 3: "Mer", 4: "Jeu", 5: "Ven", 6: "Sam", 7: "Dim"}
        return ", ".join(day_names.get(d, "?") for d in sorted(self.frequency_days))
    
    def assign_to(self, user: "User", assigned_by: "User") -> None:
        """Affecte le service à un professionnel."""
        from datetime import datetime, timezone
        self.assigned_user_id = user.id
        self.assigned_by_id = assigned_by.id
        self.assigned_at = datetime.now(timezone.utc)
        self.assignment_status = AssignmentStatus.ASSIGNED
    
    def unassign(self) -> None:
        """Retire l'affectation du service."""
        self.assigned_user_id = None
        self.assigned_by_id = None
        self.assigned_at = None
        self.assignment_status = AssignmentStatus.UNASSIGNED
    
    def confirm_assignment(self) -> None:
        """Confirme l'affectation (acceptée par le professionnel)."""
        self.assignment_status = AssignmentStatus.CONFIRMED
