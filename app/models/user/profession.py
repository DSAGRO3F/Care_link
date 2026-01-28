"""
Modèle Profession - Professions réglementées.

Ce module définit la table `professions` qui représente les professions
de santé réglementées (Médecin, Infirmier, Aide-soignant, etc.).

Important :
- Une profession est un diplôme d'État, elle ne change pas.
- Un rôle (dans la table `roles`) est une fonction dans CareLink.
- Exemple : Marie est Infirmière (profession) et Coordinatrice (rôle).
"""

from typing import TYPE_CHECKING, List

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin
from app.models.enums import ProfessionCategory

if TYPE_CHECKING:
    from app.models.user.user import User
    from app.models.catalog.service_template import ServiceTemplate


class Profession(TimestampMixin, Base):
    """
    Représente une profession de santé réglementée.
    
    Les professions sont des diplômes d'État reconnus officiellement.
    Elles déterminent notamment si un numéro RPPS est requis.
    
    Attributes:
        id: Identifiant unique
        name: Nom de la profession (Médecin, Infirmier...)
        code: Code officiel RPPS/ADELI
        category: Catégorie (MEDICAL, PARAMEDICAL, ADMINISTRATIVE)
        requires_rpps: La profession nécessite-t-elle un numéro RPPS ?
        users: Utilisateurs ayant cette profession
    
    Example:
        infirmier = Profession(
            name="Infirmier",
            code="60",
            category=ProfessionCategory.PARAMEDICAL,
            requires_rpps=True
        )
    """
    
    __tablename__ = "professions"
    __table_args__ = {
        "comment": "Table des professions de santé réglementées"
    }
    
    # === Colonnes ===
    
    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de la profession",
        info={
            "description": "Clé primaire auto-incrémentée"
        }
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        doc="Nom de la profession",
        info={
            "description": "Nom officiel de la profession de santé",
            "example": "Infirmier"
        }
    )
    
    code: Mapped[str | None] = mapped_column(
        String(10),
        unique=True,
        nullable=True,
        doc="Code officiel RPPS/ADELI de la profession",
        info={
            "description": "Code profession dans le référentiel national",
            "example": "60"
        }
    )
    
    category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Catégorie de la profession",
        info={
            "description": "Classification de la profession",
            "enum": [e.value for e in ProfessionCategory],
            "example": "PARAMEDICAL"
        }
    )
    
    requires_rpps: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        doc="La profession nécessite-t-elle un numéro RPPS ?",
        info={
            "description": "True si un RPPS est obligatoire pour exercer",
            "default": True
        }
    )
    
    # === Relations ===
    
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="profession",
        doc="Utilisateurs ayant cette profession"
    )

    # === relation service_templates dans profession.py ===
    service_templates: Mapped[List["ServiceTemplate"]] = relationship(
        "ServiceTemplate",
        back_populates="required_profession",
        doc="Services nécessitant cette profession"
    )
    
    # === Méthodes ===
    
    def __repr__(self) -> str:
        return f"<Profession(id={self.id}, name='{self.name}', code='{self.code}')>"
    
    def __str__(self) -> str:
        return self.name
    
    @property
    def is_medical(self) -> bool:
        """Retourne True si la profession est médicale."""
        return self.category == ProfessionCategory.MEDICAL.value
    
    @property
    def is_paramedical(self) -> bool:
        """Retourne True si la profession est paramédicale."""
        return self.category == ProfessionCategory.PARAMEDICAL.value


# === Données initiales (seed) ===
# Le code "10", par exemple pour Médecin, provient de la nomenclature officielle des professions de santé gérée par l'ANS (Agence du Numérique en Santé), utilisée notamment dans le RPPS.
# C'est le code profession à 2 chiffres qui identifie chaque catégorie de professionnel de santé. Par exemple :
#
# 10 = Médecin
# 21 = Pharmacien
# 40 = Chirurgien-dentiste
# 60 = Infirmier
# 70 = Masseur-kinésithérapeute

INITIAL_PROFESSIONS = [
    {"name": "Médecin", "code": "10", "category": "MEDICAL", "requires_rpps": True},
    {"name": "Pharmacien", "code": "21", "category": "MEDICAL", "requires_rpps": True},
    {"name": "Chirurgien-dentiste", "code": "40", "category": "MEDICAL", "requires_rpps": True},
    {"name": "Sage-femme", "code": "50", "category": "MEDICAL", "requires_rpps": True},
    {"name": "Infirmier", "code": "60", "category": "PARAMEDICAL", "requires_rpps": True},
    {"name": "Masseur-kinésithérapeute", "code": "70", "category": "PARAMEDICAL", "requires_rpps": True},
    {"name": "Pédicure-podologue", "code": "80", "category": "PARAMEDICAL", "requires_rpps": True},
    {"name": "Ergothérapeute", "code": "91", "category": "PARAMEDICAL", "requires_rpps": True},
    {"name": "Psychomotricien", "code": "92", "category": "PARAMEDICAL", "requires_rpps": True},
    {"name": "Orthophoniste", "code": "94", "category": "PARAMEDICAL", "requires_rpps": True},
    {"name": "Orthoptiste", "code": "95", "category": "PARAMEDICAL", "requires_rpps": True},
    {"name": "Aide-soignant", "code": "93", "category": "PARAMEDICAL", "requires_rpps": False},
    {"name": "Auxiliaire de puériculture", "code": "96", "category": "PARAMEDICAL", "requires_rpps": False},
    {"name": "Diététicien", "code": "97", "category": "PARAMEDICAL", "requires_rpps": True},
    {"name": "Psychologue", "code": "98", "category": "PARAMEDICAL", "requires_rpps": True},
    {"name": "Administratif", "code": None, "category": "ADMINISTRATIVE", "requires_rpps": False},
]
