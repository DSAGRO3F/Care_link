/**
 * Types TypeScript pour le module Catalogue.
 *
 * Alignés sur les schémas Pydantic backend (catalog/schemas.py v4.19).
 * Convention EvalSchema* non applicable ici — préfixe ServiceTemplate / EntityService.
 *
 * 🆕 v5.28 — Phase 3A : EntityServiceCreate, EntityServiceUpdate, types vue admin tenant.
 * 🔄 v5.29 — Phase 3B : types vue coordination consolidée alignés sur schemas Pydantic v4.19
 *            (6 interfaces : ConsolidatedEntityOffer, BestTarifInfo, ConsolidatedPrestation,
 *            ConsolidatedEntitySummary, ConsolidatedCatalogSummary, ConsolidatedCatalogResponse).
 *            Remplace les types v5.28 pré-endpoint (EntityOffer, EntityCatalogSummary).
 */

// =============================================================================
// ENUMS & CONSTANTES
// =============================================================================

/** Domaines SERAFIN-PH (niveau 1) */
export type ServiceDomain = 'SOINS_SANTE' | 'AUTONOMIE' | 'PARTICIPATION_SOCIALE';

/** Catégories SERAFIN-PH (niveau 2) */
export type ServiceCategory =
  | 'SOINS_INFIRMIERS'
  | 'SOINS_MEDICAUX'
  | 'REEDUCATION'
  | 'HYGIENE_ENTRETIEN_PERSONNEL'
  | 'ALIMENTATION'
  | 'MOBILITE_TRANSFERTS'
  | 'ENTRETIEN_CADRE_VIE'
  | 'ACCOMPAGNEMENT_ADMINISTRATIF'
  | 'VIE_SOCIALE_LOISIRS'
  | 'TRANSPORT';

/** Mode d'affichage du catalogue */
export type CatalogViewMode = 'platform' | 'admin';

/** Labels lisibles pour les domaines */
export const DOMAIN_LABELS: Record<ServiceDomain, string> = {
  SOINS_SANTE: 'Soins & Santé',
  AUTONOMIE: 'Autonomie',
  PARTICIPATION_SOCIALE: 'Participation sociale',
};

/** Labels lisibles pour les catégories */
export const CATEGORY_LABELS: Record<ServiceCategory, string> = {
  SOINS_INFIRMIERS: 'Soins infirmiers',
  SOINS_MEDICAUX: 'Soins médicaux',
  REEDUCATION: 'Rééducation',
  HYGIENE_ENTRETIEN_PERSONNEL: 'Hygiène & entretien personnel',
  ALIMENTATION: 'Alimentation',
  MOBILITE_TRANSFERTS: 'Mobilité & transferts',
  ENTRETIEN_CADRE_VIE: 'Entretien du cadre de vie',
  ACCOMPAGNEMENT_ADMINISTRATIF: 'Accompagnement administratif',
  VIE_SOCIALE_LOISIRS: 'Vie sociale & loisirs',
  TRANSPORT: 'Transport',
};

/** Mapping domaine → catégories autorisées */
export const DOMAIN_CATEGORY_MAP: Record<ServiceDomain, ServiceCategory[]> = {
  SOINS_SANTE: ['SOINS_INFIRMIERS', 'SOINS_MEDICAUX', 'REEDUCATION'],
  AUTONOMIE: ['HYGIENE_ENTRETIEN_PERSONNEL', 'ALIMENTATION', 'MOBILITE_TRANSFERTS'],
  PARTICIPATION_SOCIALE: [
    'ENTRETIEN_CADRE_VIE',
    'ACCOMPAGNEMENT_ADMINISTRATIF',
    'VIE_SOCIALE_LOISIRS',
    'TRANSPORT',
  ],
};

/** Ordre d'affichage des domaines */
export const DOMAIN_ORDER: ServiceDomain[] = ['SOINS_SANTE', 'AUTONOMIE', 'PARTICIPATION_SOCIALE'];

