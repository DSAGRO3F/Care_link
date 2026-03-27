/**
 * Types pour le module d'authentification
 * Correspond aux schemas Pydantic backend: app/api/v1/auth/schemas.py
 *
 * 🔧 S4.1 : Ajout tenant_code dans LoginRequest, must_change_password dans AuthenticatedUser
 */

// =============================================================================
// ENUMS
// =============================================================================

/** Méthodes d'authentification supportées */
export type AuthMethod = 'psc' | 'password';

/** Types d'accès aux données patient (RGPD) */
export type AccessType = 'READ' | 'WRITE' | 'FULL';

// =============================================================================
// REQUESTS
// =============================================================================

/** Requête de connexion email/mot de passe */
export interface LoginRequest {
  tenant_code: string;
  email: string;
  password: string;
}

/** Requête de refresh token */
export interface RefreshTokenRequest {
  refresh_token: string;
}

/** Requête de changement de mot de passe */
export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

// =============================================================================
// RESPONSES
// =============================================================================

/** Tokens JWT retournés après authentification */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

/** Informations de l'utilisateur authentifié */
export interface AuthenticatedUser {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  rpps?: string;
  profession?: string;
  speciality?: string;
  roles: string[];
  is_admin: boolean;
  must_change_password: boolean;
  tenant_id: number;
}

/** Réponse complète après login réussi */
export interface LoginResponse {
  user: AuthenticatedUser;
  tokens: TokenResponse;
  auth_method: AuthMethod;
}

/** Statut de configuration de l'authentification */
export interface AuthStatusResponse {
  authenticated: boolean;
  user?: AuthenticatedUser;
  psc_configured: boolean;
  psc_environment: string;
}

/** URL d'autorisation PSC */
export interface PSCAuthorizationResponse {
  authorization_url: string;
  state: string;
}

// =============================================================================
// JWT PAYLOAD
// =============================================================================

/** Payload décodé d'un token JWT CareLink */
export interface TokenPayload {
  sub: string;
  type: 'access' | 'refresh';
  exp: number;
  iat: number;
  iss: string;
  rpps?: string;
  email?: string;
  roles: string[];
  tenant_id?: number;
  is_admin: boolean;
}

// =============================================================================
// ERRORS
// =============================================================================

/** Réponse d'erreur d'authentification */
export interface AuthErrorResponse {
  error: string;
  error_description: string;
  detail?: string;
}
