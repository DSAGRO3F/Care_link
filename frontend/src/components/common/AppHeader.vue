<script setup lang="ts">
  /**
   * Header de l'application
   * Titre de page, recherche, notifications, menu utilisateur
   *
   * 🆕 v4.11 : Menu utilisateur custom (remplace Menu PrimeVue popup)
   *   - Dropdown soigné avec backdrop transparent pour fermeture au clic extérieur
   *   - En-tête avec avatar, nom complet et email
   *   - Items avec icônes colorées et hover élégant
   *   - Séparateur visuel avant Déconnexion
   *
   * Destination : src/components/common/AppHeader.vue
   */
  import { ref, computed } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { useAuthStore, useUiStore, useOfflineStore } from '@/stores';

  const route = useRoute();
  const router = useRouter();
  const authStore = useAuthStore();
  const uiStore = useUiStore();
  const offlineStore = useOfflineStore();

  // Titre de la page depuis les meta de la route
  const pageTitle = computed(() => route.meta.title || 'CareLink');

  // Menu utilisateur — état ouvert/fermé
  const userMenuOpen = ref(false);

  function toggleUserMenu() {
    userMenuOpen.value = !userMenuOpen.value;
  }

  function closeUserMenu() {
    userMenuOpen.value = false;
  }

  // TODO — Fonctions prévues pour le menu utilisateur (profil, paramètres)
  // function _goToProfile() {
  //   closeUserMenu();
  //   router.push('/profile');
  // }
  // function _goToSettings() {
  //   closeUserMenu();
  //   router.push('/settings');
  // }

  function handleLogout() {
    closeUserMenu();
    authStore.logout();
    router.push('/login');
  }

  // Initiales de l'utilisateur pour l'avatar
  const userInitials = computed(() => {
    if (!authStore.user) return '?';
    const first = authStore.user.first_name?.[0] || '';
    const last = authStore.user.last_name?.[0] || '';
    return (first + last).toUpperCase() || '?';
  });

  const userFullName = computed(() => {
    if (!authStore.user) return '';
    return `${authStore.user.first_name || ''} ${authStore.user.last_name || ''}`.trim();
  });

  const userEmail = computed(() => authStore.user?.email || '');
</script>

<template>
  <header class="sticky top-0 z-40 bg-white border-b border-neutral-200">
    <div class="flex items-center justify-between h-16 px-4 lg:px-6">
      <!-- Gauche: Menu mobile + Titre -->
      <div class="flex items-center gap-4">
        <!-- Bouton menu mobile -->
        <button
          v-if="uiStore.isMobile"
          class="btn-icon text-neutral-600 hover:bg-neutral-100"
          @click="uiStore.toggleMobileMenu"
        >
          <i class="pi pi-bars text-xl"></i>
        </button>

        <!-- Titre de la page -->
        <h1 class="text-lg font-semibold text-neutral-900">
          {{ pageTitle }}
        </h1>
      </div>

      <!-- Droite: Actions -->
      <div class="flex items-center gap-2">
        <!-- Indicateur sync offline -->
        <div
          v-if="offlineStore.hasPendingChanges"
          class="flex items-center gap-1 text-sm text-warning-600 bg-warning-50 px-2 py-1 rounded"
        >
          <i :class="{ 'animate-spin': offlineStore.isSyncing }" class="pi pi-sync"></i>
          <span class="hidden sm:inline">{{ offlineStore.pendingCount }} en attente</span>
        </div>

        <!-- Notifications -->
        <button class="btn-icon text-neutral-600 hover:bg-neutral-100 relative">
          <i class="pi pi-bell text-xl"></i>
          <!-- Badge notifications -->
          <span class="absolute top-1 right-1 w-2 h-2 bg-danger-500 rounded-full"></span>
        </button>

        <!-- ═══ Menu utilisateur custom ═══ -->
        <div class="relative">
          <!-- Bouton trigger -->
          <button
            :class="userMenuOpen ? 'bg-neutral-100' : 'hover:bg-neutral-100'"
            class="flex items-center gap-2 p-1.5 rounded-lg transition-colors"
            @click="toggleUserMenu"
          >
            <!-- Avatar -->
            <div
              class="w-8 h-8 rounded-full bg-primary-600 text-white flex items-center justify-center text-sm font-medium"
            >
              {{ userInitials }}
            </div>
            <!-- Nom (desktop) -->
            <span class="hidden lg:block text-sm font-medium text-neutral-700">
              {{ authStore.user?.first_name }}
            </span>
            <i
              :class="userMenuOpen ? 'pi-chevron-up' : 'pi-chevron-down'"
              class="pi text-xs text-neutral-400 hidden lg:block transition-transform duration-200"
            ></i>
          </button>

          <!-- Backdrop invisible (ferme le menu au clic extérieur) -->
          <div v-if="userMenuOpen" class="fixed inset-0 z-[99]" @click="closeUserMenu"></div>

          <!-- Dropdown -->
          <Transition
            enter-active-class="transition ease-out duration-150"
            enter-from-class="opacity-0 scale-95 -translate-y-1"
            enter-to-class="opacity-100 scale-100 translate-y-0"
            leave-active-class="transition ease-in duration-100"
            leave-from-class="opacity-100 scale-100"
            leave-to-class="opacity-0 scale-95"
          >
            <div
              v-if="userMenuOpen"
              class="absolute right-0 top-full mt-2 w-64 bg-white rounded-xl border border-neutral-200 shadow-lg shadow-neutral-900/10 z-[100] overflow-hidden"
            >
              <!-- En-tête utilisateur -->
              <div class="px-4 py-3 bg-neutral-50 border-b border-neutral-100">
                <div class="flex items-center gap-3">
                  <div
                    class="w-10 h-10 rounded-full bg-primary-600 text-white flex items-center justify-center text-sm font-semibold flex-shrink-0"
                  >
                    {{ userInitials }}
                  </div>
                  <div class="min-w-0">
                    <p class="text-sm font-semibold text-neutral-800 truncate">
                      {{ userFullName }}
                    </p>
                    <p class="text-xs text-neutral-500 truncate">{{ userEmail }}</p>
                  </div>
                </div>
              </div>

              <!-- Items de navigation -->

              <!-- TODO: Réactiver Mon profil + Paramètres quand /profile et /settings existent -->
              <!-- Séparateur + Déconnexion -->
              <div class="border-t border-neutral-100 py-1.5">
                <button
                  class="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                  @click="handleLogout"
                >
                  <i class="pi pi-sign-out text-red-400"></i>
                  Déconnexion
                </button>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </header>
</template>