"""
Routes d'authentification.

Ce module expose les endpoints pour :
- Authentification Pro Santé Connect (PSC)
- Authentification locale (email/mot de passe)
- Refresh de tokens
- Informations utilisateur courant
- Déconnexion

Flux PSC:
    1. GET /auth/psc/login → Redirige vers PSC
    2. GET /auth/psc/callback → Callback PSC, retourne les tokens

Flux local:
    1. POST /auth/login → Email/mot de passe, retourne les tokens
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.v1.auth.schemas import (
    LoginRequest,
    LoginResponse,
    TokenResponse,
    RefreshTokenRequest,
    PSCAuthorizationResponse,
    AuthenticatedUser,
    AuthStatusResponse,
    AuthErrorResponse,
    AuthMethod,
)
from app.api.v1.auth.services import (
    get_auth_service,
    InvalidCredentialsError,
    InactiveUserError,
    PSCSessionError,
)
from app.core.auth.psc import PSCTokenError, PSCUserInfoError
from app.core.auth.psc import get_psc_client
from app.core.auth.user_auth import get_current_user
from app.core.config import settings
from app.core.security.jwt import verify_token
from app.database.session_rls import get_db
from app.models.user.user import User

router = APIRouter(
    prefix="/auth",
    tags=["Authentification"],
)


# =============================================================================
# PRO SANTÉ CONNECT
# =============================================================================

@router.get(
    "/psc/login",
    summary="Initier l'authentification PSC",
    description="""
    Démarre le flux d'authentification Pro Santé Connect.
    
    Cette route redirige l'utilisateur vers la page de connexion PSC
    où il pourra s'authentifier avec son e-CPS ou sa carte CPS.
    
    Après authentification, PSC redirigera vers /auth/psc/callback.
    
    **Environnement actuel**: Configuré via PSC_ENVIRONMENT dans .env
    - `bas`: Bac à Sable (développement, identités fictives)
    - `prod`: Production (vrais professionnels de santé)
    """,
    responses={
        302: {"description": "Redirection vers PSC"},
        503: {"description": "PSC non configuré"},
    }
)
async def psc_login(
    redirect_after: Optional[str] = Query(
        None,
        description="URL où rediriger après authentification réussie"
    ),
    db: Session = Depends(get_db),
):
    """
    Initie l'authentification Pro Santé Connect.

    Redirige l'utilisateur vers la page de connexion PSC.
    """
    psc_client = get_psc_client()

    # Vérifier que PSC est configuré
    if not psc_client.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pro Santé Connect n'est pas configuré sur ce serveur. "
                   "Vérifiez PSC_CLIENT_ID et PSC_CLIENT_SECRET dans .env"
        )

    # Créer la session PSC
    auth_service = get_auth_service(db)
    authorization_url, state = auth_service.create_psc_session(redirect_after)

    # Rediriger vers PSC
    return RedirectResponse(url=authorization_url, status_code=302)


@router.get(
    "/psc/login-url",
    response_model=PSCAuthorizationResponse,
    summary="Obtenir l'URL d'authentification PSC (sans redirection)",
    description="""
    Retourne l'URL d'authentification PSC sans effectuer de redirection.
    
    Utile pour les applications SPA qui gèrent elles-mêmes la redirection,
    ou pour afficher un bouton "Se connecter avec Pro Santé Connect".
    """,
    responses={
        503: {"description": "PSC non configuré"},
    }
)
async def psc_login_url(
    redirect_after: Optional[str] = Query(
        None,
        description="URL où rediriger après authentification réussie"
    ),
    db: Session = Depends(get_db),
) -> PSCAuthorizationResponse:
    """
    Retourne l'URL d'authentification PSC.

    Pour les SPA qui gèrent la redirection côté client.
    """
    psc_client = get_psc_client()

    if not psc_client.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pro Santé Connect n'est pas configuré sur ce serveur"
        )

    auth_service = get_auth_service(db)
    authorization_url, state = auth_service.create_psc_session(redirect_after)

    return PSCAuthorizationResponse(
        authorization_url=authorization_url,
        state=state,
    )


@router.get(
    "/psc/callback",
    response_model=LoginResponse,
    summary="Callback PSC",
    description="""
    Endpoint appelé par PSC après l'authentification de l'utilisateur.
    
    Reçoit le code d'autorisation, l'échange contre des tokens,
    récupère les informations utilisateur et crée/met à jour le compte.
    
    Retourne les tokens JWT CareLink pour les requêtes suivantes.
    
    **Processus:**
    1. Valide le state (protection CSRF)
    2. Échange le code contre des tokens PSC
    3. Récupère les infos utilisateur (RPPS, nom, profession...)
    4. Crée ou met à jour l'utilisateur en base
    5. Génère un JWT CareLink
    """,
    responses={
        400: {"model": AuthErrorResponse, "description": "Erreur de callback"},
        401: {"model": AuthErrorResponse, "description": "Session invalide"},
        403: {"model": AuthErrorResponse, "description": "Compte inactif"},
    }
)
async def psc_callback(
    code: str = Query(..., description="Code d'autorisation PSC"),
    state: str = Query(..., description="State pour validation CSRF"),
    error: Optional[str] = Query(None, description="Code d'erreur PSC"),
    error_description: Optional[str] = Query(None, description="Description erreur"),
    db: Session = Depends(get_db),
) -> LoginResponse:
    """
    Callback Pro Santé Connect.

    Termine le flux d'authentification et retourne les tokens CareLink.
    """
    # Gérer les erreurs retournées par PSC
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur PSC: {error} - {error_description or 'Pas de description'}"
        )

    auth_service = get_auth_service(db)

    try:
        # Terminer l'authentification PSC
        user, psc_info = await auth_service.authenticate_with_psc(
            code=code,
            state=state
        )

        # Construire et retourner la réponse
        return auth_service.build_login_response(user, auth_method=AuthMethod.PSC)

    except PSCSessionError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except InactiveUserError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except PSCTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur d'échange de tokens: {str(e)}"
        )
    except PSCUserInfoError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur de récupération des informations: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Données PSC invalides: {str(e)}"
        )


# =============================================================================
# AUTHENTIFICATION LOCALE (EMAIL/MOT DE PASSE)
# =============================================================================

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Connexion email/mot de passe",
    description="""
    Authentifie un utilisateur avec son email et mot de passe.
    
    Cette méthode est réservée aux utilisateurs non professionnels de santé
    (administrateurs, coordinateurs sans RPPS, etc.).
    
    Les professionnels de santé doivent utiliser Pro Santé Connect
    via `/auth/psc/login`.
    """,
    responses={
        401: {"model": AuthErrorResponse, "description": "Identifiants invalides"},
        403: {"model": AuthErrorResponse, "description": "Compte inactif"},
    }
)
async def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """
    Authentifie un utilisateur avec email/mot de passe.
    """
    auth_service = get_auth_service(db)

    try:
        user = auth_service.authenticate_local(
            email=credentials.email,
            password=credentials.password
        )

        return auth_service.build_login_response(user, auth_method=AuthMethod.PASSWORD)

    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InactiveUserError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


# =============================================================================
# REFRESH TOKEN
# =============================================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renouveler les tokens",
    description="""
    Renouvelle l'access token à partir d'un refresh token valide.
    
    Utilisez cette route lorsque l'access token expire pour en obtenir
    un nouveau sans redemander les identifiants à l'utilisateur.
    
    **Durées de validité:**
    - Access token: {access_minutes} minutes
    - Refresh token: {refresh_days} jours
    """.format(
        access_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    ),
    responses={
        401: {"model": AuthErrorResponse, "description": "Refresh token invalide"},
        403: {"model": AuthErrorResponse, "description": "Compte inactif"},
    }
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Renouvelle les tokens JWT.
    """
    try:
        # Vérifier le refresh token
        payload = verify_token(request.refresh_token, token_type="refresh")
        user_id = int(payload.get("sub"))

        # Récupérer l'utilisateur
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur non trouvé"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ce compte a été désactivé"
            )

        # Générer de nouveaux tokens
        auth_service = get_auth_service(db)
        return auth_service.create_tokens_for_user(user)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Refresh token invalide: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# =============================================================================
