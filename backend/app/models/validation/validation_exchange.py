"""
Modèle ValidationExchange — Fil d'échange du portail de validation (Phase 4 bis B40-J3).

Ce module définit la table `validation_exchanges` : chaque ligne est une entrée
horodatée du fil de discussion rattaché à une `ValidationRequest`. C'est la pièce
maîtresse du portail — elle matérialise la concertation et remplace l'audit-texte
`_append_audit` (#109) pour la partie visible par les humains.

Une entrée est à la fois un message ET, le cas échéant, une décision : `action_type`
distingue le simple commentaire de l'acte décisionnel (cf. ExchangeActionType).

Rattachement (décision session — Option A) : FK vers `validation_request_id`. Le fil
complet d'un dossier se reconstruit en agrégeant les entrées de toutes les VR du même
`evaluation_id` / `care_plan_id` (chaîne explicitée par `ValidationRequest.previous_vr_id`),
triées par `created_at`.

Sécurité : RLS par tenant standard (calquée validation_requests). La finesse `visibility`
(INTERNAL_ONLY / SHARED_EXTERNAL) est portée au niveau service + permissions, pas en RLS.

Référence : cadrage_ValidationExchange.md §2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum as SQLEnum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.enums import ExchangeActionType, ExchangeVisibility
from app.models.mixins import TimestampMixin


if TYPE_CHECKING:
    from app.models.tenants.tenant import Tenant
    from app.models.user.user import User
    from app.models.validation.validation_request import ValidationRequest


class ValidationExchange(TimestampMixin, Base):
    """Entrée du fil d'échange rattachée à une demande de validation.

    Cycle de vie : créée à chaque acte (commentaire, re-soumission, décision,
    transmission). Jamais modifiée après coup — le fil est un journal append-only
    (les corrections passent par une nouvelle entrée, pas par l'édition).
    """

    __tablename__ = "validation_exchanges"
    __table_args__ = (
        Index(
            "ix_validation_exchanges_vr_created",
            "validation_request_id",
            "created_at",
        ),
        Index("ix_validation_exchanges_tenant_id", "tenant_id"),
        {"comment": "Entrées du fil d'échange de validation (Phase 4 bis B40-J3)"},
    )

    # === Clé primaire ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de l'entrée de fil",
        info={"description": "Clé primaire auto-incrémentée"},
    )

    # === Multi-tenant ===

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant propriétaire de cet enregistrement",
    )

    # === Rattachement (Option A — FK vers la VR active au moment de l'écriture) ===

    validation_request_id: Mapped[int] = mapped_column(
        ForeignKey("validation_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Demande de validation à laquelle cette entrée est rattachée",
    )

    # === Auteur ===

    author_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Auteur de l'entrée (NULL si compte supprimé)",
    )

    author_role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Rôle de l'auteur au moment de l'écriture (figé pour la trace)",
        info={
            "description": (
                "Libellé figé : COORDINATOR, INTERNAL_VALIDATOR, MEDICAL_VALIDATOR, "
                "FUNDING_VALIDATOR (instantané du rôle, pas une FK)"
            ),
        },
    )

    # === Nature de l'entrée ===

    action_type: Mapped[ExchangeActionType] = mapped_column(
        SQLEnum(
            ExchangeActionType,
            name="exchange_action_type_enum",
            create_constraint=True,
        ),
        nullable=False,
        doc="Type d'action : message simple ou acte décisionnel",
        info={
            "description": (
                "SUBMIT, COMMENT, RESUBMIT, VALIDATE, REQUEST_INFO, INVALIDATE, TRANSMIT"
            ),
            "enum": [e.value for e in ExchangeActionType],
        },
    )

    visibility: Mapped[ExchangeVisibility] = mapped_column(
        SQLEnum(
            ExchangeVisibility,
            name="exchange_visibility_enum",
            create_constraint=True,
        ),
        nullable=False,
        default=ExchangeVisibility.SHARED_EXTERNAL,
        server_default=ExchangeVisibility.SHARED_EXTERNAL.value,
        doc="Portée de visibilité (filet : isolation tenant en RLS ; finesse au service)",
        info={
            "description": "INTERNAL_ONLY (GCSMS seul) ou SHARED_EXTERNAL (GCSMS + externe)",
            "enum": [e.value for e in ExchangeVisibility],
        },
    )

    # === Contenu ===

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Corps libre du message (requis si REQUEST_INFO/INVALIDATE — porté au service)",
    )

    attachments: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
        doc="Pièces jointes de l'entrée (structure verrouillée B40-J5, comme la VR)",
    )

    # === Relations ===

    tenant: Mapped[Tenant] = relationship("Tenant", doc="Tenant propriétaire")

    validation_request: Mapped[ValidationRequest] = relationship(
        "ValidationRequest",
        back_populates="exchanges",
        doc="Demande de validation rattachée",
    )

    author: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[author_user_id],
        doc="Auteur de l'entrée",
    )

    # === Propriétés ===

    @property
    def is_decision(self) -> bool:
        """Indique si l'entrée porte un acte décisionnel (vs simple commentaire/transition)."""
        return self.action_type in (
            ExchangeActionType.VALIDATE,
            ExchangeActionType.REQUEST_INFO,
            ExchangeActionType.INVALIDATE,
        )

    @property
    def is_internal_only(self) -> bool:
        """Indique si l'entrée est réservée aux acteurs internes au GCSMS."""
        return self.visibility == ExchangeVisibility.INTERNAL_ONLY

    def __repr__(self) -> str:
        return (
            f"<ValidationExchange(id={self.id}, vr_id={self.validation_request_id}, "
            f"action={self.action_type.value}, visibility={self.visibility.value})>"
        )
