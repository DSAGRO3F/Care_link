/**
 * Types TypeScript pour le module CarePlan (Plan d'aide).
 *
 * Alignés sur les schémas Pydantic backend (careplan/schemas.py).
 * Source de vérité = code schemas.py, pas la spec narrative (convention #78).
 *
 * 🆕 v5.31 — Phase 4 : CarePlan + CarePlanService + workflow + budget.
 * 🆕 v5.44 — B28b : 5 champs de filiation (supersedes_plan_id, revision_reason,
 *           revision_comment, gir_inherited_from_evaluation_id, is_revision)
 *           + enum RevisionReason + CarePlanReviseRequest. Rattrape au passage
 *           le superseded_plan_id B28a (transitoire, convention #108) oublié
 *           côté TS au Jalon 2.
 * 🆕 v5.45 — F5 : constantes UI REVISION_REASON_LABELS + REVISION_REASON_ORDER
 *           (libellés FR pour le Select du dialog de motif de révision).

* 🆕 v5.47 — B28c : ajout du champ has_pending_revision (gating frontend
 *           du bouton Réviser, miroir de la propriété transitoire ORM,
 *           cf. décision 38 note de cadrage B28).
 *
 * 🆕 v5.48 — B51 (option A) : ajout du champ pending_revision_draft_id
*           sur CarePlanResponse (complément UX de has_pending_revision
*           pour le lien navigable « Voir le brouillon » dans le tooltip
*           pédagogique du bouton « Réviser » grisé, F4-bis frontend).

* 🆕 v5.51 — F6.5 : ajout de PLAN_STATUS_LABELS (libellés FR pour bandeau
*           parent en mode révision, à réutiliser F8a/F8b/B40 futures).

* 🆕 v5.52 — F8a/F8b : enrichissement CarePlanSummary (+gir_at_creation,
*           +supersedes_plan_id, +revision_reason) pour cards plans en cours
*           + DataTable historique 9 colonnes sur PatientDetailPage_soins.
*/

import type { TagSeverity } from './ui';

// =============================================================================
// ENUMS
// =============================================================================

/** Statuts d'un plan d'aide (state machine) */
export type CarePlanStatus =
  | 'DRAFT'
  | 'PENDING_VALIDATION'
  | 'ACTIVE'
  | 'SUSPENDED'
  | 'COMPLETED'
  | 'CANCELLED';

/** Types de fréquence d'un service */
export type FrequencyType = 'DAILY' | 'WEEKLY' | 'SPECIFIC_DAYS' | 'MONTHLY' | 'ON_DEMAND';

/** Niveau de priorité d'un service */
export type ServicePriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

/** Statut d'affectation d'un service à un professionnel */
export type AssignmentStatus = 'UNASSIGNED' | 'PENDING' | 'ASSIGNED' | 'CONFIRMED' | 'REJECTED';

/** Statut opérationnel d'un service dans le plan */
export type CarePlanServiceStatus = 'ACTIVE' | 'PAUSED' | 'COMPLETED';

/**
 * Motifs de révision d'un plan d'aide (B28b).
 *
 * 7 valeurs gravées dans la note de cadrage B28 §5.1 (décision 23).
 * Enrichissement post-retours IDEC en backlog B33.
 *
 * Libellés UI FR à mapper côté composants :
 * - HOSPITAL_RETURN     → "Retour d'hospitalisation"
 * - HEALTH_DETERIORATION → "Dégradation de l'état de santé"
 * - HEALTH_STABILIZATION → "Stabilisation / amélioration"
 * - USER_REQUEST        → "Demande du bénéficiaire"
 * - CAREGIVER_REQUEST   → "Demande de l'aidant"
 * - ANNUAL_REVIEW       → "Révision annuelle"
 * - OTHER               → "Autre motif"
 */
export type RevisionReason =
  | 'HOSPITAL_RETURN'
  | 'HEALTH_DETERIORATION'
  | 'HEALTH_STABILIZATION'
  | 'USER_REQUEST'
  | 'CAREGIVER_REQUEST'
  | 'ANNUAL_REVIEW'
  | 'OTHER';

