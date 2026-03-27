"""
Service d'encryption spécifique pour le modèle Patient.

Ce module gère le chiffrement/déchiffrement des données personnelles
des patients conformément aux exigences RGPD et HDS.

Champs chiffrés (RGPD Art. 9 - données sensibles):
- nir : Numéro de Sécurité Sociale (identifiant national)
- ins : Identifiant National de Santé
- first_name, last_name : Identification directe
- birth_date : Avec le nom, permet l'identification
- address : Localisation du domicile
- phone, email : Coordonnées de contact

Blind indexes (pour recherche sans déchiffrement):
- nir : Recherche de doublons, identification
- ins : Recherche inter-systèmes
- first_name, last_name : Recherche par nom

Usage:
    from app.services.encryption import patient_encryptor

    # Création d'un patient
    api_data = {"first_name": "Jean", "last_name": "Dupont", "nir": "185127510804236"}
    db_data = patient_encryptor.encrypt_for_db(api_data)
    patient = Patient(**db_data)

    # Lecture d'un patient
    decrypted = patient_encryptor.decrypt_model(patient)

    # Recherche par NIR
    blind = patient_encryptor.get_blind_index("185127510804236", "nir")
    patient = db.query(Patient).filter(Patient.nir_blind == blind).first()
"""

from typing import Any

from app.services.encryption.base_encryptor import BaseEncryptor


