"""
Modèle PatientEvaluation - Évaluations patient (JSON Schema).

Ce module définit la table `patient_evaluations` qui stocke les évaluations
des patients au format JSON (validées par JSON Schema).
"""

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any, Dict

from sqlalchemy import String, Integer, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin, VersionedMixin
from app.models.types import JSONBCompatible
from app.models.enums import EvaluationSchemaType

if TYPE_CHECKING:
    from app.models.user.user import User
    from app.models.patient.patient import Patient


class PatientEvaluation(VersionedMixin, TimestampMixin, Base):
    """
    Représente une évaluation patient (AGGIR, sociale, santé, etc.)

    Les données d'évaluation sont stockées en JSON et validées
    par un JSON Schema externe.

    Attributes:
        id: Identifiant unique
        patient_id: ID du patient évalué
        evaluator_id: ID du professionnel évaluateur
        schema_type: Type de schéma utilisé
        schema_version: Version du schéma
        evaluation_data: Données JSON de l'évaluation
        gir_score: Score GIR extrait (1-6)
        evaluation_date: Date de l'évaluation
        validated_at: Date de validation
        validated_by: ID du validateur
    """

    __tablename__ = "patient_evaluations"
    __table_args__ = {
        "comment": "Table des évaluations patients (JSON Schema)"
    }

    # === Colonnes ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de l'évaluation",
        info={"description": "Clé primaire auto-incrémentée"}
    )

    # --- Références ---

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID du patient évalué",
        info={"description": "Référence vers le patient"}
    )

    evaluator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        doc="ID du professionnel ayant réalisé l'évaluation",
        info={"description": "Référence vers l'évaluateur"}
    )

    # --- Type et version du schéma ---

    schema_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Type de schéma JSON utilisé",
        info={
            "description": "Identifiant du type d'évaluation",
            "enum": [e.value for e in EvaluationSchemaType],
            "example": "evaluation_complete"
        }
    )

    schema_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Version du schéma JSON",
        info={"description": "Version sémantique du schéma", "example": "v1"}
    )

    # --- Données d'évaluation (JSON) ---
    # Utilise JSONBCompatible pour compatibilité SQLite (tests) et PostgreSQL (prod)

    evaluation_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONBCompatible,
        nullable=False,
        doc="Document JSON contenant les données d'évaluation",
        info={
            "description": "Données complètes de l'évaluation validées par JSON Schema",
            "example": {"aggir": {"GIR": 4}, "usager": {...}}
        }
    )

    # --- Métadonnées extraites ---

    gir_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Score GIR extrait du JSON (1-6)",
        info={"description": "Score GIR pour requêtes SQL rapides", "min": 1, "max": 6}
    )

    evaluation_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="Date de réalisation de l'évaluation",
        info={"description": "Date à laquelle l'évaluation a été effectuée"}
    )

    # --- Validation ---

    validated_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        doc="Date et heure de validation",
        info={"description": "NULL = non validée"}
    )

    validated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID du professionnel ayant validé l'évaluation",
        info={"description": "Référence vers le validateur"}
    )

    # === Relations ===

    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="evaluations",
        doc="Patient évalué"
    )

    evaluator: Mapped["User"] = relationship(
        "User",
        foreign_keys="[PatientEvaluation.evaluator_id]",
        doc="Professionnel ayant réalisé l'évaluation"
    )

    validator: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="[PatientEvaluation.validated_by]",
        doc="Professionnel ayant validé l'évaluation"
    )

    # === Propriétés ===

    @property
    def is_validated(self) -> bool:
        """Retourne True si l'évaluation a été validée."""
        return self.validated_at is not None

    @property
    def aggir_data(self) -> Dict[str, Any] | None:
        """Retourne les données AGGIR extraites du JSON."""
        if self.evaluation_data and "aggir" in self.evaluation_data:
            return self.evaluation_data["aggir"]
        return None

    @property
    def usager_data(self) -> Dict[str, Any] | None:
        """Retourne les données usager extraites du JSON."""
        if self.evaluation_data and "usager" in self.evaluation_data:
            return self.evaluation_data["usager"]
        return None

    @property
    def sante_data(self) -> Dict[str, Any] | None:
        """Retourne les données santé extraites du JSON."""
        if self.evaluation_data and "sante" in self.evaluation_data:
            return self.evaluation_data["sante"]
        return None

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<PatientEvaluation(id={self.id}, patient_id={self.patient_id}, gir={self.gir_score})>"

    def validate(self, user_id: int) -> None:
        """Valide l'évaluation."""
        self.validated_at = datetime.now(timezone.utc)
        self.validated_by = user_id

    def extract_gir_score(self) -> int | None:
        """Extrait le score GIR depuis les données JSON."""
        if self.aggir_data and "GIR" in self.aggir_data:
            return self.aggir_data["GIR"]
        return None

    def update_gir_score(self) -> None:
        """Met à jour gir_score depuis les données JSON."""
        self.gir_score = self.extract_gir_score()
