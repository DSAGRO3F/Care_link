"""Fonctions de hashing pour mots de passe et tokens (one-way)."""

import bcrypt

# Coût computationnel (plus = plus sécurisé mais plus lent)
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """
    Hash un mot de passe avec bcrypt.

    Args:
        password: Mot de passe en clair

    Returns:
        Hash bcrypt du mot de passe
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie qu'un mot de passe correspond à son hash.

    Args:
        plain_password: Mot de passe en clair à vérifier
        hashed_password: Hash bcrypt stocké en base de données

    Returns:
        True si le mot de passe correspond, False sinon
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Hash un token pour stockage sécurisé en base."""
    return hash_password(token)


def verify_token_hash(plain_token: str, hashed_token: str) -> bool:
    """Vérifie qu'un token correspond à son hash."""
    return verify_password(plain_token, hashed_token)


def needs_update(hashed_value: str) -> bool:
    """Vérifie si un hash doit être régénéré."""
    try:
        parts = hashed_value.split('$')
        if len(parts) >= 3:
            rounds = int(parts[2])
            return rounds < BCRYPT_ROUNDS
    except (ValueError, IndexError):
        pass
    return True
