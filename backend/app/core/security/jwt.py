"""Gestion des tokens JWT avec ES256 pour conformité e-santé."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings


def _load_private_key() -> str:
    """Charge la clé privée ES256 depuis le fichier."""
    key_path = Path(settings.JWT_PRIVATE_KEY_PATH)
    if not key_path.exists():
        raise FileNotFoundError(
            f"Clé privée JWT non trouvée: {key_path}. "
            "Générez les clés avec: python scripts/generate_keys.py"
        )
    return key_path.read_text()


def _load_public_key() -> str:
    """Charge la clé publique ES256 depuis le fichier."""
    key_path = Path(settings.JWT_PUBLIC_KEY_PATH)
    if not key_path.exists():
        raise FileNotFoundError(
            f"Clé publique JWT non trouvée: {key_path}. "
            "Générez les clés avec: python scripts/generate_keys.py"
        )
    return key_path.read_text()


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Crée un token JWT d'accès signé avec ES256.

    Args:
        data: Claims à encoder (sub, roles, rpps, etc.)
        expires_delta: Durée de validité personnalisée

    Returns:
        Token JWT signé avec ES256

    Note:
        Utilise ECDSA P-256 (ES256) conformément aux recommandations
        de l'ANS pour l'espace de confiance e-santé.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Claims standards JWT
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(UTC),
            "iss": "carelink",
        }
    )
    if "type" not in to_encode:
        to_encode["type"] = "access"

    # Signature avec clé privée ES256
    private_key = _load_private_key()
    encoded_jwt = jwt.encode(
        to_encode,
        private_key,
        algorithm=settings.ALGORITHM,  # ES256
    )

    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Crée un token JWT de refresh signé avec ES256.

    Args:
        data: Claims minimaux (généralement juste sub)

    Returns:
        Refresh token JWT signé avec ES256
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(UTC),
            "iss": "carelink",
        }
    )
    # Ne pas écraser le type s'il est déjà défini
    if "type" not in to_encode:
        to_encode["type"] = "refresh"

    private_key = _load_private_key()
    encoded_jwt = jwt.encode(to_encode, private_key, algorithm=settings.ALGORITHM)

    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> dict[str, Any]:
    """
    Vérifie et décode un token JWT signé avec ES256.

    Args:
        token: Token JWT à vérifier
        token_type: Type attendu ("access" ou "refresh")

    Returns:
        Payload décodé

    Raises:
        JWTError: Si le token est invalide, expiré ou de mauvais type

    Note:
        Vérifie la signature ECDSA avec la clé publique.
    """
    try:
        public_key = _load_public_key()

        payload = jwt.decode(
            token,
            public_key,
            algorithms=[settings.ALGORITHM],  # ES256
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "require_exp": True,
                "require_iat": True,
            },
        )

        # Vérifier le type de token
        if payload.get("type") != token_type:
            raise JWTError(f"Token type mismatch. Expected {token_type}")

        # Vérifier l'issuer
        if payload.get("iss") != "carelink":
            raise JWTError("Invalid token issuer")

        return payload

    except JWTError as e:
        raise JWTError(f"Token validation failed: {e!s}") from e


def decode_token_without_verification(token: str) -> dict[str, Any]:
    """
    Décode un token sans vérifier sa signature (pour debug/audit uniquement).

    ⚠️ NE JAMAIS utiliser pour l'authentification !
    Utile pour les logs d'audit et le debugging.

    Args:
        token: Token à décoder

    Returns:
        Payload décodé (non vérifié)
    """
    return jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
