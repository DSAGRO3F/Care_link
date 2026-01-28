"""
Enums CareLink - Définitions de tous les types énumérés.

Ce module centralise tous les enums utilisés dans les modèles SQLAlchemy.
Ils sont convertis en types ENUM PostgreSQL via SQLEnum.
"""

from enum import Enum


# =============================================================================
# MODULE: ORGANIZATION - Structures organisationnelles
# =============================================================================

class EntityType(str, Enum):
    """Types de structures médico-sociales."""
    # Services d'aide et de soins à domicile
    SSIAD = "SSIAD"                      # Service de Soins Infirmiers À Domicile
    SAAD = "SAAD"                        # Service d'Aide et d'Accompagnement à Domicile
    SAD = "SAD"                          # Service d'Aide à Domicile
    SPASAD = "SPASAD"                    # Service Polyvalent d'Aide et de Soins À Domicile
    SAP = "SAP"                          # Service À la Personne

    # Établissements pour personnes âgées
    EHPAD = "EHPAD"                      # Établissement d'Hébergement pour Personnes Âgées Dépendantes
    RESIDENCE_AUTONOMIE = "RESIDENCE_AUTONOMIE"  # Ex-logement foyer
    ACCUEIL_JOUR = "ACCUEIL_JOUR"        # Accueil de jour

    # Établissements pour personnes handicapées
    FAM = "FAM"                          # Foyer d'Accueil Médicalisé
    MAS = "MAS"                          # Maison d'Accueil Spécialisée
    SESSAD = "SESSAD"                    # Service d'Éducation Spéciale et de Soins À Domicile
    IME = "IME"                          # Institut Médico-Éducatif
    ESAT = "ESAT"                        # Établissement et Service d'Aide par le Travail

    # Structures de coordination
    GCSMS = "GCSMS"                      # Groupement de Coopération Sociale et Médico-Sociale
    DAC = "DAC"                          # Dispositif d'Appui à la Coordination
    CPTS = "CPTS"                        # Communauté Professionnelle Territoriale de Santé
    PCPE = "PCPE"                        # Pôle de Compétences et de Prestations Externalisées
    PCO = "PCO"                          # Plateforme de Coordination et d'Orientation

    # Établissements sanitaires
    HOSPITAL = "HOSPITAL"                # Hôpital
    CLINIC = "CLINIC"                    # Clinique
    CSI = "CSI"                          # Centre de Soins Infirmiers
    HAD = "HAD"                          # Hospitalisation À Domicile

    # Autres
    HALTE_REPIT = "HALTE_REPIT"          # Halte répit
    FORMATION = "FORMATION"              # Organisme de formation
    OTHER = "OTHER"                      # Autre


class IntegrationType(str, Enum):
    """Types d'intégration dans un groupement."""
    MANAGED = "MANAGED"                  # Intégré (gestion complète par le GCSMS)
    FEDERATED = "FEDERATED"              # Fédéré (autonomie avec coordination)
    CONVENTION = "CONVENTION"            # Conventionné (partenariat externe)
    FINANCIAL_CONTROL = "FINANCIAL_CONTROL"  # Contrôle financier uniquement


class OrganizationModel(str, Enum):
    """Modèles d'organisation des groupements."""
    INTEGRATED = "INTEGRATED"            # Intégré (direction unique)
    FEDERATED = "FEDERATED"              # Fédéré (directions multiples coordonnées)
    HYBRID = "HYBRID"                    # Hybride (mix des deux)


class TerritoryType(str, Enum):
    """Types de zones géographiques."""
    COMMUNE = "COMMUNE"                  # Commune
    EPCI = "EPCI"                        # Intercommunalité
    DEPARTEMENT = "DEPARTEMENT"          # Département
    REGION = "REGION"                    # Région
    CUSTOM = "CUSTOM"                    # Zone personnalisée (polygone)


# =============================================================================
# MODULE: USER - Utilisateurs et professions
# =============================================================================

