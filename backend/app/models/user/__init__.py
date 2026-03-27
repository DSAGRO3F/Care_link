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

from app.models.user.permission import INITIAL_PERMISSIONS, Permission
from app.models.user.profession import INITIAL_PROFESSIONS, Profession
from app.models.user.role import INITIAL_ROLES, Role
from app.models.user.role_permission import INITIAL_ROLE_PERMISSIONS, RolePermission
from app.models.user.user import User
from app.models.user.user_associations import UserEntity, UserRole
from app.models.user.user_availability import UserAvailability
from app.models.user.user_tenant_assignment import (
    AssignmentType,
    UserTenantAssignment,
    check_user_tenant_access,
    get_user_tenant_access,
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