// =============================================================================
// CARE PLAN SERVICE — Schemas miroir schemas.py
// =============================================================================

/**
 * Payload création d'un service de plan.
 * Miroir de `CarePlanServiceCreate` (schemas.py).
 */
export interface CarePlanServiceCreate {
  service_template_id: number;
  entity_service_id?: number | null;
  quantity_per_week: number;
  frequency_type: FrequencyType;
  frequency_days?: number[] | null;
  preferred_time_start?: string | null;
  preferred_time_end?: string | null;
  duration_minutes: number;
  priority?: ServicePriority;
  special_instructions?: string | null;
}

/**
 * Payload mise à jour d'un service de plan.
 * Miroir de `CarePlanServiceUpdate` (schemas.py).
 */
export interface CarePlanServiceUpdate {
  quantity_per_week?: number;
  frequency_type?: FrequencyType;
  frequency_days?: number[] | null;
  preferred_time_start?: string | null;
  preferred_time_end?: string | null;
  duration_minutes?: number;
  priority?: ServicePriority;
  special_instructions?: string | null;
  status?: CarePlanServiceStatus;
}

/**
 * Réponse complète d'un service de plan.
 * Miroir de `CarePlanServiceResponse` (schemas.py).
 */
export interface CarePlanServiceResponse {
  id: number;
  care_plan_id: number;
  service_template_id: number;
  entity_service_id: number | null;
  quantity_per_week: number;
  frequency_type: string;
  frequency_days: number[] | null;
  preferred_time_start: string | null;
  preferred_time_end: string | null;
  duration_minutes: number;
  priority: string;
  assigned_user_id: number | null;
  assignment_status: string;
  assigned_at: string | null;
  assigned_by_id: number | null;
  special_instructions: string | null;
  status: string;
  /** Propriétés calculées (model @property) */
  is_assigned: boolean;
  is_confirmed: boolean;
  time_slot_display: string;
  days_display: string;
  frequency_display: string;
  total_weekly_minutes: number;
  total_weekly_hours: number;
  /** Infos template (enrichissement route) */
  service_name: string | null;
  service_code: string | null;
  /** Infos offre entité — catalogue consolidé (enrichissement route) */
  entity_name: string | null;
  effective_tarif: number | null;
  created_at: string;
  updated_at: string | null;
}

/** Liste des services d'un plan. Miroir de `CarePlanServiceList` (schemas.py). */
export interface CarePlanServiceList {
  items: CarePlanServiceResponse[];
  total: number;
}

/**
 * Payload affectation d'un service à un professionnel.
 * Miroir de `ServiceAssignment` (schemas.py).
 */
export interface ServiceAssignment {
  user_id: number;
  mode: 'assign' | 'propose';
}

// =============================================================================
// CARE PLAN — Schemas miroir schemas.py
// =============================================================================

/**
 * Payload création d'un plan d'aide.
 * Miroir de `CarePlanCreate` (schemas.py).
 */
export interface CarePlanCreate {
  patient_id: number;
  entity_id: number;
  title: string;
  source_evaluation_id?: number | null;
  reference_number?: string | null;
  start_date: string;
  end_date?: string | null;
  total_hours_week?: number | null;
  gir_at_creation?: number | null;
  budget_allocated?: number | null;
  notes?: string | null;
  services?: CarePlanServiceCreate[] | null;
}

/**
 * Payload mise à jour d'un plan d'aide.
 * Miroir de `CarePlanUpdate` (schemas.py).
 */
export interface CarePlanUpdate {
  title?: string;
  reference_number?: string | null;
  start_date?: string;
  end_date?: string | null;
  total_hours_week?: number | null;
  budget_allocated?: number | null;
  notes?: string | null;
}

/**
 * Réponse complète d'un plan d'aide (sans services).
 * Miroir de `CarePlanResponse` (schemas.py).
 */
