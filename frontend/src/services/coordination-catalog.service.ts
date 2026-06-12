/**
 * Service API — Module Catalogue Coordination (Phase 3B).
 *
 * Chemin : frontend/src/services/coordination-catalog.service.ts
 *
 * Rôle : appel unique GET /catalog/consolidated — vue consolidée
 * cross-entités pour le coordinateur. Lecture seule, pas de CRUD.
 *
 * ⚠️ Convention #70 : PAS de préfixe /platform/ — ce service est utilisé
 * par le coordinateur (token métier), pas par le super-admin.
 */

import api from './api';
import type { ConsolidatedCatalogResponse } from '@/types';

/**
 * Charge le catalogue consolidé de toutes les entités du tenant.
 * GET /catalog/consolidated
 *
 * Retourne un objet unique (pas paginé) — pas de pattern data.items ?? data.
 */
async function getConsolidated(): Promise<ConsolidatedCatalogResponse> {
  const { data } = await api.get<ConsolidatedCatalogResponse>('/catalog/consolidated');
  return data;
}

export const coordinationCatalogService = {
  getConsolidated,
};
