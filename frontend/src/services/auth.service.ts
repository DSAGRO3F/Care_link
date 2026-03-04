/**
 * Service d'authentification
 * Gère les appels API pour PSC, login local, refresh token
 */
import api from './api'
import type {
  LoginRequest,
  LoginResponse,
  TokenResponse,
  AuthenticatedUser,
  AuthStatusResponse,
  PSCAuthorizationResponse,
} from '@/types'

// =============================================================================
// AUTH SERVICE
// =============================================================================

export const authService = {
  /**
   * Connexion email/mot de passe
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>('/auth/login', credentials)
    return response.data
  },

  /**
   * Obtenir l'URL d'autorisation PSC (pour SPA)
   */
  async getPSCLoginUrl(redirectAfter?: string): Promise<PSCAuthorizationResponse> {
    const params = redirectAfter ? { redirect_after: redirectAfter } : {}
    const response = await api.get<PSCAuthorizationResponse>('/auth/psc/login-url', { params })
    return response.data
  },

  /**
   * Callback PSC - échange le code contre des tokens
   */
  async pscCallback(code: string, state: string): Promise<LoginResponse> {
    const response = await api.get<LoginResponse>('/auth/psc/callback', {
      params: { code, state },
    })
    return response.data
  },

  /**
   * Renouveler les tokens avec le refresh token
   */
  async refresh(refreshToken: string): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },

  /**
   * Récupérer l'utilisateur courant
   */
  async getMe(): Promise<AuthenticatedUser> {
    const response = await api.get<AuthenticatedUser>('/auth/me')
    return response.data
  },

  /**
  * Forcer le changement de mot de passe après 1ère auth.
   */
   async changePassword(currentPassword: string, newPassword: string): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
    })
    return response.data
   },

  /**
   * Vérifier le statut d'authentification et la config PSC
   */
  async getStatus(): Promise<AuthStatusResponse> {
    const response = await api.get<AuthStatusResponse>('/auth/status')
    return response.data
  },

  /**
   * Déconnexion (côté serveur)
   */
  async logout(): Promise<void> {
    await api.post('/auth/logout')
  },
}

export default authService