class ProfessionCategory(str, Enum):
    """Catégories de professions."""
    MEDICAL = "MEDICAL"                  # Médecins
    PARAMEDICAL = "PARAMEDICAL"          # Infirmiers, aides-soignants, kinés...
    ADMINISTRATIVE = "ADMINISTRATIVE"    # Secrétaires, coordinateurs...
    SOCIAL = "SOCIAL"                    # Assistants sociaux, éducateurs...


class RoleName(str, Enum):
    """Noms des rôles système."""
    ADMIN = "ADMIN"                      # Administrateur système
    COORDINATEUR = "COORDINATEUR"        # Coordinateur de soins
    MEDECIN_TRAITANT = "MEDECIN_TRAITANT"  # Médecin traitant référent
    MEDECIN_SPECIALISTE = "MEDECIN_SPECIALISTE"  # Médecin spécialiste
    INFIRMIERE = "INFIRMIERE"            # Infirmier(ère)
    AIDE_SOIGNANTE = "AIDE_SOIGNANTE"    # Aide-soignant(e)
    KINESITHERAPEUTE = "KINESITHERAPEUTE"  # Kinésithérapeute
    AUXILIAIRE_VIE = "AUXILIAIRE_VIE"    # Auxiliaire de vie
    ASSISTANT_SOCIAL = "ASSISTANT_SOCIAL"  # Assistant(e) social(e)
    INTERVENANT = "INTERVENANT"          # Intervenant générique


class ContractType(str, Enum):
    """Types de contrats de travail."""
    SALARIE = "SALARIE"                  # Salarié CDI/CDD
    LIBERAL = "LIBERAL"                  # Professionnel libéral
    VACATION = "VACATION"                # Vacataire
    REMPLACEMENT = "REMPLACEMENT"        # Remplaçant
    BENEVOLE = "BENEVOLE"                # Bénévole
    STAGIAIRE = "STAGIAIRE"              # Stagiaire
    MUTUAL_POOL = "MUTUAL_POOL"          # Pool mutualisé (GCSMS)


class PermissionCategory(str, Enum):
    """
    Catégories de permissions pour le regroupement dans l'UI.
    
    Utilisé pour organiser les permissions par domaine fonctionnel.
    """
    ADMIN = "ADMIN"                      # Permissions administrateur
    PATIENT = "PATIENT"                  # Gestion des patients
    EVALUATION = "EVALUATION"            # Évaluations AGGIR et autres
    VITALS = "VITALS"                    # Constantes vitales
    USER = "USER"                        # Gestion des utilisateurs
    COORDINATION = "COORDINATION"        # Carnet de coordination
    CAREPLAN = "CAREPLAN"                # Plans d'aide
    ACCESS = "ACCESS"                    # Gestion des accès RGPD
    ROLE = "ROLE"                        # Gestion des rôles


# =============================================================================
# MODULE: PATIENT - Dossier patient
# =============================================================================

class PatientStatus(str, Enum):
    """Statuts d'un patient."""
    ACTIVE = "ACTIVE"                    # Patient actif en prise en charge
    ARCHIVED = "ARCHIVED"                # Dossier archivé
    DECEASED = "DECEASED"                # Patient décédé
    TRANSFERRED = "TRANSFERRED"          # Transféré vers autre structure


class AccessType(str, Enum):
    """Types d'accès au dossier patient."""
    READ = "READ"                        # Lecture seule
    WRITE = "WRITE"                      # Lecture + écriture
    FULL = "FULL"                        # Accès complet (inclut suppression)


class GirLevel(str, Enum):
    """Niveaux de la grille AGGIR (Autonomie Gérontologie Groupes Iso-Ressources)."""
    GIR_1 = "GIR_1"  # Dépendance totale, fonctions mentales altérées
    GIR_2 = "GIR_2"  # Dépendance totale, fonctions mentales préservées OU déplacements OK mais cognitif altéré
    GIR_3 = "GIR_3"  # Autonomie mentale, dépendance corporelle partielle
    GIR_4 = "GIR_4"  # Autonomie pour déplacements, aide pour activités corporelles et repas
    GIR_5 = "GIR_5"  # Aide ponctuelle (toilette, repas, ménage)
    GIR_6 = "GIR_6"  # Autonome pour les actes de la vie courante


