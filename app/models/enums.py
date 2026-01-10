"""
Nouveaux enums à ajouter au fichier app/models/enums.py existant.

Ces enums sont nécessaires pour les nouvelles tables de coordination.
"""

from enum import Enum


# =============================================================================
# ENUMS POUR LE MODULE CATALOG
# =============================================================================

class ServiceCategory(str, Enum):
    """Catégories de services du catalogue."""
    SOINS = "SOINS"                    # Soins médicaux et paramédicaux
    HYGIENE = "HYGIENE"                # Toilette, habillage
    REPAS = "REPAS"                    # Préparation et aide aux repas
    MOBILITE = "MOBILITE"              # Lever, coucher, déplacements
    COURSES = "COURSES"                # Aide aux courses
    MENAGE = "MENAGE"                  # Entretien du logement
    ADMINISTRATIF = "ADMINISTRATIF"    # Démarches administratives
    SOCIAL = "SOCIAL"                  # Accompagnement, convivialité
    AUTRE = "AUTRE"                    # Autres services


# =============================================================================
# ENUMS POUR LE MODULE CAREPLAN
# =============================================================================

class CarePlanStatus(str, Enum):
    """Statuts d'un plan d'aide."""
    DRAFT = "DRAFT"                        # Brouillon en cours de création
    PENDING_VALIDATION = "PENDING_VALIDATION"  # En attente de validation
    ACTIVE = "ACTIVE"                      # Actif et en cours d'exécution
    SUSPENDED = "SUSPENDED"                # Suspendu temporairement
    COMPLETED = "COMPLETED"                # Terminé (fin de prise en charge)
    CANCELLED = "CANCELLED"                # Annulé


class FrequencyType(str, Enum):
    """Types de fréquence pour les services."""
    DAILY = "DAILY"                # Tous les jours
    WEEKLY = "WEEKLY"              # X fois par semaine
    SPECIFIC_DAYS = "SPECIFIC_DAYS"  # Jours spécifiques (Lun, Mar, Ven...)
    MONTHLY = "MONTHLY"            # X fois par mois
    ON_DEMAND = "ON_DEMAND"        # À la demande


class ServicePriority(str, Enum):
    """Priorité d'un service dans le plan."""
    LOW = "LOW"            # Basse priorité (confort)
    MEDIUM = "MEDIUM"      # Priorité normale
    HIGH = "HIGH"          # Haute priorité (important)
    CRITICAL = "CRITICAL"  # Critique (vital)


class AssignmentStatus(str, Enum):
    """Statuts d'affectation d'un service à un professionnel."""
    UNASSIGNED = "UNASSIGNED"    # Non affecté
    PENDING = "PENDING"          # Affectation en attente de confirmation
    ASSIGNED = "ASSIGNED"        # Affecté
    CONFIRMED = "CONFIRMED"      # Confirmé par le professionnel
    REJECTED = "REJECTED"        # Refusé par le professionnel


# =============================================================================
# ENUMS POUR LE MODULE COORDINATION (SCHEDULED INTERVENTIONS)
# =============================================================================

class InterventionStatus(str, Enum):
    """Statuts d'une intervention planifiée."""
    SCHEDULED = "SCHEDULED"        # Planifiée
    CONFIRMED = "CONFIRMED"        # Confirmée
    IN_PROGRESS = "IN_PROGRESS"    # En cours
    COMPLETED = "COMPLETED"        # Terminée
    CANCELLED = "CANCELLED"        # Annulée
    MISSED = "MISSED"              # Manquée (patient absent, etc.)
    RESCHEDULED = "RESCHEDULED"    # Reprogrammée


# =============================================================================
# MISE À JOUR DU FICHIER enums.py EXISTANT
# =============================================================================
#
# Ajouter ces classes au fichier app/models/enums.py existant,
# puis mettre à jour le __all__ :
#
# __all__ = [
#     # ... enums existants ...
#     "ServiceCategory",
#     "CarePlanStatus",
#     "FrequencyType",
#     "ServicePriority",
#     "AssignmentStatus",
#     "InterventionStatus",
# ]
# =============================================================================
