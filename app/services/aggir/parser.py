"""
Parser AGGIR - Conversion JSON CareLink ↔ objets AGGIR

Ce module fournit des utilitaires pour :
1. Parser le JSON d'évaluation CareLink vers les objets Variable/Adverbes
2. Convertir les résultats du calculateur vers le format JSON CareLink
3. Valider la complétude d'une évaluation AGGIR

Le format JSON CareLink pour AGGIR est :
{
    "aggir": {
        "GIR": null,  // Calculé automatiquement
        "dateValidation": null,
        "AggirVariable": [
            {
                "Nom": "Cohérence",
                "Code": "COHERENCE",
                "Resultat": "B",
                "AggirSousVariable": [
                    {
                        "Nom": "Communication",
                        "Code": "COMMUNICATION",
                        "Resultat": "B",
                        "AggirAdverbes": [
                            {"Question": "S", "Reponse": false},
                            {"Question": "T", "Reponse": true},
                            ...
                        ]
                    }
                ]
            }
        ]
    }
}
"""

from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

from app.services.aggir.calculator import (
    Variable,
    Adverbes,
    AggirCalculator,
    VARIABLE_CODE_MAPPING,
)

# =============================================================================
# CONSTANTES - Structure officielle AGGIR
# =============================================================================

# Variables discriminantes (déterminent le GIR)
VARIABLES_DISCRIMINANTES = [
    "COHERENCE",
    "ORIENTATION",
    "TOILETTE",
    "HABILLAGE",
    "ALIMENTATION",
    "ELIMINATION",
    "TRANSFERTS",
    "DEPLACEMENT_INTERIEUR",
]

# Variables illustratives (contexte, n'influencent pas le GIR)
VARIABLES_ILLUSTRATIVES = [
    "DEPLACEMENT_EXTERIEUR",
    "ALERTER",
    "CUISINE",
    "MENAGE",
    "TRANSPORTS",
    "ACHATS",
    "SUIVI_TRAITEMENT",
    "ACTIVITES_TEMPS_LIBRE",
    "GESTION",
]

# Mapping code → sous-variables
SOUS_VARIABLES = {
    "COHERENCE": ["COMMUNICATION", "COMPORTEMENT"],
    "ORIENTATION": ["TEMPS", "ESPACE"],
    "TOILETTE": ["TOILETTE_HAUT", "TOILETTE_BAS"],
    "HABILLAGE": ["HABILLAGE_HAUT", "HABILLAGE_MOYEN", "HABILLAGE_BAS"],
    "ALIMENTATION": ["SE_SERVIR", "MANGER"],
    "ELIMINATION": ["URINAIRE", "FECALE"],
}

# Nombre total de variables à évaluer (discriminantes uniquement pour le calcul)
TOTAL_VARIABLES_DISCRIMINANTES = 8
TOTAL_SOUS_VARIABLES = 17  # Pour le calcul de progression


