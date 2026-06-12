"""
Enums CareLink - Définitions de tous les types énumérés.

Ce module centralise tous les enums utilisés dans les modèles SQLAlchemy.
Ils sont convertis en types ENUM PostgreSQL via SQLEnum.
"""

from enum import StrEnum


# =============================================================================
# MODULE: ORGANIZATION - Structures organisationnelles
# =============================================================================


class EntityType(StrEnum):
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


class IntegrationType(StrEnum):
    """Types d'intégration dans un groupement."""

    MANAGED = "MANAGED"  # Intégré (gestion complète par le GCSMS)
    FEDERATED = "FEDERATED"  # Fédéré (autonomie avec coordination)
    CONVENTION = "CONVENTION"  # Conventionné (partenariat externe)
    FINANCIAL_CONTROL = "FINANCIAL_CONTROL"  # Contrôle financier uniquement


class OrganizationModel(StrEnum):
    """Modèles d'organisation des groupements."""

    INTEGRATED = "INTEGRATED"  # Intégré (direction unique)
    FEDERATED = "FEDERATED"  # Fédéré (directions multiples coordonnées)
    HYBRID = "HYBRID"  # Hybride (mix des deux)


class TerritoryType(StrEnum):
    """Types de zones géographiques."""

    COMMUNE = "COMMUNE"  # Commune
    EPCI = "EPCI"  # Intercommunalité
    DEPARTEMENT = "DEPARTEMENT"  # Département
    REGION = "REGION"  # Région
    CUSTOM = "CUSTOM"  # Zone personnalisée (polygone)


# =============================================================================
# MODULE: USER - Utilisateurs et professions
# =============================================================================


class ProfessionCategory(StrEnum):
    """Catégories de professions."""

    MEDICAL = "MEDICAL"  # Médecins
    PARAMEDICAL = "PARAMEDICAL"  # Infirmiers, aides-soignants, kinés...
    ADMINISTRATIVE = "ADMINISTRATIVE"  # Secrétaires, coordinateurs...
    SOCIAL = "SOCIAL"  # Assistants sociaux, éducateurs...


class RoleName(StrEnum):
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
    # 🆕 B40-J1 — Profils externes Phase 4 bis (cf. note_cadrage_phase4bis §6.6.2)
    VALIDATEUR_DEPARTMENT = "VALIDATEUR_DEPARTMENT"  # Agent département (instructeur APA)
    FAMILY_REFERENT = "FAMILY_REFERENT"  # Compte famille référent (lecture minimisée)


class ContractType(StrEnum):
    """Types de contrats de travail."""

    SALARIE = "SALARIE"  # Salarié CDI/CDD
    LIBERAL = "LIBERAL"  # Professionnel libéral
    VACATION = "VACATION"  # Vacataire
    REMPLACEMENT = "REMPLACEMENT"  # Remplaçant
    BENEVOLE = "BENEVOLE"  # Bénévole
    STAGIAIRE = "STAGIAIRE"  # Stagiaire
    MUTUAL_POOL = "MUTUAL_POOL"  # Pool mutualisé (GCSMS)


class PermissionCategory(StrEnum):
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
    CATALOG = "CATALOG"
    SCHEDULE = "SCHEDULE"
    CAREPLAN = "CAREPLAN"  # Plans d'aide
    ACCESS = "ACCESS"  # Gestion des accès RGPD
    ROLE = "ROLE"  # Gestion des rôles
    VALIDATION = "VALIDATION"  # 🆕 B40-J1 — Portail valideur générique (Phase 4 bis)


# =============================================================================
# MODULE: PATIENT - Dossier patient
# =============================================================================


class PatientStatus(StrEnum):
    """Statuts d'un patient."""

    ACTIVE = "ACTIVE"  # Patient actif en prise en charge
    ARCHIVED = "ARCHIVED"  # Dossier archivé
    DECEASED = "DECEASED"  # Patient décédé
    TRANSFERRED = "TRANSFERRED"  # Transféré vers autre structure


class AccessType(StrEnum):
    """Types d'accès au dossier patient."""

    READ = "READ"  # Lecture seule
    WRITE = "WRITE"  # Lecture + écriture
    FULL = "FULL"  # Accès complet (inclut suppression)


