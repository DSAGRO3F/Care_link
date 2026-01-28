"""
Modèle Country - Pays.

Ce module définit la table `countries` qui représente les pays
dans lesquels CareLink opère.
"""

from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin, StatusMixin

if TYPE_CHECKING:
    from app.models.organization.entity import Entity


class Country(TimestampMixin, StatusMixin, Base):
    """
    Représente un pays dans le système CareLink.
    
    Les pays sont le niveau supérieur de la hiérarchie géographique.
    Chaque pays peut contenir plusieurs entités de soins.
    
    Attributes:
        id: Identifiant unique
        name: Nom du pays (France, Belgique, Suisse...)
        country_code: Code ISO 3166-1 alpha-2 (FR, BE, CH...)
        entities: Liste des entités de soins dans ce pays
    
    Example:
        france = Country(
            name="France",
            country_code="FR"
        )
    """
    
    __tablename__ = "countries"
    __table_args__ = {
        "comment": "Table des pays où CareLink est déployé"
    }
    
    # === Colonnes ===
    
    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du pays",
        info={
            "description": "Clé primaire auto-incrémentée"
        }
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Nom complet du pays",
        info={
            "description": "Nom du pays (France, Belgique, Suisse...)",
            "example": "France"
        }
    )
    
    country_code: Mapped[str] = mapped_column(
        String(2),
        unique=True,
        nullable=False,
        doc="Code ISO 3166-1 alpha-2 du pays",
        info={
            "description": "Code pays à 2 lettres selon norme ISO",
            "example": "FR",
            "pattern": "^[A-Z]{2}$"
        }
    )
    
    # === Relations ===
    
    entities: Mapped[List["Entity"]] = relationship(
        "Entity",
        back_populates="country",
        lazy="selectin",
        doc="Entités de soins situées dans ce pays"
    )
    
    # === Méthodes ===
    
    def __repr__(self) -> str:
        return f"<Country(id={self.id}, name='{self.name}', code='{self.country_code}')>"
    
    def __str__(self) -> str:
        return f"{self.name} ({self.country_code})"
