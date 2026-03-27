"""
Service d'encryption spécifique pour les évaluations (JSONB).

Ce module gère le chiffrement/déchiffrement des champs texte libre
dans le JSONB `evaluation_data` des évaluations patient.

Principe:
- La STRUCTURE du JSON est préservée (clés, tableaux, imbrications)
- Seules les VALEURS des champs sensibles sont chiffrées
- Les scores, codes, dates restent en clair pour les requêtes SQL

Chemins supportés:
- Chemins simples: "usager.adresse.ligne"
- Wildcards pour tableaux: "contacts[*].personnePhysique.nomUtilise"
- Wildcards imbriqués: "sante.blocs[*].questionReponse[*].reponse"

Usage:
    from app.services.encryption import evaluation_encryptor

    # Chiffrer avant stockage
    encrypted_data = evaluation_encryptor.encrypt_evaluation_data(raw_data)

    # Déchiffrer après lecture
    decrypted_data = evaluation_encryptor.decrypt_evaluation_data(encrypted_data)
"""

import copy
from typing import Any

from app.core.security.cipher import decrypt_field, encrypt_field


# =============================================================================
# CONFIGURATION DES CHEMINS À CHIFFRER
# =============================================================================

# Liste des chemins de champs à chiffrer dans evaluation_data
# Syntaxe:
#   - "section.champ" pour un champ simple
#   - "section[*].champ" pour un champ dans chaque élément d'un tableau
#   - "section[*].sous[*].champ" pour des tableaux imbriqués

ENCRYPTED_PATHS: list[str] = [
    # =========================================================================
    # SECTION USAGER (PII direct du patient)
    # =========================================================================
    "usager.Informations d'état civil.personnePhysique.nomFamille",
    "usager.Informations d'état civil.personnePhysique.prenomsActeNaissance",
    "usager.Informations d'état civil.personnePhysique.premierPrenomActeNaissance",
    "usager.Informations d'état civil.personnePhysique.nomUtilise",
    "usager.Informations d'état civil.personnePhysique.prenomUtilise",
    "usager.Informations d'état civil.personnePhysique.dateNaissance",
    "usager.adresse.ligne",
    "usager.adresse.commentaire",
    "usager.contactInfosPersonnels.domicile",
    "usager.contactInfosPersonnels.mobile",
    "usager.contactInfosPersonnels.mail",
    # =========================================================================
    # SECTION CONTACTS (PII des tiers - tableau)
    # =========================================================================
    "contacts[*].personnePhysique.nomUtilise",
    "contacts[*].personnePhysique.prenomUtilise",
    "contacts[*].personnePhysique.dateNaissance",
    "contacts[*].adresse.ligne",
    "contacts[*].adresse.commentaire",
    "contacts[*].contactInfosPersonnels.domicile",
    "contacts[*].contactInfosPersonnels.mobile",
    "contacts[*].contactInfosPersonnels.mailMSSANTE",
    "contacts[*].contactInfosPersonnels.mailPro",
    "contacts[*].natureLien",
    # =========================================================================
    # SECTION AGGIR (Commentaires texte libre)
    # =========================================================================
    "aggir.AggirVariable[*].Commentaires",
    "aggir.AggirVariable[*].AggirSousVariable[*].Commentaires",
    # =========================================================================
    # SECTION SOCIAL (Texte libre dans questionReponse)
    # =========================================================================
    "social.blocs[*].questionReponse[*].reponse",
    # =========================================================================
    # SECTION SANTÉ (Texte libre + résultats tests)
    # =========================================================================
    "sante.blocs[*].questionReponse[*].reponse",
    "sante.blocs[*].test[*].resultat",
    "sante.blocs[*].comorbidites[*].Commentaires",
    # =========================================================================
    # SECTION DISPOSITIFS (Notes)
    # =========================================================================
    "dispositifs[*].notes",
    # =========================================================================
    # SECTION POA SOCIAL (Plans d'actions)
    # =========================================================================
    "poaSocial.problemes[*].problemePose",
    "poaSocial.problemes[*].objectifs",
    "poaSocial.problemes[*].planActions[*].detailAction",
    "poaSocial.problemes[*].critereEvaluation",
    "poaSocial.problemes[*].resultatActions",
    "poaSocial.problemes[*].message",
    # =========================================================================
    # SECTION POA SANTÉ (même structure que POA Social)
    # =========================================================================
    "poaSante.problemes[*].problemePose",
    "poaSante.problemes[*].objectifs",
    "poaSante.problemes[*].planActions[*].detailAction",
    "poaSante.problemes[*].critereEvaluation",
    "poaSante.problemes[*].resultatActions",
    "poaSante.problemes[*].message",
    # =========================================================================
    # SECTION POA AUTONOMIE
    # =========================================================================
    "poaAutonomie.actions[*].detailAction",
    "poaAutonomie.actions[*].critereEvaluation",
    "poaAutonomie.actions[*].resultatActions",
    "poaAutonomie.actions[*].message",
]


