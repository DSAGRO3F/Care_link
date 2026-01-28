"""
Module d'authentification CareLink.

Ce module gère :
- Authentification Pro Santé Connect (PSC) pour les professionnels de santé
- Authentification locale (email/mot de passe) pour les autres utilisateurs
- Gestion des tokens JWT
- Gestion des accès patients

Endpoints disponibles:
- GET  /auth/psc/login      - Redirection vers PSC
- GET  /auth/psc/login-url  - URL PSC (pour SPA)
- GET  /auth/psc/callback   - Callback PSC
- POST /auth/login          - Login email/password
- POST /auth/refresh        - Refresh token
- GET  /auth/me             - Utilisateur courant
- GET  /auth/status         - Statut configuration
- POST /auth/logout         - Déconnexion

Usage dans router.py:
    from app.api.v1.auth import router as auth_router
    api_router.include_router(auth_router)
"""

from app.api.v1.auth.routes import router
from app.api.v1.auth.schemas import (
    LoginRequest,
    LoginResponse,
    TokenResponse,
    AuthenticatedUser,
    AuthStatusResponse,
    PSCAuthorizationResponse,
    AccessType,
    AuthMethod,
)
from app.api.v1.auth.services import (
    AuthService,
    get_auth_service,
    AuthenticationError,
    InvalidCredentialsError,
    InactiveUserError,
    PSCSessionError,
    PatientAccessError,
)

__all__ = [
    # Router
    "router",
    # Services
    "AuthService",
    "get_auth_service",
    # Exceptions
    "AuthenticationError",
    "InvalidCredentialsError",
    "InactiveUserError",
    "PSCSessionError",
    "PatientAccessError",
    # Schémas
    "LoginRequest",
    "LoginResponse",
    "TokenResponse",
    "AuthenticatedUser",
    "AuthStatusResponse",
    "PSCAuthorizationResponse",
    "AccessType",
    "AuthMethod",
]