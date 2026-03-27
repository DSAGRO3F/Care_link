/**
 * Routes Admin Client
 *
 * Toutes les routes de l'espace Admin Client.
 * Layout : AdminLayout (slate/blue)
 * Guard : requireAuth + requireAdminRole
 *
 * Sprint 1-6 : Dashboard, Users CRUD, Entities, Roles
 * Sprint 7   : Patients CRUD (🆕)
 *
 * Destination : src/router/routes/admin.ts
 */
import type { RouteRecordRaw } from 'vue-router';

const adminRoutes: RouteRecordRaw[] = [
  {
    path: '/admin',
    meta: { requiresAuth: true, layout: 'admin' },
    children: [
      // ── Dashboard ──
      {
        path: '',
        name: 'admin-dashboard',
        component: () => import('@/pages/admin/DashboardPage.vue'),
        meta: { title: 'Tableau de bord' },
      },

      // ── Users (Sprint 2-5) ──
      {
        path: 'users',
        name: 'admin-users',
        component: () => import('@/pages/admin/users/UsersPage.vue'),
        meta: { title: 'Professionnels' },
      },
      {
        path: 'users/new',
        name: 'admin-user-create',
        component: () => import('@/pages/admin/users/UserCreatePage.vue'),
        meta: { title: 'Nouveau professionnel' },
      },
      {
        path: 'users/:id',
        name: 'admin-user-detail',
        component: () => import('@/pages/admin/users/UserDetailPage.vue'),
        props: true,
        meta: { title: 'Professionnel' },
      },

      // ── Patients (Sprint 7 🆕) ──
      {
        path: 'patients',
        name: 'admin-patients',
        component: () => import('@/pages/admin/patients/PatientsPage.vue'),
        meta: { title: 'Patients' },
      },
      {
        path: 'patients/new',
        name: 'admin-patient-create',
        component: () => import('@/pages/admin/patients/PatientCreatePage.vue'),
        meta: { title: 'Nouveau patient' },
      },
      {
        path: 'patients/:id',
        name: 'admin-patient-detail',
        component: () => import('@/pages/admin/patients/PatientDetailPage_admin.vue'),
        props: true,
        meta: { title: 'Patient' },
      },

      // ── Entities (Sprint 6) ──
      {
        path: 'entities',
        name: 'admin-entities',
        component: () => import('@/pages/admin/entities/EntitiesPage.vue'),
        meta: { title: 'Structure' },
      },

      // ── Roles ──
      {
        path: 'roles',
        name: 'admin-roles',
        component: () => import('@/pages/admin/roles/RolesPage.vue'),
        meta: { title: 'Rôles' },
      },

      // ── Settings (futur) ──
      // {
      //   path: 'settings',
      //   name: 'admin-settings',
      //   component: () => import('@/pages/admin/settings/SettingsPage.vue'),
      //   meta: { title: 'Paramètres' },
      // },
    ],
  },
];

export default adminRoutes;
