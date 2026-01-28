"""
Modèle EvaluationSession - Sessions de saisie d'évaluation.

Ce module définit la table `evaluation_sessions` qui stocke les sessions
de saisie pour les évaluations multi-jours.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user.user import User
    from app.models.patient.patient_evaluation import PatientEvaluation


class EvaluationSession(TimestampMixin, Base):
    """
    Représente une session de saisie d'évaluation.

    Une évaluation peut avoir plusieurs sessions (saisie sur plusieurs jours).
    Chaque session enregistre qui a saisi, quand, et quelles variables.

    Attributes:
        id: Identifiant unique
        evaluation_id: ID de l'évaluation parente
        user_id: ID du professionnel ayant saisi
        started_at: Début de la session
        ended_at: Fin de la session (null si en cours)
        status: Statut de la session
        device_info: Informations sur l'appareil utilisé
        sync_status: Statut de synchronisation (mode hors-ligne)
        variables_recorded: Liste des codes variables saisies
    """

    __tablename__ = "evaluation_sessions"
    __table_args__ = {
        "comment": "Table des sessions de saisie d'évaluation"
    }

    # === Colonnes ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de la session"
    )

    # === Multi-tenant ===

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant propriétaire"
    )

    # --- Références ---

    evaluation_id: Mapped[int] = mapped_column(
        ForeignKey("patient_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID de l'évaluation parente"
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        doc="ID du professionnel ayant effectué la saisie"
    )

    # --- Temporalité ---

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Date et heure de début de session"
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date et heure de fin de session (null si en cours)"
    )

    # --- Statut ---

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="IN_PROGRESS",
        doc="Statut de la session"
    )

    # --- Mode hors-ligne ---

    sync_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="SYNCED",
        doc="Statut de synchronisation"
    )

    local_session_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="ID local généré côté client (pour réconciliation)"
    )

    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Dernière synchronisation réussie"
    )

    # --- Métadonnées ---

    device_info: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        doc="Informations sur l'appareil (ex: 'iPad Pro - Safari')"
    )

    variables_recorded: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Liste des codes variables saisies (JSON array string)"
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Notes de session (interruption, problèmes...)"
    )

    # === Relations ===

    evaluation: Mapped["PatientEvaluation"] = relationship(
        "PatientEvaluation",
        back_populates="sessions",
        doc="Évaluation parente"
    )

    user: Mapped["User"] = relationship(
        "User",
        doc="Professionnel ayant effectué la saisie"
    )

    # === Propriétés ===

    @property
    def is_active(self) -> bool:
        """Retourne True si la session est en cours."""
        return self.status == "IN_PROGRESS" and self.ended_at is None

    @property
    def duration_minutes(self) -> int | None:
        """Retourne la durée de la session en minutes."""
        if self.ended_at:
            delta = self.ended_at - self.started_at
            return int(delta.total_seconds() / 60)
        return None

    @property
    def is_synced(self) -> bool:
        """Retourne True si la session est synchronisée."""
        return self.sync_status == "SYNCED"

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<EvaluationSession(id={self.id}, evaluation_id={self.evaluation_id}, status={self.status})>"

    def end_session(self) -> None:
        """Termine la session."""
        self.ended_at = datetime.now(timezone.utc)
        self.status = "COMPLETED"

    def interrupt_session(self, note: str = None) -> None:
        """Interrompt la session (perte de connexion, etc.)."""
        self.ended_at = datetime.now(timezone.utc)
        self.status = "INTERRUPTED"
        if note:
            self.notes = note

    def mark_synced(self) -> None:
        """Marque la session comme synchronisée."""
        self.sync_status = "SYNCED"
        self.last_sync_at = datetime.now(timezone.utc)

    def add_variable(self, variable_code: str) -> None:
        """Ajoute une variable à la liste des variables saisies."""
        import json
        current = json.loads(self.variables_recorded or "[]")
        if variable_code not in current:
            current.append(variable_code)
            self.variables_recorded = json.dumps(current)

    def get_variables_list(self) -> list:
        """Retourne la liste des codes variables saisies."""
        import json
        return json.loads(self.variables_recorded or "[]")