/** Emojis par catégorie (repris du prototype v3) */
export const CATEGORY_ICONS: Record<ServiceCategory, string> = {
  SOINS_INFIRMIERS: '💉',
  SOINS_MEDICAUX: '🩺',
  REEDUCATION: '🦿',
  HYGIENE_ENTRETIEN_PERSONNEL: '🚿',
  ALIMENTATION: '🍽️',
  MOBILITE_TRANSFERTS: '🚶',
  ENTRETIEN_CADRE_VIE: '🏠',
  ACCOMPAGNEMENT_ADMINISTRATIF: '📋',
  VIE_SOCIALE_LOISIRS: '🎭',
  TRANSPORT: '🚗',
};

/** Couleurs CSS par domaine (classes Tailwind) */
export const DOMAIN_COLORS: Record<
  ServiceDomain,
  { bg: string; text: string; icon: string; border: string }
> = {
  SOINS_SANTE: {
    bg: 'bg-blue-50',
    text: 'text-blue-600',
    icon: 'bg-blue-50 text-blue-600',
    border: 'border-blue-200',
  },
  AUTONOMIE: {
    bg: 'bg-amber-50',
    text: 'text-amber-600',
    icon: 'bg-amber-50 text-amber-600',
    border: 'border-amber-200',
  },
  PARTICIPATION_SOCIALE: {
    bg: 'bg-violet-50',
    text: 'text-violet-600',
    icon: 'bg-violet-50 text-violet-600',
    border: 'border-violet-200',
  },
};

// =============================================================================
// SERVICE TEMPLATE (Catalogue national)
// =============================================================================

/** Résumé service template — utilisé dans les listes */
export interface ServiceTemplateSummary {
  id: number;
  code: string;
  name: string;
  domain: ServiceDomain;
  category: ServiceCategory;
  domain_label: string;
  category_label: string;
  default_duration_minutes: number;
  is_medical_act: boolean;
  apa_eligible: boolean;
  requires_prescription: boolean;
  is_active: boolean;
}

/** Réponse complète service template */
export interface ServiceTemplateResponse extends ServiceTemplateSummary {
  description: string | null;
  required_profession_id: number | null;
  required_qualification: string | null;
  requires_professional: boolean;
  display_order: number;
  status: string;
  created_at: string;
  updated_at: string | null;
}

/** Payload création service template */
export interface ServiceTemplateCreate {
  code: string;
  name: string;
  domain: ServiceDomain;
  category: ServiceCategory;
  description?: string | null;
  required_profession_id?: number | null;
  required_qualification?: string | null;
  default_duration_minutes?: number;
  requires_prescription?: boolean;
  is_medical_act?: boolean;
  apa_eligible?: boolean;
  display_order?: number;
}

/** Payload mise à jour service template */
export interface ServiceTemplateUpdate {
  name?: string;
  domain?: ServiceDomain;
  category?: ServiceCategory;
  description?: string | null;
  required_profession_id?: number | null;
  required_qualification?: string | null;
  default_duration_minutes?: number;
  requires_prescription?: boolean;
  is_medical_act?: boolean;
  apa_eligible?: boolean;
  display_order?: number;
  status?: 'active' | 'inactive';
}

