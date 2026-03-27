"""
Gestionnaire de clés de chiffrement.

Ce module fournit une abstraction pour la gestion des clés de chiffrement,
permettant une évolution future vers HashiCorp Vault ou une gestion par tenant
sans modifier le reste du code.

Architecture :
- Phase 1 (actuelle) : Clé unique depuis variable d'environnement
- Phase 2 (future) : Clé par tenant via HashiCorp Vault

Usage:
    from backend.app.core.security.encryption.key_manager import get_key_manager

    key_manager = get_key_manager()
    encryption_key = key_manager.get_encryption_key()
    blind_index_key = key_manager.get_blind_index_key()
"""

import base64
import hashlib
import hmac
from abc import ABC, abstractmethod

from app.core.config import settings


class KeyManager(ABC):
    """
    Classe abstraite définissant l'interface de gestion des clés.

    Permet d'implémenter différentes stratégies :
    - EnvKeyManager : clé depuis .env (Phase 1)
    - VaultKeyManager : clé depuis HashiCorp Vault (Phase 2)
    - TenantKeyManager : clé par tenant (Phase 2)
    """

    @abstractmethod
    def get_encryption_key(self, tenant_id: int | None = None) -> bytes:
        """
        Récupère la clé de chiffrement AES-256.

        Args:
            tenant_id: ID du tenant (ignoré en Phase 1, utilisé en Phase 2)

        Returns:
            Clé de 32 bytes pour AES-256
        """

    @abstractmethod
    def get_blind_index_key(self, tenant_id: int | None = None) -> bytes:
        """
        Récupère la clé pour les blind indexes (HMAC).

        Args:
            tenant_id: ID du tenant (ignoré en Phase 1, utilisé en Phase 2)

        Returns:
            Clé pour HMAC-SHA256

        Note:
            En Phase 1, cette clé est DÉRIVÉE de la clé principale
            pour garantir la séparation des usages (best practice).
        """


class EnvKeyManager(KeyManager):
    """
    Gestionnaire de clés basé sur les variables d'environnement.

    Phase 1 : Utilise ENCRYPTION_KEY depuis .env

    La clé de blind index est dérivée de la clé principale
    en utilisant HMAC comme fonction de dérivation simplifiée
    pour garantir la séparation des usages.
    """

    # Contexte pour la dérivation de la clé blind index
    # (garantit que même avec la même clé source, les blind indexes
    # seront différents des données chiffrées)
    _BLIND_INDEX_CONTEXT = b"carelink_blind_index_v1"

    def __init__(self):
        """Initialise le gestionnaire avec la clé depuis .env"""
        self._master_key = self._load_master_key()
        self._encryption_key: bytes | None = None
        self._blind_index_key: bytes | None = None

    def _load_master_key(self) -> bytes:
        """
        Charge et valide la clé maître depuis la configuration.

        Returns:
            Clé maître décodée (32 bytes)

        Raises:
            ValueError: Si la clé est absente ou invalide
        """
        encryption_key = getattr(settings, "ENCRYPTION_KEY", None)

        if not encryption_key:
            raise ValueError(
                "ENCRYPTION_KEY non définie dans .env. "
                'Générez une clé avec: python -c "import secrets; import base64; '
                'print(base64.b64encode(secrets.token_bytes(32)).decode())"'
            )

        try:
            key = base64.b64decode(encryption_key)
        except Exception as e:
            raise ValueError(f"ENCRYPTION_KEY invalide (doit être en base64): {e}") from e

        if len(key) != 32:
            raise ValueError(
                f"ENCRYPTION_KEY doit faire 32 bytes (256 bits), actuellement: {len(key)} bytes"
            )

        return key

    def _derive_key(self, context: bytes) -> bytes:
        """
        Dérive une clé spécifique à partir de la clé maître.

        Utilise HMAC-SHA256 comme fonction de dérivation simplifiée.
        Chaque contexte produit une clé différente.

        Args:
            context: Contexte de dérivation (ex: b"blind_index")

        Returns:
            Clé dérivée de 32 bytes
        """
        return hmac.new(key=self._master_key, msg=context, digestmod=hashlib.sha256).digest()

    def get_encryption_key(self, tenant_id: int | None = None) -> bytes:
        """
        Récupère la clé de chiffrement AES-256.

        En Phase 1, tenant_id est ignoré (clé unique).

        Args:
            tenant_id: Ignoré en Phase 1

        Returns:
            Clé de 32 bytes pour AES-256-GCM
        """
        # En Phase 1, on utilise directement la clé maître pour le chiffrement
        # (compatibilité avec cipher.py existant)
        if self._encryption_key is None:
            self._encryption_key = self._master_key
        return self._encryption_key

    def get_blind_index_key(self, tenant_id: int | None = None) -> bytes:
        """
        Récupère la clé pour les blind indexes.

        IMPORTANT: Cette clé est DIFFÉRENTE de la clé de chiffrement.
        Elle est dérivée de la clé maître avec un contexte spécifique.

        Cela garantit que:
        1. Un attaquant ne peut pas utiliser les blind indexes pour déduire les clés
        2. Compromission d'un usage ne compromet pas l'autre

        Args:
            tenant_id: Ignoré en Phase 1

        Returns:
            Clé de 32 bytes pour HMAC-SHA256
        """
        if self._blind_index_key is None:
            self._blind_index_key = self._derive_key(self._BLIND_INDEX_CONTEXT)
        return self._blind_index_key


# =============================================================================
# PLACEHOLDER POUR PHASE 2 : VAULT KEY MANAGER
# =============================================================================

# class VaultKeyManager(KeyManager):
#     """
#     Gestionnaire de clés basé sur HashiCorp Vault (Phase 2).
#
#     Fonctionnalités prévues :
#     - Clé par tenant (isolation cryptographique)
#     - Rotation automatique des clés
#     - Audit des accès aux clés
#
#     Exemple d'implémentation:
#
#     def __init__(self, vault_url: str, vault_token: str):
#         import hvac
#         self._vault_client = hvac.Client(url=vault_url, token=vault_token)
#
#     def get_encryption_key(self, tenant_id: Optional[int] = None) -> bytes:
#         path = f"secret/data/carelink/tenants/{tenant_id}/encryption_key"
#         secret = self._vault_client.secrets.kv.v2.read_secret_version(path=path)
#         return base64.b64decode(secret['data']['data']['key'])
#     """
#     pass


# =============================================================================
# SINGLETON ET FACTORY
# =============================================================================

_key_manager: KeyManager | None = None


def get_key_manager() -> KeyManager:
    """
    Retourne l'instance singleton du gestionnaire de clés.

    Factory pattern permettant de changer d'implémentation
    sans modifier le code appelant.

    Returns:
        Instance de KeyManager (EnvKeyManager en Phase 1)

    Usage:
        key_manager = get_key_manager()
        enc_key = key_manager.get_encryption_key()
        blind_key = key_manager.get_blind_index_key()
    """
    global _key_manager

    if _key_manager is None:
        # Phase 1 : Utiliser EnvKeyManager
        # Phase 2 : Conditionner sur VAULT_ENABLED ou similaire
        # if getattr(settings, 'VAULT_ENABLED', False):
        #     _key_manager = VaultKeyManager(settings.VAULT_URL, settings.VAULT_TOKEN)
        # else:
        _key_manager = EnvKeyManager()

    return _key_manager


def reset_key_manager() -> None:
    """
    Réinitialise le singleton (utile pour les tests).

    Permet de:
    - Changer de configuration entre tests
    - Simuler un changement de clé
    """
    global _key_manager
    _key_manager = None
