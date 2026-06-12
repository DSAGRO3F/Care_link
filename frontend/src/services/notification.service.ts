/**
 * Service API — Module Notifications (Phase 4 bis — cloche in-app, S1 / B40-J4).
 *
 * Chemin : frontend/src/services/notification.service.ts
 *
 * Rôle : miroir des 4 endpoints du `notifications_router`
 *   (app/api/v1/validation/notifications_routes.py) :
 * - list (1)        : GET   /notifications              (paginé + filtre unread_only)
 * - unreadCount (1) : GET   /notifications/unread-count  (badge — polling 30 s, D22 β)
 * - markRead (1)    : PATCH /notifications/{id}/mark-read   ⚠ verbe PATCH (PAS POST)
 * - markAllRead (1) : POST  /notifications/mark-all-read    → { marked_count }
 *
 * Pas de gating par permission côté backend : la RLS atypique #130 filtre par
 * `recipient_user_id` (chaque utilisateur ne voit que ses propres notifications).
 * La cloche est donc visible pour tout utilisateur authentifié (composant de shell).
 *
 * Convention #74 : la réponse paginée est déjà l'enveloppe { items, total, … },
 *   on retourne `data` directement (pas de `data.items ?? data`).
 * Convention #76 : namespace plat (list, unreadCount, markRead, markAllRead),
 *   pas de sous-namespace.
 * Convention #78 : types miroir stricts depuis `@/types` (source de vérité =
 *   schémas Pydantic `validation/schemas.py`).
 *
 * 🆕 S1 / B40-J4 — création du service.
 */

import api from './api';
import type {
  NotificationList,
  NotificationResponse,
  NotificationUnreadCount,
} from '@/types';

const NOTIF_BASE = '/notifications';

// =============================================================================
// LECTURE
// =============================================================================

/**
 * Liste paginée des notifications de l'utilisateur courant (ordre antéchrono-
 * logique, filtrage RLS atypique #130 par destinataire — indépendant du tenant).
 * GET /notifications
 *
 * @param unreadOnly — si true, ne retourne que les non lues (filtre de la page « Tout voir »).
 */
async function list(page = 1, size = 20, unreadOnly = false): Promise<NotificationList> {
  const params: Record<string, string | number | boolean> = {
    page,
    size,
    unread_only: unreadOnly,
  };
  const { data } = await api.get<NotificationList>(NOTIF_BASE, { params });
  return data;
}

/**
 * Compteur de notifications non lues (badge de la cloche — interrogé toutes les
 * 30 s par le store, D22 β).
 * GET /notifications/unread-count
 */
async function unreadCount(): Promise<NotificationUnreadCount> {
  const { data } = await api.get<NotificationUnreadCount>(`${NOTIF_BASE}/unread-count`);
  return data;
}

// =============================================================================
// MUTATIONS
// =============================================================================

/**
 * Marque une notification comme lue (idempotent). Le backend vérifie en SQL que
 * la notification appartient bien au destinataire courant (RLS #130).
 * ⚠ Verbe PATCH côté backend (et non POST).
 * PATCH /notifications/{notification_id}/mark-read
 */
async function markRead(notificationId: number): Promise<NotificationResponse> {
  const { data } = await api.patch<NotificationResponse>(
    `${NOTIF_BASE}/${notificationId}/mark-read`,
  );
  return data;
}

/**
 * Marque toutes les notifications non lues du destinataire comme lues.
 * Retour ad-hoc (pas de schéma Pydantic dédié côté backend) : { marked_count }.
 * POST /notifications/mark-all-read
 */
async function markAllRead(): Promise<{ marked_count: number }> {
  const { data } = await api.post<{ marked_count: number }>(`${NOTIF_BASE}/mark-all-read`);
  return data;
}

// =============================================================================
// EXPORT — Namespace plat (convention #76)
// =============================================================================

export const notificationService = {
  // Lecture
  list,
  unreadCount,
  // Mutations
  markRead,
  markAllRead,
};
