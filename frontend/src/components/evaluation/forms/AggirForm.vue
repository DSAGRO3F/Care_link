<!--
  CareLink - AggirForm
  Chemin : frontend/src/components/evaluation/forms/AggirForm.vue

  Rôle : Formulaire de saisie AGGIR — section 3/10 du wizard évaluation.
         Grille de 17 variables (10 discriminantes + 7 illustratives).
         Protocole strict CNSA 2008 : cotation adverbe par adverbe (S/T/C/H),
         résultat A/B/C calculé automatiquement.

  Pattern : identique à UsagerForm / ContactsForm
    - Props : patient + initialData (brouillon)
    - Emits : update:data  → { AggirVariable: [...] }
              update:status → 'empty' | 'partial' | 'complete'
    - onMounted : désérialisation brouillon → émission
    - watch(formData, deep) : émission à chaque changement
-->
<template>
  <div class="aggir-form">
    <!-- ================================================================= -->
    <!-- BLOC 1 — VARIABLES DISCRIMINANTES                                 -->
    <!-- ================================================================= -->
    <fieldset class="form-fieldset">
      <legend class="form-legend">
        <span class="form-legend-icon form-legend-icon--teal">
          <BarChart3 :size="15" :stroke-width="1.8" />
        </span>
        Variables discriminantes
        <span class="aggir-section-badge aggir-section-badge--discr">
          Entrent dans le calcul du GIR
        </span>
      </legend>

      <!-- Barre de progression -->
      <div class="aggir-progress">
        <div class="aggir-progress__bar">
          <div :style="{ width: `${discrProgressPercent}%` }" class="aggir-progress__fill" />
        </div>
        <span class="aggir-progress__label">
          {{ discrCompletedCount }} / {{ DISCRIMINANTES.length }} cotées
        </span>
      </div>

      <div class="aggir-grid">
        <div
          v-for="variable in DISCRIMINANTES"
          :key="variable.nom"
          :class="[
            'aggir-card',
            getCardClass(variable),
            { 'aggir-card--wide': variable.sousVariables },
          ]"
        >
          <!-- En-tête de la carte -->
          <div class="aggir-card__header">
            <span class="aggir-card__icon">
              <component :is="VAR_ICONS[variable.nom]" :size="15" :stroke-width="1.8" />
            </span>
            <span class="aggir-card__name">{{ variable.nom }}</span>
            <!-- Chip résultat global (visible dès que la variable est complète) -->
            <span
              v-if="getVariableResult(variable) !== null"
              :class="`aggir-result-chip--${getVariableResult(variable)!.toLowerCase()}`"
              class="aggir-result-chip"
            >
              {{ getVariableResult(variable) }}
            </span>
          </div>

          <!-- Variable avec sous-variables — grille côte à côte (Option 3) -->
          <div v-if="variable.sousVariables" class="aggir-card__sous-vars">
            <div
              :style="{ gridTemplateColumns: `repeat(${variable.sousVariables.length}, 1fr)` }"
              class="aggir-sv-grid"
            >
              <div v-for="sv in variable.sousVariables" :key="sv" class="aggir-sv-col">
                <div class="aggir-sv-header">
                  <span class="aggir-sv-name">{{ sv }}</span>
                  <span
                    v-if="getSvResult(`${variable.nom}__${sv}`) !== null"
                    :class="`aggir-result-chip--${getSvResult(`${variable.nom}__${sv}`)!.toLowerCase()}`"
                    class="aggir-result-chip aggir-result-chip--sm"
                  >
                    {{ getSvResult(`${variable.nom}__${sv}`) }}
                  </span>
                </div>
                <AggirStepCard
                  :state="formData[`${variable.nom}__${sv}`]"
                  @toggle="(code) => toggleAdverbe(`${variable.nom}__${sv}`, code)"
                  @force-c="forceC(`${variable.nom}__${sv}`)"
                  @unforce-c="unforceC(`${variable.nom}__${sv}`)"
                  @reset="resetState(`${variable.nom}__${sv}`)"
                />
                <!-- Commentaire visible si variable complète -->
                <InputText
                  v-if="getSvResult(`${variable.nom}__${sv}`) !== null"
                  v-model="formData[`${variable.nom}__${sv}`].commentaires"
                  :placeholder="`Commentaire ${sv.toLowerCase()}…`"
                  class="w-full aggir-comment-input"
                />
              </div>
            </div>

            <!-- Résultat global de la variable parente -->
            <div class="aggir-parent-result">
              <span class="aggir-parent-result__label">Résultat global :</span>
              <span
                v-if="getVariableResult(variable) !== null"
                :class="`aggir-result-chip--${getVariableResult(variable)!.toLowerCase()}`"
                class="aggir-result-chip"
              >
                {{ getVariableResult(variable) }}
              </span>
              <span v-else class="aggir-parent-result__pending">
                En attente des sous-variables
              </span>
            </div>
          </div>

          <!-- Variable simple -->
          <div v-else class="aggir-card__flow">
            <AggirStepCard
              :state="formData[variable.nom]"
              @toggle="(code) => toggleAdverbe(variable.nom, code)"
              @force-c="forceC(variable.nom)"
              @unforce-c="unforceC(variable.nom)"
              @reset="resetState(variable.nom)"
            />
            <InputText
              v-if="getVariableResult(variable) !== null"
              v-model="formData[variable.nom].commentaires"
              placeholder="Commentaire (optionnel)…"
              class="w-full aggir-comment-input"
            />
          </div>
        </div>
      </div>
    </fieldset>

    <!-- ================================================================= -->
    <!-- BANDEAU GIR — Score calculé en temps réel                        -->
    <!-- ================================================================= -->
    <div :class="girBannerClass" class="gir-banner">
      <!-- État idle : discriminantes incomplètes -->
      <template v-if="girState.status === 'idle'">
        <div class="gir-banner__idle">
          <Activity :size="15" :stroke-width="1.8" class="shrink-0 text-slate-400" />
          <span class="gir-banner__idle-text">
            Cotez les {{ DISCRIMINANTES.length }} variables discriminantes pour calculer le GIR
          </span>
          <span class="gir-banner__counter">
            {{ discrCompletedCount }} / {{ DISCRIMINANTES.length }}
          </span>
        </div>
      </template>

      <!-- État loading : debounce en cours -->
      <template v-else-if="girState.status === 'loading'">
        <div class="gir-banner__loading">
          <Loader2 :size="15" :stroke-width="2" class="animate-spin shrink-0 text-teal-500" />
          <span class="text-sm text-slate-500">Calcul du GIR en cours…</span>
        </div>
      </template>

      <!-- État erreur -->
      <template v-else-if="girState.status === 'error'">
        <div class="gir-banner__error-row">
          <AlertCircle :size="15" :stroke-width="1.8" class="shrink-0 text-red-400" />
          <span class="text-sm text-red-500"
            >Impossible de calculer le GIR — vérifiez la connexion</span
          >
        </div>
      </template>

      <!-- État résultat : GIR calculé -->
      <template v-else-if="girState.status === 'ready' && girState.score !== null">
        <!-- Score + libellé -->
        <div class="gir-banner__score">
          <span :class="['gir-chip', `gir-chip--${girState.score}`]">
            GIR {{ girState.score }}
          </span>
          <span class="gir-banner__label">{{ GIR_LABELS[girState.score] }}</span>
        </div>

        <!-- Règle visuelle 1 → 6 -->
        <div class="gir-scale">
          <span class="gir-scale__legend">+ dépendant</span>
          <div class="gir-scale__track">
            <div
              v-for="n in 6"
              :key="n"
              :class="[
                'gir-scale__step',
                `gir-scale__step--${n}`,
                { 'gir-scale__step--active': n === girState.score },
              ]"
            >
              {{ n }}
            </div>
          </div>
          <span class="gir-scale__legend">autonome</span>
        </div>
      </template>
    </div>

    <!-- ================================================================= -->
    <!-- BLOC 2 — VARIABLES ILLUSTRATIVES                                  -->
    <!-- ================================================================= -->
    <fieldset class="form-fieldset">
      <legend class="form-legend">
        <span class="form-legend-icon form-legend-icon--teal">
          <ListChecks :size="15" :stroke-width="1.8" />
        </span>
        Variables illustratives
        <span class="aggir-section-badge aggir-section-badge--illus">
          Informationnel — n'entrent pas dans le GIR
        </span>
      </legend>

      <div class="aggir-grid aggir-grid--illustrative">
        <div
          v-for="variable in ILLUSTRATIVES"
          :key="variable.nom"
          :class="getCardClass(variable)"
          class="aggir-card aggir-card--illustrative"
        >
          <div class="aggir-card__header">
            <span class="aggir-card__icon">
              <component :is="VAR_ICONS[variable.nom]" :size="14" :stroke-width="1.8" />
            </span>
            <span class="aggir-card__name">{{ variable.nom }}</span>
            <span
              v-if="getVariableResult(variable) !== null"
              :class="`aggir-result-chip--${getVariableResult(variable)!.toLowerCase()}`"
              class="aggir-result-chip"
            >
              {{ getVariableResult(variable) }}
            </span>
          </div>
          <AggirStepCard
            :state="formData[variable.nom]"
            compact
            @toggle="(code) => toggleAdverbe(variable.nom, code)"
            @force-c="forceC(variable.nom)"
            @unforce-c="unforceC(variable.nom)"
            @reset="resetState(variable.nom)"
          />
        </div>
      </div>
    </fieldset>
  </div>
