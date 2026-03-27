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
          Évaluation du {{ formattedDate }} ·
          <span class="wizard-draft-badge">
            {{ wizardState.evaluationStatus }}
          </span>
        </div>
      </div>
      <div class="wizard-patient-session">
        <FileText :size="14" class="text-slate-400" />
        <span v-if="wizardState.lastSavedAt"> Sauvegardé {{ formattedLastSaved }} </span>
        <span v-else> Pas encore sauvegardé </span>
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
        :evaluation-mode="wizardState.evaluationMode"
        :confirmed-sections="confirmedSections"
        @select="selectSection"
      />

      <!-- Zone de contenu -->
      <div class="wizard-content">
        <!-- Bannière mode réévaluation -->
        <div
          v-if="wizardState.evaluationMode === 'reevaluation'"
          class="flex items-center gap-2 px-3 py-2 mb-3 bg-teal-50 border border-teal-200 rounded-lg text-xs text-teal-700"
        >
          <RefreshCw :size="13" class="shrink-0" />
          <span>
            <strong>Réévaluation</strong> — données pré-remplies depuis la dernière évaluation
            validée. La section <strong>AGGIR</strong> doit obligatoirement être recotée.
          </span>
        </div>

        <!-- En-tête de section -->
        <div class="wizard-content-header">
          <div
            :class="[
              'wizard-content-header__icon',
              `wizard-icon--${activeSectionConfig.colorClass}`,
            ]"
          >
            <component :is="iconMap[activeSectionConfig.icon]" :size="24" :stroke-width="1.8" />
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
              `wizard-content-header__status--${currentSectionStatus}`,
            ]"
          >
            <component :is="statusIconMap[currentSectionStatus]" :size="14" :stroke-width="2" />
            {{ statusLabels[currentSectionStatus] }}
          </div>

          <!-- Badge section confirmée inchangée (mode réévaluation) -->
          <div
            v-if="isCurrentSectionConfirmed"
            class="flex items-center gap-1 px-2 py-1 bg-teal-50 border border-teal-200 rounded-md text-xs text-teal-600 font-medium"
          >
            <CheckCheck :size="13" />
            Inchangé
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
                :submit-attempted="submitAttempted"
                @update:data="(data) => onSectionDataUpdate('usager', data)"
                @update:status="(status) => onSectionStatusUpdate('usager', status)"
              />

              <!-- Section CONTACTS — Formulaire implémenté -->
              <ContactsForm
                v-else-if="activeSection === 'contacts'"
                :patient="patient"
                :initial-data="sectionStates.contacts?.data"
                @update:data="(data) => onSectionDataUpdate('contacts', data)"
                @update:status="(status) => onSectionStatusUpdate('contacts', status)"
              />

              <!-- Section AGGIR — Formulaire implémenté -->
              <AggirForm
                v-else-if="activeSection === 'aggir'"
                :patient="patient"
                :evaluation-id="wizardState.evaluationId"
                :initial-data="sectionStates.aggir?.data"
                @update:data="(data) => onSectionDataUpdate('aggir', data)"
                @update:status="(status) => onSectionStatusUpdate('aggir', status)"
              />

              <!-- Section SOCIAL — Formulaire implémenté -->
              <SocialForm
                v-else-if="activeSection === 'social'"
                :patient="patient"
                :initial-data="sectionStates.social?.data"
                @update:data="(data) => onSectionDataUpdate('social', data)"
                @update:status="(status) => onSectionStatusUpdate('social', status)"
              />

              <!-- Section SANTÉ — Formulaire implémenté -->
              <SanteForm
                v-else-if="activeSection === 'sante'"
                :patient="patient"
                :initial-data="sectionStates.sante?.data"
                @update:data="(data) => onSectionDataUpdate('sante', data)"
                @update:status="(status) => onSectionStatusUpdate('sante', status)"
              />

              <!-- Section MATÉRIELS — Formulaire implémenté -->
              <MaterielsForm
                v-else-if="activeSection === 'materiels'"
                :patient="patient"
                :initial-data="sectionStates.materiels?.data"
                @update:data="(data) => onSectionDataUpdate('materiels', data)"
                @update:status="(status) => onSectionStatusUpdate('materiels', status)"
              />

              <!-- Section DISPOSITIFS — Formulaire implémenté -->
              <DispositifsForm
                v-else-if="activeSection === 'dispositifs'"
                :patient="patient"
                :initial-data="sectionStates.dispositifs?.data"
                @update:data="(data) => onSectionDataUpdate('dispositifs', data)"
                @update:status="(status) => onSectionStatusUpdate('dispositifs', status)"
              />

              <!-- Section POA SOCIAL — Formulaire implémenté -->
              <PoaSocialForm
                v-else-if="activeSection === 'poaSocial'"
                :patient="patient"
                :initial-data="sectionStates.poaSocial?.data"
                @update:data="(data) => onSectionDataUpdate('poaSocial', data)"
                @update:status="(status) => onSectionStatusUpdate('poaSocial', status)"
              />

              <!-- Section POA SANTÉ — Formulaire implémenté -->
              <PoaSanteForm
                v-else-if="activeSection === 'poaSante'"
                :patient="patient"
                :initial-data="sectionStates.poaSante?.data"
                @update:data="(data) => onSectionDataUpdate('poaSante', data)"
                @update:status="(status) => onSectionStatusUpdate('poaSante', status)"
              />

              <!-- Section POA AUTONOMIE — Formulaire implémenté -->
              <PoaAutonomieForm
                v-else-if="activeSection === 'poaAutonomie'"
                :patient="patient"
                :initial-data="sectionStates.poaAutonomie?.data"
                @update:data="(data) => onSectionDataUpdate('poaAutonomie', data)"
                @update:status="(status) => onSectionStatusUpdate('poaAutonomie', status)"
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
                <div class="wizard-form-placeholder__hint">Formulaire de saisie — à venir</div>
              </div>
            </div>
          </Transition>
        </div>

        <!-- Barre d'actions -->
        <div class="wizard-action-bar">
          <button :disabled="wizardState.saving" class="wizard-btn-draft" @click="handleSaveDraft">
            <Save :size="15" :stroke-width="2" />
            {{ wizardState.saving ? 'Sauvegarde...' : 'Sauvegarder brouillon' }}
          </button>

          <!-- Bouton "Inchangé" — visible uniquement en mode réévaluation pour les sections non-AGGIR -->
          <button
            v-if="showConfirmUnchanged"
            :title="`Confirmer que la section « ${activeSectionConfig.label} » est inchangée`"
            class="wizard-btn-unchanged"
            @click="handleConfirmUnchanged"
          >
            <CheckCheck :size="15" :stroke-width="2" />
            Inchangé — confirmer
          </button>

          <div class="flex-1" />

          <button class="wizard-btn-quit" @click="$emit('quit')">
            <X :size="15" :stroke-width="2" />
            Quitter
          </button>

          <button
            :disabled="!canSubmit || wizardState.saving"
            class="wizard-btn-submit"
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
  import { computed, type Component } from 'vue';
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
    RefreshCw,
    CheckCheck,
  } from 'lucide-vue-next';
  import WizardSectionNav from './WizardSectionNav.vue';
  import UsagerForm from './forms/UsagerForm.vue';
  import ContactsForm from './forms/ContactsForm.vue';
  import type { PatientResponse } from '@/types';
  import {
    STATUS_LABELS,
    type WizardSectionConfig,
    type WizardSectionData,
    type SectionState,
    type SectionStatus,
    type WizardState,
  } from '@/composables/useEvaluationWizard';
  import AggirForm from './forms/AggirForm.vue';
  import SocialForm from './forms/SocialForm.vue';
  import SanteForm from './forms/SanteForm.vue';
  import MaterielsForm from './forms/MaterielsForm.vue';
  import DispositifsForm from './forms/DispositifsForm.vue';
  import PoaSocialForm from './forms/PoaSocialForm.vue';
  import PoaSanteForm from './forms/PoaSanteForm.vue';
  import PoaAutonomieForm from './forms/PoaAutonomieForm.vue';

  // ── Props ──────────────────────────────────────────────────────────────

  interface Props {
    /** Nom complet du patient (ex: "BACHELARD Gaston") */
    patientName: string;
    /** Initiales pour l'avatar (ex: "GB") */
    patientInitials: string;
    /** Date d'évaluation formatée (ex: "03/02/2026") */
    formattedDate: string;
    /** Données patient déchiffrées — transmises aux formulaires */
    patient: PatientResponse | null;

    // Données du composable useEvaluationWizard
    sections: readonly WizardSectionConfig[];
    activeSection: string;
    activeSectionConfig: WizardSectionConfig;
    sectionStates: Record<string, SectionState>;
    wizardState: WizardState;
    completionPercent: number;
    completedCount: number;
    partialCount: number;
    canSubmit: boolean;
    /** Sections confirmées inchangées (mode réévaluation) */
    confirmedSections: Set<string>;
    /** Passe à true après le premier clic sur "Soumettre" — active la validation visuelle */
    submitAttempted?: boolean;
  }

  const props = defineProps<Props>();

  const emit = defineEmits<{
    (e: 'select-section', sectionId: string): void;
    (e: 'save-draft'): void;
    (e: 'submit'): void;
    (e: 'quit'): void;
    (e: 'section-data-update', sectionId: string, data: WizardSectionData): void;
    (e: 'section-status-update', sectionId: string, status: SectionStatus): void;
    (e: 'confirm-section-unchanged', sectionId: string): void;
  }>();

  // ── Computed ───────────────────────────────────────────────────────────

  const currentSectionStatus = computed<SectionStatus>(
    () => props.sectionStates[props.activeSection]?.status || 'empty',
  );

  /** Vrai si la section active a été confirmée inchangée (mode réévaluation) */
  const isCurrentSectionConfirmed = computed(() =>
    props.confirmedSections.has(props.activeSection),
  );

  /** Afficher le bouton "Inchangé" : mode réévaluation, section non-aggir, pas encore confirmée */
  const showConfirmUnchanged = computed(
    () =>
      props.wizardState.evaluationMode === 'reevaluation' &&
      props.activeSection !== 'aggir' &&
      !isCurrentSectionConfirmed.value,
  );

  const statusLabels = STATUS_LABELS;

  const formattedLastSaved = computed(() => {
    if (!props.wizardState.lastSavedAt) return '';
    try {
      return new Date(props.wizardState.lastSavedAt).toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '';
    }
  });

  // ── Mapping icônes ─────────────────────────────────────────────────────

  const iconMap: Record<string, Component> = {
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
  };

  const statusIconMap: Record<string, Component> = {
    empty: Circle,
    partial: Clock,
    complete: CheckCircle2,
  };

  // ── Handlers ───────────────────────────────────────────────────────────

  function selectSection(sectionId: string) {
    emit('select-section', sectionId);
  }

  function handleSaveDraft() {
    emit('save-draft');
  }

  function handleSubmit() {
    emit('submit');
  }

  function handleConfirmUnchanged() {
    emit('confirm-section-unchanged', props.activeSection);
  }

  /**
   * Callback quand un formulaire met à jour ses données.
   * Remonte vers EvaluationCreatePage qui appelle updateSectionData().
   */
  function onSectionDataUpdate(sectionId: string, data: WizardSectionData) {
    emit('section-data-update', sectionId, data);
  }

  /**
   * Callback quand un formulaire met à jour son statut.
   * Remonte vers EvaluationCreatePage qui appelle updateSectionStatus().
   */
  function onSectionStatusUpdate(sectionId: string, status: SectionStatus) {
    emit('section-status-update', sectionId, status);
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

  /*
 * Bouton "Inchangé — confirmer" (mode réévaluation)
 * Calqué sur wizard-btn-draft mais avec palette teal/outlined
 */
  .wizard-btn-unchanged {
    @apply flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium
         border border-teal-300 text-teal-700 bg-teal-50
         hover:bg-teal-100 hover:border-teal-400
         transition-colors duration-150 cursor-pointer;
  }
</style>