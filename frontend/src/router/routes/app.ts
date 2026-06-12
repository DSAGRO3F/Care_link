/**
 * Routes métier intra-tenant (`/admin/*` et `/soins/*`).
 *
 * Issu de la fusion physique de `admin.ts` + `soins.ts` (B48 Palier 4 / 4b).
 * Les deux préfixes `/admin` et `/soins` sont conservés comme libellés
 * d'URL (Décision 3 du cadrage B48) — préservation des bookmarks et
 * support de la navigation espace-aware (Convention #125 : `AppSidebar`
 * et `AppBottomNav` détectent le contexte via `route.path.startsWith('/soins')`).
 *
 * Organisation par ressource fonctionnelle (et non par espace) : chaque
 * bloc regroupe les routes touchant à un même domaine métier (Patients,
 * Plans d'aide, Catalogue, etc.), qu'elles soient sous /admin ou /soins.
 * Reflète l'objectif d'unification : l'espace est cosmétique, c'est la
 * ressource qui structure.
 *
 * `meta.requiredPermissions` (B48 P4 / 4b) : déclare la permission
 * minimale d'accès à chaque route (sémantique OR — au moins un des codes
 * suffit). `ADMIN_FULL` court-circuite nativement via les getters du
 * `auth.store` (Palier 1, court-circuit deux étages `isAdmin` / `ADMIN_FULL`).
 *
 * État runtime à la fin de 4b : `meta.requiredPermissions` est posé mais
 * NON LU — le guard de lecture est activé en 4c (`router/index.ts`
 * beforeEach). Comportement applicatif strictement iso à l'état pré-4b.
 *
 * Cartographie route → permission validée en 4a (resume_session 4a).
 *
 * Destination : src/router/routes/app.ts
 */
import type { RouteRecordRaw } from 'vue-router';

