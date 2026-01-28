"""
Modèle PatientDocument - Documents générés pour les patients.

Ce module définit la table `patient_documents` qui stocke les métadonnées
des documents générés par LLM/RAG (PPA, PPCS, Recommandations).
Le fichier binaire (PDF/DOCX) est stocké sur le filesystem/object storage.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict

from sqlalchemy import String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.enums import DocumentType, DocumentFormat
from app.models.mixins import TimestampMixin
from app.models.types import JSONBCompatible

if TYPE_CHECKING:
    from app.models.user.user import User
    from app.models.patient.patient import Patient
    from app.models.patient.patient_evaluation import PatientEvaluation


class PatientDocument(TimestampMixin, Base):
    """
    Représente un document généré pour un patient.

    Les documents sont générés par LLM (PPA, PPCS) ou RAG (Recommandations)
    à partir du contexte patient (évaluations JSON Schema).

    Attributes:
        id: Identifiant unique
        patient_id: ID du patient concerné
        document_type: Type de document (PPA, PPCS, RECOMMENDATION, OTHER)
        title: Titre du document
        description: Description ou résumé du contenu
        source_evaluation_id: Évaluation source (optionnel)
        generation_prompt: Prompt envoyé au LLM (audit)
        generation_context: Contexte JSON envoyé au LLM (reproductibilité)
        file_path: Chemin vers le fichier stocké
        file_format: Format du fichier (pdf, docx)
        file_size_bytes: Taille du fichier
        file_hash: Hash SHA-256 (intégrité)
        generated_at: Date de génération
        generated_by: Utilisateur ayant demandé la génération
    """

    __tablename__ = "patient_documents"
    __table_args__ = {
        "comment": "Documents générés pour les patients (PPA, PPCS, Recommandations)"
    }

    # === Colonnes ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du document"
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
        doc="ID du patient concerné"
    )

    # --- Type de document ---

    document_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        doc="Type de document",
        info={
            "enum": [e.value for e in DocumentType],
            "example": "PPA"
        }
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Titre du document"
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Description ou résumé du contenu"
    )

    # --- Source de génération (traçabilité LLM/RAG) ---

    source_evaluation_id: Mapped[int | None] = mapped_column(
        ForeignKey("patient_evaluations.id", ondelete="SET NULL"),
        nullable=True,
        doc="Évaluation source pour PPA/PPCS"
    )

    generation_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Question/prompt envoyé au LLM (pour audit)"
    )

    generation_context: Mapped[Dict[str, Any] | None] = mapped_column(
        JSONBCompatible,
        nullable=True,
        doc="Contexte JSON envoyé au LLM (pour reproductibilité)"
    )

    # --- Fichier ---

    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Chemin relatif vers le fichier stocké"
    )

    file_format: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="Format du fichier",
        info={
            "enum": [e.value for e in DocumentFormat],
            "example": "pdf"
        }
    )

    file_size_bytes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Taille du fichier en octets"
    )

    file_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="Hash SHA-256 du fichier (intégrité)"
    )

    # --- Métadonnées ---

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Date/heure de génération"
    )

    generated_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        doc="Utilisateur ayant demandé la génération"
    )

    # === Relations ===

    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="documents",
        doc="Patient concerné"
    )

    source_evaluation: Mapped["PatientEvaluation | None"] = relationship(
        "PatientEvaluation",
        foreign_keys="[PatientDocument.source_evaluation_id]",
        doc="Évaluation source"
    )

    generator: Mapped["User"] = relationship(
        "User",
        foreign_keys="[PatientDocument.generated_by]",
        doc="Utilisateur ayant généré le document"
    )

    # === Propriétés ===

    @property
    def is_ppa(self) -> bool:
        """Retourne True si c'est un PPA."""
        return self.document_type == DocumentType.PPA.value

    @property
    def is_ppcs(self) -> bool:
        """Retourne True si c'est un PPCS."""
        return self.document_type == DocumentType.PPCS.value

    @property
    def is_recommendation(self) -> bool:
        """Retourne True si c'est une recommandation."""
        return self.document_type == DocumentType.RECOMMENDATION.value

    @property
    def file_extension(self) -> str:
        """Retourne l'extension du fichier."""
        return f".{self.file_format.lower()}"

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<PatientDocument(id={self.id}, type={self.document_type}, patient_id={self.patient_id})>"

    def __str__(self) -> str:
        return f"{self.document_type}: {self.title}"