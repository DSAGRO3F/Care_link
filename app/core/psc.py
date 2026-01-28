"""
Client Pro Santé Connect (PSC).

Ce module gère l'intégration avec l'API Pro Santé Connect de l'ANS
pour l'authentification des professionnels de santé via OpenID Connect.

Améliorations par rapport à la version initiale (app/auth/psc_client.py) :
- Support PKCE (Proof Key for Code Exchange) pour sécurité renforcée
- Nonce pour protection contre les attaques de replay
- Switch automatique BAS/PROD via PSC_ENVIRONMENT
- Parsing des données utilisateur PSC

Flux OAuth2 Authorization Code + PKCE:
1. get_authorization_url() → URL de redirection vers PSC
2. L'utilisateur s'authentifie sur PSC (e-CPS ou carte CPS)
3. PSC redirige vers notre callback avec un code
4. exchange_code_for_tokens() → Échange le code contre des tokens
5. get_user_info() → Récupère les informations du professionnel

Usage:
    from app.core.psc import psc_client

    # Étape 1: Générer l'URL d'autorisation
    auth_url, state, nonce, code_verifier = psc_client.get_authorization_url()

    # Étape 2: Après callback, échanger le code
    tokens = await psc_client.exchange_code_for_tokens(code, code_verifier)

    # Étape 3: Récupérer les infos utilisateur
    user_info = await psc_client.get_user_info(tokens["access_token"])
"""

import secrets
import hashlib
import base64
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlencode
import httpx

from app.core.config import settings


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Exceptions
    "ProSanteConnectError",
    "PSCAuthenticationError",
    "PSCTokenError",
    "PSCUserInfoError",
    # Client
    "ProSanteConnectClient",
    "get_psc_client",
    "psc_client",
]


# =============================================================================
# EXCEPTIONS
# =============================================================================

class ProSanteConnectError(Exception):
    """Exception de base pour les erreurs PSC."""
    pass


class PSCAuthenticationError(ProSanteConnectError):
    """Erreur lors de l'authentification PSC."""
    pass


class PSCTokenError(ProSanteConnectError):
    """Erreur lors de l'échange de tokens."""
    pass


class PSCUserInfoError(ProSanteConnectError):
    """Erreur lors de la récupération des infos utilisateur."""
    pass


# =============================================================================
# CLIENT PRO SANTÉ CONNECT
# =============================================================================

