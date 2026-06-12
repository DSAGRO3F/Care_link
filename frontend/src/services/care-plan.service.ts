/**
 * Service API — Module Plan d'aide (Phase 4).
 *
 * Chemin : frontend/src/services/care-plan.service.ts
 *
 * Rôle : 21 appels API correspondant aux 21 endpoints backend.
 * - Care Plans : CRUD (5) + workflow state machine (7 — incl. revise B28b)
 * - Care Plan Services : CRUD (5) + affectation (4)
 *
 * Convention #76 : namespace plat (list, get, create…), pas de sous-namespace.
 * Convention #70 : PAS de préfixe /platform/ — service coordinateur.
 * Convention #74 : data.items ?? data pour endpoints paginés.
 *
 * 🆕 v01/05 — Ajout de revise() (B28b Jalon 4 / F2).
 */

import api from './api';
import type {
  CarePlanCreate,
  CarePlanFilters,
  CarePlanList,
  CarePlanReplaceServicesRequest,
  CarePlanReviseRequest,
  CarePlanServiceCreate,
  CarePlanServiceList,
  CarePlanServiceResponse,
  CarePlanServiceUpdate,
  CarePlanStatusChange,
  CarePlanUpdate,
  CarePlanWithServices,
  ServiceAssignment,
} from '@/types';

const BASE = '/care-plans';

// =============================================================================
// CARE PLANS — CRUD
// =============================================================================

/**
 * Liste les plans d'aide avec pagination et filtres.
 * GET /care-plans
 */
async function list(page = 1, size = 20, filters?: CarePlanFilters): Promise<CarePlanList> {
  const params: Record<string, string | number | boolean> = { page, size };

  if (filters) {
    if (filters.patient_id !== undefined && filters.patient_id !== null)
      params.patient_id = filters.patient_id;
    if (filters.entity_id !== undefined && filters.entity_id !== null)
      params.entity_id = filters.entity_id;
    if (filters.status) params.status = filters.status;
    if (filters.start_date_from) params.start_date_from = filters.start_date_from;
    if (filters.start_date_to) params.start_date_to = filters.start_date_to;
    if (filters.is_fully_assigned !== undefined && filters.is_fully_assigned !== null)
      params.is_fully_assigned = filters.is_fully_assigned;
  }

  const { data } = await api.get<CarePlanList>(BASE, { params });
  return data;
}

/**
 * Récupère un plan d'aide avec ses services.
 * GET /care-plans/{id}
 */
async function get(planId: number): Promise<CarePlanWithServices> {
  const { data } = await api.get<CarePlanWithServices>(`${BASE}/${planId}`);
  return data;
}

/**
 * Crée un nouveau plan d'aide.
 * POST /care-plans
 */
async function create(payload: CarePlanCreate): Promise<CarePlanWithServices> {
  const { data } = await api.post<CarePlanWithServices>(BASE, payload);
  return data;
}

/**
 * Met à jour un plan d'aide.
 * PATCH /care-plans/{id}
 */
async function update(planId: number, payload: CarePlanUpdate): Promise<CarePlanWithServices> {
  const { data } = await api.patch<CarePlanWithServices>(`${BASE}/${planId}`, payload);
  return data;
}

/**
 * Supprime un plan d'aide (seulement si en brouillon).
 * DELETE /care-plans/{id}
 */
async function remove(planId: number): Promise<void> {
  await api.delete(`${BASE}/${planId}`);
}

// =============================================================================
// CARE PLANS — WORKFLOW (State Machine)
// =============================================================================

/**
 * Soumet le plan pour validation.
 * POST /care-plans/{id}/submit
 */
async function submit(planId: number): Promise<CarePlanWithServices> {
  const { data } = await api.post<CarePlanWithServices>(`${BASE}/${planId}/submit`);
  return data;
}

/**
 * Valide et active le plan.
 * POST /care-plans/{id}/validate
 *
 * Note B28a (#108) : la réponse peut contenir un `superseded_plan_id`
 * non-NULL si un plan ACTIVE concurrent a été automatiquement fermé.
 * Cet attribut transitoire pilote le toast B28a silencieux côté UI.
 */
async function validate(planId: number): Promise<CarePlanWithServices> {
  const { data } = await api.post<CarePlanWithServices>(`${BASE}/${planId}/validate`);
  return data;
}

/**
 * Crée une révision du plan parent (B28b — Approche 4 « Clone-into-DRAFT »).
 * POST /care-plans/{parent_id}/revise
 *
 * Le backend clone le plan parent vers un nouveau DRAFT (services + fréquences
 * hérités selon `inherit_services`, GIR hérité selon `inherit_gir`), pose la
 * filiation `supersedes_plan_id`, et persiste le motif. Les affectations
 * professionnels NE sont JAMAIS héritées (décision 28).
 *
 * Statuts parent autorisés : ACTIVE, SUSPENDED, COMPLETED-récent (décision 37).
 */
async function revise(
  parentId: number,
  payload: CarePlanReviseRequest,
): Promise<CarePlanWithServices> {
  const { data } = await api.post<CarePlanWithServices>(`${BASE}/${parentId}/revise`, payload);
  return data;
}

/**
 * Remplace l'intégralité du panier de services d'un plan DRAFT
 * (B28c — sauvegarde wizard révision F6.6).
 * POST /care-plans/{id}/replace-services
 *
 * Sémantique « panier complet » : le payload contient la liste cible
 * finale des services. Le backend gère le delete-all + insert-all en
 * une transaction. Idempotent : rejouer la requête donne le même résultat.
 *
 * Statut éligible : DRAFT uniquement. Sur les autres statuts, l'API lève
 * 409 CONFLICT (CarePlanNotEditableError).
 */
