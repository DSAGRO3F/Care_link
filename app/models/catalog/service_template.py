"""
Modèle ServiceTemplate - Catalogue national des types de prestations.

Ce module définit la table `service_templates` qui représente le référentiel
des services possibles (toilette, injection, courses, etc.) avec leurs
caractéristiques (durée, profession requise, etc.).

Ce catalogue est national et partagé par toutes les entités.
Chaque entité active ensuite les services qu'elle propose via `entity_services`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin, StatusMixin
from app.models.enums import ServiceCategory

if TYPE_CHECKING:
    from app.models.user.profession import Profession
    from app.models.catalog.entity_service import EntityService
    from app.models.careplan.care_plan_service import CarePlanService


class ServiceTemplate(TimestampMixin, StatusMixin, Base):
    """
    Modèle de service du catalogue national.

    Représente un type de prestation standardisé (toilette, injection,
    aide aux courses, etc.) avec ses caractéristiques.

    Attributes:
        id: Identifiant unique
        code: Code unique du service (TOILETTE_COMPLETE, INJECTION_SC...)
        name: Nom lisible du service
        category: Catégorie (SOINS, HYGIENE, REPAS, MOBILITE, COURSES, MENAGE...)
        description: Description détaillée
        required_profession_id: Profession requise (NULL si polyvalent)
        required_qualification: Qualification spécifique requise
        default_duration_minutes: Durée standard en minutes
        requires_prescription: Nécessite une ordonnance médicale
        is_medical_act: Est un acte médical/paramédical
        apa_eligible: Facturable dans le cadre de l'APA
        display_order: Ordre d'affichage dans les listes

    Example:
        >>> toilette = ServiceTemplate(
        ...     code="TOILETTE_COMPLETE",
        ...     name="Aide à la toilette complète",
        ...     category=ServiceCategory.HYGIENE,
        ...     default_duration_minutes=45,
        ...     required_profession_id=aide_soignant.id
        ... )
    """

    __tablename__ = "service_templates"
    __table_args__ = {
        "comment": "Catalogue national des types de prestations"
    }

    # === Clé primaire ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du service",
        info={
            "description": "Clé primaire auto-incrémentée"
        }
    )

    # === Identification ===

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Code unique du service",
        info={
            "description": "Code identifiant unique du service (majuscules, underscores)",
            "example": "TOILETTE_COMPLETE"
        }
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Nom lisible du service",
        info={
            "description": "Nom complet du service pour affichage",
            "example": "Aide à la toilette complète"
        }
    )

    category: Mapped[ServiceCategory] = mapped_column(
        SQLEnum(ServiceCategory, name="service_category_enum", create_constraint=True),
        nullable=False,
        index=True,
        doc="Catégorie du service",
        info={
            "description": "Classification du service",
            "enum": [e.value for e in ServiceCategory],
            "example": "HYGIENE"
        }
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Description détaillée du service",
        info={
            "description": "Description complète pour documentation et aide contextuelle"
        }
    )

    # === Exigences professionnelles ===

    required_profession_id: Mapped[int | None] = mapped_column(
        ForeignKey("professions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Profession requise pour réaliser ce service",
        info={
            "description": "FK vers professions. NULL = service polyvalent (toute profession)",
            "example": "ID de la profession Infirmier pour une injection"
        }
    )

    required_qualification: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Qualification spécifique requise",
        info={
            "description": "Qualification additionnelle au-delà de la profession",
            "example": "Diplôme IDE, Formation pansements complexes"
        }
    )

    # === Caractéristiques temporelles ===

    default_duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
        doc="Durée standard en minutes",
        info={
            "description": "Durée par défaut pour planification",
            "unit": "minutes",
            "example": 45
        }
    )

    # === Contraintes réglementaires ===

    requires_prescription: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Nécessite une ordonnance médicale",
        info={
            "description": "True si une prescription médicale est obligatoire",
            "default": False
        }
    )

    is_medical_act: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Est un acte médical ou paramédical",
        info={
            "description": "True si c'est un acte de soin (vs aide à la personne)",
            "default": False
        }
    )

    apa_eligible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Facturable dans le cadre de l'APA",
        info={
            "description": "True si le service peut être financé par l'APA",
            "default": True
        }
    )

    # === Affichage ===

    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        doc="Ordre d'affichage dans les listes",
        info={
            "description": "Permet de trier les services dans l'interface",
            "default": 100
        }
    )

    # === Relations ===

    required_profession: Mapped[Optional["Profession"]] = relationship(
        "Profession",
        back_populates="service_templates",
        lazy="joined",
        doc="Profession requise pour ce service"
    )

    entity_services: Mapped[List["EntityService"]] = relationship(
        "EntityService",
        back_populates="service_template",
        cascade="all, delete-orphan",
        doc="Services activés par les entités basés sur ce template"
    )

    care_plan_services: Mapped[List["CarePlanService"]] = relationship(
        "CarePlanService",
        back_populates="service_template",
        doc="Services de plans d'aide utilisant ce template"
    )

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<ServiceTemplate(id={self.id}, code='{self.code}', name='{self.name}')>"

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    def activate(self) -> None:
        """Active le service."""
        self.status = "active"

    def deactivate(self) -> None:
        """Désactive le service."""
        self.status = "inactive"


    # === Propriétés ===

    @property
    def is_active(self) -> bool:
        """Indique si le service est actif."""
        return self.status == "active"

    @property
    def requires_professional(self) -> bool:
        """Indique si le service nécessite une profession spécifique."""
        return self.required_profession_id is not None


# =============================================================================
# DONNÉES INITIALES (seed)
# =============================================================================
# Ces données représentent le catalogue national des services.
# Le champ `required_profession_code` est résolu en `required_profession_id`
# lors du seeding, en faisant une jointure avec la table `professions`.

INITIAL_SERVICE_TEMPLATES = [
    # === HYGIENE ===
    {
        "code": "TOILETTE_HAUT",
        "name": "Aide à la toilette du haut",
        "category": "HYGIENE",
        "description": "Aide à la toilette du haut du corps (visage, bras, torse)",
        "default_duration_minutes": 20,
        "is_medical_act": False,
        "display_order": 10
    },
    {
        "code": "TOILETTE_BAS",
        "name": "Aide à la toilette du bas",
        "category": "HYGIENE",
        "description": "Aide à la toilette du bas du corps (jambes, pieds, parties intimes)",
        "default_duration_minutes": 25,
        "is_medical_act": False,
        "display_order": 11
    },
    {
        "code": "TOILETTE_COMPLETE",
        "name": "Aide à la toilette complète",
        "category": "HYGIENE",
        "description": "Aide à la toilette intégrale du corps",
        "default_duration_minutes": 45,
        "is_medical_act": False,
        "display_order": 12
    },
    {
        "code": "HABILLAGE",
        "name": "Aide à l'habillage/déshabillage",
        "category": "HYGIENE",
        "description": "Aide pour s'habiller et se déshabiller",
        "default_duration_minutes": 15,
        "is_medical_act": False,
        "display_order": 13
    },

    # === SOINS ===
    {
        "code": "INJECTION_INSULINE",
        "name": "Injection d'insuline",
        "category": "SOINS",
        "description": "Administration d'insuline par voie sous-cutanée",
        "default_duration_minutes": 15,
        "requires_prescription": True,
        "is_medical_act": True,
        "required_profession_code": "60",  # IDE
        "display_order": 20
    },
    {
        "code": "INJECTION_SC",
        "name": "Injection sous-cutanée",
        "category": "SOINS",
        "description": "Injection sous-cutanée (héparine, anticoagulants...)",
        "default_duration_minutes": 15,
        "requires_prescription": True,
        "is_medical_act": True,
        "required_profession_code": "60",  # IDE
        "display_order": 21
    },
    {
        "code": "PANSEMENT_SIMPLE",
        "name": "Pansement simple",
        "category": "SOINS",
        "description": "Réfection de pansement simple (plaie superficielle)",
        "default_duration_minutes": 20,
        "requires_prescription": True,
        "is_medical_act": True,
        "required_profession_code": "60",  # IDE
        "display_order": 22
    },
    {
        "code": "PANSEMENT_COMPLEXE",
        "name": "Pansement complexe",
        "category": "SOINS",
        "description": "Réfection de pansement complexe (escarre, ulcère...)",
        "default_duration_minutes": 45,
        "requires_prescription": True,
        "is_medical_act": True,
        "required_profession_code": "60",  # IDE
        "display_order": 23
    },
    {
        "code": "PRISE_MEDICAMENTS",
        "name": "Aide à la prise de médicaments",
        "category": "SOINS",
        "description": "Aide à la prise des médicaments préparés (pilulier)",
        "default_duration_minutes": 10,
        "is_medical_act": False,
        "display_order": 24
    },
    {
        "code": "SURVEILLANCE_CONSTANTES",
        "name": "Surveillance des constantes",
        "category": "SOINS",
        "description": "Prise de tension, pouls, température, glycémie",
        "default_duration_minutes": 15,
        "is_medical_act": True,
        "required_profession_code": "60",  # IDE
        "display_order": 25
    },

    # === REPAS ===
    {
        "code": "AIDE_REPAS",
        "name": "Aide à la prise des repas",
        "category": "REPAS",
        "description": "Aide pour manger (installation, aide à porter les aliments à la bouche)",
        "default_duration_minutes": 30,
        "is_medical_act": False,
        "display_order": 30
    },
    {
        "code": "PREPARATION_REPAS",
        "name": "Préparation des repas",
        "category": "REPAS",
        "description": "Préparation des repas à domicile",
        "default_duration_minutes": 45,
        "is_medical_act": False,
        "display_order": 31
    },

    # === MOBILITE ===
    {
        "code": "AIDE_LEVER",
        "name": "Aide au lever",
        "category": "MOBILITE",
        "description": "Aide pour se lever du lit et s'installer",
        "default_duration_minutes": 15,
        "is_medical_act": False,
        "display_order": 40
    },
    {
        "code": "AIDE_COUCHER",
        "name": "Aide au coucher",
        "category": "MOBILITE",
        "description": "Aide pour se mettre au lit",
        "default_duration_minutes": 15,
        "is_medical_act": False,
        "display_order": 41
    },
    {
        "code": "AIDE_DEPLACEMENT",
        "name": "Aide au déplacement intérieur",
        "category": "MOBILITE",
        "description": "Aide pour se déplacer dans le logement",
        "default_duration_minutes": 15,
        "is_medical_act": False,
        "display_order": 42
    },
    {
        "code": "KINE_MOBILISATION",
        "name": "Séance de kinésithérapie",
        "category": "MOBILITE",
        "description": "Séance de rééducation par un kinésithérapeute",
        "default_duration_minutes": 30,
        "requires_prescription": True,
        "is_medical_act": True,
        "required_profession_code": "70",  # Kiné
        "display_order": 43
    },

    # === COURSES ===
    {
        "code": "AIDE_COURSES",
        "name": "Aide aux courses",
        "category": "COURSES",
        "description": "Accompagnement ou réalisation des courses alimentaires",
        "default_duration_minutes": 60,
        "is_medical_act": False,
        "display_order": 50
    },

    # === MENAGE ===
    {
        "code": "ENTRETIEN_LOGEMENT",
        "name": "Entretien du logement",
        "category": "MENAGE",
        "description": "Ménage, nettoyage des sols et surfaces",
        "default_duration_minutes": 60,
        "is_medical_act": False,
        "display_order": 60
    },
    {
        "code": "ENTRETIEN_LINGE",
        "name": "Entretien du linge",
        "category": "MENAGE",
        "description": "Lavage, séchage, repassage du linge",
        "default_duration_minutes": 45,
        "is_medical_act": False,
        "display_order": 61
    },

    # === ADMINISTRATIF ===
    {
        "code": "AIDE_ADMINISTRATIVE",
        "name": "Aide aux démarches administratives",
        "category": "ADMINISTRATIF",
        "description": "Aide pour les papiers, courriers, démarches",
        "default_duration_minutes": 30,
        "is_medical_act": False,
        "display_order": 70
    },

    # === SOCIAL ===
    {
        "code": "ACCOMPAGNEMENT_SORTIE",
        "name": "Accompagnement sortie extérieure",
        "category": "SOCIAL",
        "description": "Accompagnement pour sorties (médecin, promenade...)",
        "default_duration_minutes": 60,
        "is_medical_act": False,
        "display_order": 80
    },
    {
        "code": "VISITE_CONVIVIALITE",
        "name": "Visite de convivialité",
        "category": "SOCIAL",
        "description": "Visite pour rompre l'isolement, discussion, compagnie",
        "default_duration_minutes": 30,
        "is_medical_act": False,
        "display_order": 81
    },
]