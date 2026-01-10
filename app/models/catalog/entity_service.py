"""
Entity Services - Services activés par chaque entité.

Ce module gère l'association entre les entités (SSIAD, SAAD, etc.) et les
services qu'elles proposent à partir du catalogue national.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.organization.entity import Entity
    from app.models.catalog.service_template import ServiceTemplate


class EntityService(Base, TimestampMixin):
    """
    Service proposé par une entité.
    
    Lie une entité à un service du catalogue avec des paramètres
    spécifiques (tarif, capacité, conditions).
    
    Attributes:
        entity_id: Entité concernée
        service_template_id: Service du catalogue
        is_active: Service actuellement proposé
        price_euros: Tarif pratiqué (peut différer du standard)
        max_capacity_week: Capacité max hebdomadaire
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
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # === Clés étrangères ===
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Entité concernée"
    )
    
    service_template_id: Mapped[int] = mapped_column(
        ForeignKey("service_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Service du catalogue"
    )
    
    # === Paramètres ===
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Service actuellement proposé"
    )
    
    price_euros: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Tarif pratiqué en euros (NULL = tarif standard)"
    )
    
    max_capacity_week: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Capacité max hebdomadaire (nombre d'interventions)"
    )
    
    custom_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Durée personnalisée (NULL = durée standard du template)"
    )
    
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Conditions particulières"
    )
    
    # === Relations ===
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="entity_services"
    )
    
    service_template: Mapped["ServiceTemplate"] = relationship(
        "ServiceTemplate",
        back_populates="entity_services"
    )
    
    # === Méthodes ===
    def __str__(self) -> str:
        return f"{self.entity.name} - {self.service_template.name}"
    
    def __repr__(self) -> str:
        return f"<EntityService(entity_id={self.entity_id}, service_template_id={self.service_template_id})>"
    
    @property
    def effective_duration_minutes(self) -> int:
        """Retourne la durée effective (personnalisée ou standard)."""
        return self.custom_duration_minutes or self.service_template.default_duration_minutes
    
    @property
    def effective_price(self) -> Decimal | None:
        """Retourne le tarif effectif."""
        return self.price_euros  # Pas de tarif standard dans le template pour l'instant
