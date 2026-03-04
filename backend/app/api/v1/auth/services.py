"""
Service d'authentification - Logique métier.

Ce module orchestre le processus d'authentification complet :
- Authentification via Pro Santé Connect (PSC)
- Authentification locale (email/mot de passe)
- Gestion des sessions PSC (Redis)
- Synchronisation des utilisateurs en base
- Génération des tokens JWT internes
- Gestion des accès patients (hérité de app/auth/service.py)

Fusion de :
- app/auth/service.py (logique métier existante)
- Nouvelles fonctionnalités (PKCE, sessions Redis, switch BAS/PROD)

Changement v4.8 : Harmonisation encryption
- Pattern expunge+decrypt utilise decrypt_model() du BaseEncryptor
- Recherche PSC par RPPS via blind index (corrige le bug clair vs chiffré)
- Création User PSC avec encrypt_for_db() + noms de colonnes _encrypted
"""

from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api.v1.auth.schemas import (
    TokenResponse,
    AuthenticatedUser,
    LoginResponse,
    PSCSessionData,
    AuthMethod,
    AccessType,
)
from app.core.auth.psc import (
    get_psc_client,
)
from app.core.config import settings
from app.core.security.hashing import verify_password, hash_password
from app.core.security.jwt import create_access_token, create_refresh_token
from app.core.session.redis_client import get_redis
from app.models.user.profession import Profession
from app.models.user.role import Role
from app.models.user.user import User

from app.models.tenants.tenant import Tenant
from app.models.enums import TenantStatus
from app.services.encryption import user_encryptor, get_user_search_blind


# =============================================================================
# EXCEPTIONS
# =============================================================================

class AuthenticationError(Exception):
    """Erreur d'authentification générique."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Identifiants invalides."""
    pass


class InactiveUserError(AuthenticationError):
    """Compte utilisateur inactif."""
    pass


class PSCSessionError(AuthenticationError):
    """Erreur de session PSC (state invalide, session expirée, etc.)."""
    pass


class PatientAccessError(Exception):
    """Erreur d'accès patient."""
    pass


# =============================================================================
# SERVICE D'AUTHENTIFICATION
# =============================================================================

