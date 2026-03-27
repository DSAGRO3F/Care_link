<script setup lang="ts">
  /**
   * EvaluationDraftProgress.vue
   * Chemin : frontend/src/components/evaluation/EvaluationDraftProgress.vue
   *
   * Rôle : Affiche la progression d'une évaluation AGGIR en brouillon
   *        sous forme de chaîne de nœuds cliquables (10 sections).
   *        Nœuds "done" et "active" sont cliquables → ouvre le wizard
   *        à la section correspondante via query param.
   *        Utilisé dans PatientDetailPage (espace Admin).
   */
  import { computed } from 'vue';
  import { useRouter } from 'vue-router';
  import { ClipboardList, ArrowRight } from 'lucide-vue-next';
  import { WIZARD_SECTIONS } from '@/composables/useEvaluationWizard';

  // =============================================================================
  // TYPES
  // =============================================================================

  export interface EvaluationDraft {
    id: number;
    status: string;
    evaluation_data: Record<string, unknown> | null;
    completion_percent: number | null;
    updated_at?: string;
    created_at: string;
  }

  type NodeStatus = 'done' | 'active' | 'todo';

  // =============================================================================
  // PROPS
  // =============================================================================

  const props = defineProps<{
    draft: EvaluationDraft;
    patientId: number;
  }>();

  // =============================================================================
  // ROUTER
  // =============================================================================

  const router = useRouter();

  // =============================================================================
  // COMPUTED — Statut des nœuds
  // =============================================================================

  /**
   * Détermine le statut de chaque nœud à partir des clés de evaluation_data.
   * Logique linéaire : done → done → ... → active → todo → todo → ...
   * Le premier nœud sans données = active, tous ceux d'après = todo.
   */
  const nodeStatuses = computed((): NodeStatus[] => {
    const data = props.draft.evaluation_data ?? {};
    let activeAssigned = false;

    return WIZARD_SECTIONS.map((section) => {
      const sectionData = data[section.id];
      const hasData =
        sectionData !== null &&
        sectionData !== undefined &&
        typeof sectionData === 'object' &&
        Object.keys(sectionData).length > 0;

      if (hasData) return 'done';

      if (!activeAssigned) {
        activeAssigned = true;
        return 'active';
      }

      return 'todo';
    });
  });

  /** Index du nœud actif (-1 si toutes les sections sont complètes) */
  const activeIndex = computed(() => nodeStatuses.value.indexOf('active'));

  /** Nombre de sections complètes */
  const doneCount = computed(() => nodeStatuses.value.filter((s) => s === 'done').length);

  // =============================================================================
  // COMPUTED — Dates formatées
  // =============================================================================

  const formattedCreatedAt = computed(() => {
    if (!props.draft.created_at) return '—';
    return new Date(props.draft.created_at).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    });
  });

  const formattedUpdatedAt = computed(() => {
    if (!props.draft.updated_at) return '';
    const date = new Date(props.draft.updated_at);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return "aujourd'hui";
    if (diffDays === 1) return 'hier';
    return `il y a ${diffDays} jours`;
  });

  /**
   * Calculé localement depuis les nodeStatuses — plus fiable que
   * props.draft.completion_percent (valeur DB potentiellement en retard).
   */
  const completionPercent = computed(() =>
    Math.round((doneCount.value / WIZARD_SECTIONS.length) * 100),
  );

  // =============================================================================
  // COMPUTED — Section active label
  // =============================================================================

  const activeSectionLabel = computed(() => {
    if (activeIndex.value < 0) return 'Toutes les sections complètes';
    return WIZARD_SECTIONS[activeIndex.value].label;
  });

  // =============================================================================
  // COMPUTED — Classe de chaque connecteur
  // =============================================================================

  function connectorClass(index: number): string {
    const current = nodeStatuses.value[index];
    const next = nodeStatuses.value[index + 1];
    if (current === 'done' && next === 'done') return 'eval-chain-connector--done';
    if (current === 'done' && next === 'active') return 'eval-chain-connector--partial';
    return 'eval-chain-connector--todo';
  }

  // =============================================================================
  // NAVIGATION
  // =============================================================================

  /** Reprendre le brouillon à la section active (ou dernière done si toutes complètes) */
  function resumeDraft() {
    const targetSectionId =
      activeIndex.value >= 0
        ? WIZARD_SECTIONS[activeIndex.value].id
        : WIZARD_SECTIONS[Math.max(0, doneCount.value - 1)].id;

    router.push({
      name: 'soins-evaluation-edit',
      params: { patientId: props.patientId, evaluationId: props.draft.id },
      query: { section: targetSectionId },
    });
  }

  /** Cliquer sur un nœud done ou active → ouvre le wizard à cette section */
  function goToSection(sectionId: string, status: NodeStatus) {
    if (status === 'todo') return;
    router.push({
      name: 'soins-evaluation-edit',
      params: { patientId: props.patientId, evaluationId: props.draft.id },
      query: { section: sectionId },
    });
  }
