"""
Calculateur AGGIR (Autonomie Gérontologique Groupes Iso-Ressources)

Ce module implémente l'algorithme officiel de calcul du GIR (Groupe Iso-Ressources)
pour l'évaluation de la dépendance des personnes âgées en France.

Basé sur le décret n°97-427 du 28 avril 1997 publié au JO du 30/04/1997
et l'implémentation documentée sur https://blog.developpez.com/sqlpro/

Auteur: Adaptation Python de l'algorithme officiel
Date: Décembre 2024
Version: 1.0.0 - Intégration CareLink
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple, Optional, Any


class Variable(Enum):
    """
    Variables discriminantes et illustratives de la grille AGGIR.

    Les variables discriminantes (valeurs 1-23) déterminent le GIR.
    Les variables illustratives donnent du contexte mais n'influencent pas le calcul.
    """
    # Variables composées (variables mères)
    COHERENCE = 1
    ORIENTATION = 4
    TOILETTE = 7
    HABILLAGE = 10
    ALIMENTATION = 14
    ELIMINATION = 17

    # Variables simples discriminantes
    TRANSFERTS = 20
    DEPLACEMENTS_INTERNES = 21
    DEPLACEMENTS_EXTERNES = 22
    ALERTER = 23

    # Sous-variables de cohérence
    COMMUNICATION = 2
    COMPORTEMENT = 3

    # Sous-variables d'orientation
    ORIENTATION_TEMPS = 5
    ORIENTATION_ESPACE = 6

    # Sous-variables de toilette
    TOILETTE_HAUT = 8
    TOILETTE_BAS = 9

    # Sous-variables d'habillage
    HABILLAGE_HAUT = 11
    HABILLAGE_MOYEN = 12
    HABILLAGE_BAS = 13

    # Sous-variables d'alimentation
    SE_SERVIR = 15
    MANGER = 16

    # Sous-variables d'élimination
    ELIMINATION_URINAIRE = 18
    ELIMINATION_FECALE = 19


# Mapping des codes string vers les Variables enum
VARIABLE_CODE_MAPPING: Dict[str, Variable] = {
    # Variables principales
    "COHERENCE": Variable.COHERENCE,
    "ORIENTATION": Variable.ORIENTATION,
    "TOILETTE": Variable.TOILETTE,
    "HABILLAGE": Variable.HABILLAGE,
    "ALIMENTATION": Variable.ALIMENTATION,
    "ELIMINATION": Variable.ELIMINATION,
    "TRANSFERTS": Variable.TRANSFERTS,
    "DEPLACEMENT_INTERIEUR": Variable.DEPLACEMENTS_INTERNES,
    "DEPLACEMENTS_INTERNES": Variable.DEPLACEMENTS_INTERNES,
    "DEPLACEMENT_EXTERIEUR": Variable.DEPLACEMENTS_EXTERNES,
    "DEPLACEMENTS_EXTERNES": Variable.DEPLACEMENTS_EXTERNES,
    "ALERTER": Variable.ALERTER,

    # Sous-variables
    "COMMUNICATION": Variable.COMMUNICATION,
    "COMPORTEMENT": Variable.COMPORTEMENT,
    "TEMPS": Variable.ORIENTATION_TEMPS,
    "ORIENTATION_TEMPS": Variable.ORIENTATION_TEMPS,
    "ESPACE": Variable.ORIENTATION_ESPACE,
    "ORIENTATION_ESPACE": Variable.ORIENTATION_ESPACE,
    "TOILETTE_HAUT": Variable.TOILETTE_HAUT,
    "TOILETTE_BAS": Variable.TOILETTE_BAS,
    "HABILLAGE_HAUT": Variable.HABILLAGE_HAUT,
    "HABILLAGE_MOYEN": Variable.HABILLAGE_MOYEN,
    "HABILLAGE_BAS": Variable.HABILLAGE_BAS,
    "SE_SERVIR": Variable.SE_SERVIR,
    "MANGER": Variable.MANGER,
    "URINAIRE": Variable.ELIMINATION_URINAIRE,
    "ELIMINATION_URINAIRE": Variable.ELIMINATION_URINAIRE,
    "FECALE": Variable.ELIMINATION_FECALE,
    "ELIMINATION_FECALE": Variable.ELIMINATION_FECALE,
}


@dataclass
class Adverbes:
    """
    Représente l'évaluation des 4 adverbes pour une variable.

    Les 4 adverbes STCH permettent d'évaluer si la personne réalise
    une activité de manière autonome.

    Attributes:
        spontanement: La personne fait-elle spontanément (sans incitation) ?
        totalement: La personne fait-elle totalement (entièrement) ?
        correctement: La personne fait-elle correctement (de manière adaptée) ?
        habituellement: La personne fait-elle habituellement (régulièrement) ?
    """
    spontanement: bool
    totalement: bool
    correctement: bool
    habituellement: bool

    def to_letter(self) -> str:
        """
        Convertit les adverbes en lettre A, B ou C.

        Règles officielles:
        - A: tous les adverbes sont à True (fait seul, totalement, correctement, habituellement)
        - C: tous les adverbes sont à False (ne fait pas du tout)
        - B: autres cas (1 à 3 adverbes à False = fait partiellement)

        Returns:
            'A', 'B' ou 'C'
        """
        if all([self.spontanement, self.totalement, self.correctement, self.habituellement]):
            return 'A'
        elif not any([self.spontanement, self.totalement, self.correctement, self.habituellement]):
            return 'C'
        else:
            return 'B'

    @classmethod
    def from_dict(cls, data: Dict[str, bool]) -> "Adverbes":
        """
        Crée une instance depuis un dictionnaire.

        Args:
            data: Dict avec clés 'S', 'T', 'C', 'H' ou noms complets

        Returns:
            Instance Adverbes
        """
        return cls(
            spontanement=data.get('S', data.get('spontanement', False)),
            totalement=data.get('T', data.get('totalement', False)),
            correctement=data.get('C', data.get('correctement', False)),
            habituellement=data.get('H', data.get('habituellement', False)),
        )


class AggiralgorithmTable:
    """
    Tables de l'algorithme AGGIR avec les coefficients pour chaque groupe.

    L'algorithme parcourt les groupes A à H dans l'ordre. Pour chaque groupe,
    il calcule un score basé sur les lettres des variables. Si le score dépasse
    un seuil, le GIR correspondant est attribué.
    """

    # Coefficients pour le groupe A
    GROUPE_A = {
        Variable.COHERENCE: {'C': 2000, 'B': 0},
        Variable.ORIENTATION: {'C': 1200, 'B': 0},
        Variable.TOILETTE: {'C': 40, 'B': 16},
        Variable.HABILLAGE: {'C': 40, 'B': 16},
        Variable.ALIMENTATION: {'C': 60, 'B': 20},
        Variable.ELIMINATION: {'C': 100, 'B': 16},
        Variable.TRANSFERTS: {'C': 800, 'B': 120},
        Variable.DEPLACEMENTS_INTERNES: {'C': 200, 'B': 32},
        Variable.DEPLACEMENTS_EXTERNES: {'C': 0, 'B': 0},
        Variable.ALERTER: {'C': 0, 'B': 0},
    }

    # Coefficients pour le groupe B
    GROUPE_B = {
        Variable.COHERENCE: {'C': 1500, 'B': 320},
        Variable.ORIENTATION: {'C': 1200, 'B': 120},
        Variable.TOILETTE: {'C': 40, 'B': 16},
        Variable.HABILLAGE: {'C': 40, 'B': 16},
        Variable.ALIMENTATION: {'C': 60, 'B': 0},
        Variable.ELIMINATION: {'C': 100, 'B': 16},
        Variable.TRANSFERTS: {'C': 800, 'B': 120},
        Variable.DEPLACEMENTS_INTERNES: {'C': -80, 'B': -40},
        Variable.DEPLACEMENTS_EXTERNES: {'C': 0, 'B': 0},
        Variable.ALERTER: {'C': 0, 'B': 0},
    }

    # Coefficients pour le groupe C
    GROUPE_C = {
        Variable.COHERENCE: {'C': 0, 'B': 0},
        Variable.ORIENTATION: {'C': 0, 'B': 0},
        Variable.TOILETTE: {'C': 40, 'B': 16},
        Variable.HABILLAGE: {'C': 40, 'B': 16},
        Variable.ALIMENTATION: {'C': 60, 'B': 20},
        Variable.ELIMINATION: {'C': 160, 'B': 20},
        Variable.TRANSFERTS: {'C': 1000, 'B': 200},
        Variable.DEPLACEMENTS_INTERNES: {'C': 400, 'B': 40},
        Variable.DEPLACEMENTS_EXTERNES: {'C': 0, 'B': 0},
        Variable.ALERTER: {'C': 0, 'B': 0},
    }

    # Coefficients pour le groupe D
    GROUPE_D = {
        Variable.COHERENCE: {'C': 0, 'B': 0},
        Variable.ORIENTATION: {'C': 0, 'B': 0},
        Variable.TOILETTE: {'C': 0, 'B': 0},
        Variable.HABILLAGE: {'C': 0, 'B': 0},
        Variable.ALIMENTATION: {'C': 2000, 'B': 200},
        Variable.ELIMINATION: {'C': 400, 'B': 200},
        Variable.TRANSFERTS: {'C': 2000, 'B': 200},
        Variable.DEPLACEMENTS_INTERNES: {'C': 200, 'B': 0},
        Variable.DEPLACEMENTS_EXTERNES: {'C': 0, 'B': 0},
        Variable.ALERTER: {'C': 0, 'B': 0},
    }

    # Coefficients pour le groupe E
    GROUPE_E = {
        Variable.COHERENCE: {'C': 400, 'B': 0},
        Variable.ORIENTATION: {'C': 400, 'B': 0},
        Variable.TOILETTE: {'C': 400, 'B': 100},
        Variable.HABILLAGE: {'C': 400, 'B': 100},
        Variable.ALIMENTATION: {'C': 400, 'B': 100},
        Variable.ELIMINATION: {'C': 800, 'B': 100},
        Variable.TRANSFERTS: {'C': 800, 'B': 100},
        Variable.DEPLACEMENTS_INTERNES: {'C': 200, 'B': 0},
        Variable.DEPLACEMENTS_EXTERNES: {'C': 0, 'B': 0},
        Variable.ALERTER: {'C': 0, 'B': 0},
    }

    # Coefficients pour le groupe F
    GROUPE_F = {
        Variable.COHERENCE: {'C': 200, 'B': 100},
        Variable.ORIENTATION: {'C': 200, 'B': 100},
        Variable.TOILETTE: {'C': 500, 'B': 100},
        Variable.HABILLAGE: {'C': 500, 'B': 100},
        Variable.ALIMENTATION: {'C': 500, 'B': 100},
        Variable.ELIMINATION: {'C': 500, 'B': 100},
        Variable.TRANSFERTS: {'C': 500, 'B': 100},
        Variable.DEPLACEMENTS_INTERNES: {'C': 200, 'B': 0},
        Variable.DEPLACEMENTS_EXTERNES: {'C': 0, 'B': 0},
        Variable.ALERTER: {'C': 0, 'B': 0},
    }

    # Coefficients pour le groupe G
    GROUPE_G = {
        Variable.COHERENCE: {'C': 150, 'B': 0},
        Variable.ORIENTATION: {'C': 150, 'B': 0},
        Variable.TOILETTE: {'C': 300, 'B': 200},
        Variable.HABILLAGE: {'C': 300, 'B': 200},
        Variable.ALIMENTATION: {'C': 500, 'B': 200},
        Variable.ELIMINATION: {'C': 500, 'B': 200},
        Variable.TRANSFERTS: {'C': 400, 'B': 200},
        Variable.DEPLACEMENTS_INTERNES: {'C': 200, 'B': 100},
        Variable.DEPLACEMENTS_EXTERNES: {'C': 0, 'B': 0},
        Variable.ALERTER: {'C': 0, 'B': 0},
    }

    # Coefficients pour le groupe H
    GROUPE_H = {
        Variable.COHERENCE: {'C': 0, 'B': 0},
        Variable.ORIENTATION: {'C': 0, 'B': 0},
        Variable.TOILETTE: {'C': 3000, 'B': 2000},
        Variable.HABILLAGE: {'C': 3000, 'B': 2000},
        Variable.ALIMENTATION: {'C': 3000, 'B': 2000},
        Variable.ELIMINATION: {'C': 3000, 'B': 2000},
        Variable.TRANSFERTS: {'C': 1000, 'B': 2000},
        Variable.DEPLACEMENTS_INTERNES: {'C': 1000, 'B': 1000},
        Variable.DEPLACEMENTS_EXTERNES: {'C': 0, 'B': 0},
        Variable.ALERTER: {'C': 0, 'B': 0},
    }

    # Regroupement de tous les groupes
    GROUPES = {
        'A': GROUPE_A,
        'B': GROUPE_B,
        'C': GROUPE_C,
        'D': GROUPE_D,
        'E': GROUPE_E,
        'F': GROUPE_F,
        'G': GROUPE_G,
        'H': GROUPE_H,
    }

    # Seuils de rang pour déterminer le GIR
    # Format: (groupe, [(seuil_min, seuil_max, rang, GIR)])
    RANGS = {
        'A': [
            (4380, float('inf'), 1, 1),
            (4140, 4380, 2, 2),
            (3390, 4140, 3, 2),
            (0, 3390, None, None),  # Passage au groupe B
        ],
        'B': [
            (2016, float('inf'), 4, 2),
            (0, 2016, None, None),  # Passage au groupe C
        ],
        'C': [
            (1700, float('inf'), 5, 2),
            (1432, 1700, 6, 2),
            (0, 1432, None, None),  # Passage au groupe D
        ],
        'D': [
            (2400, float('inf'), 7, 2),
            (0, 2400, None, None),  # Passage au groupe E
        ],
        'E': [
            (1200, float('inf'), 8, 3),
            (0, 1200, None, None),  # Passage au groupe F
        ],
        'F': [
            (800, float('inf'), 9, 3),
            (0, 800, None, None),  # Passage au groupe G
        ],
        'G': [
            (650, float('inf'), 10, 4),
            (0, 650, None, None),  # Passage au groupe H
        ],
        'H': [
            (4000, float('inf'), 11, 4),
            (2000, 4000, 12, 5),
            (0, 2000, 13, 6),
        ],
    }


class AggirCalculator:
    """
    Implémentation de l'algorithme officiel de calcul du GIR.

    Usage:
        calculator = AggirCalculator()

        evaluations = {
            Variable.COMMUNICATION: Adverbes(True, True, True, True),
            Variable.COMPORTEMENT: Adverbes(True, True, True, True),
            # ... autres variables
        }

        gir, details = calculator.calculer_gir(evaluations)
        print(f"GIR: {gir}")
    """

    @staticmethod
    def combiner_sous_variables_coherence(communication: str, comportement: str) -> str:
        """
        Combine les lettres des sous-variables de cohérence.

        Règle: AA = A, sinon si C présent = C, sinon B
        """
        if communication == 'A' and comportement == 'A':
            return 'A'
        elif 'C' in [communication, comportement]:
            return 'C'
        else:
            return 'B'

    @staticmethod
    def combiner_sous_variables_orientation(temps: str, espace: str) -> str:
        """
        Combine les lettres des sous-variables d'orientation.

        Règle: AA = A, sinon si C présent = C, sinon B
        """
        if temps == 'A' and espace == 'A':
            return 'A'
        elif 'C' in [temps, espace]:
            return 'C'
        else:
            return 'B'

    @staticmethod
    def combiner_sous_variables_toilette(haut: str, bas: str) -> str:
        """
        Combine les lettres des sous-variables de toilette.

        Règle: AA = A, CC = C, sinon B
        """
        if haut == 'A' and bas == 'A':
            return 'A'
        elif haut == 'C' and bas == 'C':
            return 'C'
        else:
            return 'B'

    @staticmethod
    def combiner_sous_variables_habillage(haut: str, moyen: str, bas: str) -> str:
        """
        Combine les lettres des sous-variables d'habillage.

        Règle: AAA = A, CCC = C, sinon B
        """
        if haut == 'A' and moyen == 'A' and bas == 'A':
            return 'A'
        elif haut == 'C' and moyen == 'C' and bas == 'C':
            return 'C'
        else:
            return 'B'

    @staticmethod
    def combiner_sous_variables_alimentation(se_servir: str, manger: str) -> str:
        """
        Combine les lettres des sous-variables d'alimentation.

        Règle: AA = A, BC = C, CB = C, CC = C, sinon B
        """
        if se_servir == 'A' and manger == 'A':
            return 'A'
        elif se_servir == 'C' or manger == 'C':
            return 'C'
        else:
            return 'B'

    @staticmethod
    def combiner_sous_variables_elimination(urinaire: str, fecale: str) -> str:
        """
        Combine les lettres des sous-variables d'élimination.

        Règle: AA = A, sinon si C présent = C, sinon B
        """
        if urinaire == 'A' and fecale == 'A':
            return 'A'
        elif 'C' in [urinaire, fecale]:
            return 'C'
        else:
            return 'B'

    @staticmethod
    def calculer_score_groupe(lettres: Dict[Variable, str], groupe: Dict) -> int:
        """
        Calcule le score pour un groupe donné.

        Args:
            lettres: Dictionnaire des lettres pour chaque variable
            groupe: Dictionnaire des coefficients du groupe

        Returns:
            Score total pour ce groupe
        """
        score = 0
        for variable, coefficients in groupe.items():
            lettre = lettres.get(variable, 'B')
            # Si la lettre est A, on ne compte rien (A n'est pas dans les coefficients)
            if lettre in coefficients:
                score += coefficients[lettre]
        return score

    @staticmethod
    def determiner_gir_depuis_score(score: int, groupe_name: str) -> Optional[int]:
        """
        Détermine le GIR à partir d'un score et du nom du groupe.

        Args:
            score: Score calculé
            groupe_name: Nom du groupe ('A', 'B', 'C', etc.)

        Returns:
            GIR (1-6) ou None si passage au groupe suivant
        """
        rangs = AggiralgorithmTable.RANGS[groupe_name]
        for seuil_min, seuil_max, rang, gir in rangs:
            if seuil_min <= score < seuil_max:
                return gir
        return None

    def calculer_gir(self, evaluations: Dict[Variable, Adverbes]) -> Tuple[int, Dict[str, Any]]:
        """
        Calcule le GIR à partir des évaluations.

        C'est la méthode principale à appeler pour obtenir le GIR.

        Args:
            evaluations: Dictionnaire des évaluations pour chaque variable/sous-variable
                        Les clés sont des Variable enum, les valeurs des Adverbes

        Returns:
            Tuple (GIR, détails) où:
            - GIR est un entier de 1 à 6
            - détails contient les informations de calcul pour traçabilité
        """
        # Étape 1: Convertir les adverbes en lettres pour les sous-variables
        lettres_sous_variables = {}
        for variable, adverbes in evaluations.items():
            lettres_sous_variables[variable] = adverbes.to_letter()

        # Étape 2: Combiner les sous-variables pour obtenir les lettres des variables principales
        lettres_principales = {}

        # Cohérence
        if Variable.COMMUNICATION in lettres_sous_variables and Variable.COMPORTEMENT in lettres_sous_variables:
            lettres_principales[Variable.COHERENCE] = self.combiner_sous_variables_coherence(
                lettres_sous_variables[Variable.COMMUNICATION],
                lettres_sous_variables[Variable.COMPORTEMENT]
            )

        # Orientation
        if Variable.ORIENTATION_TEMPS in lettres_sous_variables and Variable.ORIENTATION_ESPACE in lettres_sous_variables:
            lettres_principales[Variable.ORIENTATION] = self.combiner_sous_variables_orientation(
                lettres_sous_variables[Variable.ORIENTATION_TEMPS],
                lettres_sous_variables[Variable.ORIENTATION_ESPACE]
            )

        # Toilette
        if Variable.TOILETTE_HAUT in lettres_sous_variables and Variable.TOILETTE_BAS in lettres_sous_variables:
            lettres_principales[Variable.TOILETTE] = self.combiner_sous_variables_toilette(
                lettres_sous_variables[Variable.TOILETTE_HAUT],
                lettres_sous_variables[Variable.TOILETTE_BAS]
            )

        # Habillage
        if all(v in lettres_sous_variables for v in
               [Variable.HABILLAGE_HAUT, Variable.HABILLAGE_MOYEN, Variable.HABILLAGE_BAS]):
            lettres_principales[Variable.HABILLAGE] = self.combiner_sous_variables_habillage(
                lettres_sous_variables[Variable.HABILLAGE_HAUT],
                lettres_sous_variables[Variable.HABILLAGE_MOYEN],
                lettres_sous_variables[Variable.HABILLAGE_BAS]
            )

        # Alimentation
        if Variable.SE_SERVIR in lettres_sous_variables and Variable.MANGER in lettres_sous_variables:
            lettres_principales[Variable.ALIMENTATION] = self.combiner_sous_variables_alimentation(
                lettres_sous_variables[Variable.SE_SERVIR],
                lettres_sous_variables[Variable.MANGER]
            )

        # Élimination
        if Variable.ELIMINATION_URINAIRE in lettres_sous_variables and Variable.ELIMINATION_FECALE in lettres_sous_variables:
            lettres_principales[Variable.ELIMINATION] = self.combiner_sous_variables_elimination(
                lettres_sous_variables[Variable.ELIMINATION_URINAIRE],
                lettres_sous_variables[Variable.ELIMINATION_FECALE]
            )

        # Variables simples (pas de combinaison)
        for var in [Variable.TRANSFERTS, Variable.DEPLACEMENTS_INTERNES,
                    Variable.DEPLACEMENTS_EXTERNES, Variable.ALERTER]:
            if var in lettres_sous_variables:
                lettres_principales[var] = lettres_sous_variables[var]

        # Étape 3: Calculer les scores pour chaque groupe et déterminer le GIR
        ordre_groupes = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

        details = {
            'lettres_sous_variables': {v.name: l for v, l in lettres_sous_variables.items()},
            'lettres_principales': {v.name: l for v, l in lettres_principales.items()},
            'scores_par_groupe': {},
            'groupe_final': None,
            'rang_final': None,
            'score_final': None,
            'algorithme_version': '1997-04-28',  # Décret officiel
        }

        for groupe_name in ordre_groupes:
            groupe = AggiralgorithmTable.GROUPES[groupe_name]
            score = self.calculer_score_groupe(lettres_principales, groupe)
            details['scores_par_groupe'][groupe_name] = score

            gir = self.determiner_gir_depuis_score(score, groupe_name)

            if gir is not None:
                details['groupe_final'] = groupe_name
                details['score_final'] = score
                return gir, details

        # Cas par défaut (ne devrait pas arriver si l'évaluation est complète)
        details['groupe_final'] = 'H'
        details['score_final'] = details['scores_par_groupe'].get('H', 0)
        return 6, details


def calculer_gir_simple(evaluations: Dict[Variable, Adverbes]) -> int:
    """
    Fonction raccourcie pour calculer uniquement le GIR sans les détails.

    Args:
        evaluations: Dictionnaire Variable → Adverbes

    Returns:
        Score GIR (1-6)
    """
    calculator = AggirCalculator()
    gir, _ = calculator.calculer_gir(evaluations)
    return gir