class ProSanteConnectClient:
    """
    Client pour l'API Pro Santé Connect.

    Gère le flux OAuth2/OpenID Connect pour authentifier les professionnels
    de santé via leur e-CPS ou carte CPS.

    Attributes:
        client_id: Identifiant client PSC (fourni par Datapass)
        client_secret: Secret client PSC (fourni par Datapass)
        redirect_uri: URL de callback CareLink

    Les URLs (authorization, token, userinfo) sont dynamiques selon
    PSC_ENVIRONMENT (bas ou prod).

    Example:
        client = ProSanteConnectClient()
        auth_url, state, nonce, verifier = client.get_authorization_url()
        # ... redirection et callback ...
        tokens = await client.exchange_code_for_tokens(code, verifier)
        user_info = await client.get_user_info(tokens["access_token"])
    """

    # Scopes OpenID Connect demandés
    # - openid: obligatoire pour OIDC
    # - scope_all: accès à toutes les données sectorielles (RPPS, profession, etc.)
    DEFAULT_SCOPES = ["openid", "scope_all"]

    def __init__(self):
        """Initialise le client avec la configuration."""
        self.client_id = settings.PSC_CLIENT_ID
        self.client_secret = settings.PSC_CLIENT_SECRET
        self.redirect_uri = settings.PSC_REDIRECT_URI

    # =========================================================================
    # PROPERTIES - URLs dynamiques selon PSC_ENVIRONMENT
    # =========================================================================

    @property
    def authorization_url(self) -> str:
        """URL d'autorisation PSC (dynamique selon PSC_ENVIRONMENT)."""
        return settings.psc_authorization_url

    @property
    def token_url(self) -> str:
        """URL d'échange de tokens PSC (dynamique selon PSC_ENVIRONMENT)."""
        return settings.psc_token_url

    @property
    def userinfo_url(self) -> str:
        """URL userinfo PSC (dynamique selon PSC_ENVIRONMENT)."""
        return settings.psc_userinfo_url

    @property
    def jwks_url(self) -> str:
        """URL JWKS PSC (dynamique selon PSC_ENVIRONMENT)."""
        return settings.psc_jwks_url

    @property
    def is_configured(self) -> bool:
        """Vérifie si PSC est correctement configuré."""
        return settings.psc_configured

    # =========================================================================
    # GÉNÉRATION DES VALEURS DE SÉCURITÉ
    # =========================================================================

    def _generate_state(self) -> str:
        """
        Génère un state aléatoire pour la protection CSRF.

        Le state est renvoyé par PSC dans le callback et doit être vérifié
        pour s'assurer que la réponse correspond bien à notre requête.

        Returns:
            State aléatoire de 32 caractères hexadécimaux
        """
        return secrets.token_hex(16)

    def _generate_nonce(self) -> str:
        """
        Génère un nonce pour la protection contre les attaques de replay.

        Le nonce est inclus dans l'id_token et doit être vérifié.

        Returns:
            Nonce aléatoire de 32 caractères hexadécimaux
        """
        return secrets.token_hex(16)

    def _generate_code_verifier(self) -> str:
        """
        Génère un code_verifier pour PKCE (Proof Key for Code Exchange).

        PKCE ajoute une couche de sécurité supplémentaire en liant
        la demande d'autorisation à l'échange de tokens.

        Returns:
            Code verifier aléatoire (43-128 caractères)
        """
        return secrets.token_urlsafe(32)

    def _generate_code_challenge(self, code_verifier: str) -> str:
        """
        Génère le code_challenge à partir du code_verifier (méthode S256).

        Args:
            code_verifier: Le code verifier généré

        Returns:
            Code challenge (hash SHA256 encodé en base64url)
        """
        digest = hashlib.sha256(code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()

    # =========================================================================
    # FLUX OAUTH2 / OPENID CONNECT
    # =========================================================================

    def get_authorization_url(
        self,
        scopes: Optional[list[str]] = None,
        extra_params: Optional[Dict[str, str]] = None
    ) -> Tuple[str, str, str, str]:
        """
        Génère l'URL d'autorisation PSC pour rediriger l'utilisateur.

        Args:
            scopes: Scopes OIDC à demander (défaut: openid, scope_all)
            extra_params: Paramètres supplémentaires à ajouter à l'URL

        Returns:
            Tuple (url, state, nonce, code_verifier):
            - url: URL complète vers PSC
            - state: State à stocker en session pour vérification au callback
            - nonce: Nonce à stocker pour vérification de l'id_token
            - code_verifier: Code verifier PKCE à stocker pour l'échange

        Raises:
            PSCAuthenticationError: Si PSC n'est pas configuré

        Example:
            url, state, nonce, verifier = client.get_authorization_url()
            # Stocker state, nonce, verifier en session (Redis)
            # Rediriger l'utilisateur vers url
        """
        if not self.is_configured:
            raise PSCAuthenticationError(
                "Pro Santé Connect n'est pas configuré. "
                "Vérifiez PSC_CLIENT_ID et PSC_CLIENT_SECRET dans .env"
            )

        # Générer les valeurs de sécurité
        state = self._generate_state()
        nonce = self._generate_nonce()
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)

        # Construire les paramètres
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes or self.DEFAULT_SCOPES),
            "state": state,
            "nonce": nonce,
            # PKCE (recommandé par l'ANS)
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            # Niveau d'authentification requis (eIDAS)
            "acr_values": "eidas1",
            # Demande un prompt de connexion à chaque fois
            "prompt": "login",
            # Indique le type d'affichage souhaité
            "display": "page",
        }

        # Ajouter les paramètres supplémentaires
        if extra_params:
            params.update(extra_params)

        # Construire l'URL
        url = f"{self.authorization_url}?{urlencode(params)}"

        return url, state, nonce, code_verifier

    async def exchange_code_for_tokens(
        self,
        code: str,
        code_verifier: str
    ) -> Dict[str, Any]:
        """
        Échange le code d'autorisation contre des tokens.

        Cette méthode est appelée après le callback PSC.
        Elle envoie le code reçu + le code_verifier PKCE pour obtenir:
        - access_token: pour appeler l'API userinfo
        - id_token: JWT contenant les claims d'identité
        - refresh_token: pour renouveler l'access_token (si disponible)

        Args:
            code: Code d'autorisation reçu dans le callback
            code_verifier: Code verifier PKCE stocké en session

        Returns:
            Dict contenant les tokens:
            {
                "access_token": "...",
                "token_type": "Bearer",
                "expires_in": 300,
                "id_token": "...",
                "refresh_token": "..." (optionnel)
            }

        Raises:
            PSCTokenError: Si l'échange échoue
        """
        if not self.is_configured:
            raise PSCTokenError("Pro Santé Connect n'est pas configuré")

        # Préparer la requête
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code_verifier": code_verifier,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.token_url,
                    data=data,
                    headers=headers,
                )

                if response.status_code != 200:
                    error_detail = response.text
                    try:
                        error_json = response.json()
                        error_detail = error_json.get(
                            "error_description",
                            error_json.get("error", response.text)
                        )
                    except Exception:
                        pass

                    raise PSCTokenError(
                        f"Erreur lors de l'échange du code: {response.status_code} - {error_detail}"
                    )

                return response.json()

        except httpx.RequestError as e:
            raise PSCTokenError(f"Erreur de connexion à PSC: {str(e)}")

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Récupère les informations du professionnel de santé.

        Appelle l'endpoint userinfo de PSC avec l'access_token.
        Retourne les données d'identité et sectorielles du professionnel.

        Args:
            access_token: Token d'accès obtenu via exchange_code_for_tokens

        Returns:
            Dict contenant les informations utilisateur:
            {
                "sub": "f:xxx:yyy",           # Identifiant unique PSC
                "SubjectNameID": "12345678901",  # RPPS
                "family_name": "DUPONT",
                "given_name": "Jean",
                "SubjectRefPro": {...},       # Données d'exercice professionnel
                "SubjectRole": ["Médecin"],   # Profession
                ...
            }

        Raises:
            PSCUserInfoError: Si la récupération échoue
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.userinfo_url,
                    headers=headers,
                )

                if response.status_code != 200:
                    error_detail = response.text
                    try:
                        error_json = response.json()
                        error_detail = error_json.get(
                            "error_description",
                            error_json.get("error", response.text)
                        )
                    except Exception:
                        pass

                    raise PSCUserInfoError(
                        f"Erreur userinfo: {response.status_code} - {error_detail}"
                    )

                return response.json()

        except httpx.RequestError as e:
            raise PSCUserInfoError(f"Erreur de connexion à PSC: {str(e)}")

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Renouvelle un access token expiré avec le refresh token.

        Args:
            refresh_token: Refresh token obtenu lors de l'authentification initiale

        Returns:
            Dict contenant le nouveau access_token (même format que exchange_code)

        Raises:
            PSCTokenError: Si le refresh échoue
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.token_url,
                    data=data,
                    headers=headers,
                )

                if response.status_code != 200:
                    raise PSCTokenError(f"Erreur refresh: {response.status_code}")

                return response.json()

        except httpx.RequestError as e:
            raise PSCTokenError(f"Erreur de connexion: {str(e)}")

    async def revoke_token(
        self,
        token: str,
        token_type_hint: str = "access_token"
    ) -> bool:
        """
        Révoque un token PSC (déconnexion).

        Args:
            token: Token à révoquer (access ou refresh)
            token_type_hint: Type de token ("access_token" ou "refresh_token")

        Returns:
            True si la révocation a réussi
        """
        # L'endpoint de révocation PSC
        revoke_url = self.token_url.replace("/token", "/revoke")

        data = {
            "token": token,
            "token_type_hint": token_type_hint,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    revoke_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                return response.status_code == 200
        except httpx.RequestError:
            return False

    # =========================================================================
    # PARSING DES DONNÉES UTILISATEUR
    # =========================================================================

    def parse_user_info(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse les informations utilisateur PSC en format simplifié.

        Extrait les champs utiles de la réponse userinfo PSC
        et les formate pour une utilisation dans CareLink.

        Args:
            user_info: Réponse brute de l'endpoint userinfo

        Returns:
            Dict avec les champs normalisés:
            {
                "rpps": "12345678901",
                "family_name": "DUPONT",
                "given_name": "Jean",
                "email": "jean.dupont@example.com" (si disponible),
                "profession": "Médecin",
                "profession_code": "10",
                "speciality": "SM01",
                "exercise_modes": ["LIBERAL", "SALARIE"],
                "raw": {...}
            }
        """
        # Identifiant RPPS (ou ADELI)
        rpps = user_info.get("SubjectNameID")

        # Identité
        family_name = user_info.get("family_name", "")
        given_name = user_info.get("given_name", "")
        email = user_info.get("email")

        # Profession depuis SubjectRole
        subject_roles = user_info.get("SubjectRole", [])
        profession = None
        if isinstance(subject_roles, list) and subject_roles:
            profession = subject_roles[0]
        elif isinstance(subject_roles, str):
            profession = subject_roles

        # Données d'exercice professionnel
        subject_ref_pro = user_info.get("SubjectRefPro", {})
        exercices = subject_ref_pro.get("exercices", [])

        # Extraire les détails du premier exercice
        profession_code = None
        speciality = None
        exercise_modes = []

        if exercices:
            first_exercice = exercices[0]
            profession_code = first_exercice.get("codeProfession")

            # Spécialité
            savoir_faire = first_exercice.get("savoirFaire", [])
            if savoir_faire:
                speciality = savoir_faire[0].get("code")

            # Modes d'exercice
            for exercice in exercices:
                activites = exercice.get("activites", [])
                for activite in activites:
                    mode = activite.get("modeExercice")
                    if mode and mode not in exercise_modes:
                        exercise_modes.append(mode)

        return {
            "rpps": rpps,
            "family_name": family_name.upper() if family_name else "",
            "given_name": given_name.capitalize() if given_name else "",
            "email": email,
            "profession": profession or "Professionnel de santé",
            "profession_code": profession_code,
            "speciality": speciality,
            "exercise_modes": exercise_modes,
            "raw": user_info,
        }


# =============================================================================
# INSTANCE SINGLETON
# =============================================================================

# Instance singleton du client PSC
_psc_client: Optional[ProSanteConnectClient] = None


def get_psc_client() -> ProSanteConnectClient:
    """
    Retourne l'instance singleton du client PSC.

    Returns:
        Instance ProSanteConnectClient
    """
    global _psc_client
    if _psc_client is None:
        _psc_client = ProSanteConnectClient()
    return _psc_client


# Alias pour compatibilité
psc_client = get_psc_client()