</script>

<template>
  <div class="eval-draft-card">
    <!-- ── En-tête ─────────────────────────────────────────────────────── -->
    <div class="eval-draft-header">
      <div class="eval-draft-header-left">
        <div class="section-icon section-icon--amber">
          <ClipboardList :size="18" :stroke-width="1.8" />
        </div>
        <div>
          <p class="eval-draft-title">Évaluation AGGIR en cours</p>
          <p class="eval-draft-subtitle">
            Démarrée le {{ formattedCreatedAt }}
            <span v-if="formattedUpdatedAt"> · Modifiée {{ formattedUpdatedAt }}</span>
          </p>
        </div>
      </div>
      <div class="eval-draft-header-right">
        <span class="eval-draft-pct">
          {{ completionPercent }}<span class="eval-draft-pct-unit">%</span>
        </span>
        <button class="resume-btn" @click="resumeDraft">
          Reprendre
          <ArrowRight :size="14" :stroke-width="2" />
        </button>
      </div>
    </div>

    <!-- ── Hint section active ───────────────────────────────────────────── -->
    <div class="eval-draft-hint">
      <span class="eval-draft-hint-dot" aria-hidden="true" />
      <span>
        <strong>Étape en cours :</strong> {{ activeSectionLabel }}
        — cliquez sur le nœud pour y accéder directement
      </span>
    </div>

    <!-- ── Chaîne de nœuds ─────────────────────────────────────────────── -->
    <div class="eval-chain-scroll">
      <div class="eval-chain-track">
        <template v-for="(section, index) in WIZARD_SECTIONS" :key="section.id">
          <!-- Nœud -->
          <div class="eval-chain-node">
            <button
              :class="{
                'eval-chain-circle--done': nodeStatuses[index] === 'done',
                'eval-chain-circle--active': nodeStatuses[index] === 'active',
                'eval-chain-circle--todo': nodeStatuses[index] === 'todo',
              }"
              :disabled="nodeStatuses[index] === 'todo'"
              :title="
                section.label +
                (nodeStatuses[index] === 'done'
                  ? ' — Complété'
                  : nodeStatuses[index] === 'active'
                    ? ' — En cours'
                    : ' — À faire')
              "
              :aria-label="section.label"
              class="eval-chain-circle"
              @click="goToSection(section.id, nodeStatuses[index])"
            >
              <!-- Coche si complété, numéro sinon -->
              <svg
                v-if="nodeStatuses[index] === 'done'"
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.5"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span v-else class="eval-chain-circle-num">{{ index + 1 }}</span>
            </button>

            <!-- Label sous le nœud -->
            <span
              :class="{ 'eval-chain-label--active': nodeStatuses[index] === 'active' }"
              class="eval-chain-label"
            >
              {{ section.label }}
            </span>
          </div>

          <!-- Connecteur (pas après le dernier nœud) -->
          <div
            v-if="index < WIZARD_SECTIONS.length - 1"
            :class="connectorClass(index)"
            class="eval-chain-connector"
          />
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
  /* ── Carte conteneur ──────────────────────────────────────────────────── */
  .eval-draft-card {
    @apply rounded-2xl border border-slate-200 bg-white overflow-hidden;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  }

  /* ── En-tête ──────────────────────────────────────────────────────────── */
  .eval-draft-header {
    @apply flex items-center justify-between gap-4 px-5 py-4;
    border-bottom: 1px solid #f1f5f9;
  }

  .eval-draft-header-left {
    @apply flex items-center gap-3 min-w-0;
  }

  .eval-draft-header-right {
    @apply flex items-center gap-3 flex-shrink-0;
  }

  .eval-draft-title {
    @apply text-sm font-semibold text-slate-800 leading-tight;
  }

  .eval-draft-subtitle {
    @apply text-xs text-slate-400 mt-0.5 leading-tight;
  }

  .eval-draft-pct {
    @apply text-xl font-bold text-teal-600;
  }

  .eval-draft-pct-unit {
    @apply text-sm font-medium text-slate-400 ml-0.5;
  }

  /* ── Bouton Reprendre ─────────────────────────────────────────────────── */
  .resume-btn {
    @apply inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl
         text-sm font-semibold text-teal-700 cursor-pointer;
    background: #f0fdfa;
    border: 1.5px solid #99f6e4;
    transition: all 0.2s ease;
  }

  .resume-btn:hover {
    background: #ccfbf1;
    border-color: #5eead4;
    box-shadow: 0 2px 8px rgba(13, 148, 136, 0.12);
  }

  /* ── Hint ─────────────────────────────────────────────────────────────── */
  .eval-draft-hint {
    @apply flex items-center gap-2 mx-5 my-3 px-3 py-2 rounded-lg text-xs text-teal-700;
    background: #f0fdfa;
    border: 1px solid #99f6e4;
  }

  .eval-draft-hint-dot {
    @apply flex-shrink-0 rounded-full;
    width: 8px;
    height: 8px;
    background: #14b8a6;
    animation: eval-chain-pulse 2s ease-in-out infinite;
  }

  /* ── Scroll horizontal ────────────────────────────────────────────────── */
  .eval-chain-scroll {
    @apply px-5 pb-5 overflow-x-auto;
    /* Masque la scrollbar sur webkit sans perdre la fonctionnalité */
    scrollbar-width: thin;
    scrollbar-color: #e2e8f0 transparent;
  }

  .eval-chain-scroll::-webkit-scrollbar {
    height: 4px;
  }

  .eval-chain-scroll::-webkit-scrollbar-track {
    background: transparent;
  }

  .eval-chain-scroll::-webkit-scrollbar-thumb {
    background: #e2e8f0;
    border-radius: 2px;
  }

  /* ── Track principal ──────────────────────────────────────────────────── */
  .eval-chain-track {
    @apply flex items-center;
    min-width: max-content;
    padding-top: 4px;
  }

  /* ── Nœud ─────────────────────────────────────────────────────────────── */
  .eval-chain-node {
    @apply flex flex-col items-center;
    width: 56px;
  }

  /* Cercle du nœud */
  .eval-chain-circle {
    @apply flex items-center justify-center rounded-full cursor-pointer;
    width: 36px;
    height: 36px;
    transition:
      transform 0.15s ease,
      box-shadow 0.15s ease;
    position: relative;
    z-index: 1;
    border: none;
    outline: none;
  }

  .eval-chain-circle:not(:disabled):hover {
    transform: scale(1.1);
  }

  .eval-chain-circle:disabled {
    cursor: default;
  }

  /* Variante done */
  .eval-chain-circle--done {
    background: #14b8a6;
    color: white;
    box-shadow: 0 2px 6px rgba(20, 184, 166, 0.3);
  }

  /* Variante active — pulsante */
  .eval-chain-circle--active {
    background: white;
    color: #14b8a6;
    border: 2.5px solid #14b8a6 !important;
    width: 40px;
    height: 40px;
    animation: eval-chain-pulse 2s ease-in-out infinite;
  }

  /* Variante todo */
  .eval-chain-circle--todo {
    background: #f8fafc;
    color: #cbd5e1;
    border: 2px solid #e2e8f0 !important;
  }

  .eval-chain-circle-num {
    @apply text-xs font-bold;
  }

  /* ── Label sous le nœud ───────────────────────────────────────────────── */
  .eval-chain-label {
    @apply text-center text-slate-500 mt-2 leading-tight;
    font-size: 10px;
    font-weight: 500;
    max-width: 54px;
    word-break: break-word;
    hyphens: auto;
  }

  .eval-chain-label--active {
    @apply text-teal-600 font-bold;
  }

  /* ── Connecteur ───────────────────────────────────────────────────────── */
  .eval-chain-connector {
    height: 2px;
    width: 20px;
    flex-shrink: 0;
    /* Décalage vertical pour centrer sur les cercles (avant le label de 24px) */
    margin-bottom: 24px;
    border-radius: 1px;
  }

  .eval-chain-connector--done {
    background: #14b8a6;
  }

  .eval-chain-connector--partial {
    background: linear-gradient(to right, #14b8a6 50%, #e2e8f0 50%);
  }

  .eval-chain-connector--todo {
    background: #e2e8f0;
  }

  /* ── Icônes de section (partagé avec PatientDetailPage) ───────────────── */
  /* NB : section-icon et section-icon--amber sont déjà dans main.css       */
  /* On les redéclare ici pour l'autonomie du composant si besoin            */
</style>