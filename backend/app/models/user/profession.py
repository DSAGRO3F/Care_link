"""
Modèle Profession - Professions réglementées.

Ce module définit la table `professions` qui représente les professions
de santé réglementées (Médecin, Infirmier, Aide-soignant, etc.).

Important :
- Une profession est un diplôme d'État, elle ne change pas.
- Un rôle (dans la table `roles`) est une fonction dans CareLink.
- Exemple : Marie est Infirmière (profession) et Coordinatrice (rôle).

Changelog :
    S2 : Ajout display_order, status. Référentiel étendu à 27 professions
         (6 MEDICAL, 12 PARAMEDICAL, 6 SOCIAL, 3 ADMINISTRATIVE).
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.enums import ProfessionCategory
from app.models.mixins import TimestampMixin


if TYPE_CHECKING:
    from app.models.catalog.service_template import ServiceTemplate
    from app.models.user.user import User


class Profession(TimestampMixin, Base):
    """
    Représente une profession de santé réglementée.

    Les professions sont des diplômes d'État reconnus officiellement.
    Elles déterminent notamment si un numéro RPPS est requis.

    Attributes:
        id: Identifiant unique
        name: Nom de la profession (Médecin généraliste, Infirmier diplômé d'État...)
        code: Code officiel RPPS/ADELI (ex: "60" pour IDE)
        category: Catégorie (MEDICAL, PARAMEDICAL, SOCIAL, ADMINISTRATIVE)
        requires_rpps: La profession nécessite-t-elle un numéro RPPS ?
        display_order: Ordre d'affichage dans les listes (S2)
        status: "active" ou "inactive" (S2)
        users: Utilisateurs ayant cette profession

    Example:
        ide = Profession(
            name="Infirmier diplômé d'État",
            code="60",
            category=ProfessionCategory.PARAMEDICAL,
            requires_rpps=True,
            display_order=100,
            status="active"
        )
    """

    __tablename__ = "professions"
    __table_args__ = {"comment": "Table des professions de santé réglementées"}

    # === Colonnes ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de la profession",
        info={"description": "Clé primaire auto-incrémentée"},
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        doc="Nom de la profession",
        info={
            "description": "Nom officiel de la profession de santé",
            "example": "Infirmier diplômé d'État",
        },
    )

    code: Mapped[str | None] = mapped_column(
        String(10),
        unique=True,
        nullable=True,
        doc="Code officiel RPPS/ADELI de la profession",
        info={"description": "Code profession dans le référentiel national", "example": "60"},
    )

    category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Catégorie de la profession",
        info={
            "description": "Classification de la profession",
            "enum": [e.value for e in ProfessionCategory],
            "example": "PARAMEDICAL",
        },
    )

    requires_rpps: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        doc="La profession nécessite-t-elle un numéro RPPS ?",
        info={"description": "True si un RPPS est obligatoire pour exercer", "default": True},
    )

    # --- Ajouts S2 ---

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Ordre d'affichage dans les listes",
        info={
            "description": "Tri métier : MEDICAL 10-49, PARAMEDICAL 100-200, SOCIAL 300-350, ADMINISTRATIVE 400-420"
        },
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        doc="Statut de la profession : active ou inactive",
        info={
            "description": "Permet de déprécier une profession sans la supprimer",
            "enum": ["active", "inactive"],
        },
    )

    # === Relations ===

    users: Mapped[list["User"]] = relationship(
        "User", back_populates="profession", doc="Utilisateurs ayant cette profession"
    )

    # === relation service_templates dans profession.py ===
    service_templates: Mapped[list["ServiceTemplate"]] = relationship(
        "ServiceTemplate",
        back_populates="required_profession",
        doc="Services nécessitant cette profession",
    )

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<Profession(id={self.id}, name='{self.name}', code='{self.code}', order={self.display_order})>"

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

    @property
    def is_social(self) -> bool:
        """Retourne True si la profession est sociale."""
        return self.category == ProfessionCategory.SOCIAL.value

    @property
    def is_active(self) -> bool:
        """Retourne True si la profession est active."""
        return self.status == "active"


# === Données initiales (seed) ===
#
# Référentiel des professions médico-sociales pour CareLink.
# Les codes numériques proviennent de la nomenclature officielle ANS (RPPS) :
#   10 = Médecin, 21 = Pharmacien, 40 = Chirurgien-dentiste,
#   50 = Sage-femme, 60 = Infirmier, 70 = Masseur-kinésithérapeute, etc.
#
# Les professions SOCIAL et ADMINISTRATIVE n'ont pas de code RPPS.
#
# Les display_order utilisent des plages espacées pour permettre
# des insertions futures sans renumérotation :
#   MEDICAL 10-49 | PARAMEDICAL 100-200 | SOCIAL 300-350 | ADMINISTRATIVE 400-420

INITIAL_PROFESSIONS = [
    # ── MEDICAL (display_order 10-49) ────────────────────────────────
    {
        "name": "Médecin généraliste",
        "code": "10",
        "category": "MEDICAL",
        "requires_rpps": True,
        "display_order": 10,
    },
    {
        "name": "Médecin gériatre",
        "code": None,
        "category": "MEDICAL",
        "requires_rpps": True,
        "display_order": 11,
    },
    {
        "name": "Médecin spécialiste (autre)",
        "code": None,
        "category": "MEDICAL",
        "requires_rpps": True,
        "display_order": 12,
    },
    {
        "name": "Pharmacien",
        "code": "21",
        "category": "MEDICAL",
        "requires_rpps": True,
        "display_order": 20,
    },
    {
        "name": "Chirurgien-dentiste",
        "code": "40",
        "category": "MEDICAL",
        "requires_rpps": True,
        "display_order": 30,
    },
    {
        "name": "Sage-femme",
        "code": "50",
        "category": "MEDICAL",
        "requires_rpps": True,
        "display_order": 40,
    },
    # ── PARAMEDICAL (display_order 100-200) ──────────────────────────
    {
        "name": "Infirmier diplômé d'État",
        "code": "60",
        "category": "PARAMEDICAL",
        "requires_rpps": True,
        "display_order": 100,
    },
    {
        "name": "Infirmier en pratique avancée",
        "code": None,
        "category": "PARAMEDICAL",
        "requires_rpps": True,
        "display_order": 101,
    },
    {
        "name": "Aide-soignant",
        "code": "93",
        "category": "PARAMEDICAL",
        "requires_rpps": False,
        "display_order": 110,
    },
    {
        "name": "Masseur-kinésithérapeute",
        "code": "70",
        "category": "PARAMEDICAL",
        "requires_rpps": True,
        "display_order": 120,
    },
    {
        "name": "Ergothérapeute",
        "code": "91",
        "category": "PARAMEDICAL",
        "requires_rpps": True,
        "display_order": 130,
    },
    {
        "name": "Psychomotricien",
        "code": "92",
        "category": "PARAMEDICAL",
        "requires_rpps": True,
        "display_order": 140,
    },
    {
        "name": "Orthophoniste",
        "code": "94",
        "category": "PARAMEDICAL",
        "requires_rpps": True,
        "display_order": 150,
    },
    {
        "name": "Orthoptiste",
        "code": "95",
        "category": "PARAMEDICAL",
        "requires_rpps": True,
        "display_order": 160,
    },
    {
        "name": "Pédicure-podologue",
        "code": "80",
        "category": "PARAMEDICAL",
        "requires_rpps": True,
        "display_order": 170,
    },
    {
        "name": "Diététicien",
        "code": "97",
        "category": "PARAMEDICAL",
        "requires_rpps": True,
        "display_order": 180,
    },
    {
        "name": "Auxiliaire de puériculture",
        "code": "96",
        "category": "PARAMEDICAL",
        "requires_rpps": False,
        "display_order": 190,
    },
    {
        "name": "Psychologue",
        "code": "98",
        "category": "PARAMEDICAL",
        "requires_rpps": True,
        "display_order": 200,
    },
    # ── SOCIAL (display_order 300-350) ───────────────────────────────
    {
        "name": "Assistant de service social",
        "code": None,
        "category": "SOCIAL",
        "requires_rpps": False,
        "display_order": 300,
    },
    {
        "name": "Éducateur spécialisé",
        "code": None,
        "category": "SOCIAL",
        "requires_rpps": False,
        "display_order": 310,
    },
    {
        "name": "Conseiller en économie sociale",
        "code": None,
        "category": "SOCIAL",
        "requires_rpps": False,
        "display_order": 320,
    },
    {
        "name": "Auxiliaire de vie sociale",
        "code": None,
        "category": "SOCIAL",
        "requires_rpps": False,
        "display_order": 330,
    },
    {
        "name": "Accompagnant éducatif et social",
        "code": None,
        "category": "SOCIAL",
        "requires_rpps": False,
        "display_order": 340,
    },
    {
        "name": "Technicien intervention sociale",
        "code": None,
        "category": "SOCIAL",
        "requires_rpps": False,
        "display_order": 350,
    },
    # ── ADMINISTRATIVE (display_order 400-420) ───────────────────────
    {
        "name": "Secrétaire médical",
        "code": None,
        "category": "ADMINISTRATIVE",
        "requires_rpps": False,
        "display_order": 400,
    },
    {
        "name": "Responsable administratif",
        "code": None,
        "category": "ADMINISTRATIVE",
        "requires_rpps": False,
        "display_order": 410,
    },
    {
        "name": "Agent d'accueil",
        "code": None,
        "category": "ADMINISTRATIVE",
        "requires_rpps": False,
        "display_order": 420,
    },
]