class VitalType(str, Enum):
    """Types de constantes vitales."""
    FC = "FC"                            # Fréquence cardiaque (bpm)
    TA_SYS = "TA_SYS"                    # Tension artérielle systolique (mmHg)
    TA_DIA = "TA_DIA"                    # Tension artérielle diastolique (mmHg)
    SPO2 = "SPO2"                        # Saturation en oxygène (%)
    TEMPERATURE = "TEMPERATURE"          # Température (°C)
    POIDS = "POIDS"                      # Poids (kg)
    GLYCEMIE = "GLYCEMIE"                # Glycémie (g/L ou mmol/L)
    DOULEUR = "DOULEUR"                  # Échelle de douleur (0-10)
    FREQUENCE_RESPIRATOIRE = "FREQUENCE_RESPIRATOIRE"  # FR (cycles/min)
    DIURESE = "DIURESE"                  # Diurèse (mL/24h)


class VitalStatus(str, Enum):
    """Statuts par rapport aux seuils."""
    NORMAL = "NORMAL"                    # Dans les normes
    LOW = "LOW"                          # En dessous du seuil
    HIGH = "HIGH"                        # Au dessus du seuil
    CRITICAL = "CRITICAL"                # Critique (très hors normes)


class VitalSource(str, Enum):
    """Sources des mesures de constantes."""
    MANUAL = "MANUAL"                    # Saisie manuelle
    WITHINGS = "WITHINGS"                # Balance/montre Withings
    APPLE_WATCH = "APPLE_WATCH"          # Apple Watch
    FREESTYLE_LIBRE = "FREESTYLE_LIBRE"  # Capteur glycémie FreeStyle
    OTHER_DEVICE = "OTHER_DEVICE"        # Autre device connecté


class DeviceType(str, Enum):
    """Types de devices connectés."""
    WITHINGS_SCALE = "WITHINGS_SCALE"    # Balance Withings
    WITHINGS_BPM = "WITHINGS_BPM"        # Tensiomètre Withings
    APPLE_WATCH = "APPLE_WATCH"          # Apple Watch
    FREESTYLE_LIBRE = "FREESTYLE_LIBRE"  # Capteur FreeStyle Libre
    GENERIC = "GENERIC"                  # Device générique


class EvaluationSchemaType(str, Enum):
    """Types de schémas d'évaluation JSON."""
    EVALUATION_COMPLETE = "EVALUATION_COMPLETE"  # Évaluation complète
    AGGIR_ONLY = "AGGIR_ONLY"            # Évaluation AGGIR seule
    SOCIAL_ONLY = "SOCIAL_ONLY"          # Évaluation sociale seule
    MEDICAL_ONLY = "MEDICAL_ONLY"        # Évaluation médicale seule


class DocumentType(str, Enum):
    """Types de documents générés."""
    PPA = "PPA"                          # Plan Personnalisé d'Accompagnement
    PPCS = "PPCS"                        # Plan Personnalisé de Coordination en Santé
    RECOMMENDATION = "RECOMMENDATION"    # Recommandation générée par IA
    OTHER = "OTHER"                      # Autre document


class DocumentFormat(str, Enum):
    """Formats de fichiers de documents."""
    PDF = "pdf"
    DOCX = "docx"


# =============================================================================
# MODULE: EVALUATION - Évaluations patient (NOUVEAU)
# =============================================================================

class EvaluationStatus(str, Enum):
    """Statuts d'une évaluation patient."""
    DRAFT = "DRAFT"                          # En cours de saisie
    PENDING_COMPLETION = "PENDING_COMPLETION" # Saisie incomplète, en attente
    COMPLETE = "COMPLETE"                    # Saisie terminée, non soumise
    PENDING_MEDICAL = "PENDING_MEDICAL"      # En attente validation médecin coord.
    PENDING_DEPARTMENT = "PENDING_DEPARTMENT" # En attente validation CD
    VALIDATED = "VALIDATED"                  # Validée (GIR officiel)
    EXPIRED = "EXPIRED"                      # Expirée (délai J+7 dépassé)
    CANCELLED = "CANCELLED"                  # Annulée manuellement


