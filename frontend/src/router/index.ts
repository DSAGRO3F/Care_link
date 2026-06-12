/**
 * Configuration Vue Router
 * Définit les routes et les guards d'authentification.
 *
 * Aiguillage post-login par permission (B48 Palier 4) :
 *   - effective_permissions inclut ADMIN_FULL → /admin (Admin Client)
 *   - sinon                                    → /soins (Soignant)
 *   - Helper centralisé : getDefaultRoute() / getDefaultRouteName()
 *
 * Guard par permission sur les routes métier (B48 Palier 4 / 4c) :
 *   `meta.requiredPermissions: string[]` — sémantique OR, court-circuit
 *   ADMIN_FULL natif via les getters du auth.store.
 *
 * Destination : src/router/index.ts
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { useAuthStore } from '@/stores';
import { isAuthenticatedAsSuperAdmin } from '@/utils/platform-auth';
import { getDefaultRoute } from '@/utils/routing';

// Import des routes par module
import authRoutes from './routes/auth';
import appRoutes from './routes/app';
import platformRoutes from './routes/platform';

// =============================================================================
// ROUTES
// =============================================================================

const routes: RouteRecordRaw[] = [
  // Routes d'authentification (publiques)
  ...authRoutes,

  // Routes métier intra-tenant (/admin/* et /soins/*, B48 Palier 4)
  ...appRoutes,

  // Routes Espace Platform (SuperAdmin)
  ...platformRoutes,

  // Redirection racine — 🆕 dynamique selon le rôle
  // Note : la redirection finale est gérée dans le beforeEach guard
  // car au moment de la définition des routes, le store n'est pas encore disponible.
  // On redirige vers /soins par défaut, le guard corrigera si nécessaire.
  {
    path: '/',
    name: 'root',
    redirect: () => {
      // Tentative de lecture du store (peut ne pas être initialisé)
      try {
        const authStore = useAuthStore();
        if (authStore.isAuthenticated && authStore.user) {
          return getDefaultRoute(authStore.user);
        }
      } catch {
        // Store pas encore prêt → fallback
      }
      return '/soins';
    },
  },

  // Page 404
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/pages/NotFoundPage.vue'),
    meta: { layout: 'auth' },
  },
];

// =============================================================================
// ROUTER INSTANCE
// =============================================================================

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    // Restaurer la position si retour arrière
    if (savedPosition) {
      return savedPosition;
    }
    // Sinon scroll en haut
    return { top: 0 };
  },
});

// =============================================================================
// NAVIGATION GUARDS
// =============================================================================

router.beforeEach(async (to, _from, next) => {
  // Route publique → laisser passer
  if (to.meta.public) {
    return next();
  }

  // =========================================================================
  // GUARD SUPER ADMIN (Platform)
  // =========================================================================
  if (to.meta.requiresSuperAdmin) {
    // Vérifier si authentifié en tant que SuperAdmin
    if (!isAuthenticatedAsSuperAdmin()) {
      console.warn('[Router] Accès Platform refusé - SuperAdmin requis');
      return next({
        name: 'platform-login',
        query: { redirect: to.fullPath },
      });
    }
    // SuperAdmin authentifié → laisser passer
    return next();
  }

  // =========================================================================
  // GUARD UTILISATEUR STANDARD
  // =========================================================================
  const authStore = useAuthStore();

  // Route protégée → vérifier l'authentification
  if (!authStore.isAuthenticated) {
    // Rediriger vers login avec URL de retour
    return next({
      name: 'login',
      query: { redirect: to.fullPath },
    });
  }

  // =========================================================================
  // GUARD CHANGEMENT MOT DE PASSE OBLIGATOIRE
  // =========================================================================
  if (authStore.mustChangePassword && to.name !== 'force-change-password') {
    return next({ name: 'force-change-password' });
  }

  // =========================================================================
  // GUARD PAR PERMISSION (B48 Palier 4)
  // =========================================================================
  // Lit `meta.requiredPermissions` (sémantique OR, court-circuit ADMIN_FULL
  // natif via les getters du auth.store, cf. resume Palier 1).
  if (to.meta.requiredPermissions) {
    const requiredPermissions = to.meta.requiredPermissions as string[];
    const hasRequiredPermission = authStore.hasAnyPermission(requiredPermissions);

    if (!hasRequiredPermission) {
      console.warn(
        '[Router] Accès refusé - permission manquante:',
        requiredPermissions,
        'pour la route:',
        to.fullPath,
      );
      return next({ name: 'not-authorized' });
    }
  }

  next();
});

// =============================================================================
// EXPORT
// =============================================================================

export default router;

// Types pour les meta des routes
declare module 'vue-router' {
  interface RouteMeta {
    /** Route accessible sans authentification */
    public?: boolean;
    /** Layout à utiliser (défaut: 'default') */
    layout?: 'default' | 'auth' | 'platform';
    /** Requiert le statut SuperAdmin (équipe CareLink) */
    requiresSuperAdmin?: boolean;
    /**
     * Permissions requises pour accéder à la route (B48 Palier 4).
     * Sémantique OR : au moins un des codes suffit.
     * `ADMIN_FULL` court-circuite via les getters du auth.store.
     */
    requiredPermissions?: string[];
    /** Titre de la page */
    title?: string;
  }
}
