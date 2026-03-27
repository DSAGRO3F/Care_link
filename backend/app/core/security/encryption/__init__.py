"""
Module de chiffrement avancé pour CareLink.

Ce sous-module étend les capacités de base de cipher.py avec:
- Gestion abstraite des clés (préparation pour Vault)
- Blind indexes pour recherche sur données chiffrées
- Support des types complexes (dates, JSON)

Structure:
    encryption/
    ├── __init__.py         # Ce fichier - exports publics
    ├── key_manager.py      # Gestion des clés (abstraction)
    ├── blind_index.py      # HMAC-SHA256 pour recherche
    └── field_types.py      # Helpers dates, JSON, etc.

Usage principal:
    from app.core.security.encryption import (
        # Blind indexes
        create_blind_index,
        create_blind_index_for_search,

        # Types spéciaux
        encrypt_date, decrypt_date,
        encrypt_json, decrypt_json,

        # JSONB partiel
        encrypt_jsonb_text_fields,
        decrypt_jsonb_text_fields,
    )

Note:
    Les fonctions de base encrypt_field/decrypt_field restent dans
    le module parent (app.core.security.encryption) pour compatibilité.
"""

# =============================================================================
# KEY MANAGEMENT
# =============================================================================

# =============================================================================
# BLIND INDEXES
# =============================================================================
from app.core.security.encryption.blind_index import (
    create_blind_index,
    create_blind_index_for_search,
    normalize_value,
    verify_blind_index,
)

# =============================================================================
# FIELD TYPES
# =============================================================================
from app.core.security.encryption.field_types import (
    decrypt_date,
    decrypt_datetime,
    decrypt_dict_fields,
    decrypt_json,
    decrypt_jsonb_text_fields,
    # Dates
    encrypt_date,
    encrypt_datetime,
    # Champs sélectifs
    encrypt_dict_fields,
    # JSON
    encrypt_json,
    # JSONB avec chiffrement partiel
    encrypt_jsonb_text_fields,
)
from app.core.security.encryption.key_manager import (
    EnvKeyManager,
    KeyManager,
    get_key_manager,
    reset_key_manager,
)


# =============================================================================
# EXPORTS PUBLICS
# =============================================================================

__all__ = [
    # Key management
    "KeyManager",
    "EnvKeyManager",
    "get_key_manager",
    "reset_key_manager",
    # Blind indexes
    "create_blind_index",
    "create_blind_index_for_search",
    "verify_blind_index",
    "normalize_value",
    # Dates
    "encrypt_date",
    "decrypt_date",
    "encrypt_datetime",
    "decrypt_datetime",
    # JSON
    "encrypt_json",
    "decrypt_json",
    # Dict fields
    "encrypt_dict_fields",
    "decrypt_dict_fields",
    # JSONB
    "encrypt_jsonb_text_fields",
    "decrypt_jsonb_text_fields",
]
