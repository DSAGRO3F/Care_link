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
    SSIAD = "SSIAD"  # Service de Soins Infirmiers À Domicile
    SAAD = "SAAD"  # Service d'Aide et d'Accompagnement à Domicile
    SAD = "SAD"  # Service d'Aide à Domicile
    SPASAD = "SPASAD"  # Service Polyvalent d'Aide et de Soins À Domicile
    SAP = "SAP"  # Service À la Personne

    # Établissements pour personnes âgées
    EHPAD = "EHPAD"  # Établissement d'Hébergement pour Personnes Âgées Dépendantes
    RESIDENCE_AUTONOMIE = "RESIDENCE_AUTONOMIE"  # Ex-logement foyer
    ACCUEIL_JOUR = "ACCUEIL_JOUR"  # Accueil de jour

    # Établissements pour personnes handicapées
    FAM = "FAM"  # Foyer d'Accueil Médicalisé
    MAS = "MAS"  # Maison d'Accueil Spécialisée
    SESSAD = "SESSAD"  # Service d'Éducation Spéciale et de Soins À Domicile
    IME = "IME"  # Institut Médico-Éducatif
    ESAT = "ESAT"  # Établissement et Service d'Aide par le Travail

    # Structures de coordination et groupements
    GCSMS = "GCSMS"  # Groupement de Coopération Sociale et Médico-Sociale
    GTSMS = "GTSMS"  # Groupement Territorial Social et Médico-Social (loi Bien Vieillir 2024)
    DAC = "DAC"  # Dispositif d'Appui à la Coordination
    CPTS = "CPTS"  # Communauté Professionnelle Territoriale de Santé
    PCPE = "PCPE"  # Pôle de Compétences et de Prestations Externalisées
    PCO = "PCO"  # Plateforme de Coordination et d'Orientation

    # Établissements sanitaires
    HOSPITAL = "HOSPITAL"  # Hôpital
    CLINIC = "CLINIC"  # Clinique
    CSI = "CSI"  # Centre de Soins Infirmiers
    HAD = "HAD"  # Hospitalisation À Domicile

    # Autres
    HALTE_REPIT = "HALTE_REPIT"  # Halte répit
    FORMATION = "FORMATION"  # Organisme de formation
    OTHER = "OTHER"  # Autre

    # Structures rattachées à un SSIAD, SSAD, ... portent le même SIRET que leur entité de rattachement
    ANTENNE = "ANTENNE"
    BUREAU = "BUREAU"
    AGENCE = "AGENCE"


class IntegrationType(str, Enum):
    """Types d'intégration dans un groupement."""

    MANAGED = "MANAGED"  # Intégré (gestion complète par le GCSMS)
    FEDERATED = "FEDERATED"  # Fédéré (autonomie avec coordination)
    CONVENTION = "CONVENTION"  # Conventionné (partenariat externe)
    FINANCIAL_CONTROL = "FINANCIAL_CONTROL"  # Contrôle financier uniquement


class OrganizationModel(str, Enum):
    """Modèles d'organisation des groupements."""

    INTEGRATED = "INTEGRATED"  # Intégré (direction unique)
    FEDERATED = "FEDERATED"  # Fédéré (directions multiples coordonnées)
    HYBRID = "HYBRID"  # Hybride (mix des deux)


class TerritoryType(str, Enum):
    """Types de zones géographiques."""

    COMMUNE = "COMMUNE"  # Commune
    EPCI = "EPCI"  # Intercommunalité
    DEPARTEMENT = "DEPARTEMENT"  # Département
    REGION = "REGION"  # Région
    CUSTOM = "CUSTOM"  # Zone personnalisée (polygone)


# =============================================================================
# MODULE: USER - Utilisateurs et professions
# =============================================================================


class ProfessionCategory(str, Enum):
    """Catégories de professions."""

    MEDICAL = "MEDICAL"  # Médecins
    PARAMEDICAL = "PARAMEDICAL"  # Infirmiers, aides-soignants, kinés...
    ADMINISTRATIVE = "ADMINISTRATIVE"  # Secrétaires, coordinateurs...
    SOCIAL = "SOCIAL"  # Assistants sociaux, éducateurs...