</template>

<script setup lang="ts">
  /**
   * CareLink - AggirForm
   * Chemin : frontend/src/components/evaluation/forms/AggirForm.vue
   */
  import { reactive, computed, watch, onMounted, onUnmounted, type Component } from 'vue';
  import {
    BarChart3,
    ListChecks,
    MessageSquare,
    Compass,
    Droplets,
    Shirt,
    Utensils,
    Activity,
    ArrowLeftRight,
    Home,
    Map,
    Bell,
    ChefHat,
    Sparkles,
    Car,
    ShoppingCart,
    Wallet,
    Pill,
    Sun,
    Loader2,
    AlertCircle,
  } from 'lucide-vue-next';
  import InputText from 'primevue/inputtext';
  import { api } from '@/services';
  import AggirStepCard, { type VariableState, type AdverbeState } from './AggirStepCard.vue';
  import type { SectionStatus, WizardSectionData } from '@/composables/useEvaluationWizard';
  import type { PatientResponse } from '@/types';

  // ── Props / Emits ──────────────────────────────────────────────────────

  interface Props {
    patient: PatientResponse | null;
    initialData?: WizardSectionData;
    /** Requis pour l'appel compute-gir — à passer depuis EvaluationWizard.vue */
    evaluationId?: number | null;
  }

  const props = defineProps<Props>();

  const emit = defineEmits<{
    (e: 'update:data', data: WizardSectionData): void;
    (e: 'update:status', status: SectionStatus): void;
  }>();

  // ── Configuration des 17 variables AGGIR ──────────────────────────────

  interface AggirVarConfig {
    nom: string;
    type: 'discriminante' | 'illustrative';
    sousVariables?: readonly string[];
  }

  // Ordre conforme au guide CNSA 2008 :
  // logique "déroulement d'une journée" + Orientation et Cohérence en dernier
  // (leur évaluation est éclairée par toutes les autres variables)
  const DISCRIMINANTES: readonly AggirVarConfig[] = [
    { nom: 'Transferts', type: 'discriminante' },
    { nom: 'Déplacements intérieurs', type: 'discriminante' },
    { nom: 'Toilette', type: 'discriminante', sousVariables: ['Haut', 'Bas'] },
    { nom: 'Habillage', type: 'discriminante', sousVariables: ['Haut', 'Moyen', 'Bas'] },
    { nom: 'Alimentation', type: 'discriminante', sousVariables: ['Se servir', 'Manger'] },
    { nom: 'Élimination', type: 'discriminante', sousVariables: ['Urinaire', 'Fécale'] },
    { nom: 'Déplacements extérieurs', type: 'discriminante' },
    { nom: 'Alerter', type: 'discriminante' },
    { nom: 'Orientation', type: 'discriminante', sousVariables: ['Temps', 'Espace'] },
    { nom: 'Cohérence', type: 'discriminante', sousVariables: ['Communication', 'Comportement'] },
  ];

  const ILLUSTRATIVES: readonly AggirVarConfig[] = [
    { nom: 'Gestion', type: 'illustrative' },
    { nom: 'Cuisine', type: 'illustrative' },
    { nom: 'Ménage', type: 'illustrative' },
    { nom: 'Transports', type: 'illustrative' },
    { nom: 'Achats', type: 'illustrative' },
    { nom: 'Suivi du traitement', type: 'illustrative' },
    { nom: 'Activités de temps libre', type: 'illustrative' },
  ];

  const AGGIR_VARIABLES: readonly AggirVarConfig[] = [...DISCRIMINANTES, ...ILLUSTRATIVES];

  const VAR_ICONS: Record<string, Component> = {
    Cohérence: MessageSquare,
    Orientation: Compass,
    Toilette: Droplets,
    Habillage: Shirt,
    Alimentation: Utensils,
    Élimination: Activity,
    Transferts: ArrowLeftRight,
    'Déplacements intérieurs': Home,
    'Déplacements extérieurs': Map,
    Alerter: Bell,
    Gestion: Wallet,
    Cuisine: ChefHat,
    Ménage: Sparkles,
    Transports: Car,
    Achats: ShoppingCart,
    'Suivi du traitement': Pill,
    'Activités de temps libre': Sun,
  };

  // ── Constantes GIR ─────────────────────────────────────────────────────

  const GIR_LABELS: Record<number, string> = {
    1: 'Dépendance totale',
    2: 'Dépendance lourde',
    3: 'Dépendance modérée',
    4: 'Dépendance partielle',
    5: 'Dépendance légère',
    6: 'Autonomie',
  };

  /**
   * Mapping clés formData (feuilles) → codes attendus par POST /compute-gir
   * Seules les feuilles (sous-variables ou variables simples) sont envoyées ;
   * calculator.py reconstruit lui-même les variables parentes.
   */
  const FRONTEND_TO_API_CODE: Record<string, string> = {
    Transferts: 'TRANSFERTS',
    'Deplacements interieurs': 'DEPLACEMENT_INTERIEUR',
    Toilette__Haut: 'TOILETTE_HAUT',
    Toilette__Bas: 'TOILETTE_BAS',
    Habillage__Haut: 'HABILLAGE_HAUT',
    Habillage__Moyen: 'HABILLAGE_MOYEN',
    Habillage__Bas: 'HABILLAGE_BAS',
    'Alimentation__Se servir': 'SE_SERVIR',
    Alimentation__Manger: 'MANGER',
    Elimination__Urinaire: 'ELIMINATION_URINAIRE',
    Elimination__Fecale: 'ELIMINATION_FECALE',
    'Deplacements exterieurs': 'DEPLACEMENT_EXTERIEUR',
    Alerter: 'ALERTER',
    Orientation__Temps: 'ORIENTATION_TEMPS',
    Orientation__Espace: 'ORIENTATION_ESPACE',
    Coherence__Communication: 'COMMUNICATION',
    Coherence__Comportement: 'COMPORTEMENT',
  };

  // ── État du bandeau GIR ────────────────────────────────────────────────

  interface GirState {
    status: 'idle' | 'loading' | 'ready' | 'error';
    score: number | null;
  }

  const girState = reactive<GirState>({ status: 'idle', score: null });

  const girBannerClass = computed(() => ({
    'gir-banner--idle': girState.status === 'idle',
    'gir-banner--loading': girState.status === 'loading',
    'gir-banner--ready': girState.status === 'ready',
    'gir-banner--error': girState.status === 'error',
  }));

  // ── Appel API compute-gir (debounce 1500 ms) ───────────────────────────

  let girDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  function buildGirPayload() {
    return {
      variables: Object.entries(FRONTEND_TO_API_CODE).map(([frontendKey, apiCode]) => {
        const state = formData[frontendKey];
        return {
          code: apiCode,
          adverbes: (['S', 'T', 'C', 'H'] as const).map((q) => ({
            question: q,
            // forcedC → tous les adverbes false (résultat C côté backend)
            reponse: state?.forcedC ? false : (state?.adverbes[q] ?? false),
          })),
        };
      }),
    };
  }

  async function triggerGirCompute() {
    // Réinitialiser si les discriminantes ne sont pas toutes cotées
    if (discrCompletedCount.value < DISCRIMINANTES.length) {
      if (girDebounceTimer) {
        clearTimeout(girDebounceTimer);
        girDebounceTimer = null;
      }
      girState.status = 'idle';
      girState.score = null;
      return;
    }

    if (!props.patient?.id || !props.evaluationId) return;

    girState.status = 'loading';
    if (girDebounceTimer) clearTimeout(girDebounceTimer);

    girDebounceTimer = setTimeout(async () => {
      try {
        const { data } = await api.post<{ gir_score: number }>(
          `/patients/${props.patient!.id}/evaluations/${props.evaluationId}/compute-gir`,
          buildGirPayload(),
        );
        girState.score = data.gir_score;
        girState.status = 'ready';
      } catch (e) {
        girState.status = 'error';
        girState.score = null;
        if (import.meta.env.DEV) console.warn('[AggirForm] compute-gir error:', e);
      }
    }, 1500);
  }

  onUnmounted(() => {
    if (girDebounceTimer) clearTimeout(girDebounceTimer);
  });

  // ── Initialisation du formData ─────────────────────────────────────────

  function createState(): VariableState {
    return {
      adverbes: { S: null, T: null, C: null, H: null },
      forcedC: false,
      commentaires: '',
    };
  }

  function buildInitialFormData(): Record<string, VariableState> {
    const data: Record<string, VariableState> = {};
    for (const v of AGGIR_VARIABLES) {
      if (v.sousVariables) {
        for (const sv of v.sousVariables) {
          data[`${v.nom}__${sv}`] = createState();
        }
      } else {
        data[v.nom] = createState();
      }
    }
    return data;
  }

  const formData = reactive<Record<string, VariableState>>(buildInitialFormData());

  // ── Mutations ──────────────────────────────────────────────────────────

  /**
   * Cycle : null → true → false → null
   */
  function toggleAdverbe(key: string, code: keyof AdverbeState) {
    if (!formData[key]) return;
    const current = formData[key].adverbes[code];
    if (current === null) formData[key].adverbes[code] = true;
    else if (current === true) formData[key].adverbes[code] = false;
    else formData[key].adverbes[code] = null;
    // Si on modifie un adverbe, on lève le forçage C
    formData[key].forcedC = false;
  }

  function forceC(key: string) {
    if (formData[key]) formData[key].forcedC = true;
  }

  function unforceC(key: string) {
    if (formData[key]) formData[key].forcedC = false;
  }

  function resetState(key: string) {
    if (formData[key]) {
      formData[key].adverbes = { S: null, T: null, C: null, H: null };
      formData[key].forcedC = false;
      formData[key].commentaires = '';
    }
  }

  // ── Calcul du résultat par clé ─────────────────────────────────────────

  /**
   * Résultat pour une clé simple (variable ou sous-variable).
   * Retourne null si incomplet.
   */
  function computeKeyResult(key: string): 'A' | 'B' | 'C' | null {
    const s = formData[key];
    if (!s) return null;
    if (s.forcedC) return 'C';
    const vals = Object.values(s.adverbes);
    if (vals.some((v) => v === null)) return null;
    if (vals.every((v) => v === true)) return 'A';
    if (vals.every((v) => v === false)) return 'C';
    return 'B';
  }

  function getSvResult(key: string): 'A' | 'B' | 'C' | null {
    return computeKeyResult(key);
  }

  /**
   * Résultat global pour une variable parente (avec sous-variables).
   * Règles spécifiques par variable (guide CNSA 2008) :
   *   Toilette, Habillage, Cohérence, Orientation, Alimentation : AA=A, CC=C, autres=B
   *   Élimination : AA=A, si l'un des deux = C → C, autres=B
   */
  function computeParentResult(varConfig: AggirVarConfig): 'A' | 'B' | 'C' | null {
    if (!varConfig.sousVariables) return null;
    const results = varConfig.sousVariables.map((sv) =>
      computeKeyResult(`${varConfig.nom}__${sv}`),
    );
    if (results.some((r) => r === null)) return null;

    // Élimination : présence d'un seul C → C global
    if (varConfig.nom === 'Élimination') {
      if (results.every((r) => r === 'A')) return 'A';
      if (results.some((r) => r === 'C')) return 'C';
      return 'B';
    }
    // Autres variables à sous-variables : AA=A, CC=C, sinon B
    if (results.every((r) => r === 'A')) return 'A';
    if (results.every((r) => r === 'C')) return 'C';
    return 'B';
  }

  function getVariableResult(varConfig: AggirVarConfig): 'A' | 'B' | 'C' | null {
    if (varConfig.sousVariables) return computeParentResult(varConfig);
    return computeKeyResult(varConfig.nom);
  }

  // ── Style des cartes ───────────────────────────────────────────────────

  function getCardClass(varConfig: AggirVarConfig): string {
    const result = getVariableResult(varConfig);
    if (result === null) return '';
    return `aggir-card--${result.toLowerCase()}`;
  }

  // ── Progression ────────────────────────────────────────────────────────

  const discrCompletedCount = computed(
    () => DISCRIMINANTES.filter((v) => getVariableResult(v) !== null).length,
  );

  const discrProgressPercent = computed(() =>
    Math.round((discrCompletedCount.value / DISCRIMINANTES.length) * 100),
  );

  // ── Statut de section ──────────────────────────────────────────────────

  const sectionStatus = computed<SectionStatus>(() => {
    if (discrCompletedCount.value === 0) return 'empty';
    if (discrCompletedCount.value === DISCRIMINANTES.length) return 'complete';
    return 'partial';
  });

  // ── Sérialisation → format JSON natif AGGIR ────────────────────────────

  interface AggirAdverbe {
    Question: string;
    Reponse: string;
  }
  interface AggirSvOut {
    Nom: string;
    Resultat: string;
    Commentaires: string;
    AggirAdverbes: AggirAdverbe[];
  }
  interface AggirVarOut {
    Nom: string;
    Resultat: string;
    Commentaires?: string;
    AggirAdverbes?: AggirAdverbe[];
    AggirSousVariable?: AggirSvOut[];
  }

  function stateToAdverbes(state: VariableState): AggirAdverbe[] {
    return (['S', 'T', 'C', 'H'] as const).map((code) => ({
      Question: code,
      Reponse: state.adverbes[code] === true ? 'oui' : 'non',
    }));
  }

  function serialize(): { AggirVariable: AggirVarOut[] } {
    const variables: AggirVarOut[] = AGGIR_VARIABLES.map((varConfig) => {
      if (varConfig.sousVariables) {
        const sousVars: AggirSvOut[] = varConfig.sousVariables.map((sv) => {
          const key = `${varConfig.nom}__${sv}`;
          const state = formData[key];
          return {
            Nom: sv,
            Resultat: computeKeyResult(key) ?? '',
            Commentaires: state?.commentaires ?? '',
            AggirAdverbes: stateToAdverbes(state),
          };
        });
        return {
          Nom: varConfig.nom,
          Resultat: computeParentResult(varConfig) ?? '',
          AggirSousVariable: sousVars,
        };
      } else {
        const state = formData[varConfig.nom];
        return {
          Nom: varConfig.nom,
          Resultat: computeKeyResult(varConfig.nom) ?? '',
          Commentaires: state?.commentaires ?? '',
          AggirAdverbes: stateToAdverbes(state),
        };
      }
    });
    return { AggirVariable: variables };
  }

  // ── Désérialisation ← brouillon ────────────────────────────────────────

  function adverbesToState(adverbes: AggirAdverbe[] | undefined): AdverbeState {
    const s: AdverbeState = { S: null, T: null, C: null, H: null };
    if (!adverbes) return s;
    for (const adv of adverbes) {
      if (['S', 'T', 'C', 'H'].includes(adv.Question)) {
        s[adv.Question as keyof AdverbeState] = adv.Reponse === 'oui';
      }
    }
    return s;
  }

  function deserialize(data: WizardSectionData) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- AggirVariable est un tableau polymorphe du JSON Schema
    const vars: any[] = data.AggirVariable;
    if (!Array.isArray(vars)) return;

    for (const v of vars) {
      if (Array.isArray(v.AggirSousVariable)) {
        for (const sv of v.AggirSousVariable) {
          const key = `${v.Nom}__${sv.Nom}`;
          if (!formData[key]) continue;
          formData[key].adverbes = adverbesToState(sv.AggirAdverbes);
          formData[key].commentaires = sv.Commentaires ?? '';
          formData[key].forcedC = false;
        }
      } else {
        const key = v.Nom;
        if (!formData[key]) continue;
        formData[key].adverbes = adverbesToState(v.AggirAdverbes);
        formData[key].commentaires = v.Commentaires ?? '';
        formData[key].forcedC = false;
      }
    }
  }

  // ── Cycle de vie ───────────────────────────────────────────────────────

  onMounted(() => {
    if (props.initialData?.AggirVariable) {
      deserialize(props.initialData);
    }
    emit('update:data', serialize());
    emit('update:status', sectionStatus.value);
  });

  watch(
    formData,
    () => {
      emit('update:data', serialize());
      emit('update:status', sectionStatus.value);
      triggerGirCompute();
      if (import.meta.env.DEV) {
        // eslint-disable-next-line no-console
        console.log('[AggirForm] update — status:', sectionStatus.value);
      }
    },
    { deep: true },
  );
