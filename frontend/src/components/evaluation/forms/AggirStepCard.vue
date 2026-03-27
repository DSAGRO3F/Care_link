<!--
  CareLink - AggirStepCard
  Chemin : frontend/src/components/evaluation/forms/AggirStepCard.vue

  Rôle : Widget de cotation AGGIR — protocole strict (décret 97-427, guide CNSA 2008).
         Le praticien cote d'abord les 4 adverbes S/T/C/H (oui/non),
         le résultat A/B/C est calculé automatiquement.

         Grille 2×2 : S T / C H — chaque tuile cycle null → oui → non → null.
         Résultat en temps réel. "Forcer C" disponible quand le calcul donne B
         (cas limite : activité réalisée spontanément mais résultat à refaire).

         Ref : guide AGGIR CNSA 2008
         https://www.cnsa.fr/sites/default/files/2024-05/guide_aggir_2008.pdf

  Utilisé par : AggirForm.vue
-->
<template>
  <div :class="{ 'aggir-step-card--compact': compact }" class="aggir-step-card">
    <!-- ── Grille 2×2 des adverbes ──────────────────────────────── -->
    <div class="adv-grid">
      <button
        v-for="adv in ADVERBES"
        :key="adv.code"
        :class="tileClass(adv.code)"
        class="adv-tile"
        @click="$emit('toggle', adv.code)"
      >
        <!-- Lettre dominante -->
        <span class="adv-tile__letter">{{ adv.code }}</span>

        <!-- Label + icône info -->
        <span class="adv-tile__label">
          {{ adv.shortLabel }}
          <span class="adv-tile__tooltip-wrap">
            <HelpCircle :size="10" :stroke-width="1.8" class="adv-tile__tooltip-icon" />
            <span class="adv-tile__tooltip">
              <strong>{{ adv.code }} — {{ adv.label }}</strong
              ><br />
              {{ adv.definition }}
            </span>
          </span>
        </span>

        <!-- État oui / non / ? -->
        <span class="adv-tile__state">
          <Check v-if="state.adverbes[adv.code] === true" :size="14" :stroke-width="2.5" />
          <X v-else-if="state.adverbes[adv.code] === false" :size="14" :stroke-width="2.5" />
          <span v-else class="adv-tile__undef">?</span>
        </span>
      </button>
    </div>

    <!-- ── Résultat calculé en temps réel ──────────────────────── -->
    <div v-if="computedResult !== null" class="result-row">
      <!-- Badge résultat -->
      <span
        :class="`result-badge--${(state.forcedC ? 'C' : computedResult).toLowerCase()}`"
        class="result-badge"
      >
        {{ state.forcedC ? 'C' : computedResult }}
      </span>

      <span class="result-label">
        <template v-if="state.forcedC">Forcé C</template>
        <template v-else-if="computedResult === 'A'">Fait seul — autonome</template>
        <template v-else-if="computedResult === 'B'">Autonomie partielle</template>
        <template v-else-if="computedResult === 'C'">Ne fait pas seul</template>
      </span>

      <!-- Bouton Forcer C — visible uniquement si résultat calculé = B -->
      <button
        v-if="computedResult === 'B' && !state.forcedC"
        class="btn-force-c"
        title="Le résultat nécessite d'être entièrement refait à chaque fois (cas limite C — guide CNSA 2008)"
        @click="$emit('forceC')"
      >
        <AlertTriangle :size="11" :stroke-width="2" />
        Forcer C
      </button>

      <!-- Annuler le forçage -->
      <button v-if="state.forcedC" class="btn-unforce" @click="$emit('unforceC')">
        <RotateCcw :size="11" :stroke-width="2" />
        Annuler
      </button>
    </div>

    <!-- Bouton reset (visible si au moins un adverbe coté) -->
    <button v-if="hasAnyAnswer" class="btn-reset" @click="$emit('reset')">
      <RotateCcw :size="10" :stroke-width="2" />
      Réinitialiser
    </button>
  </div>
