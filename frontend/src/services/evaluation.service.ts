/**
 * CareLink - EvaluationService
 * Chemin : frontend/src/services/evaluation.service.ts
 *
 * Rôle : Appels API pour les évaluations patient
 *        (CRUD, soumission, sessions de saisie, synchronisation offline)
 */
import api from './api';
import axios from 'axios';

// =============================================================================
// TYPES
// =============================================================================

export interface CreateEvaluationPayload {
  evaluation_type: string;
  schema_type: string;
  schema_version: string;
  evaluation_date: string; // ✅ Fix: champ requis par le backend (format YYYY-MM-DD)
  evaluation_data?: Record<string, unknown>;
  completion_percent?: number;
  notes?: string;
}

export interface UpdateEvaluationPayload {
  evaluation_data?: Record<string, unknown>;
  completion_percent?: number;
  notes?: string;
}

export interface StartSessionPayload {
  device_info: string;
}

export interface EndSessionPayload {
  variables_saved?: string[];
  notes?: string;
}

// =============================================================================
// SERVICE
// =============================================================================

const evaluationService = {
  // ── CRUD ───────────────────────────────────────────────────────────────

  /** Liste des évaluations d'un patient */
  async getAll(patientId: number, includeExpired = false) {
    return api.get(`/patients/${patientId}/evaluations`, {
      params: { include_expired: includeExpired },
    });
  },

  /** Détail d'une évaluation */
  async get(patientId: number, evaluationId: number) {
    return api.get(`/patients/${patientId}/evaluations/${evaluationId}`);
  },

  /**
   * Dernière évaluation soumise (pré-remplissage nouvelle évaluation).
   * Retourne null (pas d'exception) si aucune évaluation soumise n'existe.
   */
  async getLatestSubmitted(patientId: number) {
    try {
      return await api.get(`/patients/${patientId}/evaluations/latest-submitted`);
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.status === 404) return null;
      throw err;
    }
  },

  /** Créer une évaluation (validation JSON Schema partielle) */
  async create(patientId: number, data: CreateEvaluationPayload) {
    return api.post(`/patients/${patientId}/evaluations`, data);
  },

  /** Modifier une évaluation DRAFT (validation partielle) */
  async update(patientId: number, evaluationId: number, data: UpdateEvaluationPayload) {
    return api.patch(`/patients/${patientId}/evaluations/${evaluationId}`, data);
  },

  /** Supprimer une évaluation (DRAFT uniquement) */
  async delete(patientId: number, evaluationId: number) {
    return api.delete(`/patients/${patientId}/evaluations/${evaluationId}`);
  },

  // ── Workflow ───────────────────────────────────────────────────────────

  /** Soumettre (validation JSON Schema complète) */
  async submit(patientId: number, evaluationId: number) {
    return api.post(`/patients/${patientId}/evaluations/${evaluationId}/submit`);
  },

  /** Validation médicale (médecin coordonnateur) */
  async validateMedical(patientId: number, evaluationId: number) {
    return api.post(`/patients/${patientId}/evaluations/${evaluationId}/validate`);
  },

  // ── Sessions de saisie ─────────────────────────────────────────────────

  /** Liste des sessions d'une évaluation */
  async getSessions(patientId: number, evaluationId: number) {
    return api.get(`/patients/${patientId}/evaluations/${evaluationId}/sessions`);
  },

  /** Démarrer une nouvelle session de saisie */
  async startSession(patientId: number, evaluationId: number, deviceInfo: string) {
    return api.post(`/patients/${patientId}/evaluations/${evaluationId}/sessions`, {
      device_info: deviceInfo,
    } as StartSessionPayload);
  },

  /** Terminer/mettre à jour une session */
  async endSession(
    patientId: number,
    evaluationId: number,
    sessionId: number,
    data: EndSessionPayload,
  ) {
    return api.post(
      `/patients/${patientId}/evaluations/${evaluationId}/sessions/${sessionId}/end`,
      data,
    );
  },

  // ── Synchronisation offline ────────────────────────────────────────────

  /** Synchroniser des données saisies hors-ligne */
  async syncOffline(
    patientId: number,
    evaluationId: number,
    evaluationData: Record<string, unknown>,
    localSessionId?: string,
  ) {
    return api.post(`/patients/${patientId}/evaluations/${evaluationId}/sync`, {
      evaluation_data: evaluationData,
      local_session_id: localSessionId,
    });
  },
};

export default evaluationService;