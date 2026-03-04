<!--
  CareLink - EvaluationWizard
  Chemin : frontend/src/components/evaluation/EvaluationWizard.vue

  Rôle : Orchestrateur « carnet à intercalaires » pour la saisie d'évaluation.
         Compose la barre patient, le navigateur latéral (WizardSectionNav),
         la zone de formulaire et la barre d'actions.

  Phase 2 : Rendu dynamique des formulaires (UsagerForm.vue branché).
  Identité visuelle : classes .wizard-* définies dans main.css
-->
<template>
  <div class="wizard-container">
    <!-- Barre contexte patient -->
    <div class="wizard-patient-bar">
      <div class="wizard-patient-avatar">
        {{ patientInitials }}
      </div>
      <div class="wizard-patient-info">
        <div class="wizard-patient-name">
          {{ patientName }}
        </div>
        <div class="wizard-patient-meta">
          Évaluation du {{ formattedDate }}
          · <span class="wizard-draft-badge">
              {{ wizardState.evaluationStatus }}
            </span>
        </div>
      </div>
      <div class="wizard-patient-session">
        <FileText :size="14" class="text-slate-400" />
        <span v-if="wizardState.lastSavedAt">
          Sauvegardé {{ formattedLastSaved }}
        </span>
        <span v-else>
          Pas encore sauvegardé
        </span>
      </div>
    </div>

    <!-- Layout principal : sidebar + contenu -->
    <div class="wizard-layout">
      <!-- Navigateur latéral -->
      <WizardSectionNav
        :sections="sections"
        :active-section="activeSection"
        :section-states="sectionStates"
        :completion-percent="completionPercent"
        :completed-count="completedCount"
        :partial-count="partialCount"
        @select="selectSection"
      />

      <!-- Zone de contenu -->
      <div class="wizard-content">
        <!-- En-tête de section -->
        <div class="wizard-content-header">
          <div
            :class="[
              'wizard-content-header__icon',
              `wizard-icon--${activeSectionConfig.colorClass}`
            ]"
          >
            <component
              :is="iconMap[activeSectionConfig.icon]"
              :size="24"
              :stroke-width="1.8"
            />
          </div>
          <div class="flex-1">
            <h2 class="wizard-content-header__title">
              {{ activeSectionConfig.label }}
            </h2>
            <span class="wizard-content-header__subtitle">
              {{ activeSectionConfig.subtitle }}
            </span>
          </div>
          <div
            :class="[
              'wizard-content-header__status',
              `wizard-content-header__status--${currentSectionStatus}`
            ]"
          >
            <component
              :is="statusIconMap[currentSectionStatus]"
              :size="14"
              :stroke-width="2"
            />
            {{ statusLabels[currentSectionStatus] }}
          </div>
        </div>

        <!-- Corps : formulaire dynamique ou placeholder -->
        <div class="wizard-content-body scrollbar-thin">
          <Transition name="wizard-section-fade" mode="out-in">
            <div :key="activeSection">
              <!--
                🔌 RENDU DYNAMIQUE DES FORMULAIRES
                Les sections avec un formulaire implémenté sont rendues ici.
                Les autres affichent le placeholder Phase 3.
              -->

              <!-- Section USAGER — Formulaire implémenté -->
              <UsagerForm
                v-if="activeSection === 'usager'"
                :patient="patient"
                :initial-data="sectionStates.usager?.data"
                @update:data="(data) => onSectionDataUpdate('usager', data)"
                @update:status="(status) => onSectionStatusUpdate('usager', status)"
              />

              <!-- Sections non encore implémentées : placeholder -->
              <div v-else class="wizard-form-placeholder">
                <component
                  :is="iconMap[activeSectionConfig.icon]"
                  :size="48"
                  :stroke-width="1.2"
                  class="wizard-form-placeholder__icon"
                />
                <div class="wizard-form-placeholder__title">
                  {{ activeSectionConfig.label }}
                </div>
                <div class="wizard-form-placeholder__hint">
                  Formulaire de saisie — à venir
                </div>
              </div>
            </div>
          </Transition>
        </div>

        <!-- Barre d'actions -->
        <div class="wizard-action-bar">
          <button
            class="wizard-btn-draft"
            :disabled="wizardState.saving"
            @click="handleSaveDraft"
          >
            <Save :size="15" :stroke-width="2" />
            {{ wizardState.saving ? 'Sauvegarde...' : 'Sauvegarder brouillon' }}
          </button>

          <div class="flex-1" />

          <button
            class="wizard-btn-quit"
            @click="$emit('quit')"
          >
            <X :size="15" :stroke-width="2" />
            Quitter
          </button>

          <button
            class="wizard-btn-submit"
            :disabled="!canSubmit || wizardState.saving"
            @click="handleSubmit"
          >
            <SendHorizontal :size="15" :stroke-width="2.2" />
            Soumettre l'évaluation
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * CareLink - EvaluationWizard
 * Chemin : frontend/src/components/evaluation/EvaluationWizard.vue
 */