const appRoutes: RouteRecordRaw[] = [
  // ════════════════════════════════════════════════════════════════════
  // BLOC 1 — DASHBOARDS
  // ════════════════════════════════════════════════════════════════════

  // Admin dashboard — B2, ADMIN_FULL (page panoramique sans code dédié)
  {
    path: '/admin',
    name: 'admin-dashboard',
    component: () => import('@/pages/admin/DashboardPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Tableau de bord',
      requiredPermissions: ['ADMIN_FULL'],
    },
  },

  // Soins dashboard — A, requiresAuth seul (écran d'accueil post-login
  // pour tout non-admin ; contenu gaté à l'intérieur de la page)
  {
    path: '/soins',
    name: 'soins-dashboard',
    component: () => import('@/pages/soins/DashboardPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Ma journée',
    },
  },

  // ════════════════════════════════════════════════════════════════════
  // BLOC 2 — PATIENTS (composants partagés — Palier 2)
  // ════════════════════════════════════════════════════════════════════

  // Liste patients — B1, PATIENT_VIEW (composant partagé, liste RLS filtrée)
  {
    path: '/admin/patients',
    name: 'admin-patients',
    component: () => import('@/pages/shared/patient/PatientsPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Patients',
      requiredPermissions: ['PATIENT_VIEW'],
    },
  },
  {
    path: '/soins/patients',
    name: 'soins-patients',
    component: () => import('@/pages/shared/patient/PatientsPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Mes patients',
      requiredPermissions: ['PATIENT_VIEW'],
    },
  },

  // Création patient — A, PATIENT_CREATE (COORDINATEUR seul + admin)
  {
    path: '/admin/patients/new',
    name: 'admin-patient-create',
    component: () => import('@/pages/admin/patients/PatientCreatePage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Nouveau patient',
      requiredPermissions: ['PATIENT_CREATE'],
    },
  },
  {
    path: '/soins/patients/new',
    name: 'soins-patient-create',
    component: () => import('@/pages/admin/patients/PatientCreatePage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Nouveau patient',
      requiredPermissions: ['PATIENT_CREATE'],
    },
  },

  // Détail patient — A, PATIENT_VIEW (composant partagé, B48 Palier 2 Lot B)
  {
    path: '/admin/patients/:id',
    name: 'admin-patient-detail',
    component: () => import('@/pages/shared/patient/PatientDetailPage.vue'),
    props: true,
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Patient',
      requiredPermissions: ['PATIENT_VIEW'],
    },
  },
  {
    path: '/soins/patients/:id',
    name: 'soins-patient-detail',
    component: () => import('@/pages/shared/patient/PatientDetailPage.vue'),
    props: true,
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Dossier patient',
      requiredPermissions: ['PATIENT_VIEW'],
    },
  },

  // ════════════════════════════════════════════════════════════════════
  // BLOC 3 — ÉVALUATIONS
  // ════════════════════════════════════════════════════════════════════

  // Création évaluation — A, EVALUATION_CREATE
  {
    path: '/soins/patients/:patientId/evaluations/new',
    name: 'soins-evaluation-create',
    component: () => import('@/pages/soins/EvaluationCreatePage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Nouvelle évaluation',
      requiredPermissions: ['EVALUATION_CREATE'],
    },
  },

  // Édition brouillon évaluation — A, EVALUATION_CREATE
  // (continuation du flow de création ; EVALUATION_EDIT non distribué,
  // admin-only via ADMIN_FULL — une évaluation AGGIR validée est un
  // document opposable CASF, figée par construction)
  {
    path: '/soins/patients/:patientId/evaluations/:evaluationId/edit',
    name: 'soins-evaluation-edit',
    component: () => import('@/pages/soins/EvaluationCreatePage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: "Modifier l'évaluation",
      requiredPermissions: ['EVALUATION_CREATE'],
    },
  },

  // ════════════════════════════════════════════════════════════════════
  // BLOC 4 — PLANS D'AIDE (Phase 4)
  // ════════════════════════════════════════════════════════════════════

  // Liste exhaustive plans d'aide — B2, ADMIN_FULL (vue de gouvernance
  // tenant ; backlog : future route /soins/care-plans B1 CAREPLAN_VIEW
  // pour vue transverse coordinateur RLS-filtered)
  {
    path: '/admin/care-plans',
    name: 'admin-care-plans',
    component: () => import('@/pages/admin/careplan/CarePlanListPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: "Plans d'aide",
      requiredPermissions: ['ADMIN_FULL'],
    },
  },

  // Création plan d'aide — A, CAREPLAN_CREATE (COORDINATEUR seul + admin)
  {
    path: '/admin/care-plans/create',
    name: 'admin-care-plans-create',
    component: () => import('@/pages/admin/careplan/CarePlanCreatePage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: "Nouveau plan d'aide",
      requiredPermissions: ['CAREPLAN_CREATE'],
    },
  },
  {
    path: '/soins/care-plans/new',
    name: 'soins-care-plans-create',
    component: () => import('@/pages/admin/careplan/CarePlanCreatePage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: "Nouveau plan d'aide",
      requiredPermissions: ['CAREPLAN_CREATE'],
    },
  },

  // Mes brouillons plans d'aide — A, CAREPLAN_CREATE
  // (« mes » brouillons → il faut pouvoir créer pour en avoir)
  {
    path: '/admin/care-plans/drafts',
    name: 'admin-care-plans-drafts',
    component: () => import('@/pages/admin/careplan/CarePlanDraftsPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Mes brouillons',
      requiredPermissions: ['CAREPLAN_CREATE'],
    },
  },
  {
    path: '/soins/care-plans/drafts',
    name: 'soins-care-plans-drafts',
    component: () => import('@/pages/admin/careplan/CarePlanDraftsPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Mes brouillons',
      requiredPermissions: ['CAREPLAN_CREATE'],
    },
  },

  // Détail plan d'aide — A, CAREPLAN_VIEW
  {
    path: '/admin/care-plans/:id',
    name: 'admin-care-plans-detail',
    component: () => import('@/pages/admin/careplan/CarePlanDetailPage.vue'),
    props: true,
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: "Plan d'aide",
      requiredPermissions: ['CAREPLAN_VIEW'],
    },
  },
  {
    path: '/soins/care-plans/:id',
    name: 'soins-care-plans-detail',
    component: () => import('@/pages/admin/careplan/CarePlanDetailPage.vue'),
    props: true,
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: "Plan d'aide",
      requiredPermissions: ['CAREPLAN_VIEW'],
    },
  },

  // ════════════════════════════════════════════════════════════════════
  // BLOC 4bis — VALIDATION (Phase 4 bis — portail valideur, B40-J4)
  // ════════════════════════════════════════════════════════════════════

  // Inbox validation — B1, VALIDATION_VIEW (liste des demandes visibles,
  // fenêtre RLS : émetteur + valideur assigné + admin tenant). Cible de
  // l'entrée sidebar SOINS.
  {
    path: '/soins/validation',
    name: 'soins-validation',
    component: () => import('@/pages/soins/validation/ValidationInboxPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Validation',
      requiredPermissions: ['VALIDATION_VIEW'],
    },
  },

  // Dossier de validation — B1, VALIDATION_VIEW (écran unifié, fil d'échange).
  // Atteint depuis l'inbox ou depuis la cloche de notifications (link_url, J7).
  {
    path: '/soins/validation/:vrId',
    name: 'soins-validation-dossier',
    component: () => import('@/pages/soins/validation/ValidationDossierPage.vue'),
    props: true,
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Dossier de validation',
      requiredPermissions: ['VALIDATION_VIEW'],
    },
  },

  // ════════════════════════════════════════════════════════════════════
  // BLOC 4ter — NOTIFICATIONS (Phase 4 bis — cloche in-app, S1 / B40-J4)
  // ════════════════════════════════════════════════════════════════════

  // Page « Toutes les notifications » — requiresAuth seul (pas de permission :
  // la RLS atypique #130 par destinataire fait office de contrôle d'accès).
  // Atteinte depuis le lien « Tout voir » de la cloche (AppHeader).
  {
    path: '/notifications',
    name: 'notifications',
    component: () => import('@/pages/shared/notifications/NotificationsPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Notifications',
    },
  },

  // ════════════════════════════════════════════════════════════════════
  // BLOC 5 — PLANNING
  // ════════════════════════════════════════════════════════════════════

  // Planning soignant — B1, SCHEDULE_VIEW (RLS filtrée au périmètre)
  {
    path: '/soins/planning',
    name: 'soins-planning',
    component: () => import('@/pages/soins/PlanningPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Mon planning',
      requiredPermissions: ['SCHEDULE_VIEW'],
    },
  },

  // ════════════════════════════════════════════════════════════════════
  // BLOC 6 — CARNET DE LIAISON
  // ════════════════════════════════════════════════════════════════════

  // Carnet de liaison — B1, COORDINATION_VIEW (RLS filtrée)
  {
    path: '/soins/liaison',
    name: 'soins-liaison',
    component: () => import('@/pages/soins/LiaisonPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Carnet de liaison',
      requiredPermissions: ['COORDINATION_VIEW'],
    },
  },

  // ════════════════════════════════════════════════════════════════════
  // BLOC 7 — CATALOGUE
  // ════════════════════════════════════════════════════════════════════

  // Catalogue entité — B2, ADMIN_FULL (gestion du catalogue tenant ;
  // CATALOG_CREATE/EDIT/DELETE non distribués, admin-only)
  {
    path: '/admin/catalog',
    name: 'admin-catalog',
    component: () => import('@/pages/admin/catalog/EntityCatalogPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Catalogue',
      requiredPermissions: ['ADMIN_FULL'],
    },
  },
  // Catalogue coordination — B2, ADMIN_FULL
  // (gating désormais porté exclusivement par requiredPermissions, B48 P4 / 4c)
  {
    path: '/admin/coordination-catalog',
    name: 'admin-coordination-catalog',
    component: () => import('@/pages/admin/catalog/CoordinationCatalogPage.vue'),
    meta: {
     requiresAuth: true,
     layout: 'default',
     title: 'Catalogue coordination',
     requiredPermissions: ['ADMIN_FULL'],
    },
  },

  // ════════════════════════════════════════════════════════════════════
  // BLOC 8 — USERS / PROFESSIONNELS
  // ════════════════════════════════════════════════════════════════════

  // Liste pros — B2 accès élargi, USER_VIEW
  // (COORDINATEUR a USER_VIEW pour consulter son équipe)
  {
    path: '/admin/users',
    name: 'admin-users',
    component: () => import('@/pages/admin/users/UsersPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Professionnels',
      requiredPermissions: ['USER_VIEW'],
    },
  },

  // Création pro — A, USER_CREATE
  // (non distribué → admin-only de facto via court-circuit ADMIN_FULL ;
  // code granulaire conservé pour future granularité)
  {
    path: '/admin/users/new',
    name: 'admin-user-create',
    component: () => import('@/pages/admin/users/UserCreatePage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Nouveau professionnel',
      requiredPermissions: ['USER_CREATE'],
    },
  },

  // Détail pro — A, USER_VIEW
  {
    path: '/admin/users/:id',
    name: 'admin-user-detail',
    component: () => import('@/pages/admin/users/UserDetailPage.vue'),
    props: true,
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Professionnel',
      requiredPermissions: ['USER_VIEW'],
    },
  },

  // ════════════════════════════════════════════════════════════════════
  // BLOC 9 — ROLES
  // ════════════════════════════════════════════════════════════════════

  // Gestion rôles — B2 accès élargi, ROLE_VIEW
  // (COORDINATEUR consulte ; actions CRUD ROLE_CREATE/EDIT/DELETE
  // admin-only par court-circuit, gating bouton à l'intérieur de la page)
  {
    path: '/admin/roles',
    name: 'admin-roles',
    component: () => import('@/pages/admin/roles/RolesPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Rôles',
      requiredPermissions: ['ROLE_VIEW'],
    },
  },

  // ════════════════════════════════════════════════════════════════════
  // BLOC 10 — ENTITIES / STRUCTURE
  // ════════════════════════════════════════════════════════════════════

  // Structure (entités) — B2, ADMIN_FULL
  // (aucun code ENTITY_* au MVP — Décision 2 du cadrage B48)
  {
    path: '/admin/entities',
    name: 'admin-entities',
    component: () => import('@/pages/admin/entities/EntitiesPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Structure',
      requiredPermissions: ['ADMIN_FULL'],
    },
  },

  // ════════════════════════════════════════════════════════════════════
  // BLOC 11 — ERREURS
  // ════════════════════════════════════════════════════════════════════

  // Page 403 — accès refusé (B48 Palier 4 / 4c)
  // requiresAuth seul : pas de requiredPermissions (sinon boucle infinie
  // — le guard du beforeEach redirige ici quand requiredPermissions échoue)
  {
    path: '/not-authorized',
    name: 'not-authorized',
    component: () => import('@/pages/NotAuthorizedPage.vue'),
    meta: {
      requiresAuth: true,
      layout: 'default',
      title: 'Accès refusé',
    },
  },
];

export default appRoutes;
