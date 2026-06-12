"""
Modèle FamilyReferentLink - Liens compte famille ↔ patient (Phase 4 bis B40-J1).

Matérialise l'autorisation d'un compte famille (FAMILY_REFERENT) à accéder
à la fiche minimisée d'un patient. Approche Option ζ du plan B40-J1 §6 étape 5 :
snapshot JSONB du contact d'origine (pas de FK vers patient_contacts car les
contacts vivent dans le JSONB `evaluation_data` de PatientEvaluation).

Convention candidate (à promouvoir J8) : "table dédiée pour les liens
famille-patient — ne jamais étendre `user_tenant_assignments` pour porter
une sémantique famille" (PS-1).

Référence : plan_B40_J1_27_05_2026.md §6 étape 5, décisions PS-1, PS-6, PS-10.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin


if TYPE_CHECKING:
    from app.models.patient.patient import Patient
    from app.models.tenants.tenant import Tenant
    from app.models.user.user import User


class FamilyReferentLink(TimestampMixin, Base):
    """
    Lien compte famille ↔ patient avec snapshot du contact d'origine.

    Un même compte utilisateur (rôle FAMILY_REFERENT) peut être lié à plusieurs
    patients sur plusieurs tenants. L'unicité est garantie au niveau du couple
    (user_id, patient_id) parmi les liens actifs (revoked_at IS NULL) via un
    index unique partiel — PS-6 du plan B40-J1.

    Éligibilité D28 : `personneConfiance=true` OR `responsableLegal=true` dans
    le contact d'origine. Vérification déléguée au service B40-J6 (UI admin
    invitations). Le snapshot conserve les booléens vrais à la création — usage
    audit/traçabilité.
    """

    __tablename__ = "family_referent_links"
    __table_args__ = (
        Index("ix_family_referent_links_patient", "patient_id"),
        Index("ix_family_referent_links_user", "user_id"),
        # PS-6 — Un seul lien actif par couple (user, patient) parmi les non révoqués
        Index(
            "uq_family_referent_links_active",
            "user_id",
            "patient_id",
            unique=True,
            postgresql_where="revoked_at IS NULL",
        ),
        {"comment": "Liens famille-patient (Phase 4 bis B40-J1)"},
    )

    # === Clé primaire ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du lien",
    )

    # === Multi-tenant ===

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant propriétaire de cet enregistrement",
    )

    # === Acteurs ===

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Compte famille bénéficiaire de l'accès",
    )

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        doc="Patient sur lequel l'accès est accordé",
    )

    # === Snapshot du contact (PS-10 ζ) ===

    original_contact_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="Snapshot dénormalisé du contact au moment de la création",
        info={
            "description": (
                "Audit/traçabilité : préserve l'état du contact (nom, prénom, email, "
                "personne_confiance, responsable_legal, dates de désignation, "
                "nature_lien) à la création. Les contacts vivent dans le JSONB "
                "evaluation_data de PatientEvaluation — pas de FK directe possible. "
                "PS-10 ζ du plan B40-J1."
            ),
            "example": {
                "nom": "Dupont",
                "prenom": "Marie",
                "email": "marie.dupont@example.com",
                "personne_confiance": True,
                "responsable_legal": False,
                "date_designation_pc": "2026-03-15",
                "nature_lien": "fille",
            },
        },
    )

    # === Octroi ===

    granted_by_admin_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        doc="Admin GCSMS ayant accordé l'accès",
        info={
            "description": (
                "Pas de CASCADE volontaire (vs user_id/patient_id) — l'audit "
                "historique de qui a accordé l'accès reste préservé même si "
                "l'admin disparaît"
            ),
        },
    )

    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="Date et heure d'octroi du lien",
    )

    # === Révocation (D28 — révocation tracée) ===

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date et heure de révocation (NULL = lien actif)",
    )

    revoked_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Motif libre de la révocation (utile pour UI J6)",
    )

    # === Relations ===

    tenant: Mapped[Tenant] = relationship("Tenant", doc="Tenant propriétaire")

    user: Mapped[User] = relationship(
        "User",
        foreign_keys=[user_id],
        doc="Compte famille bénéficiaire",
    )

    patient: Mapped[Patient] = relationship(
        "Patient",
        foreign_keys=[patient_id],
        doc="Patient sur lequel l'accès est accordé",
    )

    granted_by_admin: Mapped[User] = relationship(
        "User",
        foreign_keys=[granted_by_admin_user_id],
        doc="Admin ayant accordé l'accès",
    )

    # === Propriétés ===

    @property
    def is_active(self) -> bool:
        """Indique si le lien est actif (non révoqué)."""
        return self.revoked_at is None

    @property
    def is_revoked(self) -> bool:
        """Indique si le lien a été révoqué."""
        return self.revoked_at is not None

    # === Méthodes ===

    def revoke(self, reason: str | None = None) -> None:
        """
        Révoque le lien (idempotent).

        Args:
            reason: Motif libre de la révocation
        """
        if self.revoked_at is None:
            self.revoked_at = datetime.now(UTC)
        if reason:
            self.revoked_reason = reason

    def __repr__(self) -> str:
        status = "active" if self.is_active else "revoked"
        return (
            f"<FamilyReferentLink(id={self.id}, user_id={self.user_id}, "
            f"patient_id={self.patient_id}, {status})>"
        )
