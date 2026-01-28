# app/models/tenants/tenant.py
"""
Modèle Tenant - Représente un client/locataire de la plateforme CareLink.
Un tenant peut être un GCSMS (avec ses entités enfants) ou une structure indépendante.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin
from app.models.types import JSONBCompatible

# Imports conditionnels pour éviter les imports circulaires
if TYPE_CHECKING:
    from app.models.reference.country import Country
    from app.models.organization.entity import Entity
    from app.models.user.user import User
    from app.models.user.role import Role
    from app.models.patient.patient import Patient
    from app.models.tenants.subscription import Subscription
    from app.models.user.user_tenant_assignment import UserTenantAssignment


class TenantStatus(str, PyEnum):
    """Statuts possibles d'un tenant."""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


class TenantType(str, PyEnum):
    """Types de tenant (alignés sur EntityType pour cohérence)."""
    GCSMS = "GCSMS"
    SSIAD = "SSIAD"
    SAAD = "SAAD"
    SPASAD = "SPASAD"
    EHPAD = "EHPAD"
    DAC = "DAC"
    CPTS = "CPTS"
    OTHER = "OTHER"


class Tenant(Base, TimestampMixin):
    """
    Représente un client de CareLink (locataire).

    Un tenant correspond à l'entité facturée :
    - Soit un GCSMS (groupement) avec ses structures membres
    - Soit une structure indépendante (SSIAD, SAAD, etc.)

    Chaque tenant a :
    - Sa propre clé de chiffrement AES-256
    - Ses propres limites (patients, utilisateurs, stockage)
    - Son propre abonnement
    """

    __tablename__ = "tenants"

    # ========================
    # Clé primaire
    # ========================
    id: Mapped[int] = mapped_column(primary_key=True)

    # ========================
    # Identification
    # ========================
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="Code unique du tenant (ex: GCSMS-BV-IDF)"
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nom commercial"
    )
    legal_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="Raison sociale officielle"
    )
    siret: Mapped[Optional[str]] = mapped_column(
        String(14),
        comment="Numéro SIRET (France)"
    )

    # ========================
    # Type et statut
    # ========================
    tenant_type: Mapped[TenantType] = mapped_column(
        Enum(TenantType, name="tenant_type_enum", create_constraint=True),
        nullable=False,
        comment="Type de structure principale"
    )
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus, name="tenant_status_enum", create_constraint=True),
        default=TenantStatus.ACTIVE,
        nullable=False,
        comment="Statut du tenant"
    )

    # ========================
    # Contact
    # ========================
    contact_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Email du contact principal"
    )
    contact_phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Téléphone du contact principal"
    )
    billing_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="Email pour la facturation (si différent)"
    )

    # ========================
    # Adresse
    # ========================
    address_line1: Mapped[Optional[str]] = mapped_column(String(255))
    address_line2: Mapped[Optional[str]] = mapped_column(String(255))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    country_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("countries.id"),
        comment="Pays du tenant"
    )

    # ========================
    # Configuration technique
    # ========================
    encryption_key_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Référence vers la clé AES dans le vault"
    )
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="Europe/Paris",
        nullable=False
    )
    locale: Mapped[str] = mapped_column(
        String(10),
        default="fr_FR",
        nullable=False
    )

    # ========================
    # Limites et quotas
    # ========================
    max_patients: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Limite contractuelle de patients (NULL = illimité)"
    )
    max_users: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Limite contractuelle d'utilisateurs (NULL = illimité)"
    )
    max_storage_gb: Mapped[int] = mapped_column(
        Integer,
        default=50,
        nullable=False,
        comment="Quota de stockage en Go"
    )

    # ========================
    # Métadonnées
    # ========================
    settings: Mapped[dict] = mapped_column(
        JSONBCompatible,
        default=dict,
        nullable=False,
        comment="Paramètres personnalisés du tenant (JSON)"
    )
    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Date de mise en service"
    )
    terminated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Date de résiliation"
    )

    # ========================
    # Relations
    # ========================
    country: Mapped[Optional["Country"]] = relationship(
        "Country",
        lazy="joined"
    )

    entities: Mapped[List["Entity"]] = relationship(
        "Entity",
        back_populates="tenant",
        lazy="selectin"
    )

    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="tenant",
        lazy="selectin"
    )

    patients: Mapped[List["Patient"]] = relationship(
        "Patient",
        back_populates="tenant",
        lazy="selectin"
    )

    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription",
        back_populates="tenant",
        lazy="selectin"
    )

    # Rattachements d'utilisateurs externes (cross-tenant)
    user_assignments: Mapped[List["UserTenantAssignment"]] = relationship(
        "UserTenantAssignment",
        back_populates="tenant",
        cascade="all, delete-orphan",
        doc="Utilisateurs d'autres tenants ayant accès à ce tenant"
    )

    # Rôles personnalisés du tenant (v4.3)
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        back_populates="tenant",
        cascade="all, delete-orphan",
        doc="Rôles personnalisés créés par ce tenant"
    )

    # ========================
    # Méthodes
    # ========================
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, code='{self.code}', name='{self.name}')>"

    @property
    def is_active(self) -> bool:
        """Vérifie si le tenant est actif."""
        return self.status == TenantStatus.ACTIVE

    @property
    def is_suspended(self) -> bool:
        """Vérifie si le tenant est suspendu."""
        return self.status == TenantStatus.SUSPENDED