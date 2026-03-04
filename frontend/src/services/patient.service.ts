/**
 * Service Patient
 * Gère les appels API pour les dossiers patients, évaluations, constantes
 */
import api from './api'
import type {
  PatientResponse,
  PatientList,
  PatientCreate,
  PatientUpdate,
  PatientFilters,
  PatientEvaluationResponse,
  PatientEvaluationList,
  PatientEvaluationCreate,
  PatientEvaluationUpdate,
  PatientVitalsResponse,
  PatientVitalsList,
  PatientVitalsCreate,
  PaginationParams,
} from '@/types'

// =============================================================================
// PATIENT SERVICE
// =============================================================================

export const patientService = {
  // ===========================================================================
  // PATIENTS CRUD
  // ===========================================================================

  /** Liste des patients avec filtres et pagination */
  async getAll(params?: PaginationParams & PatientFilters): Promise<PatientList> {
    const response = await api.get<PatientList>('/patients', { params })
    return response.data
  },

  /** Récupérer un patient par ID */
  async getById(id: number): Promise<PatientResponse> {
    const response = await api.get<PatientResponse>(`/patients/${id}`)
    return response.data
  },

  /** Créer un patient */
  async create(data: PatientCreate): Promise<PatientResponse> {
    const response = await api.post<PatientResponse>('/patients', data)
    return response.data
  },

  /** Mettre à jour un patient */
  async update(id: number, data: PatientUpdate): Promise<PatientResponse> {
    const response = await api.patch<PatientResponse>(`/patients/${id}`, data)
    return response.data
  },

  /** Supprimer (archiver) un patient */
  async delete(id: number): Promise<void> {
    await api.delete(`/patients/${id}`)
  },

  // ===========================================================================
  // EVALUATIONS
  // ===========================================================================

  /** Liste des évaluations d'un patient */
  async getEvaluations(
    patientId: number,
    params?: PaginationParams
  ): Promise<PatientEvaluationList> {
    const response = await api.get<PatientEvaluationList>(
      `/patients/${patientId}/evaluations`,
      { params }
    )
    return response.data
  },

  /** Récupérer une évaluation */
  async getEvaluation(
    patientId: number,
    evaluationId: number
  ): Promise<PatientEvaluationResponse> {
    const response = await api.get<PatientEvaluationResponse>(
      `/patients/${patientId}/evaluations/${evaluationId}`
    )
    return response.data
  },

  /** Créer une évaluation */
  async createEvaluation(
    patientId: number,
    data: PatientEvaluationCreate
  ): Promise<PatientEvaluationResponse> {
    const response = await api.post<PatientEvaluationResponse>(
      `/patients/${patientId}/evaluations`,
      data
    )
    return response.data
  },

  /** Mettre à jour une évaluation */
  async updateEvaluation(
    patientId: number,
    evaluationId: number,
    data: PatientEvaluationUpdate
  ): Promise<PatientEvaluationResponse> {
    const response = await api.patch<PatientEvaluationResponse>(
      `/patients/${patientId}/evaluations/${evaluationId}`,
      data
    )
    return response.data
  },

  /** Soumettre pour validation */
  async submitEvaluation(
    patientId: number,
    evaluationId: number
  ): Promise<PatientEvaluationResponse> {
    const response = await api.post<PatientEvaluationResponse>(
      `/patients/${patientId}/evaluations/${evaluationId}/submit`
    )
    return response.data
  },

  // ===========================================================================
  // VITALS (CONSTANTES)
  // ===========================================================================

  /** Liste des constantes d'un patient */
  async getVitals(
    patientId: number,
    params?: PaginationParams & { vital_type?: string }
  ): Promise<PatientVitalsList> {
    const response = await api.get<PatientVitalsList>(
      `/patients/${patientId}/vitals`,
      { params }
    )
    return response.data
  },

  /** Dernière constante d'un type */
  async getLatestVital(
    patientId: number,
    vitalType: string
  ): Promise<PatientVitalsResponse> {
    const response = await api.get<PatientVitalsResponse>(
      `/patients/${patientId}/vitals/latest/${vitalType}`
    )
    return response.data
  },

  /** Créer une mesure */
  async createVital(
    patientId: number,
    data: PatientVitalsCreate
  ): Promise<PatientVitalsResponse> {
    const response = await api.post<PatientVitalsResponse>(
      `/patients/${patientId}/vitals`,
      data
    )
    return response.data
  },
}

export default patientService