class RoleName(str, Enum):
    """
    Noms des rôles fonctionnels système (S3).

    Les rôles expriment une responsabilité dans CareLink, pas une profession.
    La profession (diplôme d'État) est portée par la table `professions`.

    Exemple : Marie est IDE (profession) + COORDINATEUR (rôle).
    """

    ADMIN = "ADMIN"  # Administrateur du tenant
    COORDINATEUR = "COORDINATEUR"  # Coordinateur de parcours de soins
    REFERENT = "REFERENT"  # Référent patient désigné
    EVALUATEUR = "EVALUATEUR"  # Habilité aux évaluations AGGIR
    INTERVENANT = "INTERVENANT"  # Intervenant ponctuel (lecture seule)


class ContractType(str, Enum):
    """Types de contrats de travail."""

    SALARIE = "SALARIE"  # Salarié CDI/CDD
    LIBERAL = "LIBERAL"  # Professionnel libéral
    VACATION = "VACATION"  # Vacataire
    REMPLACEMENT = "REMPLACEMENT"  # Remplaçant
    BENEVOLE = "BENEVOLE"  # Bénévole
    STAGIAIRE = "STAGIAIRE"  # Stagiaire
    MUTUAL_POOL = "MUTUAL_POOL"  # Pool mutualisé (GCSMS)


class PermissionCategory(str, Enum):
    """
    Catégories de permissions pour le regroupement dans l'UI.

    Utilisé pour organiser les permissions par domaine fonctionnel.
    """

    ADMIN = "ADMIN"  # Permissions administrateur
    PATIENT = "PATIENT"  # Gestion des patients
    EVALUATION = "EVALUATION"  # Évaluations AGGIR et autres
    VITALS = "VITALS"  # Constantes vitales
    USER = "USER"  # Gestion des utilisateurs
    COORDINATION = "COORDINATION"  # Carnet de coordination
    CAREPLAN = "CAREPLAN"  # Plans d'aide
    ACCESS = "ACCESS"  # Gestion des accès RGPD
    ROLE = "ROLE"  # Gestion des rôles


# =============================================================================
# MODULE: PATIENT - Dossier patient
# =============================================================================


class PatientStatus(str, Enum):
    """Statuts d'un patient."""

    ACTIVE = "ACTIVE"  # Patient actif en prise en charge
    ARCHIVED = "ARCHIVED"  # Dossier archivé
    DECEASED = "DECEASED"  # Patient décédé
    TRANSFERRED = "TRANSFERRED"  # Transféré vers autre structure


class AccessType(str, Enum):
    """Types d'accès au dossier patient."""

    READ = "READ"  # Lecture seule
    WRITE = "WRITE"  # Lecture + écriture
    FULL = "FULL"  # Accès complet (inclut suppression)


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

    FC = "FC"  # Fréquence cardiaque (bpm)
    TA_SYS = "TA_SYS"  # Tension artérielle systolique (mmHg)
    TA_DIA = "TA_DIA"  # Tension artérielle diastolique (mmHg)
    SPO2 = "SPO2"  # Saturation en oxygène (%)
    TEMPERATURE = "TEMPERATURE"  # Température (°C)
    POIDS = "POIDS"  # Poids (kg)
    GLYCEMIE = "GLYCEMIE"  # Glycémie (g/L ou mmol/L)
    DOULEUR = "DOULEUR"  # Échelle de douleur (0-10)
    FREQUENCE_RESPIRATOIRE = "FREQUENCE_RESPIRATOIRE"  # FR (cycles/min)
    DIURESE = "DIURESE"  # Diurèse (mL/24h)


class VitalStatus(str, Enum):
    """Statuts par rapport aux seuils."""

    NORMAL = "NORMAL"  # Dans les normes
    LOW = "LOW"  # En dessous du seuil
    HIGH = "HIGH"  # Au dessus du seuil
    CRITICAL = "CRITICAL"  # Critique (très hors normes)