</template>

<script setup lang="ts">
  /**
   * CareLink - AggirStepCard
   * Chemin : frontend/src/components/evaluation/forms/AggirStepCard.vue
   */
  import { computed } from 'vue';
  import { Check, X, HelpCircle, RotateCcw, AlertTriangle } from 'lucide-vue-next';

  // ── Types exportés ─────────────────────────────────────────────────────

  export interface AdverbeState {
    S: boolean | null;
    T: boolean | null;
    C: boolean | null;
    H: boolean | null;
  }

  export interface VariableState {
    adverbes: AdverbeState;
    forcedC: boolean;
    commentaires: string;
  }

  // ── Props / Emits ──────────────────────────────────────────────────────

  interface Props {
    state: VariableState;
    compact?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), { compact: false });

  defineEmits<{
    (e: 'toggle', code: keyof AdverbeState): void;
    (e: 'forceC'): void;
    (e: 'unforceC'): void;
    (e: 'reset'): void;
  }>();

  // ── Config adverbes (définitions issues du guide CNSA 2008) ────────────

  const ADVERBES = [
    {
      code: 'S' as const,
      label: 'Spontanément',
      shortLabel: 'Spontané',
      definition:
        'Sans avoir à lui dire, à lui rappeler, à lui expliquer ou à lui montrer. ' +
        "Il n'existe pas d'incitation ou de stimulation de la part d'un tiers. " +
        'Ce point est souvent sous-estimé, entraînant des erreurs de codage.',
    },
    {
      code: 'T' as const,
      label: 'Totalement',
      shortLabel: 'Total',
      definition:
        "L'ensemble des activités entrant dans le champ analysé est réalisé. " +
        "La personne effectue la totalité des actes nécessaires à l'activité.",
    },
    {
      code: 'C' as const,
      label: 'Correctement',
      shortLabel: 'Correct',
      definition:
        'Trois aspects : qualité de la réalisation, conformité aux usages, ' +
        'sécurité vis-à-vis de soi et des autres. ' +
        "Ce n'est pas la difficulté de réalisation qui est évaluée.",
    },
    {
      code: 'H' as const,
      label: 'Habituellement',
      shortLabel: 'Habituel',
      definition:
        'Chaque fois que cela est nécessaire et souhaité. ' +
        'Référence au temps et à la fréquence de réalisation. ' +
        "Tient compte d'éventuelles fluctuations dans le temps.",
    },
  ];

  // ── Calcul automatique A / B / C ───────────────────────────────────────

  /**
   * Résultat calculé depuis les 4 adverbes :
   *   tous oui → A | tous non → C | mix → B | incomplet → null
   */
  const computedResult = computed<'A' | 'B' | 'C' | null>(() => {
    const vals = Object.values(props.state.adverbes);
    if (vals.some((v) => v === null)) return null;
    if (vals.every((v) => v === true)) return 'A';
    if (vals.every((v) => v === false)) return 'C';
    return 'B';
  });

  const hasAnyAnswer = computed(() => Object.values(props.state.adverbes).some((v) => v !== null));

  // ── Style des tuiles ───────────────────────────────────────────────────

  function tileClass(code: keyof AdverbeState): string {
    const val = props.state.adverbes[code];
    if (val === true) return 'adv-tile--oui';
    if (val === false) return 'adv-tile--non';
    return 'adv-tile--undef';
  }
</script>

