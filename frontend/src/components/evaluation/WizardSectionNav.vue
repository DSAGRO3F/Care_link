<!--
  CareLink - WizardSectionNav
  Chemin : frontend/src/components/evaluation/WizardSectionNav.vue

  Rôle : Navigateur latéral « carnet à intercalaires » pour le wizard
         de saisie d'évaluation. Affiche les 10 sections avec icônes
         Lucide colorées, indicateurs d'état, et ring de progression.

  Identité visuelle : classes .wizard-* définies dans main.css
  Dépendance : lucide-vue-next (npm install lucide-vue-next)
-->
<template>
  <nav class="wizard-nav" aria-label="Sections d'évaluation">
    <!-- En-tête : progress ring + compteurs -->
    <div class="wizard-nav-header">
      <!-- Progress ring SVG -->
      <div class="wizard-progress-ring">
        <svg width="52" height="52">
          <defs>
            <linearGradient id="wizardProgressGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#2dd4bf" />
              <stop offset="100%" stop-color="#0d9488" />
            </linearGradient>
          </defs>
          <circle class="wizard-progress-ring__track" cx="26" cy="26" r="20" />
          <circle
            :stroke-dasharray="circumference"
            :stroke-dashoffset="progressOffset"
            class="wizard-progress-ring__fill"
            cx="26"
            cy="26"
            r="20"
          />
        </svg>
        <div class="wizard-progress-ring__text">{{ completionPercent }}%</div>
      </div>

      <div>
        <div class="wizard-nav-progress-label">Progression</div>
        <div class="wizard-nav-progress-detail">
          <span class="text-emerald-600 font-semibold">{{ completedCount }}</span>
          terminée{{ completedCount > 1 ? 's' : '' }} ·
          <span class="text-amber-600 font-semibold">{{ partialCount }}</span>
          en cours
        </div>
      </div>
    </div>

    <!-- Liste des sections -->
    <div class="wizard-nav-list">
      <button
        v-for="section in sections"
        :key="section.id"
        :class="[
          'wizard-section-item',
          { 'wizard-section-item--active': section.id === activeSection },
        ]"
        :aria-current="section.id === activeSection ? 'step' : undefined"
        @click="$emit('select', section.id)"
      >
        <!-- Icône colorée -->
        <div :class="['wizard-section-icon', `wizard-icon--${section.colorClass}`]">
          <component
            :is="iconMap[section.icon]"
            :size="20"
            :stroke-width="section.id === activeSection ? 2.2 : 1.8"
          />
        </div>

        <!-- Label + subtitle -->
        <div class="wizard-section-text">
          <div class="wizard-section-label">{{ section.label }}</div>
          <div class="wizard-section-subtitle">{{ section.subtitle }}</div>
        </div>

        <!-- Indicateur de statut -->
        <!-- En mode réévaluation, une section "confirmée inchangée" affiche CheckCheck en teal -->
        <div
          v-if="confirmedSections?.has(section.id)"
          class="wizard-status wizard-status--confirmed"
        >
          <CheckCheck :size="14" :stroke-width="2" class="wizard-status__icon" />
        </div>
        <div
          v-else
          :class="[
            'wizard-status',
            `wizard-status--${sectionStates[section.id]?.status || 'empty'}`,
          ]"
        >
          <component
            :is="statusIconMap[sectionStates[section.id]?.status || 'empty']"
            :size="14"
            :stroke-width="2"
            :fill="sectionStates[section.id]?.status === 'complete' ? 'currentColor' : 'none'"
            class="wizard-status__icon"
          />
        </div>

        <!-- Chevron actif -->
        <ChevronRight
          v-if="section.id === activeSection"
          :size="16"
          :stroke-width="2.5"
          class="wizard-section-chevron"
        />
      </button>
    </div>
  </nav>
</template>

<script setup lang="ts">
  /**
   * CareLink - WizardSectionNav
   * Chemin : frontend/src/components/evaluation/WizardSectionNav.vue
   */
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
    ChevronRight,
    Circle,
    Clock,
    CheckCircle2,
    CheckCheck,
  } from 'lucide-vue-next';
  import { computed, type Component } from 'vue';
  import type { WizardSectionConfig, SectionState } from '@/composables/useEvaluationWizard';

  // ── Props ──────────────────────────────────────────────────────────────

  interface Props {
    sections: readonly WizardSectionConfig[];
    activeSection: string;
    sectionStates: Record<string, SectionState>;
    completionPercent: number;
    completedCount: number;
    partialCount: number;
    /** Mode courant du wizard (initial | reevaluation) */
    evaluationMode?: 'initial' | 'reevaluation';
    /** Sections confirmées inchangées (mode réévaluation) */
    confirmedSections?: Set<string>;
  }

  const props = defineProps<Props>();

  defineEmits<{
    (e: 'select', sectionId: string): void;
  }>();

  // ── Mapping icônes Lucide ──────────────────────────────────────────────

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
    confirmed: CheckCheck,
  };

  // ── Progress ring ──────────────────────────────────────────────────────

  const radius = 20;
  const circumference = 2 * Math.PI * radius;
  const progressOffset = computed(
    () => circumference - (props.completionPercent / 100) * circumference,
  );
</script>

<style scoped>
  /*
 * Layout structurel uniquement.
 * L'identité visuelle (couleurs, ombres, états) est dans main.css (.wizard-*)
 */
  .wizard-section-text {
    @apply flex-1 min-w-0;
  }
</style>
