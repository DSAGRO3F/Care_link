/**
 * Types TypeScript pour la gestion des Entités
 * Alignés strictement sur app/api/v1/organization/schemas.py (Pydantic v2)
 *
 * Architecture : 1 tenant = 1 racine (GCSMS/GTSMS) = 1 arbre
 * Les entités enfants (SSIAD, SAAD, SPASAD, EHPAD) sont
 * automatiquement rattachées à la racine du tenant.
 * Les sous-entités (ANTENNE, BUREAU, AGENCE) partagent le
 * SIRET de leur parent (même établissement juridique).
 *
 * IMPORTANT — tenant_id volontairement absent de EntityResponse :
 *   En base, entities.tenant_id existe et porte le RLS, mais le
 *   schéma Pydantic EntityResponse ne l'expose PAS car toute requête
 *   API est déjà tenant-scopée par construction (RLS + filtre
 *   explicite). Le client n'a donc pas besoin de cette information :
 *   tout ce qu'il reçoit appartient déjà à son tenant.
 *   Si un besoin SuperAdmin émerge un jour (vue multi-tenant),
 *   l'ajout se fera D'ABORD côté backend dans un schéma dédié
 *   (PlatformEntityResponse), puis seulement ici. Jamais l'inverse.
 *   Référence backlog : Phase 6+ — exposition tenant_id SuperAdmin.
 *
 * v3 — Session 3bis (08/04/2026) : alignement strict org_schemas.py
 *   • Renommages : finess_geo→finess_et, finess_juridique→finess_ej,
 *     address_line1→address, suppression address_line2
 *   • Suppression du champ fantôme tenant_id (jamais exposé par l'API)
 *   • Ajouts : short_name, integration_type, siren, authorized_capacity,
 *     authorization_date, authorization_reference, website,
 *     latitude, longitude, default_intervention_radius_km, country_id
 *   • Ajout type EntitySummary (pour parent_entity imbriqué)
 *   • Ajout type minimal CountryResponse (pour country imbriqué)
 *   • Ajout enum IntegrationType
 */

// =============================================================================
// ENUMS
// =============================================================================

/** Types d'entités médico-sociales */
export enum EntityType {
  // Racines (créées uniquement par SuperAdmin)
  GCSMS = 'GCSMS', // Groupement de Coopération Sociale et Médico-Sociale
  GTSMS = 'GTSMS', // Groupement Territorial Social et Médico-Social (loi Bien Vieillir 2024)

  // Enfants directs — niveau 1 (créés par Admin tenant ou SuperAdmin)
  SSIAD = 'SSIAD', // Service de Soins Infirmiers À Domicile
  SAAD = 'SAAD', // Service d'Aide et d'Accompagnement à Domicile
  SPASAD = 'SPASAD', // Service Polyvalent d'Aide et de Soins À Domicile
  EHPAD = 'EHPAD', // Établissement d'Hébergement pour Personnes Âgées Dépendantes

  // Sous-entités — niveau 2+ (même SIRET que le parent)
  ANTENNE = 'ANTENNE', // Antenne locale
  BUREAU = 'BUREAU', // Bureau territorial
  AGENCE = 'AGENCE', // Agence de proximité
}

/**
 * Type de rattachement d'une entité au tenant.
 * Aligné sur app.models.enums.IntegrationType.
 */
export enum IntegrationType {
  MANAGED = 'MANAGED', // Entité gérée directement par le tenant
  FEDERATED = 'FEDERATED', // Entité fédérée (autonomie partielle)
  CONVENTION = 'CONVENTION', // Convention de coopération
}

/** Types autorisés pour les entités racines */
export const ROOT_ENTITY_TYPES: EntityType[] = [EntityType.GCSMS, EntityType.GTSMS];

/** Types autorisés pour les entités enfants (niveau 1) */
export const CHILD_ENTITY_TYPES: EntityType[] = [
  EntityType.SSIAD,
  EntityType.SAAD,
  EntityType.SPASAD,
  EntityType.EHPAD,
];

/** Types autorisés pour les sous-entités (niveau 2+, SIRET partagé) */
export const SUB_ENTITY_TYPES: EntityType[] = [
  EntityType.ANTENNE,
  EntityType.BUREAU,
  EntityType.AGENCE,
];

// =============================================================================
// INTERFACES — RÉFÉRENCES IMBRIQUÉES
// =============================================================================

/**
 * Réponse minimale pour un pays (référence imbriquée dans EntityResponse.country).
 * Aligné sur CountryResponse Pydantic.
 */
export interface CountryResponse {
  id: number;
  name: string;
  country_code: string; // ISO 3166-1 alpha-2 (FR, BE, CH...)
  is_active: boolean;
  created_at: string;
  updated_at?: string | null;
}

/**
 * Version allégée d'une entité, utilisée pour les relations
 * (parent_entity) et les listes courtes.
 * Aligné sur EntitySummary Pydantic.
 */
export interface EntitySummary {
  id: number;
  name: string;
  short_name?: string | null;
  entity_type: EntityType;
  city?: string | null;
}