class EvaluationSessionStatus(str, Enum):
    """Statuts d'une session de saisie."""
    IN_PROGRESS = "IN_PROGRESS"              # Session en cours
    COMPLETED = "COMPLETED"                  # Session terminée
    INTERRUPTED = "INTERRUPTED"              # Session interrompue (perte connexion)


class SyncStatus(str, Enum):
    """Statuts de synchronisation pour le mode hors-ligne."""
    SYNCED = "SYNCED"                        # Synchronisé avec le serveur
    PENDING = "PENDING"                      # En attente de synchronisation
    CONFLICT = "CONFLICT"                    # Conflit détecté
    ERROR = "ERROR"                          # Erreur de synchronisation


class AggirVariableCode(str, Enum):
    """Codes des variables AGGIR (17 variables officielles)."""
    # Variables discriminantes
    COHERENCE = "COHERENCE"
    ORIENTATION = "ORIENTATION"
    TOILETTE = "TOILETTE"
    HABILLAGE = "HABILLAGE"
    ALIMENTATION = "ALIMENTATION"
    ELIMINATION = "ELIMINATION"
    TRANSFERTS = "TRANSFERTS"
    DEPLACEMENT_INTERIEUR = "DEPLACEMENT_INTERIEUR"
    # Variables illustratives
    DEPLACEMENT_EXTERIEUR = "DEPLACEMENT_EXTERIEUR"
    ALERTER = "ALERTER"
    CUISINE = "CUISINE"
    MENAGE = "MENAGE"
    TRANSPORTS = "TRANSPORTS"
    ACHATS = "ACHATS"
    SUIVI_TRAITEMENT = "SUIVI_TRAITEMENT"
    ACTIVITES_TEMPS_LIBRE = "ACTIVITES_TEMPS_LIBRE"
    GESTION = "GESTION"


class AggirSubVariableCode(str, Enum):
    """Codes des sous-variables AGGIR."""
    # Cohérence
    COMMUNICATION = "COMMUNICATION"
    COMPORTEMENT = "COMPORTEMENT"
    # Orientation
    TEMPS = "TEMPS"
    ESPACE = "ESPACE"
    # Toilette
    TOILETTE_HAUT = "TOILETTE_HAUT"
    TOILETTE_BAS = "TOILETTE_BAS"
    # Habillage
    HABILLAGE_HAUT = "HABILLAGE_HAUT"
    HABILLAGE_MOYEN = "HABILLAGE_MOYEN"
    HABILLAGE_BAS = "HABILLAGE_BAS"
    # Alimentation
    SE_SERVIR = "SE_SERVIR"
    MANGER = "MANGER"
    # Élimination
    URINAIRE = "URINAIRE"
    FECALE = "FECALE"


class AggirResultLetter(str, Enum):
    """Résultats possibles pour une variable AGGIR."""
    A = "A"  # Fait seul, totalement, correctement, habituellement
    B = "B"  # Fait partiellement, ou incorrectement, ou non habituellement
    C = "C"  # Ne fait pas


# =============================================================================
# MODULE: COORDINATION - Carnet de coordination
# =============================================================================

class CoordinationCategory(str, Enum):
    """Catégories d'interventions dans le carnet de coordination."""
    SOINS = "SOINS"                      # Soins médicaux et paramédicaux
    HYGIENE = "HYGIENE"                  # Toilette, habillage
    ALIMENTATION = "ALIMENTATION"        # Repas, hydratation
    MOBILITE = "MOBILITE"                # Lever, coucher, déplacements
    MEDICAL = "MEDICAL"                  # Consultations, examens
    SOCIAL = "SOCIAL"                    # Accompagnement social
    ADMINISTRATIF = "ADMINISTRATIF"      # Démarches administratives
    OBSERVATION = "OBSERVATION"          # Observation générale


# =============================================================================
# MODULE: CATALOG - Services
# =============================================================================

