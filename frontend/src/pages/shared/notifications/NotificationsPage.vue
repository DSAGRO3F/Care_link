<script setup lang="ts">
  /**
   * Page « Toutes les notifications » (S1 / B40-J4).
   *
   * Destination : src/pages/shared/notifications/NotificationsPage.vue
   *
   * Liste paginée des notifications de l'utilisateur (RLS atypique #130 par
   * destinataire — pas de permission requise). Filtre « non lues uniquement »,
   * « tout marquer lu », pagination simple. Réutilise `NotificationItem` (mêmes
   * lignes que le centre déroulant du header).
   *
   * Route globale `/notifications` (name `notifications`) — atteinte depuis le
   * lien « Tout voir » de la cloche.
   */
  import { onMounted, ref } from 'vue';
  import NotificationItem from '@/components/notifications/NotificationItem.vue';
  import { useNotificationsStore } from '@/stores';

  const notifications = useNotificationsStore();

  const PAGE_SIZE = 20;
  const unreadOnly = ref(false);

  onMounted(() => {
    void load(1);
  });

  async function load(page: number): Promise<void> {
    await notifications.fetchList(page, PAGE_SIZE, unreadOnly.value);
  }

  function onToggleUnread(): void {
    void load(1);
  }

  function onPrev(): void {
    if (notifications.page > 1) void load(notifications.page - 1);
  }

  function onNext(): void {
    if (notifications.page < notifications.pages) void load(notifications.page + 1);
  }

  function onMarkAllRead(): void {
    void markAllReadAndMaybeReload();
  }

  /** Marque tout lu, puis recharge si le filtre « non lues » masque désormais la page. */
  async function markAllReadAndMaybeReload(): Promise<void> {
    await notifications.markAllRead();
    if (unreadOnly.value) await load(1);
  }
</script>

<template>
  <div class="p-4 lg:p-6">
    <!-- En-tête -->
    <div class="page-header">
      <h1 class="page-title">Notifications</h1>

      <div class="flex items-center gap-4">
        <label class="flex items-center gap-2 text-sm text-neutral-600">
          <input
            v-model="unreadOnly"
            type="checkbox"
            class="h-4 w-4 accent-primary-600"
            @change="onToggleUnread"
          />
          Non lues uniquement
        </label>

        <button
          :disabled="notifications.loading || !notifications.hasUnread"
          class="btn-secondary text-sm"
          @click="onMarkAllRead"
        >
          Tout marquer lu
        </button>
      </div>
    </div>

    <!-- Carte liste -->
    <div class="overflow-hidden rounded-lg border border-neutral-200 bg-white">
      <!-- Erreur -->
      <div v-if="notifications.error" class="p-4 text-sm text-danger-600">
        {{ notifications.error }}
      </div>

      <!-- Chargement -->
      <div v-else-if="notifications.loading" class="space-y-3 p-4">
        <div v-for="i in 6" :key="i" class="skeleton h-14 w-full"></div>
      </div>

      <!-- Vide -->
      <div v-else-if="notifications.items.length === 0" class="empty-state">
        <i class="pi pi-bell-slash empty-state-icon"></i>
        <p class="empty-state-title">Aucune notification</p>
        <p class="empty-state-description">
          {{ unreadOnly ? 'Aucune notification non lue.' : 'Vous êtes à jour.' }}
        </p>
      </div>

      <!-- Liste -->
      <div v-else class="divide-y divide-neutral-100">
        <NotificationItem
          v-for="n in notifications.items"
          :key="n.id"
          :notification="n"
        />
      </div>
    </div>

    <!-- Pagination -->
    <div
      v-if="notifications.pages > 1"
      class="mt-4 flex items-center justify-between text-sm text-neutral-600"
    >
      <span>{{ notifications.total }} notification(s)</span>

      <div class="flex items-center gap-3">
        <button
          :disabled="notifications.page <= 1 || notifications.loading"
          class="btn-secondary text-sm"
          @click="onPrev"
        >
          Précédent
        </button>
        <span>Page {{ notifications.page }} sur {{ notifications.pages }}</span>
        <button
          :disabled="notifications.page >= notifications.pages || notifications.loading"
          class="btn-secondary text-sm"
          @click="onNext"
        >
          Suivant
        </button>
      </div>
    </div>
  </div>
</template>
