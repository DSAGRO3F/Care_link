/**
 * Service API pour la gestion des Tenants
 * Routes réservées aux SuperAdmins (équipe CareLink)
 *
 * Base URL: /api/v1/platform/tenants
 */
import api, { getErrorMessage } from './api'
import type {
  TenantCreate,
  TenantUpdate,
  TenantResponse,
  TenantWithStats,
  PaginatedTenants,
  SubscriptionCreate,
  SubscriptionResponse,
  CurrentUsageResponse,
  TenantAdminUserCreate,
  TenantAdminUserResponse,
} from '@/types/tenant'

// =============================================================================
// BASE PATH - IMPORTANT: toutes les routes Platform sont sous /platform
// =============================================================================

const BASE_PATH = '/platform/tenants'

// =============================================================================
// TENANT CRUD
// =============================================================================

/**
 * Liste paginée des tenants
 */
export async function listTenants(params?: {
  page?: number
  size?: number
  status?: string
  tenant_type?: string
  search?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}): Promise<PaginatedTenants> {
  const response = await api.get(BASE_PATH, { params })
  return response.data
}

/**
 * Récupère un tenant par son ID avec statistiques
 */
export async function getTenant(tenantId: number): Promise<TenantWithStats> {
  const response = await api.get(`${BASE_PATH}/${tenantId}`)
  return response.data
}

/**
 * Crée un nouveau tenant
 */
export async function createTenant(data: TenantCreate): Promise<TenantResponse> {
  const response = await api.post(BASE_PATH, data)
  return response.data
}

/**
 * Met à jour un tenant
 */
export async function updateTenant(
  tenantId: number,
  data: TenantUpdate
): Promise<TenantResponse> {
  const response = await api.patch(`${BASE_PATH}/${tenantId}`, data)
  return response.data
}

/**
 * Suspend un tenant
 */
export async function suspendTenant(
  tenantId: number,
  reason?: string
): Promise<TenantResponse> {
  const response = await api.post(`${BASE_PATH}/${tenantId}/suspend`, null, {
    params: { reason }
  })
  return response.data
}

/**
 * Réactive un tenant suspendu
 */
export async function reactivateTenant(tenantId: number): Promise<TenantResponse> {
  const response = await api.post(`${BASE_PATH}/${tenantId}/reactivate`)
  return response.data
}

/**
 * Active un tenant (alias pour reactivate, utilisé après création)
 */
export async function activateTenant(tenantId: number): Promise<TenantResponse> {
  return reactivateTenant(tenantId)
}

/**
 * Résilie un tenant (soft delete)
 */
export async function terminateTenant(tenantId: number): Promise<void> {
  await api.delete(`${BASE_PATH}/${tenantId}`)
}

/**
 * Récupère les statistiques d'un tenant
 */
export async function getTenantStats(tenantId: number): Promise<TenantWithStats> {
  const response = await api.get(`${BASE_PATH}/${tenantId}/stats`)
  return response.data
}

// =============================================================================
// SUBSCRIPTIONS (si implémenté dans le backend)
// =============================================================================

/**
 * Liste les abonnements d'un tenant
 */
export async function listSubscriptions(
  tenantId: number,
  status?: string
): Promise<SubscriptionResponse[]> {
  const response = await api.get(`${BASE_PATH}/${tenantId}/subscriptions`, {
    params: { status },
  })
  return response.data.items || response.data
}

/**
 * Récupère l'abonnement actif d'un tenant
 */
export async function getActiveSubscription(
  tenantId: number
): Promise<SubscriptionResponse | null> {
  try {
    const response = await api.get(`${BASE_PATH}/${tenantId}/subscriptions/active`)
    return response.data
  } catch {
    return null
  }
}

/**
 * Crée un nouvel abonnement pour un tenant
 */
export async function createSubscription(
  tenantId: number,
  data: SubscriptionCreate
): Promise<SubscriptionResponse> {
  const response = await api.post(`${BASE_PATH}/${tenantId}/subscriptions`, data)
  return response.data
}

/**
 * Active un abonnement (passage de TRIAL à ACTIVE)
 */
export async function activateSubscription(
  tenantId: number,
  subscriptionId: number
): Promise<SubscriptionResponse> {
  const response = await api.post(
    `${BASE_PATH}/${tenantId}/subscriptions/${subscriptionId}/activate`
  )
  return response.data
}

/**
 * Annule un abonnement
 */
export async function cancelSubscription(
  tenantId: number,
  subscriptionId: number,
  reason?: string
): Promise<SubscriptionResponse> {
  const response = await api.post(
    `${BASE_PATH}/${tenantId}/subscriptions/${subscriptionId}/cancel`,
    { status: 'CANCELLED', reason }
  )
  return response.data
}

// =============================================================================
// USAGE
// =============================================================================

/**
 * Récupère la consommation actuelle d'un tenant
 */
export async function getCurrentUsage(
  tenantId: number
): Promise<CurrentUsageResponse> {
  const response = await api.get(`${BASE_PATH}/${tenantId}/usage/current`)
  return response.data
}

// =============================================================================
// ADMIN USERS
// =============================================================================

/**
 * Crée un administrateur client pour un tenant
 */
export async function createAdminUser(
  tenantId: number,
  data: TenantAdminUserCreate
): Promise<TenantAdminUserResponse> {
  const response = await api.post(`${BASE_PATH}/${tenantId}/admin-user`, data)
  return response.data
}

/**
 * Liste les administrateurs d'un tenant
 */
export async function listAdminUsers(
  tenantId: number
): Promise<TenantAdminUserResponse[]> {
  const response = await api.get(`${BASE_PATH}/${tenantId}/admin-users`)
  return response.data
}

// =============================================================================
// EXPORT
// =============================================================================

export const tenantService = {
  // Tenants
  list: listTenants,
  get: getTenant,
  create: createTenant,
  update: updateTenant,
  suspend: suspendTenant,
  reactivate: reactivateTenant,
  activate: activateTenant,
  terminate: terminateTenant,
  getStats: getTenantStats,

  // Subscriptions
  listSubscriptions,
  getActiveSubscription,
  createSubscription,
  activateSubscription,
  cancelSubscription,

  // Usage
  getCurrentUsage,

  // Admin Users
  createAdminUser,
  listAdminUsers,
}

export default tenantService
export { getErrorMessage }