<script setup lang="ts">
/**
 * Sidebar de navigation (desktop)
 * Menu organisé par espace métier : Soins, Coordination, Admin
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores'

defineProps<{
  collapsed: boolean
}>()

const emit = defineEmits<{
  toggle: []
}>()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// Navigation par espace métier
const menuItems = computed(() => {
  const items = [
    // Espace Soins - visible par tous
    {
      label: 'Soins',
      icon: 'pi-heart',
      visible: true,
      children: [
        { label: 'Ma journée', icon: 'pi-home', to: '/soins' },
        { label: 'Mes patients', icon: 'pi-users', to: '/soins/patients' },
        { label: 'Planning', icon: 'pi-calendar', to: '/soins/planning' },
        { label: 'Liaison', icon: 'pi-comments', to: '/soins/liaison' },
      ],
    },
    // Espace Admin - visible si admin
    {
      label: 'Administration',
      icon: 'pi-cog',
      visible: authStore.isAdmin,
      children: [
        { label: 'Tableau de bord', icon: 'pi-chart-bar', to: '/admin' },
        { label: 'Utilisateurs', icon: 'pi-users', to: '/admin/users' },
        { label: 'Rôles', icon: 'pi-shield', to: '/admin/roles' },
        { label: 'Patients', icon: 'pi-id-card', to: '/admin/patients' },
      ],
    },
  ]
  
  return items.filter(item => item.visible)
})

// Vérifier si une route est active
const isActive = (path: string) => {
  return route.path === path || route.path.startsWith(path + '/')
}

// Navigation
const navigate = (path: string) => {
  router.push(path)
}
</script>

<template>
  <aside
    class="fixed top-0 left-0 z-30 h-screen bg-white border-r border-neutral-200 transition-all duration-300"
    :class="collapsed ? 'w-20' : 'w-64'"
  >
    <!-- Header sidebar -->
    <div class="flex items-center h-16 px-4 border-b border-neutral-200">
      <!-- Logo -->
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg bg-primary-600 text-white flex items-center justify-center">
          <i class="pi pi-heart text-xl"></i>
        </div>
        <span
          v-if="!collapsed"
          class="font-bold text-lg text-neutral-900"
        >
          CareLink
        </span>
      </div>
      
      <!-- Bouton toggle -->
      <button
        class="ml-auto p-2 rounded-lg hover:bg-neutral-100 text-neutral-500"
        @click="emit('toggle')"
      >
        <i :class="collapsed ? 'pi pi-angle-right' : 'pi pi-angle-left'"></i>
      </button>
    </div>

    <!-- Navigation -->
    <nav class="p-4 space-y-6 overflow-y-auto h-[calc(100vh-4rem)] scrollbar-thin">
      <div v-for="section in menuItems" :key="section.label">
        <!-- Titre section -->
        <h3
          v-if="!collapsed"
          class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-2 px-3"
        >
          {{ section.label }}
        </h3>

        <!-- Items -->
        <ul class="space-y-1">
          <li v-for="item in section.children" :key="item.to">
            <button
              class="w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors"
              :class="isActive(item.to) 
                ? 'bg-primary-50 text-primary-700' 
                : 'text-neutral-600 hover:bg-neutral-100'"
              :title="collapsed ? item.label : undefined"
              @click="navigate(item.to)"
            >
              <i
                class="pi text-lg"
                :class="[
                  item.icon,
                  isActive(item.to) ? 'text-primary-600' : 'text-neutral-400'
                ]"
              ></i>
              <span v-if="!collapsed" class="text-sm font-medium">
                {{ item.label }}
              </span>
            </button>
          </li>
        </ul>
      </div>
    </nav>
  </aside>
</template>