class AggirParser:
    """
    Parser pour convertir entre le format JSON CareLink et les objets AGGIR.

    Usage:
        parser = AggirParser()

        # Parser JSON → objets
        evaluations = parser.parse_evaluation_json(evaluation_data)

        # Calculer le GIR
        calculator = AggrirCalculator()
        gir, details = calculator.calculer_gir(evaluations)

        # Mettre à jour le JSON avec le résultat
        updated_json = parser.update_json_with_gir(evaluation_data, gir, details)
    """

    def parse_evaluation_json(self, evaluation_data: Dict[str, Any]) -> Dict[Variable, Adverbes]:
        """
        Parse le JSON d'évaluation CareLink vers un dictionnaire Variable → Adverbes.

        Args:
            evaluation_data: Dictionnaire contenant la clé "aggir"

        Returns:
            Dict[Variable, Adverbes] utilisable par AggrirCalculator
        """
        result = {}

        aggir_data = evaluation_data.get("aggir", {})
        variables = aggir_data.get("AggirVariable", [])

        for var_data in variables:
            var_code = var_data.get("Code")

            # Traiter les sous-variables si présentes
            sous_variables = var_data.get("AggirSousVariable", [])

            if sous_variables:
                # Variable composée → parser les sous-variables
                for sous_var_data in sous_variables:
                    parsed = self._parse_variable_or_subvariable(sous_var_data)
                    if parsed:
                        var_enum, adverbes = parsed
                        result[var_enum] = adverbes
            else:
                # Variable simple → parser directement
                parsed = self._parse_variable_or_subvariable(var_data)
                if parsed:
                    var_enum, adverbes = parsed
                    result[var_enum] = adverbes

        return result

    def _parse_variable_or_subvariable(
            self,
            data: Dict[str, Any]
    ) -> Optional[Tuple[Variable, Adverbes]]:
        """
        Parse une variable ou sous-variable depuis le JSON.

        Args:
            data: Dictionnaire de la variable/sous-variable

        Returns:
            Tuple (Variable enum, Adverbes) ou None si données incomplètes
        """
        code = data.get("Code")
        if not code or code not in VARIABLE_CODE_MAPPING:
            return None

        adverbes_data = data.get("AggirAdverbes", [])
        if not adverbes_data or len(adverbes_data) < 4:
            return None

        # Convertir la liste d'adverbes en dictionnaire
        adverbes_dict = {}
        for adv in adverbes_data:
            question = adv.get("Question")
            reponse = adv.get("Reponse")
            if question and reponse is not None:
                adverbes_dict[question] = bool(reponse)

        # Vérifier que tous les adverbes sont présents
        if not all(k in adverbes_dict for k in ['S', 'T', 'C', 'H']):
            return None

        var_enum = VARIABLE_CODE_MAPPING[code]
        adverbes = Adverbes.from_dict(adverbes_dict)

        return var_enum, adverbes

    def calculate_completion_percent(self, evaluation_data: Dict[str, Any]) -> int:
        """
        Calcule le pourcentage de complétion de l'évaluation AGGIR.

        Basé sur les sous-variables car c'est le niveau de saisie.

        Args:
            evaluation_data: Dictionnaire contenant la clé "aggir"

        Returns:
            Pourcentage (0-100)
        """
        completed = 0

        aggir_data = evaluation_data.get("aggir", {})
        variables = aggir_data.get("AggirVariable", [])

        for var_data in variables:
            sous_variables = var_data.get("AggirSousVariable", [])

            if sous_variables:
                # Variable composée → compter les sous-variables complètes
                for sous_var_data in sous_variables:
                    if self._is_variable_complete(sous_var_data):
                        completed += 1
            else:
                # Variable simple → vérifier si complète
                if self._is_variable_complete(var_data):
                    completed += 1

        return int((completed / TOTAL_SOUS_VARIABLES) * 100)

    def _is_variable_complete(self, data: Dict[str, Any]) -> bool:
        """
        Vérifie si une variable/sous-variable est complètement renseignée.
        """
        adverbes_data = data.get("AggirAdverbes", [])
        if len(adverbes_data) < 4:
            return False

        for adv in adverbes_data:
            if adv.get("Reponse") is None:
                return False

        return True

    def get_incomplete_variables(self, evaluation_data: Dict[str, Any]) -> List[str]:
        """
        Retourne la liste des codes des variables incomplètes.

        Args:
            evaluation_data: Dictionnaire contenant la clé "aggir"

        Returns:
            Liste des codes de variables incomplètes
        """
        incomplete = []

        aggir_data = evaluation_data.get("aggir", {})
        variables = aggir_data.get("AggirVariable", [])

        for var_data in variables:
            var_code = var_data.get("Code")
            sous_variables = var_data.get("AggirSousVariable", [])

            if sous_variables:
                for sous_var_data in sous_variables:
                    if not self._is_variable_complete(sous_var_data):
                        incomplete.append(sous_var_data.get("Code"))
            else:
                if not self._is_variable_complete(var_data):
                    incomplete.append(var_code)

        return incomplete

    def update_json_with_gir(
            self,
            evaluation_data: Dict[str, Any],
            gir: int,
            details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Met à jour le JSON d'évaluation avec le GIR calculé.

        Args:
            evaluation_data: Dictionnaire d'évaluation original
            gir: Score GIR calculé (1-6)
            details: Détails du calcul retournés par calculer_gir()

        Returns:
            Dictionnaire mis à jour
        """
        result = evaluation_data.copy()

        if "aggir" not in result:
            result["aggir"] = {}

        result["aggir"]["GIR"] = gir
        result["aggir"]["dateCalcul"] = datetime.now().isoformat()
        result["aggir"]["groupeAlgorithme"] = details.get("groupe_final")
        result["aggir"]["scoreAlgorithme"] = details.get("score_final")

        # Mettre à jour les résultats des variables principales
        lettres_principales = details.get("lettres_principales", {})

        for var_data in result["aggir"].get("AggirVariable", []):
            var_code = var_data.get("Code")
            if var_code in lettres_principales:
                var_data["Resultat"] = lettres_principales[var_code]

        return result

    def update_variable_result(
            self,
            evaluation_data: Dict[str, Any],
            variable_code: str,
            adverbes: Dict[str, bool],
            recorded_at: datetime = None,
            recorded_by_user_id: int = None,
            session_id: int = None,
    ) -> Dict[str, Any]:
        """
        Met à jour une variable spécifique dans le JSON d'évaluation.

        Args:
            evaluation_data: Dictionnaire d'évaluation
            variable_code: Code de la variable à mettre à jour
            adverbes: Dict avec clés 'S', 'T', 'C', 'H' et valeurs bool
            recorded_at: Timestamp de saisie
            recorded_by_user_id: ID de l'utilisateur
            session_id: ID de la session de saisie

        Returns:
            Dictionnaire mis à jour
        """
        result = evaluation_data.copy()

        if "aggir" not in result:
            result["aggir"] = {"AggirVariable": []}

        # Calculer le résultat (A, B, C)
        adv_obj = Adverbes.from_dict(adverbes)
        resultat = adv_obj.to_letter()

        # Trouver et mettre à jour la variable
        found = False
        for var_data in result["aggir"].get("AggirVariable", []):
            # Chercher dans les sous-variables
            for sous_var in var_data.get("AggirSousVariable", []):
                if sous_var.get("Code") == variable_code:
                    self._update_variable_data(
                        sous_var, adverbes, resultat,
                        recorded_at, recorded_by_user_id, session_id
                    )
                    found = True
                    break

            # Ou directement dans la variable
            if var_data.get("Code") == variable_code:
                self._update_variable_data(
                    var_data, adverbes, resultat,
                    recorded_at, recorded_by_user_id, session_id
                )
                found = True
                break

        return result

    def _update_variable_data(
            self,
            var_data: Dict[str, Any],
            adverbes: Dict[str, bool],
            resultat: str,
            recorded_at: datetime = None,
            recorded_by_user_id: int = None,
            session_id: int = None,
    ) -> None:
        """Met à jour les données d'une variable in-place."""
        # Mettre à jour les adverbes
        adverbes_list = []
        for q in ['S', 'T', 'C', 'H']:
            adverbes_list.append({
                "Question": q,
                "Reponse": adverbes.get(q, False)
            })

        var_data["AggirAdverbes"] = adverbes_list
        var_data["Resultat"] = resultat
        var_data["Status"] = "COMPLETED"

        if recorded_at:
            var_data["RecordedAt"] = recorded_at.isoformat()
        if recorded_by_user_id:
            var_data["RecordedByUserId"] = recorded_by_user_id
        if session_id:
            var_data["SessionId"] = session_id

    def create_empty_aggir_structure(self) -> Dict[str, Any]:
        """
        Crée une structure AGGIR vide avec toutes les variables.

        Utile pour initialiser une nouvelle évaluation.

        Returns:
            Structure JSON AGGIR complète avec valeurs nulles
        """
        variables = []

        # Variables discriminantes avec sous-variables
        for var_code, sous_var_codes in SOUS_VARIABLES.items():
            var_data = {
                "Nom": self._get_variable_name(var_code),
                "Code": var_code,
                "Resultat": None,
                "Status": "PENDING",
                "AggirSousVariable": []
            }

            for sous_code in sous_var_codes:
                sous_var = {
                    "Nom": self._get_variable_name(sous_code),
                    "Code": sous_code,
                    "Resultat": None,
                    "Status": "PENDING",
                    "RecordedAt": None,
                    "RecordedByUserId": None,
                    "SessionId": None,
                    "Commentaires": "",
                    "AggirAdverbes": [
                        {"Question": "S", "Reponse": None},
                        {"Question": "T", "Reponse": None},
                        {"Question": "C", "Reponse": None},
                        {"Question": "H", "Reponse": None},
                    ]
                }
                var_data["AggirSousVariable"].append(sous_var)

            variables.append(var_data)

        # Variables simples discriminantes
        for var_code in ["TRANSFERTS", "DEPLACEMENT_INTERIEUR"]:
            var_data = self._create_simple_variable(var_code)
            variables.append(var_data)

        # Variables illustratives
        for var_code in VARIABLES_ILLUSTRATIVES:
            var_data = self._create_simple_variable(var_code)
            variables.append(var_data)

        return {
            "GIR": None,
            "dateValidation": None,
            "dateCalcul": None,
            "groupeAlgorithme": None,
            "scoreAlgorithme": None,
            "AggirVariable": variables
        }

    def _create_simple_variable(self, var_code: str) -> Dict[str, Any]:
        """Crée une variable simple (sans sous-variables)."""
        return {
            "Nom": self._get_variable_name(var_code),
            "Code": var_code,
            "Resultat": None,
            "Status": "PENDING",
            "RecordedAt": None,
            "RecordedByUserId": None,
            "SessionId": None,
            "Commentaires": "",
            "AggirAdverbes": [
                {"Question": "S", "Reponse": None},
                {"Question": "T", "Reponse": None},
                {"Question": "C", "Reponse": None},
                {"Question": "H", "Reponse": None},
            ]
        }

    def _get_variable_name(self, code: str) -> str:
        """Retourne le nom lisible d'une variable depuis son code."""
        names = {
            # Variables principales
            "COHERENCE": "Cohérence",
            "ORIENTATION": "Orientation",
            "TOILETTE": "Toilette",
            "HABILLAGE": "Habillage",
            "ALIMENTATION": "Alimentation",
            "ELIMINATION": "Élimination",
            "TRANSFERTS": "Transferts",
            "DEPLACEMENT_INTERIEUR": "Déplacements à l'intérieur",
            "DEPLACEMENT_EXTERIEUR": "Déplacements à l'extérieur",
            "ALERTER": "Alerter",
            # Variables illustratives
            "CUISINE": "Cuisine",
            "MENAGE": "Ménage",
            "TRANSPORTS": "Transports",
            "ACHATS": "Achats",
            "SUIVI_TRAITEMENT": "Suivi du traitement",
            "ACTIVITES_TEMPS_LIBRE": "Activités du temps libre",
            "GESTION": "Gestion",
            # Sous-variables
            "COMMUNICATION": "Communication",
            "COMPORTEMENT": "Comportement",
            "TEMPS": "Temps",
            "ESPACE": "Espace",
            "TOILETTE_HAUT": "Toilette du haut",
            "TOILETTE_BAS": "Toilette du bas",
            "HABILLAGE_HAUT": "Habillage du haut",
            "HABILLAGE_MOYEN": "Habillage du moyen",
            "HABILLAGE_BAS": "Habillage du bas",
            "SE_SERVIR": "Se servir",
            "MANGER": "Manger",
            "URINAIRE": "Élimination urinaire",
            "FECALE": "Élimination fécale",
        }
        return names.get(code, code)


def calculate_gir_from_json(evaluation_data: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """
    Fonction utilitaire pour calculer le GIR directement depuis le JSON.

    Args:
        evaluation_data: Dictionnaire contenant la clé "aggir"

    Returns:
        Tuple (GIR, détails)
    """
    parser = AggirParser()
    calculator = AggirCalculator()

    evaluations = parser.parse_evaluation_json(evaluation_data)
    return calculator.calculer_gir(evaluations)