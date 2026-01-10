"""
User models - Utilisateurs et RH.

Ce module contient les modèles liés aux utilisateurs :
- User : Utilisateurs/Professionnels
- Role : Rôles fonctionnels
- Profession : Professions réglementées
- UserRole : Association User ↔ Role
- UserEntity : Association User ↔ Entity
"""

from app.models.user.user import User
from app.models.user.role import Role, INITIAL_ROLES
from app.models.user.profession import Profession, INITIAL_PROFESSIONS
from app.models.user.user_associations import UserRole, UserEntity

__all__ = [
    "User",
    "Role",
    "INITIAL_ROLES",
    "Profession",
    "INITIAL_PROFESSIONS",
    "UserRole",
    "UserEntity",
]
