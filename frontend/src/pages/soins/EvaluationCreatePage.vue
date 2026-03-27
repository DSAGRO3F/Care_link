<!--
  CareLink - EvaluationCreatePage
  Chemin : frontend/src/pages/soins/EvaluationCreatePage.vue

  Rôle : Page de création/édition d'une évaluation patient.
         Charge les données patient, initialise le wizard,
         gère le cycle de vie (sessions, navigation guards).

  Phase 2 : Transmet les données patient au wizard pour pré-remplissage
             des formulaires (UsagerForm, etc.)

  🆕 05/03/2026 — Phase 10C :
         Lecture de route.query.section au montage pour permettre
         la navigation directe depuis EvaluationDraftProgress.
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
      :confirmed-sections="confirmedSections"
      :submit-attempted="submitAttempted"
      @select-section="selectSection"
      @save-draft="onSaveDraft"
      @submit="onSubmit"
      @quit="onQuit"
      @section-data-update="onSectionDataUpdate"
      @section-status-update="onSectionStatusUpdate"
      @confirm-section-unchanged="onConfirmSectionUnchanged"
    />
  </div>
</template>

<script setup lang="ts">
  /**
   * CareLink - EvaluationCreatePage
   * Chemin : frontend/src/pages/soins/EvaluationCreatePage.vue
   */
  import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { useToast } from 'primevue/usetoast';
  import ProgressSpinner from 'primevue/progressspinner';
  import Button from 'primevue/button';

  import EvaluationWizard from '@/components/evaluation/EvaluationWizard.vue';
  import { useEvaluationWizard, WIZARD_SECTIONS } from '@/composables/useEvaluationWizard';
  import type { SectionStatus, WizardSectionData } from '@/composables/useEvaluationWizard';
  import { patientService } from '@/services';
  import type { PatientResponse, PatientEvaluationResponse } from '@/types';
  import axios from 'axios';

  // ── Route & services ───────────────────────────────────────────────────

  const route = useRoute();
  const router = useRouter();
  const toast = useToast();

  /** Intervalle de sauvegarde automatique (ms). 2 minutes. */
  const AUTO_SAVE_INTERVAL_MS = 2 * 60 * 1000;

  /** Référence au timer d'auto-sauvegarde — nettoyé dans onBeforeUnmount. */
  const autoSaveTimer = ref<ReturnType<typeof setInterval> | null>(null);

  const patientId = ref<number>(Number(route.params.patientId));
  const evaluationId = ref<number | null>(
    route.params.evaluationId ? Number(route.params.evaluationId) : null,
  );

  // ── État local (chargement patient) ────────────────────────────────────

  const loading = ref(true);
  const error = ref<string | null>(null);
  const patient = ref<PatientResponse | null>(null);

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
    prefillFromPreviousEvaluation,
    prefillFromPatient,
    saveDraft,
    submitEvaluation,
    startSession,
    endSession,
    confirmedSections,
    confirmSectionUnchanged,
    submitAttempted,
  } = useEvaluationWizard(patientId);

  // ── Sync activeSection → URL query param ──────────────────────────────
  // Quand l'utilisateur navigue entre sections via le stepper,
  // on reflète la section active dans l'URL pour garder le deep-linking fonctionnel.
  // Note : le sens inverse (URL → composable) est géré au montage (onMounted, étape 4).

  watch(activeSection, (newSection) => {
    if (newSection !== route.query.section) {
      router.replace({ query: { ...route.query, section: newSection } });
    }
  });

  // ── Computed patient ───────────────────────────────────────────────────

  const patientFullName = computed(() => {
    if (!patient.value) return '';
    return `${patient.value.last_name ?? ''} ${patient.value.first_name ?? ''}`.trim();
  });

  const patientInitials = computed(() => {
    if (!patient.value) return '';
    const first = (patient.value.first_name || '')[0] || '';
    const last = (patient.value.last_name || '')[0] || '';
    return `${first}${last}`.toUpperCase();
  });

  const todayFormatted = computed(() => {
    return new Date().toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  });

  // ── Chargement initial ─────────────────────────────────────────────────

  onMounted(async () => {
    try {
      // 1. Charger les données du patient
      const { evaluationService } = await import('@/services');
      patient.value = await patientService.getById(patientId.value);

      if (import.meta.env.DEV) {
        // eslint-disable-next-line no-console
        console.log('[EvaluationCreatePage] Patient loaded:', patient.value);
      }

      // 2. Déterminer l'évaluation à charger
      //    Priorité 1 : evaluationId dans l'URL (mode édition explicite)
      //    Priorité 2 : brouillon DRAFT existant pour ce patient (mode /new après rechargement)
      let targetEvaluationId: number | null = evaluationId.value;

      if (!targetEvaluationId) {
        // ✅ Fix : chercher un brouillon existant pour éviter d'en créer un doublon
        // et recharger les données saisies lors d'une session précédente.
        try {
          const listResponse = await evaluationService.getAll(patientId.value);
          const evaluations: PatientEvaluationResponse[] = listResponse?.data?.items ?? listResponse?.data ?? [];
          const draft = evaluations.find(
            (e) => e.status === 'DRAFT' || e.status === 'IN_PROGRESS',
          );
          if (draft) {
            targetEvaluationId = draft.id;
            if (import.meta.env.DEV) {
              // eslint-disable-next-line no-console
              console.log('[EvaluationCreatePage] Brouillon trouvé, rechargement:', draft.id);
            }
          } else {
            // Pas de brouillon → pré-remplir depuis la dernière évaluation soumise
            // (endpoint dédié : retourne PENDING_MEDICAL, PENDING_DEPARTMENT ou VALIDATED)
            const latestResponse = await evaluationService.getLatestSubmitted(
              patientId.value,
            );
            if (latestResponse?.data?.evaluation_data) {
              prefillFromPreviousEvaluation(latestResponse.data.evaluation_data);
              toast.add({
                severity: 'info',
                summary: 'Données pré-remplies',
                detail: `Sections reprises depuis l'évaluation du ${new Date(latestResponse.data.evaluation_date).toLocaleDateString('fr-FR')}.`,
                life: 6000,
              });
              if (import.meta.env.DEV) {
                // eslint-disable-next-line no-console
                console.log(
                  '[EvaluationCreatePage] Pré-remplissage depuis éval soumise:',
                  latestResponse.data.evaluation_id,
                );
              }
            } else if (patient.value) {
              // Aucune évaluation soumise → fallback fiche patient SQL
              prefillFromPatient(patient.value);
              toast.add({
                severity: 'info',
                summary: 'Données pré-remplies',
                detail: 'Section Usager pré-remplie depuis la fiche patient.',
                life: 6000,
              });
              if (import.meta.env.DEV) {
                // eslint-disable-next-line no-console
                console.log('[EvaluationCreatePage] Fallback fiche patient pour pré-remplissage');
              }
            }
          }
        } catch {
          // Pas de brouillon trouvé ou erreur réseau → démarrage vierge, pas bloquant
        }
      }

      // 3. Charger les données de l'évaluation trouvée
      if (targetEvaluationId) {
        const evalResponse = await evaluationService.get(
          patientId.value,
          targetEvaluationId,
        );
        const evaluation = evalResponse?.data ?? evalResponse;

        wizardState.evaluationId = evaluation.id;
        wizardState.evaluationStatus = evaluation.status;

        if (evaluation.evaluation_data) {
          loadEvaluationData(evaluation.evaluation_data);
        }
      }

      // 4. Naviguer vers la section cible si spécifiée en query param.
      //    Utilisé par EvaluationDraftProgress (clic sur un nœud de la chaîne).
      //    On valide que la section demandée existe dans WIZARD_SECTIONS.
      const queriedSection = route.query.section as string | undefined;
      if (queriedSection && WIZARD_SECTIONS.some((s) => s.id === queriedSection)) {
        selectSection(queriedSection);
        if (import.meta.env.DEV) {
          // eslint-disable-next-line no-console
          console.log('[EvaluationCreatePage] Navigation directe vers section:', queriedSection);
        }
      }

      loading.value = false;

      // 5. Démarrer une session de saisie (si évaluation existante)
      if (wizardState.evaluationId) {
        await startSession();
      }

      // 6. Démarrer la sauvegarde automatique toutes les 2 minutes.
      //    Silencieuse en cas de succès, toast d'erreur discret si elle échoue.
      //    Démarre uniquement si l'évaluation existe (pas encore de DRAFT créé → la
      //    première sauvegarde manuelle crée l'entrée, ensuite l'auto-save prend le relais).
      autoSaveTimer.value = setInterval(async () => {
        if (!wizardState.evaluationId) return; // pas encore de DRAFT → rien à patcher
        const ok = await saveDraft();
        if (!ok && import.meta.env.DEV) {
          console.warn('[EvaluationCreatePage] Auto-save échoué:', wizardState.error);
        }
        if (!ok) {
          toast.add({
            severity: 'warn',
            summary: 'Auto-sauvegarde échouée',
            detail: "La sauvegarde automatique n'a pas abouti. Pensez à sauvegarder manuellement.",
            life: 5000,
          });
        }
        if (import.meta.env.DEV) {
          // eslint-disable-next-line no-console
          console.log(
            '[EvaluationCreatePage] Auto-save OK à',
            new Date().toLocaleTimeString('fr-FR'),
          );
        }
      }, AUTO_SAVE_INTERVAL_MS);
    } catch (err: unknown) {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : undefined;
      error.value = detail || 'Impossible de charger le patient';
      loading.value = false;
      if (import.meta.env.DEV) {
        console.error('[EvaluationCreatePage] Load error:', err);
      }
    }
  });

  // ── Nettoyage (fin de session) ─────────────────────────────────────────

  onBeforeUnmount(async () => {
    // Arrêter l'auto-save avant de quitter
    if (autoSaveTimer.value !== null) {
      clearInterval(autoSaveTimer.value);
      autoSaveTimer.value = null;
    }
    await endSession();
  });

  // ── Callbacks des formulaires de section ───────────────────────────────

  function onSectionDataUpdate(sectionId: string, data: WizardSectionData) {
    updateSectionData(sectionId, data);
  }

  function onSectionStatusUpdate(sectionId: string, status: SectionStatus) {
    updateSectionStatus(sectionId, status);
  }

  function onConfirmSectionUnchanged(sectionId: string) {
    confirmSectionUnchanged(sectionId);
  }

  // ── Actions ────────────────────────────────────────────────────────────

  async function onSaveDraft() {
    const success = await saveDraft();
    if (success) {
      toast.add({
        severity: 'success',
        summary: 'Brouillon sauvegardé',
        detail: "L'évaluation a été enregistrée.",
        life: 3000,
      });

      // Si c'est une nouvelle évaluation, démarrer la session
      if (wizardState.evaluationId && !wizardState.sessionId) {
        await startSession();
      }
    } else {
      toast.add({
        severity: 'error',
        summary: 'Erreur',
        detail: wizardState.error || 'La sauvegarde a échoué.',
        life: 5000,
      });
    }
  }

  async function onSubmit() {
    const success = await submitEvaluation();
    if (success) {
      toast.add({
        severity: 'success',
        summary: 'Évaluation soumise',
        detail: "L'évaluation a été soumise pour validation.",
        life: 4000,
      });
      // Retour à la page patient après soumission
      await router.push({
        name: 'admin-patient-detail',
        params: { id: patientId.value },
      });
    } else {
      toast.add({
        severity: 'error',
        summary: 'Erreur de soumission',
        detail: wizardState.error || 'Les sections obligatoires ne sont pas complètes.',
        life: 5000,
      });
    }
  }

  function onQuit() {
    // TODO : confirm dialog si données non sauvegardées
    goBack();
  }

  function goBack() {
    router.back();
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