/** Liste paginée de service templates */
export interface ServiceTemplateList {
  items: ServiceTemplateSummary[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

/** Filtres de recherche */
export interface ServiceTemplateFilters {
  domain?: ServiceDomain | null;
  category?: ServiceCategory | null;
  is_medical_act?: boolean | null;
  requires_prescription?: boolean | null;
  apa_eligible?: boolean | null;
  status?: 'active' | 'inactive' | null;
  search?: string | null;
}

// =============================================================================
// DOMAINES & CATÉGORIES (endpoints /domains, /categories)
// =============================================================================

/** Domaine avec compteurs — retourné par GET /service-templates/domains */
export interface DomainWithCounts {
  code: ServiceDomain;
  name: string;
  categories: ServiceCategory[];
  active_count: number;
  total_count: number;
}

/** Catégorie avec compteurs — retourné par GET /service-templates/categories */
export interface CategoryWithCounts {
  code: ServiceCategory;
  name: string;
  domain: ServiceDomain;
  domain_name: string;
  active_count: number;
  total_count: number;
}

// =============================================================================
// ENTITY SERVICE (Services par entité — Phase 3A)
// =============================================================================

/** Réponse service d'entité — retourné par GET /entities/{id}/services */
export interface EntityServiceResponse {
  id: number;
  entity_id: number;
  service_template_id: number;
  is_active: boolean;
  price_euros: number | null;
  max_capacity_week: number | null;
  custom_duration_minutes: number | null;
  effective_duration_minutes: number;
  has_custom_duration: boolean;
  has_custom_price: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
  /** Champs enrichis par _build_entity_service_response() */
  service_code: string | null;
  service_name: string | null;
  service_domain: ServiceDomain | null;
  service_category: ServiceCategory | null;
}

/**
 * 🆕 v5.28 — Payload activation d'un service pour une entité.
 * POST /entities/{id}/services
 */
export interface EntityServiceCreate {
  service_template_id: number;
  is_active?: boolean;
  price_euros?: number | null;
  custom_duration_minutes?: number | null;
  max_capacity_week?: number | null;
  notes?: string | null;
}

/**
 * 🆕 v5.28 — Payload personnalisation d'un service entité.
 * PATCH /entities/{id}/services/{sid}
 */
export interface EntityServiceUpdate {
  is_active?: boolean;
  price_euros?: number | null;
  custom_duration_minutes?: number | null;
  max_capacity_week?: number | null;
  notes?: string | null;
}

// =============================================================================
// VUE STRUCTURÉE — ACCORDÉON (Phase 2, réutilisé Phase 3)
// =============================================================================

/** Catégorie groupée avec ses services — utilisé par CatalogCategoryCard */
export interface CategoryGroup {
  category: ServiceCategory;
  label: string;
  icon: string;
  services: ServiceTemplateSummary[];
  activeCount: number;
  totalCount: number;
}

/** Domaine groupé avec ses catégories — utilisé par CatalogDomainSection */
export interface DomainGroup {
  domain: ServiceDomain;
  label: string;
  colors: { bg: string; text: string; icon: string; border: string };
  categories: CategoryGroup[];
  activeCount: number;
  totalCount: number;
}

// =============================================================================
// 🆕 VUE ADMIN TENANT — MERGE NATIONAL ↔ ENTITÉ (Phase 3A)
// =============================================================================

/**
 * Service fusionné : template national + surcharge entité (si activé).
 * C'est le type pivot de la Phase 3A — chaque ligne de l'UI admin-tenant
 * combine les données du référentiel avec la personnalisation de l'entité.
 */
export interface MergedEntityService {
  /** Données du référentiel national (toujours présentes) */
  template: ServiceTemplateSummary;
  /** Données de l'entité (null si le service n'est pas activé par l'entité) */
  entityService: EntityServiceResponse | null;
  /** Raccourcis pratiques */
  isActivated: boolean;
  effectiveDuration: number;
  effectivePrice: number | null;
  effectiveFrequency: number | null;
  hasCustomization: boolean;
}

/**
 * 🆕 v5.28 — Catégorie groupée pour la vue admin-tenant.
 * Étend CategoryGroup avec les MergedEntityService à la place des templates bruts.
 */
export interface EntityCategoryGroup {
  category: ServiceCategory;
  label: string;
  icon: string;
  services: MergedEntityService[];
  activatedCount: number;
  totalCount: number;
}

/**
 * 🆕 v5.28 — Domaine groupé pour la vue admin-tenant.
 */
export interface EntityDomainGroup {
  domain: ServiceDomain;
  label: string;
  colors: { bg: string; text: string; icon: string; border: string };
  categories: EntityCategoryGroup[];
  activatedCount: number;
  totalCount: number;
}

// =============================================================================
// 🔄 VUE COORDINATION CONSOLIDÉE (Phase 3B — aligné schemas Pydantic v4.19)
// =============================================================================

/**
 * Offre d'une entité pour une prestation donnée.
 * Miroir de `EntityOfferResponse` (backend catalog/schemas.py v4.19).
 * Mapping champs : price_euros (DB) → custom_tarif (API),
 *                  custom_duration_minutes (DB) → custom_duree (API).
 */
export interface ConsolidatedEntityOffer {
  entity_id: number;
  entity_name: string;
  entity_type: string;
  custom_tarif: number | null;
  custom_duree: number | null;
  is_active: boolean;
}

/**
 * Meilleur tarif parmi les offres d'une prestation consolidée.
 * Miroir de `BestTarifInfo` (backend catalog/schemas.py v4.19).
 */
export interface BestTarifInfo {
  value: number;
  entity_name: string;
}

/**
 * Prestation consolidée avec toutes les offres entités.
 * Miroir de `ConsolidatedPrestationResponse` (backend catalog/schemas.py v4.19).
 * Les champs template sont aplatis dans la réponse.
 */
export interface ConsolidatedPrestation {
  /** Identification template */
  template_id: number;
  code: string;
  name: string;
  /** Classification SERAFIN-PH */
  domain: ServiceDomain;
  domain_label: string;
  category: ServiceCategory;
  category_label: string;
  description: string | null;
  /** Profession requise (nom résolu via selectinload côté backend) */
  required_profession_name: string | null;
  /** Propriétés template */
  default_duration_minutes: number | null;
  requires_prescription: boolean;
  is_medical_act: boolean;
  apa_eligible: boolean;
  /** Données consolidées cross-entités */
  offers: ConsolidatedEntityOffer[];
  offer_count: number;
  best_tarif: BestTarifInfo | null;
}

/**
 * Résumé d'une entité participante au catalogue consolidé.
 * Miroir de `ConsolidatedEntitySummary` (backend catalog/schemas.py v4.19).
 */
export interface ConsolidatedEntitySummary {
  id: number;
  name: string;
  entity_type: string;
  active_services_count: number;
}

/**
 * Compteurs globaux du catalogue consolidé.
 * Miroir de `ConsolidatedCatalogSummary` (backend catalog/schemas.py v4.19).
 * Note : les entités sont nestées dans le summary (pas au top-level).
 */
export interface ConsolidatedCatalogSummary {
  total_national: number;
  total_active_prestations: number;
  entities_count: number;
  entities: ConsolidatedEntitySummary[];
}

/**
 * Réponse top-level de GET /catalog/consolidated.
 * Miroir de `ConsolidatedCatalogResponse` (backend catalog/schemas.py v4.19).
 */
export interface ConsolidatedCatalogResponse {
  prestations: ConsolidatedPrestation[];
  summary: ConsolidatedCatalogSummary;
}

// =============================================================================
// VUE STRUCTURÉE COORDINATION — ACCORDÉON (Phase 3B, frontend-only)
// =============================================================================

/**
 * Catégorie groupée pour la vue coordination consolidée.
 * Même pattern que CategoryGroup (Phase 2) et EntityCategoryGroup (Phase 3A)
 * mais avec des ConsolidatedPrestation[] et des compteurs offres.
 */
export interface CoordinationCategoryGroup {
  category: ServiceCategory;
  label: string;
  icon: string;
  prestations: ConsolidatedPrestation[];
  prestationCount: number;
  totalOffers: number;
}

/**
 * Domaine groupé pour la vue coordination consolidée.
 */
export interface CoordinationDomainGroup {
  domain: ServiceDomain;
  label: string;
  colors: { bg: string; text: string; icon: string; border: string };
  categories: CoordinationCategoryGroup[];
  prestationCount: number;
  totalOffers: number;
}
