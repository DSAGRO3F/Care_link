/**
 * Types TypeScript pour la gestion des Entités
 * Alignés avec les schemas Pydantic du backend
 *
 * Architecture : 1 tenant = 1 racine (GCSMS/GTSMS) = 1 arbre
 * Les entités enfants (SSIAD, SAAD, SPASAD, EHPAD) sont
 * automatiquement rattachées à la racine du tenant.
 * Les sous-entités (ANTENNE, BUREAU, AGENCE) partagent le
 * SIRET de leur parent (même établissement juridique).
 *
 * v2 — Ajout types niveau 3 (ANTENNE, BUREAU, AGENCE)
 *      + SUB_ENTITY_TYPES
 *      + patients_count / users_count dans EntityResponse
 */

// =============================================================================
// ENUMS
// =============================================================================

/** Types d'entités médico-sociales */
export enum EntityType {
  // Racines (créées uniquement par SuperAdmin)
  GCSMS = 'GCSMS',   // Groupement de Coopération Sociale et Médico-Sociale
  GTSMS = 'GTSMS',   // Groupement Territorial Social et Médico-Social (loi Bien Vieillir 2024)

  // Enfants directs — niveau 1 (créés par Admin tenant ou SuperAdmin)
  SSIAD = 'SSIAD',    // Service de Soins Infirmiers À Domicile
  SAAD = 'SAAD',      // Service d'Aide et d'Accompagnement à Domicile
  SPASAD = 'SPASAD',  // Service Polyvalent d'Aide et de Soins À Domicile
  EHPAD = 'EHPAD',    // Établissement d'Hébergement pour Personnes Âgées Dépendantes

  // Sous-entités — niveau 2+ (même SIRET que le parent)
  ANTENNE = 'ANTENNE', // Antenne locale
  BUREAU = 'BUREAU',   // Bureau territorial
  AGENCE = 'AGENCE',   // Agence de proximité
}

/** Types autorisés pour les entités racines */
export const ROOT_ENTITY_TYPES: EntityType[] = [
  EntityType.GCSMS,
  EntityType.GTSMS,
]

/** Types autorisés pour les entités enfants (niveau 1) */
export const CHILD_ENTITY_TYPES: EntityType[] = [
  EntityType.SSIAD,
  EntityType.SAAD,
  EntityType.SPASAD,
  EntityType.EHPAD,
]

/** Types autorisés pour les sous-entités (niveau 2+, SIRET partagé) */
export const SUB_ENTITY_TYPES: EntityType[] = [
  EntityType.ANTENNE,
  EntityType.BUREAU,
  EntityType.AGENCE,
]

// =============================================================================
// INTERFACES
// =============================================================================

/** Réponse d'une entité (GET) */
export interface EntityResponse {
  id: number
  tenant_id: number
  name: string
  entity_type: EntityType
  parent_id: number | null
  finess_geo?: string | null
  finess_juridique?: string | null
  siret?: string | null
  address_line1?: string | null
  address_line2?: string | null
  postal_code?: string | null
  city?: string | null
  phone?: string | null
  email?: string | null
  is_active: boolean
  created_at: string
  updated_at?: string | null
  // Statistiques (propriétés calculées côté backend)
  patients_count?: number
  users_count?: number
  // Enfants (si chargés)
  children?: EntityResponse[]
}

/** Données pour créer une entité */
export interface EntityCreate {
  name: string
  entity_type: EntityType
  parent_id?: number | null
  country_id?: number
  finess_geo?: string
  finess_juridique?: string
  siret?: string
  address_line1?: string
  address_line2?: string
  postal_code?: string
  city?: string
  phone?: string
  email?: string
}

/** Données pour modifier une entité */
export interface EntityUpdate {
  name?: string
  parent_id?: number | null
  finess_geo?: string | null
  finess_juridique?: string | null
  siret?: string | null
  address_line1?: string | null
  address_line2?: string | null
  postal_code?: string | null
  city?: string | null
  phone?: string | null
  email?: string | null
  is_active?: boolean
}

// =============================================================================
// LABELS
// =============================================================================

