/**
 * Service Planning
 * Gère les interventions planifiées et le planning journalier
 */
import api from './api';
import type {
  DailyPlanning,
  ScheduledInterventionResponse,
  ScheduledInterventionList,
  InterventionStart,
  InterventionComplete,
  InterventionCancel,
  InterventionReschedule,
  PaginationParams,
} from '@/types';

// =============================================================================
// PLANNING SERVICE
// =============================================================================

export const planningService = {
  // ===========================================================================
  // PLANNING VIEWS
  // ===========================================================================

  /** Mon planning du jour (utilisateur connecté) */
  async getMyDay(date?: string): Promise<DailyPlanning> {
    const params = date ? { planning_date: date } : {};
    const response = await api.get<DailyPlanning>('/planning/my-day', { params });
    return response.data;
  },

  /** Planning d'un utilisateur spécifique */
  async getDailyPlanning(userId: number, date: string): Promise<DailyPlanning> {
    const response = await api.get<DailyPlanning>(`/planning/daily/${userId}`, {
      params: { planning_date: date },
    });
    return response.data;
  },

  // ===========================================================================
  // INTERVENTIONS CRUD
  // ===========================================================================

  /** Liste des interventions avec filtres */
  async getInterventions(
    params?: PaginationParams & {
      patient_id?: number;
      user_id?: number;
      status?: string;
      date_from?: string;
      date_to?: string;
    },
  ): Promise<ScheduledInterventionList> {
    const response = await api.get<ScheduledInterventionList>('/scheduled-interventions', {
      params,
    });
    return response.data;
  },

  /** Récupérer une intervention */
  async getIntervention(id: number): Promise<ScheduledInterventionResponse> {
    const response = await api.get<ScheduledInterventionResponse>(`/scheduled-interventions/${id}`);
    return response.data;
  },

  // ===========================================================================
  // WORKFLOW INTERVENTIONS
  // ===========================================================================

  /** Confirmer une intervention */
  async confirm(id: number): Promise<ScheduledInterventionResponse> {
    const response = await api.post<ScheduledInterventionResponse>(
      `/scheduled-interventions/${id}/confirm`,
    );
    return response.data;
  },

  /** Démarrer une intervention */
  async start(id: number, data?: InterventionStart): Promise<ScheduledInterventionResponse> {
    const response = await api.post<ScheduledInterventionResponse>(
      `/scheduled-interventions/${id}/start`,
      data || {},
    );
    return response.data;
  },

  /** Terminer une intervention */
  async complete(id: number, data?: InterventionComplete): Promise<ScheduledInterventionResponse> {
    const response = await api.post<ScheduledInterventionResponse>(
      `/scheduled-interventions/${id}/complete`,
      data || {},
    );
    return response.data;
  },

  /** Annuler une intervention */
  async cancel(id: number, data: InterventionCancel): Promise<ScheduledInterventionResponse> {
    const response = await api.post<ScheduledInterventionResponse>(
      `/scheduled-interventions/${id}/cancel`,
      data,
    );
    return response.data;
  },

  /** Marquer comme manquée */
  async markMissed(id: number, reason?: string): Promise<ScheduledInterventionResponse> {
    const response = await api.post<ScheduledInterventionResponse>(
      `/scheduled-interventions/${id}/missed`,
      null,
      { params: { reason } },
    );
    return response.data;
  },

  /** Reprogrammer une intervention */
  async reschedule(
    id: number,
    data: InterventionReschedule,
  ): Promise<ScheduledInterventionResponse> {
    const response = await api.post<ScheduledInterventionResponse>(
      `/scheduled-interventions/${id}/reschedule`,
      data,
    );
    return response.data;
  },
};

export default planningService;