class ServiceCategory(str, Enum):
    """Catégories de services du catalogue."""
    SOINS = "SOINS"                      # Soins médicaux et paramédicaux
    HYGIENE = "HYGIENE"                  # Toilette, habillage
    REPAS = "REPAS"                      # Préparation et aide aux repas
    MOBILITE = "MOBILITE"                # Lever, coucher, déplacements
    COURSES = "COURSES"                  # Aide aux courses
    MENAGE = "MENAGE"                    # Entretien du logement
    ADMINISTRATIF = "ADMINISTRATIF"      # Démarches administratives
    SOCIAL = "SOCIAL"                    # Accompagnement, convivialité
    AUTRE = "AUTRE"                      # Autres services


class ServiceType(str, Enum):
    """Types de services (acte médical vs aide à la personne)."""
    MEDICAL_ACT = "MEDICAL_ACT"          # Acte médical (nécessite prescription)
    PARAMEDICAL_ACT = "PARAMEDICAL_ACT"  # Acte paramédical
    PERSONAL_ASSISTANCE = "PERSONAL_ASSISTANCE"  # Aide à la personne
    DOMESTIC_HELP = "DOMESTIC_HELP"      # Aide ménagère
    SOCIAL_SUPPORT = "SOCIAL_SUPPORT"    # Accompagnement social


class ServiceUnit(str, Enum):
    """Unités de facturation des services."""
    HOUR = "HOUR"                        # À l'heure
    HALF_HOUR = "HALF_HOUR"              # À la demi-heure
    ACT = "ACT"                          # À l'acte
    DAY = "DAY"                          # À la journée
    PACKAGE = "PACKAGE"                  # Forfait


# =============================================================================
# MODULE: CAREPLAN - Plans d'aide
# =============================================================================

class CarePlanStatus(str, Enum):
    """Statuts d'un plan d'aide."""
    DRAFT = "DRAFT"                      # Brouillon en cours de création
    PENDING_VALIDATION = "PENDING_VALIDATION"  # En attente de validation
    ACTIVE = "ACTIVE"                    # Actif et en cours d'exécution
    SUSPENDED = "SUSPENDED"              # Suspendu temporairement
    COMPLETED = "COMPLETED"              # Terminé (fin de prise en charge)
    CANCELLED = "CANCELLED"              # Annulé


class FrequencyType(str, Enum):
    """Types de fréquence pour les services."""
    DAILY = "DAILY"                      # Tous les jours
    WEEKLY = "WEEKLY"                    # X fois par semaine
    SPECIFIC_DAYS = "SPECIFIC_DAYS"      # Jours spécifiques (Lun, Mar, Ven...)
    MONTHLY = "MONTHLY"                  # X fois par mois
    ON_DEMAND = "ON_DEMAND"              # À la demande


class ServicePriority(str, Enum):
    """Priorité d'un service dans le plan."""
    LOW = "LOW"                          # Basse priorité (confort)
    MEDIUM = "MEDIUM"                    # Priorité normale
    HIGH = "HIGH"                        # Haute priorité (important)
    CRITICAL = "CRITICAL"                # Critique (vital)


class AssignmentStatus(str, Enum):
    """Statuts d'affectation d'un service à un professionnel."""
    UNASSIGNED = "UNASSIGNED"            # Non affecté
    PENDING = "PENDING"                  # Affectation en attente de confirmation
    ASSIGNED = "ASSIGNED"                # Affecté
    CONFIRMED = "CONFIRMED"              # Confirmé par le professionnel
    REJECTED = "REJECTED"                # Refusé par le professionnel


# =============================================================================
# MODULE: COORDINATION - Interventions planifiées
# =============================================================================

class InterventionStatus(str, Enum):
    """Statuts d'une intervention planifiée."""
    SCHEDULED = "SCHEDULED"              # Planifiée
    CONFIRMED = "CONFIRMED"              # Confirmée
    IN_PROGRESS = "IN_PROGRESS"          # En cours
    COMPLETED = "COMPLETED"              # Terminée
    CANCELLED = "CANCELLED"              # Annulée
    MISSED = "MISSED"                    # Manquée (patient absent, etc.)
    RESCHEDULED = "RESCHEDULED"          # Reprogrammée


