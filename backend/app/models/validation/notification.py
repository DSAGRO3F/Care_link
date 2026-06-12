"""
Modèle Notification - Notifications utilisateur (Phase 4 bis B40-J1).

Notification générique pour le portail valideur et les événements liés.
Canal unique côté frontend (D22 β + D26 du cadrage Phase 4 bis) : polling 30s,
badge compteur, marquage lu/non-lu.

Référence : plan_B40_J1_27_05_2026.md §6 étape 3, décision PS-2.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.enums import NotificationType
from app.models.mixins import TimestampMixin


if TYPE_CHECKING:
    from app.models.careplan.care_plan import CarePlan
    from app.models.patient.patient_evaluation import PatientEvaluation
    from app.models.tenants.tenant import Tenant
    from app.models.user.user import User
    from app.models.validation.validation_request import ValidationRequest


class Notification(TimestampMixin, Base):
    """
    Notification utilisateur générique.

    Une notification cible un utilisateur destinataire unique et peut référencer
    0..3 objets (évaluation, plan d'aide, demande de validation). Pas de CHECK
    polymorphique — une notification peut légitimement référencer plusieurs
    objets ou aucun (cf. plan B40-J1 §6 étape 3).

    Sécurité (B40-J1 §6 étape 8) : RLS par utilisateur destinataire (pattern
    atypique — pas par tenant). Une notification est strictement privée à son
    destinataire.

    Décision de design (validée Session 25) : les objets référencés (Evaluation,
    CarePlan, ValidationRequest) n'exposent PAS de back_populates `notifications`.
    Asymétrie volontaire : Notification connaît ses objets, mais les objets ne
    maintiennent pas la liste de leurs notifications (lecture toujours côté
    destinataire, jamais côté objet).
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_recipient_is_read", "recipient_user_id", "is_read"),
        Index("ix_notifications_tenant", "tenant_id"),
        {
            "comment": "Notifications utilisateur (Phase 4 bis B40-J1)",
            # S9 (05/06/2026) — implicit_returning désactivé.
            # La RLS de lecture est atypique (par destinataire :
            # check_recipient_access). Or un INSERT ... RETURNING fait relire la
            # ligne insérée sous la politique SELECT : un acteur qui crée une
            # notification pour AUTRUI (médecin, soumetteur) ne peut pas la
            # relire → « new row violates row-level security policy ».
            # Sans RETURNING, l'id est récupéré via la séquence, sans relecture
            # de la ligne. La confidentialité destinataire reste intacte (la
            # politique SELECT est inchangée) ; on retire seulement l'étape de
            # relecture parasite. Cf. décision S9, option B (moindre privilège).
            "implicit_returning": False,
        },
    )

    # === Clé primaire ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de la notification",
    )

    # === Multi-tenant ===

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant propriétaire de cet enregistrement",
    )

    # === Destinataire (RLS strict par utilisateur) ===

    recipient_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Utilisateur destinataire (unique — pattern RLS atypique)",
    )

    # === Contenu ===

    type: Mapped[NotificationType] = mapped_column(
        SQLEnum(
            NotificationType,
            name="notification_type_enum",
            create_constraint=True,
        ),
        nullable=False,
        doc="Type structuré de la notification",
        info={
            "description": "Permet l'agrégation/filtrage côté UI",
            "enum": [e.value for e in NotificationType],
        },
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Titre court (badge, liste compacte)",
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Corps libre de la notification",
    )

    link_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="URL de redirection vers l'écran concerné (NULL si pas d'action)",
    )

    # === État lu/non-lu ===

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="Indicateur lu/non-lu (vérifié pour le badge compteur)",
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date et heure de marquage lu",
    )

    # === Références aux objets liés (0..3, pas de CHECK polymorphique) ===

    related_evaluation_id: Mapped[int | None] = mapped_column(
        ForeignKey("patient_evaluations.id", ondelete="CASCADE"),
        nullable=True,
        doc="Évaluation liée à la notification",
    )

    related_care_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("care_plans.id", ondelete="CASCADE"),
        nullable=True,
        doc="Plan d'aide lié à la notification",
    )

    related_validation_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("validation_requests.id", ondelete="CASCADE"),
        nullable=True,
        doc="Demande de validation liée à la notification",
    )

    # === Relations ===

    tenant: Mapped[Tenant] = relationship("Tenant", doc="Tenant propriétaire")

    recipient: Mapped[User] = relationship(
        "User",
        foreign_keys=[recipient_user_id],
        doc="Utilisateur destinataire",
    )

    related_evaluation: Mapped[PatientEvaluation | None] = relationship(
        "PatientEvaluation",
        foreign_keys=[related_evaluation_id],
        doc="Évaluation liée à la notification",
    )

    related_care_plan: Mapped[CarePlan | None] = relationship(
        "CarePlan",
        foreign_keys=[related_care_plan_id],
        doc="Plan d'aide lié à la notification",
    )

    related_validation_request: Mapped[ValidationRequest | None] = relationship(
        "ValidationRequest",
        foreign_keys=[related_validation_request_id],
        doc="Demande de validation liée à la notification",
    )

    # === Méthodes ===

    def mark_as_read(self) -> None:
        """Marque la notification comme lue (idempotent)."""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.now(UTC)

    def __repr__(self) -> str:
        return (
            f"<Notification(id={self.id}, type={self.type.value}, "
            f"recipient_user_id={self.recipient_user_id}, is_read={self.is_read})>"
        )

