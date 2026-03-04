/**
 * Utilitaires d'authentification Platform (SuperAdmin)
 *
 * Contient les fonctions PURES (sans effet de bord sur le state).
 * Les actions à effet de bord (login, logout) sont dans platform.store.ts.
 */

/**
 * Décode un token JWT (sans vérification de signature côté client)
 */
export function decodeJwt(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null

    const payload = parts[1]
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded)
  } catch {
    return null
  }
}

/**
 * Vérifie si un token est un token SuperAdmin valide (non expiré)
 */
export function isSuperAdminToken(token: string | null): boolean {
  if (!token) return false

  const payload = decodeJwt(token)
  if (!payload) return false

  // Vérifier le type
  if (payload.type !== 'super_admin') return false

  // Vérifier l'expiration
  const exp = payload.exp as number
  if (!exp) return false

  const now = Math.floor(Date.now() / 1000)
  if (exp < now) return false

  return true
}

/**
 * Récupère les infos du SuperAdmin depuis le token
 */
export function getSuperAdminFromToken(token: string | null): {
  id: number
  email: string
  role: string
} | null {
  if (!token) return null

  const payload = decodeJwt(token)
  if (!payload || payload.type !== 'super_admin') return null

  return {
    id: parseInt(payload.sub as string, 10),
    email: payload.email as string,
    role: payload.role as string,
  }
}

/**
 * Vérifie si l'utilisateur est authentifié en tant que SuperAdmin
 */
export function isAuthenticatedAsSuperAdmin(): boolean {
  const token = localStorage.getItem('platform_access_token')
  return isSuperAdminToken(token)
}