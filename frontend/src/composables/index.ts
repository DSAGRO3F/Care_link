/**
 * CareLink - Barrel export des composables
 * Chemin : frontend/src/composables/index.ts
 */

// Evaluation — formatage (visualisation)
export { useEvaluationFormatter } from './useEvaluationFormatter';

// Evaluation — wizard (saisie)
export { useEvaluationWizard } from './useEvaluationWizard';
export type {
  WizardSectionConfig,
  SectionState,
  SectionStatus,
  WizardState,
} from './useEvaluationWizard';
