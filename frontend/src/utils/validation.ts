/**
 * Utilitaires de validation partagés
 * Utilisés par les formulaires TenantCreate, TenantDetail, etc.
 */

/**
 * Regex email stricte :
 * - Partie locale : tout sauf espace et @
 * - Domaine : labels séparés par des points, pas de point en début/fin
 * - TLD obligatoirement composé de lettres, au moins 2 caractères, ancré en fin
 *   de chaîne (l'ancre $ interdit tout caractère après — notamment un point final)
 *
 * Rejette notamment :
 * - contact@foo.fr.      (point final)
 * - contact@foo          (pas de TLD)
 * - contact@foo.f        (TLD 1 caractère)
 * - contact@foo.123      (TLD numérique)
 * - contact@foo..fr      (double point)
 *
 * Durcissement suite à incident 13/04/2026 (cf. session de clôture BLOQUANT 1).
 */
const EMAIL_REGEX = /^[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)*\.[a-zA-Z]{2,}$/;

/** Vérifie qu'une chaîne est un email valide. Applique un trim() avant le test. */
export function isValidEmail(value: string): boolean {
  return EMAIL_REGEX.test(value.trim());
}
