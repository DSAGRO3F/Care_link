/**
 * Types UI transverses — primitives de présentation non rattachées à un
 * domaine métier (patient, plan d'aide, évaluation…).
 *
 * 🆕 B48 Palier 2 (Lot 0) — `TagSeverity` extrait ici lors de la consolidation
 *    des helpers de statut. La severity PrimeVue est du vocabulaire UI, pas une
 *    donnée de domaine : ne pas la loger dans `patient.ts` ni `careplan.ts`
 *    (règle « jamais de données cross-domaine », plan Palier 2 §3 Lot 0).
 */

/**
 * Severity d'un composant `Tag` PrimeVue 4 (thème Aura). Union fermée des
 * valeurs acceptées par la prop `severity`.
 */
export type TagSeverity = 'success' | 'info' | 'warn' | 'danger' | 'secondary' | 'contrast';