# =============================================================================
# MODULE: TENANT - Multi-tenant (NOUVEAU v4.1)
# =============================================================================

class TenantType(str, Enum):
    """Types de clients/locataires.

    Reprend les principaux types d'EntityType qui peuvent être
    des clients directs de la plateforme CareLink.
    """
    # Groupements (clients principaux)
    GCSMS = "GCSMS"                      # Groupement de Coopération Sociale et Médico-Sociale

    # Services à domicile (clients indépendants)
    SSIAD = "SSIAD"                      # Service de Soins Infirmiers À Domicile
    SAAD = "SAAD"                        # Service d'Aide et d'Accompagnement à Domicile
    SPASAD = "SPASAD"                    # Service Polyvalent d'Aide et de Soins À Domicile

    # Établissements (clients indépendants)
    EHPAD = "EHPAD"                      # Établissement d'Hébergement pour Personnes Âgées Dépendantes

    # Structures de coordination
    DAC = "DAC"                          # Dispositif d'Appui à la Coordination
    CPTS = "CPTS"                        # Communauté Professionnelle Territoriale de Santé

    # Autres
    OTHER = "OTHER"                      # Autre type de structure


class TenantStatus(str, Enum):
    """Statuts d'un tenant."""
    ACTIVE = "ACTIVE"                    # Tenant actif, accès autorisé
    SUSPENDED = "SUSPENDED"              # Suspendu (impayé, maintenance...)
    TERMINATED = "TERMINATED"            # Résilié définitivement


# =============================================================================
# MODULE: SUBSCRIPTION - Abonnements (existant, complété)
# =============================================================================

class SubscriptionPlan(str, Enum):
    """Plans d'abonnement disponibles."""
    S = "S"                              # 1-200 patients
    M = "M"                              # 201-500 patients
    L = "L"                              # 501-1500 patients
    XL = "XL"                            # 1501-3000 patients
    ENTERPRISE = "ENTERPRISE"            # 3000+ patients, sur devis


class SubscriptionStatus(str, Enum):
    """Statuts possibles d'un abonnement."""
    TRIAL = "TRIAL"                      # Période d'essai
    ACTIVE = "ACTIVE"                    # Abonnement actif
    PAST_DUE = "PAST_DUE"                # Paiement en retard
    CANCELLED = "CANCELLED"              # Abonnement annulé


class BillingCycle(str, Enum):
    """Cycles de facturation."""
    MONTHLY = "MONTHLY"                  # Mensuel
    QUARTERLY = "QUARTERLY"              # Trimestriel
    YEARLY = "YEARLY"                    # Annuel


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Organization
    "EntityType",
    "IntegrationType",
    "OrganizationModel",
    "TerritoryType",

    # User
    "ProfessionCategory",
    "RoleName",
    "ContractType",
    "PermissionCategory",  # NOUVEAU v4.3

    # Patient
    "PatientStatus",
    "AccessType",
    "GirLevel",
    "VitalType",
    "VitalStatus",
    "VitalSource",
    "DeviceType",
    "EvaluationSchemaType",
    "DocumentType",
    "DocumentFormat",

    # Evaluation patient
    "EvaluationStatus",
    "EvaluationSessionStatus",
    "SyncStatus",
    "AggirVariableCode",
    "AggirSubVariableCode",
    "AggirResultLetter",

    # Coordination (existant)
    "CoordinationCategory",

    # Catalog
    "ServiceCategory",
    "ServiceType",
    "ServiceUnit",

    # CarePlan
    "CarePlanStatus",
    "FrequencyType",
    "ServicePriority",
    "AssignmentStatus",

    # Interventions
    "InterventionStatus",

    # Tenant (NOUVEAU v4.1)
    "TenantType",
    "TenantStatus",

    # Subscription
    "SubscriptionPlan",
    "SubscriptionStatus",
    "BillingCycle",
]
