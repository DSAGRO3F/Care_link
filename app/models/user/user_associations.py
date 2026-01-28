"""
Tables de jonction pour les relations many-to-many des utilisateurs.

Ce module définit :
- UserRole : Association User ↔ Role
- UserEntity : Association User ↔ Entity
"""

from datetime import date, datetime, timezone, time
from typing import TYPE_CHECKING
from decimal import Decimal

from sqlalchemy import String, Boolean, ForeignKey, Date, UniqueConstraint, Integer, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.enums import ContractType

if TYPE_CHECKING:
    from app.models.user.user import User
    from app.models.user.role import Role
    from app.models.organization.entity import Entity
    from app.models.tenants.tenant import Tenant


class UserRole(Base):
    """
    Association entre un utilisateur et un rôle.

    Table de jonction many-to-many entre `users` et `roles`.
    Inclut des métadonnées sur l'attribution du rôle.

    Attributes:
        user_id: ID de l'utilisateur
        role_id: ID du rôle
        assigned_at: Date d'attribution
        assigned_by: ID de l'utilisateur ayant attribué ce rôle
    """

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        {"comment": "Table de jonction User ↔ Role (many-to-many)"}
    )

    # === Clés primaires composites ===

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        doc="ID de l'utilisateur",
        info={"description": "Référence vers l'utilisateur"}
    )

    # === Multi-tenant ===

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant propriétaire de cet enregistrement"
    )

    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
        doc="ID du rôle",
        info={"description": "Référence vers le rôle"}
    )

    # === Colonnes additionnelles ===

    assigned_at: Mapped[datetime] = mapped_column(
        default=datetime.now(timezone.utc),
        doc="Date et heure d'attribution du rôle",
        info={"description": "Timestamp de l'attribution", "auto_generated": True}
    )

    assigned_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID de l'utilisateur ayant attribué ce rôle",
        info={"description": "Référence vers l'administrateur"}
    )

    # === Relations ===
    # IMPORTANT: foreign_keys doit être spécifié car il y a 2 FK vers users

    user: Mapped["User"] = relationship(
        "User",
        back_populates="role_associations",
        foreign_keys="[UserRole.user_id]",
        doc="Utilisateur concerné"
    )

    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="user_associations",
        doc="Rôle attribué"
    )

    assigner: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="[UserRole.assigned_by]",
        doc="Utilisateur ayant attribué ce rôle"
    )

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"


class UserEntity(Base):
    """
    Association entre un utilisateur et une entité de soins.

    Table de jonction many-to-many entre `users` et `entities`.
    Permet de gérer les rattachements multiples (libéraux, remplaçants, etc.)
    avec des dates de début/fin.

    Attributes:
        id: Identifiant unique
        user_id: ID de l'utilisateur
        entity_id: ID de l'entité
        is_primary: Est-ce l'entité principale ?
        contract_type: Type de contrat (SALARIE, LIBERAL, VACATION, REMPLACEMENT)
        start_date: Date de début du rattachement
        end_date: Date de fin (None = actif)
    """

    __tablename__ = "user_entities"
    __table_args__ = (
        UniqueConstraint("user_id", "entity_id", name="uq_user_entity"),
        {"comment": "Table de jonction User ↔ Entity (many-to-many)"}
    )

    # === Colonnes ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de l'association",
        info={"description": "Clé primaire auto-incrémentée"}
    )

    # === Multi-tenant ===

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant propriétaire de cet enregistrement"
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID de l'utilisateur",
        info={"description": "Référence vers l'utilisateur"}
    )

    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID de l'entité",
        info={"description": "Référence vers l'entité"}
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        doc="Est-ce l'entité principale de rattachement ?",
        info={"description": "True = entité principale pour cet utilisateur", "default": False}
    )

    contract_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Type de contrat ou de lien avec l'entité",
        info={
            "description": "Nature du rattachement",
            "enum": [e.value for e in ContractType],
            "example": "SALARIE"
        }
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="Date de début du rattachement",
        info={"description": "Date de début de la relation avec l'entité"}
    )

    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        doc="Date de fin du rattachement (None = actif)",
        info={"description": "Date de fin, NULL si toujours actif"}
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.now(timezone.utc),
        doc="Date de création de l'enregistrement",
        info={"description": "Timestamp de création"}
    )

    # === Capacités et zone d'intervention ===
    intervention_radius_km: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Rayon d'intervention personnalisé en km (NULL = défaut entité)"
    )

    max_daily_patients: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Nombre max de patients par jour"
    )

    max_weekly_hours: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Heures max par semaine"
    )

    # === Disponibilité par défaut ===
    default_start_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        comment="Heure de début par défaut"
    )

    default_end_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        comment="Heure de fin par défaut"
    )

    # === Relations ===

    user: Mapped["User"] = relationship(
        "User",
        back_populates="entity_associations",
        doc="Utilisateur concerné"
    )

    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="user_associations",
        doc="Entité de rattachement"
    )

    # === Propriétés ===

    @property
    def is_active(self) -> bool:
        """Retourne True si le rattachement est actif (pas de date de fin)."""
        return self.end_date is None

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<UserEntity(user_id={self.user_id}, entity_id={self.entity_id}, primary={self.is_primary})>"

    def terminate(self, end_date: date | None = None) -> None:
        """Met fin au rattachement."""
        self.end_date = end_date or date.today()
