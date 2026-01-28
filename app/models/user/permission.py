"""
Modèle Permission - Permissions granulaires du système.

Ce module définit la table `permissions` qui représente les permissions
individuelles pouvant être accordées aux rôles.

Architecture normalisée :
- Permission : Définition des permissions (référentiel)
- RolePermission : Association Role ↔ Permission (many-to-many)
- Role : Rôles fonctionnels (sans JSON de permissions)

Avantages vs JSON :
- Contraintes d'intégrité en base
- Requêtes SQL efficaces ("tous les rôles ayant PATIENT_VIEW")
- Référentiel unique et auditable
- Permissions custom par tenant
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from sqlalchemy import String, Boolean, Integer, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin
from app.models.enums import PermissionCategory

if TYPE_CHECKING:
    from app.models.tenants.tenant import Tenant
    from app.models.user.role_permission import RolePermission


class Permission(TimestampMixin, Base):
    """
    Représente une permission granulaire du système.
    
    Les permissions sont les briques élémentaires de l'autorisation.
    Elles sont regroupées par catégorie pour faciliter l'UI.
    
    Attributes:
        id: Identifiant unique
        code: Code technique unique (PATIENT_VIEW, USER_CREATE...)
        name: Nom lisible ("Voir les patients")
        description: Description détaillée
        category: Catégorie (PATIENT, USER, EVALUATION...)
        is_system: Permission système non supprimable
        tenant_id: NULL = permission système, sinon = permission custom du tenant
        display_order: Ordre d'affichage dans l'UI
    
    Example:
        patient_view = Permission(
            code="PATIENT_VIEW",
            name="Voir les patients",
            description="Permet de consulter les dossiers patients",
            category=PermissionCategory.PATIENT,
            is_system=True
        )
    """
    
    __tablename__ = "permissions"
    __table_args__ = (
        # Code unique par tenant (ou global si tenant_id=NULL)
        UniqueConstraint("code", "tenant_id", name="uq_permission_code_tenant"),
        {"comment": "Table des permissions granulaires du système"}
    )
    
    # === Colonnes ===
    
    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de la permission",
        info={"description": "Clé primaire auto-incrémentée"}
    )
    
    # Multi-tenant: NULL pour les permissions système, défini pour les customs
    tenant_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="ID du tenant (NULL = permission système partagée)",
        info={"description": "Clé étrangère vers le tenant propriétaire"}
    )
    
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Code technique unique de la permission",
        info={
            "description": "Identifiant technique (PATIENT_VIEW, USER_CREATE...)",
            "example": "PATIENT_VIEW"
        }
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Nom lisible de la permission",
        info={
            "description": "Nom pour l'interface utilisateur",
            "example": "Voir les patients"
        }
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Description détaillée de la permission",
        info={
            "description": "Explication de ce que permet cette permission",
            "example": "Permet de consulter les dossiers patients et leurs informations"
        }
    )
    
    category: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        doc="Catégorie de la permission",
        info={
            "description": "Regroupement pour l'UI",
            "enum": [e.value for e in PermissionCategory],
            "example": "PATIENT"
        }
    )
    
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Permission système non supprimable",
        info={
            "description": "True = permission créée par le système, non modifiable",
            "default": False
        }
    )
    
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
        doc="Ordre d'affichage dans l'UI",
        info={
            "description": "Pour trier les permissions dans les formulaires",
            "default": 100
        }
    )
    
    # === Relations ===
    
    tenant: Mapped["Tenant | None"] = relationship(
        "Tenant",
        doc="Tenant propriétaire de la permission (None = système)"
    )
    
    role_associations: Mapped[List["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
        doc="Associations avec les rôles (via table de jonction)"
    )
    
    # === Propriétés ===
    
    @property
    def is_custom(self) -> bool:
        """Retourne True si c'est une permission custom (non système)."""
        return self.tenant_id is not None
    
    @property
    def full_code(self) -> str:
        """Retourne le code complet (avec préfixe tenant si custom)."""
        if self.tenant_id:
            return f"CUSTOM_{self.tenant_id}_{self.code}"
        return self.code
    
    # === Méthodes ===
    
    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, code='{self.code}', category='{self.category}')>"
    
    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


# =============================================================================
# DONNÉES INITIALES - Permissions système
# =============================================================================

