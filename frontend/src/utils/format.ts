/**
 * Utilitaires de formatage internationalisé (monnaie, date, pourcentage).
 *
 * Justification de la centralisation
 * ----------------------------------
 * 1. **Cohérence typographique** : un seul lieu décide du séparateur décimal,
 *    de la position du symbole monétaire, et de l'espacement (insécable en FR).
 * 2. **Anticipation i18n** : CareLink vise l'international à terme. La bascule
 *    de locale se fera ici, sans toucher aux composants appelants.
 * 3. **Suppression des `.toFixed()` ad-hoc** : `Intl.NumberFormat` gère
 *    correctement l'arrondi et la pluralisation, contrairement à `.toFixed()`.
 *
 * Locales supportées (au 29/04/2026)
 * ----------------------------------
 * - `'fr-FR'` (par défaut) : "1 234,50 €", "29/04/2026", "12,5 %"
 * - `'en-US'`              : "$1,234.50",  "4/29/2026",  "12.5%"
 *
 * Pour ajouter une locale (ex. `'de-DE'`) : étendre le type `SupportedLocale`,
 * vérifier que `Intl` la supporte (cas général : oui), et tester les rendus.
 *
 * Convention `formatPercent`
 * --------------------------
 * La valeur passée est déjà exprimée en pourcentage (ex. `12.5` pour 12,5 %),
 * **pas** une fraction (`0.125`). Cohérent avec les valeurs métier CareLink
 * (`budgetPercent`, taux GIR, etc. qui sont déjà des pourcentages).
 */

/** Locales supportées. Étendre ce type pour ajouter une locale. */
export type SupportedLocale = 'fr-FR' | 'en-US';

/**
 * Locale par défaut. Source de vérité unique — la bascule i18n future passera
 * par cette constante (probablement remplacée par un store / i18n provider).
 */
export const DEFAULT_LOCALE: SupportedLocale = 'fr-FR';

/**
 * Codes de devise associés à chaque locale. ISO 4217.
 * Étendre lors de l'ajout d'une locale.
 */
const CURRENCY_BY_LOCALE: Record<SupportedLocale, string> = {
  'fr-FR': 'EUR',
  'en-US': 'USD',
};

// ---------------------------------------------------------------------------
// Monnaie
// ---------------------------------------------------------------------------

export interface FormatCurrencyOptions {
  /** Nombre de décimales affichées. Défaut : 2. */
  decimals?: number;
  /** Locale forcée. Défaut : `DEFAULT_LOCALE`. */
  locale?: SupportedLocale;
}

/**
 * Formate un montant monétaire selon la locale (devise locale automatique).
 *
 * @example
 * formatCurrency(1234.5)                    // "1 234,50 €"      (fr-FR par défaut)
 * formatCurrency(1234.5, { decimals: 0 })   // "1 235 €"
 * formatCurrency(1234.5, { locale: 'en-US' }) // "$1,234.50"
 */
