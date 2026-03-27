/**
 * Routes d'authentification
 * Login, callback PSC, logout
 */
import type { RouteRecordRaw } from 'vue-router';

const authRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/pages/auth/LoginPage.vue'),
    meta: {
      public: true,
      layout: 'auth',
      title: 'Connexion',
    },
  },

  {
    path: '/change-password',
    name: 'force-change-password',
    component: () => import('@/pages/auth/ForceChangePasswordPage.vue'),
    meta: {
      layout: 'auth',
      title: 'Changement de mot de passe',
      // PAS public: true → nécessite un token valide
    },
  },
  {
    path: '/auth/callback',
    name: 'auth-callback',
    component: () => import('@/pages/auth/CallbackPage.vue'),
    meta: {
      public: true,
      layout: 'auth',
      title: 'Connexion en cours...',
    },
  },
  {
    path: '/logout',
    name: 'logout',
    component: () => import('@/pages/auth/LogoutPage.vue'),
    meta: {
      public: true,
      layout: 'auth',
      title: 'Déconnexion',
    },
  },
];

export default authRoutes;
