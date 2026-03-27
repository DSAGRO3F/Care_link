/**
 * Utilitaires de validation partagés
 * Utilisés par les formulaires TenantCreate, TenantDetail, etc.
 */

/** Regex email basique mais suffisante pour validation inline */
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Vérifie qu'une chaîne est un email valide */
export function isValidEmail(value: string): boolean {
  return EMAIL_REGEX.test(value.trim());
}