export interface CarePlanResponse {
  id: number;
  patient_id: number;
  entity_id: number;
  title: string;
  source_evaluation_id: number | null;
  reference_number: string | null;
  start_date: string;
  end_date: string | null;
  total_hours_week: number | null;
  gir_at_creation: number | null;
  budget_allocated: number | null;
  notes: string | null;
  status: CarePlanStatus;
  validated_by_id: number | null;
  validated_at: string | null;
  /** Propriétés calculées (model @property) */
  is_active: boolean;
  is_draft: boolean;
  is_editable: boolean;
  is_validated: boolean;
  services_count: number;
  assigned_services_count: number;
  unassigned_services_count: number;
  assignment_completion_rate: number;
  is_fully_assigned: boolean;

  // ===========================================================================
  // B28b — Champs de filiation (révision de plan)
  // ===========================================================================
  // Persistés en base. Renseignés par le service revise() pour les plans
  // issus d'un POST /revise ; NULL pour les plans créés ex nihilo.

  /**
   * ID du plan parent dont celui-ci est une révision (B28b).
   * NULL pour les plans créés ex nihilo.
   */
  supersedes_plan_id: number | null;
  /**
   * Motif de révision (B28b). NULL pour les plans non issus d'une révision.
   */
  revision_reason: RevisionReason | null;
  /**
   * Commentaire libre du coordinateur sur la révision (B28b).
   * Max 1000 caractères côté Pydantic.
   */
  revision_comment: string | null;
  /**
   * ID de l'évaluation source du GIR hérité en révision sans nouvelle
   * évaluation (B28b, traçabilité AGGIR).
   */
  gir_inherited_from_evaluation_id: number | null;
  /**
   * Computed — propagé via Pydantic from_attributes=True depuis
   * CarePlan.is_revision. True si supersedes_plan_id non-NULL.
   */
  is_revision: boolean;
  // ===========================================================================
  // B28c — Indicateur de révision en cours (convention #108)
  // ===========================================================================
  /**
   * Computed — propagé via Pydantic from_attributes=True depuis
   * CarePlan.has_pending_revision. True si au moins un DRAFT enfant
   * référence ce plan via supersedes_plan_id (cf. décision 38 note
   * de cadrage B28). Utilisé par l'UI pour griser le bouton « Réviser »
   * et éviter les révisions concurrentes.
   */
  has_pending_revision: boolean;
  /**
   * Computed — propagé via Pydantic from_attributes=True depuis
   * CarePlan.pending_revision_draft_id. ID du DRAFT-révision en cours
   * pour ce plan, NULL si aucun. Complément UX de has_pending_revision —
   * permet à l'UI un lien navigable « Voir le brouillon » dans le tooltip
   * pédagogique du bouton « Réviser » grisé.
   *
   * Exposé uniquement sur CarePlanResponse (détail), absent de
   * CarePlanSummary (listes paginées) pour préserver les performances
   * sur les chemins listing.
   */
  pending_revision_draft_id: number | null;

  // ===========================================================================
  // B28a — Attribut transitoire (convention #108)
  // ===========================================================================
  /**
   * ID du plan ACTIVE précédent fermé automatiquement (B28a).
   * Renseigné UNIQUEMENT par l'endpoint /validate quand une transition
   * auto a eu lieu. NULL en régime nominal et pour tous les autres
   * endpoints (get_by_id, list, ...).
   *
   * Cet attribut transitoire pilote le toast B28a silencieux côté UI
   * (décision 36 note de cadrage B28).
   */
  superseded_plan_id: number | null;

  created_at: string;
  updated_at: string | null;
  created_by: number | null;
}

/**
 * Plan d'aide avec ses services.
 * Miroir de `CarePlanWithServices` (schemas.py).
 */
export interface CarePlanWithServices extends CarePlanResponse {
  services: CarePlanServiceResponse[];
  budget_consumed: number | null;
}

/**
 * Résumé d'un plan pour les listes.
 * Miroir de `CarePlanSummary` (schemas.py).
 */