class VitalSource(str, Enum):
    """Sources des mesures de constantes."""

    MANUAL = "MANUAL"  # Saisie manuelle
    WITHINGS = "WITHINGS"  # Balance/montre Withings
    APPLE_WATCH = "APPLE_WATCH"  # Apple Watch
    FREESTYLE_LIBRE = "FREESTYLE_LIBRE"  # Capteur glycémie FreeStyle
    OTHER_DEVICE = "OTHER_DEVICE"  # Autre device connecté


class DeviceType(str, Enum):
    """Types d'appareils connectés."""

    SCALE = "SCALE"  # Balance connectée
    BLOOD_PRESSURE = "BLOOD_PRESSURE"  # Tensiomètre connecté
    PULSE_OXIMETER = "PULSE_OXIMETER"  # Oxymètre de pouls
    THERMOMETER = "THERMOMETER"  # Thermomètre connecté
    GLUCOMETER = "GLUCOMETER"  # Glucomètre connecté
    WATCH = "WATCH"  # Montre connectée
    OTHER = "OTHER"  # Autre appareil


class EvaluationSchemaType(str, Enum):
    """Types de schémas d'évaluation."""

    AGGIR = "AGGIR"  # Grille AGGIR
    PATHOS = "PATHOS"  # Modèle PATHOS
    CUSTOM = "CUSTOM"  # Grille personnalisée


class DocumentType(str, Enum):
    """Types de documents du dossier patient."""

    PRESCRIPTION = "PRESCRIPTION"  # Ordonnance
    CARE_PROTOCOL = "CARE_PROTOCOL"  # Protocole de soins
    LAB_RESULT = "LAB_RESULT"  # Résultat de laboratoire
    IMAGING = "IMAGING"  # Imagerie médicale
    CORRESPONDENCE = "CORRESPONDENCE"  # Courrier médical
    CONSENT = "CONSENT"  # Formulaire de consentement
    ID_DOCUMENT = "ID_DOCUMENT"  # Pièce d'identité
    INSURANCE = "INSURANCE"  # Document d'assurance
    OTHER = "OTHER"  # Autre


class DocumentFormat(str, Enum):
    """Formats de fichiers autorisés."""

    PDF = "PDF"
    JPEG = "JPEG"
    PNG = "PNG"
    DICOM = "DICOM"
    HL7 = "HL7"


# =============================================================================
# MODULE: EVALUATION - Évaluations patient
# =============================================================================


class EvaluationStatus(str, Enum):
    """Statuts d'une évaluation."""

    IN_PROGRESS = "IN_PROGRESS"  # En cours de saisie
    COMPLETED = "COMPLETED"  # Terminée
    VALIDATED = "VALIDATED"  # Validée par un responsable
    CANCELLED = "CANCELLED"  # Annulée


class EvaluationSessionStatus(str, Enum):
    """Statuts d'une session d'évaluation."""

    DRAFT = "DRAFT"  # Brouillon
    IN_PROGRESS = "IN_PROGRESS"  # En cours
    COMPLETED = "COMPLETED"  # Terminée
    VALIDATED = "VALIDATED"  # Validée


class SyncStatus(str, Enum):
    """Statuts de synchronisation."""

    PENDING = "PENDING"  # En attente
    SYNCED = "SYNCED"  # Synchronisé
    ERROR = "ERROR"  # Erreur de synchronisation


class AggirVariableCode(str, Enum):
    """Codes des variables discriminantes AGGIR."""

    COHERENCE = "COHERENCE"
    ORIENTATION = "ORIENTATION"
    TOILETTE = "TOILETTE"
    HABILLAGE = "HABILLAGE"
    ALIMENTATION = "ALIMENTATION"
    ELIMINATION = "ELIMINATION"
    TRANSFERTS = "TRANSFERTS"
    DEPLACEMENT_INTERIEUR = "DEPLACEMENT_INTERIEUR"
    DEPLACEMENT_EXTERIEUR = "DEPLACEMENT_EXTERIEUR"
    COMMUNICATION = "COMMUNICATION"


