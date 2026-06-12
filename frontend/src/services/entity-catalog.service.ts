/**
 * Service API — Module Catalogue Admin Tenant (Phase 3A).
 *
 * Deux circuits d'appels :
 * 1. Entity services CRUD : /entities/{entityId}/services (auth métier, RLS actif)
 * 2. Catalogue national lecture : /service-templates (auth métier, table partagée)
 *
 * ⚠️ Convention #70 : PAS de préfixe /platform/ — ce service est utilisé
 * par l'admin tenant (token métier), pas par le super-admin.
 * Le BASE URL dans api.ts est déjà /api/v1 — ne pas le doubler.
 *
 * Convention #72 : size ≤ 100 (PaginationParams plafond backend).
 */

import api from './api';
import type {
  EntityServiceCreate,
  EntityServiceResponse,
  EntityServiceUpdate,
  ServiceTemplateList,
  ServiceTemplateSummary,
} from '@/types';

// =============================================================================
// CATALOGUE NATIONAL — Lecture seule (circuit métier)
// =============================================================================

/**
 * Charge tous les service templates du catalogue national.
 * Utilise les endpoints /service-templates (pas /platform/).
 * Convention #72 : size=100 max. Si >100 templates, paginer.
 */
async function getNationalCatalog(page = 1, size = 100): Promise<ServiceTemplateList> {
  const { data } = await api.get<ServiceTemplateList>('/service-templates', {
    params: { page, size },
  });
  return data;
}

/**
 * Charge tous les templates en une seule passe (dépagination automatique).
 * Utile pour le merge national ↔ entity dans le store.
 */
async function getAllNationalTemplates(): Promise<ServiceTemplateSummary[]> {
  const firstPage = await getNationalCatalog(1, 100);
  const allItems = [...firstPage.items];

  // Si plus de 100 templates, paginer
  if (firstPage.pages > 1) {
    const remaining = Array.from({ length: firstPage.pages - 1 }, (_, i) => i + 2);
    const pages = await Promise.all(remaining.map((p) => getNationalCatalog(p, 100)));
    for (const page of pages) {
      allItems.push(...page.items);
    }
  }

  return allItems;
}

// =============================================================================
// ENTITY SERVICES — CRUD (circuit métier, RLS actif)
// =============================================================================

/**
 * Liste les services activés pour une entité.
 * GET /entities/{entityId}/services
 */
async function getEntityServices(entityId: number): Promise<EntityServiceResponse[]> {
  const { data } = await api.get(`/entities/${entityId}/services`);
  return data.items ?? data;
}

/**
 * Détail d'un service entité.
 * GET /entities/{entityId}/services/{serviceId}
 */
async function getEntityService(
  entityId: number,
  serviceId: number,
): Promise<EntityServiceResponse> {
  const { data } = await api.get<EntityServiceResponse>(
    `/entities/${entityId}/services/${serviceId}`,
  );
  return data;
}

/**
 * Active un service du catalogue national pour une entité.
 * POST /entities/{entityId}/services
 */
async function activateService(
  entityId: number,
  payload: EntityServiceCreate,
): Promise<EntityServiceResponse> {
  const { data } = await api.post<EntityServiceResponse>(`/entities/${entityId}/services`, payload);
  return data;
}

/**
 * Personnalise un service entité (tarif, durée, fréquence, notes).
 * PATCH /entities/{entityId}/services/{serviceId}
 */
async function updateService(
  entityId: number,
  serviceId: number,
  payload: EntityServiceUpdate,
): Promise<EntityServiceResponse> {
  const { data } = await api.patch<EntityServiceResponse>(
    `/entities/${entityId}/services/${serviceId}`,
    payload,
  );
  return data;
}

/**
 * Désactive un service pour une entité.
 * DELETE /entities/{entityId}/services/{serviceId}
 */
async function deactivateService(entityId: number, serviceId: number): Promise<void> {
  await api.delete(`/entities/${entityId}/services/${serviceId}`);
}

// =============================================================================
// EXPORT
// =============================================================================

export const entityCatalogService = {
  // Catalogue national (lecture)
  getNationalCatalog,
  getAllNationalTemplates,
  // Entity services (CRUD)
  getEntityServices,
  getEntityService,
  activateService,
  updateService,
  deactivateService,
};
