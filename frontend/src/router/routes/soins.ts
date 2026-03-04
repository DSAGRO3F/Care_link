/**
 * Routes de l'Espace Soins
 * Dashboard, patients, planning, carnet de liaison
 */
import type { RouteRecordRaw } from 'vue-router'

const soinsRoutes: RouteRecordRaw[] = [
  {
    path: '/soins',
    name: 'soins',
    redirect: { name: 'soins-dashboard' },
    meta: {
      layout: 'default',  // Explicite — sera remplacé par 'soins' quand on créera SoinsLayout
    },
    children: [
      // Dashboard "Ma journée"
      {
        path: '',
        name: 'soins-dashboard',
        component: () => import('@/pages/soins/DashboardPage.vue'),
        meta: {
          title: 'Ma journée',
        },
      },

      // Évaluation — création
      {
      path: 'patients/:patientId/evaluations/new',
      name: 'soins-evaluation-create',
      component: () => import('@/pages/soins/EvaluationCreatePage.vue'),
      meta: {
        title: 'Nouvelle évaluation',
        },
      },

    // Évaluation — édition brouillon
    {
      path: 'patients/:patientId/evaluations/:evaluationId/edit',
      name: 'soins-evaluation-edit',
      component: () => import('@/pages/soins/EvaluationCreatePage.vue'),
      meta: {
        title: 'Modifier l\'évaluation',
      },
    },
      
      // Liste des patients
      {
        path: 'patients',
        name: 'soins-patients',
        component: () => import('@/pages/soins/PatientsPage.vue'),
        meta: {
          title: 'Mes patients',
        },
      },
      
      // Dossier patient (avec onglets via query param)
      {
        path: 'patients/:id',
        name: 'soins-patient-detail',
        component: () => import('@/pages/soins/PatientDetailPage.vue'),
        meta: {
          title: 'Dossier patient',
        },
        props: true,
      },
      
      // Planning
      {
        path: 'planning',
        name: 'soins-planning',
        component: () => import('@/pages/soins/PlanningPage.vue'),
        meta: {
          title: 'Mon planning',
        },
      },
      
      // Carnet de liaison
      {
        path: 'liaison',
        name: 'soins-liaison',
        component: () => import('@/pages/soins/LiaisonPage.vue'),
        meta: {
          title: 'Carnet de liaison',
        },
      },
    ],
  },
]

export default soinsRoutes
