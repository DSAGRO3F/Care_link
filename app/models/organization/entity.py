"""
Modèle Entity - Entités de soins.

Ce module définit la table `entities` qui représente les structures
de soins (SSIAD, EHPAD, SAAD, etc.) dans lesquelles les professionnels
exercent et les patients sont suivis.

Une entité peut être :
- Rattachée à une organisation (GCSMS) de manière intégrée ou fédérée
- Avoir des sous-entités (agences géographiques)
- Avoir une capacité autorisée (places SSIAD, lits EHPAD)
"""

from datetime import date
from typing import TYPE_CHECKING, List, Optional
from decimal import Decimal

from sqlalchemy import String, ForeignKey, Text, Integer, Date, Numeric
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin, StatusMixin
from app.models.enums import EntityType, IntegrationType

if TYPE_CHECKING:
    from app.models.reference.country import Country
    from app.models.tenants.tenant import Tenant
    from app.models.user.user import User
    from app.models.patient.patient import Patient
    from app.models.user.user_associations import UserEntity
    from app.models.catalog.entity_service import EntityService
    from app.models.careplan.care_plan import CarePlan
    from app.models.user.user_availability import UserAvailability


class Entity(TimestampMixin, StatusMixin, Base):
    """
    Représente une entité/structure de soins.
    
    Les entités sont des structures juridiques ou opérationnelles
    qui emploient des professionnels de santé et prennent en charge
    des patients. Exemples : SSIAD, EHPAD, SAAD, DAC, CPTS.
    
    Une entité peut :
    - Appartenir à une organisation (GCSMS) : via organization_id (à venir)
    - Avoir des sous-entités (agences) : via parent_entity_id
    - Avoir une capacité autorisée : authorized_capacity
    
    Attributes:
        id: Identifiant unique
        name: Nom de la structure
        short_name: Nom court ou acronyme
        entity_type: Type d'entité (SSIAD, EHPAD, etc.)
        integration_type: Type de rattachement au groupement
        parent_entity_id: Entité parente (pour les agences)
        siret: Numéro SIRET (14 chiffres)
        siren: Numéro SIREN (9 chiffres)
        finess_ej: Numéro FINESS Entité Juridique
        finess_et: Numéro FINESS Établissement
        authorized_capacity: Nombre de places autorisées
        country: Pays de rattachement
        users: Professionnels rattachés à cette entité
        patients: Patients suivis par cette entité
    
    Example:
        ssiad = Entity(
            name="SSIAD Paris 12",
            entity_type=EntityType.SSIAD,
            integration_type=IntegrationType.MANAGED,
            siret="12345678901234",
            finess_et="750012345",
            authorized_capacity=30,
            country_id=1
        )
    """
    
    __tablename__ = "entities"
    __table_args__ = {
        "comment": "Table des entités de soins (SSIAD, EHPAD, SAAD...)"
    }
    
    # =========================================================================
    # COLONNES D'IDENTIFICATION
    # =========================================================================

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de l'entité",
        info={
            "description": "Clé primaire auto-incrémentée"
        }
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Nom de la structure de soins",
        info={
            "description": "Nom complet de l'entité",
            "example": "SSIAD Bien Vieillir Paris 12"
        }
    )
    
    short_name: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Nom court ou acronyme",
        info={
            "description": "Nom abrégé pour affichage",
            "example": "SSIAD P12"
        }
    )

    # =========================================================================
    # TYPE ET RATTACHEMENT
    # =========================================================================
    
    entity_type: Mapped[EntityType] = mapped_column(
        SQLEnum(EntityType, name="entity_type_enum", create_constraint=True),
        nullable=False,
        doc="Type de structure",
        info={
            "description": "Type d'entité selon classification française",
            "example": "SSIAD"
        }
    )
    
    integration_type: Mapped[Optional[IntegrationType]] = mapped_column(
        SQLEnum(IntegrationType, name="integration_type_enum", create_constraint=True),
        nullable=True,
        doc="Type de rattachement à l'organisation",
        info={
            "description": "MANAGED (intégré), FEDERATED (adhérent), CONVENTION (partenaire)",
            "example": "MANAGED"
        }
    )
    
    # =========================================================================
    # HIÉRARCHIE (auto-référence pour les agences)
    # =========================================================================
    
    parent_entity_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID de l'entité parente (pour les agences)",
        info={
            "description": "Référence vers l'entité mère si c'est une agence"
        }
    )
    
    # =========================================================================
    # IDENTIFIANTS LÉGAUX
    # =========================================================================
    
    siret: Mapped[Optional[str]] = mapped_column(
        String(14),
        unique=True,
        nullable=True,
        doc="Numéro SIRET de l'établissement",
        info={
            "description": "Numéro SIRET à 14 chiffres",
            "pattern": "^[0-9]{14}$",
            "example": "12345678901234"
        }
    )
    
    siren: Mapped[Optional[str]] = mapped_column(
        String(9),
        nullable=True,
        doc="Numéro SIREN de l'entité juridique",
        info={
            "description": "Numéro SIREN à 9 chiffres (extrait du SIRET)",
            "pattern": "^[0-9]{9}$",
            "example": "123456789"
        }
    )
    
    finess_ej: Mapped[Optional[str]] = mapped_column(
        String(9),
        nullable=True,
        doc="Numéro FINESS Entité Juridique",
        info={
            "description": "FINESS de l'entité juridique gestionnaire",
            "pattern": "^[0-9A-Z]{9}$",
            "example": "750000001"
        }
    )
    
    finess_et: Mapped[Optional[str]] = mapped_column(
        String(9),
        unique=True,
        nullable=True,
        doc="Numéro FINESS Établissement",
        info={
            "description": "FINESS de l'établissement (anciennement 'finess')",
            "pattern": "^[0-9A-Z]{9}$",
            "example": "750012345"
        }
    )
    
    # =========================================================================
    # AUTORISATION ET CAPACITÉ
    # =========================================================================
    
    authorized_capacity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Nombre de places autorisées",
        info={
            "description": "Capacité autorisée (places SSIAD, lits EHPAD...)",
            "example": 30
        }
    )
    
    authorization_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Date de l'autorisation",
        info={
            "description": "Date de délivrance de l'autorisation ARS/CD"
        }
    )
    
    authorization_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Référence de l'autorisation",
        info={
            "description": "Numéro ou référence de l'arrêté d'autorisation"
        }
    )
    
    # =========================================================================
    # COORDONNÉES
    # =========================================================================
    
    address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Adresse postale complète",
        info={
            "description": "Adresse du siège ou de l'établissement"
        }
    )
    
    postal_code: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        doc="Code postal",
        info={
            "description": "Code postal",
            "example": "75012"
        }
    )
    
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Ville",
        info={
            "description": "Nom de la commune",
            "example": "Paris"
        }
    )
    
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        doc="Numéro de téléphone principal",
        info={
            "description": "Téléphone de contact",
            "example": "0148123456"
        }
    )
    
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Adresse email de contact",
        info={
            "description": "Email principal de l'entité",
            "format": "email"
        }
    )
    
    website: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Site web",
        info={
            "description": "URL du site web de l'entité"
        }
    )

    # === Géolocalisation du siège ===
    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="Latitude du siège"
    )

    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="Longitude du siège"
    )

    # === Zone de couverture par défaut ===
    default_intervention_radius_km: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=30,
        comment="Rayon d'intervention par défaut en km"
    )
    
    # =========================================================================
    # CLÉS ÉTRANGÈRES
    # =========================================================================

    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"),
        nullable=False,
        doc="ID du pays de rattachement",
        info={
            "description": "Référence vers le pays"
        }
    )

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="ID du tenant propriétaire",
        info={
            "description": "Référence vers le tenant (client) propriétaire de cette entité"
        }
    )
    

    # =========================================================================
    # RELATIONS
    # =========================================================================

    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="entities",
        doc="Tenant propriétaire de cette entité"
    )

    country: Mapped["Country"] = relationship(
        "Country",
        back_populates="entities",
        doc="Pays de rattachement de l'entité"
    )
    
    # Auto-référence pour la hiérarchie parent/enfants
    parent_entity: Mapped[Optional["Entity"]] = relationship(
        "Entity",
        remote_side="Entity.id",
        back_populates="child_entities",
        foreign_keys=[parent_entity_id],
        doc="Entité parente (si c'est une agence)"
    )
    
    child_entities: Mapped[List["Entity"]] = relationship(
        "Entity",
        back_populates="parent_entity",
        foreign_keys=[parent_entity_id],
        doc="Sous-entités (agences) de cette entité"
    )
    
    user_associations: Mapped[List["UserEntity"]] = relationship(
        "UserEntity",
        back_populates="entity",
        cascade="all, delete-orphan",
        doc="Associations avec les utilisateurs (via table de jonction)"
    )
    
    patients: Mapped[List["Patient"]] = relationship(
        "Patient",
        back_populates="entity",
        doc="Patients suivis par cette entité"
    )

    entity_services: Mapped[List["EntityService"]] = relationship(
        "EntityService",
        back_populates="entity",
        cascade="all, delete-orphan",
        doc="Services proposés par cette entité"
    )

    care_plans: Mapped[List["CarePlan"]] = relationship(
        "CarePlan",
        back_populates="entity",
        doc="Plans d'aide coordonnés par cette entité"
    )

    user_availabilities: Mapped[List["UserAvailability"]] = relationship(
        "UserAvailability",
        back_populates="entity",
        cascade="all, delete-orphan",
        doc="Disponibilités des professionnels pour cette entité"
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="entities")
    
    # NOTE: Relations à ajouter plus tard
    # organization: Mapped[Optional["Organization"]] = relationship(...)
    # territories: Mapped[List["EntityTerritory"]] = relationship(...)
    # services: Mapped[List["EntityService"]] = relationship(...)
    
    # =========================================================================
    # PROPRIÉTÉS
    # =========================================================================
    
    @property
    def users(self) -> List["User"]:
        """Liste des utilisateurs actifs rattachés à cette entité."""
        return [ua.user for ua in self.user_associations if ua.end_date is None]
    
    @property
    def active_users_count(self) -> int:
        """Nombre d'utilisateurs actifs dans cette entité."""
        return len([ua for ua in self.user_associations if ua.end_date is None])
    
    @property
    def patients_count(self) -> int:
        """Nombre de patients actifs suivis par cette entité."""
        return len([p for p in self.patients if p.status == "active"])
    
    @property
    def is_parent(self) -> bool:
        """Indique si cette entité a des sous-entités (agences)."""
        return len(self.child_entities) > 0
    
    @property
    def is_child(self) -> bool:
        """Indique si cette entité est une sous-entité (agence)."""
        return self.parent_entity_id is not None
    
    @property
    def capacity_usage(self) -> Optional[float]:
        """
        Taux d'occupation de la capacité autorisée.
        
        Returns:
            Pourcentage d'occupation (0-100) ou None si pas de capacité définie
        """
        if not self.authorized_capacity:
            return None
        return (self.patients_count / self.authorized_capacity) * 100
    
    # =========================================================================
    # MÉTHODES
    # =========================================================================
    
    def __repr__(self) -> str:
        return f"<Entity(id={self.id}, name='{self.name}', type='{self.entity_type.value if self.entity_type else 'N/A'}')>"
    
    def __str__(self) -> str:
        return f"{self.name} ({self.entity_type.value if self.entity_type else 'N/A'})"
