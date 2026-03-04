/**
 * Détermine la route par défaut selon le profil utilisateur.
 *
 * Logique d'aiguillage :
 *   - is_admin=true sans profession → /admin  (Admin Client = syndic)
 *   - profession renseignée (RPPS)  → /soins  (Soignant = résident)
 *   - is_admin=true avec profession → /admin  (Admin qui est aussi soignant → admin d'abord)
 *   - fallback                      → /soins  (sécurité)
 *
 * Destination : src/utils/routing.ts
 */
import type { AuthenticatedUser } from '@/types'

/**
 * Retourne la route par défaut pour un utilisateur authentifié.
 */
export function getDefaultRoute(user: AuthenticatedUser | null): string {
  if (!user) return '/login'

  // Admin client (provisionné par SuperAdmin) → espace admin
  if (user.is_admin) {
    return '/admin'
  }

  // Professionnel de santé (avec ou sans RPPS) → espace soins
  // C'est aussi le fallback par défaut
  return '/soins'
}

/**
 * Retourne le nom de route par défaut (pour router.push({ name: ... }))
 */
export function getDefaultRouteName(user: AuthenticatedUser | null): string {
  if (!user) return 'login'

  if (user.is_admin) {
    return 'admin-dashboard'
  }

  return 'soins-dashboard'
}