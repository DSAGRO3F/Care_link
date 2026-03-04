<script setup lang="ts">
/**
 * AdminLayout.vue — Layout dédié à l'espace Admin Client
 *
 * Thème visuel : Slate / Teal
 *   - Sidebar : slate-900 (fond profond)
 *   - Accents : teal-500 / teal-400 (cohérent avec le card racine de l'arborescence)
 *   - Logo : gradient teal
 *   - Section titles : teal subtil
 *   - Footer : lien soins en teal
 *
 * La sidebar est intégrée directement (pas de composant séparé pour l'instant).
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUiStore, useAuthStore } from '@/stores'
import AppHeader from '@/components/common/AppHeader.vue'
import AppBottomNav from '@/components/common/AppBottomNav.vue'

const route = useRoute()
const router = useRouter()
const uiStore = useUiStore()
const authStore = useAuthStore()

// ─── Navigation items ────────────────────────────────────────────────────────

interface NavItem {
  name: string
  label: string
  icon: string
  routeName: string
  disabled?: boolean
}

const navSections: { title: string; items: NavItem[] }[] = [
  {
    title: 'Gestion',
    items: [
      { name: 'users', label: 'Professionnels', icon: 'pi pi-users', routeName: 'admin-users' },
      { name: 'patients', label: 'Patients', icon: 'pi pi-heart', routeName: 'admin-patients'},
      { name: 'entities', label: 'Structure', icon: 'pi pi-sitemap', routeName: 'admin-entities' },
    ],
  },
  {
    title: 'Configuration',
    items: [
      { name: 'roles', label: 'Rôles', icon: 'pi pi-shield', routeName: 'admin-roles' },
    ],
  },
]

// ─── State ───────────────────────────────────────────────────────────────────

const isCollapsed = computed(() => !uiStore.sidebarOpen)

const mainClasses = computed(() => ({
  'lg:ml-64': uiStore.sidebarOpen,
  'lg:ml-20': !uiStore.sidebarOpen,
}))

// ─── Helpers ─────────────────────────────────────────────────────────────────

function isActive(routeName: string): boolean {
  return route.name === routeName || (route.name?.toString().startsWith(routeName + '-') ?? false)
}

function navigateTo(item: NavItem) {
  if (!item.disabled) {
    router.push({ name: item.routeName })
  }
}

function goToSoins() {
  router.push({ name: 'soins-dashboard' })
}

// Initiales de l'utilisateur connecté
const userInitials = computed(() => {
  const user = authStore.user
  if (!user) return '?'
  return `${user.first_name?.[0] ?? ''}${user.last_name?.[0] ?? ''}`.toUpperCase()
})

const tenantName = computed(() => {
  // TODO: à brancher sur le tenant courant quand le store sera enrichi
  return 'Mon organisation'
})
</script>

<template>
  <div class="min-h-screen bg-slate-50">

    <!-- ─── Sidebar Desktop ─────────────────────────────────────────────── -->
    <aside
      v-if="!uiStore.isMobile"
      class="fixed inset-y-0 left-0 z-40 flex flex-col transition-all duration-300 border-r border-slate-800"
      :class="[
        isCollapsed ? 'w-20' : 'w-64',
        'bg-slate-900'
      ]"
    >
      <!-- Logo / Titre -->
      <div class="flex items-center h-16 px-4 border-b border-slate-800">
        <div class="flex items-center gap-3">
          <div
            class="flex items-center justify-center w-10 h-10 rounded-lg text-white font-bold text-sm"
            style="background: linear-gradient(135deg, #14b8a6, #0d9488)"
          >
            CL
          </div>
          <div v-if="!isCollapsed" class="flex flex-col">
            <span class="text-sm font-semibold text-white">CareLink</span>
            <span class="text-xs text-teal-400">Administration</span>
          </div>
        </div>
      </div>

      <!-- Dashboard (toujours visible en premier) -->
      <div class="px-3 pt-4 pb-2">
        <button
          class="flex items-center w-full gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors"
          :class="[
            isActive('admin-dashboard')
              ? 'bg-teal-500/15 text-teal-300 font-semibold'
              : 'text-slate-400 hover:bg-teal-500/10 hover:text-teal-200'
          ]"
          @click="router.push({ name: 'admin-dashboard' })"
          :title="isCollapsed ? 'Tableau de bord' : undefined"
        >
          <i class="pi pi-th-large text-lg" />
          <span v-if="!isCollapsed">Tableau de bord</span>
        </button>
      </div>

      <!-- Sections de navigation -->
      <nav class="flex-1 px-3 py-2 space-y-6 overflow-y-auto">
        <div v-for="section in navSections" :key="section.title">
          <!-- Titre de section -->
          <div
            v-if="!isCollapsed"
            class="px-3 mb-2 text-xs font-semibold tracking-wider uppercase text-teal-500/60"
          >
            {{ section.title }}
          </div>
          <div v-else class="mb-2 border-b border-slate-800" />

          <!-- Items -->
          <div class="space-y-1">
            <button
              v-for="item in section.items"
              :key="item.name"
              class="flex items-center w-full gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors"
              :class="[
                item.disabled
                  ? 'text-slate-600 cursor-not-allowed'
                  : isActive(item.routeName)
                    ? 'bg-teal-500/15 text-teal-300 font-semibold'
                    : 'text-slate-400 hover:bg-teal-500/10 hover:text-teal-200'
              ]"
              :disabled="item.disabled"
              :title="isCollapsed ? item.label : undefined"
              @click="navigateTo(item)"
            >
              <i :class="[item.icon, 'text-lg']" />
              <span v-if="!isCollapsed">{{ item.label }}</span>
              <!-- Badge "bientôt" pour les items désactivés -->
              <span
                v-if="item.disabled && !isCollapsed"
                class="ml-auto text-xs px-1.5 py-0.5 rounded bg-slate-800 text-slate-500"
              >
                bientôt
              </span>
            </button>
          </div>
        </div>
      </nav>

      <!-- Pied de sidebar : accès rapide vers Espace Soins -->
      <div class="px-3 py-4 border-t border-slate-800">
        <button
          class="flex items-center w-full gap-3 px-3 py-2.5 rounded-lg text-sm text-teal-400/70 hover:bg-teal-500/10 hover:text-teal-200 transition-colors"
          :title="isCollapsed ? 'Espace soins' : undefined"
          @click="goToSoins"
        >
          <i class="pi pi-heart text-lg" />
          <span v-if="!isCollapsed">Espace soins →</span>
        </button>
      </div>

      <!-- Bouton toggle sidebar -->
      <button
        class="absolute -right-3 top-20 flex items-center justify-center w-6 h-6 rounded-full bg-slate-800 border border-slate-700 text-slate-400 hover:text-teal-300 hover:bg-slate-700 transition-colors shadow-sm"
        @click="uiStore.toggleSidebar"
      >
        <i :class="isCollapsed ? 'pi pi-angle-right' : 'pi pi-angle-left'" class="text-xs" />
      </button>
    </aside>

    <!-- ─── Contenu principal ───────────────────────────────────────────── -->
    <div
      class="flex flex-col min-h-screen transition-all duration-300"
      :class="mainClasses"
    >
      <!-- Header -->
      <AppHeader />

      <!-- Zone de contenu -->
      <main class="flex-1 p-4 lg:p-6 pb-20 lg:pb-6">
        <slot />
      </main>
    </div>

    <!-- ─── Navigation mobile (bottom) ──────────────────────────────────── -->
    <AppBottomNav v-if="uiStore.isMobile" />
  </div>
</template>