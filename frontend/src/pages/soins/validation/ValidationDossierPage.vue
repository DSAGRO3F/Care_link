<script setup lang="ts">
  /**
   * ValidationDossierPage.vue — Écran unifié « Dossier de validation » (F5).
   *
   * Coquille de l'écran : cycle de vie (chargement VR + fil via le store),
   * états chargement/erreur, pipeline (chaîne de VR dérivée du store) et points
   * de montage des sous-composants F6 (fil) et F7 (compose).
   *
   * Identité patient : bandeau d'identitovigilance alimenté par le contexte
   * dossier du store (`patientIdentity`), agrégé côté backend (identité + GIR,
   * déchiffrés et minimisés). Le pipeline est reconstruit depuis les VR réelles
   * du dossier (`requestByStage`) — plus aucune dérivation par index.
   *
   * Destination : src/pages/soins/validation/ValidationDossierPage.vue
   */
  import { onMounted, onBeforeUnmount, computed, watch } from 'vue';
  import { useValidationThreadStore } from '@/stores';
  import { VALIDATION_STAGE_LABELS, VALIDATION_WORKFLOW_LABELS } from '@/types';
  import type { ValidationStage } from '@/types';
  import ValidationThread from '@/components/validation/ValidationThread.vue';
  import ValidationCompose from '@/components/validation/ValidationCompose.vue';
  import PatientIdentityBanner from '@/components/careplan/PatientIdentityBanner.vue';

  const props = defineProps<{
    vrId: string;
  }>();

  const store = useValidationThreadStore();

  /** Séquence d'étapes du workflow AGGIR (les autres : étape courante seule). */
  const AGGIR_STAGES: ValidationStage[] = ['INTERNAL_REVIEW', 'MEDICAL_REVIEW', 'FUNDING_REVIEW'];

  const workflowLabel = computed(() =>
    store.currentRequest ? VALIDATION_WORKFLOW_LABELS[store.currentRequest.workflow_type] : '',
  );

  /**
   * Étapes du pipeline avec statut (done / current / upcoming) et n° de VR.
   * Le n° de VR vient de la VR réelle de chaque étape (`requestByStage`) ; le
   * statut suit l'étape courante (`currentRequest`). Repli sur la VR en focus
   * pour l'étape courante tant que le contexte dossier n'est pas chargé.
   */
  const pipelineSteps = computed(() => {
    const vr = store.currentRequest;
    if (!vr) return [];
    const stages = vr.workflow_type === 'AGGIR_FUNDING' ? AGGIR_STAGES : [vr.stage];
    const currentIdx = stages.indexOf(vr.stage);
    const byStage = store.requestByStage;

    return stages.map((stage, i) => {
      let status: 'done' | 'current' | 'upcoming';
      let sublabel: string;
      if (i < currentIdx) {
        status = 'done';
        sublabel = 'Terminé';
      } else if (i === currentIdx) {
        // §8.3a : une décision ne « termine » l'étape que si elle est VALIDÉE.
        // Un MORE_INFO laisse le nœud actif (la balle repart côté émetteur) ;
        // une invalidation ne se présente pas non plus comme un « Terminé ✓ ».
        if (vr.decision === 'VALIDATED') {
          status = 'done';
          sublabel = 'Terminé';
        } else if (vr.decision === 'MORE_INFO_REQUESTED') {
          status = 'current';
          sublabel = 'Complément demandé';
        } else if (vr.decision === 'INVALIDATED') {
          status = 'current';
          sublabel = 'Invalidée';
        } else {
          status = 'current';
          sublabel = 'En cours';
        }
      } else {
        status = 'upcoming';
        sublabel = 'À venir';
      }

      // N° de VR : la VR réelle de cette étape ; repli sur la VR en focus.
      const stepVrId = byStage.get(stage)?.id ?? (i === currentIdx ? vr.id : null);

      return { stage, label: VALIDATION_STAGE_LABELS[stage], status, sublabel, vrId: stepVrId };
    });
  });

  async function load(): Promise<void> {
    try {
      await store.loadFromRequest(Number(props.vrId));
    } catch {
      // store.error porte le message ; l'UI le rend ci-dessous.
    }
  }

  onMounted(load);
  watch(() => props.vrId, load);
  onBeforeUnmount(() => store.reset());
