/**
 * Client API Axios configuré pour CareLink
 * - Intercepteurs pour injection automatique du token JWT
 * - Refresh automatique du token expiré
 * - Gestion centralisée des erreurs
 */
import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'

// =============================================================================
// CONFIGURATION
// =============================================================================

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
const API_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT) || 30000

// =============================================================================
// INSTANCE AXIOS
// =============================================================================

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
})

// =============================================================================
// INTERCEPTEUR REQUEST - Injection du token JWT
// =============================================================================

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Circuit Platform → platform_access_token
    // Circuit Métier   → access_token
    const isPlatformRequest = config.url?.startsWith('/platform/')
    const tokenKey = isPlatformRequest ? 'platform_access_token' : 'access_token'
    const token = localStorage.getItem(tokenKey)
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  (error) => Promise.reject(error)
)

// =============================================================================
// INTERCEPTEUR RESPONSE - Gestion erreurs et refresh token
// =============================================================================

let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

// Traite la queue des requêtes en attente après refresh
const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error)
    } else if (token) {
      promise.resolve(token)
    }
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    // Si erreur 401 et pas déjà en retry
    if (error.response?.status === 401 && !originalRequest._retry) {
      
      // Si déjà en train de refresh, mettre en queue
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`
            }
            return api(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      // const refreshToken = localStorage.getItem('refresh_token')
      const isPlatformRequest = originalRequest.url?.startsWith('/platform/')
      const refreshKey = isPlatformRequest ? 'platform_refresh_token' : 'refresh_token'
      const refreshToken = localStorage.getItem(refreshKey)

      if (!refreshToken) {
        // Pas de refresh token → déconnexion
        if (isPlatformRequest) {
          localStorage.removeItem('platform_access_token')
          localStorage.removeItem('platform_refresh_token')
          window.location.href = '/platform/login'
        } else {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }

      try {
        // Appel refresh token
         const refreshUrl = isPlatformRequest
           ? `${API_BASE_URL}/platform/auth/refresh`
           : `${API_BASE_URL}/auth/refresh`
         const response = await axios.post(refreshUrl, {
           refresh_token: refreshToken,
        })

        const { access_token, refresh_token: newRefreshToken } = response.data

        // Stocker les nouveaux tokens
        const accessKey = isPlatformRequest ? 'platform_access_token' : 'access_token'
        const newRefreshKey = isPlatformRequest ? 'platform_refresh_token' : 'refresh_token'
        localStorage.setItem(accessKey, access_token)
        localStorage.setItem(newRefreshKey, newRefreshToken)


        // Mettre à jour le header de la requête originale
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`
        }

        // Traiter la queue
        processQueue(null, access_token)

        return api(originalRequest)
      } catch (refreshError) {
        // Refresh échoué → déconnexion
        processQueue(refreshError, null)
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

// =============================================================================
// EXPORT
// =============================================================================

export default api

/** Helper pour extraire le message d'erreur */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.message || 'Erreur inconnue'
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Erreur inconnue'
}