import { computed, type Component } from 'vue'
import {
  User,
  BookUser,
  Grid3x3,
  Home,
  HeartPulse,
  Armchair,
  Cpu,
  HandHeart,
  Pill,
  Target,
  FileText,
  Save,
  SendHorizontal,
  X,
  Circle,
  Clock,
  CheckCircle2,
} from 'lucide-vue-next'
import WizardSectionNav from './WizardSectionNav.vue'
import UsagerForm from './forms/UsagerForm.vue'
import type { PatientResponse } from '@/types/patient'
import {
  STATUS_LABELS,
  type WizardSectionConfig,
  type SectionState,
  type SectionStatus,
  type WizardState,
} from '@/composables/useEvaluationWizard'

// ── Props ──────────────────────────────────────────────────────────────

interface Props {
  /** Nom complet du patient (ex: "BACHELARD Gaston") */
  patientName: string
  /** Initiales pour l'avatar (ex: "GB") */
  patientInitials: string
  /** Date d'évaluation formatée (ex: "03/02/2026") */
  formattedDate: string
  /** Données patient déchiffrées — transmises aux formulaires */
  patient: PatientResponse | null

  // Données du composable useEvaluationWizard
  sections: readonly WizardSectionConfig[]
  activeSection: string
  activeSectionConfig: WizardSectionConfig
  sectionStates: Record<string, SectionState>
  wizardState: WizardState
  completionPercent: number
  completedCount: number
  partialCount: number
  canSubmit: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'select-section', sectionId: string): void
  (e: 'save-draft'): void
  (e: 'submit'): void
  (e: 'quit'): void
  (e: 'section-data-update', sectionId: string, data: Record<string, any>): void
  (e: 'section-status-update', sectionId: string, status: SectionStatus): void
}>()

// ── Computed ───────────────────────────────────────────────────────────

const currentSectionStatus = computed<SectionStatus>(
  () => props.sectionStates[props.activeSection]?.status || 'empty'
)

const statusLabels = STATUS_LABELS

const formattedLastSaved = computed(() => {
  if (!props.wizardState.lastSavedAt) return ''
  try {
    return new Date(props.wizardState.lastSavedAt).toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
})

// ── Mapping icônes ─────────────────────────────────────────────────────

const iconMap: Record<string, Component> = {
  User, BookUser, Grid3x3, Home, HeartPulse,
  Armchair, Cpu, HandHeart, Pill, Target,
}

const statusIconMap: Record<string, Component> = {
  empty: Circle,
  partial: Clock,
  complete: CheckCircle2,
}

// ── Handlers ───────────────────────────────────────────────────────────

function selectSection(sectionId: string) {
  emit('select-section', sectionId)
}

function handleSaveDraft() {
  emit('save-draft')
}

function handleSubmit() {
  emit('submit')
}

/**
 * Callback quand un formulaire met à jour ses données.
 * Remonte vers EvaluationCreatePage qui appelle updateSectionData().
 */
function onSectionDataUpdate(sectionId: string, data: Record<string, any>) {
  emit('section-data-update', sectionId, data)
}

/**
 * Callback quand un formulaire met à jour son statut.
 * Remonte vers EvaluationCreatePage qui appelle updateSectionStatus().
 */
function onSectionStatusUpdate(sectionId: string, status: SectionStatus) {
  emit('section-status-update', sectionId, status)
}
</script>

<style scoped>
/*
 * Layout structurel uniquement.
 * L'identité visuelle (couleurs, ombres, états) est dans main.css (.wizard-*)
 */
.wizard-container {
  @apply flex flex-col gap-4;
}
</style>