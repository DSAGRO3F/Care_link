"""
Modèle SuperAdmin - Administrateurs de la plateforme CareLink.

Ce module définit la table `super_admins` qui représente les administrateurs
de la plateforme CareLink (équipe technique, commerciale, support).

IMPORTANT :
- Les super-admins sont SÉPARÉS des utilisateurs clients (table `users`)
- Ils n'ont PAS de tenant_id (accès cross-tenant)
- Authentification par login/password + MFA (pas PSC)
- Utilisés pour : gestion des tenants, support, audit, onboarding
"""

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List

from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.platform.platform_audit_log import PlatformAuditLog


class SuperAdminRole(str, Enum):
    """
    Rôles des super-administrateurs CareLink.

    Hiérarchie des permissions :
    - PLATFORM_OWNER : Accès total (fondateurs, CTO)
    - PLATFORM_ADMIN : Gestion des tenants et super-admins
    - PLATFORM_SUPPORT : Support technique, accès lecture
    - PLATFORM_SALES : Démos, onboarding nouveaux clients
    """
    PLATFORM_OWNER = "PLATFORM_OWNER"  # Accès total
    PLATFORM_ADMIN = "PLATFORM_ADMIN"  # Gestion tenants + support
    PLATFORM_SUPPORT = "PLATFORM_SUPPORT"  # Support, lecture seule
    PLATFORM_SALES = "PLATFORM_SALES"  # Démos, onboarding


class SuperAdmin(TimestampMixin, Base):
    """
    Représente un administrateur de la plateforme CareLink.

    Les super-admins gèrent la plateforme multi-tenant :
    - Création/suspension de tenants
    - Support technique aux clients
    - Audit et monitoring
    - Onboarding de nouveaux clients

    Attributes:
        id: Identifiant unique
        email: Email de connexion (unique)
        first_name: Prénom
        last_name: Nom de famille
        password_hash: Hash bcrypt du mot de passe
        role: Rôle (PLATFORM_OWNER, PLATFORM_ADMIN, etc.)
        mfa_secret: Secret TOTP pour MFA (chiffré)
        mfa_enabled: MFA activé ?
        is_active: Compte actif
        last_login: Dernière connexion
        failed_login_attempts: Tentatives échouées (sécurité)
        locked_until: Verrouillage temporaire après échecs

    Example:
        admin = SuperAdmin(
            email="admin@carelink.fr",
            first_name="Admin",
            last_name="CareLink",
            role=SuperAdminRole.PLATFORM_ADMIN,
            mfa_enabled=True
        )
    """

    __tablename__ = "super_admins"
    __table_args__ = {
        "comment": "Administrateurs de la plateforme CareLink (équipe interne)"
    }

    # === Colonnes d'identification ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du super-admin"
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Adresse email unique de connexion"
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Prénom"
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Nom de famille"
    )

    # === Authentification ===

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Hash bcrypt du mot de passe"
    )

    # === Rôle ===

    role: Mapped[SuperAdminRole] = mapped_column(
        SQLEnum(SuperAdminRole, name="super_admin_role_enum", create_constraint=True),
        nullable=False,
        default=SuperAdminRole.PLATFORM_SUPPORT,
        doc="Rôle du super-admin (niveau de permissions)"
    )

    # === MFA (Multi-Factor Authentication) ===

    mfa_secret: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Secret TOTP pour authentification MFA (chiffré AES-256-GCM)"
    )

    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="MFA activé pour ce compte"
    )

    mfa_backup_codes: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        doc="Codes de secours MFA (chiffrés, JSON array)"
    )

    # === Statut ===

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Compte actif"
    )

    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Dernière connexion réussie"
    )

    # === Sécurité anti-brute-force ===

    failed_login_attempts: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        doc="Nombre de tentatives de connexion échouées"
    )

    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date jusqu'à laquelle le compte est verrouillé"
    )

    last_password_change: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date du dernier changement de mot de passe"
    )

    # === Relations ===

    audit_logs: Mapped[List["PlatformAuditLog"]] = relationship(
        "PlatformAuditLog",
        back_populates="super_admin",
        cascade="all, delete-orphan",
        doc="Logs d'audit de ce super-admin"
    )

    # === Propriétés ===

    @property
    def full_name(self) -> str:
        """Nom complet (Prénom Nom)."""
        return f"{self.first_name} {self.last_name}"

    @property
    def is_locked(self) -> bool:
        """Vérifie si le compte est actuellement verrouillé."""
        if not self.locked_until:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    @property
    def is_owner(self) -> bool:
        """Vérifie si c'est un PLATFORM_OWNER."""
        return self.role == SuperAdminRole.PLATFORM_OWNER

    @property
    def can_manage_tenants(self) -> bool:
        """Vérifie si le super-admin peut gérer les tenants."""
        return self.role in (
            SuperAdminRole.PLATFORM_OWNER,
            SuperAdminRole.PLATFORM_ADMIN
        )

    @property
    def can_manage_super_admins(self) -> bool:
        """Vérifie si le super-admin peut gérer d'autres super-admins."""
        return self.role == SuperAdminRole.PLATFORM_OWNER

    @property
    def can_view_audit_logs(self) -> bool:
        """Vérifie si le super-admin peut voir les logs d'audit."""
        return self.role in (
            SuperAdminRole.PLATFORM_OWNER,
            SuperAdminRole.PLATFORM_ADMIN
        )

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<SuperAdmin(id={self.id}, email='{self.email}', role='{self.role.value}')>"

    def __str__(self) -> str:
        return f"{self.full_name} ({self.role.value})"

    def record_login_success(self) -> None:
        """Enregistre une connexion réussie."""
        self.last_login = datetime.now(timezone.utc)
        self.failed_login_attempts = 0
        self.locked_until = None

    def record_login_failure(self, max_attempts: int = 5, lock_duration_minutes: int = 30) -> None:
        """
        Enregistre une tentative de connexion échouée.

        Args:
            max_attempts: Nombre max d'échecs avant verrouillage
            lock_duration_minutes: Durée du verrouillage en minutes
        """
        self.failed_login_attempts += 1

        if self.failed_login_attempts >= max_attempts:
            from datetime import timedelta
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lock_duration_minutes)

    def has_role(self, role: SuperAdminRole) -> bool:
        """Vérifie si le super-admin a un rôle spécifique ou supérieur."""
        role_hierarchy = {
            SuperAdminRole.PLATFORM_OWNER: 4,
            SuperAdminRole.PLATFORM_ADMIN: 3,
            SuperAdminRole.PLATFORM_SUPPORT: 2,
            SuperAdminRole.PLATFORM_SALES: 1,
        }
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(role, 0)

    def enable_mfa(self, secret: str) -> None:
        """Active le MFA pour ce compte."""
        self.mfa_secret = secret
        self.mfa_enabled = True

    def disable_mfa(self) -> None:
        """Désactive le MFA pour ce compte."""
        self.mfa_secret = None
        self.mfa_enabled = False
        self.mfa_backup_codes = None