</script>

<template>
  <div class="mx-auto max-w-5xl p-6">
    <!-- ÉTAT — chargement initial -->
    <div v-if="store.loading && !store.currentRequest" class="py-16 text-center text-slate-400">
      <i class="pi pi-spin pi-spinner text-2xl" />
      <p class="mt-3 text-sm">Chargement du dossier…</p>
    </div>

    <!-- ÉTAT — erreur -->
    <div
      v-else-if="store.error && !store.currentRequest"
      class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700"
    >
      {{ store.error }}
    </div>

    <!-- CONTENU -->
    <template v-else-if="store.currentRequest">
      <!-- Bandeau d'identitovigilance patient (contexte dossier agrégé serveur) -->
      <PatientIdentityBanner
        v-if="store.patientIdentity"
        :patient="store.patientIdentity"
        class="mb-4"
      />

      <!-- En-tête dossier (contexte VR réel) -->
      <header class="mb-4 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h1 class="text-lg font-bold text-slate-800">Dossier de validation</h1>
        <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <div class="text-[10.5px] font-bold uppercase tracking-wide text-slate-400">Workflow</div>
            <div class="mt-0.5 text-sm font-medium text-slate-700">{{ workflowLabel }}</div>
          </div>
          <div>
            <div class="text-[10.5px] font-bold uppercase tracking-wide text-slate-400">Demande</div>
            <div class="mt-0.5 text-sm font-medium text-slate-700">#{{ store.currentRequest.id }}</div>
          </div>
          <div>
            <div class="text-[10.5px] font-bold uppercase tracking-wide text-slate-400">Étape</div>
            <div class="mt-0.5 text-sm font-medium text-slate-700">
              {{ store.currentStage ? VALIDATION_STAGE_LABELS[store.currentStage] : '—' }}
            </div>
          </div>
        </div>
      </header>

      <!-- Pipeline -->
      <section class="mb-4 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div class="mb-4 text-[10.5px] font-bold uppercase tracking-wide text-slate-400">
          Parcours de validation
        </div>
        <ol class="flex items-start">
          <li
            v-for="(step, i) in pipelineSteps"
            :key="step.stage"
            :class="
              i < pipelineSteps.length - 1
                ? 'flex min-w-0 flex-1 items-start'
                : 'flex items-start'
            "
          >
            <div class="flex w-24 flex-shrink-0 flex-col items-center gap-1.5 text-center">
              <span
                :class="{
                  'border-teal-600 bg-teal-600 text-white': step.status === 'done',
                  'border-amber-500 bg-white text-amber-600 ring-4 ring-amber-50':
                    step.status === 'current',
                  'border-slate-200 bg-white text-slate-400': step.status === 'upcoming',
                }"
                class="grid h-[30px] w-[30px] place-items-center rounded-full border-2 text-xs font-bold"
              >
                <i v-if="step.status === 'done'" class="pi pi-check text-[11px]" />
                <template v-else>{{ i + 1 }}</template>
              </span>
              <span
                :class="step.status === 'upcoming' ? 'text-slate-400' : 'text-slate-700'"
                class="text-[11.5px] font-bold leading-tight"
              >
                {{ step.label }}
                <small class="mt-0.5 block text-[10px] font-medium text-slate-400">
                  {{ step.sublabel }}<template v-if="step.vrId"> · VR #{{ step.vrId }}</template>
                </small>
              </span>
            </div>
            <span
              v-if="i < pipelineSteps.length - 1"
              :class="step.status === 'done' ? 'bg-teal-500' : 'bg-slate-200'"
              class="mt-3.5 h-0.5 flex-1 rounded"
            />
          </li>
        </ol>
      </section>

      <!-- Fil d'échange (F6) -->
      <section class="mb-4">
        <ValidationThread />
      </section>

      <!-- Compose / décision (F7) -->
      <section>
        <ValidationCompose />
      </section>
    </template>
  </div>
</template>