class GirLevel(StrEnum):
    """Niveaux de la grille AGGIR (Autonomie Gérontologie Groupes Iso-Ressources)."""

    GIR_1 = "GIR_1"  # Dépendance totale, fonctions mentales altérées
    GIR_2 = "GIR_2"  # Dépendance totale, fonctions mentales préservées OU déplacements OK mais cognitif altéré
    GIR_3 = "GIR_3"  # Autonomie mentale, dépendance corporelle partielle
    GIR_4 = "GIR_4"  # Autonomie pour déplacements, aide pour activités corporelles et repas
    GIR_5 = "GIR_5"  # Aide ponctuelle (toilette, repas, ménage)
    GIR_6 = "GIR_6"  # Autonome pour les actes de la vie courante


class VitalType(StrEnum):
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


class VitalStatus(StrEnum):
    """Statuts par rapport aux seuils."""

    NORMAL = "NORMAL"  # Dans les normes
    LOW = "LOW"  # En dessous du seuil
    HIGH = "HIGH"  # Au dessus du seuil
    CRITICAL = "CRITICAL"  # Critique (très hors normes)


class VitalSource(StrEnum):
    """Sources des mesures de constantes."""

    MANUAL = "MANUAL"  # Saisie manuelle
    WITHINGS = "WITHINGS"  # Balance/montre Withings
    APPLE_WATCH = "APPLE_WATCH"  # Apple Watch
    FREESTYLE_LIBRE = "FREESTYLE_LIBRE"  # Capteur glycémie FreeStyle
    OTHER_DEVICE = "OTHER_DEVICE"  # Autre device connecté


class DeviceType(StrEnum):
    """Types d'appareils connectés."""

    SCALE = "SCALE"  # Balance connectée
    BLOOD_PRESSURE = "BLOOD_PRESSURE"  # Tensiomètre connecté
    PULSE_OXIMETER = "PULSE_OXIMETER"  # Oxymètre de pouls
    THERMOMETER = "THERMOMETER"  # Thermomètre connecté
    GLUCOMETER = "GLUCOMETER"  # Glucomètre connecté
    WATCH = "WATCH"  # Montre connectée
    OTHER = "OTHER"  # Autre appareil


class EvaluationSchemaType(StrEnum):
    """Types de schémas d'évaluation."""

    AGGIR = "AGGIR"  # Grille AGGIR
    PATHOS = "PATHOS"  # Modèle PATHOS
    CUSTOM = "CUSTOM"  # Grille personnalisée


class EvaluationStatus(StrEnum):
    """
    Statuts d'une évaluation patient — workflow long AGGIR_FUNDING (B40-J1).

    Workflow : IN_PROGRESS → PENDING_INTERNAL_REVIEW → PENDING_MEDICAL
    → AWAITING_FUNDING_DECISION → VALIDATED | FUNDING_REJECTED.

    Convention sémantique (D4) :
    - PENDING_* : attente active dans CareLink (un acteur doit y agir)
    - AWAITING_* : attente passive (décision se prend hors CareLink)

    Note métier (§2.1 cadrage Phase 4 bis) : l'évaluation AGGIR dans CareLink
    est un objet interne de coordination, jointe en pièce d'instruction au
    dossier APA traité par le département. L'étape AWAITING_FUNDING_DECISION
    n'est pas une attente de validation de l'évaluation, mais une attente
    de la décision APA prise au niveau département.

    Référence : note_cadrage_phase4bis_22_05_2026.md (D3, D4, D5, D9).
    """

    DRAFT = "DRAFT"  # Brouillon en cours de saisie
    IN_PROGRESS = "IN_PROGRESS"  # Évaluation commencée, pas terminée
    PENDING_INTERNAL_REVIEW = (
        "PENDING_INTERNAL_REVIEW"  # 🆕 B40-J1 — Soumise à relecture interne admin GCSMS
    )
    PENDING_MEDICAL = "PENDING_MEDICAL"  # En attente de validation médicale externe
    AWAITING_FUNDING_DECISION = "AWAITING_FUNDING_DECISION"  # 🔄 B40-J1 (ex-PENDING_DEPARTMENTAL) — Décision APA en cours d'instruction au département
    VALIDATED = "VALIDATED"  # Terminal positif — document opposable (D19)
    FUNDING_REJECTED = "FUNDING_REJECTED"  # 🆕 B40-J1 — Terminal négatif (refus APA département)
    OBSOLETE = "OBSOLETE"  # 🆕 B40-J1 — Supersédée par une nouvelle évaluation (filiation B28-like)


