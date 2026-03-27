"""
Génération de blind indexes pour recherche sur données chiffrées.

Un blind index est une empreinte (hash) d'une valeur qui permet de faire
des recherches SQL sans exposer la valeur en clair.

Principe:
1. Donnée en clair: "DUPONT"
2. Blind index: HMAC-SHA256("dupont") = "8f3a2b..."
3. Recherche SQL: WHERE last_name_blind = '8f3a2b...'

Avantages:
- Recherche performante via index SQL standard
- Pas de fuite d'information (HMAC irréversible)
- Conforme RGPD (donnée pseudonymisée)

Usage:
    from backend.app.core.security.encryption.blind_index import create_blind_index

    # Stockage
    blind = create_blind_index("DUPONT", "last_name")

    # Recherche
    search_blind = create_blind_index(search_term, "last_name")
    query.filter(Patient.last_name_blind == search_blind)
"""

import hashlib
import hmac
import re
import unicodedata

from app.core.security.encryption.key_manager import get_key_manager


def normalize_value(value: str, field_name: str) -> str:
    """
    Normalise une valeur avant création du blind index.

    La normalisation garantit que les recherches fonctionnent
    indépendamment des variations de saisie (majuscules, accents, espaces).

    Règles appliquées:
    1. Conversion en minuscules
    2. Suppression des accents (é → e, ç → c)
    3. Suppression des espaces en début/fin
    4. Normalisation des espaces internes (plusieurs → un seul)
    5. Règles spécifiques selon le type de champ

    Args:
        value: Valeur originale
        field_name: Nom du champ (pour règles spécifiques)

    Returns:
        Valeur normalisée

    Examples:
        >>> normalize_value("  DUPONT  ", "last_name")
        "dupont"
        >>> normalize_value("Jean-Pierre", "first_name")
        "jean-pierre"
        >>> normalize_value("1 85 12 75 108 042 36", "nir")
        "185127510804236"
    """
    if not value:
        return ""

    # 1. Suppression des espaces en début/fin
    result = value.strip()

    # 2. Conversion en minuscules
    result = result.lower()

    # 3. Suppression des accents (NFD décompose, puis on enlève les diacritiques)
    result = unicodedata.normalize("NFD", result)
    result = "".join(
        char
        for char in result
        if unicodedata.category(char) != "Mn"  # Mn = Mark, Nonspacing (accents)
    )

    # 4. Règles spécifiques selon le champ
    if field_name in ("nir", "ins", "rpps", "phone"):
        # Pour les identifiants numériques: garder uniquement les chiffres
        result = re.sub(r"[^0-9]", "", result)

    elif field_name in ("first_name", "last_name"):
        # Pour les noms: normaliser les espaces, garder tirets et apostrophes
        result = re.sub(r"\s+", " ", result)  # Plusieurs espaces → un seul
        # Garder les caractères alphabétiques, espaces, tirets, apostrophes
        result = re.sub(r"[^a-z \-']", "", result)

    elif field_name == "email":
        # Pour les emails: tout en minuscules, pas d'espaces
        result = result.replace(" ", "")

    else:
        # Par défaut: normaliser les espaces
        result = re.sub(r"\s+", " ", result)

    return result


def create_blind_index(
    value: str | None, field_name: str, tenant_id: int | None = None
) -> str | None:
    """
    Crée un blind index (empreinte) pour une valeur.

    Le blind index permet de rechercher des données chiffrées
    sans les déchiffrer, via une empreinte HMAC-SHA256.

    Args:
        value: Valeur en clair à indexer
        field_name: Nom du champ (utilisé pour normalisation et contexte)
        tenant_id: ID du tenant (pour clé par tenant en Phase 2)

    Returns:
        Empreinte hexadécimale de 64 caractères, ou None si valeur vide

    Security:
        - HMAC (pas SHA256 simple) empêche les rainbow tables
        - Clé dérivée séparée de la clé de chiffrement
        - Normalisation empêche les variations de révéler des infos

    Examples:
        >>> create_blind_index("DUPONT", "last_name")
        "8f3a2b4c5d6e7f..."  # 64 caractères hex

        >>> create_blind_index(None, "last_name")
        None
    """
    if value is None or value == "":
        return None

    # Normaliser la valeur
    normalized = normalize_value(value, field_name)

    if not normalized:
        return None

    # Récupérer la clé de blind index
    key_manager = get_key_manager()
    blind_key = key_manager.get_blind_index_key(tenant_id)

    # Créer le message avec contexte du champ
    # Le contexte empêche les collisions entre champs différents
    # (même valeur dans deux champs = deux blind indexes différents)
    message = f"{field_name}:{normalized}".encode()

    # Calculer HMAC-SHA256
    digest = hmac.new(key=blind_key, msg=message, digestmod=hashlib.sha256).hexdigest()

    return digest


def create_blind_index_for_search(
    search_value: str, field_name: str, tenant_id: int | None = None
) -> str | None:
    """
    Crée un blind index pour une recherche.

    Alias sémantique de create_blind_index, utilisé dans le code de recherche
    pour plus de clarté.

    Args:
        search_value: Terme de recherche
        field_name: Champ à rechercher
        tenant_id: ID du tenant

    Returns:
        Blind index pour la comparaison SQL

    Usage:
        # Dans le service de recherche
        blind = create_blind_index_for_search(search_nir, "nir")
        query = query.filter(Patient.nir_blind == blind)
    """
    return create_blind_index(search_value, field_name, tenant_id)


def verify_blind_index(
    value: str, stored_blind: str, field_name: str, tenant_id: int | None = None
) -> bool:
    """
    Vérifie qu'une valeur correspond à un blind index stocké.

    Utile pour validation sans requête SQL.

    Args:
        value: Valeur en clair à vérifier
        stored_blind: Blind index stocké en base
        field_name: Nom du champ
        tenant_id: ID du tenant

    Returns:
        True si la valeur correspond au blind index

    Examples:
        >>> verify_blind_index("DUPONT", stored_blind, "last_name")
        True  # si stored_blind a été créé avec "Dupont" ou "DUPONT"
    """
    computed = create_blind_index(value, field_name, tenant_id)

    if computed is None or stored_blind is None:
        return computed == stored_blind

    # Comparaison en temps constant pour éviter les timing attacks
    return hmac.compare_digest(computed, stored_blind)
