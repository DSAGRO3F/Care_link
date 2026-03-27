/**
 * Types pour le module User
 * Utilisateurs, rôles, professions, disponibilités
 *
 * MàJ Sprint S2 :
 *   - Ajout UserQueryParams (filtres de recherche paginés)
 *   - Ajout UserWithEntities (user + associations entités)
 * MàJ S4 :
 *   - Ajout effective_permissions sur UserResponse
 * MàJ S5 :
 *   - Ajout ProfessionGroup, PROFESSION_CATEGORY_LABELS, PROFESSION_CATEGORY_ORDER
 *   - Ajout OBSOLETE_ROLE_NAMES (rôles-professions supprimés en v4.11)
 * MàJ R1 (RolesPage) :
 *   - Ajout ROLE_DISPLAY_CONFIG, PERMISSION_CATEGORIES, PERMISSION_LABELS
 *   - Ajout PERMISSION_CATEGORY_ORDER, getPermissionCategory()
 */

// =============================================================================
// ENUMS
// =============================================================================

/** Types de contrat */
export type ContractType = 'SALARIE' | 'LIBERAL' | 'VACATION' | 'REMPLACEMENT' | 'BENEVOLE';

// =============================================================================
// PROFESSION
// =============================================================================

/** Profession de santé */
export interface ProfessionResponse {
  id: number;
  name: string;
  code?: string;
  category?: string;
  requires_rpps: boolean;
  display_order: number; // AJOUT S2
  status: string; // AJOUT S2 — "active" | "inactive"
  created_at: string;
}

/** 🆕 S5 — Groupe de professions pour affichage par catégorie */
export interface ProfessionGroup {
  category: string;
  label: string;
  professions: ProfessionResponse[];
}

/** 🆕 S5 — Labels des catégories de profession */
export const PROFESSION_CATEGORY_LABELS: Record<string, string> = {
  MEDICAL: 'Médical',
  PARAMEDICAL: 'Paramédical',
  SOCIAL: 'Social',
  ADMINISTRATIVE: 'Administratif',
};

/** 🆕 S5 — Ordre d'affichage des catégories */
export const PROFESSION_CATEGORY_ORDER = ['MEDICAL', 'PARAMEDICAL', 'SOCIAL', 'ADMINISTRATIVE'];

/** 🆕 S5 — Rôles obsolètes à masquer dans le wizard (supprimés v4.11) */
export const OBSOLETE_ROLE_NAMES = [
  'MEDECIN_TRAITANT',
  'MEDECIN_SPECIALISTE',
  'INFIRMIERE',
  'AIDE_SOIGNANTE',
  'KINESITHERAPEUTE',
  'AUXILIAIRE_VIE',
  'ASSISTANT_SOCIAL',
];

// =============================================================================
// ROLE
// =============================================================================

/** Rôle utilisateur */
export interface RoleResponse {
  id: number;
  name: string;
  description?: string;
  permissions: string[];
  is_system_role: boolean;
  tenant_id?: number;
  created_at: string;
}