class EvaluationSessionStatus(StrEnum):
    """Statuts d'une session d'évaluation."""

    ACTIVE = "ACTIVE"  # Session en cours
    COMPLETED = "COMPLETED"  # Session terminée normalement
    EXPIRED = "EXPIRED"  # Session expirée (timeout)
    CANCELLED = "CANCELLED"  # Session annulée


class AggirVariableCode(StrEnum):
    """Codes des 17 variables AGGIR."""

    COHERENCE = "COHERENCE"
    ORIENTATION = "ORIENTATION"
    TOILETTE = "TOILETTE"
    HABILLAGE = "HABILLAGE"
    ALIMENTATION = "ALIMENTATION"
    ELIMINATION = "ELIMINATION"
    TRANSFERTS = "TRANSFERTS"
    DEPLACEMENTS_INTERIEURS = "DEPLACEMENTS_INTERIEURS"
    DEPLACEMENTS_EXTERIEURS = "DEPLACEMENTS_EXTERIEURS"
    COMMUNICATION = "COMMUNICATION"
    GESTION = "GESTION"
    CUISINE = "CUISINE"
    MENAGE = "MENAGE"
    TRANSPORTS = "TRANSPORTS"
    ACHATS = "ACHATS"
    SUIVI_TRAITEMENT = "SUIVI_TRAITEMENT"
    ACTIVITES_TEMPS_LIBRE = "ACTIVITES_TEMPS_LIBRE"


class AggirSubVariableCode(StrEnum):
    """Codes des sous-variables AGGIR (adverbes)."""

    SPONTANEMENT = "SPONTANEMENT"
    TOTALEMENT = "TOTALEMENT"
    HABITUELLEMENT = "HABITUELLEMENT"
    CORRECTEMENT = "CORRECTEMENT"
    HAUT = "HAUT"
    BAS = "BAS"
    MOYEN = "MOYEN"
    URINAIRE = "URINAIRE"
    FECALE = "FECALE"
    SE_SERVIR = "SE_SERVIR"
    MANGER = "MANGER"


class AggirResultLetter(StrEnum):
    """Résultats possibles d'une variable AGGIR."""

    A = "A"  # Fait seul, totalement, habituellement, correctement
    B = "B"  # Fait partiellement, ou non habituellement, ou non correctement
    C = "C"  # Ne fait pas


class DocumentType(StrEnum):
    """Types de documents générés."""

    PPA = "PPA"  # Plan Personnalisé d'Accompagnement
    PPCS = "PPCS"  # Plan Personnalisé de Coordination en Santé
    EVALUATION_REPORT = "EVALUATION_REPORT"  # Rapport d'évaluation
    COORDINATION_REPORT = "COORDINATION_REPORT"  # Rapport de coordination
    CUSTOM = "CUSTOM"  # Document personnalisé


class DocumentFormat(StrEnum):
    """Formats de documents."""

    PDF = "PDF"
    DOCX = "DOCX"
    HTML = "HTML"


class SyncStatus(StrEnum):
    """Statuts de synchronisation des appareils."""

    CONNECTED = "CONNECTED"  # Connecté et synchronisé
    DISCONNECTED = "DISCONNECTED"  # Déconnecté
    ERROR = "ERROR"  # Erreur de synchronisation
    PENDING = "PENDING"  # En attente de première synchronisation


# =============================================================================
# MODULE: COORDINATION
# =============================================================================


class CoordinationCategory(StrEnum):
    """Catégories d'entrées de coordination."""

    OBSERVATION = "OBSERVATION"  # Observation clinique
    TRANSMISSION = "TRANSMISSION"  # Transmission ciblée
    INCIDENT = "INCIDENT"  # Incident ou événement indésirable
    EVOLUTION = "EVOLUTION"  # Évolution de l'état du patient


