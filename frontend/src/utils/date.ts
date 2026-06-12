/**
 * Utilitaires de calcul sur les dates.
 *
 * Distinct de `format.ts`, qui ne fait que de la *présentation* i18n : ici on
 * calcule (différences, âges…), on ne formate pas.
 *
 * 🆕 B48 Palier 2 (Lot 0) — `computeAge` extrait ici lors de la consolidation
 *    des helpers dupliqués des pages patient.
 */

/**
 * Calcule l'âge en années révolues à partir d'une date de naissance.
 *
 * Algorithme calendaire exact : différence d'années ajustée du mois et du jour.
 * On n'utilise PAS une division en millisecondes (`/ 365.25j`), qui dérive d'un
 * an autour de la date anniversaire.
 *
 * Accepte une `Date`, une chaîne ISO 8601, ou `null`/`undefined`.
 *
 * @returns l'âge en années, ou `null` si la date est absente ou invalide.
 */
export function computeAge(birthDate: string | Date | null | undefined): number | null {
  if (birthDate === null || birthDate === undefined || birthDate === '') return null;

  const birth = birthDate instanceof Date ? birthDate : new Date(birthDate);
  if (Number.isNaN(birth.getTime())) return null;

  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age -= 1;
  }
  return age;
}