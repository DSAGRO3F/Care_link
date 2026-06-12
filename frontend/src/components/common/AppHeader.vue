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
  import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
    useAuthStore,
    useUiStore,
    useOfflineStore,
    useNotificationsStore,
  } from '@/stores';
  import NotificationItem from '@/components/notifications/NotificationItem.vue';

  const route = useRoute();
  const router = useRouter();
  const authStore = useAuthStore();
  const uiStore = useUiStore();
  const offlineStore = useOfflineStore();
  const notifications = useNotificationsStore();

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

  // ═══ Centre de notifications ═══
  const notifMenuOpen = ref(false);

  function toggleNotifMenu() {
    notifMenuOpen.value = !notifMenuOpen.value;
    // Charge les dernières notifications à l'ouverture (le badge, lui, est polled).
    if (notifMenuOpen.value) void notifications.fetchRecent();
  }

  function closeNotifMenu() {
    notifMenuOpen.value = false;
  }

  function onMarkAllRead() {
    void notifications.markAllRead();
  }

  function goToAllNotifications() {
    closeNotifMenu();
    void router.push({ name: 'notifications' });
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
    closeNotifMenu();
    notifications.reset();
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

  // Polling du badge de notifications tant que le shell (utilisateur authentifié)
  // est monté ; coupé à l'unmount (changement de layout) et au logout (reset).
  onMounted(() => {
    notifications.startPolling();
  });

  onBeforeUnmount(() => {
    notifications.stopPolling();
  });
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

        <!-- ═══ Centre de notifications ═══ -->
        <div class="relative">
          <!-- Bouton cloche -->
          <button
            class="btn-icon relative text-neutral-600 hover:bg-neutral-100"
            aria-label="Notifications"
            @click="toggleNotifMenu"
          >
            <i class="pi pi-bell text-xl"></i>
            <!-- Badge compteur (masqué si aucune non lue) -->
            <span
              v-if="notifications.hasUnread"
              class="absolute -right-1 -top-1 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-danger-500 px-1 text-[10px] font-semibold leading-none text-white"
            >
              {{ notifications.badgeLabel }}
            </span>
          </button>

          <!-- Backdrop invisible (ferme au clic extérieur) -->
          <div v-if="notifMenuOpen" class="fixed inset-0 z-[99]" @click="closeNotifMenu"></div>

          <!-- Panneau -->
          <Transition
            enter-active-class="transition ease-out duration-150"
            enter-from-class="opacity-0 scale-95 -translate-y-1"
            enter-to-class="opacity-100 scale-100 translate-y-0"
            leave-active-class="transition ease-in duration-100"
            leave-from-class="opacity-100 scale-100"
            leave-to-class="opacity-0 scale-95"
          >
            <div
              v-if="notifMenuOpen"
              class="absolute right-0 top-full z-[100] mt-2 w-80 overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-lg shadow-neutral-900/10"
            >
              <!-- En-tête -->
              <div
                class="flex items-center justify-between border-b border-neutral-100 bg-neutral-50 px-4 py-3"
              >
                <p class="text-sm font-semibold text-neutral-800">Notifications</p>
                <button
                  v-if="notifications.hasUnread"
                  class="text-xs font-medium text-primary-600 hover:text-primary-700"
                  @click="onMarkAllRead"
                >
                  Tout marquer lu
                </button>
              </div>

              <!-- Liste -->
              <div class="scrollbar-thin max-h-96 divide-y divide-neutral-100 overflow-y-auto">
                <!-- Chargement -->
                <div v-if="notifications.recentLoading" class="space-y-3 p-4">
                  <div class="skeleton h-12 w-full"></div>
                  <div class="skeleton h-12 w-full"></div>
                  <div class="skeleton h-12 w-full"></div>
                </div>

                <!-- Vide -->
                <div v-else-if="notifications.recent.length === 0" class="empty-state">
                  <i class="pi pi-bell-slash empty-state-icon"></i>
                  <p class="empty-state-title">Aucune notification</p>
                  <p class="empty-state-description">Vous êtes à jour.</p>
                </div>

                <!-- Items -->
                <template v-else>
                  <NotificationItem
                    v-for="n in notifications.recent"
                    :key="n.id"
                    :notification="n"
                    @activate="closeNotifMenu"
                  />
                </template>
              </div>

              <!-- Pied -->
              <div class="border-t border-neutral-100">
                <button
                  class="flex w-full items-center justify-center px-4 py-2.5 text-sm font-medium text-primary-600 hover:bg-neutral-50"
                  @click="goToAllNotifications"
                >
                  Tout voir
                </button>
              </div>
            </div>
          </Transition>
        </div>

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
