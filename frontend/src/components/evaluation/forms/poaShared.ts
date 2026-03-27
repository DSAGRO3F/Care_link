/**
 * CareLink - Types et référentiels partagés POA Social / POA Santé
 * Chemin : frontend/src/components/evaluation/forms/poaShared.ts
 *
 * Utilisé par : PoaSocialForm.vue, PoaSanteForm.vue, PoaProblemeCard.vue
 */
import type { SectionStatus } from '@/composables/useEvaluationWizard';
import { prefillDateParts, parseDateParts } from './dateHelpers';

// Ré-export pour les formulaires parents (sérialisation des actions)
export { joinDateParts } from './dateHelpers';

// ── Types ────────────────────────────────────────────────────────────

export interface PoaAction {
  nomAction: string;
  detailAction: string;
  personneChargeAction: string;
  dateDebutJour: string;
  dateDebutMois: string;
  dateDebutAnnee: string;
  dureeAction: string;
  recurrenceAction: string;
  momentJournee: string[];
}

export interface PoaProbleme {
  nomBloc: string;
  statut: string;
  problemePose: string;
  objectifs: string;
  preoccupationPatient: string;
  preoccupationProfessionel: string;
  planActions: PoaAction[];
  critereEvaluation: string;
  resultatActions: string;
  message: string;
}

// ── Référentiels ─────────────────────────────────────────────────────

export const STATUT_OPTIONS = [
  { label: 'Actif', value: 'Actif' },
  { label: 'Inactif', value: 'Inactif' },
];

export const PREOCCUPATION_OPTIONS = [
  { label: 'Élevée', value: 'Élevée' },
  { label: 'Assez élevée', value: 'Assez élevée' },
  { label: 'Moyenne', value: 'Moyenne' },
  { label: 'Assez faible', value: 'Assez faible' },
  { label: 'Faible', value: 'Faible' },
];

export const MOMENT_JOURNEE_OPTIONS = [
  'Lever',
  'Matin',
  'Midi',
  'Après-midi',
  'Soir',
  'Coucher',
  'Nuit',
];

// ── Fabriques ────────────────────────────────────────────────────────

export function createEmptyAction(): PoaAction {
  const { jour, mois, annee } = prefillDateParts();
  return {
    nomAction: '',
    detailAction: '',
    personneChargeAction: '',
    dateDebutJour: jour,
    dateDebutMois: mois,
    dateDebutAnnee: annee,
    dureeAction: '',
    recurrenceAction: '',
    momentJournee: [],
  };
}

export function createEmptyProbleme(nomBloc: string): PoaProbleme {
  return {
    nomBloc,
    statut: 'Actif',
    problemePose: '',
    objectifs: '',
    preoccupationPatient: '',
    preoccupationProfessionel: '',
    planActions: [],
    critereEvaluation: '',
    resultatActions: '',
    message: '',
  };
}

// ── Hydratation ──────────────────────────────────────────────────────

/** Extraction sûre d'une valeur string depuis un objet brut (narrowing unknown → string). */
function str(v: unknown, fallback = ''): string {
  return typeof v === 'string' ? v : fallback;
}

/**
 * Hydrate un objet brut (EvalSchema ou brouillon) vers un PoaProbleme typé.
 * Assure que tous les champs sont présents avec des valeurs par défaut.
 */
export function hydrateProbleme(raw: Record<string, unknown>): PoaProbleme {
  return {
    nomBloc: str(raw.nomBloc),
    statut: str(raw.statut, 'Actif'),
    problemePose: str(raw.problemePose),
    objectifs: str(raw.objectifs),
    preoccupationPatient: str(raw.preoccupationPatient),
    preoccupationProfessionel: str(raw.preoccupationProfessionel),
    planActions: Array.isArray(raw.planActions)
      ? raw.planActions.map(hydrateAction)
      : [],
    critereEvaluation: str(raw.critereEvaluation),
    resultatActions: str(raw.resultatActions),
    message: str(raw.message),
  };
}

export function hydrateAction(raw: Record<string, unknown>): PoaAction {
  const { jour, mois, annee } = parseDateParts(str(raw.dateDebutAction));
  return {
    nomAction: str(raw.nomAction),
    detailAction: str(raw.detailAction),
    personneChargeAction: str(raw.personneChargeAction),
    dateDebutJour: jour,
    dateDebutMois: mois,
    dateDebutAnnee: annee,
    dureeAction: str(raw.dureeAction),
    recurrenceAction: str(raw.recurrenceAction),
    momentJournee: Array.isArray(raw.momentJournee)
      ? (raw.momentJournee as string[])
      : [],
  };
}

// ── Calcul de statut partagé ─────────────────────────────────────────

/**
 * Calcul du statut de section POA (Social ou Santé).
 * Logique identique pour les deux sections.
 */
export function computePoaStatus(problemes: PoaProbleme[]): SectionStatus {
  const activeProblemes = problemes.filter((p) => p.statut === 'Actif');

  if (activeProblemes.length === 0) return 'empty';

  const hasContent = activeProblemes.some(
    (p) => p.problemePose.trim() !== '' || p.planActions.length > 0,
  );

  if (!hasContent) return 'empty';

  const allComplete = activeProblemes.every(
    (p) =>
      (p.problemePose.trim() === '' && p.planActions.length === 0) ||
      (p.problemePose.trim() !== '' &&
        p.planActions.length > 0 &&
        p.planActions.every((a) => a.nomAction.trim() !== '')),
  );

  return allComplete ? 'complete' : 'partial';
}