// =============================================================================
// INTERFACES — ENTITY
// =============================================================================

/**
 * Réponse complète d'une entité (GET).
 * Aligné strictement sur EntityResponse Pydantic.
 *
 * Note Decimal : latitude/longitude sont des Decimal côté Pydantic.
 * En JSON, Pydantic v2 les sérialise par défaut en string. Le frontend
 * doit donc les coercer si calcul numérique nécessaire (parseFloat).
 * Type retenu : number pour faciliter l'usage UI ; à valider runtime
 * lors de la première consommation effective (Phase 4+).
 */
export interface EntityResponse {
  id: number;

  // Identification
  name: string;
  short_name?: string | null;
  entity_type: EntityType;
  integration_type?: IntegrationType | null;
  parent_id?: number | null; // alias backend de parent_entity_id

  // Identifiants légaux
  siret?: string | null;
  siren?: string | null;
  finess_ej?: string | null; // FINESS Entité Juridique (ex-finess_juridique)
  finess_et?: string | null; // FINESS Établissement / géographique (ex-finess_geo)

  // Autorisation et capacité
  authorized_capacity?: number | null;
  authorization_date?: string | null; // ISO date
  authorization_reference?: string | null;

  // Coordonnées
  address?: string | null; // chaîne libre unique (ex-address_line1, address_line2 absorbé)
  postal_code?: string | null;
  city?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;

  // Géolocalisation
  latitude?: number | null;
  longitude?: number | null;
  default_intervention_radius_km?: number | null;

  // Références
  country_id: number;
  country?: CountryResponse | null;
  parent_entity?: EntitySummary | null;

  // Métadonnées
  is_active: boolean;
  created_at: string;
  updated_at?: string | null;

  // Statistiques (propriétés calculées côté backend)
  patients_count?: number | null;
  users_count?: number | null; // alias backend de active_users_count
}

/**
 * Entité avec ses sous-entités, pour affichage hiérarchique.
 * Aligné sur EntityWithChildren Pydantic.
 *
 * Note : le champ s'appelle child_entities (pas children) pour
 * matcher exactement le schéma Pydantic.
 */
export interface EntityWithChildren extends EntityResponse {
  child_entities: EntitySummary[];
}

/**
 * Données pour créer une entité (POST).
 * Aligné strictement sur EntityCreate Pydantic.
 *
 * country_id est REQUIS (contrainte backend).
 * Validation backend : SIRET 14 chiffres, SIREN 9 chiffres,
 * FINESS 9 caractères alphanumériques.
 */
export interface EntityCreate {
  // Identification
  name: string;
  short_name?: string;
  entity_type: EntityType;

  // Rattachement
  integration_type?: IntegrationType;
  parent_id?: number | null; // alias backend

  // Identifiants légaux
  siret?: string;
  siren?: string;
  finess_ej?: string;
  finess_et?: string;

  // Autorisation
  authorized_capacity?: number;
  authorization_date?: string;
  authorization_reference?: string;

  // Coordonnées
  address?: string;
  postal_code?: string;
  city?: string;
  phone?: string;
  email?: string;
  website?: string;

  // Géolocalisation
  latitude?: number;
  longitude?: number;
  default_intervention_radius_km?: number;

  // Pays (REQUIS côté backend)
  country_id: number;
}

/**
 * Données pour modifier une entité (PATCH).
 * Aligné sur EntityUpdate Pydantic — TOUS les champs optionnels.
 *
 * NOTE PRODUIT — entity_type volontairement OMIS :
 *   Le backend accepte techniquement la modification d'entity_type,
 *   mais nous ne l'exposons PAS dans l'UI standard. Raison :
 *   transformer un EHPAD en SSIAD (par exemple) implique une refonte
 *   complète des autorisations administratives (ARS, conseil
 *   départemental, FINESS, capacité, tarification…) et n'arrive
 *   quasiment jamais dans la vraie vie. Permettre ce changement via
 *   un Dropdown standard ferait courir un risque produit majeur
 *   (clic accidentel = corruption métier).
 *   Si un cas réel émerge, ajouter le champ avec une UX dédiée
 *   (modale de confirmation, double validation, traçabilité audit).
 *   Référence backlog : Phase 6+.
 */
export interface EntityUpdate {
  // Identification
  name?: string;
  short_name?: string | null;
  // entity_type : volontairement omis (voir note ci-dessus)

  // Rattachement
  integration_type?: IntegrationType | null;
  parent_id?: number | null;

  // Identifiants légaux
  siret?: string | null;
  siren?: string | null;
  finess_ej?: string | null;
  finess_et?: string | null;

  // Autorisation
  authorized_capacity?: number | null;
  authorization_date?: string | null;
  authorization_reference?: string | null;

  // Coordonnées
  address?: string | null;
  postal_code?: string | null;
  city?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;

  // Géolocalisation
  latitude?: number | null;
  longitude?: number | null;
  default_intervention_radius_km?: number | null;

  // Pays
  country_id?: number;

  // Métadonnées
  is_active?: boolean;
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
};

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
};

