/**
 * Service API pour la gestion des Entités
 *
 * Endpoints backend existants :
 *   GET    /entities              → liste des entités du tenant
 *   POST   /entities              → créer une entité
 *   GET    /entities/{id}         → détail d'une entité
 *   PATCH  /entities/{id}         → modifier une entité
 *   DELETE /entities/{id}         → supprimer une entité
 *   GET    /entities/{id}/children → enfants d'une entité
 *
 * Note : pour le SuperAdmin, les endpoints sont préfixés
 *        /platform/tenants/{tenantId}/entities
 */
import api, { getErrorMessage } from './api'
import type { EntityResponse, EntityCreate, EntityUpdate } from '@/types/entity'

// =============================================================================
// TENANT CONTEXT (Admin tenant — routes /entities)
// =============================================================================

const TENANT_BASE = '/organizations/entities'

/**
 * Liste toutes les entités du tenant courant
 */
export async function listEntities(): Promise<EntityResponse[]> {
  const response = await api.get(TENANT_BASE)
  return response.data.items ?? response.data
}

/**
 * Récupère une entité par son ID
 */
export async function getEntity(entityId: number): Promise<EntityResponse> {
  const response = await api.get(`${TENANT_BASE}/${entityId}`)
  return response.data
}

/**
 * Crée une nouvelle entité
 */
export async function createEntity(data: EntityCreate): Promise<EntityResponse> {
  const response = await api.post(TENANT_BASE, data)
  return response.data
}

/**
 * Met à jour une entité
 */
export async function updateEntity(
  entityId: number,
  data: EntityUpdate
): Promise<EntityResponse> {
  const response = await api.patch(`${TENANT_BASE}/${entityId}`, data)
  return response.data
}

/**
 * Supprime une entité
 */
export async function deleteEntity(entityId: number): Promise<void> {
  await api.delete(`${TENANT_BASE}/${entityId}`)
}

/**
 * Récupère les enfants directs d'une entité
 */
export async function getEntityChildren(entityId: number): Promise<EntityResponse[]> {
  const response = await api.get(`${TENANT_BASE}/${entityId}/children`)
  return response.data.items ?? response.data
}

// =============================================================================
// PLATFORM CONTEXT (SuperAdmin — routes /platform/tenants/{id}/entities)
// =============================================================================

function platformBase(tenantId: number): string {
  return `/platform/tenants/${tenantId}/entities`
}

/**
 * Liste les entités d'un tenant (SuperAdmin)
 */
export async function listTenantEntities(tenantId: number): Promise<EntityResponse[]> {
  const response = await api.get(platformBase(tenantId))
  return response.data.items ?? response.data
}

/**
 * Récupère une entité d'un tenant (SuperAdmin)
 */
export async function getTenantEntity(
  tenantId: number,
  entityId: number
): Promise<EntityResponse> {
  const response = await api.get(`${platformBase(tenantId)}/${entityId}`)
  return response.data
}

/**
 * Crée une entité pour un tenant (SuperAdmin)
 */
export async function createTenantEntity(
  tenantId: number,
  data: EntityCreate
): Promise<EntityResponse> {
  const response = await api.post(platformBase(tenantId), data)
  return response.data
}

/**
 * Met à jour une entité d'un tenant (SuperAdmin)
 */
export async function updateTenantEntity(
  tenantId: number,
  entityId: number,
  data: EntityUpdate
): Promise<EntityResponse> {
  const response = await api.patch(`${platformBase(tenantId)}/${entityId}`, data)
  return response.data
}

/**
 * Supprime une entité d'un tenant (SuperAdmin)
 */
export async function deleteTenantEntity(
  tenantId: number,
  entityId: number
): Promise<void> {
  await api.delete(`${platformBase(tenantId)}/${entityId}`)
}

/**
 * Récupère les enfants d'une entité d'un tenant (SuperAdmin)
 */
export async function getTenantEntityChildren(
  tenantId: number,
  entityId: number
): Promise<EntityResponse[]> {
  const response = await api.get(`${platformBase(tenantId)}/${entityId}/children`)
  return response.data.items ?? response.data
}

// =============================================================================
// EXPORT
// =============================================================================

export const entityService = {
  // Tenant context
  list: listEntities,
  get: getEntity,
  create: createEntity,
  update: updateEntity,
  delete: deleteEntity,
  getChildren: getEntityChildren,

  // Platform context (SuperAdmin)
  platform: {
    list: listTenantEntities,
    get: getTenantEntity,
    create: createTenantEntity,
    update: updateTenantEntity,
    delete: deleteTenantEntity,
    getChildren: getTenantEntityChildren,
  },
}

export default entityService
export { getErrorMessage }