export function formatCurrency(value: number, options: FormatCurrencyOptions = {}): string {
  const locale = options.locale ?? DEFAULT_LOCALE;
  const decimals = options.decimals ?? 2;
  const currency = CURRENCY_BY_LOCALE[locale];

  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Alias historique de `formatCurrency` pour la lisibilité du code appelant
 * en contexte FR. À l'usage, préférer `formatCurrency` pour le code i18n-aware
 * et `formatEuro` pour le code franco-centré.
 *
 * @example
 * formatEuro(1234.5)                  // "1 234,50 €"
 * formatEuro(1234, { decimals: 0 })   // "1 234 €"
 */
export const formatEuro = formatCurrency;

// ---------------------------------------------------------------------------
// Date
// ---------------------------------------------------------------------------

export type DateStyle = 'short' | 'medium' | 'long';

export interface FormatDateOptions {
  /**
   * Style d'affichage.
   * - `'short'` (défaut) : "29/04/2026" (FR), "4/29/2026" (US)
   * - `'medium'`         : "29 avr. 2026" (FR) — jour + mois abrégé + année
   * - `'long'`           : "29 avril 2026" (FR), "April 29, 2026" (US)
   */
  style?: DateStyle;
  /** Locale forcée. Défaut : `DEFAULT_LOCALE`. */
  locale?: SupportedLocale;
  /**
   * Valeur retournée lorsque la date est absente (`null`/`undefined`/`''`)
   * ou invalide. Défaut : `''`.
   *
   * 🆕 B48 Palier 2 (Lot 0) — permet aux fiches patient d'afficher un tiret
   * « — » (convention « champ vide » du dossier médical) sans réintroduire un
   * `formatDate` ad-hoc par page. Ex. : `formatDate(d, { emptyValue: '—' })`.
   */
  emptyValue?: string;
}

/**
 * Formate une date selon la locale.
 *
 * Accepte les formats d'entrée suivants :
 * - `Date` JS
 * - chaîne ISO 8601 (ex. `"2026-04-29"` ou `"2026-04-29T10:30:00Z"`)
 * - timestamp numérique (ms depuis epoch)
 *
 * Retourne une chaîne vide si la valeur est `null`, `undefined`, ou invalide.
 *
 * @example
 * formatDate('2026-04-29')                          // "29/04/2026"
 * formatDate('2026-04-29', { style: 'medium' })     // "29 avr. 2026"
 * formatDate('2026-04-29', { style: 'long' })       // "29 avril 2026"
 * formatDate(new Date(), { locale: 'en-US' })       // "4/29/2026"
 */
export function formatDate(
  value: Date | string | number | null | undefined,
  options: FormatDateOptions = {},
): string {
  const emptyValue = options.emptyValue ?? '';
  if (value === null || value === undefined || value === '') return emptyValue;

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return emptyValue;

  const locale = options.locale ?? DEFAULT_LOCALE;
  const style = options.style ?? 'short';

  const formatOptions: Intl.DateTimeFormatOptions =
    style === 'long'
      ? { day: 'numeric', month: 'long', year: 'numeric' }
      : style === 'medium'
        ? { day: '2-digit', month: 'short', year: 'numeric' }
        : { day: '2-digit', month: '2-digit', year: 'numeric' };

  return new Intl.DateTimeFormat(locale, formatOptions).format(date);
}

// ---------------------------------------------------------------------------
// Pourcentage
// ---------------------------------------------------------------------------

export interface FormatPercentOptions {
  /** Nombre de décimales affichées. Défaut : 0. */
  decimals?: number;
  /** Locale forcée. Défaut : `DEFAULT_LOCALE`. */
  locale?: SupportedLocale;
}

/**
 * Formate un pourcentage selon la locale.
 *
 * **Convention d'entrée** : la valeur est déjà en pourcentage (`12.5` → "12,5 %"),
 * pas une fraction (`0.125`). Cohérent avec les valeurs métier CareLink.
 *
 * Note : `Intl.NumberFormat` avec `style: 'percent'` attend une fraction et
 * la multiplie par 100. On utilise donc `style: 'decimal'` + suffixe manuel
 * pour respecter notre convention d'entrée.
 *
 * @example
 * formatPercent(12.5)                       // "12 %"        (0 décimale par défaut)
 * formatPercent(12.5, { decimals: 1 })      // "12,5 %"
 * formatPercent(150, { locale: 'en-US' })   // "150%"
 */
export function formatPercent(value: number, options: FormatPercentOptions = {}): string {
  const locale = options.locale ?? DEFAULT_LOCALE;
  const decimals = options.decimals ?? 0;

  const formatted = new Intl.NumberFormat(locale, {
    style: 'decimal',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);

  // FR utilise une espace insécable avant le %, US colle le symbole.
  const separator = locale === 'fr-FR' ? '\u00A0' : '';
  return `${formatted}${separator}%`;
}
// ---------------------------------------------------------------------------
// Date relative
// ---------------------------------------------------------------------------

export interface FormatRelativeTimeOptions {
  /** Locale forcée. Défaut : `DEFAULT_LOCALE`. */
  locale?: SupportedLocale;
  /**
   * Seuil (en jours) au-delà duquel on bascule sur une date absolue via
   * `formatDate`. Défaut : 30.
   */
  absoluteAfterDays?: number;
  /** Style de la date absolue de repli (cf. `FormatDateOptions.style`). Défaut : `'medium'`. */
  fallbackStyle?: DateStyle;
  /**
   * Valeur retournée lorsque la date est absente (`null`/`undefined`/`''`) ou
   * invalide. Défaut : `''`.
   */
  emptyValue?: string;
}

/**
 * Formate un horodatage en libellé relatif (« il y a 5 min », « dans 2 jours »),
 * avec repli sur une date absolue au-delà d'un seuil (`absoluteAfterDays`).
 *
 * Accepte les mêmes formats d'entrée que `formatDate` :
 * - `Date` JS
 * - chaîne ISO 8601 (ex. `"2026-04-29T10:30:00Z"`)
 * - timestamp numérique (ms depuis epoch)
 *
 * Retourne `emptyValue` si la valeur est `null`, `undefined`, `''` ou invalide.
 *
 * Note : `Intl.RelativeTimeFormat` n'a pas de notion de seuil — au-delà de
 * `absoluteAfterDays`, « il y a 312 jours » serait illisible, d'où le repli sur
 * `formatDate` (source unique du formatage de date absolue, cohérence garantie).
 *
 * @example
 * formatRelativeTime('2026-04-29T10:30:00Z')              // "il y a 5 min"
 * formatRelativeTime(d, { absoluteAfterDays: 7 })         // bascule en date au-delà de 7 j
 * formatRelativeTime(null, { emptyValue: '—' })           // "—"
 */
export function formatRelativeTime(
  value: Date | string | number | null | undefined,
  options: FormatRelativeTimeOptions = {},
): string {
  const emptyValue = options.emptyValue ?? '';
  if (value === null || value === undefined || value === '') return emptyValue;

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return emptyValue;

  const locale = options.locale ?? DEFAULT_LOCALE;
  const absoluteAfterDays = options.absoluteAfterDays ?? 30;
  const fallbackStyle = options.fallbackStyle ?? 'medium';

  const diffSec = Math.round((date.getTime() - Date.now()) / 1000); // < 0 pour le passé
  const abs = Math.abs(diffSec);

  if (abs >= absoluteAfterDays * 86400) {
    return formatDate(date, { style: fallbackStyle, locale });
  }

  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
  if (abs < 60) return rtf.format(diffSec, 'second');
  if (abs < 3600) return rtf.format(Math.round(diffSec / 60), 'minute');
  if (abs < 86400) return rtf.format(Math.round(diffSec / 3600), 'hour');
  return rtf.format(Math.round(diffSec / 86400), 'day');
}