<style scoped>
  .aggir-step-card {
    @apply flex flex-col gap-2.5 w-full;
  }

  /* ── Grille 2×2 ─────────────────────────────────────────────────── */
  .adv-grid {
    @apply grid grid-cols-2 gap-2;
  }

  /* ── Tuile adverbe ──────────────────────────────────────────────── */
  .adv-tile {
    @apply relative flex flex-col items-center gap-1
         p-3 rounded-xl border-2 cursor-pointer
         transition-all duration-150 select-none
         min-h-[72px] justify-center;
  }

  /* États */
  .adv-tile--undef {
    @apply bg-slate-50 border-slate-200 text-slate-400
         hover:border-teal-300 hover:bg-teal-50/50;
  }
  .adv-tile--oui {
    @apply bg-green-50 border-green-400 text-green-700;
  }
  .adv-tile--non {
    @apply bg-red-50 border-red-400 text-red-700;
  }

  /* Lettre dominante */
  .adv-tile__letter {
    @apply text-xl font-bold leading-none;
  }
  .adv-tile--undef .adv-tile__letter {
    @apply text-slate-300;
  }
  .adv-tile--oui .adv-tile__letter {
    @apply text-green-500;
  }
  .adv-tile--non .adv-tile__letter {
    @apply text-red-500;
  }

  /* Label + icône info */
  .adv-tile__label {
    @apply flex items-center gap-1 text-[10px] font-medium leading-none;
  }

  /* État oui/non/? */
  .adv-tile__state {
    @apply text-current;
  }
  .adv-tile__undef {
    @apply text-xs font-bold text-slate-300;
  }

  /* ── Tooltip sur l'icône info ───────────────────────────────────── */
  .adv-tile__tooltip-wrap {
    @apply relative flex items-center;
  }
  .adv-tile__tooltip-icon {
    @apply text-slate-300 hover:text-teal-400 cursor-help transition-colors;
  }
  .adv-tile__tooltip {
    @apply absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-30
         w-52 px-3 py-2 rounded-xl shadow-xl
         bg-slate-800 text-white text-xs leading-relaxed
         pointer-events-none opacity-0 invisible
         transition-opacity duration-150 text-left whitespace-normal;
  }
  .adv-tile__tooltip::after {
    content: '';
    @apply absolute top-full left-1/2 -translate-x-1/2
         border-4 border-transparent border-t-slate-800;
  }
  .adv-tile__tooltip-wrap:hover .adv-tile__tooltip {
    @apply opacity-100 visible;
  }

  /* ── Ligne résultat ─────────────────────────────────────────────── */
  .result-row {
    @apply flex items-center gap-2 flex-wrap pt-1;
  }

  .result-badge {
    @apply flex items-center justify-center w-9 h-9 rounded-lg
         text-white text-base font-bold shadow-sm shrink-0;
  }
  .result-badge--a {
    @apply bg-green-500;
  }
  .result-badge--b {
    @apply bg-amber-500;
  }
  .result-badge--c {
    @apply bg-red-500;
  }

  .result-label {
    @apply flex-1 text-xs text-slate-600 font-medium;
  }

  /* ── Bouton Forcer C ────────────────────────────────────────────── */
  .btn-force-c {
    @apply inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg
         text-xs font-medium cursor-pointer transition-all
         bg-red-50 border border-red-200 text-red-600
         hover:bg-red-100 hover:border-red-300;
  }

  .btn-unforce {
    @apply inline-flex items-center gap-1 px-2 py-1 rounded-lg
         text-xs text-slate-400 cursor-pointer transition-colors
         hover:text-slate-600;
  }

  /* ── Bouton reset ───────────────────────────────────────────────── */
  .btn-reset {
    @apply inline-flex items-center gap-1 text-[11px] text-slate-300
         cursor-pointer transition-colors hover:text-slate-500 w-fit;
  }

  /* ── Mode compact (variables illustratives) ────────────────────── */
  .aggir-step-card--compact .adv-tile {
    @apply min-h-[56px] p-2;
  }
  .aggir-step-card--compact .adv-tile__letter {
    @apply text-base;
  }
  .aggir-step-card--compact .adv-tile__label {
    @apply text-[9px];
  }
  .aggir-step-card--compact .result-badge {
    @apply w-7 h-7 text-sm;
  }
</style>