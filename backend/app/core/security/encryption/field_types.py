"""
Helpers pour chiffrer/déchiffrer des types de données spéciaux.

Ce module étend les capacités de cipher.py (qui ne gère que les strings)
pour supporter des types couramment utilisés dans CareLink:
- Dates (date, datetime)
- JSON (dict, list)
- Nombres (pour certains identifiants)

Principe:
1. Sérialisation du type natif vers string
2. Chiffrement de la string
3. Stockage du ciphertext

Au déchiffrement:
1. Déchiffrement vers string
2. Désérialisation vers type natif

Usage:
    from backend.app.core.security.encryption.field_types import (
        encrypt_date, decrypt_date,
        encrypt_json, decrypt_json,
    )

    # Dates
    encrypted = encrypt_date(patient.birth_date)
    birth_date = decrypt_date(encrypted)

    # JSON
    encrypted = encrypt_json({"observations": "..."})
    data = decrypt_json(encrypted)
"""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Union

from app.core.security.cipher import decrypt_field, encrypt_field


# =============================================================================
# DATES
# =============================================================================


def encrypt_date(value: date | None) -> str | None:
    """
    Chiffre une date.

    Format de sérialisation: ISO 8601 (YYYY-MM-DD)

    Args:
        value: Date à chiffrer (ou None)

    Returns:
        Date chiffrée en base64, ou None

    Examples:
        >>> encrypt_date(date(1985, 12, 15))
        "encrypted_base64_string..."

        >>> encrypt_date(None)
        None
    """
    if value is None:
        return None

    # Sérialiser en ISO 8601
    date_str = value.isoformat()

    # Chiffrer
    return encrypt_field(date_str)


def decrypt_date(ciphertext: str | None) -> date | None:
    """
    Déchiffre une date.

    Args:
        ciphertext: Date chiffrée

    Returns:
        Date native Python, ou None

    Raises:
        ValueError: Si le format de date est invalide
    """
    if ciphertext is None or ciphertext == "":
        return None

    # Déchiffrer
    date_str = decrypt_field(ciphertext)

    if date_str is None:
        return None

    # Désérialiser depuis ISO 8601
    return date.fromisoformat(date_str)


def encrypt_datetime(value: datetime | None) -> str | None:
    """
    Chiffre un datetime.

    Format de sérialisation: ISO 8601 avec timezone

    Args:
        value: Datetime à chiffrer

    Returns:
        Datetime chiffré, ou None
    """
    if value is None:
        return None

    # Sérialiser en ISO 8601
    dt_str = value.isoformat()

    return encrypt_field(dt_str)


def decrypt_datetime(ciphertext: str | None) -> datetime | None:
    """
    Déchiffre un datetime.

    Args:
        ciphertext: Datetime chiffré

    Returns:
        Datetime natif, ou None
    """
    if ciphertext is None or ciphertext == "":
        return None

    dt_str = decrypt_field(ciphertext)

    if dt_str is None:
        return None

    return datetime.fromisoformat(dt_str)


# =============================================================================
# JSON (pour données structurées comme evaluation_data)
# =============================================================================


class EncryptionJSONEncoder(json.JSONEncoder):
    """
    Encodeur JSON personnalisé pour les types non-standard.

    Gère:
    - date, datetime
    - Decimal
    - Autres types courants
    """

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return {"__type__": "datetime", "value": obj.isoformat()}
        if isinstance(obj, date):
            return {"__type__": "date", "value": obj.isoformat()}
        if isinstance(obj, Decimal):
            return {"__type__": "decimal", "value": str(obj)}
        return super().default(obj)


def _decode_special_types(obj: Any) -> Any:
    """
    Décodeur pour les types spéciaux sérialisés par EncryptionJSONEncoder.
    """
    if isinstance(obj, dict) and "__type__" in obj:
        type_name = obj["__type__"]
        value = obj["value"]

        if type_name == "datetime":
            return datetime.fromisoformat(value)
        if type_name == "date":
            return date.fromisoformat(value)
        if type_name == "decimal":
            return Decimal(value)

    return obj


