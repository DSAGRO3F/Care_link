<!--
  CareLink - EvaluationCreatePage
  Chemin : frontend/src/pages/soins/EvaluationCreatePage.vue

  Rôle : Page de création/édition d'une évaluation patient.
         Charge les données patient, initialise le wizard,
         gère le cycle de vie (sessions, navigation guards).

  Phase 2 : Transmet les données patient au wizard pour pré-remplissage
             des formulaires (UsagerForm, etc.)
-->
<template>
  <div class="evaluation-create-page">
    <!-- Loading initial -->
    <div v-if="loading" class="page-loading">
      <ProgressSpinner stroke-width="4" />
      <span class="text-slate-500 mt-4">Chargement du patient...</span>
    </div>

    <!-- Erreur -->
    <div v-else-if="error" class="page-error">
      <i class="pi pi-exclamation-triangle text-4xl text-red-400 mb-3"></i>
      <span class="text-slate-600 mb-4">{{ error }}</span>
      <Button label="Retour aux patients" icon="pi pi-arrow-left" @click="goBack" />
    </div>

    <!-- Wizard -->
    <EvaluationWizard
      v-else
      :patient-name="patientFullName"
      :patient-initials="patientInitials"
      :formatted-date="todayFormatted"
      :patient="patient"
      :sections="sections"
      :active-section="activeSection"
      :active-section-config="activeSectionConfig"
      :section-states="sectionStates"
      :wizard-state="wizardState"
      :completion-percent="completionPercent"
      :completed-count="completedCount"
      :partial-count="partialCount"
      :can-submit="canSubmit"
      @select-section="selectSection"
      @save-draft="onSaveDraft"
      @submit="onSubmit"
      @quit="onQuit"
      @section-data-update="onSectionDataUpdate"
      @section-status-update="onSectionStatusUpdate"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * CareLink - EvaluationCreatePage
 * Chemin : frontend/src/pages/soins/EvaluationCreatePage.vue
 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import ProgressSpinner from 'primevue/progressspinner'
import Button from 'primevue/button'

import EvaluationWizard from '@/components/evaluation/EvaluationWizard.vue'
import { useEvaluationWizard } from '@/composables/useEvaluationWizard'
import type { SectionStatus } from '@/composables/useEvaluationWizard'
import { patientService } from '@/services'
import type { PatientResponse } from '@/types/patient'

// ── Route & services ───────────────────────────────────────────────────

const route = useRoute()
const router = useRouter()
const toast = useToast()

const patientId = ref<number>(Number(route.params.patientId))
const evaluationId = ref<number | null>(
  route.params.evaluationId ? Number(route.params.evaluationId) : null
)

// ── État local (chargement patient) ────────────────────────────────────

const loading = ref(true)
const error = ref<string | null>(null)
const patient = ref<PatientResponse | null>(null)

// ── Wizard composable ──────────────────────────────────────────────────

const {
  sections,
  activeSection,
  activeSectionConfig,
  sectionStates,
  wizardState,
  completionPercent,
  completedCount,
  partialCount,
  canSubmit,
  selectSection,
  updateSectionData,
  updateSectionStatus,
  loadEvaluationData,
  saveDraft,
  submitEvaluation,
  startSession,
  endSession,
} = useEvaluationWizard(patientId)

// ── Computed patient ───────────────────────────────────────────────────

const patientFullName = computed(() => {
  if (!patient.value) return ''
  return `${patient.value.last_name ?? ''} ${patient.value.first_name ?? ''}`.trim()
})

const patientInitials = computed(() => {
  if (!patient.value) return ''
  const first = (patient.value.first_name || '')[0] || ''
  const last = (patient.value.last_name || '')[0] || ''
  return `${first}${last}`.toUpperCase()
})

const todayFormatted = computed(() => {
  return new Date().toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
})

// ── Chargement initial ─────────────────────────────────────────────────

onMounted(async () => {
  try {
    // Charger les données du patient
    // getById() retourne PatientResponse (déchiffré côté backend)
    patient.value = await patientService.getById(patientId.value)

    // Debug en dev pour vérifier ce qu'on reçoit
    if (import.meta.env.DEV) {
      console.log('[EvaluationCreatePage] Patient loaded:', patient.value)
    }

    // Si édition d'une évaluation existante, charger ses données
    if (evaluationId.value) {
      const { evaluationService } = await import('@/services')
      const evaluation = await evaluationService.get(
        patientId.value,
        evaluationId.value
      ) as any  // evaluationService.get() retourne la réponse evaluation

      wizardState.evaluationId = evaluation.id
      wizardState.evaluationStatus = evaluation.status

      if (evaluation.evaluation_data) {
        loadEvaluationData(evaluation.evaluation_data)
      }
    }

    loading.value = false

    // Démarrer une session de saisie (si évaluation existante)
    if (wizardState.evaluationId) {
      await startSession()
    }
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Impossible de charger le patient'
    loading.value = false
    if (import.meta.env.DEV) {
      console.error('[EvaluationCreatePage] Load error:', err)
    }
  }
})

// ── Nettoyage (fin de session) ─────────────────────────────────────────

onBeforeUnmount(async () => {
  await endSession()
})

// ── Callbacks des formulaires de section ───────────────────────────────

function onSectionDataUpdate(sectionId: string, data: Record<string, any>) {
  updateSectionData(sectionId, data)
}

function onSectionStatusUpdate(sectionId: string, status: SectionStatus) {
  updateSectionStatus(sectionId, status)
}

// ── Actions ────────────────────────────────────────────────────────────

async function onSaveDraft() {
  const success = await saveDraft()
  if (success) {
    toast.add({
      severity: 'success',
      summary: 'Brouillon sauvegardé',
      detail: 'L\'évaluation a été enregistrée.',
      life: 3000,
    })

    // Si c'est une nouvelle évaluation, démarrer la session
    if (wizardState.evaluationId && !wizardState.sessionId) {
      await startSession()
    }
  } else {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: wizardState.error || 'La sauvegarde a échoué.',
      life: 5000,
    })
  }
}

async function onSubmit() {
  const success = await submitEvaluation()
  if (success) {
    toast.add({
      severity: 'success',
      summary: 'Évaluation soumise',
      detail: 'L\'évaluation a été soumise pour validation.',
      life: 4000,
    })
    // Retour à la page patient après soumission
    await router.push({
      name: 'admin-patient-detail',
      params: { id: patientId.value },
    })
  } else {
    toast.add({
      severity: 'error',
      summary: 'Erreur de soumission',
      detail: wizardState.error || 'Les sections obligatoires ne sont pas complètes.',
      life: 5000,
    })
  }
}

function onQuit() {
  // TODO : confirm dialog si données non sauvegardées
  goBack()
}

function goBack() {
  router.back()
}
</script>

<style scoped>
.evaluation-create-page {
  @apply p-4 lg:p-6 max-w-7xl mx-auto;
}

.page-loading {
  @apply flex flex-col items-center justify-center py-24;
}

.page-error {
  @apply flex flex-col items-center justify-center py-24 text-center;
}
</style>