/**
 * Types pour le module Patient
 * Correspond aux schemas Pydantic backend: app/api/v1/patient/schemas.py
 *
 * Sprint 7 — Ajout de PatientQueryParams pour alignement avec admin.store.ts
 */

// =============================================================================
// ENUMS
// =============================================================================

/** Statuts possibles d'un patient */
export type PatientStatus = 'ACTIVE' | 'INACTIVE' | 'ARCHIVED' | 'DECEASED'

/** Types de constantes vitales */
export type VitalType = 'FC' | 'TA_SYS' | 'TA_DIA' | 'SPO2' | 'TEMP' | 'GLYC' | 'POIDS' | 'DOULEUR'

/** Sources de mesure des constantes */
export type VitalSource = 'MANUAL' | 'DEVICE' | 'IMPORT' | 'PATIENT'

/** Types de documents générés */
export type DocumentType = 'PPA' | 'PPCS' | 'RECOMMENDATION' | 'OTHER'

/** Statuts d'une évaluation */
export type EvaluationStatus =
  | 'DRAFT'
  | 'IN_PROGRESS'
  | 'PENDING_MEDICAL'
  | 'PENDING_DEPARTMENT'
  | 'VALIDATED'

/** Types d'accès RGPD */
export type PatientAccessType = 'READ' | 'WRITE' | 'FULL'

// =============================================================================
// PATIENT
// =============================================================================

/** Patient - Version résumée pour les listes */
export interface PatientSummary {
  id: number
  first_name?: string
  last_name?: string
  birth_date?: string
  status: PatientStatus
  entity_id: number
  current_gir?: number
  created_at: string
}

/** Patient - Version complète */
export interface PatientResponse extends PatientSummary {
  nir?: string
  ins?: string
  address?: string
  phone?: string
  email?: string
  medecin_traitant_id?: number
  latitude?: number
  longitude?: number
  updated_at?: string
  entity_name?: string
  evaluations?: PatientEvaluationResponse[]
}

/** Patient - Création */
export interface PatientCreate {
  first_name?: string
  last_name?: string
  birth_date?: string
  nir?: string
  ins?: string
  address?: string
  phone?: string
  email?: string
  entity_id: number
  medecin_traitant_id?: number
  latitude?: number
  longitude?: number
}

/** Patient - Mise à jour */
export interface PatientUpdate {
  first_name?: string
  last_name?: string
  birth_date?: string
  nir?: string
  ins?: string
  address?: string
  phone?: string
  email?: string
  medecin_traitant_id?: number
  latitude?: number
  longitude?: number
  status?: PatientStatus
}

/** Liste paginée de patients */
export interface PatientList {
  items: PatientSummary[]
  total: number
  page: number
  size: number
  pages: number
}

/**
 * Paramètres de requête pour la liste patients (admin)
 *
 * 🆕 Sprint 7 — Même pattern que UserQueryParams
 * Correspond aux query params acceptés par GET /patients
 */
export interface PatientQueryParams {
  page?: number
  size?: number
  search?: string
  entity_id?: number
  status?: PatientStatus
  gir_min?: number
  gir_max?: number
  medecin_traitant_id?: number
}

// =============================================================================
// EVALUATION
// =============================================================================

/** Évaluation patient (AGGIR, etc.) */
export interface PatientEvaluationResponse {
  id: number
  patient_id: number
  evaluator_id: number
  schema_type: string
  schema_version: string
  evaluation_data: Record<string, unknown>
  evaluation_date: string
  status: EvaluationStatus
  completion_percent: number
  gir_score?: number
  expires_at?: string
  days_until_expiration?: number
  validated_at?: string
  validated_by?: number
  medical_validated_at?: string
  medical_validated_by?: number
  department_validated_at?: string
  department_validator_name?: string
  department_reference?: string
  created_at: string
  updated_at?: string
}

/** Création d'une évaluation */
export interface PatientEvaluationCreate {
  schema_type: string
  schema_version?: string
  evaluation_data: Record<string, unknown>
  evaluation_date: string
}

/** Mise à jour d'une évaluation */
export interface PatientEvaluationUpdate {
  evaluation_data?: Record<string, unknown>
  aggir_variable_code?: string
  aggir_variable_data?: Record<string, unknown>
}

/** Liste paginée d'évaluations */
export interface PatientEvaluationList {
  items: PatientEvaluationResponse[]
  total: number
  page: number
  size: number
  pages: number
}

/** Session de saisie d'évaluation (multi-jours) */
export interface EvaluationSessionResponse {
  id: number
  evaluation_id: number
  user_id: number
  started_at: string
  ended_at?: string
  device_info?: string
  local_session_id?: string
  changes_count: number
  is_active: boolean
}

// =============================================================================
// VITALS (CONSTANTES)
// =============================================================================

/** Mesure de constante vitale */
export interface PatientVitalsResponse {
  id: number
  patient_id: number
  vital_type: VitalType
  value: number
  unit: string
  source: VitalSource
  measured_at: string
  status?: string
  device_id?: number
  recorded_by?: number
  is_manual: boolean
  is_abnormal: boolean
  is_critical: boolean
  notes?: string
  created_at: string
}

/** Création d'une mesure */
export interface PatientVitalsCreate {
  vital_type: VitalType
  value: number
  unit: string
  source?: VitalSource
  measured_at: string
  notes?: string
  device_id?: number
}

/** Liste paginée de mesures */
export interface PatientVitalsList {
  items: PatientVitalsResponse[]
  total: number
  page: number
  size: number
  pages: number
}

// =============================================================================
// THRESHOLD (SEUILS)
// =============================================================================

/** Seuil personnalisé de constante */
export interface PatientThresholdResponse {
  id: number
  patient_id: number
  vital_type: VitalType
  min_value?: number
  max_value?: number
  min_critical?: number
  max_critical?: number
  created_at: string
  updated_at?: string
}

/** Création d'un seuil */
export interface PatientThresholdCreate {
  vital_type: VitalType
  min_value?: number
  max_value?: number
  min_critical?: number
  max_critical?: number
}

// =============================================================================
// ACCESS (RGPD)
// =============================================================================

/** Accès à un dossier patient */
export interface PatientAccessResponse {
  id: number
  patient_id: number
  user_id: number
  access_type: PatientAccessType
  reason: string
  granted_by: number
  granted_at: string
  expires_at?: string
  revoked_at?: string
  revoked_by?: number
  is_active: boolean
  is_expired: boolean
  is_revoked: boolean
}

// =============================================================================
// DOCUMENT
// =============================================================================

/** Document généré (PPA, PPCS) */
export interface PatientDocumentResponse {
  id: number
  patient_id: number
  document_type: DocumentType
  title: string
  description?: string
  source_evaluation_id?: number
  file_path: string
  file_format: string
  file_size_bytes?: number
  generated_at: string
  generated_by: number
  is_ppa: boolean
  is_ppcs: boolean
  is_recommendation: boolean
  created_at: string
}

// =============================================================================
// FILTERS
// =============================================================================

/** Filtres pour la recherche de patients */
export interface PatientFilters {
  entity_id?: number
  status?: PatientStatus
  medecin_traitant_id?: number
  gir_min?: number
  gir_max?: number
  search?: string
}