/**
 * utils/navigation.ts — Helpers de navigation factorisés (shell unique)
 *
 * 🔄 B48 Palier 5 (21/05/2026) — Factorisation du helper `isActive` + constante
 *   `ROOT_PATHS` initialement dupliqué entre `AppSidebar.vue` (desktop) et
 *   `AppBottomNav.vue` (mobile). La duplication était byte-pour-byte identique
 *   ; sa centralisation ici évite toute dérive future entre les deux shells.
 *
 * Cf. Convention #128 (CONVENTIONS — « shell unique : helpers de navigation
 * factorisés dans utils/navigation.ts »).
 *
 * Destination : src/utils/navigation.ts
 */

/**
 * Chemins racines des deux espaces applicatifs.
 *
 * Traités en exact-match dans `isRootActive` pour éviter le double-surlignage
 * de l'item racine (`/admin`, `/soins`) sur toutes ses sous-routes — sans
 * cette discrimination, `route.path.startsWith('/admin')` matcherait
 * également `/admin/patients`, `/admin/care-plans`, etc., et l'item « Tableau
 * de bord » resterait visuellement actif en permanence.
 */
export const ROOT_PATHS: readonly string[] = ['/admin', '/soins'];

/**
 * Détermine si un item de navigation doit être marqué comme actif.
 *
 * Règles :
 * - Pour un **chemin racine** (`/admin`, `/soins`) → exact-match (avec
 *   tolérance trailing slash) ; l'item n'est actif que sur la racine elle-même.
 * - Pour un **sous-chemin** (`/admin/patients`, `/soins/care-plans`, …) →
 *   match préfixe ; l'item reste actif sur `/admin/patients`, mais aussi
 *   `/admin/patients/7`, `/admin/patients/7/edit`, etc.
 *
 * @param currentPath Le chemin courant (`route.path` de Vue Router)
 * @param itemPath Le chemin de l'item de navigation à tester
 * @returns true si l'item doit être surligné comme actif
 */
export function isRootActive(currentPath: string, itemPath: string): boolean {
  if (ROOT_PATHS.includes(itemPath)) {
    return currentPath === itemPath || currentPath === itemPath + '/';
  }
  return currentPath === itemPath || currentPath.startsWith(itemPath + '/');
}