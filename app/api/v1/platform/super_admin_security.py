"""
Dépendances FastAPI pour le module Platform.

Gestion de l'authentification et des permissions SuperAdmin.
Compatible avec le modèle SuperAdmin utilisant SuperAdminRole (enum).
"""
from typing import Optional, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database.session_rls import get_db_no_rls as get_db
from app.core.jwt import verify_token
from app.models.platform.super_admin import SuperAdmin, SuperAdminRole


# =============================================================================
# SECURITY SCHEME
# =============================================================================

super_admin_bearer = HTTPBearer(
    scheme_name="SuperAdminAuth",
    description="JWT Bearer token pour l'authentification SuperAdmin",
    auto_error=False,
)


# =============================================================================
# DEPENDENCIES
# =============================================================================

async def get_current_super_admin(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(super_admin_bearer),
        db: Session = Depends(get_db),
) -> SuperAdmin:
    """
    Récupère le SuperAdmin actuellement authentifié.

    Le token JWT doit contenir :
    - sub: ID du SuperAdmin
    - type: "super_admin"

    Raises:
        HTTPException 401: Si pas de token ou token invalide
        HTTPException 403: Si SuperAdmin inactif ou verrouillé
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification SuperAdmin requise",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = verify_token(token, token_type="super_admin")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalide: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Vérifier que c'est un token SuperAdmin
    token_type = payload.get("type")
    if token_type != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce endpoint nécessite une authentification SuperAdmin",
        )

    # Récupérer le SuperAdmin
    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide: ID manquant",
        )

    admin = db.get(SuperAdmin, int(admin_id))
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SuperAdmin non trouvé",
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte SuperAdmin désactivé",
        )

    if admin.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte SuperAdmin temporairement verrouillé",
        )

    return admin


def require_super_admin_permission(permission: str) -> Callable:
    """
    Factory pour créer une dépendance qui vérifie une permission spécifique.

    Les permissions sont mappées vers les rôles SuperAdminRole :
    - PLATFORM_OWNER : Toutes les permissions
    - PLATFORM_ADMIN : Gestion tenants, support, audit
    - PLATFORM_SUPPORT : Lecture seule
    - PLATFORM_SALES : Démos, onboarding

    Usage:
        @router.post("/tenants")
        def create_tenant(
            admin: SuperAdmin = Depends(require_super_admin_permission("tenants.create"))
        ):
            ...

    Args:
        permission: Permission requise (ex: "tenants.create", "audit.view")

    Returns:
        Dépendance FastAPI qui vérifie la permission
    """
    async def check_permission(
            admin: SuperAdmin = Depends(get_current_super_admin),
    ) -> SuperAdmin:
        # PLATFORM_OWNER a tous les droits
        if admin.role == SuperAdminRole.PLATFORM_OWNER:
            return admin

        # Mapper la permission vers les capacités du rôle
        permission_check = _check_permission_for_role(admin, permission)

        if not permission_check:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' requise. Votre rôle: {admin.role.value}",
            )

        return admin

    return check_permission


def _check_permission_for_role(admin: SuperAdmin, permission: str) -> bool:
    """
    Vérifie si le rôle du SuperAdmin permet l'action demandée.

    Mapping des permissions vers les capacités des rôles.
    """
    # Permissions de gestion des tenants
    if permission in (
        SuperAdminPermissions.TENANTS_VIEW,
        SuperAdminPermissions.TENANTS_CREATE,
        SuperAdminPermissions.TENANTS_UPDATE,
        SuperAdminPermissions.TENANTS_DELETE,
        SuperAdminPermissions.TENANTS_SUSPEND,
    ):
        return admin.can_manage_tenants

    # Permissions de gestion des super admins
    if permission in (
        SuperAdminPermissions.SUPERADMINS_VIEW,
        SuperAdminPermissions.SUPERADMINS_CREATE,
        SuperAdminPermissions.SUPERADMINS_UPDATE,
        SuperAdminPermissions.SUPERADMINS_DELETE,
    ):
        return admin.can_manage_super_admins

    # Permissions d'audit
    if permission == SuperAdminPermissions.AUDIT_VIEW:
        return admin.can_view_audit_logs

    # Permissions d'affectations cross-tenant
    if permission in (
        SuperAdminPermissions.ASSIGNMENTS_VIEW,
        SuperAdminPermissions.ASSIGNMENTS_CREATE,
        SuperAdminPermissions.ASSIGNMENTS_UPDATE,
        SuperAdminPermissions.ASSIGNMENTS_DELETE,
    ):
        # Même niveau que gestion tenants
        return admin.can_manage_tenants

    # Permission inconnue -> refuser
    return False


async def get_optional_super_admin(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(super_admin_bearer),
        db: Session = Depends(get_db),
) -> Optional[SuperAdmin]:
    """
    Récupère le SuperAdmin si authentifié, sinon retourne None.

    Utile pour les endpoints qui peuvent être accédés par les deux types d'utilisateurs.
    """
    if not credentials:
        return None

    try:
        payload = verify_token(credentials.credentials)
    except Exception:
        return None

    if payload.get("type") != "super_admin":
        return None

    admin_id = payload.get("sub")
    if not admin_id:
        return None

    admin = db.get(SuperAdmin, int(admin_id))
    if not admin or not admin.is_active or admin.is_locked:
        return None

    return admin


def require_role(minimum_role: SuperAdminRole) -> Callable:
    """
    Factory pour créer une dépendance qui vérifie un rôle minimum.

    Usage:
        @router.delete("/super-admins/{id}")
        def delete_super_admin(
            admin: SuperAdmin = Depends(require_role(SuperAdminRole.PLATFORM_OWNER))
        ):
            ...

    Args:
        minimum_role: Rôle minimum requis

    Returns:
        Dépendance FastAPI qui vérifie le rôle
    """
    async def check_role(
            admin: SuperAdmin = Depends(get_current_super_admin),
    ) -> SuperAdmin:
        if not admin.has_role(minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle minimum requis: {minimum_role.value}. Votre rôle: {admin.role.value}",
            )
        return admin

    return check_role


# =============================================================================
# PERMISSION CONSTANTS
# =============================================================================

class SuperAdminPermissions:
    """
    Constantes pour les permissions SuperAdmin.

    Ces constantes sont utilisées pour identifier les actions.
    La vérification réelle se fait via le rôle (SuperAdminRole) du super-admin.
    """

    # Gestion des tenants
    TENANTS_VIEW = "tenants.view"
    TENANTS_CREATE = "tenants.create"
    TENANTS_UPDATE = "tenants.update"
    TENANTS_DELETE = "tenants.delete"
    TENANTS_SUSPEND = "tenants.suspend"

    # Gestion des SuperAdmins
    SUPERADMINS_VIEW = "superadmins.view"
    SUPERADMINS_CREATE = "superadmins.create"
    SUPERADMINS_UPDATE = "superadmins.update"
    SUPERADMINS_DELETE = "superadmins.delete"

    # Audit
    AUDIT_VIEW = "audit.view"

    # Affectations cross-tenant
    ASSIGNMENTS_VIEW = "assignments.view"
    ASSIGNMENTS_CREATE = "assignments.create"
    ASSIGNMENTS_UPDATE = "assignments.update"
    ASSIGNMENTS_DELETE = "assignments.delete"

    @classmethod
    def all_permissions(cls) -> list[str]:
        """Retourne la liste de toutes les permissions."""
        return [
            cls.TENANTS_VIEW, cls.TENANTS_CREATE, cls.TENANTS_UPDATE,
            cls.TENANTS_DELETE, cls.TENANTS_SUSPEND,
            cls.SUPERADMINS_VIEW, cls.SUPERADMINS_CREATE,
            cls.SUPERADMINS_UPDATE, cls.SUPERADMINS_DELETE,
            cls.AUDIT_VIEW,
            cls.ASSIGNMENTS_VIEW, cls.ASSIGNMENTS_CREATE,
            cls.ASSIGNMENTS_UPDATE, cls.ASSIGNMENTS_DELETE,
        ]


# =============================================================================
# ROLE-PERMISSION MAPPING (Documentation)
# =============================================================================
"""
Mapping des rôles vers les permissions :

PLATFORM_OWNER (niveau 4):
    - Toutes les permissions
    - Peut gérer les autres super-admins

PLATFORM_ADMIN (niveau 3):
    - tenants.* (view, create, update, delete, suspend)
    - audit.view
    - assignments.* (view, create, update, delete)
    - superadmins.view (lecture seule)

PLATFORM_SUPPORT (niveau 2):
    - tenants.view (lecture seule)
    - audit.view
    - assignments.view (lecture seule)

PLATFORM_SALES (niveau 1):
    - Accès limité aux démos
    - Pas d'accès aux données sensibles
"""