class EvaluationEncryptor:
    """
    Encryptor pour les données d'évaluation (JSONB).

    Gère le chiffrement AES-256-GCM des champs texte libre
    dans le JSON d'évaluation tout en préservant la structure.

    Exemple de transformation:

    AVANT (clair):
    {
        "usager": {
            "adresse": {
                "ligne": "12 avenue caffin",
                "codePostal": "94100"   ← Non chiffré
            }
        }
    }

    APRÈS (chiffré):
    {
        "usager": {
            "adresse": {
                "ligne": "aXY0c2RmNGVy...==",  ← Chiffré
                "codePostal": "94100"           ← Intact
            }
        }
    }
    """

    def __init__(self, encrypted_paths: list[str] | None = None):
        """
        Initialise l'encryptor avec la liste des chemins à chiffrer.

        Args:
            encrypted_paths: Liste des chemins à chiffrer.
                            Si None, utilise la liste par défaut ENCRYPTED_PATHS.
        """
        self.encrypted_paths = encrypted_paths or ENCRYPTED_PATHS
        # Parser les chemins une seule fois pour optimiser
        self._parsed_paths = [self._parse_path(p) for p in self.encrypted_paths]

    # =========================================================================
    # MÉTHODES PUBLIQUES
    # =========================================================================

    def encrypt_evaluation_data(self, data: dict[str, Any] | None) -> dict[str, Any] | None:
        """
        Chiffre les champs sensibles dans les données d'évaluation.

        Args:
            data: Données d'évaluation en clair (JSONB)

        Returns:
            Copie des données avec champs sensibles chiffrés

        Note:
            - Retourne None si data est None
            - Crée une copie profonde pour ne pas modifier l'original
            - Les champs absents ou vides sont ignorés
        """
        if data is None:
            return None

        # Copie profonde pour ne pas modifier l'original
        result = copy.deepcopy(data)

        # Appliquer le chiffrement sur chaque chemin configuré
        for parsed_path in self._parsed_paths:
            self._process_path(result, parsed_path, encrypt=True)

        return result

    def decrypt_evaluation_data(self, data: dict[str, Any] | None) -> dict[str, Any] | None:
        """
        Déchiffre les champs sensibles dans les données d'évaluation.

        Args:
            data: Données d'évaluation chiffrées (depuis DB)

        Returns:
            Copie des données avec champs sensibles déchiffrés
        """
        if data is None:
            return None

        # Copie profonde
        result = copy.deepcopy(data)

        # Appliquer le déchiffrement sur chaque chemin configuré
        for parsed_path in self._parsed_paths:
            self._process_path(result, parsed_path, encrypt=False)

        return result

    def encrypt_partial_update(
        self, update_data: dict[str, Any], paths_to_encrypt: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Chiffre une mise à jour partielle des données d'évaluation.

        Utile pour les PATCH où seules certaines sections sont mises à jour.

        Args:
            update_data: Données partielles à mettre à jour
            paths_to_encrypt: Liste spécifique de chemins à chiffrer.
                             Si None, utilise la liste complète.

        Returns:
            Données partielles avec champs sensibles chiffrés
        """
        if paths_to_encrypt:
            # Utiliser une liste personnalisée temporairement
            parsed_paths = [self._parse_path(p) for p in paths_to_encrypt]
        else:
            parsed_paths = self._parsed_paths

        result = copy.deepcopy(update_data)

        for parsed_path in parsed_paths:
            self._process_path(result, parsed_path, encrypt=True)

        return result

    def get_encrypted_paths(self) -> list[str]:
        """Retourne la liste des chemins configurés pour le chiffrement."""
        return self.encrypted_paths.copy()

    def add_encrypted_path(self, path: str) -> None:
        """
        Ajoute dynamiquement un chemin à chiffrer.

        Args:
            path: Chemin à ajouter (ex: "nouvelle_section[*].champ")
        """
        if path not in self.encrypted_paths:
            self.encrypted_paths.append(path)
            self._parsed_paths.append(self._parse_path(path))

    def remove_encrypted_path(self, path: str) -> bool:
        """
        Retire dynamiquement un chemin de la liste.

        Args:
            path: Chemin à retirer

        Returns:
            True si le chemin a été retiré, False s'il n'existait pas
        """
        if path in self.encrypted_paths:
            idx = self.encrypted_paths.index(path)
            self.encrypted_paths.pop(idx)
            self._parsed_paths.pop(idx)
            return True
        return False

    # =========================================================================
    # MÉTHODES DE PARSING DES CHEMINS
    # =========================================================================

    @staticmethod
    def _parse_path(path: str) -> list[dict[str, Any]]:
        """
        Parse un chemin en segments.

        Exemple:
            "contacts[*].personnePhysique.nomUtilise"
            →
            [
                {"key": "contacts", "is_array": True},
                {"key": "personnePhysique", "is_array": False},
                {"key": "nomUtilise", "is_array": False},
            ]
        """
        segments = []
        parts = path.split(".")

        for part in parts:
            if part.endswith("[*]"):
                # C'est un tableau avec wildcard
                key = part[:-3]  # Enlever "[*]"
                segments.append({"key": key, "is_array": True})
            else:
                segments.append({"key": part, "is_array": False})

        return segments

    # =========================================================================
    # MÉTHODES DE TRAITEMENT RÉCURSIF
    # =========================================================================

    def _process_path(
        self, data: dict[str, Any], segments: list[dict[str, Any]], encrypt: bool, depth: int = 0
    ) -> None:
        """
        Traite récursivement un chemin (chiffrement ou déchiffrement).

        Args:
            data: Dictionnaire courant
            segments: Segments du chemin parsé
            encrypt: True pour chiffrer, False pour déchiffrer
            depth: Profondeur actuelle dans le chemin
        """
        if depth >= len(segments) or data is None:
            return

        segment = segments[depth]
        key = segment["key"]
        is_array = segment["is_array"]
        is_last = depth == len(segments) - 1

        # Vérifier que la clé existe
        if not isinstance(data, dict) or key not in data:
            return

        value = data[key]

        if is_last:
            # C'est le champ final à traiter
            if is_array and isinstance(value, list):
                # Traiter chaque élément du tableau
                for i, item in enumerate(value):
                    if self._should_process(item):
                        if encrypt:
                            data[key][i] = self._encrypt_value(item)
                        else:
                            data[key][i] = self._decrypt_value(item)
            else:
                # Traiter la valeur directement
                if self._should_process(value):
                    if encrypt:
                        data[key] = self._encrypt_value(value)
                    else:
                        data[key] = self._decrypt_value(value)
        else:
            # Continuer à descendre dans la structure
            if is_array and isinstance(value, list):
                # Itérer sur chaque élément du tableau
                for item in value:
                    if isinstance(item, dict):
                        self._process_path(item, segments, encrypt, depth + 1)
            elif isinstance(value, dict):
                # Descendre dans le sous-dictionnaire
                self._process_path(value, segments, encrypt, depth + 1)

    # =========================================================================
    # MÉTHODES UTILITAIRES
    # =========================================================================

    @staticmethod
    def _should_process(value: Any) -> bool:
        """
        Détermine si une valeur doit être traitée.

        Args:
            value: Valeur à vérifier

        Returns:
            True si la valeur doit être chiffrée/déchiffrée
        """
        if value is None:
            return False
        return not (isinstance(value, str) and value.strip() == "")

    @staticmethod
    def _encrypt_value(value: Any) -> str:
        """
        Chiffre une valeur.

        Args:
            value: Valeur à chiffrer (string, int, etc.)

        Returns:
            Valeur chiffrée (string base64)
        """
        # Convertir en string si nécessaire
        str_value = str(value) if not isinstance(value, str) else value

        try:
            return encrypt_field(str_value)
        except Exception:
            # En cas d'erreur, retourner la valeur originale
            return str_value

    @staticmethod
    def _decrypt_value(encrypted_value: str) -> str:
        """
        Déchiffre une valeur.

        Args:
            encrypted_value: Valeur chiffrée (string base64)

        Returns:
            Valeur déchiffrée
        """
        if not isinstance(encrypted_value, str):
            return encrypted_value

        try:
            return decrypt_field(encrypted_value)
        except Exception:
            # Si le déchiffrement échoue, retourner la valeur telle quelle
            # (peut-être déjà en clair ou format invalide)
            return encrypted_value


# =============================================================================
# INSTANCE SINGLETON
# =============================================================================

# Instance unique pour utilisation dans les services
evaluation_encryptor = EvaluationEncryptor()


# =============================================================================
# FONCTIONS HELPER (pour imports simplifiés)
# =============================================================================


def encrypt_evaluation_data(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    Helper pour chiffrer des données d'évaluation.

    Usage:
        from app.services.encryption import encrypt_evaluation_data
        encrypted = encrypt_evaluation_data(raw_data)
    """
    return evaluation_encryptor.encrypt_evaluation_data(data)


def decrypt_evaluation_data(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    Helper pour déchiffrer des données d'évaluation.

    Usage:
        from app.services.encryption import decrypt_evaluation_data
        decrypted = decrypt_evaluation_data(db_data)
    """
    return evaluation_encryptor.decrypt_evaluation_data(data)


def get_evaluation_encrypted_paths() -> list[str]:
    """
    Retourne la liste des chemins configurés pour le chiffrement.

    Utile pour la documentation ou le debug.
    """
    return evaluation_encryptor.get_encrypted_paths()
