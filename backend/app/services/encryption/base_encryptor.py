"""
Classe de base abstraite pour les services d'encryption.

Ce module définit le contrat que doivent respecter tous les encryptors
spécifiques (PatientEncryptor, UserEncryptor, EvaluationEncryptor).

Architecture:
    BaseEncryptor (abstrait)
        ├── PatientEncryptor
        ├── UserEncryptor
        └── EvaluationEncryptor

Changement v4.8 :
- Ajout validation runtime : tenant_id requis si blind_index_fields non vide
- Signature tenant_id: Optional[int] = None conservée (cas SuperAdmin sans blind index)
"""

from abc import ABC, abstractmethod
from typing import Any

from app.core.security.cipher import decrypt_field, encrypt_field
from app.core.security.encryption import (
    create_blind_index,
    decrypt_date,
    decrypt_datetime,
    encrypt_date,
    encrypt_datetime,
)


class BaseEncryptor(ABC):
    """
    Classe abstraite définissant l'interface des services d'encryption.

    Chaque encryptor spécifique doit :
    1. Définir les champs à chiffrer et leur type
    2. Définir les champs nécessitant un blind index
    3. Implémenter la logique de mapping entre noms API et noms DB

    Conventions de nommage:
    - Colonnes chiffrées en DB : {field}_encrypted (ex: first_name_encrypted)
    - Colonnes blind index : {field}_blind (ex: first_name_blind)
    - Noms API : {field} (ex: first_name)

    Types de champs supportés:
    - "string" : Texte simple
    - "date" : Date (datetime.date)
    - "datetime" : DateTime avec timezone
    """

    # À définir dans les classes enfants

    @property
    @abstractmethod
    def encrypted_fields(self) -> dict[str, str]:
        """
        Dictionnaire des champs à chiffrer.

        Format: {"nom_api": "type"}
        Types: "string", "date", "datetime"

        Example:
            {
                "first_name": "string",
                "birth_date": "date",
            }
        """

    @property
    @abstractmethod
    def blind_index_fields(self) -> set[str]:
        """
        Ensemble des champs nécessitant un blind index.

        Ces champs doivent aussi être dans encrypted_fields.

        Example:
            {"first_name", "last_name", "nir"}
        """

    # =========================================================================
    # MÉTHODES DE CHIFFREMENT
    # =========================================================================

    def encrypt_for_db(self, data: dict[str, Any], tenant_id: int | None = None) -> dict[str, Any]:
        """
        Transforme des données API en données DB (chiffrées).

        - Renomme les champs : {field} → {field}_encrypted
        - Chiffre les valeurs
        - Génère les blind indexes

        Args:
            data: Données en clair (format API)
            tenant_id: ID du tenant pour les blind indexes.
                       Requis si blind_index_fields est non vide.
                       Peut être None pour un encryptor sans blind index
                       ou dans un contexte SuperAdmin sans blind index.

        Returns:
            Données prêtes pour insertion en DB

        Raises:
            ValueError: Si tenant_id est None et qu'un blind index est requis

        Example:
            >>> encryptor.encrypt_for_db({"first_name": "Jean", "age": 65}, tenant_id=1)
            {
                "first_name_encrypted": "encrypted...",
                "first_name_blind": "8f3a2b...",
                "age": 65  # Non chiffré
            }
        """
        result = {}

        for key, value in data.items():
            if key in self.encrypted_fields:
                field_type = self.encrypted_fields[key]

                # Nom de la colonne DB
                db_column = f"{key}_encrypted"

                if value is None:
                    result[db_column] = None
                    # Mettre aussi le blind index à None si applicable
                    if key in self.blind_index_fields:
                        result[f"{key}_blind"] = None
                else:
                    # Chiffrer la valeur
                    result[db_column] = self._encrypt_value(value, field_type)

                    # Générer le blind index si configuré
                    if key in self.blind_index_fields:
                        # v4.8 : garde-fou — tenant_id requis pour blind index
                        if tenant_id is None:
                            raise ValueError(
                                f"tenant_id est requis pour générer le blind index "
                                f"du champ '{key}'. "
                                f"Appelez encrypt_for_db(data, tenant_id=...) "
                                f"avec un tenant_id valide."
                            )
                        blind_column = f"{key}_blind"
                        string_value = self._value_to_string(value, field_type)
                        result[blind_column] = create_blind_index(string_value, key, tenant_id)
            else:
                # Champ non chiffré : copier tel quel
                result[key] = value

        return result

    def decrypt_from_db(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Transforme des données DB en données API (déchiffrées).

        - Renomme les champs : {field}_encrypted → {field}
        - Déchiffre les valeurs
        - Supprime les blind indexes (données internes)

        Args:
            data: Données chiffrées (format DB)

        Returns:
            Données déchiffrées (format API)

        Example:
            >>> encryptor.decrypt_from_db(
            ...     {
            ...         "first_name_encrypted": "encrypted...",
            ...         "first_name_blind": "8f3a2b...",
            ...         "age": 65,
            ...     }
            ... )
            {"first_name": "Jean", "age": 65}
        """
        result = {}
        processed_fields = set()

        for key, value in data.items():
            # Ignorer les blind indexes
            if key.endswith("_blind"):
                continue

            # Vérifier si c'est un champ chiffré
            if key.endswith("_encrypted"):
                # Extraire le nom API
                api_name = key[:-10]  # Enlever "_encrypted"

                if api_name in self.encrypted_fields:
                    field_type = self.encrypted_fields[api_name]

                    if value is None:
                        result[api_name] = None
                    else:
                        result[api_name] = self._decrypt_value(value, field_type)

                    processed_fields.add(key)
                    continue

            # Champ non chiffré : copier tel quel
            result[key] = value

        return result

    def decrypt_model(self, model: Any) -> dict[str, Any]:
        """
        Extrait et déchiffre les champs d'un modèle SQLAlchemy.

        Utilise la convention {api_name}_encrypted pour lire les colonnes.
        Fonctionne pour tous les modèles (Patient, User, etc.) à condition
        que les colonnes suivent la convention de nommage.

        Args:
            model: Instance de modèle SQLAlchemy

        Returns:
            Dictionnaire avec les champs déchiffrés (noms API)

        Example:
            >>> decrypted = encryptor.decrypt_model(user)
            >>> decrypted["email"]  # "marie.dupont@ssiad.fr"
        """
        result = {}

        for api_name, field_type in self.encrypted_fields.items():
            db_column = f"{api_name}_encrypted"
            encrypted_value = getattr(model, db_column, None)

            if encrypted_value is None:
                result[api_name] = None
            else:
                result[api_name] = self._decrypt_value(encrypted_value, field_type)

        return result

    # =========================================================================
    # MÉTHODES DE RECHERCHE (BLIND INDEX)
    # =========================================================================

    def get_blind_index(
        self, value: Any, field_name: str, tenant_id: int | None = None
    ) -> str | None:
        """
        Génère un blind index pour une recherche.

        Args:
            value: Valeur de recherche en clair
            field_name: Nom du champ (format API, ex: "last_name")
            tenant_id: ID du tenant

        Returns:
            Blind index pour la clause WHERE

        Raises:
            ValueError: Si le champ n'a pas de blind index configuré

        Example:
            >>> blind = encryptor.get_blind_index("Dupont", "last_name")
            >>> query.filter(Patient.last_name_blind == blind)
        """
        if field_name not in self.blind_index_fields:
            raise ValueError(
                f"Le champ '{field_name}' n'a pas de blind index. "
                f"Champs disponibles: {self.blind_index_fields}"
            )

        if value is None:
            return None

        field_type = self.encrypted_fields.get(field_name, "string")
        string_value = self._value_to_string(value, field_type)

        return create_blind_index(string_value, field_name, tenant_id)

    def get_db_column_name(self, api_field: str, column_type: str = "encrypted") -> str:
        """
        Retourne le nom de colonne DB pour un champ API.

        Args:
            api_field: Nom du champ API (ex: "first_name")
            column_type: "encrypted" ou "blind"

        Returns:
            Nom de colonne DB (ex: "first_name_encrypted")
        """
        if column_type == "encrypted":
            return f"{api_field}_encrypted"
        if column_type == "blind":
            return f"{api_field}_blind"
        raise ValueError(f"Type de colonne inconnu: {column_type}")

    # =========================================================================
    # MÉTHODES UTILITAIRES
    # =========================================================================

    def get_encrypted_field_names(self) -> list[str]:
        """Liste des noms de champs chiffrés (format API)."""
        return list(self.encrypted_fields.keys())

    def get_blind_index_field_names(self) -> list[str]:
        """Liste des noms de champs avec blind index."""
        return list(self.blind_index_fields)

    def get_db_encrypted_columns(self) -> list[str]:
        """Liste des noms de colonnes DB chiffrées."""
        return [f"{f}_encrypted" for f in self.encrypted_fields.keys()]

    def get_db_blind_columns(self) -> list[str]:
        """Liste des noms de colonnes DB blind index."""
        return [f"{f}_blind" for f in self.blind_index_fields]

    # =========================================================================
    # MÉTHODES PRIVÉES
    # =========================================================================

    @staticmethod
    def _encrypt_value(value: Any, field_type: str) -> str | None:
        """Chiffre une valeur selon son type."""
        if value is None:
            return None

        if field_type == "string":
            return encrypt_field(str(value))
        if field_type == "date":
            from datetime import date

            if isinstance(value, str):
                value = date.fromisoformat(value)
            return encrypt_date(value)
        if field_type == "datetime":
            from datetime import datetime

            if isinstance(value, str):
                value = datetime.fromisoformat(value)
            return encrypt_datetime(value)
        return encrypt_field(str(value))

    @staticmethod
    def _decrypt_value(encrypted_value: str, field_type: str) -> Any:
        """Déchiffre une valeur selon son type."""
        if encrypted_value is None:
            return None

        if field_type == "string":
            return decrypt_field(encrypted_value)
        if field_type == "date":
            return decrypt_date(encrypted_value)
        if field_type == "datetime":
            return decrypt_datetime(encrypted_value)
        return decrypt_field(encrypted_value)

    @staticmethod
    def _value_to_string(value: Any, field_type: str) -> str:
        """Convertit une valeur en string pour le blind index."""
        if value is None:
            return ""

        if field_type == "date":
            from datetime import date

            if isinstance(value, date):
                return value.isoformat()
        elif field_type == "datetime":
            from datetime import datetime

            if isinstance(value, datetime):
                return value.isoformat()

        return str(value)
