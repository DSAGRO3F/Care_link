/**
 * Détermine la route par défaut selon les permissions effectives.
 *
 * Logique d'aiguillage (B48 Palier 4 / 4c) :
 *   - `ADMIN_FULL` présent  → /admin (Admin Client)
 *   - sinon                 → /soins (Soignant)
 *
 * Iso-comportement avec la logique pré-4c basée sur `is_admin` :
 * un user `is_admin=True` a toujours `ADMIN_FULL` dans ses permissions
 * effectives (rôle ADMIN attribué + court-circuit ADMIN_FULL côté
 * backend, cf. backend_spec §8.1). Bascule de lecture de donnée, pas
 * de logique métier.
 *
 * Destination : src/utils/routing.ts
 */
import type { AuthenticatedUser } from '@/types';

/**
 * Retourne la route par défaut (URL) pour un utilisateur authentifié.
 */
export function getDefaultRoute(user: AuthenticatedUser | null): string {
  if (!user) return '/login';

  // ADMIN_FULL court-circuite (cf. backend_spec §8.1)
  if (user.effective_permissions?.includes('ADMIN_FULL')) {
    return '/admin';
  }

  // Sinon, l'écran d'accueil par défaut est le dashboard Soins
  return '/soins';
}

/**
 * Retourne le nom de route par défaut (pour router.push({ name: ... }))
 */
export function getDefaultRouteName(user: AuthenticatedUser | null): string {
  if (!user) return 'login';

  if (user.effective_permissions?.includes('ADMIN_FULL')) {
    return 'admin-dashboard';
  }

  return 'soins-dashboard';
}