export interface CarePlanSummary {
  id: number;
  patient_id: number;
  /** 🆕 v5.54 — Prénom patient déchiffré (transient #108, backend v4.37) */
  patient_first_name: string | null;
  /** 🆕 v5.54 — Nom de famille patient déchiffré (transient #108, backend v4.37) */
  patient_last_name: string | null;
  entity_id: number;
  title: string;
  status: CarePlanStatus;
  start_date: string;
  end_date: string | null;
  services_count: number;
  is_fully_assigned: boolean;
  budget_allocated: number | null;
  /** 🆕 F8a/F8b — GIR à la création (1-6), NULL si non renseigné */
  gir_at_creation: number | null;
  /** 🆕 F8a/F8b — ID du plan parent (B28b), NULL pour les plans ex nihilo */
  supersedes_plan_id: number | null;
  /** 🆕 F8a/F8b — Motif de révision (B28b), NULL pour les plans non issus d'une révision */
  revision_reason: RevisionReason | null;
  created_at: string;
}

/** Liste paginée de plans. Miroir de `CarePlanList` (schemas.py). */
export interface CarePlanList {
  items: CarePlanSummary[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// =============================================================================
// ACTIONS & FILTRES
// =============================================================================

/**
 * Payload changement de statut (suspend, cancel).
 * Miroir de `CarePlanStatusChange` (schemas.py).
 */
export interface CarePlanStatusChange {
  reason?: string | null;
}

/**
 * Payload du POST /care-plans/{parent_id}/revise (B28b).
 * Miroir de `CarePlanReviseRequest` (schemas.py).
 *
 * Capte le motif de révision et les options de granularité d'héritage.
 * Décisions B28 sources de vérité : note de cadrage §4-5.
 *
 * Vocabulaire UI vs DB : côté frontend les libellés utilisent
 * « révision », « plan révisé », « révisé par » (décision 22).
 * Le payload reste neutre techniquement (revision_reason, revision_comment).
 */
export interface CarePlanReviseRequest {
  /**
   * Motif obligatoire de la révision. 7 valeurs v1 gravées dans la
   * note de cadrage B28 §5.1 (décision 23). 'OTHER' réservé aux cas
   * non anticipés — enrichissement post-retours IDEC en backlog B33.
   */
  revision_reason: RevisionReason;
  /**
   * Commentaire libre du coordinateur, particulièrement utile quand
   * revision_reason = OTHER. Max 1000 caractères côté Pydantic.
   */
  revision_comment?: string | null;
  /**
   * Si true (défaut), copie les services + fréquences du plan parent
   * vers la révision (décision 28). Les affectations professionnels et
   * les ScheduledIntervention ne sont JAMAIS héritées par construction.
   */
  inherit_services?: boolean;
  /**
   * Si true (défaut), pose gir_inherited_from_evaluation_id =
   * parent.source_evaluation_id pour traçabilité AGGIR (décision 24,
   * note de cadrage §3.2). À mettre false si une nouvelle évaluation
   * sera attachée explicitement à la révision.
   */
  inherit_gir?: boolean;
}
/**
 * Payload du POST /care-plans/{plan_id}/replace-services.
 * Miroir de `CarePlanReplaceServicesRequest` (schemas.py).
 *
 * Sémantique « panier complet » : la liste fournie remplace
 * intégralement les services du plan en une transaction DB
 * (delete-all + insert-all côté backend).
 *
 * Statut éligible : DRAFT uniquement (les plans en autre statut
 * lèvent CarePlanNotEditableError → 409 Conflict). Cf. F6.6.
 *
 * Note : une liste vide est autorisée (cas d'un brouillon
 * temporairement vidé pour reprise ultérieure).
 */
export interface CarePlanReplaceServicesRequest {
  services: CarePlanServiceCreate[];
}

/**
 * Filtres pour la recherche de plans.
 * Miroir de `CarePlanFilters` (schemas.py).
 */
export interface CarePlanFilters {
  patient_id?: number | null;
  entity_id?: number | null;
  status?: CarePlanStatus | null;
  start_date_from?: string | null;
  start_date_to?: string | null;
  is_fully_assigned?: boolean | null;
}

// =============================================================================
// DRAFT — Frontend-only (pas de miroir schemas.py)
// =============================================================================

/**
 * Service draft pour le panier de création (frontend-only).
 * Étend CarePlanServiceCreate avec des champs d'affichage issus du catalogue.
 * Les champs _display_* ne sont PAS envoyés à l'API — ils servent
 * uniquement au rendu du SelectedServicesPanel.
 */
export interface CarePlanServiceDraft extends CarePlanServiceCreate {
  /** Nom de la prestation (depuis le template catalogue) */
  _display_service_name: string;
  /** Code SERAFIN-PH */
  _display_service_code: string;
  /** Nom de l'entité fournisseuse (depuis l'offre sélectionnée) */
  _display_entity_name: string | null;
  /** Tarif de l'entité (custom_tarif depuis l'offre) */
  _display_tarif: number | null;
  /** Profession requise */
  _display_profession_name: string | null;
  /** 🆕 F3 — Domaine SERAFIN-PH (pour groupement palette semaine type) */
  _display_domain: string | null;
}

// =============================================================================
// SEMAINE TYPE — Frontend-only (F3)
// =============================================================================

/** Définition d'une période de la journée pour la grille semaine type. */
export interface PeriodDefinition {
  /** Clé unique de la période */
  key: string;
  /** Label affiché */
  label: string;
  /** Plage horaire affichée */
  range: string;
  /** Heure de début (0-23) */
  startH: number;
  /** Heure de fin (peut dépasser 23 pour la nuit : 32 = 08h lendemain) */
  endH: number;
}

/** Les 5 périodes de la journée (08h → 08h lendemain). */
export const PERIODS: PeriodDefinition[] = [
  { key: 'matin', label: 'Matin', range: '08h – 12h', startH: 8, endH: 12 },
  { key: 'midi', label: 'Midi', range: '12h – 14h', startH: 12, endH: 14 },
  { key: 'apresmidi', label: 'Après-midi', range: '14h – 18h', startH: 14, endH: 18 },
  { key: 'soir', label: 'Soir', range: '18h – 22h', startH: 18, endH: 22 },
  { key: 'nuit', label: 'Nuit', range: '22h – 08h', startH: 22, endH: 32 },
];

/** Les 7 jours de la semaine (labels FR). */
export const WEEK_DAYS = [
  'Lundi',
  'Mardi',
  'Mercredi',
  'Jeudi',
  'Vendredi',
  'Samedi',
  'Dimanche',
] as const;

/** Abréviations 1 lettre pour les boutons jour du popover récurrence. */
export const WEEK_DAY_ABBR = ['L', 'M', 'M', 'J', 'V', 'S', 'D'] as const;

/** Abréviations 3 lettres pour les previews. */
export const WEEK_DAY_SHORT = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'] as const;

/**
 * Placement d'une prestation dans la grille hebdomadaire (frontend-only).
 *
 * Un placement lie un service draft (identifié par son index dans draftServices[])
 * à un créneau jour × heure. Plusieurs placements peuvent référencer le même
 * draftIndex (récurrence sur plusieurs jours).
 *
 * Approche A : un placement = une combinaison (prestation × horaire × jour).
 * En Phase 6, migration possible vers Approche B (JSONB weekly_schedule).
 */
export interface WeeklyPlacement {
  /** Identifiant unique du placement (auto-incrémenté frontend) */
  id: number;
  /** Index dans draftServices[] — identifie la prestation source */
  draftIndex: number;
  /** Jour de la semaine (0=Lundi … 6=Dimanche) */
  day: number;
  /** Clé de la période (matin, midi, apresmidi, soir, nuit) */
  period: string;
  /** Heure de début au format 'HH:MM' */
  startTime: string;
  /** Durée en minutes (peut différer de la durée catalogue si éditée) */
  duration: number;
}

// =============================================================================
// REVISION REASONS — UI labels FR (Frontend-only, F5)
// =============================================================================

/**
 * Libellés FR synthétiques pour l'enum RevisionReason.
 * Utilisés dans le Select du dialog de motif de révision (F5).
 *
 * Vocabulaire validé pour IDEC SSIAD français :
 * - « Dégradation de l'autonomie » (vs « état de santé ») — vocabulaire AGGIR/GIR
 * - « À la demande de l'aidant » — terme officiel loi ASV 2015
 */
export const REVISION_REASON_LABELS: Record<RevisionReason, string> = {
  HOSPITAL_RETURN: "Retour d'hospitalisation",
  HEALTH_DETERIORATION: "Dégradation de l'autonomie",
  HEALTH_STABILIZATION: "Amélioration de l'état",
  USER_REQUEST: 'À la demande du bénéficiaire',
  CAREGIVER_REQUEST: "À la demande de l'aidant",
  ANNUAL_REVIEW: 'Révision annuelle',
  OTHER: 'Autre motif',
};

/**
 * Ordre d'affichage des motifs dans le Select.
 * Les motifs cliniques en premier (les plus fréquents en SSIAD),
 * OTHER en dernier (filet de sécurité).
 */
export const REVISION_REASON_ORDER: RevisionReason[] = [
  'HOSPITAL_RETURN',
  'HEALTH_DETERIORATION',
  'HEALTH_STABILIZATION',
  'ANNUAL_REVIEW',
  'USER_REQUEST',
  'CAREGIVER_REQUEST',
  'OTHER',
];

// =============================================================================
// PLAN STATUS — UI labels FR (Frontend-only, F6.5)
// =============================================================================

/**
 * Libellés FR synthétiques pour l'enum CarePlanStatus.
 *
 * Utilisés dans les bandeaux contextuels (F6.5 bandeau parent en mode révision),
 * les listings (F8a refonte onglet plans-aide, F8 « Mes brouillons », F8b
 * historique enrichi), et tout autre affichage de statut côté UI.
 *
 * Genre : masculin (« le plan d'aide »).
 * Source de vérité : pas de mapping backend équivalent — choix UI pur.
 */
export const PLAN_STATUS_LABELS: Record<CarePlanStatus, string> = {
  DRAFT: 'Brouillon',
  PENDING_VALIDATION: 'En attente de validation',
  ACTIVE: 'Actif',
  SUSPENDED: 'Suspendu',
  COMPLETED: 'Terminé',
  CANCELLED: 'Annulé',
};

/**
 * Severity PrimeVue `Tag` pour l'enum `CarePlanStatus`.
 *
 * 🆕 B48 Palier 2 (Lot 0) — consolide `getCarePlanStatusSeverity`, dupliqué et
 * divergent entre PatientDetailPage_admin et _soins. Choix actés :
 * - SUSPENDED → `warn` : état légitime du cycle de vie (pause), pas une
 *   erreur — ne pas le dramatiser en rouge (était `danger` côté soins).
 * - CANCELLED → `danger` : état terminal négatif (était `secondary` côté soins).
 */
export const PLAN_STATUS_SEVERITY: Record<CarePlanStatus, TagSeverity> = {
  DRAFT: 'secondary',
  PENDING_VALIDATION: 'warn',
  ACTIVE: 'success',
  SUSPENDED: 'warn',
  COMPLETED: 'info',
  CANCELLED: 'danger',
};
/**
 * 🆕 v5.54 — Construit un libellé patient lisible "Prénom NOM" depuis
 * un CarePlanSummary, avec fallback "Patient #N" si les noms ne sont
 * pas disponibles (cas non-eager backend, sécurité).
 *
 * Convention : prénom en casse normale, nom en MAJUSCULES (usage français
 * standard du dossier médical pour distinguer prénom et patronyme).
 *
 * Utilisé par CarePlanDraftsPage (F8) ; pourra être réutilisé par
 * CarePlanListPage (admin) et toute future liste care-plan multi-patients.
 */
export function formatPatientName(plan: CarePlanSummary): string {
  if (plan.patient_first_name && plan.patient_last_name) {
    return `${plan.patient_first_name} ${plan.patient_last_name.toUpperCase()}`;
  }
  return `Patient #${plan.patient_id}`;
}