"""
Modèle PlatformAuditLog - Logs d'audit des actions super-admin.

Ce module définit la table `platform_audit_logs` qui trace toutes les actions
effectuées par les super-admins sur la plateforme CareLink.

IMPORTANT :
- Traçabilité obligatoire pour la conformité (RGPD, HDS)
- Logs immuables (pas de UPDATE/DELETE)
- Rétention configurable (par défaut 2 ans)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.types import JSONBCompatible

if TYPE_CHECKING:
    from app.models.platform.super_admin import SuperAdmin
    from app.models.tenants.tenant import Tenant


class AuditAction(str, Enum):
    """
    Types d'actions auditées.

    Catégories :
    - AUTH : Authentification
    - TENANT : Gestion des tenants
    - USER : Gestion des utilisateurs
    - DATA : Accès aux données
    - CONFIG : Configuration plateforme
    """
    # Authentification
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    MFA_ENABLED = "MFA_ENABLED"
    MFA_DISABLED = "MFA_DISABLED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"

    # Gestion des tenants
    TENANT_CREATED = "TENANT_CREATED"
    TENANT_UPDATED = "TENANT_UPDATED"
    TENANT_SUSPENDED = "TENANT_SUSPENDED"
    TENANT_ACTIVATED = "TENANT_ACTIVATED"
    TENANT_DELETED = "TENANT_DELETED"
    TENANT_VIEWED = "TENANT_VIEWED"

    # Gestion des super-admins
    SUPER_ADMIN_CREATED = "SUPER_ADMIN_CREATED"
    SUPER_ADMIN_UPDATED = "SUPER_ADMIN_UPDATED"
    SUPER_ADMIN_DEACTIVATED = "SUPER_ADMIN_DEACTIVATED"

    # Accès aux données (cross-tenant)
    DATA_ACCESSED = "DATA_ACCESSED"
    DATA_EXPORTED = "DATA_EXPORTED"
    SUPPORT_ACCESS = "SUPPORT_ACCESS"

    # Switch de tenant (Option B)
    SWITCH_TENANT = "SWITCH_TENANT"

    # Configuration
    CONFIG_UPDATED = "CONFIG_UPDATED"

    # Divers
    OTHER = "OTHER"


class PlatformAuditLog(Base):
    """
    Log d'audit d'une action super-admin.

    Chaque entrée représente une action effectuée par un super-admin
    sur la plateforme. Ces logs sont immuables et conservés pour
    la conformité réglementaire.

    Attributes:
        id: Identifiant unique
        super_admin_id: Super-admin ayant effectué l'action
        action: Type d'action (AuditAction)
        target_tenant_id: Tenant concerné (si applicable)
        target_table: Table concernée (si data access)
        target_id: ID de l'enregistrement concerné
        details: Détails JSON de l'action
        ip_address: Adresse IP source
        user_agent: User-agent du navigateur
        created_at: Horodatage de l'action

    Example:
        log = PlatformAuditLog(
            super_admin_id=1,
            action=AuditAction.TENANT_CREATED,
            target_tenant_id=5,
            details={"name": "SSIAD Lyon", "plan": "STANDARD"},
            ip_address="192.168.1.100"
        )
    """

    __tablename__ = "platform_audit_logs"
    __table_args__ = {
        "comment": "Logs d'audit des actions super-admin (immuables)"
    }

    # === Colonnes ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du log"
    )

    # --- Qui ---

    super_admin_id: Mapped[int] = mapped_column(
        ForeignKey("super_admins.id", ondelete="SET NULL"),
        nullable=True,  # Peut être NULL si super-admin supprimé
        index=True,
        doc="Super-admin ayant effectué l'action"
    )

    # --- Quoi ---

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Type d'action effectuée"
    )

    # --- Sur quoi ---

    target_tenant_id: Mapped[int | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Tenant concerné par l'action (si applicable)"
    )

    target_table: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Table concernée (si accès données)"
    )

    target_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="ID de l'enregistrement concerné"
    )

    # --- Détails ---

    details: Mapped[Dict[str, Any] | None] = mapped_column(
        JSONBCompatible,
        nullable=True,
        doc="Détails JSON de l'action (ancien/nouveau valeurs, etc.)"
    )

    # --- Contexte technique ---

    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
        doc="Adresse IP source de la requête"
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="User-Agent du navigateur"
    )

    request_id: Mapped[str | None] = mapped_column(
        String(36),  # UUID
        nullable=True,
        index=True,
        doc="ID de corrélation de la requête"
    )

    # --- Horodatage ---

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        doc="Horodatage de l'action"
    )

    # === Relations ===

    super_admin: Mapped[Optional["SuperAdmin"]] = relationship(
        "SuperAdmin",
        back_populates="audit_logs",
        doc="Super-admin ayant effectué l'action"
    )

    target_tenant: Mapped[Optional["Tenant"]] = relationship(
        "Tenant",
        doc="Tenant concerné par l'action"
    )

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<PlatformAuditLog(id={self.id}, action='{self.action}', super_admin_id={self.super_admin_id})>"

    def __str__(self) -> str:
        tenant_info = f" on tenant {self.target_tenant_id}" if self.target_tenant_id else ""
        return f"[{self.created_at}] {self.action}{tenant_info}"

    @classmethod
    def create_log(
            cls,
            super_admin_id: int,
            action: AuditAction,
            target_tenant_id: int | None = None,
            target_table: str | None = None,
            target_id: int | None = None,
            details: Dict[str, Any] | None = None,
            ip_address: str | None = None,
            user_agent: str | None = None,
            request_id: str | None = None,
    ) -> "PlatformAuditLog":
        """
        Factory method pour créer un log d'audit.

        Args:
            super_admin_id: ID du super-admin
            action: Type d'action
            target_tenant_id: Tenant concerné
            target_table: Table concernée
            target_id: ID de l'enregistrement
            details: Détails JSON
            ip_address: Adresse IP
            user_agent: User-Agent
            request_id: ID de corrélation

        Returns:
            Instance de PlatformAuditLog
        """
        return cls(
            super_admin_id=super_admin_id,
            action=action.value if isinstance(action, AuditAction) else action,
            target_tenant_id=target_tenant_id,
            target_table=target_table,
            target_id=target_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )


# === Fonctions utilitaires ===

def log_tenant_action(
        db_session,
        super_admin_id: int,
        action: AuditAction,
        tenant_id: int,
        details: Dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
) -> PlatformAuditLog:
    """
    Crée et enregistre un log d'action sur un tenant.

    Usage:
        log = log_tenant_action(
            db,
            super_admin_id=1,
            action=AuditAction.TENANT_SUSPENDED,
            tenant_id=5,
            details={"reason": "Non-paiement"}
        )
    """
    log = PlatformAuditLog.create_log(
        super_admin_id=super_admin_id,
        action=action,
        target_tenant_id=tenant_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db_session.add(log)
    return log


def log_data_access(
        db_session,
        super_admin_id: int,
        tenant_id: int,
        table_name: str,
        record_id: int | None = None,
        reason: str | None = None,
        ip_address: str | None = None,
) -> PlatformAuditLog:
    """
    Crée et enregistre un log d'accès aux données d'un tenant.

    Usage:
        log = log_data_access(
            db,
            super_admin_id=1,
            tenant_id=5,
            table_name="patients",
            record_id=42,
            reason="Support ticket #12345"
        )
    """
    log = PlatformAuditLog.create_log(
        super_admin_id=super_admin_id,
        action=AuditAction.DATA_ACCESSED,
        target_tenant_id=tenant_id,
        target_table=table_name,
        target_id=record_id,
        details={"reason": reason} if reason else None,
        ip_address=ip_address,
    )
    db_session.add(log)
    return log