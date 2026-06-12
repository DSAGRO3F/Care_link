/**
 * Service API — Module Validation (Phase 4 bis — portail valideur).
 *
 * Chemin : frontend/src/services/validation.service.ts
 *
 * Rôle : mirror des 14 endpoints du `validation_router` (validation/routes.py).
 * - VR lecture (2) : list (paginée + filtres) + get
 * - Soumission (2) : submitEvaluation / submitCarePlan  [flux soumetteur, écran reporté]
 * - Re-soumission (1) : resubmitEvaluation                [R1 — boucle MORE_INFO]
 * - Transmission (2) : transmitMedical / transmitFunding
 * - Décision (1) : decide
 * - Retrait (1) : withdraw                               [flux soumetteur, écran reporté]
 * - Recours (1) : markUnderAppeal                        [flux département, hors J4]
 * - Fil d'échange (4) : listExchanges / addComment / getEvaluationThread / getCarePlanThread
 *
 * Convention #76 : namespace plat (list, get, decide…), pas de sous-namespace.
 * Convention #74 : data.items ?? data pour endpoints paginés (ici la réponse
 *   est déjà l'enveloppe { items, total, … }, on retourne data directement).
 * Les 4 endpoints du fil et /decide /transmit-* sont les seuls consommés par
 * l'écran J4 ; les autres complètent le mirror du router (cf. care-plan.service).
 *
 * Tous gatés `VALIDATION_VIEW` côté backend, sauf markUnderAppeal (EVALUATION_CREATE).
 *
 * 🆕 B40-J4 / F2 — création du service.
 */

import api from './api';
import type {
  DossierContext,
  ExchangeCreate,
  ExchangeResponse,
  MarkUnderAppealRequest,
  ResubmitRequest,
  ValidationDecisionRequest,
  ValidationRequestFilters,
  ValidationRequestList,
  ValidationRequestResponse,
  ValidationSubmitRequest,
  ValidationTransmitRequest,
  ValidationWithdrawRequest,
} from '@/types';

const VR_BASE = '/validation-requests';

// =============================================================================
// VALIDATION REQUEST — LECTURE
// =============================================================================

/**
 * Liste paginée des demandes de validation (fenêtre RLS : émetteur + valideur
 * assigné + admin tenant).
 * GET /validation-requests
 */
async function list(
  page = 1,
  size = 20,
  filters?: ValidationRequestFilters,
): Promise<ValidationRequestList> {
  const params: Record<string, string | number | boolean> = { page, size };

  if (filters) {
    if (filters.workflow_type) params.workflow_type = filters.workflow_type;
    if (filters.stage) params.stage = filters.stage;
    if (filters.decision) params.decision = filters.decision;
    if (
      filters.assigned_validator_user_id !== undefined &&
      filters.assigned_validator_user_id !== null
    )
      params.assigned_validator_user_id = filters.assigned_validator_user_id;
    if (filters.submitted_by_user_id !== undefined && filters.submitted_by_user_id !== null)
      params.submitted_by_user_id = filters.submitted_by_user_id;
    if (filters.pending_only !== undefined && filters.pending_only !== null)
      params.pending_only = filters.pending_only;
  }

  const { data } = await api.get<ValidationRequestList>(VR_BASE, { params });
  return data;
}

/**
 * Récupère une demande de validation par son id.
 * GET /validation-requests/{vr_id}
 */
async function get(vrId: number): Promise<ValidationRequestResponse> {
  const { data } = await api.get<ValidationRequestResponse>(`${VR_BASE}/${vrId}`);
  return data;
}

// =============================================================================
// VALIDATION REQUEST — SOUMISSION (flux soumetteur — écran /soins reporté)
// =============================================================================

/**
 * Soumet une évaluation pour validation (workflow AGGIR_FUNDING dérivé serveur).
 * POST /evaluations/{evaluation_id}/submit-for-validation
 */
async function submitEvaluation(
  evaluationId: number,
  payload?: ValidationSubmitRequest,
): Promise<ValidationRequestResponse> {
  const { data } = await api.post<ValidationRequestResponse>(
    `/evaluations/${evaluationId}/submit-for-validation`,
    payload ?? {},
  );
  return data;
}

