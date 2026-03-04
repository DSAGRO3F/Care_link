/**
 * Service API pour la gestion des Utilisateurs (Professionnels de santé)
 *
 * Contexte : Admin Client — le tenant est implicite via le JWT.
 *
 * Endpoints backend (specs v4.6) :
 *
 *   CRUD utilisateur :
 *     GET    /users                           → liste paginée
 *     POST   /users                           → créer un utilisateur
 *     GET    /users/{id}                      → détail
 *     PATCH  /users/{id}                      → modifier
 *     DELETE /users/{id}                      → désactiver (soft delete)
 *
 *   Rôles utilisateur :
 *     GET    /users/{id}/roles                → rôles de l'utilisateur
 *     POST   /users/{id}/roles                → assigner un rôle
 *     DELETE /users/{id}/roles/{roleId}       → retirer un rôle
 *
 *   Rôles tenant (standalone) :
 *     GET    /roles                           → 🆕 R1 — tous les rôles du tenant
 *
 *   Rattachement entités (multi-rattachement) :
 *     GET    /users/{id}/entities             → entités rattachées
 *     POST   /users/{id}/entities             → rattacher à une entité
 *     DELETE /users/{id}/entities/{eid}       → détacher d'une entité
 *
 *   Disponibilités :
 *     GET    /users/{id}/availabilities       → plages horaires
 *     POST   /users/{id}/availabilities       → ajouter une plage
 *     PATCH  /users/{id}/availabilities/{aid} → modifier
 *     DELETE /users/{id}/availabilities/{aid} → supprimer
 *
 * Destination : src/services/user.service.ts
 */
import api, { getErrorMessage } from './api'
import type {
  UserResponse,
  UserList,
  UserCreate,
  UserUpdate,
  UserWithEntities,
  UserQueryParams,
  UserEntityResponse,
  UserEntityCreate,
  UserAvailabilityResponse,
  UserAvailabilityCreate,
  UserAvailabilityList,
  RoleResponse,
} from '@/types/user'

const BASE = '/users'

// =============================================================================
// CRUD UTILISATEUR
// =============================================================================

/**
 * Liste paginée des utilisateurs du tenant courant
 */
export async function listUsers(params?: UserQueryParams): Promise<UserList> {
  const response = await api.get(BASE, { params })
  return response.data
}

/**
 * Récupère un utilisateur par son ID
 */
export async function getUser(userId: number): Promise<UserResponse> {
  const response = await api.get(`${BASE}/${userId}`)
  return response.data
}

/**
 * Récupère un utilisateur avec ses entités rattachées
 */
export async function getUserWithEntities(userId: number): Promise<UserWithEntities> {
  const response = await api.get(`${BASE}/${userId}`, {
    params: { include_entities: true },
  })
  return response.data
}

/**
 * Crée un nouvel utilisateur
 */
export async function createUser(data: UserCreate): Promise<UserResponse> {
  const response = await api.post(BASE, data)
  return response.data
}

/**
 * Met à jour un utilisateur
 */
export async function updateUser(
  userId: number,
  data: UserUpdate
): Promise<UserResponse> {
  const response = await api.patch(`${BASE}/${userId}`, data)
  return response.data
}

/**
 * Désactive un utilisateur (soft delete)
 */
export async function deleteUser(userId: number): Promise<void> {
  await api.delete(`${BASE}/${userId}`)
}

// =============================================================================
// RÔLES UTILISATEUR (par user)
// =============================================================================

/**
 * Récupère les rôles d'un utilisateur
 */
export async function getUserRoles(userId: number): Promise<RoleResponse[]> {
  const response = await api.get(`${BASE}/${userId}/roles`)
  return response.data.items ?? response.data
}

/**
 * Assigne un rôle à un utilisateur
 */
export async function addUserRole(
  userId: number,
  roleId: number
): Promise<void> {
  await api.post(`${BASE}/${userId}/roles`, { role_id: roleId })
}

/**
 * Retire un rôle d'un utilisateur
 */
export async function removeUserRole(
  userId: number,
  roleId: number
): Promise<void> {
  await api.delete(`${BASE}/${userId}/roles/${roleId}`)
}

// =============================================================================
// RÔLES TENANT (standalone — GET /roles)
// =============================================================================

/**
 * 🆕 R1 — Liste tous les rôles disponibles pour le tenant courant
 *
 * Inclut les rôles système (is_system_role=true, tenant_id=NULL)
 * et les éventuels rôles custom du tenant (Phase 2 R6).
 * Chaque rôle contient son tableau permissions: string[].
 */
export async function listRoles(): Promise<RoleResponse[]> {
  const response = await api.get('/roles')
  return response.data.items ?? response.data
}

// =============================================================================
// RATTACHEMENT ENTITÉS (multi-rattachement)
// =============================================================================

/**
 * Récupère les entités rattachées à un utilisateur
 */
export async function getUserEntities(
  userId: number
): Promise<UserEntityResponse[]> {
  const response = await api.get(`${BASE}/${userId}/entities`)
  return response.data.items ?? response.data
}

/**
 * Rattache un utilisateur à une entité
 */
export async function attachUserEntity(
  userId: number,
  data: UserEntityCreate
): Promise<UserEntityResponse> {
  const response = await api.post(`${BASE}/${userId}/entities`, data)
  return response.data
}

/**
 * Détache un utilisateur d'une entité
 */
export async function detachUserEntity(
  userId: number,
  entityAssociationId: number
): Promise<void> {
  await api.delete(`${BASE}/${userId}/entities/${entityAssociationId}`)
}

// =============================================================================
// DISPONIBILITÉS
// =============================================================================

/**
 * Récupère les disponibilités d'un utilisateur
 */
export async function getUserAvailabilities(
  userId: number
): Promise<UserAvailabilityList> {
  const response = await api.get(`${BASE}/${userId}/availabilities`)
  return response.data
}

/**
 * Ajoute une disponibilité
 */
export async function createUserAvailability(
  userId: number,
  data: UserAvailabilityCreate
): Promise<UserAvailabilityResponse> {
  const response = await api.post(`${BASE}/${userId}/availabilities`, data)
  return response.data
}

/**
 * Modifie une disponibilité
 */
export async function updateUserAvailability(
  userId: number,
  availabilityId: number,
  data: Partial<UserAvailabilityCreate>
): Promise<UserAvailabilityResponse> {
  const response = await api.patch(
    `${BASE}/${userId}/availabilities/${availabilityId}`,
    data
  )
  return response.data
}

/**
 * Supprime une disponibilité
 */
export async function deleteUserAvailability(
  userId: number,
  availabilityId: number
): Promise<void> {
  await api.delete(`${BASE}/${userId}/availabilities/${availabilityId}`)
}

// =============================================================================
// EXPORT
// =============================================================================

export const userService = {
  // CRUD
  list: listUsers,
  get: getUser,
  getWithEntities: getUserWithEntities,
  create: createUser,
  update: updateUser,
  delete: deleteUser,

  // Rôles par utilisateur
  roles: {
    list: getUserRoles,
    add: addUserRole,
    remove: removeUserRole,
  },

  // 🆕 R1 — Rôles du tenant (standalone)
  allRoles: {
    list: listRoles,
  },

  // Rattachement entités
  entities: {
    list: getUserEntities,
    attach: attachUserEntity,
    detach: detachUserEntity,
  },

  // Disponibilités
  availabilities: {
    list: getUserAvailabilities,
    create: createUserAvailability,
    update: updateUserAvailability,
    delete: deleteUserAvailability,
  },
}

export default userService
export { getErrorMessage }