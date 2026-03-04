# app/models/tenants/tenant.py
"""
Modèle Tenant - Représente un client/locataire de la plateforme CareLink.

Un tenant peut être :
- Un groupement fédérateur (GCSMS, GTSMS) avec des tenants membres
- Une structure indépendante (SSIAD, SAAD, etc.)
- Une structure membre d'un groupement (modèle fédéré)

Hiérarchie de fédération :
    GCSMS/GTSMS (parent_tenant_id = NULL)
     ├── SSIAD Arcachon  (parent_tenant_id → GCSMS, integration_type = FEDERATED)
     ├── SAAD La Teste   (parent_tenant_id → GCSMS, integration_type = FEDERATED)
     └── Cabinet kiné    (parent_tenant_id → GCSMS, integration_type = CONVENTION)
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    String,
    DateTime,
    Date,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.enums import IntegrationType, TenantType, TenantStatus
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


class Tenant(Base, TimestampMixin):
    """
    Représente un client de CareLink (locataire).

    Un tenant correspond à l'entité facturée :
    - Soit un groupement fédérateur (GCSMS, GTSMS) avec ses structures membres
    - Soit une structure indépendante (SSIAD, SAAD, etc.)
    - Soit une structure autonome rattachée à un groupement (modèle fédéré)

    Chaque tenant a :
    - Sa propre clé de chiffrement AES-256
    - Ses propres limites (patients, utilisateurs, stockage)
    - Son propre abonnement
    """

    __tablename__ = "tenants"
    __table_args__ = (
        # Un tenant ne peut pas être son propre parent
        CheckConstraint(
            "parent_tenant_id != id",
            name="ck_tenant_no_self_parent"
        ),
        # Un GCSMS ou GTSMS ne peut pas avoir de parent (c'est lui le fédérateur)
        CheckConstraint(
            """
            NOT (
                tenant_type IN ('GCSMS', 'GTSMS')
                AND parent_tenant_id IS NOT NULL
            )
            """,
            name="ck_federation_parent_cannot_have_parent"
        ),
        # integration_type doit être renseigné si et seulement si parent_tenant_id est renseigné
        CheckConstraint(
            """
            (parent_tenant_id IS NULL AND integration_type IS NULL)
            OR (parent_tenant_id IS NOT NULL AND integration_type IS NOT NULL)
            """,
            name="ck_integration_type_requires_parent"
        ),
    )

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
    # Fédération (rattachement à un groupement)
    # ========================
    parent_tenant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID du groupement fédérateur (GCSMS/GTSMS) de rattachement"
    )
    integration_type: Mapped[Optional[IntegrationType]] = mapped_column(
        Enum(IntegrationType, name="integration_type_enum", create_constraint=False),
        nullable=True,
        comment="Type de rattachement au groupement (MANAGED, FEDERATED, CONVENTION)"
    )
    federation_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date de rattachement au groupement"
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

    # --- Fédération : auto-référence parent/membres ---
    parent_tenant: Mapped[Optional["Tenant"]] = relationship(
        "Tenant",
        remote_side="Tenant.id",
        back_populates="member_tenants",
        foreign_keys=[parent_tenant_id],
        doc="Groupement fédérateur (GCSMS/GTSMS) dont ce tenant est membre"
    )

    member_tenants: Mapped[List["Tenant"]] = relationship(
        "Tenant",
        back_populates="parent_tenant",
        foreign_keys=[parent_tenant_id],
        doc="Tenants membres de ce groupement (si GCSMS/GTSMS)"
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

    @property
    def is_federation_parent(self) -> bool:
        """Vérifie si ce tenant est un groupement fédérateur (GCSMS/GTSMS)."""
        return self.tenant_type in (TenantType.GCSMS, TenantType.GTSMS)

    @property
    def is_federation_member(self) -> bool:
        """Vérifie si ce tenant est rattaché à un groupement."""
        return self.parent_tenant_id is not None

    @property
    def is_independent(self) -> bool:
        """Vérifie si ce tenant est indépendant (ni fédérateur, ni membre)."""
        return not self.is_federation_parent and not self.is_federation_member

    @property
    def members_count(self) -> int:
        """Nombre de tenants membres (si groupement fédérateur)."""
        return len(self.member_tenants)