# =============================================================================
# MODULE: CATALOG - Services de soins (🔄 v4.17 — SERAFIN-PH)
# =============================================================================


class ServiceDomain(StrEnum):
    """
    Domaines de prestations — niveau 1 de la hiérarchie catalogue.

    Aligné sur la nomenclature SERAFIN-PH (3 grands domaines).
    Chaque domaine regroupe plusieurs catégories de services.

    🆕 v4.17 — Ajout pour structure à 2 niveaux du catalogue.
    """

    SOINS_SANTE = "SOINS_SANTE"  # Soins & Santé (soins infirmiers, médicaux, rééducation)
    AUTONOMIE = "AUTONOMIE"  # Autonomie (hygiène, alimentation, mobilité)
    PARTICIPATION_SOCIALE = "PARTICIPATION_SOCIALE"  # Participation sociale (cadre de vie, administratif, loisirs, transport)


class ServiceCategory(StrEnum):
    """
    Catégories de services — niveau 2 de la hiérarchie catalogue.

    10 catégories alignées SERAFIN-PH, remplaçant les 7 catégories anglaises
    initiales (NURSING, PERSONAL_CARE, DOMESTIC, etc.).

    🔄 v4.17 — Refonte complète pour alignement SERAFIN-PH.

    Correspondance domaine → catégories :
    - SOINS_SANTE : SOINS_INFIRMIERS, SOINS_MEDICAUX, REEDUCATION
    - AUTONOMIE : HYGIENE_ENTRETIEN_PERSONNEL, ALIMENTATION, MOBILITE_TRANSFERTS
    - PARTICIPATION_SOCIALE : ENTRETIEN_CADRE_VIE, ACCOMPAGNEMENT_ADMINISTRATIF,
                              VIE_SOCIALE_LOISIRS, TRANSPORT
    """

    # Domaine : Soins & Santé
    SOINS_INFIRMIERS = "SOINS_INFIRMIERS"  # Injections, pansements, surveillance...
    SOINS_MEDICAUX = "SOINS_MEDICAUX"  # Consultations, distribution médicaments...
    REEDUCATION = "REEDUCATION"  # Kiné, orthophonie, ergothérapie...

    # Domaine : Autonomie
    HYGIENE_ENTRETIEN_PERSONNEL = "HYGIENE_ENTRETIEN_PERSONNEL"  # Toilette, habillage, change...
    ALIMENTATION = "ALIMENTATION"  # Aide repas, préparation, portage...
    MOBILITE_TRANSFERTS = "MOBILITE_TRANSFERTS"  # Transferts, déplacements, prévention escarres...

    # Domaine : Participation sociale
    ENTRETIEN_CADRE_VIE = "ENTRETIEN_CADRE_VIE"  # Ménage, courses, linge...
    ACCOMPAGNEMENT_ADMINISTRATIF = (
        "ACCOMPAGNEMENT_ADMINISTRATIF"  # Démarches, coordination parcours...
    )
    VIE_SOCIALE_LOISIRS = "VIE_SOCIALE_LOISIRS"  # Stimulation cognitive, sorties, soutien psy...
    TRANSPORT = "TRANSPORT"  # Accompagnement RDV, transport social, téléassistance...


# Mapping domaine → catégories autorisées (validé côté API)
DOMAIN_CATEGORY_MAP: dict[ServiceDomain, list[ServiceCategory]] = {
    ServiceDomain.SOINS_SANTE: [
        ServiceCategory.SOINS_INFIRMIERS,
        ServiceCategory.SOINS_MEDICAUX,
        ServiceCategory.REEDUCATION,
    ],
    ServiceDomain.AUTONOMIE: [
        ServiceCategory.HYGIENE_ENTRETIEN_PERSONNEL,
        ServiceCategory.ALIMENTATION,
        ServiceCategory.MOBILITE_TRANSFERTS,
    ],
    ServiceDomain.PARTICIPATION_SOCIALE: [
        ServiceCategory.ENTRETIEN_CADRE_VIE,
        ServiceCategory.ACCOMPAGNEMENT_ADMINISTRATIF,
        ServiceCategory.VIE_SOCIALE_LOISIRS,
        ServiceCategory.TRANSPORT,
    ],
}