class AuthService:
    """
    Service d'authentification.

    Gère les deux modes d'authentification :
    - PSC pour les professionnels de santé
    - Email/mot de passe pour les autres utilisateurs

    Gère également les accès aux données patients.
    """

    # Durée de validité d'une session PSC (entre redirection et callback)
    PSC_SESSION_TTL_SECONDS = 600  # 10 minutes

    # Préfixe pour les clés Redis des sessions PSC
    PSC_SESSION_PREFIX = "psc_session:"

    def __init__(self, db: Session):
        """
        Initialise le service.

        Args:
            db: Session SQLAlchemy
        """
        self.db = db
        self._redis = None

    @property
    def redis(self):
        """Lazy loading du client Redis."""
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    # =========================================================================
    # AUTHENTIFICATION LOCALE (EMAIL/MOT DE PASSE)
    # =========================================================================

    # ============================================================================
    # PATCH pour app/api/v1/auth/services.py
    # ============================================================================
    #
    # Problème : Le RLS bloque la recherche d'utilisateur lors du login
    # car tenant_id n'est pas encore connu.
    #
    # Solution : Bypasser temporairement le RLS pour authenticate_local
    # ============================================================================


    def authenticate_local(self, email: str, password: str, tenant_code: str) -> User:
        """
        Authentifie un utilisateur avec email/mot de passe.

        IMPORTANT: Cette méthode est réservée aux utilisateurs dont la profession
        ne nécessite pas de RPPS. Les professionnels de santé (requires_rpps=True)
        doivent utiliser Pro Santé Connect.

        Note: Le RLS est temporairement bypassé pour chercher l'utilisateur par email,
        car on ne connaît pas encore le tenant_id à ce stade.
        """
        # Bypass RLS pour chercher l'utilisateur par email
        # (on ne connaît pas encore le tenant_id)
        self.db.execute(text("SET app.is_super_admin = 'true'"))
        try:
            # Résoudre le tenant par son code
            tenant = self.db.query(Tenant).filter(
                Tenant.code == tenant_code.upper()
            ).first()
            if not tenant:
                raise InvalidCredentialsError("Code structure, email ou mot de passe incorrect")
            if tenant.status != TenantStatus.ACTIVE:
                raise InactiveUserError("Cette structure est actuellement désactivée")

            # Rechercher l'utilisateur via blind index (email chiffré)
            tenant_id_value: int = tenant.id  # type: ignore[assignment]
            email_blind = get_user_search_blind(email, "email", tenant_id_value)

            user: User | None = self.db.query(User).filter(
                User.email_blind == email_blind,
                User.tenant_id == tenant.id,
            ).first()

            if not user:
                raise InvalidCredentialsError("Email ou mot de passe incorrect")

            # Vérifier si le compte est verrouillé
            if user.is_locked:
                raise InvalidCredentialsError(
                    "Compte temporairement verrouillé suite à des tentatives échouées. "
                    "Réessayez dans quelques minutes."
                )

            # ATTENTION ! : Vérifier que la profession ne nécessite pas PSC
            if user.profession and user.profession.requires_rpps:
                raise InvalidCredentialsError(
                    "Les professionnels de santé doivent utiliser Pro Santé Connect. "
                    "Veuillez vous connecter avec votre e-CPS."
                )

            # Vérifier que l'utilisateur a un mot de passe (pas un compte PSC uniquement)
            if not user.password_hash:
                raise InvalidCredentialsError(
                    "Ce compte utilise Pro Santé Connect. "
                    "Veuillez vous connecter avec votre e-CPS."
                )

            # À ce stade, password_hash est garanti non-None
            password_hash = str(user.password_hash)

            # Vérifier le mot de passe
            if not verify_password(password, password_hash):
                user.record_login_failure()
                self.db.commit()
                raise InvalidCredentialsError("Email ou mot de passe incorrect")

            # Vérifier que le compte est actif
            if not user.is_active:
                raise InactiveUserError("Ce compte a été désactivé")

            # Succès : réinitialiser les compteurs
            user.record_login_success()

            # Configurer le contexte RLS avec le bon tenant pour les opérations suivantes
            self.db.execute(text(f"SET app.current_tenant_id = '{user.tenant_id}'"))
            self.db.execute(text("SET app.is_super_admin = 'false'"))

            self.db.commit()
            self.db.refresh(user)

            # Forcer le chargement des relations avant détachement
            _ = user.role_associations
            for ra in user.role_associations:
                _ = ra.role  # 🔄 S5 fix — charger le Role imbriqué (évite DetachedInstanceError)
            _ = user.profession

            # v4.8 : Pattern expunge+decrypt via decrypt_model
            self.db.expunge(user)  # Détacher → plus de tracking
            self._decrypt_user_in_place(user)

            assert isinstance(user, User)
            return user

        except (InvalidCredentialsError, InactiveUserError):
            # Remettre RLS en mode normal avant de propager l'exception
            self.db.execute(text("SET app.is_super_admin = 'false'"))
            raise
        except Exception as e:
            # Remettre RLS en mode normal en cas d'erreur inattendue
            self.db.execute(text("SET app.is_super_admin = 'false'"))
            raise

    def change_password(self, user: User, current_password: str, new_password: str) -> User:
        """
        Change le mot de passe d'un utilisateur.
        """
        # Re-fetch le user dans CETTE session (current_user vient d'une autre session)
        db_user = self.db.get(User, user.id)
        if not db_user:
            raise InvalidCredentialsError("Utilisateur non trouvé")

        if not db_user.password_hash:
            raise InvalidCredentialsError("Ce compte n'a pas de mot de passe local")

        if not verify_password(current_password, str(db_user.password_hash)):
            raise InvalidCredentialsError("Mot de passe actuel incorrect")

        # Mettre à jour
        db_user.password_hash = hash_password(new_password)
        db_user.must_change_password = False

        self.db.commit()
        self.db.refresh(db_user)

        # Charger les relations avant détachement
        _ = db_user.role_associations
        for ra in db_user.role_associations:
            _ = ra.role  # 🔄 S5 fix — charger le Role imbriqué
        _ = db_user.profession

        # v4.8 : Pattern expunge+decrypt via decrypt_model
        self.db.expunge(db_user)
        self._decrypt_user_in_place(db_user)

        return db_user

    # =========================================================================
    # AUTHENTIFICATION PRO SANTÉ CONNECT
    # =========================================================================

    def create_psc_session(self, redirect_after: Optional[str] = None) -> Tuple[str, str]:
        """
        Crée une session PSC et retourne l'URL d'autorisation.

        Cette méthode :
        1. Génère l'URL d'autorisation PSC avec state, nonce, PKCE
        2. Stocke les données de session dans Redis
        3. Retourne l'URL pour rediriger l'utilisateur

        Args:
            redirect_after: URL optionnelle où rediriger après le login

        Returns:
            Tuple (authorization_url, state)
        """
        psc_client = get_psc_client()

        # Générer l'URL d'autorisation et les valeurs de sécurité
        auth_url, state, nonce, code_verifier = psc_client.get_authorization_url()

        # Créer les données de session
        session_data = PSCSessionData(
            state=state,
            nonce=nonce,
            code_verifier=code_verifier,
            created_at=datetime.now(timezone.utc),
            redirect_after=redirect_after,
        )

        # Stocker en Redis avec TTL
        session_key = f"{self.PSC_SESSION_PREFIX}{state}"
        self.redis.setex(
            session_key,
            self.PSC_SESSION_TTL_SECONDS,
            session_data.model_dump_json()
        )

        return auth_url, state

    def get_psc_session(self, state: str) -> PSCSessionData:
        """
        Récupère et valide une session PSC.

        Args:
            state: State reçu dans le callback

        Returns:
            Données de session PSC

        Raises:
            PSCSessionError: Si la session est invalide ou expirée
        """
        session_key = f"{self.PSC_SESSION_PREFIX}{state}"
        session_json = self.redis.get(session_key)

        if not session_json:
            raise PSCSessionError(
                "Session PSC invalide ou expirée. Veuillez recommencer la connexion."
            )

        # Supprimer la session (usage unique)
        self.redis.delete(session_key)

        return PSCSessionData.model_validate_json(session_json)

    async def authenticate_with_psc(self, code: str, state: str) -> Tuple[User, Dict[str, Any]]:
        """
        Processus complet d'authentification via Pro Santé Connect.

        Orchestration :
        1. Valide la session PSC (state)
        2. Échange le code PSC contre un access token
        3. Récupère les infos du professionnel depuis PSC
        4. Crée ou met à jour l'utilisateur en base locale

        Args:
            code: Code d'autorisation reçu de PSC
            state: State pour validation CSRF

        Returns:
            Tuple (User, parsed_user_info)

        Raises:
            PSCSessionError: Si le state est invalide
            PSCTokenError: Si l'échange de tokens échoue
            PSCUserInfoError: Si la récupération des infos échoue
        """
        psc_client = get_psc_client()

        # Récupérer et valider la session
        session = self.get_psc_session(state)

        # Échanger le code contre des tokens
        tokens = await psc_client.exchange_code_for_tokens(
            code=code,
            code_verifier=session.code_verifier
        )

        # Récupérer les infos utilisateur
        access_token = tokens["access_token"]
        user_info = await psc_client.get_user_info(access_token)

        # Parser les infos
        parsed_info = psc_client.parse_user_info(user_info)

        # Créer ou mettre à jour l'utilisateur
        user = self._create_or_update_user_from_psc(parsed_info)

        # Vérifier que l'utilisateur a accès
        if not user.is_active:
            raise InactiveUserError(
                "Votre compte est inactif. Contactez un administrateur."
            )

        return user, parsed_info

    def _create_or_update_user_from_psc(self, psc_info: Dict[str, Any]) -> User:
        """
        Crée ou met à jour un utilisateur depuis les données PSC.

        La logique :
        1. Chercher par RPPS (blind index)
        2. Si trouvé : mettre à jour les infos et last_login
        3. Si non trouvé : créer un nouvel utilisateur avec rôle par défaut

        Args:
            psc_info: Informations parsées de PSC

        Returns:
            User (existant ou nouvellement créé)
        """
        rpps = psc_info.get("rpps")

        if not rpps:
            raise ValueError("RPPS manquant dans les données PSC")

        # v4.8 : Chercher l'utilisateur par RPPS via blind index
        # Note: tenant_id=None car recherche cross-tenant lors d'une connexion PSC
        # TODO: Évaluer si la recherche cross-tenant par RPPS nécessite
        #       un blind index global (sans tenant) ou une itération sur les tenants
        rpps_blind = user_encryptor.get_blind_index(rpps, "rpps", tenant_id=None)
        user = self.db.query(User).filter(User.rpps_blind == rpps_blind).first()

        # Extraire les infos
        first_name = psc_info.get("given_name", "")
        last_name = psc_info.get("family_name", "")
        email = psc_info.get("email")
        profession_name = psc_info.get("profession", "Professionnel de santé")
        profession_code = psc_info.get("profession_code")

        if user:
            # === Mise à jour d'un utilisateur existant ===
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name

            # v4.8 : Re-chiffrer l'email si mis à jour
            if email:
                encrypted_email = user_encryptor.encrypt_for_db(
                    {"email": email}, tenant_id=user.tenant_id
                )
                user.email_encrypted = encrypted_email["email_encrypted"]
                user.email_blind = encrypted_email["email_blind"]

            user.last_login = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(user)

        else:
            # === Création d'un nouvel utilisateur ===

            # Trouver la profession correspondante
            profession = None
            if profession_code:
                profession = self.db.query(Profession).filter(
                    Profession.code == profession_code
                ).first()

            # Générer un email si non fourni par PSC
            if not email:
                email = f"{rpps}@psc.carelink.local"

            # v4.8 : Chiffrer email et rpps via encrypt_for_db
            # TODO: Déterminer dynamiquement le tenant_id pour les nouveaux users PSC
            target_tenant_id = 1  # TODO: Déterminer dynamiquement
            encrypted_data = user_encryptor.encrypt_for_db(
                {"email": email, "rpps": rpps},
                tenant_id=target_tenant_id
            )

            # Créer l'utilisateur avec les colonnes _encrypted
            user = User(
                email_encrypted=encrypted_data["email_encrypted"],
                email_blind=encrypted_data["email_blind"],
                rpps_encrypted=encrypted_data.get("rpps_encrypted"),
                rpps_blind=encrypted_data.get("rpps_blind"),
                first_name=first_name or "Prénom",
                last_name=last_name or "Nom",
                profession_id=profession.id if profession else None,
                password_hash=None,  # Pas de mot de passe, auth PSC uniquement
                is_active=True,
                is_admin=False,
                tenant_id=target_tenant_id,
                last_login=datetime.now(timezone.utc),
            )

            self.db.add(user)
            self.db.flush()  # Pour obtenir l'ID

            # Attribuer un rôle par défaut selon la profession
            default_role = self._get_default_role_for_profession(profession_name)
            if default_role:
                user.roles.append(default_role)

            self.db.commit()
            self.db.refresh(user)

        return user

    def _get_default_role_for_profession(self, profession: str) -> Optional[Role]:
        """
        Retourne le rôle par défaut à attribuer selon la profession.

        🔄 S5 fix : Depuis S3, les 7 rôles-professions (MEDECIN_TRAITANT, INFIRMIERE, etc.)
        ont été supprimés. Le rôle par défaut est INTERVENANT (accès lecture seule).
        L'admin du tenant ajustera les responsabilités ensuite.

        Args:
            profession: Profession extraite de PSC

        Returns:
            Objet Role ou None
        """
        # Post-S3 : tous les nouveaux utilisateurs PSC reçoivent INTERVENANT
        # comme rôle fonctionnel de base. L'admin client assignera
        # COORDINATEUR, REFERENT ou EVALUATEUR selon les besoins.
        return self.db.query(Role).filter(Role.name == "INTERVENANT").first()

    # =========================================================================
    # GÉNÉRATION DE TOKENS JWT
    # =========================================================================

    def create_tokens_for_user(self, user: User) -> TokenResponse:
        """
        Génère les tokens JWT pour un utilisateur authentifié.

        Note: user.email et user.rpps retournent les valeurs via les
        properties de rétro-compatibilité (email_encrypted / rpps_encrypted).
        Après expunge+decrypt, elles contiennent les valeurs en clair.

        Args:
            user: Utilisateur authentifié

        Returns:
            TokenResponse avec access_token et refresh_token
        """
        # Récupérer les noms de rôles
        role_names = [role.name for role in user.roles] if user.roles else []

        # Claims pour l'access token
        # user.email et user.rpps sont les properties rétro-compat
        # qui pointent vers email_encrypted / rpps_encrypted (en clair post-decrypt)
        access_token_data = {
            "sub": str(user.id),
            "email": user.email,
            "rpps": user.rpps,
            "roles": role_names,
            "tenant_id": user.tenant_id,
            "is_admin": user.is_admin,
        }

        # Claims pour le refresh token (minimaux)
        refresh_token_data = {
            "sub": str(user.id),
        }

        # Créer les tokens
        access_token = create_access_token(access_token_data)
        refresh_token = create_refresh_token(refresh_token_data)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # =========================================================================
    # GESTION DES ACCÈS PATIENTS
    # =========================================================================

    def verify_patient_access(self, user: User, patient_id: int) -> bool:
        """
        Vérifie si un utilisateur a le droit d'accéder à un patient.

        Règles d'accès :
        - Admins : accès à tous les patients
        - Médecin traitant du patient : accès complet
        - Professionnels autorisés explicitement : accès selon PatientAccess
        - Même tenant : selon la politique de l'organisation

        Args:
            user: Utilisateur demandant l'accès
            patient_id: ID du patient

        Returns:
            True si l'utilisateur peut accéder au patient
        """
        from app.models.patient.patient import Patient
        from app.models.patient.patient_access import PatientAccess

        # Admin : accès total
        if user.is_admin:
            return True

        # Récupérer le patient
        patient = self.db.query(Patient).filter(Patient.id == patient_id).first()

        if not patient:
            return False

        # Médecin traitant : accès total
        if hasattr(patient, 'medecin_traitant_id') and patient.medecin_traitant_id == user.id:
            return True

        # Vérifier les autorisations explicites
        access = self.db.query(PatientAccess).filter(
            PatientAccess.patient_id == patient_id,
            PatientAccess.user_id == user.id,
            PatientAccess.revoked_at.is_(None)
        ).first()

        if access:
            # Vérifier l'expiration si définie
            if access.expires_at and access.expires_at < datetime.now(timezone.utc):
                return False
            return True

        # Même tenant = accès (selon politique)
        if hasattr(patient, 'tenant_id') and patient.tenant_id == user.tenant_id:
            return True

        return False

    def grant_patient_access(
            self,
            patient_id: int,
            user_id: int,
            granted_by_id: int,
            access_type: AccessType,
            reason: str,
            expires_in_days: Optional[int] = None
    ) -> None:
        """
        Accorde à un utilisateur l'accès à un patient.

        Args:
            patient_id: ID du patient
            user_id: ID de l'utilisateur recevant l'accès
            granted_by_id: ID de l'utilisateur accordant l'accès
            access_type: Type d'accès ("READ", "WRITE", "FULL")
            reason: Raison de l'accès (obligatoire pour audit)
            expires_in_days: Nombre de jours avant expiration (None = permanent)

        Raises:
            PatientAccessError: Si l'utilisateur a déjà un accès actif
        """
        from app.models.patient.patient_access import PatientAccess

        # Vérifier si l'accès existe déjà
        existing_access = self.db.query(PatientAccess).filter(
            PatientAccess.patient_id == patient_id,
            PatientAccess.user_id == user_id,
            PatientAccess.revoked_at.is_(None)
        ).first()

        if existing_access:
            raise PatientAccessError("L'utilisateur a déjà un accès actif à ce patient")

        # Calculer la date d'expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        # Créer l'accès
        access = PatientAccess(
            patient_id=patient_id,
            user_id=user_id,
            access_type=access_type.value,
            reason=reason,
            granted_by=granted_by_id,
            granted_at=datetime.now(timezone.utc),
            expires_at=expires_at,
        )

        self.db.add(access)
        self.db.commit()

    def revoke_patient_access(self, patient_id: int, user_id: int) -> bool:
        """
        Révoque l'accès d'un utilisateur à un patient.

        Args:
            patient_id: ID du patient
            user_id: ID de l'utilisateur

        Returns:
            True si un accès a été révoqué, False sinon
        """
        from app.models.patient.patient_access import PatientAccess

        access = self.db.query(PatientAccess).filter(
            PatientAccess.patient_id == patient_id,
            PatientAccess.user_id == user_id,
            PatientAccess.revoked_at.is_(None)
        ).first()

        if access:
            access.revoked_at = datetime.now(timezone.utc)
            self.db.commit()
            return True

        return False

    def verify_user_role(self, user: User, required_role: str) -> bool:
        """
        Vérifie si un utilisateur a un rôle spécifique.

        Args:
            user: Utilisateur à vérifier
            required_role: Nom du rôle requis

        Returns:
            True si l'utilisateur a le rôle (ou est admin), False sinon
        """
        # Les admins ont toujours accès
        if user.is_admin:
            return True

        # Vérifier les rôles
        user_roles = [role.name for role in user.roles] if user.roles else []
        return required_role in user_roles

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _decrypt_user_in_place(self, user: User) -> None:
        """
        Déchiffre les champs sensibles d'un User détaché (post-expunge).

        Utilise BaseEncryptor.decrypt_model() pour obtenir les valeurs claires,
        puis les écrit via les properties de rétro-compatibilité.

        ATTENTION: Appeler uniquement APRÈS db.expunge(user).

        Args:
            user: User détaché de la session SQLAlchemy
        """
        try:
            decrypted = user_encryptor.decrypt_model(user)
            # Les properties email/rpps écrivent dans email_encrypted/rpps_encrypted
            if "email" in decrypted and decrypted["email"] is not None:
                user.email = decrypted["email"]
            if "rpps" in decrypted and decrypted["rpps"] is not None:
                user.rpps = decrypted["rpps"]
        except Exception:
            pass  # Si le déchiffrement échoue, on garde les valeurs brutes

    def build_authenticated_user(self, user: User) -> AuthenticatedUser:
        """
        Construit un objet AuthenticatedUser depuis un User.

        Args:
            user: Utilisateur SQLAlchemy (post-decrypt si détaché)

        Returns:
            AuthenticatedUser (schéma Pydantic)
        """
        # Récupérer les noms de rôles
        role_names = [role.name for role in user.roles] if user.roles else []

        # Récupérer le nom de profession
        profession_name = None
        if user.profession:
            profession_name = user.profession.name

        # user.email et user.rpps utilisent les properties rétro-compat
        return AuthenticatedUser(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=f"{user.first_name} {user.last_name}",
            rpps=user.rpps,
            profession=profession_name,
            speciality=getattr(user, 'speciality', None),
            roles=role_names,
            is_admin=user.is_admin,
            must_change_password=user.must_change_password,
            tenant_id=user.tenant_id,
        )

    def build_login_response(
            self,
            user: User,
            auth_method: AuthMethod
    ) -> LoginResponse:
        """
        Construit la réponse complète de login.

        Args:
            user: Utilisateur authentifié
            auth_method: Méthode d'authentification

        Returns:
            LoginResponse avec user, tokens et méthode
        """
        return LoginResponse(
            user=self.build_authenticated_user(user),
            tokens=self.create_tokens_for_user(user),
            auth_method=auth_method,
        )


# =============================================================================
# FACTORY
# =============================================================================

def get_auth_service(db: Session) -> AuthService:
    """Factory pour créer un AuthService avec une session DB."""
    return AuthService(db)