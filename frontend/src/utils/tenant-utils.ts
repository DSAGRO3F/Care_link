/**
 * Utilitaires partagés pour les Tenants
 *
 * Centralise les fonctions réutilisées dans TenantsPage, TenantDetailPage, etc.
 * Évite la duplication de logique entre composants.
 *
 * Destination : src/utils/tenant-utils.ts
 */
import { TenantStatus } from '@/types';

/**
 * Retourne la severity PrimeVue (Tag, Badge) selon le statut du tenant
 */
export function getStatusSeverity(status: TenantStatus): string {
  const map: Record<TenantStatus, string> = {
    [TenantStatus.PENDING]: 'warning',
    [TenantStatus.ACTIVE]: 'success',
    [TenantStatus.SUSPENDED]: 'danger',
    [TenantStatus.TERMINATED]: 'secondary',
  };
  return map[status] || 'info';
}

/**
 * Formate une date ISO en format lisible (ex: "03 févr. 2026")
 */
export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}
