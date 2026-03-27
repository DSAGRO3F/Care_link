"""
Mixins réutilisables pour les modèles SQLAlchemy.

Ce module définit des mixins qui ajoutent des fonctionnalités communes
à plusieurs modèles (timestamps, audit, versioning, chiffrement).
"""

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

# Imports pour le chiffrement
from app.core.security.cipher import decrypt_field, encrypt_field
from app.core.security.encryption import (
    create_blind_index,
    decrypt_date,
    decrypt_datetime,
    encrypt_date,
    encrypt_datetime,
)


if TYPE_CHECKING:
    pass


class TimestampMixin:
    """
    Mixin ajoutant les colonnes created_at et updated_at.

    - created_at : auto-rempli à la création
    - updated_at : auto-mis à jour à chaque modification

    Usage:
        class MyModel(TimestampMixin, Base):
            __tablename__ = "my_table"
            id: Mapped[int] = mapped_column(primary_key=True)
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # <-- TIMESTAMP WITH TIME ZONE
        default=datetime.now(UTC),
        doc="Date et heure de création",
        info={"description": "Timestamp de création", "auto_generated": True},
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),  # <-- TIMESTAMP WITH TIME ZONE
        default=None,
        onupdate=datetime.now(UTC),
        doc="Date et heure de dernière modification",
        info={"description": "Timestamp de mise à jour", "auto_generated": True},
    )


class AuditMixin:
    """
    Mixin ajoutant les colonnes created_by et updated_by.

    Permet de tracer quel utilisateur a créé/modifié un enregistrement.

    Usage:
        class MyModel(AuditMixin, Base):
            __tablename__ = "my_table"
            id: Mapped[int] = mapped_column(primary_key=True)
    """

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID de l'utilisateur ayant créé l'enregistrement",
        info={"description": "Référence vers le créateur"},
    )

    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID de l'utilisateur ayant modifié l'enregistrement",
        info={"description": "Référence vers le modificateur"},
    )


class VersionedMixin:
    """
    Mixin ajoutant une colonne de version pour le verrouillage optimiste.

    La colonne `version` doit être incrémentée manuellement ou via
    un trigger lors des modifications. Pour activer le verrouillage
    optimiste automatique de SQLAlchemy, ajoutez dans votre modèle :

        __mapper_args__ = {"version_id_col": __table__.c.version}

    Usage:
        class MyModel(VersionedMixin, Base):
            __tablename__ = "my_table"
            id: Mapped[int] = mapped_column(primary_key=True)

    Note: Pour une implémentation complète de l'optimistic locking en
    production, utilisez les events SQLAlchemy ou configurez version_id_col
    au niveau du modèle individuel.
    """

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Version pour verrouillage optimiste",
        info={"description": "Incrémenté à chaque modification", "auto_generated": True},
    )


class StatusMixin:
    """
    Mixin ajoutant une colonne status.

    Usage:
        class MyModel(StatusMixin, Base):
            __tablename__ = "my_table"
            id: Mapped[int] = mapped_column(primary_key=True)
    """

    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        doc="Statut de l'enregistrement",
        info={"description": "active, inactive, archived, etc.", "default": "active"},
    )


# =============================================================================
# ENCRYPTED FIELDS MIXIN
# =============================================================================


class EncryptedFieldsMixin:
    """
    Mixin pour gérer le chiffrement/déchiffrement des champs sensibles.

    Ce mixin fournit une infrastructure réutilisable pour chiffrer les données
    personnelles (RGPD) dans les modèles SQLAlchemy.

    Configuration dans le modèle enfant:
    ------------------------------------

    Définir les attributs de classe suivants :

    - __encrypted_fields__ : Dict des champs à chiffrer
      Format: {"nom_champ": "type"}
      Types supportés: "string", "date", "datetime"

    - __blind_index_fields__ : Set des champs nécessitant un blind index
      Ces champs doivent avoir une colonne correspondante "{field}_blind"

    Exemple d'implémentation:
    -------------------------

        class Patient(EncryptedFieldsMixin, Base):
            __tablename__ = "patients"

            # Configuration du chiffrement
            __encrypted_fields__ = {
                "first_name": "string",
                "last_name": "string",
                "nir": "string",
                "birth_date": "date",
            }
            __blind_index_fields__ = {"first_name", "last_name", "nir"}

            # Colonnes stockées (chiffrées)
            id: Mapped[int] = mapped_column(primary_key=True)
            first_name: Mapped[str | None]      # Stocke la valeur chiffrée
            last_name: Mapped[str | None]       # Stocke la valeur chiffrée
            nir: Mapped[str | None]             # Stocke la valeur chiffrée
            birth_date: Mapped[str | None]      # Date chiffrée (stockée comme string)

            # Blind indexes pour recherche
            first_name_blind: Mapped[str | None]
            last_name_blind: Mapped[str | None]
            nir_blind: Mapped[str | None]

    Usage dans les services:
    ------------------------

        # Création avec chiffrement
        patient_data = {"first_name": "Jean", "last_name": "Dupont", ...}
        encrypted_data = Patient.encrypt_fields(patient_data)
        patient = Patient(**encrypted_data)

        # Lecture avec déchiffrement
        decrypted = patient.get_decrypted_fields()
        # → {"first_name": "Jean", "last_name": "Dupont", ...}

        # Recherche par blind index
        blind = Patient.get_blind_index("Dupont", "last_name")
        query.filter(Patient.last_name_blind == blind)

    Sécurité:
    ---------

    - Chiffrement AES-256-GCM (confidentialité + intégrité)
    - Blind indexes HMAC-SHA256 (recherche sans déchiffrement)
    - Clés dérivées séparées pour chiffrement et blind index
    """

    # À surcharger dans les classes enfants
    __encrypted_fields__: dict[str, str] = {}
    __blind_index_fields__: set[str] = set()

    # =========================================================================
    # MÉTHODES DE CLASSE (pour chiffrement avant création)
    # =========================================================================

    @classmethod
    def encrypt_fields(cls, data: dict[str, Any], tenant_id: int | None = None) -> dict[str, Any]:
        """
        Chiffre les champs sensibles d'un dictionnaire de données.

        Utilisé avant la création ou mise à jour d'un enregistrement.
        Génère également les blind indexes pour les champs configurés.

        Args:
            data: Dictionnaire des données en clair
            tenant_id: ID du tenant (pour clé par tenant, Phase 2)

        Returns:
            Nouveau dictionnaire avec:
            - Champs sensibles chiffrés
            - Blind indexes générés (clés "{field}_blind")

        Example:
            >>> data = {"first_name": "Jean", "last_name": "Dupont", "age": 65}
            >>> Patient.encrypt_fields(data)
            {
                "first_name": "encrypted...",
                "last_name": "encrypted...",
                "first_name_blind": "8f3a2b...",
                "last_name_blind": "c4d5e6...",
                "age": 65  # Non chiffré (pas dans __encrypted_fields__)
            }
        """
        result = dict(data)  # Copie pour ne pas modifier l'original

        for field_name, field_type in cls.__encrypted_fields__.items():
            if field_name not in result:
                continue

            value = result[field_name]

            if value is None:
                # Garder None, pas de blind index
                continue

            # Chiffrer selon le type
            encrypted_value = cls._encrypt_value(value, field_type)
            result[field_name] = encrypted_value

            # Générer le blind index si configuré
            if field_name in cls.__blind_index_fields__:
                blind_key = f"{field_name}_blind"
                # Le blind index utilise la valeur EN CLAIR (avant chiffrement)
                result[blind_key] = create_blind_index(
                    cls._value_to_string(value, field_type), field_name, tenant_id
                )

        return result

    @classmethod
    def decrypt_fields(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Déchiffre les champs sensibles d'un dictionnaire de données.

        Args:
            data: Dictionnaire avec champs chiffrés

        Returns:
            Nouveau dictionnaire avec champs déchiffrés
        """
        result = dict(data)

        for field_name, field_type in cls.__encrypted_fields__.items():
            if field_name not in result:
                continue

            value = result[field_name]

            if value is None:
                continue

            result[field_name] = cls._decrypt_value(value, field_type)

        return result

    @classmethod
    def get_blind_index(
        cls, value: Any, field_name: str, tenant_id: int | None = None
    ) -> str | None:
        """
        Génère un blind index pour une valeur de recherche.

        Utilisé pour construire des requêtes SQL sur les champs chiffrés.

        Args:
            value: Valeur de recherche en clair
            field_name: Nom du champ à rechercher
            tenant_id: ID du tenant

        Returns:
            Blind index (hash HMAC-SHA256)

        Example:
            >>> blind = Patient.get_blind_index("Dupont", "last_name")
            >>> query.filter(Patient.last_name_blind == blind)
        """
        if field_name not in cls.__blind_index_fields__:
            raise ValueError(
                f"Le champ '{field_name}' n'a pas de blind index configuré. "
                f"Champs disponibles: {cls.__blind_index_fields__}"
            )

        # Déterminer le type du champ
        field_type = cls.__encrypted_fields__.get(field_name, "string")

        # Convertir en string pour le blind index
        string_value = cls._value_to_string(value, field_type)

        return create_blind_index(string_value, field_name, tenant_id)

    @classmethod
    def get_encrypted_field_names(cls) -> list[str]:
        """Retourne la liste des noms de champs chiffrés."""
        return list(cls.__encrypted_fields__.keys())

    @classmethod
    def get_blind_index_field_names(cls) -> list[str]:
        """Retourne la liste des noms de champs avec blind index."""
        return list(cls.__blind_index_fields__)

    # =========================================================================
    # MÉTHODES D'INSTANCE (pour déchiffrement après lecture)
    # =========================================================================

    def get_decrypted_fields(self) -> dict[str, Any]:
        """
        Retourne tous les champs chiffrés sous forme déchiffrée.

        Returns:
            Dict avec les valeurs déchiffrées

        Example:
            >>> patient = db.query(Patient).first()
            >>> patient.get_decrypted_fields()
            {"first_name": "Jean", "last_name": "Dupont", "birth_date": date(1958, 5, 12)}
        """
        result = {}

        for field_name, field_type in self.__encrypted_fields__.items():
            encrypted_value = getattr(self, field_name, None)

            if encrypted_value is None:
                result[field_name] = None
            else:
                result[field_name] = self._decrypt_value(encrypted_value, field_type)

        return result

    def get_decrypted_field(self, field_name: str) -> Any:
        """
        Retourne un champ spécifique déchiffré.

        Args:
            field_name: Nom du champ à déchiffrer

        Returns:
            Valeur déchiffrée

        Raises:
            ValueError: Si le champ n'est pas configuré comme chiffré
        """
        if field_name not in self.__encrypted_fields__:
            raise ValueError(
                f"Le champ '{field_name}' n'est pas configuré comme chiffré. "
                f"Champs disponibles: {list(self.__encrypted_fields__.keys())}"
            )

        field_type = self.__encrypted_fields__[field_name]
        encrypted_value = getattr(self, field_name, None)

        if encrypted_value is None:
            return None

        return self._decrypt_value(encrypted_value, field_type)

    def set_encrypted_field(
        self, field_name: str, value: Any, tenant_id: int | None = None
    ) -> None:
        """
        Définit un champ avec chiffrement automatique.

        Met également à jour le blind index si configuré.

        Args:
            field_name: Nom du champ
            value: Valeur en clair
            tenant_id: ID du tenant
        """
        if field_name not in self.__encrypted_fields__:
            raise ValueError(f"Le champ '{field_name}' n'est pas configuré comme chiffré.")

        field_type = self.__encrypted_fields__[field_name]

        if value is None:
            setattr(self, field_name, None)
            if field_name in self.__blind_index_fields__:
                setattr(self, f"{field_name}_blind", None)
            return

        # Chiffrer et assigner
        encrypted = self._encrypt_value(value, field_type)
        setattr(self, field_name, encrypted)

        # Mettre à jour le blind index si configuré
        if field_name in self.__blind_index_fields__:
            string_value = self._value_to_string(value, field_type)
            blind = create_blind_index(string_value, field_name, tenant_id)
            setattr(self, f"{field_name}_blind", blind)

    def to_dict_decrypted(
        self, include_fields: list[str] | None = None, exclude_fields: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Convertit l'instance en dictionnaire avec déchiffrement automatique.

        Pratique pour la sérialisation vers l'API.

        Args:
            include_fields: Liste des champs à inclure (tous si None)
            exclude_fields: Liste des champs à exclure

        Returns:
            Dictionnaire avec champs chiffrés déchiffrés
        """
        exclude_fields = exclude_fields or []

        # Récupérer tous les attributs de l'instance
        result = {}

        for key in dir(self):
            # Ignorer les attributs privés et méthodes
            if key.startswith("_"):
                continue
            if callable(getattr(self, key)):
                continue
            # Ignorer les blind indexes (données internes)
            if key.endswith("_blind"):
                continue
            # Appliquer les filtres
            if include_fields and key not in include_fields:
                continue
            if key in exclude_fields:
                continue

            value = getattr(self, key)

            # Déchiffrer si c'est un champ chiffré
            if key in self.__encrypted_fields__:
                field_type = self.__encrypted_fields__[key]
                if value is not None:
                    value = self._decrypt_value(value, field_type)

            result[key] = value

        return result

    # =========================================================================
    # MÉTHODES PRIVÉES (helpers internes)
    # =========================================================================

    @staticmethod
    def _encrypt_value(value: Any, field_type: str) -> str | None:
        """
        Chiffre une valeur selon son type.

        Args:
            value: Valeur en clair
            field_type: Type du champ ("string", "date", "datetime")

        Returns:
            Valeur chiffrée (toujours string pour stockage)
        """
        if value is None:
            return None

        if field_type == "string":
            return encrypt_field(str(value))

        if field_type == "date":
            if isinstance(value, str):
                # Conversion string ISO → date
                value = date.fromisoformat(value)
            return encrypt_date(value)

        if field_type == "datetime":
            if isinstance(value, str):
                value = datetime.fromisoformat(value)
            return encrypt_datetime(value)

        # Type inconnu, traiter comme string
        return encrypt_field(str(value))

    @staticmethod
    def _decrypt_value(encrypted_value: str, field_type: str) -> Any:
        """
        Déchiffre une valeur selon son type.

        Args:
            encrypted_value: Valeur chiffrée
            field_type: Type du champ

        Returns:
            Valeur déchiffrée dans son type natif
        """
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
        """
        Convertit une valeur en string pour le blind index.

        La normalisation est ensuite appliquée par create_blind_index().

        Args:
            value: Valeur à convertir
            field_type: Type du champ

        Returns:
            Représentation string de la valeur
        """
        if value is None:
            return ""

        if field_type == "date":
            if isinstance(value, date):
                return value.isoformat()
            return str(value)

        if field_type == "datetime":
            if isinstance(value, datetime):
                return value.isoformat()
            return str(value)

        return str(value)
