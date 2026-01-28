"""
Middleware de contexte tenant pour RLS.

Ce module configure le contexte tenant PostgreSQL à chaque requête
pour que les politiques RLS fonctionnent correctement.

Usage:
    app.add_middleware(TenantContextMiddleware)
"""

from typing import Optional, Callable
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Variable de contexte pour stocker le tenant_id de la requête courante
current_tenant_id: ContextVar[Optional[int]] = ContextVar('current_tenant_id', default=None)
current_user_id: ContextVar[Optional[int]] = ContextVar('current_user_id', default=None)
is_super_admin: ContextVar[bool] = ContextVar('is_super_admin', default=False)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware qui extrait le tenant_id du JWT et le stocke dans le contexte.
    
    Le contexte est ensuite utilisé par get_db() pour configurer
    les variables de session PostgreSQL avant chaque requête.
    
    Flow:
        1. Request arrive
        2. Middleware extrait tenant_id du JWT (si présent)
        3. Stocke dans ContextVar
        4. get_db() lit le ContextVar et configure PostgreSQL
        5. RLS s'applique automatiquement
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process la requête et configure le contexte tenant."""
        
        # Reset le contexte pour chaque requête
        token_tenant = current_tenant_id.set(None)
        token_user = current_user_id.set(None)
        token_admin = is_super_admin.set(False)
        
        try:
            # Extraire les infos du state de la requête
            # (définies par les dépendances d'authentification)
            
            # Le tenant_id peut être dans request.state après auth
            if hasattr(request.state, 'tenant_id'):
                current_tenant_id.set(request.state.tenant_id)
            
            if hasattr(request.state, 'user_id'):
                current_user_id.set(request.state.user_id)
            
            if hasattr(request.state, 'is_super_admin'):
                is_super_admin.set(request.state.is_super_admin)
            
            # Continuer le traitement de la requête
            response = await call_next(request)
            return response
            
        finally:
            # Nettoyer le contexte
            current_tenant_id.reset(token_tenant)
            current_user_id.reset(token_user)
            is_super_admin.reset(token_admin)


def get_current_tenant_id() -> Optional[int]:
    """Récupère le tenant_id du contexte de la requête courante."""
    return current_tenant_id.get()


def get_current_user_id() -> Optional[int]:
    """Récupère le user_id du contexte de la requête courante."""
    return current_user_id.get()


def get_is_super_admin() -> bool:
    """Vérifie si la requête courante est d'un super-admin."""
    return is_super_admin.get()


def set_tenant_context(tenant_id: Optional[int], user_id: Optional[int] = None, super_admin: bool = False):
    """
    Définit manuellement le contexte tenant.
    
    Utile pour les tâches de fond, scripts, etc.
    
    Args:
        tenant_id: ID du tenant
        user_id: ID de l'utilisateur (optionnel)
        super_admin: Est-ce un super-admin ?
    """
    current_tenant_id.set(tenant_id)
    current_user_id.set(user_id)
    is_super_admin.set(super_admin)
