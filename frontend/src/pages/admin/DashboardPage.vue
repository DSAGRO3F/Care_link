<script setup lang="ts">
/**
 * DashboardPage.vue — Tableau de bord Admin Client
 *
 * Cockpit de l'administrateur : 4 cards de raccourcis dynamiques
 * avec compteurs temps réel (Professionnels, Patients, Structure, Rôles).
 *
 * Chaque card = une jauge branchée sur l'API via des appels légers (size=1)
 * pour récupérer uniquement le compteur `total`, sans charger les données.
 *
 * Destination : src/pages/admin/DashboardPage.vue
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'

// ─── Types ───────────────────────────────────────────────────────────────────

interface DashboardCard {
  key: string
  label: string
  sublabel: string
  icon: string
  colorClass: string
  bgClass: string
  route: string
  count: number | null
  loading: boolean
  error: boolean
}

// ─── State ───────────────────────────────────────────────────────────────────

const router = useRouter()


const cards = ref<DashboardCard[]>([
  {
    key: 'users',
    label: 'Professionnels',
    sublabel: 'Gérer les professionnels de santé',
    icon: 'pi pi-users',
    colorClass: 'text-teal-600',
    bgClass: 'bg-teal-50',
    route: '/admin/users',
    count: null,
    loading: true,
    error: false,
  },
  {
    key: 'patients',
    label: 'Patients',
    sublabel: 'Gérer les patients pris en charge',
    icon: 'pi pi-id-card',
    colorClass: 'text-cyan-600',
    bgClass: 'bg-cyan-50',
    route: '/admin/patients',
    count: null,
    loading: true,
    error: false,
  },
  {
    key: 'entities',
    label: 'Structure',
    sublabel: 'Organisation et entités',
    icon: 'pi pi-building',
    colorClass: 'text-slate-600',
    bgClass: 'bg-slate-50',
    route: '/admin/entities',
    count: null,
    loading: true,
    error: false,
  },
  {
    key: 'roles',
    label: 'Rôles',
    sublabel: 'Rôles et permissions',
    icon: 'pi pi-shield',
    colorClass: 'text-amber-600',
    bgClass: 'bg-amber-50',
    route: '/admin/roles',
    count: null,
    loading: true,
    error: false,
  },
])

// ─── Data fetching ───────────────────────────────────────────────────────────

/**
 * Récupère un compteur depuis un endpoint paginé (size=1 → on ne veut que `total`).
 * Gère gracieusement les erreurs : la card affiche `--` en cas d'échec.
 */
async function fetchCount(
  index: number,
  url: string,
  extractTotal: (data: any) => number
) {
  try {
    const { data } = await api.get(url)
    cards.value[index].count = extractTotal(data)
  } catch (err) {
    if (import.meta.env.DEV) {
      console.error(`[Dashboard] Erreur chargement ${cards.value[index].key}:`, err)
    }
    cards.value[index].error = true
  } finally {
    cards.value[index].loading = false
  }
}

/**
 * Extracteur de total robuste :
 * Gère les réponses paginées { total: N } et les listes brutes [...]
 */
function extractTotal(data: any): number {
  if (typeof data?.total === 'number') return data.total
  if (Array.isArray(data)) return data.length
  if (Array.isArray(data?.items)) return data.items.length
  return 0
}

onMounted(() => {
  // 4 appels légers en parallèle — chaque card se charge indépendamment
  Promise.allSettled([
    fetchCount(0, '/users?page=1&size=1', (d) => d.total),
    fetchCount(1, '/patients?page=1&size=1', (d) => d.total),
    fetchCount(2, '/entities?page=1&size=1', extractTotal),
    fetchCount(3, '/roles', extractTotal),
  ])
})

// ─── Navigation ──────────────────────────────────────────────────────────────

function navigateTo(route: string) {
  router.push(route)
}
</script>

<template>
  <div class="space-y-8">
    <!-- ── Header de bienvenue ── -->
    <div>
      <h1 class="text-2xl font-semibold text-slate-800">
        Administration
      </h1>
      <p class="mt-1 text-sm text-slate-500">
        Vue d'ensemble de votre structure
      </p>
    </div>

    <!-- ── Cards compteurs ── -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      <button
        v-for="card in cards"
        :key="card.key"
        class="dashboard-card group"
        @click="navigateTo(card.route)"
      >
        <!-- Icône -->
        <div
          class="flex items-center justify-center w-12 h-12 rounded-xl transition-transform duration-200 group-hover:scale-110"
          :class="card.bgClass"
        >
          <i :class="[card.icon, card.colorClass, 'text-xl']"></i>
        </div>

        <!-- Compteur + Label -->
        <div class="mt-4 text-left">
          <!-- Skeleton loading -->
          <div v-if="card.loading" class="h-8 w-16 bg-slate-100 rounded animate-pulse"></div>

          <!-- Erreur -->
          <div
            v-else-if="card.error"
            class="text-2xl font-bold text-slate-300"
            title="Données indisponibles"
          >
            --
          </div>

          <!-- Compteur réel -->
          <div v-else class="text-2xl font-bold text-slate-800">
            {{ card.count }}
          </div>

          <div class="mt-1 text-sm font-medium text-slate-600">
            {{ card.label }}
          </div>
          <div class="mt-0.5 text-xs text-slate-400">
            {{ card.sublabel }}
          </div>
        </div>

        <!-- Flèche de navigation -->
        <div
          class="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
        >
          <i class="pi pi-arrow-right text-sm text-slate-400"></i>
        </div>
      </button>
    </div>

    <!-- ── Activité récente (placeholder) ── -->
    <div class="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div class="px-6 py-4 border-b border-slate-100">
        <h2 class="text-base font-semibold text-slate-700">Activité récente</h2>
      </div>
      <div class="px-6 py-12 text-center">
        <i class="pi pi-clock text-3xl text-slate-200 mb-3"></i>
        <p class="text-sm text-slate-400">
          Le journal d'activité sera disponible prochainement
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard-card {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 1.25rem;
  background: white;
  border: 1px solid #e2e8f0; /* slate-200 */
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.dashboard-card:hover {
  border-color: #94a3b8; /* slate-400 */
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08); /* slate-900 shadow */
  transform: translateY(-2px);
}

.dashboard-card:focus-visible {
  outline: 2px solid #14b8a6; /* teal-500 */
  outline-offset: 2px;
}

.dashboard-card:active {
  transform: translateY(0);
}
</style>