"""
User Availabilities - Disponibilités des professionnels.

Ce module gère les créneaux de disponibilité récurrents des professionnels
de santé pour la planification des interventions.
"""

from __future__ import annotations

from datetime import date, time
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Integer, Boolean, Text, ForeignKey, Date, Time, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user.user import User
    from app.models.organization.entity import Entity
    from app.models.tenants.tenant import Tenant


class UserAvailability(TimestampMixin, Base):
    """
    Créneau de disponibilité d'un professionnel.
    
    Représente un créneau horaire récurrent pendant lequel un professionnel
    est disponible pour des interventions.
    
    Attributes:
        user_id: Professionnel concerné
        entity_id: Pour quelle entité (si multi-rattachement)
        day_of_week: Jour de la semaine (1=Lundi ... 7=Dimanche)
        start_time: Heure de début
        end_time: Heure de fin
        is_recurring: Disponibilité récurrente (vs ponctuelle)
        valid_from: Date de début de validité
        valid_until: Date de fin de validité
        max_patients: Nombre max de patients sur ce créneau
        notes: Notes (ex: "sauf jours fériés")
    
    Example:
        >>> availability = UserAvailability(
        ...     user_id=infirmiere.id,
        ...     entity_id=ssiad.id,
        ...     day_of_week=1,  # Lundi
        ...     start_time=time(7, 0),
        ...     end_time=time(12, 0),
        ...     is_recurring=True
        ... )
    """
    
    __tablename__ = "user_availabilities"
    __table_args__ = (
        CheckConstraint("day_of_week >= 1 AND day_of_week <= 7", name="ck_day_of_week"),
        CheckConstraint("start_time < end_time", name="ck_time_range"),
        {"comment": "Disponibilités récurrentes des professionnels"}
    )
    
    # === Clé primaire ===
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # === Multi-tenant ===
    tenant_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant propriétaire de cet enregistrement"
    )
    
    # === Références ===
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Professionnel concerné"
    )
    
    entity_id: Mapped[int | None] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Pour quelle entité (NULL = toutes)"
    )
    
    # === Jour ===
    day_of_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Jour de la semaine (1=Lundi ... 7=Dimanche)"
    )
    
    # === Créneau horaire ===
    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        comment="Heure de début"
    )
    
    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        comment="Heure de fin"
    )
    
    # === Récurrence ===
    is_recurring: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Disponibilité récurrente (True) ou ponctuelle (False)"
    )
    
    # === Validité ===
    valid_from: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Date de début de validité"
    )
    
    valid_until: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Date de fin de validité (NULL = indéfiniment)"
    )
    
    # === Capacité ===
    max_patients: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Nombre max de patients sur ce créneau"
    )
    
    # === Notes ===
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Notes (ex: 'sauf jours fériés')"
    )
    
    # === Statut ===
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Disponibilité active"
    )
    
    # === Relations ===
    user: Mapped["User"] = relationship(
        "User",
        back_populates="availabilities"
    )
    
    entity: Mapped[Optional["Entity"]] = relationship(
        "Entity",
        back_populates="user_availabilities"
    )
    
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        doc="Tenant propriétaire de cette disponibilité"
    )
    
    # === Méthodes ===
    def __str__(self) -> str:
        day_names = {1: "Lun", 2: "Mar", 3: "Mer", 4: "Jeu", 5: "Ven", 6: "Sam", 7: "Dim"}
        day = day_names.get(self.day_of_week, "?")
        return f"{day} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"
    
    def __repr__(self) -> str:
        return f"<UserAvailability(user_id={self.user_id}, day={self.day_of_week}, {self.start_time}-{self.end_time})>"
    
    @property
    def duration_minutes(self) -> int:
        """Calcule la durée du créneau en minutes."""
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        return end_minutes - start_minutes
    
    @property
    def duration_hours(self) -> float:
        """Calcule la durée du créneau en heures."""
        return self.duration_minutes / 60
    
    def is_valid_on(self, check_date: date) -> bool:
        """Vérifie si la disponibilité est valide pour une date donnée."""
        if not self.is_active:
            return False
        
        # Vérifier le jour de la semaine (isoweekday: 1=Lun, 7=Dim)
        if check_date.isoweekday() != self.day_of_week:
            return False
        
        # Vérifier la période de validité
        if self.valid_from and check_date < self.valid_from:
            return False
        if self.valid_until and check_date > self.valid_until:
            return False
        
        return True
    
    def overlaps_with(self, other: "UserAvailability") -> bool:
        """Vérifie si ce créneau chevauche un autre créneau."""
        if self.day_of_week != other.day_of_week:
            return False
        
        # Deux créneaux se chevauchent si l'un commence avant que l'autre finisse
        return (self.start_time < other.end_time and other.start_time < self.end_time)
