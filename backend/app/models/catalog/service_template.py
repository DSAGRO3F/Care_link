"""
Modèle ServiceTemplate - Catalogue national des types de prestations.

Ce module définit la table `service_templates` qui représente le référentiel
des services possibles (toilette, injection, courses, etc.) avec leurs
caractéristiques (durée, profession requise, etc.).

Ce catalogue est national et partagé par toutes les entités.
Chaque entité active ensuite les services qu'elle propose via `entity_services`.

🔄 v4.17 — Ajout colonne `domain` (SERAFIN-PH), refonte ENUM `category`
           (10 catégories), seed data complet (44 services).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.enums import ServiceCategory, ServiceDomain
from app.models.mixins import StatusMixin, TimestampMixin


if TYPE_CHECKING:
    from app.models.careplan.care_plan_service import CarePlanService
    from app.models.catalog.entity_service import EntityService
    from app.models.user.profession import Profession


class ServiceTemplate(TimestampMixin, StatusMixin, Base):
    """
    Modèle de service du catalogue national.

    Représente un type de prestation standardisé (toilette, injection,
    aide aux courses, etc.) avec ses caractéristiques.

    Structure à 2 niveaux (alignée SERAFIN-PH) :
    - domain : niveau 1 (Soins & Santé, Autonomie, Participation sociale)
    - category : niveau 2 (10 catégories)

    Attributes:
        id: Identifiant unique
        code: Code unique du service (TOILETTE_COMPLETE, INJECTION_SC...)
        name: Nom lisible du service
        domain: Domaine SERAFIN-PH niveau 1 (🆕 v4.17)
        category: Catégorie niveau 2 (🔄 v4.17 — 10 catégories SERAFIN-PH)
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
        ...     name="Toilette complète",
        ...     domain=ServiceDomain.AUTONOMIE,
        ...     category=ServiceCategory.HYGIENE_ENTRETIEN_PERSONNEL,
        ...     default_duration_minutes=30,
        ...     required_profession_id=aide_soignant.id,
        ... )
    """

    __tablename__ = "service_templates"
    __table_args__ = {"comment": "Catalogue national des types de prestations"}

    # === Clé primaire ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du service",
        info={"description": "Clé primaire auto-incrémentée"},
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
            "example": "TOILETTE_COMPLETE",
        },
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Nom lisible du service",
        info={
            "description": "Nom complet du service pour affichage",
            "example": "Toilette complète",
        },
    )

    # === Classification SERAFIN-PH à 2 niveaux ===

    domain: Mapped[ServiceDomain] = mapped_column(
        SQLEnum(ServiceDomain, name="service_domain_enum", create_constraint=True),
        nullable=False,
        index=True,
        doc="Domaine SERAFIN-PH niveau 1",
        info={
            "description": "Domaine de prestation (Soins & Santé, Autonomie, Participation sociale)",
            "enum": [e.value for e in ServiceDomain],
            "example": "AUTONOMIE",
        },
    )

    category: Mapped[ServiceCategory] = mapped_column(
        SQLEnum(ServiceCategory, name="service_category_enum", create_constraint=True),
        nullable=False,
        index=True,
        doc="Catégorie du service (niveau 2)",
        info={
            "description": "Catégorie de prestation alignée SERAFIN-PH",
            "enum": [e.value for e in ServiceCategory],
            "example": "HYGIENE_ENTRETIEN_PERSONNEL",
        },
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Description détaillée du service",
        info={"description": "Description complète pour documentation et aide contextuelle"},
    )

    # === Exigences professionnelles ===

    required_profession_id: Mapped[int | None] = mapped_column(
        ForeignKey("professions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Profession requise pour réaliser ce service",
        info={
            "description": "FK vers professions. NULL = service polyvalent (toute profession)",
            "example": "ID de la profession Infirmier pour une injection",
        },
    )

    required_qualification: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Qualification spécifique requise",
        info={
            "description": "Qualification additionnelle au-delà de la profession",
            "example": "Diplôme IDE, Formation pansements complexes",
        },
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
            "example": 45,
        },
    )

    # === Contraintes réglementaires ===

    requires_prescription: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Nécessite une ordonnance médicale",
        info={"description": "True si une prescription médicale est obligatoire", "default": False},
    )

    is_medical_act: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Est un acte médical ou paramédical",
        info={
            "description": "True si c'est un acte de soin (vs aide à la personne)",
            "default": False,
        },
    )

    apa_eligible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Facturable dans le cadre de l'APA",
        info={"description": "True si le service peut être financé par l'APA", "default": True},
    )

    # === Affichage ===

    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        doc="Ordre d'affichage dans les listes",
        info={"description": "Permet de trier les services dans l'interface", "default": 100},
    )

    # === Relations ===

    required_profession: Mapped[Profession | None] = relationship(
        "Profession",
        back_populates="service_templates",
        lazy="joined",
        doc="Profession requise pour ce service",
    )

    entity_services: Mapped[list[EntityService]] = relationship(
        "EntityService",
        back_populates="service_template",
        cascade="all, delete-orphan",
        doc="Services activés par les entités basés sur ce template",
    )

    care_plan_services: Mapped[list[CarePlanService]] = relationship(
        "CarePlanService",
        back_populates="service_template",
        doc="Services de plans d'aide utilisant ce template",
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
# DONNÉES INITIALES (seed) — 44 services, 3 domaines, 10 catégories
# =============================================================================
# Alignement SERAFIN-PH (nomenclature CNSA 2018).
#
# Le champ `required_profession_code` est résolu en `required_profession_id`
# lors du seeding via init_service_templates(), par jointure sur professions.code.
#
# Codes profession utilisés : IDE, AS, MED_GEN, KINE, ORTHO, ERGO,
# PSYCHOMOT, PSYCHO, AVS, ASS, PEDICURE. NULL = polyvalent.

INITIAL_SERVICE_TEMPLATES = [
    # =========================================================================
    # DOMAINE : SOINS_SANTE
    # =========================================================================
    # --- Catégorie : SOINS_INFIRMIERS (9 services) ---
    {
        "code": "INJECTION_SC",
        "name": "Injection sous-cutanée",
        "domain": "SOINS_SANTE",
        "category": "SOINS_INFIRMIERS",
        "description": "Administration de médicaments par voie sous-cutanée (insuline, anticoagulants, héparines). Inclut la vérification de la prescription, la préparation et l'élimination du matériel.",
        "default_duration_minutes": 15,
        "requires_prescription": True,
        "is_medical_act": True,
        "apa_eligible": False,
        "required_profession_code": "60",
        "display_order": 10,
    },
    {
        "code": "PANSEMENT_SIMPLE",
        "name": "Pansement simple",
        "domain": "SOINS_SANTE",
        "category": "SOINS_INFIRMIERS",
        "description": "Réfection de pansement simple, nettoyage et protection de plaie superficielle.",
        "default_duration_minutes": 20,
        "requires_prescription": True,
        "is_medical_act": True,
        "apa_eligible": False,
        "required_profession_code": "60",
        "display_order": 20,
    },
    {
        "code": "PANSEMENT_COMPLEXE",
        "name": "Pansement complexe",
        "domain": "SOINS_SANTE",
        "category": "SOINS_INFIRMIERS",
        "description": "Réfection de pansement complexe (escarre, ulcère veineux, plaie chronique). Détersion, irrigation, application de protocole spécifique.",
        "default_duration_minutes": 40,
        "requires_prescription": True,
        "is_medical_act": True,
        "apa_eligible": False,
        "required_profession_code": "60",
        "display_order": 30,
    },
    {
        "code": "SURVEILLANCE_GLYCEMIE",
        "name": "Surveillance glycémique",
        "domain": "SOINS_SANTE",
        "category": "SOINS_INFIRMIERS",
        "description": "Contrôle de la glycémie capillaire et adaptation du traitement selon protocole médical.",
        "default_duration_minutes": 10,
        "requires_prescription": True,
        "is_medical_act": True,
        "apa_eligible": False,
        "required_profession_code": "60",
        "display_order": 40,
    },
    {
        "code": "PERFUSION_SC",
        "name": "Perfusion sous-cutanée",
        "domain": "SOINS_SANTE",
        "category": "SOINS_INFIRMIERS",
        "description": "Mise en place et surveillance de perfusion sous-cutanée (hydratation, antibiothérapie).",
        "default_duration_minutes": 45,
        "requires_prescription": True,
        "is_medical_act": True,
        "apa_eligible": False,
        "required_profession_code": "60",
        "display_order": 50,
    },
    {
        "code": "BAS_CONTENTION",
        "name": "Pose/dépose bas de contention",
        "domain": "SOINS_SANTE",
        "category": "SOINS_INFIRMIERS",
        "description": "Pose et dépose de bas de contention ou bandes de compression veineuse.",
        "default_duration_minutes": 10,
        "requires_prescription": True,
        "is_medical_act": True,
        "apa_eligible": False,
        "required_profession_code": "60",
        "display_order": 60,
    },
    {
        "code": "PRELEVEMENT_SANGUIN",
        "name": "Prélèvement sanguin",
        "domain": "SOINS_SANTE",
        "category": "SOINS_INFIRMIERS",
        "description": "Prélèvement sanguin veineux sur prescription pour analyses biologiques.",
        "default_duration_minutes": 15,
        "requires_prescription": True,
        "is_medical_act": True,
        "apa_eligible": False,
        "required_profession_code": "60",
        "display_order": 70,
    },
    {
        "code": "SURVEILLANCE_CONSTANTES",
        "name": "Surveillance des constantes",
        "domain": "SOINS_SANTE",
        "category": "SOINS_INFIRMIERS",
        "description": "Prise de tension artérielle, température, saturation en oxygène, fréquence cardiaque. Alerte si valeurs hors normes.",
        "default_duration_minutes": 15,
        "requires_prescription": True,
        "is_medical_act": True,
        "apa_eligible": False,
        "required_profession_code": "60",
        "display_order": 80,
    },
    {
        "code": "SOINS_STOMIE",
        "name": "Soins de stomie",
        "domain": "SOINS_SANTE",
        "category": "SOINS_INFIRMIERS",
        "description": "Soins et changement d'appareillage de stomie (colostomie, urostomie). Surveillance de la peau péristomiale.",
        "default_duration_minutes": 30,
        "requires_prescription": True,
        "is_medical_act": True,
        "apa_eligible": False,
        "required_profession_code": "60",
        "display_order": 90,
    },
    # --- Catégorie : SOINS_MEDICAUX (4 services) ---
    {
        "code": "CONSULTATION_MED_COORD",
        "name": "Consultation médecin coordonnateur",
        "domain": "SOINS_SANTE",
        "category": "SOINS_MEDICAUX",
        "description": "Visite du médecin coordonnateur pour évaluation clinique et ajustement du plan de soins.",
        "default_duration_minutes": 30,
        "requires_prescription": False,
        "is_medical_act": True,
        "apa_eligible": False,
        "required_profession_code": "10",
        "display_order": 10,
    },
    {
        "code": "DISTRIBUTION_MEDICAMENTS",
        "name": "Distribution de médicaments",
        "domain": "SOINS_SANTE",
        "category": "SOINS_MEDICAUX",
        "description": "Préparation du pilulier et distribution sécurisée des traitements prescrits.",
        "default_duration_minutes": 15,
        "requires_prescription": True,
        "is_medical_act": False,
        "apa_eligible": False,
        "display_order": 20,
    },
    {
        "code": "TELECONSULTATION",
        "name": "Téléconsultation médicale",
        "domain": "SOINS_SANTE",
        "category": "SOINS_MEDICAUX",
        "description": "Consultation médicale à distance avec accompagnement du patient pour la mise en place technique.",
        "default_duration_minutes": 20,
        "requires_prescription": False,
        "is_medical_act": True,
        "apa_eligible": False,
        "required_profession_code": "10",
        "display_order": 30,
    },
    {
        "code": "EVALUATION_GERIATRIQUE",
        "name": "Évaluation gériatrique à domicile",
        "domain": "SOINS_SANTE",
        "category": "SOINS_MEDICAUX",
        "description": "Évaluation gériatrique standardisée à domicile : bilan fonctionnel, cognitif, nutritionnel et social.",
        "default_duration_minutes": 60,
        "requires_prescription": False,
        "is_medical_act": True,
        "apa_eligible": False,
        "required_profession_code": "10",
        "display_order": 40,
    },
    # --- Catégorie : REEDUCATION (5 services) ---
    {
        "code": "KINESITHERAPIE",
        "name": "Séance de kinésithérapie",
        "domain": "SOINS_SANTE",
        "category": "REEDUCATION",
        "description": "Rééducation motrice, entretien articulaire, travail de l'équilibre et prévention des chutes.",
        "default_duration_minutes": 30,
        "requires_prescription": True,
        "is_medical_act": True,
        "apa_eligible": True,
        "required_profession_code": "70",
        "display_order": 10,
    },
    {
        "code": "ORTHOPHONIE",
        "name": "Séance d'orthophonie",
        "domain": "SOINS_SANTE",
        "category": "REEDUCATION",
        "description": "Rééducation des troubles du langage, de la déglutition et de la communication.",
        "default_duration_minutes": 45,
        "requires_prescription": True,
        "is_medical_act": True,
        "apa_eligible": False,
        "required_profession_code": "94",
        "display_order": 20,
    },
    {
        "code": "ERGOTHERAPIE",
        "name": "Séance d'ergothérapie",
        "domain": "SOINS_SANTE",
        "category": "REEDUCATION",
        "description": "Évaluation et adaptation de l'environnement, rééducation des gestes de la vie quotidienne, préconisation d'aides techniques.",
        "default_duration_minutes": 45,
        "requires_prescription": True,
        "is_medical_act": True,
        "apa_eligible": True,
        "required_profession_code": "91",
        "display_order": 30,
    },
    {
        "code": "PSYCHOMOTRICITE",
        "name": "Séance de psychomotricité",
        "domain": "SOINS_SANTE",
        "category": "REEDUCATION",
        "description": "Rééducation psychomotrice : schéma corporel, tonus, coordination, gestion du stress et de l'anxiété.",
        "default_duration_minutes": 45,
        "requires_prescription": True,
        "is_medical_act": True,
        "apa_eligible": False,
        "required_profession_code": "92",
        "display_order": 40,
    },
    {
        "code": "PEDICURIE_PODOLOGIE",
        "name": "Soins de pédicurie-podologie",
        "domain": "SOINS_SANTE",
        "category": "REEDUCATION",
        "description": "Soins des pieds : coupe d'ongles, traitement des cors et durillons, bilan podologique.",
        "default_duration_minutes": 30,
        "requires_prescription": False,
        "is_medical_act": True,
        "apa_eligible": False,
        "required_profession_code": "80",
        "display_order": 50,
    },
    # =========================================================================
    # DOMAINE : AUTONOMIE
    # =========================================================================
    # --- Catégorie : HYGIENE_ENTRETIEN_PERSONNEL (6 services) ---
    {
        "code": "TOILETTE_COMPLETE",
        "name": "Toilette complète",
        "domain": "AUTONOMIE",
        "category": "HYGIENE_ENTRETIEN_PERSONNEL",
        "description": "Aide à la toilette complète au lit ou au lavabo, incluant soins d'hygiène corporelle, soins de peau, prévention des irritations et habillage. Réalisée dans le respect de la pudeur et de l'autonomie résiduelle.",
        "default_duration_minutes": 30,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "93",
        "display_order": 10,
    },
    {
        "code": "TOILETTE_PARTIELLE",
        "name": "Toilette partielle",
        "domain": "AUTONOMIE",
        "category": "HYGIENE_ENTRETIEN_PERSONNEL",
        "description": "Aide partielle à la toilette pour les actes que la personne ne peut accomplir seule. Stimulation de l'autonomie résiduelle.",
        "default_duration_minutes": 20,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "93",
        "display_order": 20,
    },
    {
        "code": "AIDE_HABILLAGE",
        "name": "Aide à l'habillage",
        "domain": "AUTONOMIE",
        "category": "HYGIENE_ENTRETIEN_PERSONNEL",
        "description": "Accompagnement pour l'habillage et le déshabillage, choix des vêtements adaptés à la saison et à la mobilité.",
        "default_duration_minutes": 15,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "display_order": 30,
    },
    {
        "code": "CHANGE_PROTECTION",
        "name": "Change de protection",
        "domain": "AUTONOMIE",
        "category": "HYGIENE_ENTRETIEN_PERSONNEL",
        "description": "Change de protection urinaire ou fécale, soins de prévention d'escarre, surveillance cutanée.",
        "default_duration_minutes": 15,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "93",
        "display_order": 40,
    },
    {
        "code": "SOINS_BOUCHE",
        "name": "Soins de bouche",
        "domain": "AUTONOMIE",
        "category": "HYGIENE_ENTRETIEN_PERSONNEL",
        "description": "Brossage des dents, soins des prothèses dentaires, hydratation des lèvres et de la cavité buccale.",
        "default_duration_minutes": 10,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "93",
        "display_order": 50,
    },
    {
        "code": "AIDE_ELIMINATION",
        "name": "Aide à l'élimination",
        "domain": "AUTONOMIE",
        "category": "HYGIENE_ENTRETIEN_PERSONNEL",
        "description": "Accompagnement aux toilettes, mise en place du bassin ou de l'urinal, surveillance de l'élimination.",
        "default_duration_minutes": 15,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "93",
        "display_order": 60,
    },
    # --- Catégorie : ALIMENTATION (3 services) ---
    {
        "code": "AIDE_REPAS",
        "name": "Aide à la prise des repas",
        "domain": "AUTONOMIE",
        "category": "ALIMENTATION",
        "description": "Aide à l'alimentation, stimulation, positionnement adapté, surveillance de la déglutition.",
        "default_duration_minutes": 30,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "display_order": 10,
    },
    {
        "code": "PREPARATION_REPAS",
        "name": "Préparation des repas",
        "domain": "AUTONOMIE",
        "category": "ALIMENTATION",
        "description": "Préparation de repas adaptés aux régimes et textures prescrits (mixé, haché, sans sel, diabétique...).",
        "default_duration_minutes": 45,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "AVS",
        "display_order": 20,
    },
    {
        "code": "PORTAGE_REPAS",
        "name": "Portage de repas",
        "domain": "AUTONOMIE",
        "category": "ALIMENTATION",
        "description": "Livraison de repas à domicile, installation et vérification de la prise alimentaire.",
        "default_duration_minutes": 15,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "display_order": 30,
    },
    # --- Catégorie : MOBILITE_TRANSFERTS (4 services) ---
    {
        "code": "AIDE_TRANSFERT",
        "name": "Aide aux transferts",
        "domain": "AUTONOMIE",
        "category": "MOBILITE_TRANSFERTS",
        "description": "Aide au lever, au coucher, passage lit/fauteuil, utilisation du lève-personne si nécessaire.",
        "default_duration_minutes": 15,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "93",
        "display_order": 10,
    },
    {
        "code": "AIDE_DEPLACEMENT",
        "name": "Aide aux déplacements",
        "domain": "AUTONOMIE",
        "category": "MOBILITE_TRANSFERTS",
        "description": "Accompagnement à la marche, surveillance des risques de chute, stimulation à la mobilité.",
        "default_duration_minutes": 20,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "display_order": 20,
    },
    {
        "code": "INSTALLATION_POSITIONNEMENT",
        "name": "Installation et positionnement",
        "domain": "AUTONOMIE",
        "category": "MOBILITE_TRANSFERTS",
        "description": "Installation au fauteuil, positionnement au lit avec coussins de décharge, prévention des attitudes vicieuses.",
        "default_duration_minutes": 15,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "93",
        "display_order": 30,
    },
    {
        "code": "PREVENTION_ESCARRES",
        "name": "Prévention des escarres",
        "domain": "AUTONOMIE",
        "category": "MOBILITE_TRANSFERTS",
        "description": "Changements de position réguliers, effleurages, mise en place de supports anti-escarres, surveillance des points d'appui.",
        "default_duration_minutes": 20,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "93",
        "display_order": 40,
    },
    # =========================================================================
    # DOMAINE : PARTICIPATION_SOCIALE
    # =========================================================================
    # --- Catégorie : ENTRETIEN_CADRE_VIE (3 services) ---
    {
        "code": "MENAGE_ENTRETIEN",
        "name": "Ménage et entretien du logement",
        "domain": "PARTICIPATION_SOCIALE",
        "category": "ENTRETIEN_CADRE_VIE",
        "description": "Entretien courant du logement, nettoyage des pièces de vie, dépoussiérage, aspiration.",
        "default_duration_minutes": 90,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "AVS",
        "display_order": 10,
    },
    {
        "code": "COURSES",
        "name": "Courses et approvisionnement",
        "domain": "PARTICIPATION_SOCIALE",
        "category": "ENTRETIEN_CADRE_VIE",
        "description": "Établissement de la liste, courses alimentaires et de première nécessité, rangement.",
        "default_duration_minutes": 60,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "AVS",
        "display_order": 20,
    },
    {
        "code": "GESTION_LINGE",
        "name": "Gestion du linge",
        "domain": "PARTICIPATION_SOCIALE",
        "category": "ENTRETIEN_CADRE_VIE",
        "description": "Lavage, séchage, repassage et rangement du linge. Entretien des vêtements.",
        "default_duration_minutes": 60,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "AVS",
        "display_order": 30,
    },
    # --- Catégorie : ACCOMPAGNEMENT_ADMINISTRATIF (2 services) ---
    {
        "code": "AIDE_DEMARCHES",
        "name": "Aide aux démarches administratives",
        "domain": "PARTICIPATION_SOCIALE",
        "category": "ACCOMPAGNEMENT_ADMINISTRATIF",
        "description": "Accompagnement pour les courriers, formulaires, dossiers APA, mutuelle, retraite.",
        "default_duration_minutes": 45,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "AVS",
        "display_order": 10,
    },
    {
        "code": "COORDINATION_PARCOURS",
        "name": "Coordination du parcours",
        "domain": "PARTICIPATION_SOCIALE",
        "category": "ACCOMPAGNEMENT_ADMINISTRATIF",
        "description": "Coordination entre les différents intervenants du plan d'aide, transmissions ciblées, réunions de synthèse.",
        "default_duration_minutes": 30,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": False,
        "display_order": 20,
    },
    # --- Catégorie : VIE_SOCIALE_LOISIRS (5 services) ---
    {
        "code": "STIMULATION_COGNITIVE",
        "name": "Stimulation cognitive",
        "domain": "PARTICIPATION_SOCIALE",
        "category": "VIE_SOCIALE_LOISIRS",
        "description": "Activités de stimulation cognitive : jeux de mémoire, lecture, conversation thématique, exercices d'attention.",
        "default_duration_minutes": 30,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "display_order": 10,
    },
    {
        "code": "ACCOMPAGNEMENT_SORTIE",
        "name": "Accompagnement sortie",
        "domain": "PARTICIPATION_SOCIALE",
        "category": "VIE_SOCIALE_LOISIRS",
        "description": "Accompagnement pour promenades, courses, rendez-vous extérieurs, maintien de la vie sociale.",
        "default_duration_minutes": 60,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "AVS",
        "display_order": 20,
    },
    {
        "code": "SOUTIEN_PSYCHOLOGIQUE",
        "name": "Soutien psychologique",
        "domain": "PARTICIPATION_SOCIALE",
        "category": "VIE_SOCIALE_LOISIRS",
        "description": "Entretien de soutien psychologique, aide à l'expression des émotions, accompagnement dans les moments difficiles.",
        "default_duration_minutes": 45,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": False,
        "required_profession_code": "98",
        "display_order": 30,
    },
    {
        "code": "MAINTIEN_LIEN_FAMILIAL",
        "name": "Maintien du lien familial",
        "domain": "PARTICIPATION_SOCIALE",
        "category": "VIE_SOCIALE_LOISIRS",
        "description": "Aide à la communication avec la famille : appels téléphoniques, visioconférences, rédaction de courriers.",
        "default_duration_minutes": 30,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "AVS",
        "display_order": 40,
    },
    {
        "code": "GARDE_NUIT",
        "name": "Garde de nuit / veille nocturne",
        "domain": "PARTICIPATION_SOCIALE",
        "category": "VIE_SOCIALE_LOISIRS",
        "description": "Présence sécurisante au domicile pendant la nuit. Surveillance, aide aux levers nocturnes, change si nécessaire.",
        "default_duration_minutes": 480,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "display_order": 50,
    },
    # --- Catégorie : TRANSPORT (3 services) ---
    {
        "code": "TRANSPORT_RDV_MEDICAL",
        "name": "Accompagnement RDV médical",
        "domain": "PARTICIPATION_SOCIALE",
        "category": "TRANSPORT",
        "description": "Accompagnement du patient pour ses rendez-vous médicaux : transport, attente, retour au domicile.",
        "default_duration_minutes": 120,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "AVS",
        "display_order": 10,
    },
    {
        "code": "TRANSPORT_SOCIAL",
        "name": "Accompagnement transport social",
        "domain": "PARTICIPATION_SOCIALE",
        "category": "TRANSPORT",
        "description": "Accompagnement pour déplacements sociaux : visites familiales, activités associatives, lieux de culte.",
        "default_duration_minutes": 90,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "required_profession_code": "AVS",
        "display_order": 20,
    },
    {
        "code": "TELEASSISTANCE",
        "name": "Téléassistance / télésurveillance",
        "domain": "PARTICIPATION_SOCIALE",
        "category": "TRANSPORT",
        "description": "Dispositif de veille à distance (médaillon, bracelet, capteurs). Service continu, pas d'intervention ponctuelle.",
        "default_duration_minutes": 0,
        "requires_prescription": False,
        "is_medical_act": False,
        "apa_eligible": True,
        "display_order": 30,
    },
]