</script>

<style scoped>
  .aggir-form {
    @apply flex flex-col gap-6;
  }

  /* ── Badges de section ────────────────────────────────────────── */
  .aggir-section-badge {
    @apply ml-2 text-xs px-2 py-0.5 rounded-full font-normal;
  }
  .aggir-section-badge--discr {
    @apply bg-teal-50 text-teal-700 border border-teal-200;
  }
  .aggir-section-badge--illus {
    @apply bg-slate-100 text-slate-500 border border-slate-200;
  }

  /* ── Barre de progression ─────────────────────────────────────── */
  .aggir-progress {
    @apply flex items-center gap-3 mb-4;
  }
  .aggir-progress__bar {
    @apply flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden;
  }
  .aggir-progress__fill {
    @apply h-full bg-teal-500 rounded-full transition-all duration-500;
  }
  .aggir-progress__label {
    @apply text-xs text-slate-400 whitespace-nowrap;
  }

  /* ── Grilles ──────────────────────────────────────────────────── */
  .aggir-grid {
    @apply grid grid-cols-1 sm:grid-cols-2 gap-3;
    grid-auto-flow: dense;
  }
  /* Les cartes avec sous-variables occupent les 2 colonnes */
  .aggir-card--wide {
    @apply sm:col-span-2;
  }
  .aggir-grid--illustrative {
    @apply grid-cols-2 sm:grid-cols-3 lg:grid-cols-4;
  }
  /* Sous-variables côte à côte dans les cartes wide */
  .aggir-sv-grid {
    @apply grid gap-3;
  }
  .aggir-sv-col {
    @apply flex flex-col gap-2 pl-3 border-l-2 border-slate-200;
  }

  /* ── Carte variable ───────────────────────────────────────────── */
  .aggir-card {
    @apply flex flex-col gap-3 p-4 rounded-xl border border-slate-200 bg-white
         transition-colors duration-200;
  }
  .aggir-card--a {
    @apply border-green-200 bg-green-50/40;
  }
  .aggir-card--b {
    @apply border-amber-200 bg-amber-50/40;
  }
  .aggir-card--c {
    @apply border-red-200   bg-red-50/40;
  }
  .aggir-card--illustrative {
    @apply p-3 gap-2;
  }

  /* En-tête */
  .aggir-card__header {
    @apply flex items-center gap-2;
  }
  .aggir-card__icon {
    @apply flex items-center justify-center w-7 h-7 rounded-lg
         bg-slate-100 text-slate-500 shrink-0;
  }
  .aggir-card--a .aggir-card__icon {
    @apply bg-green-100 text-green-600;
  }
  .aggir-card--b .aggir-card__icon {
    @apply bg-amber-100 text-amber-600;
  }
  .aggir-card--c .aggir-card__icon {
    @apply bg-red-100   text-red-600;
  }

  .aggir-card__name {
    @apply flex-1 text-sm font-semibold text-slate-700 leading-tight;
  }

  /* Chips résultat */
  .aggir-result-chip {
    @apply px-2 py-0.5 rounded-md text-xs font-bold text-white shrink-0;
  }
  .aggir-result-chip--sm {
    @apply px-1.5 py-0 text-[11px];
  }
  .aggir-result-chip--a {
    @apply bg-green-500;
  }
  .aggir-result-chip--b {
    @apply bg-amber-500;
  }
  .aggir-result-chip--c {
    @apply bg-red-500;
  }

  /* ── Sous-variables ───────────────────────────────────────────── */
  .aggir-card__sous-vars {
    @apply flex flex-col gap-3;
  }
  /* .aggir-sv-row remplacé par .aggir-sv-col */
  .aggir-sv-header {
    @apply flex items-center gap-2;
  }
  .aggir-sv-name {
    @apply flex-1 text-xs font-medium text-slate-500 uppercase tracking-wide;
  }

  /* Résultat global variable parente */
  .aggir-parent-result {
    @apply flex items-center gap-2 pt-2 border-t border-slate-200 mt-1;
  }
  .aggir-parent-result__label {
    @apply text-xs text-slate-500;
  }
  .aggir-parent-result__pending {
    @apply text-xs text-slate-400 italic;
  }

  /* Variable simple */
  .aggir-card__flow {
    @apply flex flex-col gap-2;
  }

  /* ── Bandeau GIR ──────────────────────────────────────────────── */
  .gir-banner {
    @apply rounded-xl border px-5 py-3.5 transition-all duration-300;
  }
  .gir-banner--idle {
    @apply border-slate-200 bg-slate-50;
  }
  .gir-banner--loading {
    @apply border-teal-100 bg-teal-50/50;
  }
  .gir-banner--ready {
    @apply border-teal-200 bg-white;
  }
  .gir-banner--error {
    @apply border-red-200 bg-red-50/50;
  }

  /* Ligne idle */
  .gir-banner__idle {
    @apply flex items-center gap-3;
  }
  .gir-banner__idle-text {
    @apply flex-1 text-sm text-slate-400;
  }
  .gir-banner__counter {
    @apply text-xs font-semibold text-slate-400 tabular-nums;
  }

  /* Ligne loading */
  .gir-banner__loading {
    @apply flex items-center gap-3;
  }

  /* Ligne erreur */
  .gir-banner__error-row {
    @apply flex items-center gap-3;
  }

  /* Score + libellé */
  .gir-banner__score {
    @apply flex items-center gap-3 mb-3;
  }
  .gir-banner__label {
    @apply text-sm font-medium text-slate-600;
  }

  /* Chip GIR coloré */
  .gir-chip {
    @apply inline-flex items-center justify-center
         px-3 py-1 rounded-lg text-sm font-bold text-white shrink-0;
  }
  .gir-chip--1 {
    @apply bg-red-600;
  }
  .gir-chip--2 {
    @apply bg-red-500;
  }
  .gir-chip--3 {
    @apply bg-orange-500;
  }
  .gir-chip--4 {
    @apply bg-amber-500;
  }
  .gir-chip--5 {
    @apply bg-lime-500;
  }
  .gir-chip--6 {
    @apply bg-green-500;
  }

  /* Règle visuelle 1 → 6 */
  .gir-scale {
    @apply flex items-center gap-2;
  }
  .gir-scale__legend {
    @apply text-[11px] text-slate-400 whitespace-nowrap shrink-0;
  }
  .gir-scale__track {
    @apply flex flex-1 items-center gap-1;
  }
  .gir-scale__step {
    @apply flex-1 flex items-center justify-center
         h-7 rounded-md text-xs font-semibold
         text-slate-300 bg-slate-100 border border-slate-200
         transition-all duration-200;
  }
  /* Couleurs des steps inactifs (teinte légère) */
  .gir-scale__step--1 {
    @apply text-red-300 bg-red-50 border-red-100;
  }
  .gir-scale__step--2 {
    @apply text-red-300 bg-red-50 border-red-100;
  }
  .gir-scale__step--3 {
    @apply text-orange-300 bg-orange-50 border-orange-100;
  }
  .gir-scale__step--4 {
    @apply text-amber-300 bg-amber-50 border-amber-100;
  }
  .gir-scale__step--5 {
    @apply text-lime-400 bg-lime-50 border-lime-100;
  }
  .gir-scale__step--6 {
    @apply text-green-400 bg-green-50 border-green-100;
  }
  /* Step actif : couleur pleine + légère ombre */
  .gir-scale__step--active.gir-scale__step--1 {
    @apply bg-red-600    text-white border-red-600    scale-110 shadow-sm;
  }
  .gir-scale__step--active.gir-scale__step--2 {
    @apply bg-red-500    text-white border-red-500    scale-110 shadow-sm;
  }
  .gir-scale__step--active.gir-scale__step--3 {
    @apply bg-orange-500 text-white border-orange-500 scale-110 shadow-sm;
  }
  .gir-scale__step--active.gir-scale__step--4 {
    @apply bg-amber-500  text-white border-amber-500  scale-110 shadow-sm;
  }
  .gir-scale__step--active.gir-scale__step--5 {
    @apply bg-lime-500   text-white border-lime-500   scale-110 shadow-sm;
  }
  .gir-scale__step--active.gir-scale__step--6 {
    @apply bg-green-500  text-white border-green-500  scale-110 shadow-sm;
  }
</style>