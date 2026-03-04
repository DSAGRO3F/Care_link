/**
 * Types pour le module Coordination
 * Carnet de liaison + planning des interventions
 */

// =============================================================================
// ENUMS
// =============================================================================

/** Catégories d'entrées de coordination */
export type CoordinationCategory = 
  | 'SOINS' 
  | 'HYGIENE' 
  | 'REPAS' 
  | 'MOBILITE' 
  | 'SOCIAL' 
  | 'ADMINISTRATIF' 
  | 'AUTRE'

/** Statuts d'une intervention planifiée */
export type InterventionStatus = 
  | 'SCHEDULED' 
  | 'CONFIRMED' 
  | 'IN_PROGRESS' 
  | 'COMPLETED' 
  | 'CANCELLED' 
  | 'MISSED'

// =============================================================================
// COORDINATION ENTRY (Carnet de liaison)
// =============================================================================

/** Entrée du carnet de coordination */
export interface CoordinationEntryResponse {
  id: number
  patient_id: number
  user_id: number
  category: CoordinationCategory
  intervention_type: string
  description: string
  observations?: string
  next_actions?: string
  performed_at: string
  duration_minutes?: number
  deleted_at?: string
  is_active: boolean
  is_recent: boolean
  user_name?: string
  created_at: string
  updated_at?: string
}

/** Création d'une entrée */
export interface CoordinationEntryCreate {
  patient_id: number
  category: CoordinationCategory
  intervention_type: string
  description: string
  observations?: string
  next_actions?: string
  performed_at: string
  duration_minutes?: number
}

/** Liste paginée */
export interface CoordinationEntryList {
  items: CoordinationEntryResponse[]
  total: number
  page: number
  size: number
  pages: number
}

// =============================================================================
// SCHEDULED INTERVENTION (Planning)
// =============================================================================

/** Intervention planifiée */
export interface ScheduledInterventionResponse {
  id: number
  care_plan_service_id: number
  patient_id: number
  user_id?: number
  scheduled_date: string
  scheduled_start_time: string
  scheduled_end_time: string
  status: InterventionStatus
  actual_start_time?: string
  actual_end_time?: string
  actual_duration_minutes?: number
  completion_notes?: string
  cancellation_reason?: string
  coordination_entry_id?: number
  scheduled_duration_minutes: number
  time_slot_display: string
  is_pending: boolean
  is_completed: boolean
  is_cancelled: boolean
  is_terminal: boolean
  can_be_started: boolean
  user_name?: string
  service_name?: string
  created_at: string
  updated_at?: string
}

/** Liste paginée */
export interface ScheduledInterventionList {
  items: ScheduledInterventionResponse[]
  total: number
  page: number
  size: number
  pages: number
}

/** Planning journalier */
export interface DailyPlanning {
  user_id: number
  date: string
  interventions: ScheduledInterventionResponse[]
  total_scheduled_minutes: number
  total_interventions: number
}

// =============================================================================
// ACTIONS INTERVENTION
// =============================================================================

/** Démarrer une intervention */
export interface InterventionStart {
  actual_start_time?: string
}

/** Terminer une intervention */
export interface InterventionComplete {
  actual_end_time?: string
  completion_notes?: string
}

/** Annuler une intervention */
export interface InterventionCancel {
  cancellation_reason: string
}

/** Reprogrammer une intervention */
export interface InterventionReschedule {
  new_date: string
  new_start_time: string
  new_end_time: string
  reason?: string
}