class AggirSubVariableCode(str, Enum):
    """Codes des sous-variables AGGIR."""

    # Toilette
    TOILETTE_HAUT = "TOILETTE_HAUT"
    TOILETTE_BAS = "TOILETTE_BAS"
    # Habillage
    HABILLAGE_HAUT = "HABILLAGE_HAUT"
    HABILLAGE_MOYEN = "HABILLAGE_MOYEN"
    HABILLAGE_BAS = "HABILLAGE_BAS"
    # Alimentation
    ALIMENTATION_SE_SERVIR = "ALIMENTATION_SE_SERVIR"
    ALIMENTATION_MANGER = "ALIMENTATION_MANGER"
    # Élimination
    ELIMINATION_URINAIRE = "ELIMINATION_URINAIRE"
    ELIMINATION_FECALE = "ELIMINATION_FECALE"


class AggirResultLetter(str, Enum):
    """Lettres de résultat AGGIR (A, B, C)."""

    A = "A"  # Fait seul, spontanément, totalement, habituellement, correctement
    B = "B"  # Fait partiellement, ou non habituellement, ou non correctement
    C = "C"  # Ne fait pas


# =============================================================================
# MODULE: COORDINATION
# =============================================================================


class CoordinationCategory(str, Enum):
    """Catégories d'entrées de coordination."""

    OBSERVATION = "OBSERVATION"  # Observation clinique
    TRANSMISSION = "TRANSMISSION"  # Transmission ciblée
    INCIDENT = "INCIDENT"  # Incident ou événement indésirable
    EVOLUTION = "EVOLUTION"  # Évolution de l'état du patient


# =============================================================================
# MODULE: CATALOG - Services de soins
# =============================================================================


class ServiceCategory(str, Enum):
    """Catégories de services."""

    NURSING = "NURSING"  # Soins infirmiers
    PERSONAL_CARE = "PERSONAL_CARE"  # Aide à la personne (toilette, habillage)
    DOMESTIC = "DOMESTIC"  # Aide domestique (ménage, courses)
    REHABILITATION = "REHABILITATION"  # Rééducation (kiné, ergo)
    SOCIAL = "SOCIAL"  # Accompagnement social
    MEDICAL = "MEDICAL"  # Actes médicaux
    COORDINATION = "COORDINATION"  # Coordination de parcours


class ServiceType(str, Enum):
    """Types de services."""

    INDIVIDUAL = "INDIVIDUAL"  # Service individuel
    COLLECTIVE = "COLLECTIVE"  # Service collectif
    TELECARE = "TELECARE"  # Télésoin


class ServiceUnit(str, Enum):
    """Unités de facturation des services."""

    HOUR = "HOUR"  # À l'heure
    HALF_HOUR = "HALF_HOUR"  # À la demi-heure
    ACT = "ACT"  # À l'acte
    DAY = "DAY"  # À la journée
    PACKAGE = "PACKAGE"  # Forfait


# =============================================================================
# MODULE: CAREPLAN - Plans d'aide
# =============================================================================


class CarePlanStatus(str, Enum):
    """Statuts d'un plan d'aide."""

    DRAFT = "DRAFT"  # Brouillon en cours de création
    PENDING_VALIDATION = "PENDING_VALIDATION"  # En attente de validation
    ACTIVE = "ACTIVE"  # Actif et en cours d'exécution
    SUSPENDED = "SUSPENDED"  # Suspendu temporairement
    COMPLETED = "COMPLETED"  # Terminé (fin de prise en charge)
    CANCELLED = "CANCELLED"  # Annulé


class FrequencyType(str, Enum):
    """Types de fréquence pour les services."""

    DAILY = "DAILY"  # Tous les jours
    WEEKLY = "WEEKLY"  # X fois par semaine
    SPECIFIC_DAYS = "SPECIFIC_DAYS"  # Jours spécifiques (Lun, Mar, Ven...)
    MONTHLY = "MONTHLY"  # X fois par mois
    ON_DEMAND = "ON_DEMAND"  # À la demande


class ServicePriority(str, Enum):
    """Priorité d'un service dans le plan."""

    LOW = "LOW"  # Basse priorité (confort)
    MEDIUM = "MEDIUM"  # Priorité normale
    HIGH = "HIGH"  # Haute priorité (important)
    CRITICAL = "CRITICAL"  # Critique (vital)


