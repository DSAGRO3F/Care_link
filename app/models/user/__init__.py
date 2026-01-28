"""
User models - Utilisateurs et RH.

Ce module contient les modèles liés aux utilisateurs :
- User : Utilisateurs/Professionnels
- Role : Rôles fonctionnels
- Permission : Permissions granulaires (v4.3)
- RolePermission : Association Role ↔ Permission (v4.3)
- Profession : Professions réglementées
- UserRole : Association User ↔ Role
- UserEntity : Association User ↔ Entity
- UserTenantAssignment : Association User ↔ Tenant (cross-tenant, v4.3)
- UserAvailability : Disponibilités des professionnels

Changelog:
    v4.3: Ajout Permission, RolePermission (normalisation)
    v4.3: Déplacement UserTenantAssignment depuis platform/
"""
from app.models.user.permission import Permission, INITIAL_PERMISSIONS
from app.models.user.profession import Profession, INITIAL_PROFESSIONS
from app.models.user.role import Role, INITIAL_ROLES
from app.models.user.role_permission import RolePermission, INITIAL_ROLE_PERMISSIONS
from app.models.user.user import User
from app.models.user.user_associations import UserRole, UserEntity
from app.models.user.user_availability import UserAvailability
from app.models.user.user_tenant_assignment import (
    UserTenantAssignment,
    AssignmentType,
    get_user_tenant_access,
    check_user_tenant_access,
)

__all__ = [
    # Modèles principaux
    "User",
    "Role",
    "Permission",
    "Profession",

    # Tables de jonction
    "RolePermission",
    "UserRole",
    "UserEntity",
    "UserAvailability",
    "UserTenantAssignment",

    # Enums
    "AssignmentType",

    # Fonctions utilitaires
    "get_user_tenant_access",
    "check_user_tenant_access",

    # Données initiales (seed)
    "INITIAL_ROLES",
    "INITIAL_PERMISSIONS",
    "INITIAL_ROLE_PERMISSIONS",
    "INITIAL_PROFESSIONS",
]