"""
Configuration centralisée CareLink
Charge les variables depuis le fichier .env

MODIFICATIONS:
- Ajout de PSC_ENVIRONMENT pour switch BAS/PROD
- URLs PSC dynamiques selon l'environnement (properties)
- Correction URL callback PSC: /api/v1/auth/psc/callback
"""
import json
from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration de l'application CareLink.

    Les valeurs sont chargées depuis les variables d'environnement
    ou le fichier .env à la racine du projet.

    Usage:
        from app.core.config import settings
        print(settings.DATABASE_URL)
    """

    # === Environnement ===
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "CareLink"
    APP_VERSION: str = "0.1.0"

    # === Base de données PostgreSQL ===
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/dbname"

    # === Redis ===
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_SSL: bool = False
    REDIS_MAX_CONNECTIONS: int = 50

    # Locks d'édition
    EDIT_LOCK_TTL_SECONDS: int = 600  # 10 minutes
    LOCK_HEARTBEAT_INTERVAL_SECONDS: int = 30

    # === JWT (Authentification) ===
    ALGORITHM: str = "ES256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_PRIVATE_KEY_PATH: str = "keys/jwt_private_key.pem"
    JWT_PUBLIC_KEY_PATH: str = "keys/jwt_public_key.pem"

    # === Chiffrement AES-256 (Données patients) ===
    ENCRYPTION_KEY: Optional[str] = None

    # === Pro Santé Connect (OAuth2/OIDC) ===
    # Identifiants client (fournis par Datapass après validation)
    PSC_CLIENT_ID: Optional[str] = None
    PSC_CLIENT_SECRET: Optional[str] = None

    # URL de callback (doit correspondre à celle déclarée dans Datapass)
    PSC_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/psc/callback"

    # Environnement PSC: "bas" (Bac à Sable) ou "prod" (Production)
    # - bas: pour développement et tests avec identités fictives (EDiT)
    # - prod: pour production avec vrais professionnels de santé
    PSC_ENVIRONMENT: str = "bas"

    # URLs PSC (optionnel - calculées automatiquement selon PSC_ENVIRONMENT)
    # Ne définir dans .env que si vous avez besoin d'URLs personnalisées
    PSC_AUTHORIZATION_URL_OVERRIDE: Optional[str] = None
    PSC_TOKEN_URL_OVERRIDE: Optional[str] = None
    PSC_USERINFO_URL_OVERRIDE: Optional[str] = None
    PSC_JWKS_URL_OVERRIDE: Optional[str] = None

    # === CORS ===
    CORS_ORIGINS: List[str] = ["http://localhost:8000", "http://localhost:3000"]

    # === Logging ===
    LOG_LEVEL: str = "INFO"

    # === Configuration Pydantic ===
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignorer les variables non définies
    )

    # === Validators ===

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS depuis une string JSON ou une liste"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Si c'est une simple string, la mettre dans une liste
                return [v]
        return v

    @field_validator('ENVIRONMENT')
    @classmethod
    def validate_environment(cls, v):
        """Valide que l'environnement est valide"""
        allowed = ['development', 'staging', 'production', 'test']
        if v.lower() not in allowed:
            raise ValueError(f"ENVIRONMENT doit être parmi : {allowed}")
        return v.lower()

    @field_validator('PSC_ENVIRONMENT')
    @classmethod
    def validate_psc_environment(cls, v):
        """Valide que l'environnement PSC est valide"""
        allowed = ['bas', 'prod']
        if v.lower() not in allowed:
            raise ValueError(f"PSC_ENVIRONMENT doit être 'bas' ou 'prod'")
        return v.lower()

    # === Properties générales ===

    @property
    def is_development(self) -> bool:
        """Retourne True si en mode développement"""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Retourne True si en mode production"""
        return self.ENVIRONMENT == "production"

    @property
    def is_test(self) -> bool:
        """Retourne True si en mode test"""
        return self.ENVIRONMENT == "test"

    @property
    def redis_url(self) -> str:
        """Retourne l'URL Redis complète"""
        password = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        protocol = "rediss" if self.REDIS_SSL else "redis"
        return f"{protocol}://{password}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def psc_configured(self) -> bool:
        """Retourne True si Pro Santé Connect est configuré"""
        return bool(self.PSC_CLIENT_ID and self.PSC_CLIENT_SECRET)

    @property
    def encryption_configured(self) -> bool:
        """Retourne True si le chiffrement est configuré"""
        return bool(self.ENCRYPTION_KEY)

    # === Properties PSC - URLs dynamiques selon l'environnement ===

    @property
    def psc_is_bas(self) -> bool:
        """Retourne True si on utilise le Bac à Sable PSC"""
        return self.PSC_ENVIRONMENT.lower() == "bas"

    @property
    def psc_authorization_url(self) -> str:
        """
        URL d'autorisation PSC (dépend de l'environnement).

        BAS: https://wallet.bas.psc.esante.gouv.fr/auth
        PROD: https://wallet.esw.esante.gouv.fr/auth
        """
        if self.PSC_AUTHORIZATION_URL_OVERRIDE:
            return self.PSC_AUTHORIZATION_URL_OVERRIDE

        if self.psc_is_bas:
            return "https://wallet.bas.psc.esante.gouv.fr/auth"
        return "https://wallet.esw.esante.gouv.fr/auth"

    @property
    def psc_token_url(self) -> str:
        """
        URL d'échange de tokens PSC (dépend de l'environnement).

        BAS: https://auth.bas.psc.esante.gouv.fr/auth/realms/esante-wallet/protocol/openid-connect/token
        PROD: https://auth.esw.esante.gouv.fr/auth/realms/esante-wallet/protocol/openid-connect/token
        """
        if self.PSC_TOKEN_URL_OVERRIDE:
            return self.PSC_TOKEN_URL_OVERRIDE

        if self.psc_is_bas:
            return "https://auth.bas.psc.esante.gouv.fr/auth/realms/esante-wallet/protocol/openid-connect/token"
        return "https://auth.esw.esante.gouv.fr/auth/realms/esante-wallet/protocol/openid-connect/token"

    @property
    def psc_userinfo_url(self) -> str:
        """
        URL userinfo PSC (dépend de l'environnement).

        BAS: https://auth.bas.psc.esante.gouv.fr/auth/realms/esante-wallet/protocol/openid-connect/userinfo
        PROD: https://auth.esw.esante.gouv.fr/auth/realms/esante-wallet/protocol/openid-connect/userinfo
        """
        if self.PSC_USERINFO_URL_OVERRIDE:
            return self.PSC_USERINFO_URL_OVERRIDE

        if self.psc_is_bas:
            return "https://auth.bas.psc.esante.gouv.fr/auth/realms/esante-wallet/protocol/openid-connect/userinfo"
        return "https://auth.esw.esante.gouv.fr/auth/realms/esante-wallet/protocol/openid-connect/userinfo"

    @property
    def psc_jwks_url(self) -> str:
        """
        URL JWKS PSC pour vérification des tokens (dépend de l'environnement).

        BAS: https://auth.bas.psc.esante.gouv.fr/auth/realms/esante-wallet/protocol/openid-connect/certs
        PROD: https://auth.esw.esante.gouv.fr/auth/realms/esante-wallet/protocol/openid-connect/certs
        """
        if self.PSC_JWKS_URL_OVERRIDE:
            return self.PSC_JWKS_URL_OVERRIDE

        if self.psc_is_bas:
            return "https://auth.bas.psc.esante.gouv.fr/auth/realms/esante-wallet/protocol/openid-connect/certs"
        return "https://auth.esw.esante.gouv.fr/auth/realms/esante-wallet/protocol/openid-connect/certs"


@lru_cache()
def get_settings() -> Settings:
    """
    Retourne l'instance des settings (mise en cache).

    Utilise lru_cache pour ne charger les settings qu'une seule fois.

    Usage:
        settings = get_settings()
    """
    return Settings()


# Instance globale pour import facile
settings = get_settings()