INITIAL_PERMISSIONS = [
    # === ADMIN ===
    {
        "code": "ADMIN_FULL",
        "name": "Accès administrateur complet",
        "description": "Donne accès à toutes les fonctionnalités sans restriction",
        "category": "ADMIN",
        "is_system": True,
        "display_order": 1
    },
    
    # === PATIENT ===
    {
        "code": "PATIENT_VIEW",
        "name": "Voir les patients",
        "description": "Permet de consulter les dossiers patients et leurs informations",
        "category": "PATIENT",
        "is_system": True,
        "display_order": 10
    },
    {
        "code": "PATIENT_CREATE",
        "name": "Créer un patient",
        "description": "Permet de créer un nouveau dossier patient",
        "category": "PATIENT",
        "is_system": True,
        "display_order": 11
    },
    {
        "code": "PATIENT_EDIT",
        "name": "Modifier un patient",
        "description": "Permet de modifier les informations d'un patient existant",
        "category": "PATIENT",
        "is_system": True,
        "display_order": 12
    },
    {
        "code": "PATIENT_DELETE",
        "name": "Supprimer un patient",
        "description": "Permet de supprimer ou archiver un dossier patient",
        "category": "PATIENT",
        "is_system": True,
        "display_order": 13
    },
    
    # === EVALUATION ===
    {
        "code": "EVALUATION_VIEW",
        "name": "Voir les évaluations",
        "description": "Permet de consulter les évaluations AGGIR et autres",
        "category": "EVALUATION",
        "is_system": True,
        "display_order": 20
    },
    {
        "code": "EVALUATION_CREATE",
        "name": "Créer une évaluation",
        "description": "Permet de créer une nouvelle évaluation patient",
        "category": "EVALUATION",
        "is_system": True,
        "display_order": 21
    },
    {
        "code": "EVALUATION_EDIT",
        "name": "Modifier une évaluation",
        "description": "Permet de modifier une évaluation existante",
        "category": "EVALUATION",
        "is_system": True,
        "display_order": 22
    },
    {
        "code": "EVALUATION_VALIDATE",
        "name": "Valider une évaluation",
        "description": "Permet de valider officiellement une évaluation",
        "category": "EVALUATION",
        "is_system": True,
        "display_order": 23
    },
    
    # === VITALS ===
    {
        "code": "VITALS_VIEW",
        "name": "Voir les constantes",
        "description": "Permet de consulter les constantes vitales des patients",
        "category": "VITALS",
        "is_system": True,
        "display_order": 30
    },
    {
        "code": "VITALS_CREATE",
        "name": "Saisir des constantes",
        "description": "Permet de saisir de nouvelles mesures de constantes vitales",
        "category": "VITALS",
        "is_system": True,
        "display_order": 31
    },
    
    # === USER ===
    {
        "code": "USER_VIEW",
        "name": "Voir les utilisateurs",
        "description": "Permet de consulter la liste des professionnels",
        "category": "USER",
        "is_system": True,
        "display_order": 40
    },
    {
        "code": "USER_CREATE",
        "name": "Créer un utilisateur",
        "description": "Permet de créer un nouveau compte utilisateur",
        "category": "USER",
        "is_system": True,
        "display_order": 41
    },
    {
        "code": "USER_EDIT",
        "name": "Modifier un utilisateur",
        "description": "Permet de modifier les informations d'un utilisateur",
        "category": "USER",
        "is_system": True,
        "display_order": 42
    },
    {
        "code": "USER_DELETE",
        "name": "Supprimer un utilisateur",
        "description": "Permet de désactiver ou supprimer un compte utilisateur",
        "category": "USER",
        "is_system": True,
        "display_order": 43
    },
    
    # === COORDINATION ===
    {
        "code": "COORDINATION_VIEW",
        "name": "Voir la coordination",
        "description": "Permet de consulter le carnet de coordination",
        "category": "COORDINATION",
        "is_system": True,
        "display_order": 50
    },
    {
        "code": "COORDINATION_CREATE",
        "name": "Créer une entrée",
        "description": "Permet d'ajouter une entrée au carnet de coordination",
        "category": "COORDINATION",
        "is_system": True,
        "display_order": 51
    },
    {
        "code": "COORDINATION_EDIT",
        "name": "Modifier une entrée",
        "description": "Permet de modifier une entrée de coordination",
        "category": "COORDINATION",
        "is_system": True,
        "display_order": 52
    },
    
    # === CAREPLAN ===
    {
        "code": "CAREPLAN_VIEW",
        "name": "Voir les plans d'aide",
        "description": "Permet de consulter les plans d'aide des patients",
        "category": "CAREPLAN",
        "is_system": True,
        "display_order": 60
    },
    {
        "code": "CAREPLAN_CREATE",
        "name": "Créer un plan d'aide",
        "description": "Permet de créer un nouveau plan d'aide",
        "category": "CAREPLAN",
        "is_system": True,
        "display_order": 61
    },
    {
        "code": "CAREPLAN_EDIT",
        "name": "Modifier un plan d'aide",
        "description": "Permet de modifier un plan d'aide existant",
        "category": "CAREPLAN",
        "is_system": True,
        "display_order": 62
    },
    {
        "code": "CAREPLAN_VALIDATE",
        "name": "Valider un plan d'aide",
        "description": "Permet de valider officiellement un plan d'aide",
        "category": "CAREPLAN",
        "is_system": True,
        "display_order": 63
    },
    
    # === ACCESS (Gestion des accès RGPD) ===
    {
        "code": "ACCESS_GRANT",
        "name": "Accorder un accès",
        "description": "Permet d'accorder l'accès à un dossier patient",
        "category": "ACCESS",
        "is_system": True,
        "display_order": 70
    },
    {
        "code": "ACCESS_REVOKE",
        "name": "Révoquer un accès",
        "description": "Permet de révoquer l'accès à un dossier patient",
        "category": "ACCESS",
        "is_system": True,
        "display_order": 71
    },
    
    # === ROLE (Gestion des rôles) ===
    {
        "code": "ROLE_VIEW",
        "name": "Voir les rôles",
        "description": "Permet de consulter les rôles et leurs permissions",
        "category": "ROLE",
        "is_system": True,
        "display_order": 80
    },
    {
        "code": "ROLE_CREATE",
        "name": "Créer un rôle",
        "description": "Permet de créer un nouveau rôle personnalisé",
        "category": "ROLE",
        "is_system": True,
        "display_order": 81
    },
    {
        "code": "ROLE_EDIT",
        "name": "Modifier un rôle",
        "description": "Permet de modifier un rôle et ses permissions",
        "category": "ROLE",
        "is_system": True,
        "display_order": 82
    },
    {
        "code": "ROLE_DELETE",
        "name": "Supprimer un rôle",
        "description": "Permet de supprimer un rôle personnalisé",
        "category": "ROLE",
        "is_system": True,
        "display_order": 83
    },
    {
        "code": "ROLE_ASSIGN",
        "name": "Attribuer un rôle",
        "description": "Permet d'attribuer un rôle à un utilisateur",
        "category": "ROLE",
        "is_system": True,
        "display_order": 84
    },
]
