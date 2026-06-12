/**
 * Store Pinia — Notifications in-app (Phase 4 bis — cloche de shell, S1 / B40-J4).
 *
 * Chemin : frontend/src/stores/notifications.store.ts
 *
 * Backe la cloche du header (badge + centre déroulant) ET la page « Tout voir ».
 * Trois états distincts, volontairement non couplés :
 *  - `unreadCount` : compteur du badge, rafraîchi par polling 30 s (D22 β) ;
 *  - `recent`      : ~8 dernières notifications, chargées à l'ouverture du dropdown ;
 *  - `items` (+ pagination) : liste paginée de la page « Tout voir ».
 * Ouvrir le dropdown ne doit pas écraser la pagination de la page → deux listes.
 *
 * Le polling n'interroge que `/unread-count` (léger). Ses erreurs sont
 * silencieuses (un hoquet réseau ne doit pas casser l'UI ni vider le badge).
 * Le handle d'intervalle vit dans la closure du store (singleton), non réactif.
 *
 * Convention Pinia maison : defineStore + ref/computed (cf. validation-thread.store).
 * Convention #78 : type `NotificationResponse` miroir depuis `@/types`.
 *
 * 🆕 S1 / B40-J4 — création du store.
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { notificationService } from '@/services';
import type { NotificationResponse } from '@/types';

const POLL_INTERVAL_MS = 30_000; // 30 s (D22 β)
const RECENT_LIMIT = 8; // nombre d'items du dropdown

export const useNotificationsStore = defineStore('notifications', () => {
  // ===========================================================================
  // STATE — Badge
  // ===========================================================================

  /** Nombre de notifications non lues (badge de la cloche). */
  const unreadCount = ref(0);

  // ===========================================================================
  // STATE — Dropdown (liste récente)
  // ===========================================================================

  /** Dernières notifications affichées dans le centre déroulant. */
  const recent = ref<NotificationResponse[]>([]);
  const recentLoading = ref(false);

  // ===========================================================================
  // STATE — Page « Tout voir » (liste paginée)
  // ===========================================================================

  const items = ref<NotificationResponse[]>([]);
  const total = ref(0);
  const page = ref(1);
  const size = ref(20);
  const pages = ref(0);
  const unreadOnly = ref(false);
  const loading = ref(false);

  const error = ref<string | null>(null);

  /** Handle du polling — closure du store (singleton), volontairement non réactif. */
  let pollHandle: ReturnType<typeof setInterval> | null = null;

  // ===========================================================================
  // COMPUTED
  // ===========================================================================

  /** Y a-t-il au moins une non lue ? (pilote l'affichage du badge). */
  const hasUnread = computed(() => unreadCount.value > 0);

  /** Libellé du badge, plafonné à « 99+ ». */
  const badgeLabel = computed(() => (unreadCount.value > 99 ? '99+' : String(unreadCount.value)));

  // ===========================================================================
  // HELPERS PRIVÉS (non exposés)
  // ===========================================================================

  /** Remplace en place une notification (par id) dans les deux listes locales. */
  function replaceLocal(updated: NotificationResponse): void {
    for (const list of [recent, items]) {
      const idx = list.value.findIndex((n) => n.id === updated.id);
      if (idx !== -1) list.value.splice(idx, 1, updated);
    }
  }

  // ===========================================================================
  // ACTIONS — Badge & polling
  // ===========================================================================

  /** Rafraîchit le compteur du badge. Silencieux : appelé en boucle par le polling. */
  async function fetchUnreadCount(): Promise<void> {
    try {
      const res = await notificationService.unreadCount();
      unreadCount.value = res.unread_count;
    } catch (err: unknown) {
      if (import.meta.env.DEV) console.error('[notifications] unreadCount', err);
    }
  }

  /** Démarre le polling (tir immédiat + intervalle 30 s). Idempotent. */
  function startPolling(): void {
    if (pollHandle !== null) return;
    void fetchUnreadCount();
    pollHandle = setInterval(() => void fetchUnreadCount(), POLL_INTERVAL_MS);
  }

  /** Arrête le polling (à l'unmount du shell / au logout). */
  function stopPolling(): void {
    if (pollHandle !== null) {
      clearInterval(pollHandle);
      pollHandle = null;
    }
  }

  // ===========================================================================
  // ACTIONS — Chargement des listes
  // ===========================================================================

  /** Charge les dernières notifications pour le dropdown (à l'ouverture). */
  async function fetchRecent(): Promise<void> {
    recentLoading.value = true;
    error.value = null;
    try {
      const data = await notificationService.list(1, RECENT_LIMIT, false);
      recent.value = data.items;
    } catch (err: unknown) {
      error.value =
        err instanceof Error ? err.message : 'Erreur lors du chargement des notifications';
    } finally {
      recentLoading.value = false;
    }
  }

  /** Charge une page de la liste « Tout voir » (filtre `onlyUnread` optionnel). */
  async function fetchList(targetPage = 1, targetSize = 20, onlyUnread = false): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      const data = await notificationService.list(targetPage, targetSize, onlyUnread);
      items.value = data.items;
      total.value = data.total;
      page.value = data.page;
      size.value = data.size;
      pages.value = data.pages;
      unreadOnly.value = onlyUnread;
    } catch (err: unknown) {
      error.value =
        err instanceof Error ? err.message : 'Erreur lors du chargement des notifications';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  // ===========================================================================
  // ACTIONS — Mutations (lecture)
  // ===========================================================================

  /**
   * Marque une notification comme lue. Met à jour les listes locales depuis la
   * réponse, puis resynchronise le badge depuis le serveur (léger et fiable).
   */
  async function markRead(id: number): Promise<void> {
    error.value = null;
    try {
      const updated = await notificationService.markRead(id);
      replaceLocal(updated);
      await fetchUnreadCount();
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors du marquage';
      throw err;
    }
  }

  /** Marque toutes les non lues comme lues. Met à jour l'état local + badge à 0. */
  async function markAllRead(): Promise<number> {
    error.value = null;
    try {
      const { marked_count } = await notificationService.markAllRead();
      const stamp = new Date().toISOString();
      for (const list of [recent, items]) {
        for (const n of list.value) {
          if (!n.is_read) {
            n.is_read = true;
            n.read_at = stamp;
          }
        }
      }
      unreadCount.value = 0;
      return marked_count;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors du marquage';
      throw err;
    }
  }

  // ===========================================================================
  // RESET
  // ===========================================================================

  /** Réinitialise le store et coupe le polling (logout). */
  function reset(): void {
    stopPolling();
    unreadCount.value = 0;
    recent.value = [];
    recentLoading.value = false;
    items.value = [];
    total.value = 0;
    page.value = 1;
    size.value = 20;
    pages.value = 0;
    unreadOnly.value = false;
    loading.value = false;
    error.value = null;
  }

  // ===========================================================================
  // RETURN
  // ===========================================================================

  return {
    // State — badge
    unreadCount,
    // State — dropdown
    recent,
    recentLoading,
    // State — page
    items,
    total,
    page,
    size,
    pages,
    unreadOnly,
    loading,
    error,

    // Computed
    hasUnread,
    badgeLabel,

    // Actions — badge & polling
    fetchUnreadCount,
    startPolling,
    stopPolling,

    // Actions — listes
    fetchRecent,
    fetchList,

    // Actions — mutations
    markRead,
    markAllRead,

    // Reset
    reset,
  };
});
