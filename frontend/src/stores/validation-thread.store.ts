/**
 * Store Pinia — Fil de validation (Phase 4 bis — portail valideur, B40-J4).
 *
 * Chemin : frontend/src/stores/validation-thread.store.ts
 *
 * Backe l'écran unifié « Dossier de validation » :
 * - le fil agrégé d'un dossier (évaluation OU plan d'aide) ;
 * - la VR en focus (`currentRequest`) contre laquelle s'exercent les actes
 *   du compose (commentaire / décision / transmission) ;
 * - les segments du fil (groupés par VR) pour les séparateurs d'étape (F6).
 *
 * Principe clé (A1/D32) : le filtrage par visibilité est porté côté service
 * backend. L'UI NE re-filtre PAS. Après tout acte, on RECHARGE le fil depuis
 * le serveur (le contexte dossier mémorisé indique quel endpoint rappeler) —
 * pas de reconstruction optimiste locale qui contournerait le serializer.
 *
 * Convention Pinia maison : defineStore + ref/computed (cf. care-plan.store).
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { validationService } from '@/services';
import type {
  DossierContext,
  ExchangeCreate,
  ExchangeResponse,
  PatientIdentity,
  ResubmitRequest,
  ValidationDecisionRequest,
  ValidationRequestResponse,
  ValidationRequestSummary,
  ValidationStage,
  ValidationTransmitRequest,
} from '@/types';

/** Contexte du dossier chargé — sert à recharger le bon fil après un acte. */
type ThreadContext = { kind: 'evaluation'; id: number } | { kind: 'care-plan'; id: number };

/** Un segment du fil = toutes les entrées rattachées à une même VR, dans l'ordre. */
interface ThreadSegment {
  validationRequestId: number;
  /** Étape de la VR du segment (depuis le contexte dossier), null si inconnue. */
  stage: ValidationStage | null;
  entries: ExchangeResponse[];
}

