/**
 * Types génériques pour les appels API
 * Pagination, erreurs, réponses standardisées
 */

// =============================================================================
// PAGINATION
// =============================================================================

/** Paramètres de pagination */
export interface PaginationParams {
  page?: number
  size?: number
}

/** Réponse paginée générique */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

// =============================================================================
// API ERRORS
// =============================================================================

/** Erreur API standard */
export interface ApiError {
  detail: string
  status_code?: number
}

/** Erreur de validation (422) */
export interface ValidationError {
  detail: ValidationErrorDetail[]
}

export interface ValidationErrorDetail {
  loc: (string | number)[]
  msg: string
  type: string
}

// =============================================================================
// API STATE
// =============================================================================

/** État générique d'un appel API */
export interface ApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

/** État de liste avec pagination */
export interface ListState<T> extends ApiState<T[]> {
  total: number
  page: number
  pages: number
}
