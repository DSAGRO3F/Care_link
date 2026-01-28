"""
Modèle PatientEvaluation - Évaluations patient (JSON Schema).

Ce module définit la table `patient_evaluations` qui stocke les évaluations
des patients au format JSON (validées par JSON Schema).
"""

from datetime import date, datetime, timezone, timedelta
from typing import TYPE_CHECKING, Any, Dict, List

from sqlalchemy import String, Integer, Date, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin, VersionedMixin
from app.models.types import JSONBCompatible
from app.models.enums import EvaluationSchemaType, EvaluationStatus

if TYPE_CHECKING:
    from app.models.user.user import User
    from app.models.patient.patient import Patient
    from app.models.patient.evaluation_session import EvaluationSession
    from app.models.careplan.care_plan import CarePlan
    from app.models.tenants.tenant import Tenant


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

    # === Multi-tenant ===

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant propriétaire de cet enregistrement"
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

    # --- Gestion multi-session (NOUVEAU) ---

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="DRAFT",
        doc="Statut de l'évaluation",
        info={
            "description": "Statut courant de l'évaluation",
            "enum": [e.value for e in EvaluationStatus]
        }
    )

    completion_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Pourcentage de complétion (0-100)",
        info={"description": "Progression de la saisie"}
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date d'expiration du brouillon",
        info={"description": "J+7 après création si non validée"}
    )

    # --- Validation double (médecin coord. + CD) ---

    medical_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date de validation par le médecin coordonnateur"
    )

    medical_validated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID du médecin coordonnateur valideur"
    )

    department_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date de validation par le Conseil Départemental"
    )

    department_validator_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        doc="Nom du valideur CD (externe au système)"
    )

    department_validator_reference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Référence/matricule du valideur CD"
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

    care_plans: Mapped[List["CarePlan"]] = relationship(
        "CarePlan",
        back_populates="source_evaluation",
        doc="Plans d'aide issus de cette évaluation"
    )

    # Relation vers les sessions de saisie (NOUVEAU)
    sessions: Mapped[List["EvaluationSession"]] = relationship(
        "EvaluationSession",
        back_populates="evaluation",
        cascade="all, delete-orphan",
        order_by="EvaluationSession.started_at",
        doc="Sessions de saisie de l'évaluation"
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

    @property
    def is_expired(self) -> bool:
        """Retourne True si l'évaluation a expiré."""
        if self.expires_at and self.status == "DRAFT":
            expires = self.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) > expires
        return False

    @property
    def is_complete(self) -> bool:
        """Retourne True si toutes les variables sont saisies."""
        return self.completion_percent == 100

    @property
    def is_fully_validated(self) -> bool:
        """Retourne True si validée par médecin ET conseil départemental."""
        return (
                self.medical_validated_at is not None
                and self.department_validated_at is not None
        )

    @property
    def days_until_expiration(self) -> int | None:
        """Retourne le nombre de jours avant expiration."""
        if self.expires_at and self.status == "DRAFT":
            expires = self.expires_at
            # S'assurer que expires_at a un timezone (protection SQLite/tests)
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            delta = expires - datetime.now(timezone.utc)
            return max(0, delta.days)
        return None

    @property
    def current_session(self) -> "EvaluationSession | None":
        """Retourne la session en cours si elle existe."""
        for session in self.sessions:
            if session.status == "IN_PROGRESS":
                return session
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

    def set_expiration(self, days: int = 7) -> None:
        """Définit la date d'expiration (J+X)."""
        self.expires_at = datetime.now(timezone.utc) + timedelta(days=days)

    def check_expiration(self) -> bool:
        """Vérifie et met à jour le statut si expiré."""
        if self.is_expired and self.status == "DRAFT":
            self.status = "EXPIRED"
            return True
        return False

    def submit_for_validation(self) -> None:
        """
        Soumet l'évaluation pour validation médicale.

        Note: La validation JSON Schema est effectuée dans le service.
        Cette méthode ne fait que changer le statut.
        """
        if self.status not in ["DRAFT", "PENDING_COMPLETION", "COMPLETE"]:
            raise ValueError(f"Impossible de soumettre depuis le statut {self.status}")

        self.status = "PENDING_MEDICAL"

    def validate_medical(self, user_id: int) -> None:
        """Validation par le médecin coordonnateur."""
        self.medical_validated_at = datetime.now(timezone.utc)
        self.medical_validated_by = user_id
        self.status = "PENDING_DEPARTMENT"

    def validate_department(self, validator_name: str, reference: str) -> None:
        """Validation par le Conseil Départemental."""
        self.department_validated_at = datetime.now(timezone.utc)
        self.department_validator_name = validator_name
        self.department_validator_reference = reference
        self.validated_at = datetime.now(timezone.utc)
        self.status = "VALIDATED"

    def update_completion(self) -> None:
        """Recalcule le pourcentage de complétion."""
        if not self.evaluation_data:
            self.completion_percent = 0
            return

        aggir_data = self.evaluation_data.get("aggir", {})
        variables = aggir_data.get("AggirVariable", [])

        total_variables = 17  # Variables AGGIR officielles
        completed = sum(1 for v in variables if v.get("Resultat") is not None)

        self.completion_percent = int((completed / total_variables) * 100)
