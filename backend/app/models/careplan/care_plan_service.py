"""
Modèle CarePlanService - Services du plan d'aide avec fréquence et affectation.

Ce module définit la table `care_plan_services` qui représente les services
individuels d'un plan d'aide avec leurs caractéristiques :
- Fréquence (quotidien, hebdomadaire, jours spécifiques)
- Créneau horaire préféré
- Durée prévue
- Affectation à un professionnel

C'est la table pivot entre le plan d'aide (care_plans) et le catalogue
de services (service_templates).
"""

from __future__ import annotations

from datetime import time, datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import JSON
from sqlalchemy import String, Integer, Text, ForeignKey, Time, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.enums import FrequencyType, ServicePriority, AssignmentStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.careplan.care_plan import CarePlan
    from app.models.catalog.service_template import ServiceTemplate
    from app.models.user.user import User
    from app.models.coordination.scheduled_intervention import ScheduledIntervention


class CarePlanService(TimestampMixin, Base):
    """
    Service individuel dans un plan d'aide.

    Représente un service spécifique avec sa fréquence, son créneau horaire
    préféré, et son affectation à un professionnel.

    Lifecycle d'affectation:
        UNASSIGNED → PENDING → ASSIGNED → CONFIRMED
                            ↘ REJECTED

    Attributes:
        id: Identifiant unique
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
        assigned_at: Date d'affectation
        assigned_by_id: Coordinateur ayant affecté
        special_instructions: Instructions spécifiques
        status: Statut du service (active, paused, completed)

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
    __table_args__ = {
        "comment": "Services individuels des plans d'aide"
    }

    # === Clé primaire ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du service dans le plan",
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

    care_plan_id: Mapped[int] = mapped_column(
        ForeignKey("care_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Plan d'aide parent",
        info={
            "description": "FK vers care_plans. Suppression en cascade",
            "example": 1
        }
    )

    service_template_id: Mapped[int] = mapped_column(
        ForeignKey("service_templates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Type de service du catalogue",
        info={
            "description": "FK vers service_templates. RESTRICT car le service doit exister",
            "example": 1
        }
    )

    # === Fréquence ===

    quantity_per_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        doc="Nombre de fois par semaine",
        info={
            "description": "Fréquence hebdomadaire du service",
            "unit": "fois/semaine",
            "min": 1,
            "max": 21,
            "example": 5
        }
    )

    frequency_type: Mapped[FrequencyType] = mapped_column(
        SQLEnum(FrequencyType, name="frequency_type_enum", create_constraint=True),
        nullable=False,
        default=FrequencyType.WEEKLY,
        doc="Type de fréquence",
        info={
            "description": "Mode de récurrence du service",
            "enum": [e.value for e in FrequencyType],
            "default": "WEEKLY"
        }
    )

    frequency_days: Mapped[list | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        doc="Jours concernés",
        info={
            "description": "Liste des jours de la semaine (1=Lun, 7=Dim)",
            "example": [1, 2, 3, 4, 5],
            "format": "array of integers 1-7"
        }
    )

    # === Créneau horaire préféré ===

    preferred_time_start: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        doc="Heure de début souhaitée",
        info={
            "description": "Début du créneau horaire préféré",
            "format": "HH:MM",
            "example": "07:00"
        }
    )

    preferred_time_end: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        doc="Heure de fin souhaitée",
        info={
            "description": "Fin du créneau horaire préféré",
            "format": "HH:MM",
            "example": "09:00"
        }
    )

    # === Durée ===

    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Durée prévue en minutes",
        info={
            "description": "Durée estimée de l'intervention",
            "unit": "minutes",
            "example": 45
        }
    )

    # === Priorité ===

    priority: Mapped[ServicePriority] = mapped_column(
        SQLEnum(ServicePriority, name="service_priority_enum", create_constraint=True),
        nullable=False,
        default=ServicePriority.MEDIUM,
        doc="Priorité du service",
        info={
            "description": "Niveau de priorité pour la planification",
            "enum": [e.value for e in ServicePriority],
            "default": "MEDIUM"
        }
    )

    # === Affectation ===

    assigned_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Professionnel affecté",
        info={
            "description": "FK vers users. Professionnel responsable de ce service"
        }
    )

    assignment_status: Mapped[AssignmentStatus] = mapped_column(
        SQLEnum(AssignmentStatus, name="assignment_status_enum", create_constraint=True),
        nullable=False,
        default=AssignmentStatus.UNASSIGNED,
        index=True,
        doc="Statut d'affectation",
        info={
            "description": "État de l'affectation à un professionnel",
            "enum": [e.value for e in AssignmentStatus],
            "default": "UNASSIGNED"
        }
    )

    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date et heure d'affectation",
        info={
            "description": "Timestamp de l'affectation au professionnel"
        }
    )

    assigned_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Coordinateur ayant effectué l'affectation",
        info={
            "description": "FK vers users. Utilisateur ayant affecté le service"
        }
    )

    # === Instructions ===

    special_instructions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Instructions spécifiques pour ce service",
        info={
            "description": "Consignes particulières pour la réalisation du service"
        }
    )

    # === Statut ===

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        doc="Statut du service",
        info={
            "description": "État du service dans le plan",
            "values": ["active", "paused", "completed"],
            "default": "active"
        }
    )

    # === Relations ===

    care_plan: Mapped["CarePlan"] = relationship(
        "CarePlan",
        back_populates="services",
        doc="Plan d'aide contenant ce service"
    )

    service_template: Mapped["ServiceTemplate"] = relationship(
        "ServiceTemplate",
        back_populates="care_plan_services",
        doc="Template du service (catalogue national)"
    )

    assigned_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_user_id],
        back_populates="assigned_services",
        doc="Professionnel affecté à ce service"
    )

    assigned_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_by_id],
        doc="Coordinateur ayant effectué l'affectation"
    )

    scheduled_interventions: Mapped[List["ScheduledIntervention"]] = relationship(
        "ScheduledIntervention",
        back_populates="care_plan_service",
        cascade="all, delete-orphan",
        doc="Interventions planifiées pour ce service"
    )

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<CarePlanService(id={self.id}, template_id={self.service_template_id}, status='{self.assignment_status.value}')>"

    def __str__(self) -> str:
        template_name = self.service_template.name if self.service_template else f"Service#{self.service_template_id}"
        freq = f"{self.quantity_per_week}x/sem"
        return f"{template_name} ({freq})"

    # === Propriétés d'état ===

    @property
    def is_assigned(self) -> bool:
        """Indique si le service est affecté à un professionnel."""
        return self.assigned_user_id is not None

    @property
    def is_confirmed(self) -> bool:
        """Indique si l'affectation est confirmée par le professionnel."""
        return self.assignment_status == AssignmentStatus.CONFIRMED

    @property
    def is_pending(self) -> bool:
        """Indique si l'affectation est en attente de confirmation."""
        return self.assignment_status == AssignmentStatus.PENDING

    @property
    def is_active(self) -> bool:
        """Indique si le service est actif."""
        return self.status == "active"

    @property
    def is_paused(self) -> bool:
        """Indique si le service est en pause."""
        return self.status == "paused"

    # === Propriétés d'affichage ===

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
            if self.frequency_type == FrequencyType.DAILY:
                return "Tous les jours"
            return "À définir"

        day_names = {1: "Lun", 2: "Mar", 3: "Mer", 4: "Jeu", 5: "Ven", 6: "Sam", 7: "Dim"}
        return ", ".join(day_names.get(d, "?") for d in sorted(self.frequency_days))

    @property
    def frequency_display(self) -> str:
        """Affiche la fréquence de manière lisible."""
        if self.frequency_type == FrequencyType.DAILY:
            return "Quotidien"
        elif self.frequency_type == FrequencyType.ON_DEMAND:
            return "À la demande"
        else:
            return f"{self.quantity_per_week}x/semaine ({self.days_display})"

    @property
    def total_weekly_minutes(self) -> int:
        """Calcule le total de minutes par semaine pour ce service."""
        return self.quantity_per_week * self.duration_minutes

    @property
    def total_weekly_hours(self) -> float:
        """Calcule le total d'heures par semaine pour ce service."""
        return self.total_weekly_minutes / 60

    # === Méthodes d'affectation ===

    def assign_to(self, user: "User", assigned_by: "User") -> None:
        """
        Affecte le service à un professionnel.

        Args:
            user: Professionnel à qui affecter le service
            assigned_by: Coordinateur effectuant l'affectation
        """
        self.assigned_user_id = user.id
        self.assigned_by_id = assigned_by.id
        self.assigned_at = datetime.now(timezone.utc)
        self.assignment_status = AssignmentStatus.ASSIGNED

    def propose_to(self, user: "User", assigned_by: "User") -> None:
        """
        Propose le service à un professionnel (en attente de confirmation).

        Args:
            user: Professionnel à qui proposer le service
            assigned_by: Coordinateur effectuant la proposition
        """
        self.assigned_user_id = user.id
        self.assigned_by_id = assigned_by.id
        self.assigned_at = datetime.now(timezone.utc)
        self.assignment_status = AssignmentStatus.PENDING

    def unassign(self) -> None:
        """Retire l'affectation du service."""
        self.assigned_user_id = None
        self.assigned_by_id = None
        self.assigned_at = None
        self.assignment_status = AssignmentStatus.UNASSIGNED

    def confirm_assignment(self) -> None:
        """Confirme l'affectation (acceptée par le professionnel)."""
        if self.assignment_status not in (AssignmentStatus.ASSIGNED, AssignmentStatus.PENDING):
            raise ValueError("Le service doit être affecté ou en attente pour être confirmé")
        self.assignment_status = AssignmentStatus.CONFIRMED

    def reject_assignment(self) -> None:
        """Rejette l'affectation (refusée par le professionnel)."""
        if self.assignment_status != AssignmentStatus.PENDING:
            raise ValueError("Seul un service en attente peut être rejeté")
        self.assignment_status = AssignmentStatus.REJECTED

    # === Méthodes de statut ===

    def pause(self) -> None:
        """Met le service en pause."""
        self.status = "paused"

    def resume(self) -> None:
        """Reprend un service en pause."""
        self.status = "active"

    def complete(self) -> None:
        """Marque le service comme terminé."""
        self.status = "completed"