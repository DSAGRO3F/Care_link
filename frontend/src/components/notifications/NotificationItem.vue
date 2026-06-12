<script setup lang="ts">
  /**
   * Ligne de notification — composant partagé (S1 / B40-J4).
   *
   * Destination : src/components/notifications/NotificationItem.vue
   *
   * Réutilisé par le centre déroulant (AppHeader) ET la page « Tout voir »
   * (NotificationsPage) — 2 occurrences justifient l'extraction (DRY).
   *
   * Comportement de clic centralisé ici (source unique) :
   *   1. si non lue → store.markRead(id) ;
   *   2. si link_url présent → navigation Vue Router ;
   *   3. émet `activate` pour le ménage de contexte du parent (fermer le dropdown).
   *
   * Présentation : icône + teinte dérivées du `type`, titre, corps (line-clamp-2),
   * horodatage relatif, pastille « non lue ». Classes issues de main.css / palette
   * Tailwind du projet — aucun style scopé.
   */
  import { computed } from 'vue';
  import { useRouter } from 'vue-router';
  import { useNotificationsStore } from '@/stores';
  import { formatRelativeTime } from '@/utils/format';
  import type { NotificationResponse, NotificationType } from '@/types';

  const props = defineProps<{ notification: NotificationResponse }>();
  const emit = defineEmits<{ (e: 'activate'): void }>();

  const router = useRouter();
  const notifications = useNotificationsStore();

  // Icône PrimeIcons par type de notification.
  const ICON_BY_TYPE: Record<NotificationType, string> = {
    VALIDATION_REQUEST_RECEIVED: 'pi-inbox',
    VALIDATION_DECISION_TAKEN: 'pi-check-circle',
    VALIDATION_INFO_REQUESTED: 'pi-question-circle',
    EVALUATION_FUNDING_REJECTED: 'pi-times-circle',
  };

  // Teinte (texte + fond de la pastille d'icône) par type — paires -100/-700
  // présentes dans main.css (badges, gir-*).
  const TONE_BY_TYPE: Record<NotificationType, string> = {
    VALIDATION_REQUEST_RECEIVED: 'text-primary-700 bg-primary-100',
    VALIDATION_DECISION_TAKEN: 'text-secondary-700 bg-secondary-100',
    VALIDATION_INFO_REQUESTED: 'text-warning-700 bg-warning-100',
    EVALUATION_FUNDING_REJECTED: 'text-danger-700 bg-danger-100',
  };

  const icon = computed(() => ICON_BY_TYPE[props.notification.type] ?? 'pi-bell');
  const tone = computed(
    () => TONE_BY_TYPE[props.notification.type] ?? 'text-neutral-600 bg-neutral-100',
  );

  const timeLabel = computed(() => formatRelativeTime(props.notification.created_at));

  function onActivate(): void {
    void activate();
  }

  async function activate(): Promise<void> {
    const { id, is_read, link_url } = props.notification;
    if (!is_read) {
      try {
        await notifications.markRead(id);
      } catch {
        // Erreur déjà capturée et exposée par le store ; on ne bloque pas la navigation.
      }
    }
    if (link_url) void router.push(link_url);
    emit('activate');
  }
</script>

<template>
  <button
    :class="{ 'bg-primary-50': !notification.is_read }"
    type="button"
    class="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-neutral-50"
    @click="onActivate"
  >
    <!-- Pastille d'icône colorée par type -->
    <span
      :class="tone"
      class="mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full"
    >
      <i :class="icon" class="pi text-base"></i>
    </span>

    <!-- Contenu -->
    <span class="min-w-0 flex-1">
      <span class="flex items-center gap-2">
        <span
          :class="notification.is_read ? 'font-medium' : 'font-semibold'"
          class="truncate text-sm text-neutral-900"
        >
          {{ notification.title }}
        </span>
        <!-- Pastille « non lue » -->
        <span
          v-if="!notification.is_read"
          class="ml-auto h-2 w-2 flex-shrink-0 rounded-full bg-primary-500"
          aria-label="Non lue"
        ></span>
      </span>

      <span class="mt-0.5 block text-sm text-neutral-600 line-clamp-2">
        {{ notification.body }}
      </span>

      <span class="mt-1 block text-xs text-neutral-400">{{ timeLabel }}</span>
    </span>
  </button>
</template>