# Mapping inverse : catégorie → domaine (dérivé automatiquement)
CATEGORY_DOMAIN_MAP: dict[ServiceCategory, ServiceDomain] = {
    cat: domain for domain, cats in DOMAIN_CATEGORY_MAP.items() for cat in cats
}


class ServiceType(StrEnum):
    """Types de services."""

    INDIVIDUAL = "INDIVIDUAL"  # Service individuel
    COLLECTIVE = "COLLECTIVE"  # Service collectif
    TELECARE = "TELECARE"  # Télésoin


class ServiceUnit(StrEnum):
    """Unités de facturation des services."""

    HOUR = "HOUR"  # À l'heure
    HALF_HOUR = "HALF_HOUR"  # À la demi-heure
    ACT = "ACT"  # À l'acte
    DAY = "DAY"  # À la journée
    PACKAGE = "PACKAGE"  # Forfait


# =============================================================================
# MODULE: CAREPLAN - Plans d'aide
# =============================================================================


class CarePlanStatus(StrEnum):
    """Statuts d'un plan d'aide."""

    DRAFT = "DRAFT"  # Brouillon en cours de création
    PENDING_VALIDATION = "PENDING_VALIDATION"  # En attente de validation
    ACTIVE = "ACTIVE"  # Actif et en cours d'exécution
    SUSPENDED = "SUSPENDED"  # Suspendu temporairement
    COMPLETED = "COMPLETED"  # Terminé (fin de prise en charge)
    CANCELLED = "CANCELLED"  # Annulé


class FrequencyType(StrEnum):
    """Types de fréquence pour les services."""

    DAILY = "DAILY"  # Tous les jours
    WEEKLY = "WEEKLY"  # X fois par semaine
    SPECIFIC_DAYS = "SPECIFIC_DAYS"  # Jours spécifiques (Lun, Mar, Ven...)
    MONTHLY = "MONTHLY"  # X fois par mois
    ON_DEMAND = "ON_DEMAND"  # À la demande


class ServicePriority(StrEnum):
    """Priorité d'un service dans le plan."""

    LOW = "LOW"  # Basse priorité (confort)
    MEDIUM = "MEDIUM"  # Priorité normale
    HIGH = "HIGH"  # Haute priorité (important)
    CRITICAL = "CRITICAL"  # Critique (vital)


class AssignmentStatus(StrEnum):
    """Statuts d'affectation d'un service à un professionnel."""

    UNASSIGNED = "UNASSIGNED"  # Non affecté
    PENDING = "PENDING"  # Affectation en attente de confirmation
    ASSIGNED = "ASSIGNED"  # Affecté
    CONFIRMED = "CONFIRMED"  # Confirmé par le professionnel
    REJECTED = "REJECTED"  # Refusé par le professionnel


class CarePlanServiceStatus(StrEnum):
    """Statut opérationnel d'un service dans un plan d'aide."""

    ACTIVE = "ACTIVE"  # Service actif et en cours
    PAUSED = "PAUSED"  # Service temporairement en pause
    COMPLETED = "COMPLETED"  # Service terminé


class RevisionReason(StrEnum):
    """
    Motifs de révision d'un plan d'aide (B28b).

    Enum v1 issu de la note de cadrage B28 §5.1 (décision 23, 23/04/2026).
    OTHER positionné comme filet de sécurité pour les cas non anticipés.
    Enrichissement post-retours IDEC terrain → backlog B33.

    Référence métier : HAS/ANESM 2008 (recommandations co-construction PPA),
    article D.312-3 du CASF.
    """

    HOSPITAL_RETURN = "HOSPITAL_RETURN"  # Retour d'hospitalisation avec ajustements
    HEALTH_DETERIORATION = "HEALTH_DETERIORATION"  # Dégradation de l'état de santé
    HEALTH_STABILIZATION = "HEALTH_STABILIZATION"  # Stabilisation / amélioration
    USER_REQUEST = "USER_REQUEST"  # Demande de l'usager / représentant légal
    CAREGIVER_REQUEST = "CAREGIVER_REQUEST"  # Demande d'un proche aidant
    ANNUAL_REVIEW = "ANNUAL_REVIEW"  # Révision annuelle (rythme HAS/ANESM)
    OTHER = "OTHER"  # Autre motif (à préciser dans revision_comment)