/**
 * Soumet un plan d'aide pour validation (workflow COORDINATION_DOSSIER).
 * POST /care-plans/{care_plan_id}/submit-for-validation
 */
async function submitCarePlan(
  carePlanId: number,
  payload?: ValidationSubmitRequest,
): Promise<ValidationRequestResponse> {
  const { data } = await api.post<ValidationRequestResponse>(
    `/care-plans/${carePlanId}/submit-for-validation`,
    payload ?? {},
  );
  return data;
}

/**
 * Re-soumet une évaluation après une demande de compléments (R1 — boucle MORE_INFO).
 * L'éval « garée » en PENDING_INTERNAL_REVIEW est ré-ouverte : nouvelle VR
 * INTERNAL_REVIEW chaînée à la VR qui a demandé le complément (chaînage serveur).
 * POST /evaluations/{evaluation_id}/resubmit-for-validation
 */
async function resubmitEvaluation(
  evaluationId: number,
  payload?: ResubmitRequest,
): Promise<ValidationRequestResponse> {
  const { data } = await api.post<ValidationRequestResponse>(
    `/evaluations/${evaluationId}/resubmit-for-validation`,
    payload ?? {},
  );
  return data;
}

// =============================================================================
// VALIDATION REQUEST — TRANSMISSION (transition d'étape → valideur externe)
// =============================================================================

/**
 * Transmet la VR au médecin (étape MEDICAL_REVIEW). Crée le maillon suivant
 * de la chaîne (previous_vr_id posé côté service).
 * POST /validation-requests/{vr_id}/transmit-medical
 */
async function transmitMedical(
  vrId: number,
  payload: ValidationTransmitRequest,
): Promise<ValidationRequestResponse> {
  const { data } = await api.post<ValidationRequestResponse>(
    `${VR_BASE}/${vrId}/transmit-medical`,
    payload,
  );
  return data;
}

/**
 * Transmet la VR à l'agent département (étape FUNDING_REVIEW — décision APA).
 * POST /validation-requests/{vr_id}/transmit-funding
 */
async function transmitFunding(
  vrId: number,
  payload: ValidationTransmitRequest,
): Promise<ValidationRequestResponse> {
  const { data } = await api.post<ValidationRequestResponse>(
    `${VR_BASE}/${vrId}/transmit-funding`,
    payload,
  );
  return data;
}

// =============================================================================
// VALIDATION REQUEST — DÉCISION
// =============================================================================

/**
 * Décision d'un valideur (VALIDATED | INVALIDATED | MORE_INFO_REQUESTED).
 * Validation stricte miroir du model_validator Pydantic (422 si motif manquant).
 * POST /validation-requests/{vr_id}/decide
 */
async function decide(
  vrId: number,
  payload: ValidationDecisionRequest,
): Promise<ValidationRequestResponse> {
  const { data } = await api.post<ValidationRequestResponse>(
    `${VR_BASE}/${vrId}/decide`,
    payload,
  );
  return data;
}

// =============================================================================
// VALIDATION REQUEST — RETRAIT (flux soumetteur — écran reporté)
// =============================================================================

/**
 * Retrait par le soumetteur avant décision (cycle interne uniquement — D14 v2).
 * POST /validation-requests/{vr_id}/withdraw
 */
async function withdraw(
  vrId: number,
  payload?: ValidationWithdrawRequest,
): Promise<ValidationRequestResponse> {
  const { data } = await api.post<ValidationRequestResponse>(
    `${VR_BASE}/${vrId}/withdraw`,
    payload ?? {},
  );
  return data;
}

// =============================================================================
// ÉVALUATION — RECOURS (flux département, hors J4 — gating EVALUATION_CREATE)
// =============================================================================

/**
 * Active le drapeau « recours en cours » sur une évaluation FUNDING_REJECTED (D21).
 * Retour ad-hoc (pas de schéma Pydantic dédié côté backend).
 * POST /evaluations/{evaluation_id}/mark-under-appeal
 */
