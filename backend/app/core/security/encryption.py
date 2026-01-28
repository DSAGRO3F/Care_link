"""Chiffrement AES-256-GCM des données sensibles patients."""

import base64
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


class FieldEncryption:
    """
    Chiffrement/déchiffrement de champs individuels avec AES-256-GCM.

    AES-256-GCM offre :
    - Confidentialité (chiffrement)
    - Intégrité (authentification)
    - Protection contre les attaques par rejeu

    Conforme aux recommandations pour données de santé.
    """

    def __init__(self):
        """Initialise le chiffreur avec la clé de configuration."""
        # Décoder la clé base64 depuis la config
        self.key = base64.b64decode(settings.ENCRYPTION_KEY)

        # Vérifier que c'est bien une clé 256 bits (32 bytes)
        if len(self.key) != 32:
            raise ValueError(
                "ENCRYPTION_KEY doit être une clé AES-256 (32 bytes en base64). "
                "Générez-en une avec: python scripts/generate_keys.py"
            )

        self.aesgcm = AESGCM(self.key)

    def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        """
        Chiffre une valeur avec AES-256-GCM.

        Args:
            plaintext: Valeur en clair (ou None)

        Returns:
            Valeur chiffrée encodée en base64 (format: nonce||ciphertext||tag)
            ou None si l'entrée est None

        Note:
            Un nonce aléatoire est généré pour chaque chiffrement,
            garantissant qu'un même plaintext produit des ciphertexts différents.
        """
        if plaintext is None or plaintext == "":
            return plaintext

        # Générer un nonce aléatoire de 96 bits (12 bytes, recommandé pour GCM)
        nonce = os.urandom(12)

        # Chiffrer avec authentification
        ciphertext = self.aesgcm.encrypt(
            nonce,
            plaintext.encode('utf-8'),
            None  # Associated data (optionnel)
        )

        # Format: nonce (12 bytes) || ciphertext+tag
        encrypted_data = nonce + ciphertext

        # Encoder en base64 pour stockage en DB
        return base64.b64encode(encrypted_data).decode('utf-8')

    def decrypt(self, ciphertext: Optional[str]) -> Optional[str]:
        """
        Déchiffre une valeur chiffrée avec AES-256-GCM.

        Args:
            ciphertext: Valeur chiffrée en base64

        Returns:
            Valeur déchiffrée ou None

        Raises:
            Exception: Si le tag d'authentification est invalide (données altérées)
        """
        if ciphertext is None or ciphertext == "":
            return ciphertext

        try:
            # Décoder depuis base64
            encrypted_data = base64.b64decode(ciphertext)

            # Extraire nonce et ciphertext+tag
            nonce = encrypted_data[:12]
            ciphertext_with_tag = encrypted_data[12:]

            # Déchiffrer et vérifier l'authentification
            plaintext_bytes = self.aesgcm.decrypt(
                nonce,
                ciphertext_with_tag,
                None
            )

            return plaintext_bytes.decode('utf-8')

        except Exception as e:
            # En production, logger cette erreur (possible tentative d'altération)
            raise ValueError(f"Échec du déchiffrement (données altérées?) : {str(e)}")


# Instance singleton
_encryptor = None

def get_encryptor() -> FieldEncryption:
    """Retourne l'instance singleton du chiffreur."""
    global _encryptor
    if _encryptor is None:
        _encryptor = FieldEncryption()
    return _encryptor


def encrypt_field(value: Optional[str]) -> Optional[str]:
    """
    Fonction helper pour chiffrer un champ.

    Args:
        value: Valeur en clair

    Returns:
        Valeur chiffrée
    """
    return get_encryptor().encrypt(value)


def decrypt_field(value: Optional[str]) -> Optional[str]:
    """
    Fonction helper pour déchiffrer un champ.

    Args:
        value: Valeur chiffrée

    Returns:
        Valeur déchiffrée
    """
    return get_encryptor().decrypt(value)