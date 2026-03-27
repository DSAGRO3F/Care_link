"""
Service d'encryption spécifique pour les utilisateurs (professionnels de santé).

Ce module gère le chiffrement/déchiffrement des données sensibles
des utilisateurs : email et RPPS.

Classification RGPD/HDS:
- email: 🟠 Fortement recommandé (si nominatif)
- rpps: 🟠 Fortement recommandé (identifiant professionnel)
- first_name/last_name: 🟢 Souhaitable (non chiffré pour l'instant)

Changement v4.8 : Harmonisation encryption
- Suppression des overrides encrypt_for_db, decrypt_model, prepare_update
- Tout est délégué à BaseEncryptor (convention {field}_encrypted)
- Aligné sur le pattern PatientEncryptor

Mapping des champs:

| Champ API | Colonne DB         | Blind Index   | Type   |
|-----------|--------------------|---------------|--------|
| email     | email_encrypted    | email_blind   | string |
| rpps      | rpps_encrypted     | rpps_blind    | string |

Usage:
    from app.services.encryption import user_encryptor

    # Chiffrer pour stockage
    encrypted = user_encryptor.encrypt_for_db({"email": "...", "rpps": "..."}, tenant_id)

    # Déchiffrer après lecture
    decrypted = user_encryptor.decrypt_model(user)

    # Recherche par blind index
    blind = user_encryptor.get_blind_index("email@example.com", "email", tenant_id)
"""

from typing import Any

from app.services.encryption.base_encryptor import BaseEncryptor


class UserEncryptor(BaseEncryptor):
    """
    Encryptor spécifique pour le modèle User.

    Gère le chiffrement AES-256-GCM et les blind indexes HMAC-SHA256
    pour les données sensibles des utilisateurs.

    Champs chiffrés:
    - email: Email professionnel (souvent nominatif)
    - rpps: Numéro RPPS (identifiant national professionnel)

    Blind indexes:
    - email_blind: Pour login et recherche par email
    - rpps_blind: Pour recherche/validation Pro Santé Connect

    Champs NON chiffrés (pour l'instant):
    - first_name, last_name: 🟢 Souhaitable mais pas obligatoire
    - password_hash: Déjà sécurisé par bcrypt
    """

    @property
    def encrypted_fields(self) -> dict[str, str]:
        """
        Définition des champs à chiffrer pour User.

        Format: {"nom_api": "type"}
        """
        return {
            "email": "string",
            "rpps": "string",
        }

    @property
    def blind_index_fields(self) -> set[str]:
        """
        Champs nécessitant un blind index pour la recherche.

        - email: Login multi-tenant, recherche d'unicité
        - rpps: Validation Pro Santé Connect, recherche cross-tenant
        """
        return {"email", "rpps"}

    # =========================================================================
    # MÉTHODES SÉMANTIQUES SPÉCIFIQUES USER
    # =========================================================================

    def search_by_email(self, email: str, tenant_id: int) -> str:
        """
        Génère le blind index pour recherche par email.

        Args:
            email: Adresse email en clair
            tenant_id: ID du tenant (requis — email unique par tenant)

        Returns:
            Blind index pour clause WHERE

        Example:
            >>> blind = user_encryptor.search_by_email("marie@ssiad.fr", tenant_id=1)
            >>> user = db.query(User).filter(User.email_blind == blind).first()
        """
        return self.get_blind_index(email, "email", tenant_id)

    def search_by_rpps(self, rpps: str, tenant_id: int | None = None) -> str:
        """
        Génère le blind index pour recherche par RPPS.

        Args:
            rpps: Numéro RPPS (11 chiffres)
            tenant_id: ID du tenant (None pour recherche cross-tenant PSC)

        Returns:
            Blind index pour clause WHERE

        Example:
            >>> blind = user_encryptor.search_by_rpps("12345678901", tenant_id=1)
            >>> user = db.query(User).filter(User.rpps_blind == blind).first()
        """
        return self.get_blind_index(rpps, "rpps", tenant_id)

    def prepare_for_update(
        self, update_data: dict[str, Any], tenant_id: int | None = None
    ) -> dict[str, Any]:
        """
        Prépare des données partielles pour une mise à jour.

        Ne chiffre que les champs présents dans update_data.
        Utile pour les PATCH où seuls certains champs sont modifiés.

        Args:
            update_data: Données partielles à mettre à jour
            tenant_id: ID du tenant

        Returns:
            Données chiffrées pour UPDATE

        Example:
            >>> update = {"email": "new@ssiad.fr"}
            >>> db_update = user_encryptor.prepare_for_update(update, tenant_id=1)
            >>> # {"email_encrypted": "encrypted...", "email_blind": "8f3a..."}
        """
        return self.encrypt_for_db(update_data, tenant_id)


# =============================================================================
# INSTANCE SINGLETON
# =============================================================================

user_encryptor = UserEncryptor()


# =============================================================================
# FONCTIONS HELPER (pour imports simplifiés)
# =============================================================================


def encrypt_user_data(data: dict[str, Any], tenant_id: int) -> dict[str, Any]:
    """
    Helper pour chiffrer des données utilisateur.

    Usage:
        from app.services.encryption import encrypt_user_data
        encrypted = encrypt_user_data({"email": "...", "rpps": "..."}, tenant_id)
    """
    return user_encryptor.encrypt_for_db(data, tenant_id)


def decrypt_user_data(user: Any) -> dict[str, Any]:
    """
    Helper pour déchiffrer un utilisateur.

    Usage:
        from app.services.encryption import decrypt_user_data
        decrypted = decrypt_user_data(user_model)
    """
    return user_encryptor.decrypt_model(user)


def get_user_search_blind(value: str, field_name: str, tenant_id: int) -> str:
    """
    Helper pour obtenir un blind index de recherche.

    Usage:
        from app.services.encryption import get_user_search_blind
        blind = get_user_search_blind("marie@ssiad.fr", "email", tenant_id)
    """
    return user_encryptor.get_blind_index(value, field_name, tenant_id)