# =============================================================================
# MODULE: COORDINATION - Interventions planifiées
# =============================================================================


class InterventionStatus(StrEnum):
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


class TenantType(StrEnum):
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


class TenantStatus(StrEnum):
    """Statuts d'un tenant."""

    ACTIVE = "ACTIVE"  # Tenant actif, accès autorisé
    SUSPENDED = "SUSPENDED"  # Suspendu (impayé, maintenance...)
    TERMINATED = "TERMINATED"  # Résilié définitivement


# =============================================================================
# MODULE: SUBSCRIPTION - Abonnements
# =============================================================================


class SubscriptionPlan(StrEnum):
    """Plans d'abonnement disponibles."""

    S = "S"  # 1-200 patients
    M = "M"  # 201-500 patients
    L = "L"  # 501-1500 patients
    XL = "XL"  # 1501-3000 patients
    ENTERPRISE = "ENTERPRISE"  # 3000+ patients, sur devis


class SubscriptionStatus(StrEnum):
    """Statuts possibles d'un abonnement."""

    TRIAL = "TRIAL"  # Période d'essai
    ACTIVE = "ACTIVE"  # Abonnement actif
    PAST_DUE = "PAST_DUE"  # Paiement en retard
    CANCELLED = "CANCELLED"  # Abonnement annulé


class BillingCycle(StrEnum):
    """Cycles de facturation."""

    MONTHLY = "MONTHLY"  # Mensuel
    QUARTERLY = "QUARTERLY"  # Trimestriel
    YEARLY = "YEARLY"  # Annuel


# =============================================================================
# MODULE: VALIDATION - Portail valideur générique (Phase 4 bis B40-J1)
# =============================================================================


class ValidationWorkflowType(StrEnum):
    """
    Type de workflow de validation.

    Détermine la nature de l'objet validé (B40-J1 §6 étape 4, décision PS-9).
    V1 limitée aux deux workflows ci-dessous ; extensible (LIAISON_NOTEBOOK,
    SYNTHESIS_PATIENT, etc.) sans changement de schéma.
    """

    AGGIR_FUNDING = "AGGIR_FUNDING"  # Évaluation AGGIR (instruction APA)
    COORDINATION_DOSSIER = "COORDINATION_DOSSIER"  # Plan d'aide / dossier de coordination


class ValidationStage(StrEnum):
    """
    Étape courante du workflow de validation.

    Workflow Phase 4 bis AGGIR_FUNDING : INTERNAL_REVIEW → MEDICAL_REVIEW
    → FUNDING_REVIEW. Simplifié pour COORDINATION_DOSSIER selon configuration.
    """

    INTERNAL_REVIEW = "INTERNAL_REVIEW"  # Relecture admin GCSMS
    MEDICAL_REVIEW = "MEDICAL_REVIEW"  # Validation médicale externe
    FUNDING_REVIEW = "FUNDING_REVIEW"  # Décision département (APA)


class ValidationDecision(StrEnum):
    """
    Issue d'une demande de validation.

    Référence : plan B40-J1 §6 étape 4.
    """

    VALIDATED = "VALIDATED"  # Décision favorable
    INVALIDATED = "INVALIDATED"  # Décision défavorable (invalidation_reason obligatoire)
    MORE_INFO_REQUESTED = "MORE_INFO_REQUESTED"  # Information complémentaire demandée
    WITHDRAWN = "WITHDRAWN"  # Retrait par le soumetteur avant décision


class InvalidationReason(StrEnum):
    """
    Catégorie structurée du motif d'invalidation.

    Complémentaire du motif libre `decision_motif` — permet l'agrégation
    statistique et le tri par typologie d'erreur côté UI valideur.
    """

    INCOMPLETE_INFO = "INCOMPLETE_INFO"  # Informations manquantes
    CLINICAL_DISAGREEMENT = "CLINICAL_DISAGREEMENT"  # Désaccord clinique
    OUT_OF_SCOPE = "OUT_OF_SCOPE"  # Hors périmètre de validation
    OTHER = "OTHER"  # Autre (motif libre obligatoire)