# UTILISATEUR COURANT
# =============================================================================

@router.get(
    "/me",
    response_model=AuthenticatedUser,
    summary="Obtenir l'utilisateur courant",
    description="Retourne les informations de l'utilisateur authentifié.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    """
    Retourne les informations de l'utilisateur courant.
    """
    auth_service = get_auth_service(db)
    return auth_service.build_authenticated_user(current_user)


@router.get(
    "/status",
    response_model=AuthStatusResponse,
    summary="Statut d'authentification et configuration",
    description="""
    Vérifie la configuration de l'authentification.
    
    Cette route ne nécessite pas d'authentification.
    Utile pour savoir si PSC est configuré avant d'afficher le bouton.
    """,
)
async def auth_status() -> AuthStatusResponse:
    """
    Retourne le statut de configuration de l'authentification.
    """
    psc_client = get_psc_client()

    return AuthStatusResponse(
        authenticated=False,  # Route publique, pas d'info utilisateur
        user=None,
        psc_configured=psc_client.is_configured,
        psc_environment=settings.PSC_ENVIRONMENT,
    )


# =============================================================================
# DÉCONNEXION
# =============================================================================

@router.post(
    "/logout",
    summary="Déconnexion",
    description="""
    Déconnecte l'utilisateur courant.
    
    **Note**: Les JWT étant stateless, cette route ne fait que confirmer
    la déconnexion. Le client doit supprimer les tokens de son côté.
    
    Pour une vraie invalidation de tokens côté serveur, il faudrait
    implémenter une blacklist (Redis).
    """,
    status_code=status.HTTP_200_OK,
)
async def logout(
    current_user: User = Depends(get_current_user),
):
    """
    Déconnecte l'utilisateur.
    """
    # TODO: Implémenter une blacklist de tokens si nécessaire
    return {
        "message": "Déconnexion réussie",
        "detail": "Veuillez supprimer les tokens côté client",
        "user_id": current_user.id,
    }