/** Labels français pour les types d'entités */
export const EntityTypeLabels: Record<EntityType, string> = {
  [EntityType.GCSMS]: 'GCSMS — Groupement de Coopération',
  [EntityType.GTSMS]: 'GTSMS — Groupement Territorial',
  [EntityType.SSIAD]: 'SSIAD — Soins Infirmiers à Domicile',
  [EntityType.SAAD]: 'SAAD — Aide à Domicile',
  [EntityType.SPASAD]: 'SPASAD — Service Polyvalent',
  [EntityType.EHPAD]: 'EHPAD — Hébergement Personnes Âgées',
  [EntityType.ANTENNE]: 'Antenne locale',
  [EntityType.BUREAU]: 'Bureau territorial',
  [EntityType.AGENCE]: 'Agence de proximité',
}

/** Labels courts */
export const EntityTypeShortLabels: Record<EntityType, string> = {
  [EntityType.GCSMS]: 'GCSMS',
  [EntityType.GTSMS]: 'GTSMS',
  [EntityType.SSIAD]: 'SSIAD',
  [EntityType.SAAD]: 'SAAD',
  [EntityType.SPASAD]: 'SPASAD',
  [EntityType.EHPAD]: 'EHPAD',
  [EntityType.ANTENNE]: 'Antenne',
  [EntityType.BUREAU]: 'Bureau',
  [EntityType.AGENCE]: 'Agence',
}

/** Couleurs associées aux types (classes Tailwind) */
export const EntityTypeColors: Record<EntityType, { bg: string; text: string; border: string }> = {
  [EntityType.GCSMS]: { bg: 'bg-indigo-100', text: 'text-indigo-700', border: 'border-indigo-300' },
  [EntityType.GTSMS]: { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-300' },
  [EntityType.SSIAD]: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-300' },
  [EntityType.SAAD]: { bg: 'bg-emerald-100', text: 'text-emerald-700', border: 'border-emerald-300' },
  [EntityType.SPASAD]: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-300' },
  [EntityType.EHPAD]: { bg: 'bg-rose-100', text: 'text-rose-700', border: 'border-rose-300' },
  [EntityType.ANTENNE]: { bg: 'bg-teal-100', text: 'text-teal-700', border: 'border-teal-300' },
  [EntityType.BUREAU]: { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-300' },
  [EntityType.AGENCE]: { bg: 'bg-cyan-100', text: 'text-cyan-700', border: 'border-cyan-300' },
}

/** Couleurs dark theme (SuperAdmin) */
export const EntityTypeDarkColors: Record<EntityType, { bg: string; text: string; border: string }> = {
  [EntityType.GCSMS]: { bg: 'bg-indigo-500/20', text: 'text-indigo-300', border: 'border-indigo-500/40' },
  [EntityType.GTSMS]: { bg: 'bg-purple-500/20', text: 'text-purple-300', border: 'border-purple-500/40' },
  [EntityType.SSIAD]: { bg: 'bg-blue-500/20', text: 'text-blue-300', border: 'border-blue-500/40' },
  [EntityType.SAAD]: { bg: 'bg-emerald-500/20', text: 'text-emerald-300', border: 'border-emerald-500/40' },
  [EntityType.SPASAD]: { bg: 'bg-amber-500/20', text: 'text-amber-300', border: 'border-amber-500/40' },
  [EntityType.EHPAD]: { bg: 'bg-rose-500/20', text: 'text-rose-300', border: 'border-rose-500/40' },
  [EntityType.ANTENNE]: { bg: 'bg-teal-500/20', text: 'text-teal-300', border: 'border-teal-500/40' },
  [EntityType.BUREAU]: { bg: 'bg-slate-500/20', text: 'text-slate-300', border: 'border-slate-500/40' },
  [EntityType.AGENCE]: { bg: 'bg-cyan-500/20', text: 'text-cyan-300', border: 'border-cyan-500/40' },
}

/** Icônes PrimeIcons par type */
export const EntityTypeIcons: Record<EntityType, string> = {
  [EntityType.GCSMS]: 'pi pi-sitemap',
  [EntityType.GTSMS]: 'pi pi-sitemap',
  [EntityType.SSIAD]: 'pi pi-heart',
  [EntityType.SAAD]: 'pi pi-home',
  [EntityType.SPASAD]: 'pi pi-shield',
  [EntityType.EHPAD]: 'pi pi-building',
  [EntityType.ANTENNE]: 'pi pi-map-marker',
  [EntityType.BUREAU]: 'pi pi-inbox',
  [EntityType.AGENCE]: 'pi pi-compass',
}