export const useValidationThreadStore = defineStore('validation-thread', () => {
  // ===========================================================================
  // STATE
  // ===========================================================================

  /** Entrées du fil agrégé (déjà filtrées par visibilité côté serveur). */
  const thread = ref<ExchangeResponse[]>([]);

  /** VR en focus (pipeline « étape courante » + cible des actes du compose). */
  const currentRequest = ref<ValidationRequestResponse | null>(null);

  /** Dossier chargé (mémorisé pour le rechargement post-acte). */
  const context = ref<ThreadContext | null>(null);

  /**
   * Contexte dossier (bandeau patient + pipeline des VR), agrégé côté backend.
   * Chargé en parallèle du fil et rafraîchi après chaque acte (un transmit crée
   * une VR, une décision change le pipeline).
   */
  const dossierContext = ref<DossierContext | null>(null);

  // ===========================================================================
  // STATE — UI
  // ===========================================================================

  const loading = ref(false); // chargement du fil / de la VR
  const posting = ref(false); // acte en cours (commentaire / décision / transmission)
  const error = ref<string | null>(null);

  // ===========================================================================
  // COMPUTED
  // ===========================================================================

  /** Le fil contient-il au moins une entrée ? */
  const hasThread = computed(() => thread.value.length > 0);

  /** Étape courante du dossier (depuis la VR en focus). */
  const currentStage = computed(() => currentRequest.value?.stage ?? null);

  /** Identité patient pour le bandeau (sous-ensemble minimisé, déchiffré serveur). */
  const patientIdentity = computed<PatientIdentity | null>(
    () => dossierContext.value?.patient ?? null,
  );

  /**
   * VR du dossier indexée par étape (pour le pipeline F5). `requests` arrive en
   * ordre chronologique : en cas de rebond (nouvelle VR à la même étape), la
   * plus récente écrase la précédente — c'est bien elle qu'on veut afficher.
   */
  const requestByStage = computed<Map<ValidationStage, ValidationRequestSummary>>(() => {
    const map = new Map<ValidationStage, ValidationRequestSummary>();
    for (const r of dossierContext.value?.requests ?? []) map.set(r.stage, r);
    return map;
  });

  /** Étape de chaque VR du dossier, indexée par id (pour les séparateurs F6). */
  const stageByRequestId = computed<Record<number, ValidationStage>>(() => {
    const map: Record<number, ValidationStage> = {};
    for (const r of dossierContext.value?.requests ?? []) map[r.id] = r.stage;
    return map;
  });

  /**
   * Segments du fil, groupés par VR dans l'ordre chronologique d'apparition.
   * F6 pose un séparateur d'étape à chaque frontière de segment. Le fil arrive
   * déjà trié du serveur ; on respecte cet ordre sans le recalculer. Le `stage`
   * est résolu via le contexte dossier (fini le best-effort par index).
   */
  const threadSegments = computed<ThreadSegment[]>(() => {
    const segments: ThreadSegment[] = [];
    const stageMap = stageByRequestId.value;
    for (const entry of thread.value) {
      const last = segments[segments.length - 1];
      if (last && last.validationRequestId === entry.validation_request_id) {
        last.entries.push(entry);
      } else {
        segments.push({
          validationRequestId: entry.validation_request_id,
          stage: stageMap[entry.validation_request_id] ?? null,
          entries: [entry],
        });
      }
    }
    return segments;
  });

  // ===========================================================================
  // ACTIONS — Chargement
  // ===========================================================================

  /** Charge le contexte dossier (bandeau + pipeline) selon le contexte mémorisé. */
  async function loadDossierContext(): Promise<void> {
    if (!context.value) return;
    dossierContext.value =
      context.value.kind === 'evaluation'
        ? await validationService.getEvaluationDossierContext(context.value.id)
        : await validationService.getCarePlanDossierContext(context.value.id);
  }

  /** Recharge fil + contexte dossier depuis le serveur (silencieux, post-acte). */
  async function refreshThread(): Promise<void> {
    if (!context.value) return;
    thread.value =
      context.value.kind === 'evaluation'
        ? await validationService.getEvaluationThread(context.value.id)
        : await validationService.getCarePlanThread(context.value.id);
    await loadDossierContext();
  }

  /** Charge le fil d'un dossier d'évaluation. */
  async function loadEvaluationThread(evaluationId: number): Promise<void> {
    loading.value = true;
    error.value = null;
    context.value = { kind: 'evaluation', id: evaluationId };
    try {
      thread.value = await validationService.getEvaluationThread(evaluationId);
      await loadDossierContext();
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors du chargement du fil';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /** Charge le fil d'un dossier de plan d'aide. */
  async function loadCarePlanThread(carePlanId: number): Promise<void> {
    loading.value = true;
    error.value = null;
    context.value = { kind: 'care-plan', id: carePlanId };
    try {
      thread.value = await validationService.getCarePlanThread(carePlanId);
      await loadDossierContext();
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors du chargement du fil';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /** Charge la VR en focus. */
  async function loadRequest(vrId: number): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      currentRequest.value = await validationService.get(vrId);
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Demande de validation non trouvée';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Entrée principale de l'écran : charge la VR puis le fil de son dossier.
   * Le valideur arrive typiquement depuis une notification pointant une VR.
   */
  async function loadFromRequest(vrId: number): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      const vr = await validationService.get(vrId);
      currentRequest.value = vr;
      if (vr.evaluation_id !== null) {
        context.value = { kind: 'evaluation', id: vr.evaluation_id };
        thread.value = await validationService.getEvaluationThread(vr.evaluation_id);
      } else if (vr.care_plan_id !== null) {
        context.value = { kind: 'care-plan', id: vr.care_plan_id };
        thread.value = await validationService.getCarePlanThread(vr.care_plan_id);
      }
      await loadDossierContext();
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors du chargement du dossier';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  // ===========================================================================
  // ACTIONS — Actes (rechargent le fil depuis le serveur après mutation)
  // ===========================================================================

  /** Ajoute un commentaire manuel au fil (COMMENT forcé serveur). */
  async function addComment(vrId: number, payload: ExchangeCreate): Promise<ExchangeResponse> {
    posting.value = true;
    error.value = null;
    try {
      const entry = await validationService.addComment(vrId, payload);
      await refreshThread();
      return entry;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : "Erreur lors de l'ajout du commentaire";
      throw err;
    } finally {
      posting.value = false;
    }
  }

  /** Décision d'un valideur (VALIDATED | INVALIDATED | MORE_INFO_REQUESTED). */
  async function decide(
    vrId: number,
    payload: ValidationDecisionRequest,
  ): Promise<ValidationRequestResponse> {
    posting.value = true;
    error.value = null;
    try {
      const vr = await validationService.decide(vrId, payload);
      currentRequest.value = vr;
      await refreshThread();
      return vr;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors de la décision';
      throw err;
    } finally {
      posting.value = false;
    }
  }

  /** Transmet la VR au médecin (étape MEDICAL_REVIEW). */
  async function transmitMedical(
    vrId: number,
    payload: ValidationTransmitRequest,
  ): Promise<ValidationRequestResponse> {
    posting.value = true;
    error.value = null;
    try {
      const vr = await validationService.transmitMedical(vrId, payload);
      currentRequest.value = vr;
      await refreshThread();
      return vr;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors de la transmission';
      throw err;
    } finally {
      posting.value = false;
    }
  }

  /** Transmet la VR à l'agent département (étape FUNDING_REVIEW). */
  async function transmitFunding(
    vrId: number,
    payload: ValidationTransmitRequest,
  ): Promise<ValidationRequestResponse> {
    posting.value = true;
    error.value = null;
    try {
      const vr = await validationService.transmitFunding(vrId, payload);
      currentRequest.value = vr;
      await refreshThread();
      return vr;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors de la transmission';
      throw err;
    } finally {
      posting.value = false;
    }
  }

  /**
   * Re-soumet une évaluation après une demande de compléments (R1 — boucle
   * MORE_INFO). Ré-ouvre une VR INTERNAL_REVIEW chaînée ; la nouvelle VR
   * devient la VR en focus, puis on recharge fil + pipeline.
   */
  async function resubmitEvaluation(
    evaluationId: number,
    payload?: ResubmitRequest,
  ): Promise<ValidationRequestResponse> {
    posting.value = true;
    error.value = null;
    try {
      const vr = await validationService.resubmitEvaluation(evaluationId, payload);
      currentRequest.value = vr;
      await refreshThread();
      return vr;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors de la re-soumission';
      throw err;
    } finally {
      posting.value = false;
    }
  }

  /** Réinitialise le store (à la sortie de l'écran). */
  function reset(): void {
    thread.value = [];
    currentRequest.value = null;
    context.value = null;
    dossierContext.value = null;
    loading.value = false;
    posting.value = false;
    error.value = null;
  }

  // ===========================================================================
  // RETURN
  // ===========================================================================

  return {
    // State
    thread,
    currentRequest,
    context,
    dossierContext,
    loading,
    posting,
    error,

    // Computed
    hasThread,
    currentStage,
    patientIdentity,
    requestByStage,
    stageByRequestId,
    threadSegments,

    // Actions — Chargement
    refreshThread,
    loadEvaluationThread,
    loadCarePlanThread,
    loadRequest,
    loadFromRequest,

    // Actions — Actes
    addComment,
    decide,
    transmitMedical,
    transmitFunding,
    resubmitEvaluation,

    // Divers
    reset,
  };
});