class AssignmentStatus(str, Enum):
    """Statuts d'affectation d'un service à un professionnel."""

    UNASSIGNED = "UNASSIGNED"  # Non affecté
    PENDING = "PENDING"  # Affectation en attente de confirmation
    ASSIGNED = "ASSIGNED"  # Affecté
    CONFIRMED = "CONFIRMED"  # Confirmé par le professionnel
    REJECTED = "REJECTED"  # Refusé par le professionnel


# =============================================================================
# MODULE: COORDINATION - Interventions planifiées
# =============================================================================


class InterventionStatus(str, Enum):
    """Statuts d'une intervention planifiée."""

    SCHEDULED = "SCHEDULED"  # Planifiée
    CONFIRMED = "CONFIRMED"  # Confirmée
    IN_PROGRESS = "IN_PROGRESS"  # En cours
    COMPLETED = "COMPLETED"  # Terminée
    CANCELLED = "CANCELLED"  # Annulée
    MISSED = "MISSED"  # Manquée (patient absent, etc.)
    RESCHEDULED = "RESCHEDULED"  # Reprogrammée


# =============================================================================
# MODULE: TENANT - Multi-tenant (v4.1, mis à jour v4.4)
# =============================================================================


class TenantType(str, Enum):
    """Types de clients/locataires.

    Reprend les principaux types d'EntityType qui peuvent être
    des clients directs de la plateforme CareLink.
    """

    # Groupements fédérateurs (clients principaux)
    GCSMS = "GCSMS"  # Groupement de Coopération Sociale et Médico-Sociale
    GTSMS = "GTSMS"  # Groupement Territorial Social et Médico-Social (loi Bien Vieillir 2024)

    # Services à domicile (clients indépendants ou membres d'un groupement)
    SSIAD = "SSIAD"  # Service de Soins Infirmiers À Domicile
    SAAD = "SAAD"  # Service d'Aide et d'Accompagnement à Domicile
    SPASAD = "SPASAD"  # Service Polyvalent d'Aide et de Soins À Domicile

    # Établissements (clients indépendants ou membres d'un groupement)
    EHPAD = "EHPAD"  # Établissement d'Hébergement pour Personnes Âgées Dépendantes

    # Structures de coordination
    DAC = "DAC"  # Dispositif d'Appui à la Coordination
    CPTS = "CPTS"  # Communauté Professionnelle Territoriale de Santé

    # Autres
    OTHER = "OTHER"  # Autre type de structure


class TenantStatus(str, Enum):
    """Statuts d'un tenant."""

    ACTIVE = "ACTIVE"  # Tenant actif, accès autorisé
    SUSPENDED = "SUSPENDED"  # Suspendu (impayé, maintenance...)
    TERMINATED = "TERMINATED"  # Résilié définitivement


# =============================================================================
# MODULE: SUBSCRIPTION - Abonnements
# =============================================================================


class SubscriptionPlan(str, Enum):
    """Plans d'abonnement disponibles."""

    S = "S"  # 1-200 patients
    M = "M"  # 201-500 patients
    L = "L"  # 501-1500 patients
    XL = "XL"  # 1501-3000 patients
    ENTERPRISE = "ENTERPRISE"  # 3000+ patients, sur devis


class SubscriptionStatus(str, Enum):
    """Statuts possibles d'un abonnement."""

    TRIAL = "TRIAL"  # Période d'essai
    ACTIVE = "ACTIVE"  # Abonnement actif
    PAST_DUE = "PAST_DUE"  # Paiement en retard
    CANCELLED = "CANCELLED"  # Abonnement annulé


class BillingCycle(str, Enum):
    """Cycles de facturation."""

    MONTHLY = "MONTHLY"  # Mensuel
    QUARTERLY = "QUARTERLY"  # Trimestriel
    YEARLY = "YEARLY"  # Annuel


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
    "PermissionCategory",
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
    # Coordination
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
    # Tenant (v4.1, mis à jour v4.4)
    "TenantType",
    "TenantStatus",
    # Subscription
    "SubscriptionPlan",
    "SubscriptionStatus",
    "BillingCycle",
]
