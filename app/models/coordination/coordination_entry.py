"""
Modèle CoordinationEntry - Carnet de coordination.

Ce module définit la table `coordination_entries` qui stocke les interventions
des professionnels de santé pour assurer la coordination et éviter les doublons.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin
from app.models.enums import CoordinationCategory

if TYPE_CHECKING:
    from app.models.user.user import User
    from app.models.patient.patient import Patient


class CoordinationEntry(TimestampMixin, Base):
    """
    Représente une entrée dans le carnet de coordination.

    Permet de tracer qui a fait quoi, quand, pour un patient donné.
    Utilisé pour la coordination entre professionnels et éviter les doublons
    d'interventions.

    Attributes:
        id: Identifiant unique
        patient_id: ID du patient concerné
        user_id: ID du professionnel ayant réalisé l'intervention
        category: Catégorie d'intervention (SOINS, HYGIENE, etc.)
        intervention_type: Type spécifique (toilette, pansement, etc.)
        description: Description de l'intervention
        observations: Remarques, état du patient
        next_actions: Actions à prévoir
        performed_at: Date/heure de l'intervention
        duration_minutes: Durée en minutes
        deleted_at: Soft delete (NULL = actif)
    """

    __tablename__ = "coordination_entries"
    __table_args__ = {
        "comment": "Carnet de coordination des interventions"
    }

    # === Colonnes ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de l'entrée"
    )

    # --- Références ---

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID du patient concerné"
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
        doc="Professionnel ayant réalisé l'intervention"
    )

    # --- Catégorisation ---

    category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        doc="Catégorie d'intervention",
        info={
            "enum": [e.value for e in CoordinationCategory],
            "example": "SOINS"
        }
    )

    intervention_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Type spécifique d'intervention (toilette, pansement, injection...)"
    )

    # --- Contenu ---

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Description de l'intervention réalisée"
    )

    observations: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Observations complémentaires (état du patient, remarques...)"
    )

    next_actions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Actions à prévoir pour la prochaine intervention"
    )

    # --- Horodatage ---

    performed_at: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
        doc="Date/heure de réalisation de l'intervention"
    )

    duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Durée de l'intervention en minutes"
    )

    # --- Soft delete ---

    deleted_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        doc="Date de suppression logique (NULL = actif)"
    )

    # === Relations ===

    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="coordination_entries",
        doc="Patient concerné"
    )

    user: Mapped["User"] = relationship(
        "User",
        foreign_keys="[CoordinationEntry.user_id]",
        doc="Professionnel ayant réalisé l'intervention"
    )

    # === Propriétés ===

    @property
    def is_active(self) -> bool:
        """Retourne True si l'entrée n'est pas supprimée."""
        return self.deleted_at is None

    @property
    def is_deleted(self) -> bool:
        """Retourne True si l'entrée est supprimée (soft delete)."""
        return self.deleted_at is not None

    @property
    def is_recent(self) -> bool:
        """Retourne True si l'intervention date de moins de 24h."""
        if self.performed_at is None:
            return False
        now = datetime.now(timezone.utc)
        # Gérer les datetime naive
        performed = self.performed_at
        if performed.tzinfo is None:
            performed = performed.replace(tzinfo=timezone.utc)
        delta = now - performed
        return delta.total_seconds() < 24 * 3600  # 24 heures

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<CoordinationEntry(id={self.id}, category={self.category}, patient_id={self.patient_id})>"

    def __str__(self) -> str:
        return f"{self.category}/{self.intervention_type}: {self.description[:50]}..."

    def soft_delete(self) -> None:
        """Supprime logiquement l'entrée (soft delete)."""
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """Restaure une entrée supprimée."""
        self.deleted_at = None
