"""
Modèle UserTenantAssignment - Rattachements cross-tenant.

Ce module définit la table `user_tenant_assignments` qui permet à un
utilisateur d'accéder à plusieurs tenants (rattachement temporaire,
remplacement, consultant, etc.).

IMPORTANT :
- Un utilisateur a toujours un tenant PRINCIPAL (users.tenant_id)
- Cette table gère les accès SUPPLÉMENTAIRES à d'autres tenants
- Permet le cross-tenant sans dupliquer l'utilisateur
- Conserve la contrainte RPPS unique

Historique :
- v4.3 : Déplacé de platform/ vers user/ (cohérence avec user_associations)
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    String, Text, Boolean, Date, DateTime,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin
from app.models.types import JSONBCompatible

if TYPE_CHECKING:
    from app.models.user.user import User
    from app.models.tenants.tenant import Tenant
    from app.models.platform.super_admin import SuperAdmin


class AssignmentType(str, Enum):
    """
    Types de rattachement à un tenant supplémentaire.

    - PRIMARY : Tenant principal (dans users.tenant_id, pas ici)
    - TEMPORARY : Mission temporaire avec dates
    - REPLACEMENT : Remplacement d'un professionnel absent
    - CONSULTANT : Intervention ponctuelle (médecin spécialiste)
    - PERMANENT : Rattachement permanent à un autre tenant
    """
    TEMPORARY = "TEMPORARY"  # Mission temporaire (ex: 3 mois)
    REPLACEMENT = "REPLACEMENT"  # Remplacement congé maternité, etc.
    CONSULTANT = "CONSULTANT"  # Intervention ponctuelle
    PERMANENT = "PERMANENT"  # Rattachement permanent multi-structures


class UserTenantAssignment(TimestampMixin, Base):
    """
    Rattachement d'un utilisateur à un tenant supplémentaire.

    Permet à un professionnel de santé d'intervenir sur plusieurs
    structures sans dupliquer son compte (RPPS unique conservé).

    Attributes:
        id: Identifiant unique
        user_id: Utilisateur concerné
        tenant_id: Tenant de destination
        assignment_type: Type de rattachement
        start_date: Date de début
        end_date: Date de fin (NULL = indéterminé)
        reason: Justification (traçabilité)
        permissions: Permissions spécifiques (JSON, NULL = hérite du user)
        granted_by_user_id: Admin du tenant ayant accordé l'accès
        granted_by_super_admin_id: Ou super-admin ayant accordé
        is_active: Rattachement actif
        revoked_at: Date de révocation
        revoked_by_user_id: Qui a révoqué

    Example:
        # Sophie (user_id=10, tenant principal=1) intervient sur tenant 2
        assignment = UserTenantAssignment(
            user_id=10,
            tenant_id=2,
            assignment_type=AssignmentType.TEMPORARY,
            start_date=date(2025, 1, 15),
            end_date=date(2025, 4, 15),
            reason="Remplacement congé maternité Mme Dupont",
            granted_by_user_id=42  # Admin du SSIAD Lyon
        )
    """

    __tablename__ = "user_tenant_assignments"
    __table_args__ = (
        # Un user ne peut avoir qu'un seul rattachement actif par tenant
        UniqueConstraint(
            "user_id", "tenant_id", "is_active",
            name="uq_user_tenant_active"
        ),
        # Index pour les requêtes fréquentes
        Index("ix_user_tenant_assignments_user", "user_id"),
        Index("ix_user_tenant_assignments_tenant", "tenant_id"),
        Index("ix_user_tenant_assignments_active", "is_active", "start_date", "end_date"),
        {
            "comment": "Rattachements d'utilisateurs à des tenants supplémentaires (cross-tenant)"
        }
    )

    # === Clé primaire ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du rattachement"
    )

    # === Références principales ===

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Utilisateur concerné"
    )

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        doc="Tenant de destination (différent du tenant principal)"
    )

    # === Type et période ===

    assignment_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AssignmentType.TEMPORARY.value,
        doc="Type de rattachement"
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="Date de début du rattachement"
    )

    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        doc="Date de fin du rattachement (NULL = indéterminé)"
    )

    # === Justification (traçabilité) ===

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Justification du rattachement (obligatoire pour conformité)"
    )

    # === Permissions spécifiques (optionnel) ===

    permissions: Mapped[List[str] | None] = mapped_column(
        JSONBCompatible,
        nullable=True,
        doc="Permissions spécifiques pour ce tenant (JSON array, NULL = hérite du user)"
    )

    # === Qui a accordé l'accès ===

    granted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Admin du tenant ayant accordé l'accès"
    )

    granted_by_super_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("super_admins.id", ondelete="SET NULL"),
        nullable=True,
        doc="Super-admin ayant accordé l'accès"
    )

    # === Statut ===

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Rattachement actif"
    )

    # === Révocation ===

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date de révocation"
    )

    revoked_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Admin ayant révoqué l'accès"
    )

    revoked_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Raison de la révocation"
    )

    # === Relations ===

    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="tenant_assignments",
        doc="Utilisateur concerné"
    )

    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="user_assignments",
        doc="Tenant de destination"
    )

    granted_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[granted_by_user_id],
        doc="Admin du tenant ayant accordé l'accès"
    )

    granted_by_super_admin: Mapped[Optional["SuperAdmin"]] = relationship(
        "SuperAdmin",
        doc="Super-admin ayant accordé l'accès"
    )

    revoked_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[revoked_by_user_id],
        doc="Admin ayant révoqué l'accès"
    )

    # === Propriétés ===

    @property
    def is_expired(self) -> bool:
        """Vérifie si le rattachement a expiré (date de fin dépassée)."""
        if not self.end_date:
            return False
        return self.end_date < date.today()

    @property
    def is_future(self) -> bool:
        """Vérifie si le rattachement n'a pas encore commencé."""
        return self.start_date > date.today()

    @property
    def is_valid(self) -> bool:
        """
        Vérifie si le rattachement est actuellement valide.

        Un rattachement est valide si :
        - Il est actif (is_active=True)
        - Il n'a pas expiré (end_date non dépassée ou NULL)
        - Il a commencé (start_date atteinte)
        """
        if not self.is_active:
            return False
        if self.is_expired:
            return False
        if self.is_future:
            return False
        return True

    @property
    def days_remaining(self) -> int | None:
        """Retourne le nombre de jours restants (None si pas de date de fin)."""
        if not self.end_date:
            return None
        if self.is_expired:
            return 0
        return (self.end_date - date.today()).days

    @property
    def assignment_type_label(self) -> str:
        """Retourne un libellé lisible du type de rattachement."""
        labels = {
            AssignmentType.TEMPORARY.value: "Mission temporaire",
            AssignmentType.REPLACEMENT.value: "Remplacement",
            AssignmentType.CONSULTANT.value: "Consultant/Intervenant",
            AssignmentType.PERMANENT.value: "Rattachement permanent",
        }
        return labels.get(self.assignment_type, self.assignment_type)

    # === Méthodes ===

    def __repr__(self) -> str:
        return (
            f"<UserTenantAssignment("
            f"user_id={self.user_id}, "
            f"tenant_id={self.tenant_id}, "
            f"type='{self.assignment_type}', "
            f"valid={self.is_valid}"
            f")>"
        )

    def __str__(self) -> str:
        status = "✓" if self.is_valid else "✗"
        return f"{status} User {self.user_id} → Tenant {self.tenant_id} ({self.assignment_type_label})"

    def revoke(self, revoked_by: int, reason: str | None = None) -> None:
        """
        Révoque le rattachement.

        Args:
            revoked_by: ID de l'utilisateur révoquant
            reason: Raison de la révocation
        """
        self.is_active = False
        self.revoked_at = datetime.now(timezone.utc)
        self.revoked_by_user_id = revoked_by
        self.revoked_reason = reason

    def extend(self, new_end_date: date) -> None:
        """
        Prolonge le rattachement.

        Args:
            new_end_date: Nouvelle date de fin
        """
        if new_end_date <= (self.end_date or date.today()):
            raise ValueError("La nouvelle date doit être postérieure à la date actuelle")
        self.end_date = new_end_date

    def has_permission(self, permission: str) -> bool:
        """
        Vérifie si le rattachement accorde une permission spécifique.

        Args:
            permission: Permission à vérifier

        Returns:
            True si la permission est accordée (ou si permissions=NULL)
        """
        if self.permissions is None:
            # NULL = hérite toutes les permissions du user
            return True
        return permission in self.permissions

    def get_effective_permissions(self, user_permissions: List[str]) -> List[str]:
        """
        Calcule les permissions effectives pour ce tenant.

        Args:
            user_permissions: Permissions de base du user

        Returns:
            Liste des permissions effectives
        """
        if self.permissions is None:
            # Hérite toutes les permissions du user
            return user_permissions
        # Intersection : permissions du user ∩ permissions accordées
        return [p for p in user_permissions if p in self.permissions]


