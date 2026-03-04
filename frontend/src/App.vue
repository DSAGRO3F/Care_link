<script setup lang="ts">
/**
 * Composant racine de l'application
 * - Affiche le layout approprié selon la route
 * - Gère les notifications Toast globales
 * - Détecte le statut online/offline
 */
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'


// Stores
import { useOfflineStore } from '@/stores/offline.store'
import { useUiStore } from '@/stores/ui.store'

// Layouts
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import AuthLayout from '@/layouts/AuthLayout.vue'
import PlatformLayout from '@/layouts/PlatformLayout.vue'
import AdminLayout from '@/layouts/AdminLayout.vue'


const route = useRoute()
const offlineStore = useOfflineStore()
const uiStore = useUiStore()

// Détermine le layout à utiliser selon la route
const layout = computed(() => {
  // Routes d'authentification = layout minimal
  if (route.meta.layout === 'auth') {
    return AuthLayout
  }
  if (route.meta.layout === 'platform')
    return PlatformLayout
  if (route.meta.layout === 'admin')
    return AdminLayout

  // Par défaut = layout complet avec sidebar
  return DefaultLayout
})

// Initialiser la détection offline au montage
offlineStore.initialize()

// Initialiser le store UI (responsive breakpoints + thème sombre)
uiStore.initialize()

// Log du statut online/offline (dev uniquement)
if (import.meta.env.DEV) {
  watch(() => offlineStore.isOnline, (isOnline) => {
    console.log(`[CareLink] Statut réseau: ${isOnline ? '🟢 En ligne' : '🔴 Hors ligne'}`)
  })
}
</script>

<template>
  <!-- Notifications Toast globales -->
  <Toast position="top-right" />

  <!-- Dialogues de confirmation -->
  <ConfirmDialog />

  <!-- Indicateur mode offline -->
  <div
    v-if="!offlineStore.isOnline"
    class="fixed top-0 left-0 right-0 z-50 bg-warning-500 text-white text-center py-2 text-sm font-medium"
  >
    <i class="pi pi-wifi-slash mr-2"></i>
    Mode hors ligne - Les modifications seront synchronisées au retour de la connexion
  </div>

  <!-- Layout dynamique avec la vue routée -->
  <component :is="layout">
    <RouterView />
  </component>
</template>

<style>
/* Style global pour le scroll smooth */
html {
  scroll-behavior: smooth;
}

/* Empêcher le zoom sur iOS lors du focus input */
@media screen and (max-width: 768px) {
  input, select, textarea {
    font-size: 16px !important;
  }
}
</style>