/** Couleurs associées aux types (classes Tailwind) */
export const EntityTypeColors: Record<EntityType, { bg: string; text: string; border: string }> = {
  [EntityType.GCSMS]: { bg: 'bg-indigo-100', text: 'text-indigo-700', border: 'border-indigo-300' },
  [EntityType.GTSMS]: { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-300' },
  [EntityType.SSIAD]: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-300' },
  [EntityType.SAAD]: {
    bg: 'bg-emerald-100',
    text: 'text-emerald-700',
    border: 'border-emerald-300',
  },
  [EntityType.SPASAD]: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-300' },
  [EntityType.EHPAD]: { bg: 'bg-rose-100', text: 'text-rose-700', border: 'border-rose-300' },
  [EntityType.ANTENNE]: { bg: 'bg-teal-100', text: 'text-teal-700', border: 'border-teal-300' },
  [EntityType.BUREAU]: { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-300' },
  [EntityType.AGENCE]: { bg: 'bg-cyan-100', text: 'text-cyan-700', border: 'border-cyan-300' },
};

/** Couleurs Platform dark theme (SuperAdmin — fond zinc-900) */
export const EntityTypePlatformColors: Record<
  EntityType,
  { bg: string; text: string; border: string }
> = {
  [EntityType.GCSMS]: {
    bg: 'bg-indigo-500/20',
    text: 'text-indigo-300',
    border: 'border-indigo-500/40',
  },
  [EntityType.GTSMS]: {
    bg: 'bg-purple-500/20',
    text: 'text-purple-300',
    border: 'border-purple-500/40',
  },
  [EntityType.SSIAD]: { bg: 'bg-blue-500/20', text: 'text-blue-300', border: 'border-blue-500/40' },
  [EntityType.SAAD]: {
    bg: 'bg-emerald-500/20',
    text: 'text-emerald-300',
    border: 'border-emerald-500/40',
  },
  [EntityType.SPASAD]: {
    bg: 'bg-amber-500/20',
    text: 'text-amber-300',
    border: 'border-amber-500/40',
  },
  [EntityType.EHPAD]: { bg: 'bg-rose-500/20', text: 'text-rose-300', border: 'border-rose-500/40' },
  [EntityType.ANTENNE]: {
    bg: 'bg-teal-500/20',
    text: 'text-teal-300',
    border: 'border-teal-500/40',
  },
  [EntityType.BUREAU]: {
    bg: 'bg-slate-500/20',
    text: 'text-slate-300',
    border: 'border-slate-500/40',
  },
  [EntityType.AGENCE]: {
    bg: 'bg-cyan-500/20',
    text: 'text-cyan-300',
    border: 'border-cyan-500/40',
  },
};

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
};

// =============================================================================
// API ENTREPRISES (recherche-entreprises.api.gouv.fr)
// =============================================================================

/** Siège social d'un résultat de recherche API Entreprises */
export interface EntrepriseSiege {
  siret?: string;
  code_postal?: string;
  libelle_commune?: string;
  numero_voie?: string;
  type_voie?: string;
  libelle_voie?: string;
  adresse?: string;
  liste_finess?: string[];
  liste_enseignes?: string[];
  /**
   * État administratif au répertoire SIRENE.
   *   • 'A' : actif
   *   • 'F' : fermé (déclaration de fermeture prise en compte par l'INSEE)
   * Utilisé pour détecter les établissements obsolètes et alerter l'utilisateur
   * (voir incident UX 15/04/2026 sur FONDATION SANTE SERVICE — SIRET fermé
   * hydraté sans warning).
   */
  etat_administratif?: 'A' | 'F';
  /** Date de fermeture de l'établissement (ISO date, uniquement si etat_administratif='F'). */
  date_fermeture?: string | null;
}

/**
 * Établissement matchant la requête (présent dans matching_etablissements[]).
 *
 * Utile quand l'utilisateur cherche par SIRET d'un établissement secondaire :
 * l'API renvoie le siège dans `siege` (ex. mairie d'un CCAS), MAIS aussi
 * l'établissement précis dans `matching_etablissements[0]` (ex. SSIAD avec
 * sa propre adresse, son SIRET et son FINESS).
 *
 * Différences notables avec EntrepriseSiege :
 *   • pas de champs structurés (numero_voie/type_voie/libelle_voie) : seule
 *     la chaîne agrégée `adresse` est disponible. Le composable retombe sur
 *     son fallback regex pour extraire la voie.
 */
export interface EntrepriseEtablissement {
  siret?: string;
  code_postal?: string;
  libelle_commune?: string;
  adresse?: string;
  liste_finess?: string[];
  liste_enseignes?: string[];
  /** Voir EntrepriseSiege.etat_administratif — même sémantique. */
  etat_administratif?: 'A' | 'F';
  /** Voir EntrepriseSiege.date_fermeture — même sémantique. */
  date_fermeture?: string | null;
}

/** Résultat de recherche API Entreprises */
export interface EntrepriseSearchResult {
  nom_complet?: string;
  nom_raison_sociale?: string;
  nature_juridique?: string;
  siege?: EntrepriseSiege;
  matching_etablissements?: EntrepriseEtablissement[];
}
