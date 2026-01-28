"""
Service de validation JSON Schema pour les évaluations.

Valide les documents JSON d'évaluation contre les schemas définis.
Supporte la validation complète et partielle (pendant la saisie).
"""

import json
from pathlib import Path
from functools import lru_cache
from typing import Dict, Any, List, Optional

from jsonschema import Draft202012Validator, ValidationError


# =============================================================================
# EXCEPTIONS
# =============================================================================

class SchemaValidationError(Exception):
    """Erreur de validation JSON Schema."""

    def __init__(
            self,
            message: str,
            path: Optional[str] = None,
            errors: Optional[List[Dict[str, Any]]] = None
    ):
        self.message = message
        self.path = path  # Ex: "aggir.AggirVariable[0].Resultat"
        self.errors = errors or []
        super().__init__(message)


class SchemaNotFoundError(Exception):
    """Schema JSON non trouvé."""
    pass


# =============================================================================
# SERVICE
# =============================================================================

class EvaluationSchemaValidator:
    """
    Validateur de données d'évaluation contre les JSON Schemas.

    Usage:
        validator = EvaluationSchemaValidator()

        # Validation complète (avant soumission)
        validator.validate_full("evaluation_complete", "v1", data)

        # Validation partielle (pendant saisie) - retourne les erreurs
        errors = validator.validate_partial("evaluation_complete", "v1", data)

        # Validation d'une variable AGGIR seule
        validator.validate_aggir_variable(variable_data)
    """

    # Chemin vers les schemas JSON
    SCHEMA_DIR = Path(__file__).parent.parent / "schemas" / "json_schemas"

    # Mapping type → fichier
    SCHEMA_FILES = {
        "evaluation_complete": "evaluation_{version}.json",
        "aggir_only": "aggir_only_{version}.json",
        "social_only": "social_only_{version}.json",
        "health_only": "health_only_{version}.json",
    }

    @lru_cache(maxsize=10)
    def _load_schema(self, schema_type: str, version: str) -> Dict[str, Any]:
        """
        Charge et cache un schema JSON.

        Args:
            schema_type: Type de schéma (evaluation_complete, aggir_only, etc.)
            version: Version du schéma (v1, v2, etc.)

        Returns:
            Le schema JSON parsé

        Raises:
            SchemaNotFoundError: Si le schema n'existe pas
        """
        # Normaliser en minuscules pour accepter EVALUATION_COMPLETE ou evaluation_complete
        schema_type_lower = schema_type.lower()

        template = self.SCHEMA_FILES.get(schema_type_lower)
        if not template:
            raise SchemaNotFoundError(f"Type de schéma inconnu: {schema_type}")

        filename = template.format(version=version)
        schema_path = self.SCHEMA_DIR / filename

        if not schema_path.exists():
            raise SchemaNotFoundError(f"Schema non trouvé: {schema_path}")

        with open(schema_path, encoding="utf-8") as f:
            return json.load(f)

    def validate_full(
            self,
            schema_type: str,
            version: str,
            data: Dict[str, Any]
    ) -> bool:
        """
        Validation COMPLÈTE contre le schema.

        Utilisé lors de la soumission pour validation médicale.
        Lève SchemaValidationError si invalide.

        Args:
            schema_type: Type de schéma
            version: Version du schéma
            data: Données à valider (evaluation_data)

        Returns:
            True si valide

        Raises:
            SchemaValidationError: Si les données sont invalides
        """
        schema = self._load_schema(schema_type, version)
        validator = Draft202012Validator(schema)

        errors = list(validator.iter_errors(data))

        if errors:
            # Formater les erreurs pour le retour
            formatted_errors = [
                {
                    "path": ".".join(str(p) for p in err.absolute_path),
                    "message": err.message,
                    "value": err.instance if not isinstance(err.instance, dict) else "...",
                }
                for err in errors[:10]  # Limiter à 10 erreurs
            ]

            raise SchemaValidationError(
                message=f"Validation échouée: {len(errors)} erreur(s) détectée(s)",
                errors=formatted_errors,
            )

        return True

    def validate_partial(
            self,
            schema_type: str,
            version: str,
            data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Validation PARTIELLE - retourne la liste des erreurs sans lever d'exception.

        Utilisé pendant la saisie pour feedback UI ou calcul de complétion.

        Args:
            schema_type: Type de schéma
            version: Version du schéma
            data: Données à valider

        Returns:
            Liste des erreurs (vide si tout est valide)
        """
        schema = self._load_schema(schema_type, version)
        validator = Draft202012Validator(schema)

        return [
            {
                "path": ".".join(str(p) for p in err.absolute_path),
                "message": err.message,
            }
            for err in validator.iter_errors(data)
        ]

    def validate_aggir_variable(
            self,
            variable_data: Dict[str, Any],
            schema_type: str = "evaluation_complete",
            version: str = "v1",
    ) -> bool:
        """
        Valide une seule variable AGGIR.

        Utilisé lors de la saisie incrémentale d'une variable.

        Args:
            variable_data: Données de la variable AGGIR
            schema_type: Type de schéma parent
            version: Version du schéma

        Returns:
            True si valide

        Raises:
            SchemaValidationError: Si la variable est invalide
        """
        schema = self._load_schema(schema_type, version)

        # Extraire le sous-schema pour aggirVariable
        aggir_var_schema = schema.get("$defs", {}).get("aggirVariable")

        if not aggir_var_schema:
            # Si pas de sous-schema défini, on skippe la validation
            return True

        validator = Draft202012Validator(aggir_var_schema)
        errors = list(validator.iter_errors(variable_data))

        if errors:
            raise SchemaValidationError(
                message=f"Variable AGGIR invalide: {errors[0].message}",
                path=f"aggir.AggirVariable.{variable_data.get('Code', '?')}",
            )

        return True

    def get_completion_status(
            self,
            schema_type: str,
            version: str,
            data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calcule le statut de complétion basé sur les champs requis.

        Returns:
            {
                "complete": bool,
                "percent": int,
                "missing_required": ["usager.adresse", "aggir.GIR", ...]
            }
        """
        errors = self.validate_partial(schema_type, version, data)

        # Filtrer les erreurs de type "required"
        missing = [
            err["path"] or err["message"]
            for err in errors
            if "required" in err["message"].lower()
        ]

        # Calcul simplifié du pourcentage
        # (à affiner selon la logique métier)
        total_required = 17 + 2  # 17 variables AGGIR + usager + aggir
        filled = total_required - len(missing)
        percent = max(0, min(100, int((filled / total_required) * 100)))

        return {
            "complete": len(missing) == 0,
            "percent": percent,
            "missing_required": missing,
        }


# =============================================================================
# SINGLETON
# =============================================================================

# Instance globale pour éviter de recharger les schemas
_validator_instance: Optional[EvaluationSchemaValidator] = None


def get_schema_validator() -> EvaluationSchemaValidator:
    """Retourne l'instance singleton du validateur."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = EvaluationSchemaValidator()
    return _validator_instance