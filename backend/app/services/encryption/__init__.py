"""
Module de services d'encryption pour CareLink.

Ce module fournit les services métier pour le chiffrement/déchiffrement
des données sensibles dans l'application.

Structure:
    services/encryption/
    ├── __init__.py              # Ce fichier - exports publics
    ├── base_encryptor.py        # Classe abstraite commune
    ├── patient_encryptor.py     # Logique spécifique Patient
    ├── user_encryptor.py        # Logique spécifique User
    └── evaluation_encryptor.py  # Logique spécifique Evaluation (JSONB)

Usage Patient:
    from app.services.encryption import (
        patient_encryptor,
        encrypt_patient_data,
        decrypt_patient_data,
        get_patient_search_blind,
    )

    # Chiffrer pour stockage
    db_data = encrypt_patient_data(api_data, tenant_id)

    # Déchiffrer pour API
    api_data = decrypt_patient_data(db_data)

    # Recherche par blind index
    blind = get_patient_search_blind("185127510804236", "nir", tenant_id)
    patient = db.query(Patient).filter(Patient.nir_blind == blind).first()

Usage User:
    from app.services.encryption import (
        user_encryptor,
        encrypt_user_data,
        decrypt_user_data,
        get_user_search_blind,
    )

    # Chiffrer pour stockage
    db_data = encrypt_user_data({"email": "...", "rpps": "..."}, tenant_id)

    # Déchiffrer après lecture
    api_data = decrypt_user_data(user_model)

    # Recherche par blind index (email)
    blind = get_user_search_blind("marie@ssiad.fr", "email", tenant_id)
    user = db.query(User).filter(User.email_blind == blind).first()

Usage Evaluation (JSONB):
    from app.services.encryption import (
        evaluation_encryptor,
        encrypt_evaluation_data,
        decrypt_evaluation_data,
    )

    # Chiffrer evaluation_data avant stockage
    encrypted_data = encrypt_evaluation_data(raw_evaluation_data)

    # Déchiffrer après lecture
    decrypted_data = decrypt_evaluation_data(db_evaluation_data)
"""

# =============================================================================
# BASE
# =============================================================================

from app.services.encryption.base_encryptor import BaseEncryptor

# =============================================================================
# EVALUATION
# =============================================================================
from app.services.encryption.evaluation_encryptor import (
    EvaluationEncryptor,
    decrypt_evaluation_data,
    encrypt_evaluation_data,
    evaluation_encryptor,
    get_evaluation_encrypted_paths,
)

# =============================================================================
# PATIENT
# =============================================================================
from app.services.encryption.patient_encryptor import (
    PatientEncryptor,
    decrypt_patient_data,
    encrypt_patient_data,
    get_patient_search_blind,
    patient_encryptor,
)

# =============================================================================
# USER
# =============================================================================
from app.services.encryption.user_encryptor import (
    UserEncryptor,
    decrypt_user_data,
    encrypt_user_data,
    get_user_search_blind,
    user_encryptor,
)


# =============================================================================
# EXPORTS PUBLICS
# =============================================================================

__all__ = [
    # Base
    "BaseEncryptor",
    # Patient
    "PatientEncryptor",
    "patient_encryptor",
    "encrypt_patient_data",
    "decrypt_patient_data",
    "get_patient_search_blind",
    # User
    "UserEncryptor",
    "user_encryptor",
    "encrypt_user_data",
    "decrypt_user_data",
    "get_user_search_blind",
    # Evaluation
    "EvaluationEncryptor",
    "evaluation_encryptor",
    "encrypt_evaluation_data",
    "decrypt_evaluation_data",
    "get_evaluation_encrypted_paths",
]
