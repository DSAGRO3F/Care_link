/**
 * CareLink - useEvaluationWizard
 * Chemin : frontend/src/composables/useEvaluationWizard.ts
 *
 * Rôle : Gestion d'état du wizard de saisie d'évaluation.
 *        Navigation entre sections, suivi de complétion,
 *        sauvegarde brouillon et soumission.
 */
import { ref, reactive, computed, type Ref } from 'vue'
import { evaluationService } from '@/services'

// =============================================================================
// TYPES
// =============================================================================

export type SectionStatus = 'empty' | 'partial' | 'complete'

export interface WizardSectionConfig {
  /** Clé technique (correspond aux clés du JSON evaluation_data) */
  id: string
  /** Label affiché */
  label: string
  /** Description courte sous le label */
  subtitle: string
  /** Nom du composant icône Lucide (résolu par WizardSectionNav) */
  icon: string
  /** Suffixe de la classe CSS wizard-icon--{colorClass} */
  colorClass: string
  /** Obligatoire pour la soumission (validation complète) */
  requiredForSubmit: boolean
}

export interface SectionState {
  status: SectionStatus
  /** Données du formulaire pour cette section */
  data: Record<string, any>
}

export interface WizardState {
  /** ID de l'évaluation (null si création en cours) */
  evaluationId: number | null
  /** ID du patient */
  patientId: number
  /** Statut global de l'évaluation */
  evaluationStatus: 'DRAFT' | 'SUBMITTED' | 'VALIDATED' | 'ARCHIVED'
  /** ID de la session de saisie en cours */
  sessionId: number | null
  /** Date de dernière sauvegarde */
  lastSavedAt: string | null
  /** Opération en cours */
  saving: boolean
  /** Erreur éventuelle */
  error: string | null
}

// =============================================================================
// CONFIGURATION DES SECTIONS
// =============================================================================

export const WIZARD_SECTIONS: readonly WizardSectionConfig[] = Object.freeze([
  {
    id: 'usager',
    label: 'Usager',
    subtitle: 'État civil & adresse',
    icon: 'User',
    colorClass: 'blue',
    requiredForSubmit: true,
  },
  {
    id: 'contacts',
    label: 'Contacts',
    subtitle: 'Cercle d\'aide',
    icon: 'BookUser',
    colorClass: 'violet',
    requiredForSubmit: false,
  },
  {
    id: 'aggir',
    label: 'AGGIR',
    subtitle: 'Grille d\'autonomie',
    icon: 'Grid3x3',
    colorClass: 'teal',
    requiredForSubmit: true,
  },
  {
    id: 'social',
    label: 'Social',
    subtitle: 'Habitat & vie sociale',
    icon: 'Home',
    colorClass: 'amber',
    requiredForSubmit: false,
  },
  {
    id: 'sante',
    label: 'Santé',
    subtitle: '7 blocs cliniques',
    icon: 'HeartPulse',
    colorClass: 'pink',
    requiredForSubmit: false,
  },
  {
    id: 'materiels',
    label: 'Matériels',
    subtitle: 'Équipements',
    icon: 'Armchair',
    colorClass: 'emerald',
    requiredForSubmit: false,
  },
  {
    id: 'dispositifs',
    label: 'Dispositifs',
    subtitle: 'Appareillages',
    icon: 'Cpu',
    colorClass: 'slate',
    requiredForSubmit: false,
  },
  {
    id: 'poaSocial',
    label: 'POA Social',
    subtitle: 'Plan d\'aide social',
    icon: 'HandHeart',
    colorClass: 'orange',
    requiredForSubmit: false,
  },
  {
    id: 'poaSante',
    label: 'POA Santé',
    subtitle: 'Plan d\'aide santé',
    icon: 'Pill',
    colorClass: 'red',
    requiredForSubmit: false,
  },
  {
    id: 'poaAutonomie',
    label: 'POA Autonomie',
    subtitle: 'Maintien autonomie',
    icon: 'Target',
    colorClass: 'indigo',
    requiredForSubmit: false,
  },
])

