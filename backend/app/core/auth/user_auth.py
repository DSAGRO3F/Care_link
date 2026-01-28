"""
Dépendances d'authentification Users avec support RLS multi-tenant.

Ce module fournit les dépendances FastAPI pour l'authentification
des utilisateurs (professionnels de santé) et la configuration
automatique du contexte tenant.

Flow:
    1. get_current_user() extrait le JWT et charge l'utilisateur
    2. Configure automatiquement le contexte tenant (ContextVar)
    3. get_db() lit ce contexte et configure PostgreSQL
    4. RLS s'applique à toutes les requêtes

Usage:
    @router.get("/patients")
    async def list_patients(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        # RLS filtre automatiquement par tenant de current_user
        return db.query(Patient).all()

Note:
    Pour l'authentification SuperAdmin (équipe CareLink), utiliser :
    from app.api.v1.platform.super_admin_security import (
        get_current_super_admin,
        require_super_admin_permission,
        require_role,
    )
"""

from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security.jwt import verify_token
from app.core.session.tenant_context import set_tenant_context
from app.database.session_rls import get_db_no_rls
from app.models.user.user import User

# Security scheme pour le token Bearer
bearer_scheme = HTTPBearer(auto_error=False)


# =============================================================================
# AUTHENTIFICATION UTILISATEUR (PROFESSIONNELS DE SANTÉ)
# =============================================================================

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db_no_rls),  # Pas de RLS pour charger l'utilisateur
) -> User:
    """
    Dépendance pour obtenir l'utilisateur courant depuis le JWT.

    Configure automatiquement le contexte tenant pour RLS.

    Raises:
        HTTPException 401: Token manquant ou invalide
        HTTPException 403: Utilisateur inactif

    Returns:
        User: L'utilisateur authentifié
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification requis",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Décoder et vérifier le JWT
        payload = verify_token(credentials.credentials, token_type="access")

        user_id_raw = payload.get("sub")
        tenant_id = payload.get("tenant_id")

        # Convertir user_id en int (le JWT stocke des strings)
        try:
            user_id = int(user_id_raw) if user_id_raw else None
        except (ValueError, TypeError):
            user_id = None

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide: user_id manquant",
            )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalide: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Charger l'utilisateur depuis la DB
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte utilisateur désactivé",
        )

    # Vérifier la cohérence du tenant_id
    if tenant_id and user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incohérence de tenant",
        )

    # Configurer le contexte tenant pour RLS
    set_tenant_context(
        tenant_id=user.tenant_id,
        user_id=user.id,
        super_admin=False
    )

    # Stocker aussi dans request.state pour le middleware
    request.state.tenant_id = user.tenant_id
    request.state.user_id = user.id
    request.state.is_super_admin = False

    return user


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db_no_rls),
) -> Optional[User]:
    """
    Comme get_current_user mais retourne None si pas authentifié.

    Utile pour les endpoints publics avec fonctionnalités étendues
    pour les utilisateurs authentifiés.
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None


# =============================================================================
# VÉRIFICATION DES PERMISSIONS UTILISATEUR
# =============================================================================

def require_permission(permission: str):
    """
    Factory de dépendance pour vérifier une permission utilisateur.

    Usage:
        @router.post("/patients")
        async def create_patient(
            current_user: User = Depends(require_permission("patient.create"))
        ):
            ...
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission requise: {permission}",
            )
        return current_user

    return permission_checker


def require_role(role_name: str):
    """
    Factory de dépendance pour vérifier un rôle utilisateur.

    Usage:
        @router.get("/admin/stats")
        async def get_stats(
            current_user: User = Depends(require_role("ADMIN"))
        ):
            ...
    """
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not current_user.has_role(role_name) and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle requis: {role_name}",
            )
        return current_user

    return role_checker


def require_tenant_access(tenant_id_param: str = "tenant_id"):
    """
    Factory de dépendance pour vérifier l'accès à un tenant spécifique.

    Vérifie que l'utilisateur a accès au tenant passé en paramètre
    (via son tenant principal ou ses assignments).

    Usage:
        @router.get("/tenants/{tenant_id}/patients")
        async def get_tenant_patients(
            tenant_id: int,
            current_user: User = Depends(require_tenant_access("tenant_id"))
        ):
            ...
    """
    async def tenant_access_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        # Récupérer le tenant_id depuis les path params
        target_tenant_id = request.path_params.get(tenant_id_param)

        if target_tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Paramètre {tenant_id_param} requis",
            )

        target_tenant_id = int(target_tenant_id)

        # Vérifier l'accès
        if not current_user.has_access_to_tenant(target_tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé à ce tenant",
            )

        # Mettre à jour le contexte avec le tenant cible
        set_tenant_context(
            tenant_id=target_tenant_id,
            user_id=current_user.id,
            super_admin=False
        )

        return current_user

    return tenant_access_checker