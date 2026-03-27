/**
 * CareLink - Utilitaires dates partagés (champs 3-parts JJ / MM / AAAA)
 * Chemin : frontend/src/components/evaluation/forms/dateHelpers.ts
 *
 * Fournit les fonctions de parsing, jointure et pré-remplissage mois/année
 * pour le pattern « split date input » utilisé dans tous les formulaires
 * d'évaluation (POA Autonomie, POA Social, POA Santé, Dispositifs, Social, Santé).
 *
 * Format interne affiché : JJ / MM / AAAA (3 champs séparés)
 * Format sérialisé (émission) : ISO YYYY-MM-DD
 */

// ── Types ────────────────────────────────────────────────────────────

export interface DateParts {
  jour: string;
  mois: string;
  annee: string;
}

// ── Pré-remplissage ──────────────────────────────────────────────────

/**
 * Retourne le mois courant (2 chiffres, ex : "03").
 */
export function getCurrentMonth(): string {
  return String(new Date().getMonth() + 1).padStart(2, '0');
}

/**
 * Retourne l'année courante (4 chiffres, ex : "2026").
 */
export function getCurrentYear(): string {
  return String(new Date().getFullYear());
}

/**
 * Retourne un objet DateParts pré-rempli avec le mois et l'année courants.
 * Le jour reste vide (à saisir par l'utilisateur).
 */
export function prefillDateParts(): DateParts {
  return {
    jour: '',
    mois: getCurrentMonth(),
    annee: getCurrentYear(),
  };
}

/**
 * Retourne un objet DateParts entièrement vide (aucun pré-remplissage).
 */
export function emptyDateParts(): DateParts {
  return { jour: '', mois: '', annee: '' };
}

// ── Parsing ──────────────────────────────────────────────────────────

/**
 * Parse une date string (ISO `YYYY-MM-DD`, display `DD/MM/YYYY`,
 * ou native HTML `YYYY-MM-DD`) en 3 parties.
 *
 * Retourne des parties vides si la chaîne est vide ou non reconnue.
 */
export function parseDateParts(date: string): DateParts {
  if (!date) return emptyDateParts();

  // ISO : 2025-09-23
  if (date.includes('-') && date.length >= 10) {
    const [y, m, d] = date.split('-');
    return { jour: d ?? '', mois: m ?? '', annee: y ?? '' };
  }

  // Display : 23/09/2025
  if (date.includes('/')) {
    const [d, m, y] = date.split('/');
    return { jour: d ?? '', mois: m ?? '', annee: y ?? '' };
  }

  return emptyDateParts();
}

// ── Jointure / Sérialisation ─────────────────────────────────────────

/**
 * Reconstruit une date ISO `YYYY-MM-DD` à partir des 3 parties.
 * Retourne une chaîne vide si le jour OU le mois OU l'année manque
 * (date incomplète = non sérialisée).
 */
export function joinDateParts(jour: string, mois: string, annee: string): string {
  const j = jour.trim();
  const m = mois.trim();
  const a = annee.trim();
  if (!j || !m || !a) return '';
  return `${a.padStart(4, '0')}-${m.padStart(2, '0')}-${j.padStart(2, '0')}`;
}

/**
 * Raccourci : joinDateParts depuis un objet DateParts.
 */
export function joinDatePartsObj(parts: DateParts): string {
  return joinDateParts(parts.jour, parts.mois, parts.annee);
}
