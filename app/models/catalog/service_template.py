"""
Service Templates - Catalogue national des types de prestations.

Ce module définit le référentiel des services possibles (toilette, injection,
courses, etc.) avec leurs caractéristiques (durée, profession requise, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, StatusMixin
from app.models.enums import ServiceCategory

if TYPE_CHECKING:
    from app.models.user.profession import Profession
    from app.models.catalog.entity_service import EntityService
    from app.models.careplan.care_plan_service import CarePlanService


class ServiceTemplate(Base, TimestampMixin, StatusMixin):
    """
    Modèle de service du catalogue national.
    
    Représente un type de prestation standardisé (toilette, injection,
    aide aux courses, etc.) avec ses caractéristiques.
    
    Attributes:
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
    __table_args__ = (
        {"comment": "Catalogue national des types de prestations"}
    )
    
    # === Clé primaire ===
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # === Identification ===
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Code unique du service (TOILETTE_COMPLETE, INJECTION_SC...)"
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Nom lisible du service"
    )
    
    category: Mapped[ServiceCategory] = mapped_column(
        SQLEnum(ServiceCategory, name="service_category_enum", create_constraint=True),
        nullable=False,
        index=True,
        comment="Catégorie du service"
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description détaillée du service"
    )
    
    # === Exigences ===
    required_profession_id: Mapped[int | None] = mapped_column(
        ForeignKey("professions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Profession requise (NULL = polyvalent)"
    )
    
    required_qualification: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Qualification spécifique requise (ex: 'Diplôme IDE')"
    )
    
    # === Caractéristiques ===
    default_duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
        comment="Durée standard en minutes"
    )
    
    requires_prescription: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Nécessite une ordonnance médicale"
    )
    
    is_medical_act: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Est un acte médical ou paramédical"
    )
    
    apa_eligible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Facturable dans le cadre de l'APA"
    )
    
    # === Affichage ===
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        comment="Ordre d'affichage dans les listes"
    )
    
    # === Relations ===
    required_profession: Mapped[Optional["Profession"]] = relationship(
        "Profession",
        back_populates="service_templates",
        lazy="joined"
    )
    
    entity_services: Mapped[List["EntityService"]] = relationship(
        "EntityService",
        back_populates="service_template",
        cascade="all, delete-orphan"
    )
    
    care_plan_services: Mapped[List["CarePlanService"]] = relationship(
        "CarePlanService",
        back_populates="service_template"
    )
    
    # === Méthodes ===
    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
    
    def __repr__(self) -> str:
        return f"<ServiceTemplate(id={self.id}, code='{self.code}', name='{self.name}')>"
    
    @property
    def requires_specific_profession(self) -> bool:
        """Indique si le service nécessite une profession spécifique."""
        return self.required_profession_id is not None


# =============================================================================
# DONNÉES INITIALES
# =============================================================================

INITIAL_SERVICE_TEMPLATES = [
    # === HYGIENE ===
    {
        "code": "TOILETTE_HAUT",
        "name": "Aide à la toilette du haut",
        "category": "HYGIENE",
        "default_duration_minutes": 20,
        "is_medical_act": False,
        "display_order": 10
    },
    {
        "code": "TOILETTE_BAS",
        "name": "Aide à la toilette du bas",
        "category": "HYGIENE",
        "default_duration_minutes": 25,
        "is_medical_act": False,
        "display_order": 11
    },
    {
        "code": "TOILETTE_COMPLETE",
        "name": "Aide à la toilette complète",
        "category": "HYGIENE",
        "default_duration_minutes": 45,
        "is_medical_act": False,
        "display_order": 12
    },
    {
        "code": "HABILLAGE",
        "name": "Aide à l'habillage/déshabillage",
        "category": "HYGIENE",
        "default_duration_minutes": 15,
        "is_medical_act": False,
        "display_order": 13
    },
    
    # === SOINS ===
    {
        "code": "INJECTION_INSULINE",
        "name": "Injection d'insuline",
        "category": "SOINS",
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
        "default_duration_minutes": 10,
        "is_medical_act": False,
        "display_order": 24
    },
    {
        "code": "SURVEILLANCE_CONSTANTES",
        "name": "Surveillance des constantes",
        "category": "SOINS",
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
        "default_duration_minutes": 30,
        "is_medical_act": False,
        "display_order": 30
    },
    {
        "code": "PREPARATION_REPAS",
        "name": "Préparation des repas",
        "category": "REPAS",
        "default_duration_minutes": 45,
        "is_medical_act": False,
        "display_order": 31
    },
    
    # === MOBILITE ===
    {
        "code": "AIDE_LEVER",
        "name": "Aide au lever",
        "category": "MOBILITE",
        "default_duration_minutes": 15,
        "is_medical_act": False,
        "display_order": 40
    },
    {
        "code": "AIDE_COUCHER",
        "name": "Aide au coucher",
        "category": "MOBILITE",
        "default_duration_minutes": 15,
        "is_medical_act": False,
        "display_order": 41
    },
    {
        "code": "AIDE_DEPLACEMENT",
        "name": "Aide au déplacement intérieur",
        "category": "MOBILITE",
        "default_duration_minutes": 15,
        "is_medical_act": False,
        "display_order": 42
    },
    {
        "code": "KINE_MOBILISATION",
        "name": "Séance de kinésithérapie",
        "category": "MOBILITE",
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
        "default_duration_minutes": 60,
        "is_medical_act": False,
        "display_order": 50
    },
    
    # === MENAGE ===
    {
        "code": "ENTRETIEN_LOGEMENT",
        "name": "Entretien du logement",
        "category": "MENAGE",
        "default_duration_minutes": 60,
        "is_medical_act": False,
        "display_order": 60
    },
    {
        "code": "ENTRETIEN_LINGE",
        "name": "Entretien du linge",
        "category": "MENAGE",
        "default_duration_minutes": 45,
        "is_medical_act": False,
        "display_order": 61
    },
    
    # === ADMINISTRATIF ===
    {
        "code": "AIDE_ADMINISTRATIVE",
        "name": "Aide aux démarches administratives",
        "category": "ADMINISTRATIF",
        "default_duration_minutes": 30,
        "is_medical_act": False,
        "display_order": 70
    },
    
    # === SOCIAL ===
    {
        "code": "ACCOMPAGNEMENT_SORTIE",
        "name": "Accompagnement sortie extérieure",
        "category": "SOCIAL",
        "default_duration_minutes": 60,
        "is_medical_act": False,
        "display_order": 80
    },
    {
        "code": "VISITE_CONVIVIALITE",
        "name": "Visite de convivialité",
        "category": "SOCIAL",
        "default_duration_minutes": 30,
        "is_medical_act": False,
        "display_order": 81
    },
]