# === Fonctions utilitaires ===

def get_user_tenant_access(
        db_session,
        user_id: int,
        include_expired: bool = False
) -> List[Dict[str, Any]]:
    """
    Retourne tous les tenants accessibles par un utilisateur.

    Args:
        db_session: Session SQLAlchemy
        user_id: ID de l'utilisateur
        include_expired: Inclure les rattachements expirés

    Returns:
        Liste de dicts avec tenant_id, type, is_primary, is_valid
    """
    from app.models.user.user import User

    user = db_session.query(User).get(user_id)
    if not user:
        return []

    # Tenant principal
    tenants = [{
        "tenant_id": user.tenant_id,
        "type": "PRIMARY",
        "is_primary": True,
        "is_valid": True,
        "start_date": None,
        "end_date": None,
    }]

    # Rattachements supplémentaires
    query = db_session.query(UserTenantAssignment).filter(
        UserTenantAssignment.user_id == user_id
    )

    if not include_expired:
        query = query.filter(UserTenantAssignment.is_active == True)

    for assignment in query.all():
        tenants.append({
            "tenant_id": assignment.tenant_id,
            "type": assignment.assignment_type,
            "is_primary": False,
            "is_valid": assignment.is_valid,
            "start_date": assignment.start_date,
            "end_date": assignment.end_date,
        })

    return tenants


def check_user_tenant_access(
        db_session,
        user_id: int,
        tenant_id: int
) -> bool:
    """
    Vérifie si un utilisateur a accès à un tenant spécifique.

    Args:
        db_session: Session SQLAlchemy
        user_id: ID de l'utilisateur
        tenant_id: ID du tenant à vérifier

    Returns:
        True si l'utilisateur a accès
    """
    from app.models.user.user import User

    user = db_session.query(User).get(user_id)
    if not user:
        return False

    # Tenant principal
    if user.tenant_id == tenant_id:
        return True

    # Rattachement supplémentaire valide
    assignment = db_session.query(UserTenantAssignment).filter(
        UserTenantAssignment.user_id == user_id,
        UserTenantAssignment.tenant_id == tenant_id,
        UserTenantAssignment.is_active == True
    ).first()

    if assignment and assignment.is_valid:
        return True

    return False