async function markUnderAppeal(
  evaluationId: number,
  payload?: MarkUnderAppealRequest,
): Promise<{ evaluation_id: number; is_under_appeal: boolean; appeal_notes: string | null }> {
  const { data } = await api.post<{
    evaluation_id: number;
    is_under_appeal: boolean;
    appeal_notes: string | null;
  }>(`/evaluations/${evaluationId}/mark-under-appeal`, payload ?? {});
  return data;
}

// =============================================================================
// FIL D'ÉCHANGE (B40-J3)
// =============================================================================

/**
 * Fil d'une VR (entrées filtrées par visibilité au service backend — l'UI ne
 * re-filtre pas).
 * GET /validation-requests/{vr_id}/exchanges
 */
async function listExchanges(vrId: number): Promise<ExchangeResponse[]> {
  const { data } = await api.get<ExchangeResponse[]>(`${VR_BASE}/${vrId}/exchanges`);
  return data;
}

/**
 * Ajoute un commentaire manuel au fil d'une VR (action_type COMMENT forcé serveur).
 * POST /validation-requests/{vr_id}/exchanges
 */
async function addComment(vrId: number, payload: ExchangeCreate): Promise<ExchangeResponse> {
  const { data } = await api.post<ExchangeResponse>(`${VR_BASE}/${vrId}/exchanges`, payload);
  return data;
}

/**
 * Fil agrégé d'un dossier d'évaluation (toutes les VR de l'objet, triées).
 * GET /evaluations/{evaluation_id}/thread
 */
async function getEvaluationThread(evaluationId: number): Promise<ExchangeResponse[]> {
  const { data } = await api.get<ExchangeResponse[]>(`/evaluations/${evaluationId}/thread`);
  return data;
}

/**
 * Fil agrégé d'un dossier de plan d'aide (toutes les VR de l'objet, triées).
 * GET /care-plans/{care_plan_id}/thread
 */
async function getCarePlanThread(carePlanId: number): Promise<ExchangeResponse[]> {
  const { data } = await api.get<ExchangeResponse[]>(`/care-plans/${carePlanId}/thread`);
  return data;
}

// =============================================================================
// CONTEXTE DOSSIER (S2/S3 — D-α.2)
// =============================================================================

/**
 * Contexte d'un dossier d'évaluation : bandeau patient (identité + adresse + GIR,
 * déchiffré et minimisé côté backend) + pipeline des VR du dossier en ordre
 * chronologique. Agrégat porté côté backend (A0) — un seul aller-retour ;
 * fiabilise séparateurs d'étape et n° de VR (fini le best-effort par index).
 * GET /evaluations/{evaluation_id}/dossier-context
 */
async function getEvaluationDossierContext(evaluationId: number): Promise<DossierContext> {
  const { data } = await api.get<DossierContext>(
    `/evaluations/${evaluationId}/dossier-context`,
  );
  return data;
}

/**
 * Contexte d'un dossier de plan d'aide (symétrique de l'évaluation).
 * GET /care-plans/{care_plan_id}/dossier-context
 */
async function getCarePlanDossierContext(carePlanId: number): Promise<DossierContext> {
  const { data } = await api.get<DossierContext>(
    `/care-plans/${carePlanId}/dossier-context`,
  );
  return data;
}

// =============================================================================
// EXPORT — Namespace plat (convention #76)
// =============================================================================

export const validationService = {
  // VR — Lecture
  list,
  get,
  // VR — Soumission (flux soumetteur)
  submitEvaluation,
  submitCarePlan,
  // VR — Re-soumission après complément (R1)
  resubmitEvaluation,
  // VR — Transmission
  transmitMedical,
  transmitFunding,
  // VR — Décision
  decide,
  // VR — Retrait (flux soumetteur)
  withdraw,
  // Évaluation — Recours
  markUnderAppeal,
  // Fil d'échange
  listExchanges,
  addComment,
  getEvaluationThread,
  getCarePlanThread,
  // Contexte dossier (S2/S3)
  getEvaluationDossierContext,
  getCarePlanDossierContext,
};
