/**
 * Store Pinia pour la gestion offline (PWA)
 * Détecte le statut réseau, gère la queue de synchronisation
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

// =============================================================================
// TYPES
// =============================================================================

/** Élément en attente de synchronisation */
interface PendingSync {
  id: string;
  type: 'coordination' | 'evaluation' | 'vitals';
  action: 'create' | 'update' | 'delete';
  endpoint: string;
  data: unknown;
  createdAt: Date;
  retryCount: number;
}

// =============================================================================
// STORE
// =============================================================================

export const useOfflineStore = defineStore('offline', () => {
  // ===========================================================================
  // STATE
  // ===========================================================================

  /** Statut de connexion réseau */
  const isOnline = ref(navigator.onLine);

  /** Queue des modifications en attente de sync */
  const pendingSync = ref<PendingSync[]>([]);

  /** Synchronisation en cours */
  const isSyncing = ref(false);

  /** Dernière synchronisation réussie */
  const lastSyncAt = ref<Date | null>(null);

  // ===========================================================================
  // GETTERS
  // ===========================================================================

  /** Y a-t-il des modifications en attente ? */
  const hasPendingChanges = computed(() => pendingSync.value.length > 0);

  /** Nombre de modifications en attente */
  const pendingCount = computed(() => pendingSync.value.length);

  // ===========================================================================
  // ACTIONS
  // ===========================================================================

  /** Initialiser les listeners de connexion */
  function initialize() {
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Charger la queue depuis localStorage
    loadPendingFromStorage();
  }

  /** Nettoyer les listeners */
  function cleanup() {
    window.removeEventListener('online', handleOnline);
    window.removeEventListener('offline', handleOffline);
  }

  /** Handler retour en ligne */
  function handleOnline() {
    isOnline.value = true;
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.log('[Offline] Connexion rétablie');
    }

    // Lancer la synchronisation automatique
    if (hasPendingChanges.value) {
      syncAll();
    }
  }

  /** Handler passage hors ligne */
  function handleOffline() {
    isOnline.value = false;
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.log('[Offline] Connexion perdue');
    }
  }

  /** Ajouter une modification à la queue de sync */
  function queueForSync(item: Omit<PendingSync, 'id' | 'createdAt' | 'retryCount'>) {
    const syncItem: PendingSync = {
      ...item,
      id: crypto.randomUUID(),
      createdAt: new Date(),
      retryCount: 0,
    };

    pendingSync.value.push(syncItem);
    savePendingToStorage();

    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.log('[Offline] Ajouté à la queue:', syncItem.type, syncItem.action);
    }
  }

  /** Synchroniser toutes les modifications en attente */
  async function syncAll() {
    if (!isOnline.value || isSyncing.value || !hasPendingChanges.value) {
      return;
    }

    isSyncing.value = true;
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.log('[Offline] Démarrage sync:', pendingCount.value, 'éléments');
    }

    const failedItems: PendingSync[] = [];

    for (const item of pendingSync.value) {
      try {
        await syncItem(item);
      } catch (error) {
        console.error('[Offline] Échec sync:', item.id, error);

        // Réessayer jusqu'à 3 fois
        if (item.retryCount < 3) {
          item.retryCount++;
          failedItems.push(item);
        }
      }
    }

    // Garder uniquement les échecs
    pendingSync.value = failedItems;
    savePendingToStorage();

    lastSyncAt.value = new Date();
    isSyncing.value = false;

    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.log('[Offline] Sync terminée, échecs:', failedItems.length);
    }
  }

  /** Synchroniser un élément */
  async function syncItem(item: PendingSync): Promise<void> {
    const { api } = await import('@/services');

    switch (item.action) {
      case 'create':
        await api.post(item.endpoint, item.data);
        break;
      case 'update':
        await api.patch(item.endpoint, item.data);
        break;
      case 'delete':
        await api.delete(item.endpoint);
        break;
    }
  }

  /** Sauvegarder la queue dans localStorage */
  function savePendingToStorage() {
    localStorage.setItem('carelink_pending_sync', JSON.stringify(pendingSync.value));
  }

  /** Charger la queue depuis localStorage */
  function loadPendingFromStorage() {
    const stored = localStorage.getItem('carelink_pending_sync');
    if (stored) {
      try {
        pendingSync.value = JSON.parse(stored);
      } catch {
        pendingSync.value = [];
      }
    }
  }

  /** Vider la queue (après confirmation utilisateur) */
  function clearPending() {
    pendingSync.value = [];
    savePendingToStorage();
  }

  // ===========================================================================
  // RETURN
  // ===========================================================================

  return {
    // State
    isOnline,
    pendingSync,
    isSyncing,
    lastSyncAt,

    // Getters
    hasPendingChanges,
    pendingCount,

    // Actions
    initialize,
    cleanup,
    queueForSync,
    syncAll,
    clearPending,
  };
});