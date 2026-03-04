/**
 * Configuration Vue Router
 * Définit les routes et les guards d'authentification
 *
 * 🆕 v4.11 : Redirection post-login par rôle
 *   - is_admin=true → /admin (Admin Client)
 *   - profession RPPS → /soins (Soignant)
 *   - Helper centralisé : getDefaultRoute() / getDefaultRouteName()
 *
 * Destination : src/router/index.ts
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores'
import { isAuthenticatedAsSuperAdmin } from '@/utils/platform-auth'
import { getDefaultRoute, getDefaultRouteName } from '@/utils/routing'

// Import des routes par module
import authRoutes from './routes/auth'
import soinsRoutes from './routes/soins'
import adminRoutes from './routes/admin'
import platformRoutes from './routes/platform'

// =============================================================================
// ROUTES
// =============================================================================

const routes: RouteRecordRaw[] = [
  // Routes d'authentification (publiques)
  ...authRoutes,

  // Routes Espace Soins (protégées)
  ...soinsRoutes,

  // Routes Espace Admin (protégées + rôle admin)
  ...adminRoutes,

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
        const authStore = useAuthStore()
        if (authStore.isAuthenticated && authStore.user) {
          return getDefaultRoute(authStore.user)
        }
      } catch {
        // Store pas encore prêt → fallback
      }
      return '/soins'
    },
  },

  // Page 404
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/pages/NotFoundPage.vue'),
    meta: { layout: 'auth' },
  },
]

// =============================================================================
// ROUTER INSTANCE
// =============================================================================

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    // Restaurer la position si retour arrière
    if (savedPosition) {
      return savedPosition
    }
    // Sinon scroll en haut
    return { top: 0 }
  },
})

// =============================================================================
// NAVIGATION GUARDS
// =============================================================================

router.beforeEach(async (to, _from, next) => {
  // Route publique → laisser passer
  if (to.meta.public) {
    return next()
  }

  // =========================================================================
  // GUARD SUPER ADMIN (Platform)
  // =========================================================================
  if (to.meta.requiresSuperAdmin) {
    // Vérifier si authentifié en tant que SuperAdmin
    if (!isAuthenticatedAsSuperAdmin()) {
      console.warn('[Router] Accès Platform refusé - SuperAdmin requis')
      return next({
        name: 'platform-login',
        query: { redirect: to.fullPath },
      })
    }
    // SuperAdmin authentifié → laisser passer
    return next()
  }

  // =========================================================================
  // GUARD UTILISATEUR STANDARD
  // =========================================================================
  const authStore = useAuthStore()

  // Route protégée → vérifier l'authentification
  if (!authStore.isAuthenticated) {
    // Rediriger vers login avec URL de retour
    return next({
      name: 'login',
      query: { redirect: to.fullPath },
    })
  }

  // =========================================================================
  // GUARD CHANGEMENT MOT DE PASSE OBLIGATOIRE
  // =========================================================================
  if (authStore.mustChangePassword && to.name !== 'force-change-password') {
    return next({ name: 'force-change-password' })
  }

  // =========================================================================
  // 🆕 AIGUILLAGE PAR RÔLE
  // =========================================================================
  // Un admin client qui tente d'accéder à /soins sans profession → /admin
  // Un soignant qui tente d'accéder à /admin sans droits → /soins
  const defaultRouteName = getDefaultRouteName(authStore.user)

  // Vérifier les rôles requis
  if (to.meta.roles) {
    const requiredRoles = to.meta.roles as string[]
    const hasRequiredRole = authStore.hasAnyRole(requiredRoles)

    if (!hasRequiredRole) {
      console.warn('[Router] Accès refusé - rôle manquant:', requiredRoles)
      return next({ name: defaultRouteName })
    }
  }

  // Vérifier si admin requis
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    console.warn('[Router] Accès refusé - admin requis')
    return next({ name: defaultRouteName })
  }

  next()
})

// =============================================================================
// EXPORT
// =============================================================================

export default router

// Types pour les meta des routes
declare module 'vue-router' {
  interface RouteMeta {
    /** Route accessible sans authentification */
    public?: boolean
    /** Layout à utiliser (défaut: 'default') */
    layout?: 'default' | 'auth' | 'platform' | 'admin'
    /** Rôles requis pour accéder */
    roles?: string[]
    /** Requiert le statut admin */
    requiresAdmin?: boolean
    /** Requiert le statut SuperAdmin (équipe CareLink) */
    requiresSuperAdmin?: boolean
    /** Titre de la page */
    title?: string
  }
}