async function replaceServices(
  planId: number,
  payload: CarePlanReplaceServicesRequest,
): Promise<CarePlanWithServices> {
  const { data } = await api.post<CarePlanWithServices>(
    `${BASE}/${planId}/replace-services`,
    payload,
  );
  return data;
}

/**
 * Suspend le plan.
 * POST /care-plans/{id}/suspend
 */
async function suspend(
  planId: number,
  payload?: CarePlanStatusChange,
): Promise<CarePlanWithServices> {
  const { data } = await api.post<CarePlanWithServices>(`${BASE}/${planId}/suspend`, payload ?? {});
  return data;
}

/**
 * Réactive un plan suspendu.
 * POST /care-plans/{id}/reactivate
 */
async function reactivate(planId: number): Promise<CarePlanWithServices> {
  const { data } = await api.post<CarePlanWithServices>(`${BASE}/${planId}/reactivate`);
  return data;
}

/**
 * Marque le plan comme terminé.
 * POST /care-plans/{id}/complete
 */
async function complete(planId: number): Promise<CarePlanWithServices> {
  const { data } = await api.post<CarePlanWithServices>(`${BASE}/${planId}/complete`);
  return data;
}

/**
 * Annule le plan.
 * POST /care-plans/{id}/cancel
 */
async function cancel(
  planId: number,
  payload?: CarePlanStatusChange,
): Promise<CarePlanWithServices> {
  const { data } = await api.post<CarePlanWithServices>(`${BASE}/${planId}/cancel`, payload ?? {});
  return data;
}

// =============================================================================
// CARE PLAN SERVICES — CRUD
// =============================================================================

/**
 * Liste les services d'un plan.
 * GET /care-plans/{id}/services
 */
async function listServices(planId: number): Promise<CarePlanServiceList> {
  const { data } = await api.get<CarePlanServiceList>(`${BASE}/${planId}/services`);
  return data;
}

/**
 * Récupère un service de plan.
 * GET /care-plans/{id}/services/{serviceId}
 */
async function getService(planId: number, serviceId: number): Promise<CarePlanServiceResponse> {
  const { data } = await api.get<CarePlanServiceResponse>(
    `${BASE}/${planId}/services/${serviceId}`,
  );
  return data;
}

/**
 * Ajoute un service à un plan.
 * POST /care-plans/{id}/services
 */
async function addService(
  planId: number,
  payload: CarePlanServiceCreate,
): Promise<CarePlanServiceResponse> {
  const { data } = await api.post<CarePlanServiceResponse>(`${BASE}/${planId}/services`, payload);
  return data;
}

/**
 * Met à jour un service de plan.
 * PATCH /care-plans/{id}/services/{serviceId}
 */
async function updateService(
  planId: number,
  serviceId: number,
  payload: CarePlanServiceUpdate,
): Promise<CarePlanServiceResponse> {
  const { data } = await api.patch<CarePlanServiceResponse>(
    `${BASE}/${planId}/services/${serviceId}`,
    payload,
  );
  return data;
}

/**
 * Supprime un service de plan.
 * DELETE /care-plans/{id}/services/{serviceId}
 */
async function removeService(planId: number, serviceId: number): Promise<void> {
  await api.delete(`${BASE}/${planId}/services/${serviceId}`);
}

// =============================================================================
// CARE PLAN SERVICES — AFFECTATION
// =============================================================================

/**
 * Affecte un service à un professionnel.
 * POST /care-plans/{id}/services/{serviceId}/assign
 */
async function assignService(
  planId: number,
  serviceId: number,
  payload: ServiceAssignment,
): Promise<CarePlanServiceResponse> {
  const { data } = await api.post<CarePlanServiceResponse>(
    `${BASE}/${planId}/services/${serviceId}/assign`,
    payload,
  );
  return data;
}

/**
 * Retire l'affectation d'un service.
 * DELETE /care-plans/{id}/services/{serviceId}/assign
 */
async function unassignService(
  planId: number,
  serviceId: number,
): Promise<CarePlanServiceResponse> {
  const { data } = await api.delete<CarePlanServiceResponse>(
    `${BASE}/${planId}/services/${serviceId}/assign`,
  );
  return data;
}

/**
 * Confirme l'affectation (acceptée par le professionnel).
 * POST /care-plans/{id}/services/{serviceId}/confirm
 */
async function confirmService(planId: number, serviceId: number): Promise<CarePlanServiceResponse> {
  const { data } = await api.post<CarePlanServiceResponse>(
    `${BASE}/${planId}/services/${serviceId}/confirm`,
  );
  return data;
}

/**
 * Rejette l'affectation (refusée par le professionnel).
 * POST /care-plans/{id}/services/{serviceId}/reject
 */
async function rejectService(planId: number, serviceId: number): Promise<CarePlanServiceResponse> {
  const { data } = await api.post<CarePlanServiceResponse>(
    `${BASE}/${planId}/services/${serviceId}/reject`,
  );
  return data;
}

// =============================================================================
// EXPORT — Namespace plat (convention #76)
// =============================================================================

export const carePlanService = {
  // Plans — CRUD
  list,
  get,
  create,
  update,
  remove,
  // Plans — Workflow
  submit,
  validate,
  revise,
  replaceServices,
  suspend,
  reactivate,
  complete,
  cancel,
  // Services — CRUD
  listServices,
  getService,
  addService,
  updateService,
  removeService,
  // Services — Affectation
  assignService,
  unassignService,
  confirmService,
  rejectService,
};