/** Liste de rôles */
export interface RoleList {
  items: RoleResponse[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

/**
 * 🆕 R1 — Métadonnées d'affichage par rôle fonctionnel
 *
 * Chaque rôle système a une icône, une couleur d'accent et une description
 * utilisées dans RoleCard.vue pour la grille de la RolesPage.
 */
export const ROLE_DISPLAY_CONFIG: Record<
  string,
  {
    icon: string;
    color: string;
    description: string;
  }
> = {
  ADMIN: {
    icon: 'pi pi-shield',
    color: 'amber',
    description: 'Administration complète du tenant',
  },
  COORDINATEUR: {
    icon: 'pi pi-sitemap',
    color: 'teal',
    description: 'Coordination des parcours de soins',
  },
  REFERENT: {
    icon: 'pi pi-user-plus',
    color: 'blue',
    description: 'Référent patient désigné',
  },
  EVALUATEUR: {
    icon: 'pi pi-file-edit',
    color: 'violet',
    description: 'Habilité aux évaluations AGGIR',
  },
  INTERVENANT: {
    icon: 'pi pi-eye',
    color: 'slate',
    description: 'Accès ponctuel en lecture',
  },
};

// =============================================================================
// PERMISSIONS — Catégories, labels, résolution (R1 — RolesPage)
// =============================================================================

/**
 * 🆕 R1 — Catégories de permissions pour affichage groupé
 *
 * Synchronisé avec le mapping backend (section 8.4 des specs) :
 *   PATIENT_* → PATIENT, EVALUATION_* → EVALUATION, VITALS_* → VITALS,
 *   COORDINATION_* → COORDINATION, CAREPLAN_* → CAREPLAN, USER_* → USER,
 *   ENTITY_* / ADMIN_* / autres → ADMIN
 *
 * Note : ACCESS_* et ROLE_* sont regroupés sous USER (gestion des accès).
 */
export const PERMISSION_CATEGORIES: Record<
  string,
  {
    label: string;
    icon: string;
    color: string;
  }
> = {
  PATIENT: { label: 'Patients', icon: 'pi pi-users', color: 'teal' },
  EVALUATION: { label: 'Évaluations', icon: 'pi pi-file-edit', color: 'blue' },
  VITALS: { label: 'Constantes vitales', icon: 'pi pi-heart', color: 'red' },
  COORDINATION: { label: 'Coordination', icon: 'pi pi-comments', color: 'violet' },
  CAREPLAN: { label: "Plans d'aide", icon: 'pi pi-list-check', color: 'amber' },
  USER: { label: 'Utilisateurs', icon: 'pi pi-user-edit', color: 'slate' },
  ADMIN: { label: 'Administration', icon: 'pi pi-cog', color: 'zinc' },
};

/** 🆕 R1 — Ordre d'affichage des catégories dans le panel permissions */
export const PERMISSION_CATEGORY_ORDER = [
  'PATIENT',
  'EVALUATION',
  'VITALS',
  'COORDINATION',
  'CAREPLAN',
  'USER',
  'ADMIN',
];

/**
 * 🆕 R1 — Labels humains des permissions
 *
 * Couvre les ~20 permissions du tenant (matrice 8.2 des specs backend).
 * VITALS_CREATE est inclus car utilisé dans les permissions par profession.
 */
export const PERMISSION_LABELS: Record<string, string> = {
  // ── Patients ──────────────────────────────────────────────
  PATIENT_VIEW: 'Consulter les dossiers patients',
  PATIENT_CREATE: 'Créer un patient',
  PATIENT_EDIT: 'Modifier un dossier patient',

  // ── Évaluations ───────────────────────────────────────────
  EVALUATION_VIEW: 'Consulter les évaluations',
  EVALUATION_CREATE: 'Créer une évaluation',
  EVALUATION_VALIDATE: 'Valider une évaluation',

  // ── Constantes vitales ────────────────────────────────────
  VITALS_VIEW: 'Consulter les constantes vitales',
  VITALS_CREATE: 'Saisir des constantes vitales',

  // ── Coordination ──────────────────────────────────────────
  COORDINATION_VIEW: 'Consulter la coordination',
  COORDINATION_CREATE: 'Créer une note de coordination',
  COORDINATION_EDIT: 'Modifier une note de coordination',

  // ── Plans d'aide ──────────────────────────────────────────
  CAREPLAN_VIEW: "Consulter les plans d'aide",
  CAREPLAN_CREATE: "Créer un plan d'aide",
  CAREPLAN_EDIT: "Modifier un plan d'aide",
  CAREPLAN_VALIDATE: "Valider un plan d'aide",

  // ── Utilisateurs / Accès ──────────────────────────────────
  USER_VIEW: 'Consulter les professionnels',
  ACCESS_GRANT: 'Accorder un accès utilisateur',
  ACCESS_REVOKE: 'Révoquer un accès utilisateur',
  ROLE_VIEW: 'Consulter les rôles',
  ROLE_ASSIGN: 'Assigner un rôle',

  // ── Administration ────────────────────────────────────────
  ADMIN_FULL: 'Accès administrateur complet',
};

/**
 * 🆕 R1 — Résout la catégorie d'une permission à partir de son code
 *
 * Logique de résolution (alignée sur le backend section 8.4) :
 *   1. Mapping explicite pour les codes sans préfixe standard (ACCESS_*, ROLE_*)
 *   2. Extraction du préfixe (avant le premier _)
 *   3. Fallback → ADMIN
 */
export function getPermissionCategory(code: string): string {
  // Cas explicites : permissions dont le préfixe ne correspond pas à la catégorie UX
  const EXPLICIT: Record<string, string> = {
    ACCESS_GRANT: 'USER',
    ACCESS_REVOKE: 'USER',
    ROLE_VIEW: 'USER',
    ROLE_ASSIGN: 'USER',
  };
  if (EXPLICIT[code]) return EXPLICIT[code];

  // Résolution par préfixe
  const prefix = code.split('_')[0];
  const VALID = ['PATIENT', 'EVALUATION', 'VITALS', 'COORDINATION', 'CAREPLAN', 'USER', 'ADMIN'];
  return VALID.includes(prefix) ? prefix : 'ADMIN';
}

// =============================================================================
// USER
// =============================================================================

/** Utilisateur - Version résumée */
export interface UserSummary {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  rpps?: string;
  is_active: boolean;
}

/** Utilisateur - Version complète */
export interface UserResponse extends UserSummary {
  is_admin: boolean;
  profession?: ProfessionResponse;
  roles: RoleResponse[];
  role_names: string[];
  effective_permissions: string[]; // S4 — permissions profession ∪ rôles
  created_at: string;
  updated_at?: string;
  last_login?: string;
}

/** Utilisateur avec entités rattachées */
export interface UserWithEntities extends UserResponse {
  entity_associations: UserEntityResponse[];
}

/** Liste paginée */
export interface UserList {
  items: UserSummary[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

/** Création utilisateur */
export interface UserCreate {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  rpps?: string;
  profession_id?: number;
  is_admin?: boolean;
}

/** Mise à jour utilisateur */
export interface UserUpdate {
  email?: string;
  first_name?: string;
  last_name?: string;
  rpps?: string;
  profession_id?: number;
  is_active?: boolean;
}

/**
 * Paramètres de requête pour la liste des utilisateurs
 * Utilisé par userService.list() et admin.store.ts
 */
export interface UserQueryParams {
  /** Numéro de page (1-based) */
  page?: number;
  /** Nombre d'éléments par page */
  size?: number;
  /** Recherche textuelle (nom, prénom, email, RPPS) */
  search?: string;
  /** Filtrer par entité rattachée */
  entity_id?: number;
  /** Filtrer par nom de rôle */
  role?: string;
  /** Filtrer par profession */
  profession_id?: number;
  /** Filtrer par statut actif/inactif */
  is_active?: boolean;
}

// =============================================================================
// USER ENTITY (Rattachement)
// =============================================================================

/** Rattachement utilisateur-entité */
export interface UserEntityResponse {
  id: number;
  user_id: number;
  entity_id: number;
  is_primary: boolean;
  contract_type?: ContractType;
  start_date: string;
  end_date?: string;
  intervention_radius_km?: number;
  max_daily_patients?: number;
  is_active: boolean;
  entity_name?: string;
}

/** Création rattachement */
export interface UserEntityCreate {
  entity_id: number;
  is_primary?: boolean;
  contract_type?: ContractType;
  start_date: string;
  end_date?: string;
  intervention_radius_km?: number;
  max_daily_patients?: number;
}

/** Rattachement utilisateur-entité (réponse GET /users/:id/entities) */
export interface UserEntityAssignment {
  id: number;
  user_id: number;
  entity_id: number;
  entity_name?: string;
  is_primary: boolean;
  contract_type?: string;
  start_date?: string;
  end_date?: string;
}

// =============================================================================
// USER AVAILABILITY (Disponibilités)
// =============================================================================

/** Disponibilité utilisateur */
export interface UserAvailabilityResponse {
  id: number;
  user_id: number;
  entity_id?: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_recurring: boolean;
  is_active: boolean;
  day_name?: string;
  duration_minutes?: number;
  time_range_display?: string;
}

/** Création disponibilité */
export interface UserAvailabilityCreate {
  entity_id?: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_recurring?: boolean;
}

/** Liste de disponibilités */
export interface UserAvailabilityList {
  items: UserAvailabilityResponse[];
  total: number;
}