def _recursive_decode(obj: Any) -> Any:
    """
    Parcourt récursivement une structure pour décoder les types spéciaux.
    """
    if isinstance(obj, dict):
        # Vérifier si c'est un type spécial
        decoded = _decode_special_types(obj)
        if decoded is not obj:
            return decoded

        # Sinon, parcourir récursivement
        return {k: _recursive_decode(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_recursive_decode(item) for item in obj]

    return obj


def encrypt_json(value: Union[dict, list] | None) -> str | None:
    """
    Chiffre une structure JSON (dict ou list).

    Utilisé pour chiffrer des données structurées comme les observations
    dans evaluation_data.

    Args:
        value: Dict ou List à chiffrer

    Returns:
        JSON chiffré en base64, ou None

    Examples:
        >>> encrypt_json({"observations": "Patient fatigué", "score": 5})
        "encrypted_base64_string..."

        >>> encrypt_json(None)
        None
    """
    if value is None:
        return None

    # Sérialiser en JSON avec support des types spéciaux
    json_str = json.dumps(value, cls=EncryptionJSONEncoder, ensure_ascii=False)

    return encrypt_field(json_str)


def decrypt_json(ciphertext: str | None) -> Union[dict, list] | None:
    """
    Déchiffre une structure JSON.

    Args:
        ciphertext: JSON chiffré

    Returns:
        Dict ou List natif, ou None

    Raises:
        ValueError: Si le JSON est invalide
    """
    if ciphertext is None or ciphertext == "":
        return None

    json_str = decrypt_field(ciphertext)

    if json_str is None:
        return None

    # Désérialiser et décoder les types spéciaux
    obj = json.loads(json_str)
    return _recursive_decode(obj)


# =============================================================================
# CHIFFREMENT SÉLECTIF DE CHAMPS DANS UN DICT
# =============================================================================


def encrypt_dict_fields(data: dict[str, Any], fields_to_encrypt: list[str]) -> dict[str, Any]:
    """
    Chiffre sélectivement certains champs d'un dictionnaire.

    Utilisé pour chiffrer uniquement les champs texte libre dans evaluation_data
    tout en gardant les scores et statuts en clair.

    Args:
        data: Dictionnaire source
        fields_to_encrypt: Liste des clés à chiffrer

    Returns:
        Nouveau dictionnaire avec les champs spécifiés chiffrés

    Examples:
        >>> data = {"observations": "Texte sensible", "gir_score": 3}
        >>> encrypt_dict_fields(data, ["observations"])
        {"observations": "encrypted...", "gir_score": 3}
    """
    result = dict(data)  # Copie superficielle

    for field in fields_to_encrypt:
        if field in result and result[field] is not None:
            value = result[field]

            if isinstance(value, str):
                result[field] = encrypt_field(value)
            elif isinstance(value, (dict, list)):
                result[field] = encrypt_json(value)
            # Autres types: laisser en clair

    return result


def decrypt_dict_fields(data: dict[str, Any], fields_to_decrypt: list[str]) -> dict[str, Any]:
    """
    Déchiffre sélectivement certains champs d'un dictionnaire.

    Args:
        data: Dictionnaire avec champs chiffrés
        fields_to_decrypt: Liste des clés à déchiffrer

    Returns:
        Dictionnaire avec les champs spécifiés déchiffrés
    """
    result = dict(data)

    for field in fields_to_decrypt:
        if field in result and result[field] is not None:
            value = result[field]

            if isinstance(value, str):
                # Tenter de déchiffrer comme JSON d'abord
                try:
                    decrypted = decrypt_json(value)
                    if decrypted is not None:
                        result[field] = decrypted
                        continue
                except (json.JSONDecodeError, ValueError):
                    pass

                # Sinon, déchiffrer comme string simple
                result[field] = decrypt_field(value)

    return result


# =============================================================================
# CHAMPS JSONB AVEC CHIFFREMENT PARTIEL
# =============================================================================


def encrypt_jsonb_text_fields(
    jsonb_data: dict[str, Any] | None, text_field_paths: list[str]
) -> dict[str, Any] | None:
    """
    Chiffre les champs texte libre dans une structure JSONB complexe.

    Permet de chiffrer sélectivement des champs profonds dans une structure
    tout en gardant le reste en clair pour les requêtes SQL.

    Args:
        jsonb_data: Structure JSONB (ex: evaluation_data)
        text_field_paths: Chemins des champs à chiffrer (ex: ["observations", "activities.*.commentaire"])

    Returns:
        Structure avec champs texte chiffrés

    Note:
        Les chemins avec '*' indiquent une itération sur tous les éléments
        d'une liste ou d'un dict.

    Examples:
        >>> data = {
        ...     "observations": "Texte sensible",
        ...     "activities": {"toilette": {"score": 1, "commentaire": "Aide partielle"}},
        ... }
        >>> encrypt_jsonb_text_fields(data, ["observations", "activities.*.commentaire"])
        {
            "observations": "encrypted...",
            "activities": {
                "toilette": {"score": 1, "commentaire": "encrypted..."}
            }
        }
    """
    if jsonb_data is None:
        return None

    import copy

    result = copy.deepcopy(jsonb_data)

    for path in text_field_paths:
        _encrypt_path(result, path.split("."))

    return result


def decrypt_jsonb_text_fields(
    jsonb_data: dict[str, Any] | None, text_field_paths: list[str]
) -> dict[str, Any] | None:
    """
    Déchiffre les champs texte libre dans une structure JSONB.

    Inverse de encrypt_jsonb_text_fields.
    """
    if jsonb_data is None:
        return None

    import copy

    result = copy.deepcopy(jsonb_data)

    for path in text_field_paths:
        _decrypt_path(result, path.split("."))

    return result


def _encrypt_path(obj: Any, path_parts: list[str]) -> None:
    """
    Chiffre récursivement un champ selon son chemin.

    Modifie l'objet en place.
    """
    if not path_parts:
        return

    current = path_parts[0]
    remaining = path_parts[1:]

    if current == "*":
        # Itérer sur tous les éléments
        if isinstance(obj, dict):
            for key in obj:
                _encrypt_path(obj[key], remaining)
        elif isinstance(obj, list):
            for item in obj:
                _encrypt_path(item, remaining)

    elif isinstance(obj, dict) and current in obj:
        if not remaining:
            # C'est le champ final à chiffrer
            if isinstance(obj[current], str) and obj[current]:
                obj[current] = encrypt_field(obj[current])
        else:
            # Continuer la descente
            _encrypt_path(obj[current], remaining)


def _decrypt_path(obj: Any, path_parts: list[str]) -> None:
    """
    Déchiffre récursivement un champ selon son chemin.

    Modifie l'objet en place.
    """
    if not path_parts:
        return

    current = path_parts[0]
    remaining = path_parts[1:]

    if current == "*":
        if isinstance(obj, dict):
            for key in obj:
                _decrypt_path(obj[key], remaining)
        elif isinstance(obj, list):
            for item in obj:
                _decrypt_path(item, remaining)

    elif isinstance(obj, dict) and current in obj:
        if not remaining:
            # C'est le champ final à déchiffrer
            if isinstance(obj[current], str) and obj[current]:
                obj[current] = decrypt_field(obj[current])
        else:
            _decrypt_path(obj[current], remaining)
