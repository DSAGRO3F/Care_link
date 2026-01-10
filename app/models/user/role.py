"""
Modèle Role - Rôles fonctionnels.

Ce module définit la table `roles` qui représente les rôles
fonctionnels dans CareLink (Médecin traitant, Coordinateur, etc.).

Important :
- Un rôle est une fonction dans CareLink, il peut changer.
- Une profession (dans la table `professions`) est un diplôme d'État.
- Les permissions sont attachées aux rôles, pas aux professions.
"""

from typing import TYPE_CHECKING, List, Any

from sqlalchemy import String, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin
from app.models.enums import RoleName, Permission

if TYPE_CHECKING:
    from app.models.user.user import User
    from app.models.user.user_associations import UserRole


class Role(TimestampMixin, Base):
    """
    Représente un rôle fonctionnel dans CareLink.
    
    Les rôles définissent ce qu'un utilisateur peut faire dans l'application.
    Un utilisateur peut avoir plusieurs rôles (many-to-many via user_roles).
    
    Attributes:
        id: Identifiant unique
        name: Nom du rôle (MEDECIN_TRAITANT, COORDINATEUR, etc.)
        description: Description du rôle
        permissions: Liste des permissions JSON
        is_system_role: Rôle système non modifiable
        users: Utilisateurs ayant ce rôle
    
    Example:
        coordinateur = Role(
            name=RoleName.COORDINATEUR,
            description="Coordinateur de parcours de soins",
            permissions=[
                Permission.PATIENT_VIEW,
                Permission.PATIENT_EDIT,
                Permission.ACCESS_GRANT
            ],
            is_system_role=True
        )
    """
    
    __tablename__ = "roles"
    __table_args__ = {
        "comment": "Table des rôles fonctionnels avec leurs permissions"
    }
    
    # === Colonnes ===
    
    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du rôle",
        info={
            "description": "Clé primaire auto-incrémentée"
        }
    )
    
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        doc="Nom technique du rôle",
        info={
            "description": "Identifiant unique du rôle",
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
    
    permissions: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        doc="Liste des permissions accordées à ce rôle",
        info={
            "description": "Permissions JSON",
            "example": ["PATIENT_VIEW", "PATIENT_EDIT", "EVALUATION_CREATE"]
        }
    )
    
    is_system_role: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        doc="Rôle système protégé contre les modifications",
        info={
            "description": "True = rôle créé par le système, non modifiable",
            "default": False
        }
    )
    
    # === Relations ===
    
    user_associations: Mapped[List["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
        doc="Associations avec les utilisateurs (via table de jonction)"
    )
    
    # === Propriétés ===
    
    @property
    def users(self) -> List["User"]:
        """Liste des utilisateurs ayant ce rôle."""
        return [ua.user for ua in self.user_associations]
    
    # === Méthodes ===
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}')>"
    
    def __str__(self) -> str:
        return self.description or self.name
    
    def has_permission(self, permission: Permission | str) -> bool:
        """
        Vérifie si le rôle possède une permission spécifique.
        
        Args:
            permission: Permission à vérifier (enum ou string)
            
        Returns:
            True si le rôle a la permission
        """
        if isinstance(permission, Permission):
            permission = permission.value
        
        # ADMIN_FULL donne toutes les permissions
        if Permission.ADMIN_FULL.value in self.permissions:
            return True
            
        return permission in self.permissions
    
    def add_permission(self, permission: Permission | str) -> None:
        """
        Ajoute une permission au rôle.
        
        Args:
            permission: Permission à ajouter
        """
        if isinstance(permission, Permission):
            permission = permission.value
            
        if permission not in self.permissions:
            self.permissions = self.permissions + [permission]
    
    def remove_permission(self, permission: Permission | str) -> None:
        """
        Retire une permission du rôle.
        
        Args:
            permission: Permission à retirer
        """
        if isinstance(permission, Permission):
            permission = permission.value
            
        if permission in self.permissions:
            self.permissions = [p for p in self.permissions if p != permission]


# === Données initiales (seed) ===

INITIAL_ROLES = [
    {
        "name": "ADMIN",
        "description": "Administrateur système",
        "permissions": ["ADMIN_FULL"],
        "is_system_role": True
    },
    {
        "name": "COORDINATEUR",
        "description": "Coordinateur de parcours de soins",
        "permissions": [
            "PATIENT_VIEW", "PATIENT_CREATE", "PATIENT_EDIT",
            "EVALUATION_VIEW", "EVALUATION_CREATE",
            "USER_VIEW",
            "ACCESS_GRANT", "ACCESS_REVOKE"
        ],
        "is_system_role": True
    },
    {
        "name": "MEDECIN_TRAITANT",
        "description": "Médecin traitant référent",
        "permissions": [
            "PATIENT_VIEW", "PATIENT_EDIT",
            "EVALUATION_VIEW", "EVALUATION_CREATE", "EVALUATION_VALIDATE",
            "VITALS_VIEW", "VITALS_CREATE"
        ],
        "is_system_role": True
    },
    {
        "name": "MEDECIN_SPECIALISTE",
        "description": "Médecin spécialiste intervenant",
        "permissions": [
            "PATIENT_VIEW",
            "EVALUATION_VIEW",
            "VITALS_VIEW"
        ],
        "is_system_role": True
    },
    {
        "name": "INFIRMIERE",
        "description": "Infirmier(ère)",
        "permissions": [
            "PATIENT_VIEW", "PATIENT_EDIT",
            "EVALUATION_VIEW", "EVALUATION_CREATE",
            "VITALS_VIEW", "VITALS_CREATE"
        ],
        "is_system_role": True
    },
    {
        "name": "AIDE_SOIGNANTE",
        "description": "Aide-soignant(e)",
        "permissions": [
            "PATIENT_VIEW",
            "EVALUATION_VIEW",
            "VITALS_VIEW", "VITALS_CREATE"
        ],
        "is_system_role": True
    },
    {
        "name": "KINESITHERAPEUTE",
        "description": "Kinésithérapeute",
        "permissions": [
            "PATIENT_VIEW",
            "EVALUATION_VIEW",
            "VITALS_VIEW"
        ],
        "is_system_role": True
    },
    {
        "name": "INTERVENANT",
        "description": "Intervenant ponctuel",
        "permissions": [
            "PATIENT_VIEW",
            "VITALS_VIEW"
        ],
        "is_system_role": True
    }
]