// =============================================================================
// LABELS DE STATUT
// =============================================================================

export const STATUS_LABELS: Record<SectionStatus, string> = {
  empty: 'Non commencé',
  partial: 'En cours',
  complete: 'Complet',
}

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useEvaluationWizard(patientId: Ref<number>) {
  // ── État ─────────────────────────────────────────────────────────────

  const activeSection = ref<string>(WIZARD_SECTIONS[0].id)

  const sectionStates = reactive<Record<string, SectionState>>(
    Object.fromEntries(
      WIZARD_SECTIONS.map((s) => [
        s.id,
        { status: 'empty' as SectionStatus, data: {} },
      ])
    )
  )

  const wizardState = reactive<WizardState>({
    evaluationId: null,
    patientId: patientId.value,
    evaluationStatus: 'DRAFT',
    sessionId: null,
    lastSavedAt: null,
    saving: false,
    error: null,
  })

  // ── Computed ─────────────────────────────────────────────────────────

  const activeSectionConfig = computed(() =>
    WIZARD_SECTIONS.find((s) => s.id === activeSection.value)!
  )

  const completedCount = computed(() =>
    Object.values(sectionStates).filter((s) => s.status === 'complete').length
  )

  const partialCount = computed(() =>
    Object.values(sectionStates).filter((s) => s.status === 'partial').length
  )

  const completionPercent = computed(() => {
    let total = 0
    for (const state of Object.values(sectionStates)) {
      if (state.status === 'complete') total += 10
      else if (state.status === 'partial') total += 4
    }
    return Math.min(total, 100)
  })

  const canSubmit = computed(() => {
    const requiredSections = WIZARD_SECTIONS.filter((s) => s.requiredForSubmit)
    return requiredSections.every(
      (s) => sectionStates[s.id]?.status === 'complete'
    )
  })

  const currentSectionIndex = computed(() =>
    WIZARD_SECTIONS.findIndex((s) => s.id === activeSection.value)
  )

  const hasNext = computed(() => currentSectionIndex.value < WIZARD_SECTIONS.length - 1)
  const hasPrev = computed(() => currentSectionIndex.value > 0)

  // ── Navigation ───────────────────────────────────────────────────────

  function selectSection(sectionId: string) {
    if (WIZARD_SECTIONS.some((s) => s.id === sectionId)) {
      activeSection.value = sectionId
    }
  }

  function nextSection() {
    if (hasNext.value) {
      activeSection.value = WIZARD_SECTIONS[currentSectionIndex.value + 1].id
    }
  }

  function prevSection() {
    if (hasPrev.value) {
      activeSection.value = WIZARD_SECTIONS[currentSectionIndex.value - 1].id
    }
  }

  // ── Données de section ───────────────────────────────────────────────

  function updateSectionData(sectionId: string, data: Record<string, any>) {
    if (sectionStates[sectionId]) {
      sectionStates[sectionId].data = { ...data }
    }
  }

  function updateSectionStatus(sectionId: string, status: SectionStatus) {
    if (sectionStates[sectionId]) {
      sectionStates[sectionId].status = status
    }
  }

  // ── Assemblage JSON evaluation_data ──────────────────────────────────

  function buildEvaluationData(): Record<string, any> {
    const data: Record<string, any> = {}
    for (const section of WIZARD_SECTIONS) {
      const state = sectionStates[section.id]
      if (state && state.status !== 'empty' && Object.keys(state.data).length > 0) {
        data[section.id] = state.data
      }
    }
    return data
  }

  // ── Chargement (édition d'un brouillon existant) ─────────────────────

  function loadEvaluationData(evaluationData: Record<string, any>) {
    for (const section of WIZARD_SECTIONS) {
      const sectionData = evaluationData[section.id]
      if (sectionData && typeof sectionData === 'object' && Object.keys(sectionData).length > 0) {
        sectionStates[section.id].data = { ...sectionData }
        // Le statut sera affiné par chaque formulaire au montage
        // Pour l'instant, on le marque 'partial' si des données existent
        sectionStates[section.id].status = 'partial'
      }
    }
  }

  // ── Persistance ──────────────────────────────────────────────────────

  async function saveDraft(): Promise<boolean> {
    wizardState.saving = true
    wizardState.error = null

    try {
      const evaluationData = buildEvaluationData()
      const payload = {
        evaluation_data: evaluationData,
        completion_percent: completionPercent.value,
      }

      if (wizardState.evaluationId) {
        // Mise à jour d'un brouillon existant
        await evaluationService.update(
          wizardState.patientId,
          wizardState.evaluationId,
          payload
        )
      } else {
        // Création d'une nouvelle évaluation
        const response = await evaluationService.create(
          wizardState.patientId,
          {
            ...payload,
            evaluation_type: 'AGGIR',
            schema_type: 'aggir',
            schema_version: '1.0',
          }
        )
        wizardState.evaluationId = response.data.id
      }

      wizardState.lastSavedAt = new Date().toISOString()
      return true
    } catch (err: any) {
      wizardState.error = err.response?.data?.detail || 'Erreur lors de la sauvegarde'
      if (import.meta.env.DEV) {
        console.error('[EvaluationWizard] Save error:', err)
      }
      return false
    } finally {
      wizardState.saving = false
    }
  }

  async function submitEvaluation(): Promise<boolean> {
    if (!canSubmit.value) return false
    if (!wizardState.evaluationId) {
      const saved = await saveDraft()
      if (!saved) return false
    }

    wizardState.saving = true
    wizardState.error = null

    try {
      await evaluationService.submit(
        wizardState.patientId,
        wizardState.evaluationId!
      )
      wizardState.evaluationStatus = 'SUBMITTED'
      return true
    } catch (err: any) {
      wizardState.error = err.response?.data?.detail || 'Erreur lors de la soumission'
      if (import.meta.env.DEV) {
        console.error('[EvaluationWizard] Submit error:', err)
      }
      return false
    } finally {
      wizardState.saving = false
    }
  }

  // ── Sessions ─────────────────────────────────────────────────────────

  async function startSession(): Promise<void> {
    if (!wizardState.evaluationId) return

    try {
      const response = await evaluationService.startSession(
        wizardState.patientId,
        wizardState.evaluationId,
        {
          user_agent: navigator.userAgent,
          screen_width: window.innerWidth,
          screen_height: window.innerHeight,
        }
      )
      wizardState.sessionId = response.data.id
    } catch (err) {
      if (import.meta.env.DEV) {
        console.warn('[EvaluationWizard] Could not start session:', err)
      }
    }
  }

  async function endSession(): Promise<void> {
    if (!wizardState.evaluationId || !wizardState.sessionId) return

    try {
      const variablesSaved = Object.entries(sectionStates)
        .filter(([, state]) => state.status !== 'empty')
        .map(([id]) => id)

      await evaluationService.endSession(
        wizardState.patientId,
        wizardState.evaluationId,
        wizardState.sessionId,
        { variables_saved: variablesSaved }
      )
      wizardState.sessionId = null
    } catch (err) {
      if (import.meta.env.DEV) {
        console.warn('[EvaluationWizard] Could not end session:', err)
      }
    }
  }

  // ── API publique ─────────────────────────────────────────────────────

  return {
    // Configuration (readonly)
    sections: WIZARD_SECTIONS,

    // État
    activeSection,
    activeSectionConfig,
    sectionStates,
    wizardState,

    // Computed
    completedCount,
    partialCount,
    completionPercent,
    canSubmit,
    hasNext,
    hasPrev,

    // Navigation
    selectSection,
    nextSection,
    prevSection,

    // Données
    updateSectionData,
    updateSectionStatus,
    loadEvaluationData,
    buildEvaluationData,

    // Persistance
    saveDraft,
    submitEvaluation,

    // Sessions
    startSession,
    endSession,
  }
}