class PatientEncryptor(BaseEncryptor):
    """
    Encryptor pour le modèle Patient.

    Gère le chiffrement AES-256-GCM et les blind indexes HMAC-SHA256
    pour toutes les données personnelles des patients.

    Mapping des champs:

    | Champ API    | Colonne DB              | Blind Index        | Type     |
    |--------------|-------------------------|--------------------|----------|
    | nir          | nir_encrypted           | nir_blind          | string   |
    | ins          | ins_encrypted           | ins_blind          | string   |
    | first_name   | first_name_encrypted    | first_name_blind   | string   |
    | last_name    | last_name_encrypted     | last_name_blind    | string   |
    | birth_date   | birth_date_encrypted    | -                  | date     |
    | address      | address_encrypted       | -                  | string   |
    | phone        | phone_encrypted         | -                  | string   |
    | email        | email_encrypted         | -                  | string   |
    """

    @property
    def encrypted_fields(self) -> dict[str, str]:
        """
        Définition des champs à chiffrer pour Patient.

        Tous ces champs sont des données personnelles (PII) au sens RGPD.
        """
        return {
            # Identifiants nationaux (Article 9 RGPD - données sensibles)
            "nir": "string",  # N° Sécurité Sociale
            "ins": "string",  # Identifiant National de Santé
            # Identification directe
            "first_name": "string",
            "last_name": "string",
            # Date de naissance (permet identification avec le nom)
            "birth_date": "date",
            # Coordonnées
            "address": "string",
            "postal_code": "string",
            "city": "string",
            "phone": "string",
            "email": "string",
        }

    @property
    def blind_index_fields(self) -> set[str]:
        """
        Champs nécessitant un blind index pour la recherche.

        Critères de sélection:
        - Recherche fréquente (lookup)
        - Détection de doublons
        - Identification inter-systèmes

        Non inclus (pas de recherche directe):
        - birth_date : Rarement recherché seul
        - address : Trop variable, recherche géo via lat/long
        - phone, email : Rarement utilisés comme critère principal
        """
        return {
            "nir",  # Recherche doublons, identification SS
            "ins",  # Recherche inter-systèmes santé
            "first_name",  # Recherche par nom
            "last_name",  # Recherche par nom
        }

    # =========================================================================
    # MÉTHODES SPÉCIFIQUES PATIENT
    # =========================================================================

    def encrypt_patient_data(
        self, data: dict[str, Any], tenant_id: int | None = None
    ) -> dict[str, Any]:
        """
        Alias sémantique pour encrypt_for_db.

        Chiffre les données patient pour stockage en base.

        Args:
            data: Données patient en clair (depuis l'API)
            tenant_id: ID du tenant pour isolation des blind indexes

        Returns:
            Données prêtes pour insertion dans Patient
        """
        return self.encrypt_for_db(data, tenant_id)

    def decrypt_patient_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Alias sémantique pour decrypt_from_db.

        Déchiffre les données patient depuis la base.

        Args:
            data: Données chiffrées (depuis la DB)

        Returns:
            Données déchiffrées pour l'API
        """
        return self.decrypt_from_db(data)

    def search_by_nir(self, nir: str, tenant_id: int | None = None) -> str:
        """
        Génère le blind index pour recherche par NIR.

        Le NIR est normalisé (espaces supprimés) avant hachage.

        Args:
            nir: Numéro de Sécurité Sociale (avec ou sans espaces)
            tenant_id: ID du tenant

        Returns:
            Blind index pour clause WHERE

        Example:
            >>> blind = encryptor.search_by_nir("1 85 12 75 108 042 36")
            >>> patient = db.query(Patient).filter(Patient.nir_blind == blind).first()
        """
        return self.get_blind_index(nir, "nir", tenant_id)

    def search_by_ins(self, ins: str, tenant_id: int | None = None) -> str:
        """
        Génère le blind index pour recherche par INS.

        Args:
            ins: Identifiant National de Santé
            tenant_id: ID du tenant

        Returns:
            Blind index pour clause WHERE
        """
        return self.get_blind_index(ins, "ins", tenant_id)

    def search_by_name(
        self,
        last_name: str | None = None,
        first_name: str | None = None,
        tenant_id: int | None = None,
    ) -> dict[str, str | None]:
        """
        Génère les blind indexes pour recherche par nom.

        Args:
            last_name: Nom de famille (optionnel)
            first_name: Prénom (optionnel)
            tenant_id: ID du tenant

        Returns:
            Dict avec les blind indexes générés

        Example:
            >>> blinds = encryptor.search_by_name(last_name="Dupont")
            >>> query.filter(Patient.last_name_blind == blinds["last_name"])
        """
        result = {}

        if last_name:
            result["last_name"] = self.get_blind_index(last_name, "last_name", tenant_id)

        if first_name:
            result["first_name"] = self.get_blind_index(first_name, "first_name", tenant_id)

        return result

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
            >>> update = {"phone": "0612345678"}
            >>> db_update = encryptor.prepare_for_update(update)
            >>> # {"phone_encrypted": "encrypted..."}
        """
        # encrypt_for_db gère déjà les champs partiels
        return self.encrypt_for_db(update_data, tenant_id)

    def is_duplicate_nir(self, nir: str, existing_blind: str, tenant_id: int | None = None) -> bool:
        """
        Vérifie si un NIR correspond à un blind index existant.

        Utile pour vérifier les doublons sans exposer les données.

        Args:
            nir: NIR à vérifier
            existing_blind: Blind index d'un patient existant
            tenant_id: ID du tenant

        Returns:
            True si c'est le même NIR
        """
        computed = self.get_blind_index(nir, "nir", tenant_id)
        return computed == existing_blind


# =============================================================================
# INSTANCE SINGLETON
# =============================================================================

# Instance unique pour utilisation dans les services
patient_encryptor = PatientEncryptor()


# =============================================================================
# FONCTIONS HELPER (pour imports simplifiés)
# =============================================================================


def encrypt_patient_data(data: dict[str, Any], tenant_id: int | None = None) -> dict[str, Any]:
    """
    Helper pour chiffrer des données patient.

    Usage:
        from app.services.encryption import encrypt_patient_data
        db_data = encrypt_patient_data(api_data)
    """
    return patient_encryptor.encrypt_for_db(data, tenant_id)


def decrypt_patient_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Helper pour déchiffrer des données patient.

    Usage:
        from app.services.encryption import decrypt_patient_data
        api_data = decrypt_patient_data(db_data)
    """
    return patient_encryptor.decrypt_from_db(data)


def get_patient_search_blind(value: str, field: str, tenant_id: int | None = None) -> str:
    """
    Helper pour générer un blind index de recherche.

    Usage:
        from app.services.encryption import get_patient_search_blind
        blind = get_patient_search_blind("185127510804236", "nir")
    """
    return patient_encryptor.get_blind_index(value, field, tenant_id)
