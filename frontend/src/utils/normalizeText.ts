/**
 * CareLink — Normalisation de texte (anti-homoglyphes Unicode)
 * Chemin : frontend/src/utils/normalizeText.ts
 *
 * Pourquoi ce module existe
 * -------------------------
 * Quand un utilisateur copie-colle une valeur depuis un site web, un PDF ou
 * un document Word, des caractères Unicode visuellement identiques aux
 * caractères ASCII peuvent se glisser sans qu'il s'en rende compte. Exemples
 * observés en production :
 *   • U+2212 MINUS SIGN « − » (math) au lieu de U+002D HYPHEN-MINUS « - »
 *     → email refusé par Pydantic email-validator (strict ASCII sur le domain)
 *   • U+2013 EN DASH « – » et U+2014 EM DASH « — » (auto-correct Word)
 *   • U+2019 RIGHT SINGLE QUOTATION MARK « ’ » au lieu de U+0027 « ' »
 *   • U+00A0 NO-BREAK SPACE au lieu de l'espace ordinaire
 *
 * Le bug initial (15/04/2026) : un email `aidesccas@ville−gennevilliers.fr`
 * collé depuis un site municipal contenait U+2212 dans le domaine, refusé en
 * 422 par le backend.
 *
 * Stratégie
 * ---------
 * Nous normalisons systématiquement à la saisie (@blur sur les inputs) ET au
 * submit (filet de sécurité). Le périmètre couvre les champs où ces
 * caractères posent un problème technique (email, téléphone) ou augmentent
 * le bruit en base (adresse). Les noms propres (name, legal_name) sont
 * volontairement exclus pour préserver la fidélité de la saisie.
 *
 * Ce module n'effectue PAS de validation : il transforme. La validation
 * format reste à la charge de @/utils/validation (isValidEmail) et du
 * backend Pydantic.
 */

// =============================================================================
// CARTOGRAPHIE DES HOMOGLYPHES
// =============================================================================

/**
 * Variantes Unicode du tiret/trait d'union à normaliser vers U+002D (« - »).
 *   • U+2010 HYPHEN
 *   • U+2011 NON-BREAKING HYPHEN
 *   • U+2012 FIGURE DASH
 *   • U+2013 EN DASH (auto-correct Word)
 *   • U+2014 EM DASH (auto-correct Word, typographie française)
 *   • U+2015 HORIZONTAL BAR
 *   • U+2212 MINUS SIGN (LaTeX, formules — bug initial)
 *   • U+FF0D FULLWIDTH HYPHEN-MINUS (sites CJK)
 */
const DASH_VARIANTS = /[\u2010\u2011\u2012\u2013\u2014\u2015\u2212\uFF0D]/g;

/**
 * Variantes Unicode de l'apostrophe à normaliser vers U+0027 (« ' »).
 *   • U+2018 LEFT SINGLE QUOTATION MARK
 *   • U+2019 RIGHT SINGLE QUOTATION MARK (auto-correct Word — le plus fréquent)
 *   • U+201B SINGLE HIGH-REVERSED-9 QUOTATION MARK
 *   • U+02BC MODIFIER LETTER APOSTROPHE
 *   • U+FF07 FULLWIDTH APOSTROPHE
 */
const APOSTROPHE_VARIANTS = /[\u2018\u2019\u201B\u02BC\uFF07]/g;

/**
 * Variantes d'espace à normaliser vers U+0020 (espace ordinaire).
 *   • U+00A0 NO-BREAK SPACE (le plus problématique : invisible mais présent)
 *   • U+2007 FIGURE SPACE
 *   • U+2009 THIN SPACE
 *   • U+202F NARROW NO-BREAK SPACE (typographie française avant ; : ! ?)
 *   • U+3000 IDEOGRAPHIC SPACE
 */
const SPACE_VARIANTS = /[\u00A0\u2007\u2009\u202F\u3000]/g;

// =============================================================================
// FONCTIONS PUBLIQUES
// =============================================================================

/**
 * Normalise les ponctuations Unicode courantes vers leurs équivalents ASCII.
 * Préserve les autres caractères (lettres accentuées, signes diacritiques,
 * etc.). Idempotente.
 *
 * @example
 *   normalizeAsciiPunctuation('ville−gennevilliers') // → 'ville-gennevilliers'
 *   normalizeAsciiPunctuation('o’connor')            // → "o'connor"
 *   normalizeAsciiPunctuation('Paris\u00A075008')    // → 'Paris 75008'
 */
export function normalizeAsciiPunctuation(s: string): string {
  return s
    .replace(DASH_VARIANTS, '-')
    .replace(APOSTROPHE_VARIANTS, "'")
    .replace(SPACE_VARIANTS, ' ');
}

/**
 * Normalise une adresse email :
 *   1. Trim des espaces de bord
 *   2. Normalisation des ponctuations Unicode (anti-homoglyphes)
 *   3. Lowercase de la partie domaine (RFC 5321 — case-insensitive)
 *
 * La partie locale (avant @) garde sa casse car techniquement elle peut être
 * sensible à la casse (RFC 5321 §2.4), même si en pratique tous les MTA
 * modernes la traitent en case-insensitive aussi.
 *
 * @example
 *   normalizeEmail(' Aides@Ville−Gennevilliers.FR ')
 *   // → 'Aides@ville-gennevilliers.fr'
 */
export function normalizeEmail(s: string): string {
  const cleaned = normalizeAsciiPunctuation(s.trim());
  const atIndex = cleaned.lastIndexOf('@');
  if (atIndex === -1) return cleaned;
  const local = cleaned.slice(0, atIndex);
  const domain = cleaned.slice(atIndex + 1).toLowerCase();
  return `${local}@${domain}`;
}

/**
 * Normalise un numéro de téléphone : trim + ponctuations Unicode.
 * Ne supprime PAS les espaces, points, parenthèses ou + : la mise en forme
 * (ex. « 01 40 85 65 81 ») est conservée car certains backends/affichages
 * la requièrent ou la préfèrent.
 *
 * @example
 *   normalizePhone(' 01–40–85–65–81 ') // → '01-40-85-65-81'
 */
export function normalizePhone(s: string): string {
  return normalizeAsciiPunctuation(s.trim());
}

/**
 * Normalise une adresse postale : trim + ponctuations Unicode.
 * Conserve la casse, les accents, et toute la structure.
 *
 * @example
 *   normalizeAddress(' 46–48 RUE CARNOT ') // → '46-48 RUE CARNOT'
 */
export function normalizeAddress(s: string): string {
  return normalizeAsciiPunctuation(s.trim());
}