class NotificationType(StrEnum):
    """
    Type structuré de notification utilisateur.

    Permet l'agrégation et le filtrage côté UI (notification center).
    Référence : plan B40-J1 §6 étape 3, D10 du cadrage Phase 4 bis.
    """

    VALIDATION_REQUEST_RECEIVED = "VALIDATION_REQUEST_RECEIVED"  # Valideur reçoit une demande
    VALIDATION_DECISION_TAKEN = "VALIDATION_DECISION_TAKEN"  # Soumetteur reçoit la décision
    VALIDATION_INFO_REQUESTED = "VALIDATION_INFO_REQUESTED"  # Soumetteur reçoit demande d'info
    EVALUATION_FUNDING_REJECTED = "EVALUATION_FUNDING_REJECTED"  # Acteurs notifiés du refus APA


class ExchangeActionType(StrEnum):
    """Type d'action d'une entrée du fil d'échange (B40-J3).

    Une entrée du fil est à la fois un message ET, le cas échéant, une décision :
    c'est `action_type` qui distingue le simple commentaire de l'acte décisionnel.

    - SUBMIT        : soumission initiale — ouvre le fil d'un nouveau dossier
    - COMMENT       : message simple, pas de transition de workflow
    - RESUBMIT      : le soumetteur renvoie après une demande de complément
    - VALIDATE      : geste de validation (absorbé par transmit_* en workflow long)
    - REQUEST_INFO  : demande de complément (réversible — la boucle continue)
    - INVALIDATE    : refus (terminal, justification obligatoire)
    - TRANSMIT      : transition d'étape (frontière de VR : interne→médical→financement)
    """

    SUBMIT = "SUBMIT"
    COMMENT = "COMMENT"
    RESUBMIT = "RESUBMIT"
    VALIDATE = "VALIDATE"
    REQUEST_INFO = "REQUEST_INFO"
    INVALIDATE = "INVALIDATE"
    TRANSMIT = "TRANSMIT"


class ExchangeVisibility(StrEnum):
    """Portée de visibilité d'une entrée du fil d'échange (B40-J3, décision session).

    Filet : l'isolation tenant est portée par la RLS. La visibilité affine le
    besoin-d'en-connaître INTRA-tenant (masquage au serializer côté service) ;
    elle n'est PAS portée en RLS (cf. cadrage §5).

    - INTERNAL_ONLY   : visible des seuls acteurs internes au GCSMS
    - SHARED_EXTERNAL : visible aussi du valideur externe assigné (et famille si partagé)
    """

    INTERNAL_ONLY = "INTERNAL_ONLY"
    SHARED_EXTERNAL = "SHARED_EXTERNAL"


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "CATEGORY_DOMAIN_MAP",
    "DOMAIN_CATEGORY_MAP",
    "AccessType",
    "AggirResultLetter",
    "AggirSubVariableCode",
    "AggirVariableCode",
    "AssignmentStatus",
    "BillingCycle",
    "CarePlanServiceStatus",
    "CarePlanStatus",
    "ContractType",
    "CoordinationCategory",
    "DeviceType",
    "DocumentFormat",
    "DocumentType",
    "EntityType",
    "EvaluationSchemaType",
    "EvaluationSessionStatus",
    "EvaluationStatus",
    "ExchangeActionType",
    "ExchangeVisibility",
    "FrequencyType",
    "GirLevel",
    "IntegrationType",
    "InterventionStatus",
    "InvalidationReason",
    "NotificationType",
    "OrganizationModel",
    "PatientStatus",
    "PermissionCategory",
    "ProfessionCategory",
    "RevisionReason",
    "RoleName",
    "ServiceCategory",
    "ServiceDomain",
    "ServicePriority",
    "ServiceType",
    "ServiceUnit",
    "SubscriptionPlan",
    "SubscriptionStatus",
    "SyncStatus",
    "TenantStatus",
    "TenantType",
    "TerritoryType",
    "ValidationDecision",
    "ValidationStage",
    "ValidationWorkflowType",
    "VitalSource",
    "VitalStatus",
    "VitalType",
]
