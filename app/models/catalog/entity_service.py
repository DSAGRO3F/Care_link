"""
Modèle EntityService - Services activés par chaque entité.

Ce module définit la table `entity_services` qui gère l'association entre
les entités (SSIAD, SAAD, etc.) et les services qu'elles proposent à partir
du catalogue national (service_templates).

Chaque entité peut personnaliser les paramètres d'un service :
- Tarif pratiqué
- Durée personnalisée
- Capacité maximale
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Integer, Boolean, Text, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.organization.entity import Entity
    from app.models.catalog.service_template import ServiceTemplate
    from app.models.tenants.tenant import Tenant


class EntityService(TimestampMixin, Base):
    """
    Service proposé par une entité.

    Lie une entité à un service du catalogue national avec des paramètres
    spécifiques (tarif, capacité, conditions). Permet à chaque structure
    de personnaliser son offre de services.

    Attributes:
        id: Identifiant unique
        entity_id: Entité concernée
        service_template_id: Service du catalogue
        is_active: Service actuellement proposé
        price_euros: Tarif pratiqué (peut différer du standard)
        max_capacity_week: Capacité max hebdomadaire
        custom_duration_minutes: Durée personnalisée
        notes: Conditions particulières

    Example:
        >>> entity_service = EntityService(
        ...     entity_id=ssiad.id,
        ...     service_template_id=toilette.id,
        ...     is_active=True,
        ...     price_euros=Decimal("25.50")
        ... )
    """

    __tablename__ = "entity_services"
    __table_args__ = (
        UniqueConstraint("entity_id", "service_template_id", name="uq_entity_service"),
        {"comment": "Services proposés par chaque entité"}
    )

    # === Clé primaire ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de l'association entité-service",
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

    # === Clés étrangères ===

    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Entité proposant ce service",
        info={
            "description": "FK vers entities. Suppression en cascade",
            "example": 1
        }
    )

    service_template_id: Mapped[int] = mapped_column(
        ForeignKey("service_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Service du catalogue national",
        info={
            "description": "FK vers service_templates. Suppression en cascade",
            "example": 1
        }
    )

    # === Paramètres de l'offre ===

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Service actuellement proposé par l'entité",
        info={
            "description": "True si l'entité propose activement ce service",
            "default": True
        }
    )

    price_euros: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        doc="Tarif pratiqué en euros",
        info={
            "description": "Tarif horaire ou à l'acte. NULL = tarif standard",
            "unit": "EUR",
            "example": "25.50"
        }
    )

    max_capacity_week: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Capacité maximale hebdomadaire",
        info={
            "description": "Nombre max d'interventions de ce type par semaine",
            "unit": "interventions/semaine",
            "example": 50
        }
    )

    custom_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Durée personnalisée pour cette entité",
        info={
            "description": "Durée en minutes. NULL = durée standard du template",
            "unit": "minutes",
            "example": 45
        }
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Conditions particulières",
        info={
            "description": "Notes sur les conditions de réalisation du service"
        }
    )

    # === Relations ===

    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="entity_services",
        doc="Entité proposant ce service"
    )

    service_template: Mapped["ServiceTemplate"] = relationship(
        "ServiceTemplate",
        back_populates="entity_services",
        doc="Template du service (catalogue national)"
    )

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<EntityService(id={self.id}, entity_id={self.entity_id}, service_template_id={self.service_template_id})>"

    def __str__(self) -> str:
        entity_name = self.entity.name if self.entity else f"Entity#{self.entity_id}"
        service_name = self.service_template.name if self.service_template else f"Service#{self.service_template_id}"
        return f"{entity_name} - {service_name}"

    @property
    def effective_duration_minutes(self) -> int:
        """Retourne la durée effective (personnalisée ou standard)."""
        if self.custom_duration_minutes is not None:
            return self.custom_duration_minutes
        return self.service_template.default_duration_minutes

    @property
    def effective_price(self) -> Decimal | None:
        """Retourne le tarif effectif (personnalisé ou None si non défini)."""
        return self.price_euros

    @property
    def has_custom_duration(self) -> bool:
        """Indique si une durée personnalisée est définie."""
        return self.custom_duration_minutes is not None

    @property
    def has_custom_price(self) -> bool:
        """Indique si un tarif personnalisé est défini."""
        return self.price_euros is not None

    @property
    def is_at_capacity(self) -> bool:
        """
        Indique si la capacité max est définie.
        Note: La vérification réelle nécessite de compter les interventions planifiées.
        """
        return self.max_capacity_week is not None