"""
Modèle Role - Rôles fonctionnels.

Ce module définit la table `roles` qui représente les rôles
fonctionnels dans CareLink (Médecin traitant, Coordinateur, etc.).

Architecture normalisée (v4.3) :
- Les permissions sont stockées dans la table `permissions`
- L'association Role ↔ Permission est dans `role_permissions`
- Plus de stockage JSON des permissions

Important :
- Un rôle est une fonction dans CareLink, il peut changer.
- Une profession (dans la table `professions`) est un diplôme d'État.
- Les permissions sont attachées aux rôles via la table de jonction.
"""

from typing import TYPE_CHECKING, List

from sqlalchemy import String, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.enums import RoleName
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user.user import User
    from app.models.user.user_associations import UserRole
    from app.models.user.permission import Permission
    from app.models.user.role_permission import RolePermission
    from app.models.tenants.tenant import Tenant


class Role(TimestampMixin, Base):
    """
    Représente un rôle fonctionnel dans CareLink.
    
    Les rôles définissent ce qu'un utilisateur peut faire dans l'application.
    Un utilisateur peut avoir plusieurs rôles (many-to-many via user_roles).
    Les permissions sont associées via la table role_permissions.
    
    Attributes:
        id: Identifiant unique
        name: Nom du rôle (MEDECIN_TRAITANT, COORDINATEUR, etc.)
        description: Description du rôle
        is_system_role: Rôle système non modifiable
        tenant_id: NULL = rôle système, sinon = rôle custom du tenant
        users: Utilisateurs ayant ce rôle
        permissions: Permissions du rôle (via role_permissions)
    
    Example:
        coordinateur = Role(
            name="COORDINATEUR",
            description="Coordinateur de parcours de soins",
            is_system_role=True
        )
        # Les permissions sont ajoutées via RolePermission
    """
    
    __tablename__ = "roles"
    __table_args__ = {
        "comment": "Table des rôles fonctionnels"
    }
    
    # === Colonnes ===
    
    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du rôle",
        info={"description": "Clé primaire auto-incrémentée"}
    )
    
    # Multi-tenant: NULL pour les rôles système, défini pour les rôles personnalisés
    tenant_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="ID du tenant (NULL = rôle système partagé)",
        info={"description": "Clé étrangère vers le tenant propriétaire du rôle"}
    )
    
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Nom technique du rôle",
        info={
            "description": "Identifiant du rôle (unique par tenant)",
            "enum": [e.value for e in RoleName],
            "example": "COORDINATEUR"
        }
    )
    
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Description lisible du rôle",
        info={
            "description": "Description pour l'interface utilisateur",
            "example": "Coordinateur de parcours de soins"
        }
    )
    
    is_system_role: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Rôle système protégé contre les modifications",
        info={
            "description": "True = rôle créé par le système, non modifiable",
            "default": False
        }
    )
    
    # === Relations ===
    
    tenant: Mapped["Tenant | None"] = relationship(
        "Tenant",
        back_populates="roles",
        doc="Tenant propriétaire du rôle (None = rôle système)"
    )
    
    user_associations: Mapped[List["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
        doc="Associations avec les utilisateurs (via table de jonction)"
    )
    
    permission_associations: Mapped[List["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
        doc="Associations avec les permissions (via table de jonction)"
    )
    
    # === Propriétés ===
    
    @property
    def users(self) -> List["User"]:
        """Liste des utilisateurs ayant ce rôle."""
        return [ua.user for ua in self.user_associations]
    
    @property
    def permissions(self) -> List["Permission"]:
        """Liste des permissions de ce rôle."""
        return [pa.permission for pa in self.permission_associations]
    
    @property
    def permission_codes(self) -> List[str]:
        """Liste des codes de permissions de ce rôle."""
        return [p.code for p in self.permissions]
    
    @property
    def is_custom(self) -> bool:
        """Retourne True si c'est un rôle custom (non système)."""
        return self.tenant_id is not None and not self.is_system_role
    
    # === Méthodes ===
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}', system={self.is_system_role})>"
    
    def __str__(self) -> str:
        return self.description or self.name
    
    def has_permission(self, permission_code: str) -> bool:
        """
        Vérifie si le rôle possède une permission spécifique.
        
        Args:
            permission_code: Code de la permission à vérifier
            
        Returns:
            True si le rôle a la permission
        """
        # ADMIN_FULL donne toutes les permissions
        if "ADMIN_FULL" in self.permission_codes:
            return True
        
        return permission_code in self.permission_codes
    
    def has_any_permission(self, permission_codes: List[str]) -> bool:
        """
        Vérifie si le rôle possède au moins une des permissions.
        
        Args:
            permission_codes: Liste des codes de permissions à vérifier
            
        Returns:
            True si le rôle a au moins une des permissions
        """
        if "ADMIN_FULL" in self.permission_codes:
            return True
        
        return any(code in self.permission_codes for code in permission_codes)
    
    def has_all_permissions(self, permission_codes: List[str]) -> bool:
        """
        Vérifie si le rôle possède toutes les permissions.
        
        Args:
            permission_codes: Liste des codes de permissions à vérifier
            
        Returns:
            True si le rôle a toutes les permissions
        """
        if "ADMIN_FULL" in self.permission_codes:
            return True
        
        return all(code in self.permission_codes for code in permission_codes)


# =============================================================================
# DONNÉES INITIALES - Rôles système
# =============================================================================
# Note: Les permissions sont maintenant dans INITIAL_ROLE_PERMISSIONS (role_permission.py)

INITIAL_ROLES = [
    {
        "name": "ADMIN",
        "description": "Administrateur système",
        "is_system_role": True
    },
    {
        "name": "COORDINATEUR",
        "description": "Coordinateur de parcours de soins",
        "is_system_role": True
    },
    {
        "name": "MEDECIN_TRAITANT",
        "description": "Médecin traitant référent",
        "is_system_role": True
    },
    {
        "name": "MEDECIN_SPECIALISTE",
        "description": "Médecin spécialiste intervenant",
        "is_system_role": True
    },
    {
        "name": "INFIRMIERE",
        "description": "Infirmier(ère)",
        "is_system_role": True
    },
    {
        "name": "AIDE_SOIGNANTE",
        "description": "Aide-soignant(e)",
        "is_system_role": True
    },
    {
        "name": "KINESITHERAPEUTE",
        "description": "Kinésithérapeute",
        "is_system_role": True
    },
    {
        "name": "AUXILIAIRE_VIE",
        "description": "Auxiliaire de vie sociale",
        "is_system_role": True
    },
    {
        "name": "ASSISTANT_SOCIAL",
        "description": "Assistant(e) social(e)",
        "is_system_role": True
    },
    {
        "name": "INTERVENANT",
        "description": "Intervenant ponctuel",
        "is_system_role": True
    }
]
